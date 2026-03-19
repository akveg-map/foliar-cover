Note: Covariate definitions and prefixes in this workflow were sourced from: https://github.com/orgs/alaska-soil-data-bank/projects/3

# Terrain Covariates COG Conversion Workflow

This document tracks the status, decisions, and technical strategies for converting 111 terrain covariates to optimized Cloud Optimized GeoTIFFs (COGs).

## Current Status (2026-03-14 19:30 AKDT)
- **High-Integrity Transition:** All continuous variables migrated from `Int16` to **`Int32`** to achieve elite precision and zero clamping.
- **Variable Count:** Reduced from 111 to **105 unique variables**.
- **Pruning:** 6 redundant variables (`ca_10000`, `relmeanelev_*`, `no_2`, `diffopen_2`) moved to `dropped_covars.csv`.
- **Location:** `gs://akveg-data/aksdb_dem_covars_v20250422_scaled_i32/cogs/`

## Technical Strategy

### 1. Scaling Architecture (Unified Int32)
- **Target:** Convert all continuous data to **`Int32`**.
- **Why Int32?**: 
    - **Zero Clamping**: Eliminates the need for safe range clamping (`[-32000, 32000]`).
    - **Elite Precision**: Allows for massive scale factors (e.g., 10,000,000 for Curvatures) to push precision error < 0.1%.
    - **Compression**: Integer bit patterns compress better than standard `Float32`.
- **Scale Factors:** Power-of-10 multipliers (1, 10k, 100k, 10M) standardized across groups.
- **NoData Standard**: `-2147483648` (Int32 min).

### 2. Processing Pipeline (Parallel Local-Disk)
- **Engine:** Custom Python script using `rasterio` and `ProcessPoolExecutor`.
- **I/O Strategy:** Download raw source from GCS to local `/tmp` disk *once*. Perform all processing against local file to eliminate network latency.
- **COG Standards:** `DEFLATE` compression, `PREDICTOR=2` (Integers only), 512x512 tiling, Average/Mode resampling across 9 overview levels.

## GCP Batch Tips
- Use `python:3.10-slim` for a stable environment.
- Explicitly install `libgdal-dev` and `gdal-bin`.
- Use `google-cloud-storage` Python library instead of `gsutil` for more reliable GCS uploads within the container.
- Always use **SPOT** instances for significant cost savings.
