Note: Covariate definitions and prefixes in this workflow were sourced from: https://github.com/orgs/alaska-soil-data-bank/projects/3

# Terrain Covariates COG Conversion Workflow

This document tracks the status, decisions, and technical strategies for converting 111 terrain covariates to optimized Cloud Optimized GeoTIFFs (COGs).

## Current Status (2026-03-12 11:20 AKDT)
- **Production Complete:** All 111 terrain covariates successfully scaled, clamped, and converted to optimized COGs.
- **Location:** `gs://akveg-data/aksdb_dem_covars_v20250422_scaled_cog/cogs/`
- **Total Variables:** 111
- **Optimization:** Final 11 large files completed using `n2-highmem-16` VMs to avoid OOM issues.
- **QAQC in Progress:** Conducting NoData and anomaly assessment using GEE random point sampling (comparing scaled results vs original baseline).

## Technical Strategy

### 1. Statistics and Scaling
- **Target:** Convert continuous data to `Int16` to reduce size and improve performance.
- **Scale Factors:** Power-of-10 multipliers (10, 100, 1000, 10000) chosen to preserve maximum precision.
- **Clamping:** Safe range of `[-32000, 32000]` to avoid collision with NoData (`-32768`).
- **Resampling:** `AVERAGE` for continuous, `MODE` for categorical (Byte).

### 2. Processing Pipeline (The "Traditional" approach)
- **Step 1:** `gdal_calc.py` scales/clamps floating-point data to a local `Int16` GeoTIFF on the 500GB balanced PD boot disk.
- **Step 2:** `gdal_translate` converts the local file to a final COG on GCS with deep pyramids (9-10 levels).

### 3. Optimized Parallel Pipeline (In Development)
- **Logic:** Use a custom Python script with `rasterio` and `ProcessPoolExecutor`.
- **Concurrency:** Read/Process blocks in parallel across all available vCPUs.
- **Goal:** Reduce the Step 1 duration by 4x to 8x on `n2-standard-16` instances.

## GCP Batch Tips
- Use `python:3.10-slim` for a stable environment.
- Explicitly install `libgdal-dev` and `gdal-bin`.
- Use `google-cloud-storage` Python library instead of `gsutil` for more reliable GCS uploads within the container.
- Always use **SPOT** instances for significant cost savings.
