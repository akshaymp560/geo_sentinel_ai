import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from timm.models.vision_transformer import VisionTransformer

# --- Architecture matching manuelhorveydaniel/ChangeFormer ---
class FeatureDifferenceModule(nn.Module):
    def __init__(self, in_channels):
        super(FeatureDifferenceModule, self).__init__()
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
        super(DeconvDecoder, self).__init__()
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
        super(Sentinel2ChangeFormer, self).__init__()
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
        feat1 = self.encoder.forward_features(img1)
        feat2 = self.encoder.forward_features(img2)
        feat1 = feat1[:, 1:, :]
        feat2 = feat2[:, 1:, :]
        B, N, C = feat1.shape
        h = w = self.img_size // self.patch_size
        feat1 = feat1.transpose(1, 2).view(B, C, h, w)
        feat2 = feat2.transpose(1, 2).view(B, C, h, w)
        diff = self.feature_diff(feat1, feat2)
        out = self.decoder(diff)
        out = F.interpolate(out, size=(self.img_size, self.img_size), mode='bilinear', align_corners=False)
        return out

def test_pipeline():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"1. Target Device: {device}")

    weights_path = os.path.join("models", "best_model.pth")
    if not os.path.exists(weights_path):
        print(f"[ERROR] Could not find weights at {weights_path}")
        return

    print("2. Instantiating Sentinel-2 4-Band ChangeFormer...")
    model = Sentinel2ChangeFormer(img_size=256, num_classes=1).to(device)

    print("3. Loading checkpoint state dictionary...")
    state_dict = torch.load(weights_path, map_location=device)
    model.load_state_dict(state_dict)
    model.eval()
    print("-> State dictionary loaded successfully with 0 missing/unexpected keys!")

    print("4. Executing forward pass with dummy 4-band Sentinel-2 patches [B, 4, 256, 256]...")
    dummy_t1 = torch.randn(1, 4, 256, 256, device=device)
    dummy_t2 = torch.randn(1, 4, 256, 256, device=device)

    with torch.no_grad():
        logits = model(dummy_t1, dummy_t2)
        probs = torch.sigmoid(logits)
        mask = (probs > 0.5).long()

    print(f"-> Raw logits shape: {tuple(logits.shape)}")
    print(f"-> Predicted mask shape: {tuple(mask.shape)}")
    print("\n[PASS] Phase 2 complete. The model architecture, checkpoint, and forward pass are verified.")

if __name__ == "__main__":
    test_pipeline()