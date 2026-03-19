import ee
import time
import json
import pandas as pd

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

# 1. Prepare Stacks
print("Preparing stacks...")
raw_coll = ee.ImageCollection(f"projects/{PROJECT_ID}/assets/covariates/aksdb/aksdb_topo_v20250422_raw")
scaled_coll = ee.ImageCollection(f"projects/{PROJECT_ID}/assets/covariates/aksdb/aksdb_topo_v20250422_scaled_i32")

def clean_names(stack):
    b_names = stack.bandNames()
    clean_b_names = b_names.map(lambda b: ee.String(b).replace('^[0-9]+_', ''))
    return stack.rename(clean_b_names)

orig_stack = clean_names(raw_coll.toBands())
scaled_stack = clean_names(scaled_coll.toBands())

# Add coordinate bands to orig for reference
lonlat = ee.Image.pixelLonLat()
orig_stack = orig_stack.addBands(lonlat)

# 2. Sample Points Configuration (Native EPSG:3338 Bounding Box)
ak_bounds_3338 = ee.Geometry.Rectangle(
    coords=[-2175592.6, 405266.0, 1550577.3, 2384026.0],
    proj='EPSG:3338',
    geodesic=False
)

# FULL RUN: 35,000 points, fresh seed
NUM_POINTS = 35000  
print(f"Generating {NUM_POINTS} random points across the native study area (EPSG:3338)...")
points = ee.FeatureCollection.randomPoints(region=ak_bounds_3338, points=NUM_POINTS, seed=123)

def run_export(stack, description, fileName):
    sampled = stack.reduceRegions(
        collection=points,
        reducer=ee.Reducer.first(),
        scale=10
    )
    
    def add_coords(f):
        coords = f.geometry().coordinates()
        return f.set({
            'longitude': coords.get(0),
            'latitude': coords.get(1)
        })
    
    sampled = sampled.map(add_coords)

    task = ee.batch.Export.table.toCloudStorage(
        collection=sampled,
        description=description,
        bucket='akveg-data',
        fileNamePrefix=f'aksdb_dem_covars_v20250422_scaled_i32/qaqc/{fileName}',
        fileFormat='CSV'
    )
    task.start()
    print(f"Started {description}: {task.id}")
    return task

if __name__ == "__main__":
    # orig_task = run_export(orig_stack, "final_full_orig_35000", "assessment_orig_35000")
    scaled_task = run_export(scaled_stack, "final_full_scaled_35000", "assessment_scaled_35000")
    print(f"Scaled Task ID: {scaled_task.id}")
