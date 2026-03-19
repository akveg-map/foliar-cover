import os
import sys
import argparse
import glob
import re
import datetime
import math
import subprocess
import json

# Try importing rasterio for local footprint extraction
try:
    import rasterio
    from rasterio.warp import transform_geom
except ImportError:
    print("Error: rasterio is required. Please install it.")
    sys.exit(1)

# Try importing earthengine-api
try:
    import ee
except ImportError:
    print("Error: earthengine-api is required. Please install it.")
    sys.exit(1)

"""
202_export_ccdc_sr.py

Description:
    Step 202 of VHR Workflow (formerly Step 215).
    Generates synthetic Landsat Surface Reflectance imagery matching the 
    date and location of input VHR files using CCDC model coefficients.
    
    This script ports logic from 'vhr_ccdc_sr_export_prototype.js'.
    It reads local VHR files (Ortho) to determine the extent and acquisition date,
    then submits Earth Engine export tasks to generate the corresponding
    CCDC-predicted Landsat imagery.
    
    This runs early in the pipeline to allow EE tasks to process asynchronously.

Usage:
    python 202_export_ccdc_sr.py \
        --input "/path/to/01_ortho" \
        --bucket "akveg-data" \
        --prefix "vhr/landsat_ccdc_sr" \
        --project "your-google-cloud-project"
"""

def parse_maxar_date(filename):
    """
    Parses date from Maxar filename (e.g., 22AUG03213641-M1BS...).
    Returns datetime object and formatted string YYYYMMDD_HHMMSS.
    """
    # 1. Look for YYYYMMDD_HHMMSS (New Format - Preferred)
    match_new = re.search(r'(\d{8})_(\d{6})', filename)
    if match_new:
        ts_str = match_new.group(1) + match_new.group(2)
        try:
            return datetime.datetime.strptime(ts_str, "%Y%m%d%H%M%S"), f"{match_new.group(1)}_{match_new.group(2)}"
        except ValueError:
            pass

    # 2. Try PGC/Full Timestamp format (YYYYMMDDHHMMSS)
    # Look for 14 digits (Note: This can match CatIDs, so we catch ValueError)
    match_full = re.search(r'(\d{14})', filename)
    if match_full:
        ts_str = match_full.group(1)
        try:
            return datetime.datetime.strptime(ts_str, "%Y%m%d%H%M%S"), f"{ts_str[:8]}_{ts_str[8:]}"
        except ValueError:
            pass

    # Regex for YYMMMDDHHMMSS (e.g., 22AUG03213641)
    match = re.search(r'(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})(\d{2})', filename, re.IGNORECASE)
    if not match:
        return None, None
    
    yy, mmm, dd, hh, mm, ss = match.groups()
    
    # Handle century (assuming 20xx)
    year = int("20" + yy)
    
    month_map = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    month = month_map.get(mmm.upper())
    
    if not month:
        return None, None
        
    dt = datetime.datetime(year, month, int(dd), int(hh), int(mm), int(ss))
    formatted = dt.strftime("%Y%m%d_%H%M%S")
    return dt, formatted

def get_footprint(filepath):
    """
    Returns the footprint of the image as an ee.Geometry.Polygon.
    Uses raster bounding box for efficiency.
    """
    with rasterio.open(filepath) as src:
        # Get bounds
        bounds = src.bounds
        # Create polygon from bounds (xmin, ymin, xmax, ymax)
        # (left, bottom, right, top)
        geom = {
            'type': 'Polygon',
            'coordinates': [[
                [bounds.left, bounds.bottom],
                [bounds.left, bounds.top],
                [bounds.right, bounds.top],
                [bounds.right, bounds.bottom],
                [bounds.left, bounds.bottom]
            ]]
        }
        
        # Reproject to WGS84 if needed
        if src.crs.to_epsg() != 4326:
            geom = transform_geom(src.crs, 'EPSG:4326', geom)
            
        return ee.Geometry.Polygon(geom['coordinates'])

