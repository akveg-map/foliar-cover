# Workflow Status: Topography COG Scaling (Unified Int32)

## Current Objective
Executing the final high-integrity topography run using the **Unified Int32** architecture. This run eliminates clamping, pushes precision < 0.11% for all continuous bands, and prunes redundant variables.

## Current State
- **High-Integrity Architecture:** All 103 continuous variables moved to **Int32** with optimized scaling factors (1, 10k, 100k, 10M).
- **Pruning Complete:** 6 redundant variables (`ca_10000`, `relmeanelev_*`, `no_2`, `diffopen_2`) removed from the stack to ensure high information density. 
- **Tracking:** Pruned variables are documented in **`dropped_covars.csv`**.
- **Distilled Pipeline:** The 6 core scripts (`01_` to `06_`) have been updated to support `Int32`, unique job IDs, and dynamic configuration lookup.
- **Verification Run:** Initial batch of 9 representative variables currently running in `aksdb_dem_covars_v20250422_scaled_i32/`.
- **Reports:** Branded Typst and HTML reports will be updated once the full 105-variable run is complete.

## Next Immediate Sub-tasks
1.  **Monitor**: Verify completion of the 9 initial `Int32` jobs.
2.  **QA/QC**: Run `06_comparative_analysis.py` on the test results.
3.  **Full Submission**: Launch the remaining 96 variables.
4.  **Reporting**: Update metrics and re-render final PDF/HTML.

## Resume Prompt
> Read `03_data_topography/cog_pipeline/workflow_status.md`.
>
> **Current State:** Transitioning to **Unified Int32** architecture for elite precision and zero clamping. 6 redundant variables pruned. 9 initial verification jobs are currently running.
> **Next Task:** QA/QC the verification jobs and then submit the full 105-variable stack.
