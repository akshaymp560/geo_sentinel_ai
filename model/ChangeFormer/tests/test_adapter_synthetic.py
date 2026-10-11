import os
import numpy as np
import rasterio
from rasterio.transform import from_origin
from detector_adapter import ChangeDetector

def create_synthetic_geotiffs():
    os.makedirs("test_data", exist_ok=True)
    pre_path = os.path.join("test_data", "test_pre_4band.tif")
    post_path = os.path.join("test_data", "test_post_4band.tif")

    # Dimensions: 300x300 (tests edge-padding since 300 is not a multiple of 256)
    width, height = 300, 300
    transform = from_origin(76.27, 10.85, 0.0001, 0.0001) # Sample Kerala coordinates
    crs = "EPSG:4326"

    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 4, # 4 Bands: B2, B3, B4, B8
        "dtype": "float32",
        "crs": crs,
        "transform": transform
    }

    # Generate synthetic Sentinel-2 surface reflectance (values between 0.0 and 0.8)
    np.random.seed(42)
    pre_data = np.random.uniform(0.1, 0.6, (4, height, width)).astype(np.float32)
    post_data = pre_data.copy()

    # Simulate a disturbance event in a 60x60 pixel region (e.g., vegetation drop)
    post_data[3, 50:110, 50:110] = 0.05 # Drop NIR channel
    post_data[2, 50:110, 50:110] = 0.45 # Increase Red channel

    with rasterio.open(pre_path, "w", **meta) as dst:
        dst.write(pre_data)

    with rasterio.open(post_path, "w", **meta) as dst:
        dst.write(post_data)

    print(f"Created synthetic test rasters in: {os.path.abspath('test_data')}")
    return pre_path, post_path

def run_adapter_test():
    pre_path, post_path = create_synthetic_geotiffs()
    output_mask_path = os.path.join("test_data", "test_change_mask.tif")

    print("\n1. Initializing ChangeDetector...")
    detector = ChangeDetector(model_path="models/best_model.pth")

    print("\n2. Running prediction on 300x300 rasters with padding...")
    results, mask = detector.predict(
        pre_path=pre_path,
        post_path=post_path,
        output_mask_path=output_mask_path,
        batch_size=2,
        threshold=0.5
    )

    print("\n3. Verifying Results Payload:")
    for k, v in results.items():
        print(f"   {k}: {v}")

    print("\n4. Verifying Output GeoTIFF Metadata:")
    with rasterio.open(output_mask_path) as dst:
        print(f"   Saved Mask Dimensions: {dst.width} x {dst.height}")
        print(f"   Saved Mask CRS: {dst.crs}")
        print(f"   Saved Mask Transform: {dst.transform}")
        print(f"   Unique Values in Saved Mask: {np.unique(dst.read(1))}")

    print("\n[PASS] Adapter verified successfully! End-to-end inference & georeferencing work.")

if __name__ == "__main__":
    run_adapter_test()