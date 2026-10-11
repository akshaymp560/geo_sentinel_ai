import os
import sys

# Ensure src/ is on Python module search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pipeline import ChangeDetectionPipeline

def run_e2e_test():
    print("=== Testing Automated End-to-End Pipeline ===")
    
    orchestrator = ChangeDetectionPipeline(project_id="geosentinel-ai-511016")

    # Wayanad coordinates: [min_lon, min_lat, max_lon, max_lat]
    bbox = [76.150, 11.510, 76.180, 11.540]
    pre_range = ("2024-02-01", "2024-04-15")
    post_range = ("2024-12-01", "2025-01-30")

    result = orchestrator.run(
        bbox=bbox,
        pre_range=pre_range,
        post_range=post_range,
        job_id="test_run_e2e",
        base_output_dir="data/runs",
        threshold=0.5
    )

    print("\n=== Pipeline Execution Completed Successfully ===")
    print(f"Job ID: {result['job_id']}")
    print(f"Pre Date: {result['metadata']['pre_acquisition_date']}")
    print(f"Post Date: {result['metadata']['post_acquisition_date']}")
    print(f"Mask Path: {result['artifacts']['mask_geotiff']}")
    print(f"Change Percentage: {result['analytics']['change_percentage']}%")
    print(f"Disturbed Area: {result['analytics']['estimated_change_ha']} ha")

if __name__ == "__main__":
    run_e2e_test()