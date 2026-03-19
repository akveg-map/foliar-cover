#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import re
import datetime
import math
import subprocess
import json
import tempfile
import shutil

# Try importing fiona for shapefile parsing
try:
    import fiona
except ImportError:
    print("Error: fiona is required. Please install it (e.g., conda install -c conda-forge fiona).")
    sys.exit(1)

# Try importing earthengine-api
try:
    import ee
except ImportError:
    print("Error: earthengine-api is required. Please install it.")
    sys.exit(1)

def parse_maxar_date(filename):
    """
    Parses date from Maxar filename (e.g., 22AUG03213641-M1BS...).
    Returns datetime object and formatted string YYYYMMDD_HHMMSS.
    """
    match_full = re.search(r'(\d{14})', filename)
    if match_full:
        ts_str = match_full.group(1)
        return datetime.datetime.strptime(ts_str, "%Y%m%d%H%M%S"), f"{ts_str[:8]}_{ts_str[8:]}"
        
    match_new = re.search(r'(\d{8})_(\d{6})', filename)
    if match_new:
        ts_str = match_new.group(1) + match_new.group(2)
        return datetime.datetime.strptime(ts_str, "%Y%m%d%H%M%S"), f"{match_new.group(1)}_{match_new.group(2)}"

    match = re.search(r'(\d{2})([A-Z]{3})(\d{2})(\d{2})(\d{2})(\d{2})', filename, re.IGNORECASE)
    if not match:
        return None, None
    
    yy, mmm, dd, hh, mm, ss = match.groups()
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

def get_footprint_from_shp(filepath):
    """
    Returns the footprint of the image as an ee.Geometry.Polygon 
    by reading the bounding box of a shapefile.
    """
    with fiona.open(filepath) as src:
        bounds = src.bounds
        geom = {
            'type': 'Polygon',
            'coordinates': [[
                [bounds[0], bounds[1]],
                [bounds[0], bounds[3]],
                [bounds[2], bounds[3]],
                [bounds[2], bounds[1]],
                [bounds[0], bounds[1]]
            ]]
        }
        # Maxar PIXEL_SHAPE is typically in EPSG:4326.
        return ee.Geometry.Polygon(geom['coordinates'])

def get_ccdc_prediction(target_date_dt, region):
    ee_date = ee.Date(target_date_dt)
    fractional_year = ee_date.get('year').add(ee_date.getFraction('year'))
    
    ccdc = ee.ImageCollection([
        ee.ImageCollection("projects/CCDC/measures/v1").mosaic(),
        ee.ImageCollection("projects/CCDC/measures/v1_overlap").mosaic()
    ]).mosaic()
    
    bands = ['BLUE', 'GREEN', 'RED', 'NIR']
    
    tStart = ccdc.select('tStart')
    tEnd = ccdc.select('tEnd')
    
    strict_match = tStart.lte(fractional_year).And(tEnd.gt(fractional_year))
    
    max_tEnd_array = tEnd.arrayReduce(ee.Reducer.max(), [0])
    max_tEnd = max_tEnd_array.arrayGet([0])
    
    is_last_segment = tEnd.eq(max_tEnd)
    has_strict_match_array = strict_match.arrayReduce(ee.Reducer.max(), [0])
    has_strict_match = has_strict_match_array.arrayGet([0])
    should_extrapolate = has_strict_match.Not().And(max_tEnd.lte(fractional_year))
    
    segment_mask = strict_match.add(is_last_segment.multiply(should_extrapolate))
    has_segment = segment_mask.arrayReduce(ee.Reducer.max(), [0]).arrayFlatten([['has_segment']])
    
    seg_count = segment_mask.arrayLength(0)
    shape_2d = ee.Image.cat([seg_count, ee.Image(1)]).toArray()
    segment_mask_2d = segment_mask.arrayReshape(shape_2d, 2)
    
    def predict_band(band_name):
        coefs = ccdc.select(band_name + '_coefs')
        valid_coefs = coefs.arrayMask(segment_mask_2d)
        final_coefs = valid_coefs.arrayProject([1]) 
        
        t = fractional_year
        omega = 2.0 * math.pi
        
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
        
        predicted = final_coefs.multiply(terms).arrayReduce(ee.Reducer.sum(), [0])
        return predicted.arrayFlatten([[band_name.lower() + '_ccdc']])

    predicted_img = ee.Image.cat([predict_band(b) for b in bands])
    predicted_img = predicted_img.updateMask(has_segment)
    
    water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('occurrence').rename('water_occurrence').unmask(0)
    spectral_scaled = predicted_img.multiply(10000).clamp(0, 16000).uint16().unmask(65535)
    
    spectral_scaled = spectral_scaled.select(
        ['blue_ccdc', 'green_ccdc', 'red_ccdc', 'nir_ccdc'],
        ['blue', 'green', 'red', 'nir']
    )
    
    water = water.rename('water_occurrence')
    
    days_extrapolated = ee.Image(fractional_year).subtract(max_tEnd).multiply(365.25)
    days_extrapolated = days_extrapolated.updateMask(has_segment).max(0).uint16().unmask(0).rename('days_extrapolated')
    
    final_img = spectral_scaled.addBands(water.uint16()).addBands(days_extrapolated)
    return final_img.clip(region)

