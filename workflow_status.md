# Workflow Status - Navy North Slope CHM Production

## Current State (2026-03-21 17:30 UTC)
The Meta DINOv3 Canopy Height Model (CHM) pipeline is **fully operational and verified**. The infrastructure has been stabilized under the **Verified V5.0 Architecture**, and production is currently scaling across the Navy North Slope study area.

### **Recent Accomplishments**
- **Infrastructure:** Verified V5.0 Unified Environment (all libraries in `/opt/conda`).
- **Edge Fix:** Implemented **V3.7 "True Source Masking"** using `src.read_masks()`, eliminating edge garbage and tightening cleanup with 5px erosion.
- **Security:** Successfully mapped `HF_TOKEN` from Secret Manager to the production workflow.
- **Behemoth Support:** Increased default disk size to **500GB** and implemented **Standard (non-Spot)** overrides for strips >10GB to ensure robustness.
- **Validation:** Smallest Navy strip (3.6GB) completed successfully with clean edges.

### **Infrastructure Standard (V5.0)**
- **Image:** `Dockerfile.gpu` (V5.0) - Unifies science libraries in `/opt/conda`. No environment collisions.
- **I/O:** GCS FUSE mount at `/mnt/disks/akveg`. 
- **Runner:** `run_chm_job.sh` - Decoupled shim pattern. Pulls scripts from GCS at runtime for instant iteration.
- **Resiliency:** 500GB default scratch disk; Standard instances for long-running behemoth strips.

### **Production Live Monitor**
- **Strip 20240710 (3.6 GB):** **SUCCESS** (Finalized with clean edges).
- **Strip 20220803 (5.8 GB):** **RUNNING** (Job `...112971`, ~35% complete).
- **Strip 20200714 (21.6 GB):** **RUNNING** (Job `...112973`, ~15% complete).

## **Next Steps**
1.  **Navy Finalization:** Monitor the remaining two Navy strips to completion.
2.  **Science Audit:** Review output CHM in GEE using `navy_chm_viz.js`.
3.  **Nome Beaver Expansion:** Relaunch CHM track for Nome Beaver study area.

## **Resume Prompt**
> "Resume Navy North Slope CHM production. Check status of Jobs ...112971 and ...112973 using the logging-based protocol (Three-Point Verification). Once Navy is complete, proceed to Nome Beaver expansion."
