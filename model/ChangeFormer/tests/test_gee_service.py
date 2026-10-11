import os
import sys

# Ensure src/ is discoverable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import rasterio
from gee_service import EarthEngineService

def run_test():
    print("1. Initializing EarthEngineService...")
    service = EarthEngineService(project_id="geosentinel-ai-511016")

    # Bounding box: [min_lon, min_lat, max_lon, max_lat] (Wayanad AOI)
    bbox = [76.150, 11.510, 76.180, 11.540]
    pre_range = ("2024-02-01", "2024-04-15")
    post_range = ("2024-12-01", "2025-01-30")
    
    test_output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "gee_test_output"))

    print("\n2. Executing automated fetch_temporal_pair query...")
    manifest = service.fetch_temporal_pair(
        bbox=bbox,
        pre_range=pre_range,
        post_range=post_range,
        output_dir=test_output_dir,
        scale=10,
        max_cloud_pct=15
    )

    print("\n3. Returned Manifest:")
    for k, v in manifest.items():
        print(f"   {k}: {v}")

    print("\n4. Validating Downloaded Raster Contracts:")
    for key, path in [("Pre-event", manifest["pre_path"]), ("Post-event", manifest["post_path"])]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing expected output raster: {path}")
            
        with rasterio.open(path) as src:
            print(f"   [{key}]")
            print(f"     Path: {path}")
            print(f"     Dimensions: {src.width} x {src.height}")
            print(f"     Band count: {src.count} (Expected: 4)")
            print(f"     CRS: {src.crs}")
            assert src.count == 4, f"Expected 4 bands, got {src.count}"

    print("\n[PASS] Phase 4 GEE Ingestion Service fully verified.")

if __name__ == "__main__":
    run_test()