def check_gcs_exists(gcs_path):
    try:
        subprocess.check_call(["gsutil", "ls", gcs_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def process_order(order_path, args):
    print(f"\\nProcessing order: {order_path}")
    
    shapefiles_local = []
    temp_dir = None
    
    if order_path.startswith("gs://"):
        # Download shapefiles to a temp directory
        temp_dir = tempfile.mkdtemp(prefix="ccdc_prestage_")
        print(f"  Downloading shapefiles to temp dir: {temp_dir}")
        try:
            # We want PIXEL_SHAPE files. We'll download .shp, .shx, .dbf, .prj
            cmd = f"gsutil -m cp {os.path.join(order_path, 'GIS_FILES', '*PIXEL_SHAPE.*')} {temp_dir}/"
            subprocess.check_call(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            shapefiles_local = glob.glob(os.path.join(temp_dir, "*PIXEL_SHAPE.shp"))
        except subprocess.CalledProcessError as e:
            print(f"  Failed to download shapefiles from {order_path}: {e}")
            if temp_dir:
                shutil.rmtree(temp_dir)
            return
    else:
        # Local path
        gis_dir = os.path.join(order_path, "GIS_FILES")
        shapefiles_local = glob.glob(os.path.join(gis_dir, "*PIXEL_SHAPE.shp"))

    if not shapefiles_local:
        print(f"  No PIXEL_SHAPE.shp found for {order_path}")
        if temp_dir:
            shutil.rmtree(temp_dir)
        return

    # Group shapefiles by Product and Order ID (ignoring timestamp seconds and Part number)
    # e.g., 22JUL12214724-M1BS-050291279010_01_P001_PIXEL_SHAPE.shp
    groups = {}
    for shp in shapefiles_local:
        filename = os.path.basename(shp)
        match = re.search(r'-(M1BS|P1BS|M2AS|P2AS)-([A-Z0-9_]+)_P\d{3}', filename)
        if match:
            product, order_id = match.groups()
            key = (product, order_id)
            if key not in groups:
                groups[key] = []
            groups[key].append(shp)
        else:
            # Fallback if pattern doesn't match
            groups[filename] = [shp]

    processed_dates = set()

    for key, shp_list in groups.items():
        # Sort to ensure P001 comes first
        shp_list.sort()
        
        first_shp = shp_list[0]
        first_filename = os.path.basename(first_shp)
        
        # Parse Date
        dt, date_str = parse_maxar_date(first_filename)
        if not dt:
            print(f"  Skipping group {key}: Could not parse date from {first_filename}.")
            continue
        
        if date_str in processed_dates:
            continue
        processed_dates.add(date_str)
            
        export_name = f"ccdc_{date_str}"
        print(f"  Exporting Group {key} ({len(shp_list)} parts) -> {export_name} ({dt})")
        
        # Merge coordinates from all parts into a MultiPolygon
        multi_coords = []
        for shp_path in shp_list:
            geom = get_footprint_from_shp(shp_path)
            # geom is ee.Geometry.Polygon; get coordinates
            multi_coords.extend(geom.getInfo()['coordinates'])
        
        region = ee.Geometry.MultiPolygon(multi_coords)
        
        result_img = get_ccdc_prediction(dt, region)
        
        crs_transform = [30.0, 0.0, 15.0, 0.0, -30.0, 15.0]
        crs = 'EPSG:3338'
        
        gcs_output_path = f"gs://{args.bucket}/{args.prefix}/{export_name}.tif"
        print(f"    Output GCS Path: {gcs_output_path}")

        if not args.overwrite and check_gcs_exists(gcs_output_path):
            print(f"    Skipping {export_name}: File exists on GCS.")
            continue

        task_config = {
            'image': result_img,
            'description': f"gcp_prestage_{export_name}",
            'bucket': args.bucket,
            'fileNamePrefix': f"{args.prefix}/{export_name}",
            'region': region,
            'crs': crs,
            'crsTransform': crs_transform,
            'formatOptions': {'cloudOptimized': True, 'noData': 65535},
            'maxPixels': 1e13
        }
        
        if args.dry_run:
            print(f"    [Dry Run] Would submit export to {gcs_output_path}")
        else:
            task = ee.batch.Export.image.toCloudStorage(**task_config)
            task.start()
            print(f"    Task submitted: {task.id}")
            
    if temp_dir:
        shutil.rmtree(temp_dir)

def main():
    parser = argparse.ArgumentParser(description="Pre-stage CCDC Synthetic Landsat Imagery using Order Shapefiles")
    parser.add_argument("--input", required=True, nargs='+', help="Order directory/directories (GCS or local)")
    parser.add_argument("--bucket", default="akveg-data", help="GCS Bucket for export")
    parser.add_argument("--prefix", default="vhr/landsat_ccdc_sr_prestage", help="GCS Prefix for export (separate from pipeline)")
    parser.add_argument("--project", help="Google Cloud Project for EE")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing GCS files")
    parser.add_argument("--dry-run", action="store_true", help="Print tasks without submitting")
    args = parser.parse_args()

    try:
        ee.Initialize(project=args.project)
        print(f"Earth Engine initialized.")
    except Exception as e:
        print(f"Failed to initialize Earth Engine: {e}")
        print("Try running 'earthengine authenticate' first.")
        sys.exit(1)

    for order_path in args.input:
        process_order(order_path, args)

if __name__ == "__main__":
    main()
