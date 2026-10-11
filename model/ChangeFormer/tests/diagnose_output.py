import os
import torch
import numpy as np
import rasterio
from detector_adapter import ChangeDetector

def diagnose():
    pre_path = os.path.join("real_test_data", "pre_event.tif")
    post_path = os.path.join("real_test_data", "post_event.tif")

    # 1. Inspect raw GeoTIFF stats
    with rasterio.open(pre_path) as src:
        print("=== 1. GeoTIFF Band Statistics (pre_event.tif) ===")
        print(f"Data type: {src.dtypes[0]}")
        for b in range(1, 5):
            arr = src.read(b)
            print(f"Band {b} -> Min: {np.nanmin(arr):.2f}, Max: {np.nanmax(arr):.2f}, Mean: {np.nanmean(arr):.2f}")

    detector = ChangeDetector(model_path="models/best_model.pth")
    detector.model.eval()

    # 2. Test identical images (T1 vs T1)
    print("\n=== 2. Identical Image Test (T1 vs T1) ===")
    results_identical, mask_identical = detector.predict(
        pre_path=pre_path,
        post_path=pre_path,
        batch_size=4,
        threshold=0.5
    )
    print(f"Identical Test Change % (at > 0.5): {results_identical['change_percentage']}%")

    # 3. Inspect raw logits and probability distribution
    # Extract one 256x256 patch from T1 and T2
    with rasterio.open(pre_path) as src1, rasterio.open(post_path) as src2:
        p1 = src1.read([1, 2, 3, 4], window=rasterio.windows.Window(0, 0, 256, 256)).astype(np.float32)
        p2 = src2.read([1, 2, 3, 4], window=rasterio.windows.Window(0, 0, 256, 256)).astype(np.float32)

    # Scale to [0, 1]
    p1 = np.clip(p1 / 10000.0, 0, 1)
    p2 = np.clip(p2 / 10000.0, 0, 1)

    t1 = torch.from_numpy(p1).unsqueeze(0).to(detector.device)
    t2 = torch.from_numpy(p2).unsqueeze(0).to(detector.device)

    with torch.no_grad():
        # Case A: Identical
        logits_same = detector.model(t1, t1)
        prob_same = torch.sigmoid(logits_same)

        # Case B: T1 vs T2
        logits_diff = detector.model(t1, t2)
        prob_diff = torch.sigmoid(logits_diff)

    print("\n=== 3. Raw Probabilities (Sigmoid) ===")
    print(f"Identical inputs (T1 vs T1) -> Min prob: {prob_same.min().item():.4f}, Max prob: {prob_same.max().item():.4f}, Mean prob: {prob_same.mean().item():.4f}")
    print(f"Real pair (T1 vs T2)         -> Min prob: {prob_diff.min().item():.4f}, Max prob: {prob_diff.max().item():.4f}, Mean prob: {prob_diff.mean().item():.4f}")

    # Case C: What if inputs are uint8 scaled [0, 255]?
    t1_255 = t1 * 255.0
    t2_255 = t2 * 255.0
    with torch.no_grad():
        prob_255_same = torch.sigmoid(detector.model(t1_255, t1_255))
        prob_255_diff = torch.sigmoid(detector.model(t1_255, t2_255))
    print("\n=== 4. Test If Model Expects [0, 255] Range ===")
    print(f"[0, 255] scale identical   -> Mean prob: {prob_255_same.mean().item():.4f}")
    print(f"[0, 255] scale real pair   -> Mean prob: {prob_255_diff.mean().item():.4f}")

if __name__ == "__main__":
    diagnose()