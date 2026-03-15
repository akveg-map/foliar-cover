import ee
import time
import json

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

# Get the list of variables and their suffixes from the config
config_file = "03_data_topography/cog_pipeline/scaling_config.json"
with open(config_file, "r") as f:
    config = json.load(f)

# 1. Prepare Original Stack
orig_root = 'gs://akveg-data/aksdb_dem_covars_v20250422/'
scaled_root = 'gs://akveg-data/aksdb_dem_covars_v20250422_scaled_cog/cogs/'

def create_stack(is_scaled):
    images = []
    # Identify variables from config keys
    # Note: We need to handle the specific files like aspct_16, aspct_32 etc.
    # Our ALL_FILES list from earlier turns is best for this.
    ALL_FILES = [
      'aspct_16', 'aspct_32', 'aspct_4', 'ca_10', 'ca_10000', 'ci_16', 'ci_32', 'ci_4',
      'crosc_16', 'crosc_32', 'crosc_4', 'dah', 'devmeanelev_16', 'devmeanelev_32',
      'devmeanelev_4', 'dfa', 'diffmeanelev_16', 'diffmeanelev_32', 'diffmeanelev_4',
      'diffopen_2', 'diffopen_256', 'diffopen_32', 'dis', 'fel', 'gmrph_ms_30',
      'gmrph_ms_300', 'gmrph_r_30', 'gmrph_r_300', 'gmrph_r_3000', 'hs_st', 'longc_16',
      'longc_32', 'longc_4', 'maxc_16', 'maxc_32', 'maxc_4', 'mbi_0.001', 'mbi_0.01',
      'mbi_0.1', 'mca_10', 'mca_10000', 'minc_16', 'minc_32', 'minc_4', 'minelev_16',
      'minelev_32', 'minelev_4', 'morpfeat_16', 'morpfeat_32', 'morpfeat_4', 'msp',
      'nh', 'no_2', 'no_256', 'no_32', 'perctelev_16', 'perctelev_32', 'perctelev_4',
      'pisrdif_2023-01-22', 'pisrdif_2023-02-22', 'pisrdif_2023-03-22',
      'pisrdif_2023-04-22', 'pisrdif_2023-05-22', 'pisrdif_2023-06-22',
      'pisrdif_2023-12-22', 'pisrdir_2023-01-22', 'pisrdir_2023-02-22',
      'pisrdir_2023-03-22', 'pisrdir_2023-04-22', 'pisrdir_2023-05-22',
      'pisrdir_2023-06-22', 'pisrdir_2023-12-22', 'planc_16', 'planc_32', 'planc_4',
      'po_2', 'po_256', 'po_32', 'profc_16', 'profc_32', 'profc_4', 'relelev_16',
      'relelev_32', 'relelev_4', 'relmeanelev_16', 'relmeanelev_32', 'relmeanelev_4',
      'sl_16', 'sl_32', 'sl_4', 'slh', 'spi', 'stddevelev_16', 'stddevelev_32',
      'stddevelev_4', 'stdh', 'swi_10', 'swi_10000', 'tpi_32', 'tpi_4', 'tri_16',
      'tri_32', 'tri_4', 'tsc_16', 'tsc_32', 'tsc_4', 'twi', 'vlyd', 'vrm_16',
      'vrm_32', 'vrm_4'
    ]
    
    # Sort keys by length descending to match longest prefix first
    config_keys_sorted = sorted(config.keys(), key=len, reverse=True)
    
    for name in ALL_FILES:
        # Sanitize name for GEE band name (replace dots with 'p' for consistency)
        safe_band_name = name.replace(".", "p")
        
        if is_scaled:
            # Find the group to get the suffix
            suffix = ""
            for key in config_keys_sorted:
                if name.startswith(key):
                    suffix = config[key]["suffix"]
                    break
            path = f"{scaled_root}{name}{suffix}.tif"
            img = ee.Image.loadGeoTIFF(path).rename(safe_band_name)
        else:
            path = f"{orig_root}{name}.tif"
            img = ee.Image.loadGeoTIFF(path).rename(safe_band_name)
             
        images.append(img)
    
    # Add a control band that is valid everywhere to prevent sampleRegions from dropping points
    # where all topographic bands are masked (e.g. ocean).
    control_band = ee.Image(1).rename('control_band')
    images.append(control_band)
    
    # Add coordinate bands
    lonlat = ee.Image.pixelLonLat()
    images.append(lonlat)
    
    return ee.ImageCollection.fromImages(images).toBands()

print("Preparing stacks...")
orig_stack = create_stack(False)
scaled_stack = create_stack(True)

# Clean up band names (remove the 0_, 1_ prefix from toBands())
def clean_names(stack):
    b_names = stack.bandNames().map(lambda b: ee.String(b).replace('^[0-9]+_', ''))
    return stack.rename(b_names)

orig_stack = clean_names(orig_stack)
scaled_stack = clean_names(scaled_stack)

# 2. Sample Points
ak_bounds = ee.Geometry.Rectangle([-170.0, 52.0, -130.0, 71.0])
points = ee.FeatureCollection.randomPoints(region=ak_bounds, points=10000, seed=42)

def run_export(stack, description, fileName):
    # Using reduceRegions with first() instead of sampleRegions
    # This is more robust against NoData drops
    sampled = stack.reduceRegions(
        collection=points,
        reducer=ee.Reducer.first(),
        scale=10
    )
    
    # Add lat/lon explicitly as properties for the CSV
    # TODO (Optimization): Instead of mapping over the collection, just add ee.Image.pixelLonLat() 
    # to the image stack before sampling.
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
        fileNamePrefix=f'aksdb_dem_covars_v20250422_scaled_cog/qaqc/{fileName}',
        fileFormat='CSV'
    )
    task.start()
    print(f"Started {description}: {task.id}")

run_export(orig_stack, "final_qaqc_orig_10000", "assessment_orig_10000")
run_export(scaled_stack, "final_qaqc_scaled_10000", "assessment_scaled_10000")
