# Workflow Status: Topography COG Scaling (Finalized)

## Current Objective
Topography scaling, verification, and Earth Engine registration are 100% complete. The workflow has been distilled into a maintainable sequence of 6 core scripts.

## Current State
- **Distilled Pipeline:** The `cog_pipeline/` folder is now organized into a clear sequence:
    1. `01_extract_raw_stats.py`
    2. `02_production_worker.py` (Core scaling/clamping logic)
    3. `03_submit_production.py` (Batch orchestration)
    4. `04_register_gee_assets.py` (Asset registration)
    5. `05_gee_sample_extraction.py` (10k point sampling)
    6. `06_comparative_analysis.py` (Final QA/QC report generation)
- **Metadata Vetted:** `metadata_crosswalk.csv` is the source of truth for all 111 variables.
- **Fluvial Healing:** Pipeline correctly masks negative background artifacts in `dfa` and `spi`.
- **GEE Assets Registered:** Exactly 111 assets in both `aksdb_topo_v20250422_raw` and `_scaled`.
- **Final Reports:** Rendered via **Typst** (`topography_cog_scaling_report.pdf`) with full metrics and GEE asset paths listed.
- **Legacy Archived:** All one-off debugging and trial scripts moved to `03_data_topography/archive/`.

## Next Immediate Sub-tasks
1.  **Handoff:** Topography is finished. Transition to the next covariate set (e.g., Floodplains, Hydrography) or model training.

## Resume Prompt
> Read `03_data_topography/cog_pipeline/workflow_status.md`.
>
> **Current State:** Topography is 100% complete and verified. The pipeline is distilled to 6 scripts.
> **Next Task:** Await user instruction for the next major project milestone.
