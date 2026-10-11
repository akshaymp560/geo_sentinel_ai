import os
import math
import numpy as np
import rasterio
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from timm.models.vision_transformer import VisionTransformer


class FeatureDifferenceModule(nn.Module):
    def __init__(self, in_channels):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, in_channels // 2, kernel_size=3, padding=1)
        self.bn = nn.BatchNorm2d(in_channels // 2)
        self.relu = nn.ReLU()

    def forward(self, feat1, feat2):
        x = torch.abs(feat1 - feat2)
        x = self.conv(x)
        x = self.bn(x)
        x = self.relu(x)
        return x


class DeconvDecoder(nn.Module):
    def __init__(self, in_channels, num_classes):
        super().__init__()
        self.deconv1 = nn.ConvTranspose2d(in_channels // 2, 128, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.deconv2 = nn.ConvTranspose2d(128, 32, kernel_size=3, stride=2, padding=1, output_padding=1)
        self.deconv3 = nn.ConvTranspose2d(32, num_classes, kernel_size=3, stride=2, padding=1, output_padding=1)

    def forward(self, x):
        x = F.relu(self.deconv1(x))
        x = F.relu(self.deconv2(x))
        x = self.deconv3(x)
        return x


class Sentinel2ChangeFormer(nn.Module):
    def __init__(self, img_size=256, num_classes=1):
        super().__init__()
        self.encoder = VisionTransformer(
            img_size=img_size,
            patch_size=16,
            embed_dim=384,
            depth=4,
            num_heads=6,
            in_chans=4,
        )
        self.feature_diff = FeatureDifferenceModule(in_channels=384)
        self.decoder = DeconvDecoder(in_channels=384, num_classes=num_classes)
        self.img_size = img_size
        self.patch_size = 16

    def forward(self, img1, img2):
        feat1 = self.encoder.forward_features(img1)[:, 1:, :]
        feat2 = self.encoder.forward_features(img2)[:, 1:, :]
        B, N, C = feat1.shape
        h = w = self.img_size // self.patch_size
        feat1 = feat1.transpose(1, 2).view(B, C, h, w)
        feat2 = feat2.transpose(1, 2).view(B, C, h, w)
        diff = self.feature_diff(feat1, feat2)
        out = self.decoder(diff)
        out = F.interpolate(out, size=(self.img_size, self.img_size), mode='bilinear', align_corners=False)
        return out


class ChangeDetector:
    def __init__(self, model_path=None, device=None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.patch_size = 256
        self.transform = transforms.ToTensor()

        # Dynamic fallback: if None or default relative path, resolve relative to project root
        if model_path is None or not os.path.isabs(model_path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidate = os.path.join(base_dir, "models", "best_model.pth") if model_path is None else os.path.join(base_dir, model_path)
            if os.path.exists(candidate):
                model_path = candidate

        if not model_path or not os.path.exists(model_path):
            raise FileNotFoundError(f"Weights file not found at: {model_path}")

        print(f"Loading ChangeFormer detector on {self.device}...")
        print(f"Weights path: {model_path}")
        self.model = Sentinel2ChangeFormer(img_size=self.patch_size, num_classes=1).to(self.device)
        state_dict = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.eval()
        print("ChangeFormer initialized successfully.")

    def predict(self, pre_path, post_path, output_mask_path=None, batch_size=4, threshold=0.5):
        """
        Runs tiled change detection on two 4-band Sentinel-2 GeoTIFFs (B2, B3, B4, B8).
        Uses verified disturbance semantics (Prob < threshold = Disturbance).
        """
        with rasterio.open(pre_path) as src_pre, rasterio.open(post_path) as src_post:
            if src_pre.count < 4 or src_post.count < 4:
                raise ValueError("Both images must contain at least 4 bands (B2, B3, B4, B8).")

            if (src_pre.width, src_pre.height) != (src_post.width, src_post.height):
                raise ValueError(f"Dimension mismatch: Pre ({src_pre.width}x{src_pre.height}) vs Post ({src_post.width}x{src_post.height})")

            w, h = src_pre.width, src_pre.height
            meta = src_pre.meta.copy()

            img1 = src_pre.read([1, 2, 3, 4]).astype(np.float32)
            img2 = src_post.read([1, 2, 3, 4]).astype(np.float32)

        # Transpose to (H, W, C)
        img1 = np.transpose(img1, (1, 2, 0))
        img2 = np.transpose(img2, (1, 2, 0))

        # Normalize reflectance to [0.0, 1.0]
        if np.nanmax(img1) > 1.0:
            img1 = np.clip(img1 / 10000.0, 0.0, 1.0)
        if np.nanmax(img2) > 1.0:
            img2 = np.clip(img2 / 10000.0, 0.0, 1.0)

        img1 = np.nan_to_num(img1, nan=0.0)
        img2 = np.nan_to_num(img2, nan=0.0)

        # Dynamic reflection padding to multiples of 256
        pad_h = math.ceil(h / self.patch_size) * self.patch_size - h
        pad_w = math.ceil(w / self.patch_size) * self.patch_size - w

        if pad_h > 0 or pad_w > 0:
            img1 = np.pad(img1, ((0, pad_h), (0, pad_w), (0, 0)), mode='reflect')
            img2 = np.pad(img2, ((0, pad_h), (0, pad_w), (0, 0)), mode='reflect')

        padded_h, padded_w, _ = img1.shape
        coords = [(x, y) for y in range(0, padded_h, self.patch_size)
                         for x in range(0, padded_w, self.patch_size)]

        raw_probs = np.zeros((padded_h, padded_w), dtype=np.float32)

        for i in range(0, len(coords), batch_size):
            batch_coords = coords[i:i + batch_size]
            b_t1, b_t2 = [], []

            for x, y in batch_coords:
                p1 = img1[y:y + self.patch_size, x:x + self.patch_size, :]
                p2 = img2[y:y + self.patch_size, x:x + self.patch_size, :]
                b_t1.append(self.transform(p1))
                b_t2.append(self.transform(p2))

            t1_tensor = torch.stack(b_t1).to(self.device)
            t2_tensor = torch.stack(b_t2).to(self.device)

            with torch.no_grad():
                logits = self.model(t1_tensor, t2_tensor)
                probs = torch.sigmoid(logits).squeeze(1).cpu().numpy()
                if probs.ndim == 2:
                    probs = np.expand_dims(probs, axis=0)

                for p, (x, y) in zip(probs, batch_coords):
                    raw_probs[y:y + self.patch_size, x:x + self.patch_size] = p

        # Crop back to original dimensions
        cropped_probs = raw_probs[:h, :w]

        # Validated disturbance semantics: Values below threshold indicate disturbance
        final_mask = (cropped_probs < threshold).astype(np.uint8)

        total_pixels = int(h * w)
        changed_pixels = int(np.sum(final_mask == 1))
        change_percentage = round((changed_pixels / total_pixels) * 100.0, 4)
        area_ha = round(changed_pixels * 0.01, 2)  # 10m pixel = 100 m² = 0.01 ha

        results = {
            "dimensions": {"width": w, "height": h},
            "total_pixels": total_pixels,
            "changed_pixels": changed_pixels,
            "change_percentage": change_percentage,
            "estimated_change_ha": area_ha,
            "output_mask_path": output_mask_path
        }

        if output_mask_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_mask_path)), exist_ok=True)
            meta.update({
                "count": 1,
                "dtype": "uint8",
                "nodata": 0
            })
            with rasterio.open(output_mask_path, "w", **meta) as dst:
                dst.write(final_mask, 1)

        return results, final_mask


if __name__ == "__main__":
    print("detector_adapter.py successfully updated and locked.")