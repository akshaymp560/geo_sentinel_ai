import os
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from detector_adapter import ChangeDetector

def run_inverted_test():
    pre_path = os.path.join("real_test_data", "pre_event.tif")
    post_path = os.path.join("real_test_data", "post_event.tif")
    mask_path = os.path.join("real_test_data", "detected_mask.tif")

    print("1. Running ChangeFormer with inverted disturbance semantics...")
    detector = ChangeDetector(model_path="models/best_model.pth")
    
    # Notice: Inverted logic -> Change is where probability drops below 0.5
    # We will compute the mask where prob < 0.5
    with rasterio.open(pre_path) as src_pre, rasterio.open(post_path) as src_post:
        w, h = src_pre.width, src_pre.height
        meta = src_pre.meta.copy()
        img1 = src_pre.read([1, 2, 3, 4]).astype(np.float32)
        img2 = src_post.read([1, 2, 3, 4]).astype(np.float32)

    img1 = np.transpose(img1, (1, 2, 0))
    img2 = np.transpose(img2, (1, 2, 0))

    if np.nanmax(img1) > 1.0:
        img1 = np.clip(img1 / 10000.0, 0.0, 1.0)
    if np.nanmax(img2) > 1.0:
        img2 = np.clip(img2 / 10000.0, 0.0, 1.0)

    # Pad to multiple of 256
    import math
    import torch
    pad_h = math.ceil(h / 256) * 256 - h
    pad_w = math.ceil(w / 256) * 256 - w
    if pad_h > 0 or pad_w > 0:
        img1 = np.pad(img1, ((0, pad_h), (0, pad_w), (0, 0)), mode='reflect')
        img2 = np.pad(img2, ((0, pad_h), (0, pad_w), (0, 0)), mode='reflect')

    padded_h, padded_w, _ = img1.shape
    coords = [(x, y) for y in range(0, padded_h, 256) for x in range(0, padded_w, 256)]
    raw_probs = np.zeros((padded_h, padded_w), dtype=np.float32)

    for i in range(0, len(coords), 4):
        batch_coords = coords[i:i + 4]
        b_t1, b_t2 = [], []
        for x, y in batch_coords:
            p1 = img1[y:y + 256, x:x + 256, :]
            p2 = img2[y:y + 256, x:x + 256, :]
            b_t1.append(detector.transform(p1))
            b_t2.append(detector.transform(p2))

        t1_t = torch.stack(b_t1).to(detector.device)
        t2_t = torch.stack(b_t2).to(detector.device)

        with torch.no_grad():
            logits = detector.model(t1_t, t2_t)
            probs = torch.sigmoid(logits).squeeze(1).cpu().numpy()
            if probs.ndim == 2:
                probs = np.expand_dims(probs, axis=0)

            for p, (x, y) in zip(probs, batch_coords):
                raw_probs[y:y + 256, x:x + 256] = p

    cropped_probs = raw_probs[:h, :w]
    
    # --- SEMANTIC FIX ---
    # Prob ~ 1.0 is Stable Forest.
    # Disturbance / Change is where Prob < 0.5:
    disturbance_mask = (cropped_probs < 0.5).astype(np.uint8)

    total_pixels = int(h * w)
    changed_pixels = int(np.sum(disturbance_mask == 1))
    change_pct = round((changed_pixels / total_pixels) * 100.0, 4)
    area_ha = round(changed_pixels * 0.01, 2)

    print("\n=== Corrected Metrics Payload ===")
    print(f"Dimensions: {w} x {h}")
    print(f"Total Pixels: {total_pixels}")
    print(f"True Disturbance Pixels: {changed_pixels}")
    print(f"True Change Percentage: {change_pct}%")
    print(f"Disturbed Area: {area_ha} ha")

    # Visual Plot
    with rasterio.open(pre_path) as pre, rasterio.open(post_path) as post:
        pre_rgb = pre.read([3, 2, 1]).astype(np.float32)
        post_rgb = post.read([3, 2, 1]).astype(np.float32)

    def stretch(arr):
        arr = np.transpose(arr, (1, 2, 0))
        p2, p98 = np.percentile(arr, 2), np.percentile(arr, 98)
        return np.clip((arr - p2) / (p98 - p2) if p98 > p2 else arr / 255.0, 0, 1)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(stretch(pre_rgb))
    axes[0].set_title("Pre-Event (T1)")
    axes[0].axis('off')

    axes[1].imshow(stretch(post_rgb))
    axes[1].set_title("Post-Event (T2)")
    axes[1].axis('off')

    axes[2].imshow(disturbance_mask, cmap='hot')
    axes[2].set_title(f"True Disturbance Mask ({change_pct}%)")
    axes[2].axis('off')

    plt.tight_layout()
    plt.savefig("real_test_data/corrected_proof.png", dpi=200)
    print("-> Saved corrected plot to real_test_data/corrected_proof.png")
    plt.show()

if __name__ == "__main__":
    run_inverted_test()