def get_ccdc_prediction(target_date_dt, region):
    """
    Constructs the CCDC prediction image for the given date.
    Replicates logic from vhr_ccdc_sr_export_prototype.js
    """
    
    # 1. Handle Date Logic (The "2022/2021 Hack" from JS)
    # JS: if date > 2022-07-01, use 2021 date with same month/day
    # cutoff = datetime.datetime(2022, 7, 1)
    # if target_date_dt > cutoff:
    #     sim_date = target_date_dt.replace(year=2021)
    # else:
    #     sim_date = target_date_dt
        
    # ee_date = ee.Date(sim_date)
    ee_date = ee.Date(target_date_dt)
    fractional_year = ee_date.get('year').add(ee_date.getFraction('year'))
    
    # 2. Load CCDC Collections
    ccdc = ee.ImageCollection([
        ee.ImageCollection("projects/CCDC/measures/v1").mosaic(),
        ee.ImageCollection("projects/CCDC/measures/v1_overlap").mosaic()
    ]).mosaic()
    
    # 3. Select Bands
    # CCDC v1 usually has: BLUE_coefs, GREEN_coefs, RED_coefs, NIR_coefs, tStart, tEnd
    # Coefs are [INTP, SLP, COS1, SIN1, COS2, SIN2, COS3, SIN3]
    bands = ['BLUE', 'GREEN', 'RED', 'NIR']
    
    # 4. Find Segment
    # tStart <= t < tEnd
    tStart = ccdc.select('tStart')
    tEnd = ccdc.select('tEnd')
    
    # 1. Strict Match Mask: Check if date is within [tStart, tEnd)
    strict_match = tStart.lte(fractional_year).And(tEnd.gt(fractional_year))
    
    # 2. Forward Extrapolation Logic
    # If the date is after the last segment, use the last segment.
    # NOTE: This could create issues if there is a disturbance after the CCDC record ended.
    
    # Find the latest tEnd across all segments for each pixel
    # arrayReduce returns an array of size 1. Convert to scalar Image for broadcasting.
    max_tEnd_array = tEnd.arrayReduce(ee.Reducer.max(), [0])
    max_tEnd = max_tEnd_array.arrayGet([0])
    
    # Identify the last segment
    is_last_segment = tEnd.eq(max_tEnd)
    # Check if we have a strict match
    has_strict_match_array = strict_match.arrayReduce(ee.Reducer.max(), [0])
    has_strict_match = has_strict_match_array.arrayGet([0])
    # We extrapolate if: No strict match AND Date >= max_tEnd
    should_extrapolate = has_strict_match.Not().And(max_tEnd.lte(fractional_year))
    
    # Combine: Use strict match OR (Last Segment IF Extrapolating)
    segment_mask = strict_match.add(is_last_segment.multiply(should_extrapolate))

    # Determine if any segment matched (for final masking)
    has_segment = segment_mask.arrayReduce(ee.Reducer.max(), [0]).arrayFlatten([['has_segment']])
    
    # Reshape mask to 2D [segments, 1] to match coefs dimensions for arrayMask
    seg_count = segment_mask.arrayLength(0)
    shape_2d = ee.Image.cat([seg_count, ee.Image(1)]).toArray()
    segment_mask_2d = segment_mask.arrayReshape(shape_2d, 2)
    
    # If multiple segments match (overlap), usually take the last one or first? 
    # Standard CCDC logic often takes the one that matches.
    # We need to project the array to a single image based on the mask.
    
    # Helper to predict for a single band
    def predict_band(band_name):
        coefs = ccdc.select(band_name + '_coefs') # 2D array
        
        # Filter coefs to the matching segment
        # arrayMask keeps elements where mask is 1. 
        # We expect exactly 1 segment to match in a well-formed CCDC result, 
        # but overlaps can happen. We take the first match.
        valid_coefs = coefs.arrayMask(segment_mask_2d)
        
        # If no segment matches, we might want to extrapolate (JS had extrapolateMaxDays: 0)
        # For now, let's assume coverage. If empty, it will be masked.
        
        # Flatten to 1D array (8 coefficients)
        # .project([1]) reduces the segment dimension (0) leaving the coef dimension (1)
        # We take the first valid segment found.
        final_coefs = valid_coefs.arrayProject([1]) 
        
        # Harmonic Model
        # t = fractional_year
        # omega = 2 * pi
        # P(t) = c0 + c1*t + c2*cos(wt) + c3*sin(wt) + c4*cos(2wt) + c5*sin(2wt) + c6*cos(3wt) + c7*sin(3wt)
        
        t = fractional_year
        omega = 2.0 * math.pi
        
        # Construct harmonic terms vector
        # Note: CCDC v1 coef order is usually [INTP, SLP, COS, SIN, COS, SIN, COS, SIN]
        # Check if slope is c1. Yes, usually.
        
        terms = ee.Image.cat([
            ee.Image(1),
            t,
            t.multiply(omega).cos(),
            t.multiply(omega).sin(),
            t.multiply(omega * 2).cos(),
            t.multiply(omega * 2).sin(),
            t.multiply(omega * 3).cos(),
            t.multiply(omega * 3).sin()
        ]).toArray()
        
        # Dot product
        predicted = final_coefs.multiply(terms).arrayReduce(ee.Reducer.sum(), [0])
        
        return predicted.arrayFlatten([[band_name.lower() + '_ccdc']])

    # Predict all bands
    predicted_img = ee.Image.cat([predict_band(b) for b in bands])
    
    # Mask pixels where no segment matched (prevents 0 values from sum reducer)
    predicted_img = predicted_img.updateMask(has_segment)
    
    # 5. Add Water Occurrence
    # Water mask is independent of CCDC. unmask(0) makes "no water" explicit 0.
    water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence').rename('water_occurrence').unmask(0)
    
    # 6. Scale and Clamp (from JS)
    # .multiply(10000).clamp(0, 16000) to fit uint16 with 65535 as nodata
    # Explicitly unmask spectral bands to 65535 to ensure gaps are not filled with 0
    # when combined with the unmasked water band.
    spectral_scaled = predicted_img.multiply(10000).clamp(0, 16000).uint16().unmask(65535)
    
    # Rename bands to standard names
    spectral_scaled = spectral_scaled.select(
        ['blue_ccdc', 'green_ccdc', 'red_ccdc', 'nir_ccdc'],
        ['blue', 'green', 'red', 'nir']
    )
    
    water = water.rename('water_occurrence')
    
    # 6b. Calculate Days Extrapolated
    # (fractional_year - max_tEnd) * 365.25
    # Clamped to 0 if VHR date is before last tEnd.
    days_extrapolated = ee.Image(fractional_year).subtract(max_tEnd).multiply(365.25)
    days_extrapolated = days_extrapolated.updateMask(has_segment).max(0).uint16().unmask(0).rename('days_extrapolated')
    
    final_img = spectral_scaled.addBands(water.uint16()).addBands(days_extrapolated)
    
    # 7. Clip to region
    return final_img.clip(region)

