import os
from typing import Any, Dict, List, Tuple
import ee
import geemap


class EarthEngineService:
    def __init__(self, project_id: str = "geosentinel-ai-511016"):
        self.project_id = project_id
        self._initialize_ee()

    def _initialize_ee(self):
        try:
            ee.Initialize(project=self.project_id)
            print(f"[GEE] Earth Engine initialized successfully (Project: {self.project_id})")
        except Exception as e:
            raise RuntimeError(
                f"[GEE Error] Could not initialize Earth Engine with project '{self.project_id}'. "
                f"Verify credentials via 'earthengine authenticate'. Details: {e}"
            )

    @staticmethod
    def _mask_s2_clouds(image: ee.Image) -> ee.Image:
        """Masks Sentinel-2 L2A clouds using the QA60 bitmask."""
        qa = image.select('QA60')
        cloud_bit = 1 << 10
        cirrus_bit = 1 << 11
        clear_mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
        return image.updateMask(clear_mask)

    def fetch_temporal_pair(
        self,
        bbox: List[float],
        pre_range: Tuple[str, str],
        post_range: Tuple[str, str],
        output_dir: str,
        scale: int = 10,
        max_cloud_pct: int = 15
    ) -> Dict[str, Any]:
        """
        Fetches an aligned, cloud-filtered 4-band Sentinel-2 pair (Pre and Post)
        for a given bounding box.

        Args:
            bbox: [min_lon, min_lat, max_lon, max_lat]
            pre_range: ('YYYY-MM-DD', 'YYYY-MM-DD')
            post_range: ('YYYY-MM-DD', 'YYYY-MM-DD')
            output_dir: Directory where GeoTIFFs will be saved
            scale: Spatial resolution in meters (default: 10m native)
            max_cloud_pct: Maximum allowed cloud metadata percentage

        Returns:
            Dictionary containing output paths, metadata, and acquisition dates
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        roi = ee.Geometry.Polygon([
            [[min_lon, min_lat], [max_lon, min_lat],
             [max_lon, max_lat], [min_lon, max_lat],
             [min_lon, min_lat]]
        ])

        bands = ['B2', 'B3', 'B4', 'B8']

        # 1. Query Pre-event Collection
        pre_col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(pre_range[0], pre_range[1])
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_pct))
            .sort('CLOUDY_PIXEL_PERCENTAGE')
        )

        # 2. Query Post-event Collection
        post_col = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(roi)
            .filterDate(post_range[0], post_range[1])
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_pct))
            .sort('CLOUDY_PIXEL_PERCENTAGE')
        )

        pre_count = pre_col.size().getInfo()
        post_count = post_col.size().getInfo()

        if pre_count == 0:
            raise ValueError(f"No Sentinel-2 imagery with <{max_cloud_pct}% clouds found for Pre-range {pre_range}")
        if post_count == 0:
            raise ValueError(f"No Sentinel-2 imagery with <{max_cloud_pct}% clouds found for Post-range {post_range}")

        pre_img = pre_col.first()
        post_img = post_col.first()

        pre_date = ee.Date(pre_img.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        post_date = ee.Date(post_img.get('system:time_start')).format('YYYY-MM-dd').getInfo()

        os.makedirs(output_dir, exist_ok=True)
        pre_file = os.path.join(output_dir, f"pre_{pre_date}.tif")
        post_file = os.path.join(output_dir, f"post_{post_date}.tif")

        print(f"[GEE] Exporting Pre-event image ({pre_date}) to {pre_file}...")
        geemap.ee_export_image(
            pre_img.select(bands),
            filename=pre_file,
            scale=scale,
            region=roi,
            file_per_band=False
        )

        print(f"[GEE] Exporting Post-event image ({post_date}) to {post_file}...")
        geemap.ee_export_image(
            post_img.select(bands),
            filename=post_file,
            scale=scale,
            region=roi,
            file_per_band=False
        )

        return {
            "pre_path": os.path.abspath(pre_file),
            "post_path": os.path.abspath(post_file),
            "pre_date": pre_date,
            "post_date": post_date,
            "bbox": bbox,
            "scale": scale,
            "bands": bands
        }


if __name__ == "__main__":
    service = EarthEngineService()
    print("[GEE Service] Module ready for automated ingestion.")