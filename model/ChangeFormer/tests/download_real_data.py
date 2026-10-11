import os
import ee
import geemap

def mask_s2_clouds(image):
    """Masks clouds in Sentinel-2 using the QA60 band."""
    qa = image.select('QA60')
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    return image.updateMask(mask)

def main():
    print("1. Initializing Earth Engine...")
    ee.Initialize(project='geosentinel-ai-511016')

    # Bounding box over Chooralmala / Meppadi, Wayanad (landslide epicenter)
    roi = ee.Geometry.Polygon(
        [[[76.150, 11.510], 
          [76.190, 11.510], 
          [76.190, 11.550], 
          [76.150, 11.550]]]
    )

    print("2. Querying clean pre-event and post-event imagery...")
    
    # Pre-event: Clear dry season scene (Feb-April 2024)
    pre_col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate('2024-02-01', '2024-04-15')
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 5))
        .sort('CLOUDY_PIXEL_PERCENTAGE')
    )

    # Post-event: Clear post-monsoon scene after the event (Dec 2024 - Jan 2025)
    post_col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate('2024-12-01', '2025-01-30')
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 5))
        .sort('CLOUDY_PIXEL_PERCENTAGE')
    )

    pre_img = pre_col.first().select(['B2', 'B3', 'B4', 'B8'])
    post_img = post_col.first().select(['B2', 'B3', 'B4', 'B8'])

    pre_path = os.path.abspath("real_test_data/pre_event.tif")
    post_path = os.path.abspath("real_test_data/post_event.tif")

    print(f"3. Downloading clean T1 to:\n   {pre_path}")
    geemap.ee_export_image(pre_img, filename=pre_path, scale=10, region=roi, file_per_band=False)

    print(f"4. Downloading clean T2 to:\n   {post_path}")
    geemap.ee_export_image(post_img, filename=post_path, scale=10, region=roi, file_per_band=False)

    print("\n[SUCCESS] Clean cloud-free satellite pair downloaded!")

if __name__ == "__main__":
    main()