def check_gcs_exists(gcs_path):
    """Checks if a file exists on GCS using gsutil."""
    try:
        subprocess.check_call(["gsutil", "ls", gcs_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    parser = argparse.ArgumentParser(description="Export CCDC Synthetic Landsat Imagery")
    parser.add_argument("--input", required=True, help="Folder containing VHR files (to derive date/extent)")
    parser.add_argument("--bucket", default="akveg-data", help="GCS Bucket for export")
    parser.add_argument("--prefix", default="vhr/landsat_ccdc_sr_pipeline", help="GCS Prefix for export")
    parser.add_argument("--project", help="Google Cloud Project for EE")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing GCS files")
    parser.add_argument("--dry-run", action="store_true", help="Print tasks without submitting")
    args = parser.parse_args()

    # Initialize Earth Engine
    try:
        ee.Initialize(project=args.project)
        print(f"Earth Engine Project: {args.project}")
    except Exception as e:
        print(f"Failed to initialize Earth Engine: {e}")
        print("Try running 'earthengine authenticate' first.")
        sys.exit(1)

    # Find images
    extensions = ["*.tif", "*.TIF", "*.ntf", "*.NTF"]
    images = []
    for ext in extensions:
        images.extend(glob.glob(os.path.join(args.input, ext)))
        
    # Filter for TOA or Ortho files to avoid duplicates
    # Prefer _toa.tif if available, else _ortho.tif
    images = [img for img in images if "TOA" in img or "Ortho" in img or "_toa" in img or "_ortho" in img]
    
    # Sort to ensure deterministic order and prioritize MS (ms < pan)
    images.sort()
    
    print(f"Found {len(images)} images.")

    processed_dates = set()

    for img_path in images:
        filename = os.path.basename(img_path)
        
        # Parse Date
        dt, date_str = parse_maxar_date(filename)
        if not dt:
            print(f"Skipping {filename}: Could not parse date.")
            continue
        
        # Deduplicate: Only process one image per unique timestamp (e.g. skip Pan if MS processed)
        if date_str in processed_dates:
            continue
        processed_dates.add(date_str)
            
        # Define Export Name
        # JS: var fileNoExt = 'ccdc_'+yyyymmdd_hhmmss;
        export_name = f"ccdc_{date_str}"
        
        print(f"Processing {filename} -> {export_name} ({dt})")
        
        # Get Geometry
        region = get_footprint(img_path)
        
        # Generate Image
        result_img = get_ccdc_prediction(dt, region)
        
        # Define Export Task
        # JS: crs_transform = [30.0, 0.0, 15.0, 0.0, -30.0, 15.0]
        # JS: crs = 'EPSG:3338'
        crs_transform = [30.0, 0.0, 15.0, 0.0, -30.0, 15.0]
        crs = 'EPSG:3338'
        
        # Store output location in variable
        gcs_output_path = f"gs://{args.bucket}/{args.prefix}/{export_name}.tif"
        print(f"  Output GCS Path: {gcs_output_path}")

        if not args.overwrite and check_gcs_exists(gcs_output_path):
            print(f"  Skipping {export_name}: File exists on GCS.")
            continue

        task_config = {
            'image': result_img,
            'description': f"gcp_{export_name}",
            'bucket': args.bucket,
            'fileNamePrefix': f"{args.prefix}/{export_name}",
            'region': region,
            'crs': crs,
            'crsTransform': crs_transform,
            'formatOptions': {'cloudOptimized': True, 'noData': 65535},
            'maxPixels': 1e13
        }
        
        if args.dry_run:
            print(f"  [Dry Run] Would submit export to {gcs_output_path}")
        else:
            task = ee.batch.Export.image.toCloudStorage(**task_config)
            task.start()
            print(f"  Task submitted: {task.id}")

if __name__ == "__main__":
    main()