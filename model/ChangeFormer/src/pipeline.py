import os
import uuid
from typing import List, Tuple, Dict, Any
from gee_service import EarthEngineService
from detector_adapter import ChangeDetector


class ChangeDetectionPipeline:
    def __init__(self, project_id: str = "geosentinel-ai-511016", model_path: str = None):
        print("[Pipeline] Initializing Earth Engine Service...")
        self.gee_service = EarthEngineService(project_id=project_id)
        
        print("[Pipeline] Initializing ChangeFormer Detector...")
        self.detector = ChangeDetector(model_path=model_path)

    def run(
        self,
        bbox: List[float],
        pre_range: Tuple[str, str],
        post_range: Tuple[str, str],
        job_id: str = None,
        base_output_dir: str = "data/runs",
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Executes end-to-end ingestion and inference:
        1. Queries and downloads cloud-filtered Sentinel-2 pair via GEE.
        2. Runs tiled Siamese ViT inference with edge padding.
        3. Exports georeferenced binary change GeoTIFF.
        4. Compiles unified analytics payload.
        """
        if job_id is None:
            job_id = f"job_{uuid.uuid4().hex[:8]}"

        job_dir = os.path.abspath(os.path.join(base_output_dir, job_id))
        os.makedirs(job_dir, exist_ok=True)

        print(f"\n[Pipeline] Starting Job: {job_id}")
        print(f"[Pipeline] Workspace: {job_dir}")

        # Step 1: Fetch multi-temporal satellite pair
        print("[Pipeline] Step 1/2: Ingesting satellite data from GEE...")
        manifest = self.gee_service.fetch_temporal_pair(
            bbox=bbox,
            pre_range=pre_range,
            post_range=post_range,
            output_dir=job_dir,
            scale=10,
            max_cloud_pct=15
        )

        # Step 2: Execute Change Detection Inference
        output_mask_path = os.path.join(job_dir, "change_mask.tif")
        print("[Pipeline] Step 2/2: Running ChangeFormer ViT inference...")
        metrics, _ = self.detector.predict(
            pre_path=manifest["pre_path"],
            post_path=manifest["post_path"],
            output_mask_path=output_mask_path,
            batch_size=4,
            threshold=threshold
        )

        # Step 3: Package unified response payload
        unified_payload = {
            "job_id": job_id,
            "status": "COMPLETED",
            "metadata": {
                "bbox": bbox,
                "pre_acquisition_date": manifest["pre_date"],
                "post_acquisition_date": manifest["post_date"],
                "bands": manifest["bands"],
                "spatial_resolution_m": manifest["scale"],
                "crs": "EPSG:32643"
            },
            "artifacts": {
                "pre_geotiff": manifest["pre_path"],
                "post_geotiff": manifest["post_path"],
                "mask_geotiff": os.path.abspath(output_mask_path)
            },
            "analytics": {
                "dimensions": metrics["dimensions"],
                "total_pixels": metrics["total_pixels"],
                "changed_pixels": metrics["changed_pixels"],
                "change_percentage": metrics["change_percentage"],
                "estimated_change_ha": metrics["estimated_change_ha"]
            }
        }

        print(f"[Pipeline] Job {job_id} completed successfully.")
        return unified_payload


if __name__ == "__main__":
    print("ChangeDetectionPipeline compiled successfully.")