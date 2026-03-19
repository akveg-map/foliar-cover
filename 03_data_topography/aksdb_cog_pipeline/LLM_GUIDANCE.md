Note: Covariate definitions and prefixes in this workflow were sourced from: https://github.com/orgs/alaska-soil-data-bank/projects/3

# LLM Guidance: COG Scaling and Conversion Pipeline

This document distills crucial lessons learned during the topographic covariate scaling and COG conversion process. Future LLM agents should review these notes before attempting similar large-scale raster transformations.

## 1. NoData Integrity and "Phantom Data"
Always explicitly check for and mask hardcoded background values in addition to the tagged `NoData` value.
*   **The Trap:** In this dataset, raw rasters (like `dfa.tif`) used `-99999.0` for ocean/background pixels, but the GeoTIFF metadata tagged `-3.4e+38` as the NoData value.
*   **The Result:** If you only mask `src.nodata`, Python will treat the `-99999.0` background pixels as valid data, scale them (e.g., `-9999.9`), and clamp them into the valid data range, creating "phantom data" where there should be masks.
*   **The Fix:** Explicitly mask extreme negative values alongside the metadata tag: `mask = (arr > -99990) & (~np.isnan(arr)) & (arr != src.nodata)`.

## 2. Dynamic Range Constraints (Float32 vs. Int16)
Do not aggressively force high-dynamic-range indices into `Int16` without careful outlier analysis.
*   **The Trap:** Variables like Catchment Area (`ca`) and Modified Catchment Area (`mca`) span 8 orders of magnitude (1 to 800 million).
*   **The Result:** Attempting to scale `mca` to fit `Int16` (max 32,767) resulted in over 7% of the landscape being clamped, destroying detail in the entire middle and lower reaches of river systems.
*   **The Fix:** Use a 10,000-point random sample to check the 99.9% percentile. If the 99.9% range exceeds the target integer limits after scaling, the variable **must** remain `Float32` (Scale 1.0).

## 3. GEE Sampling Traps
When using Google Earth Engine to sample pixels for QA/QC, be wary of silent point dropping.
*   **The Trap:** Using `stack.sampleRegions()` will silently drop any point that has a NoData value in *any* of the bands in the stack. 
*   **The Result:** A request for 10,000 points might return only 200 rows if one band (like Distance to Coast) is primarily NoData, making it impossible to verify the masking logic.
*   **The Fix:** Use `stack.reduceRegions(reducer=ee.Reducer.first())`. This method preserves the point geometry and returns `NaN` for masked pixels, allowing for true 1:1 validation of the NoData tags.

## 4. GCP Batch Memory Tuning
Scale down concurrency relative to VM RAM when processing massive files.
*   **The Trap:** Running 12 concurrent `rasterio` workers while keeping a 48GB GDAL cache on a 64GB RAM machine.
*   **The Result:** Processing 100GB+ files (like Catchment Area) resulted in Google Cloud Batch tasks failing with `Exit Code 137` (Out Of Memory).
*   **The Fix:** Lower `num_workers` (e.g., to 8) and limit `GDAL_CACHEMAX` (e.g., to `32768`) to ensure sufficient overhead for the OS and Python runtime.