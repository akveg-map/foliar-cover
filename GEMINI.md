# Environment & Authentication Setup

## Mandatory Environment
All production scripts should be run within the `akveg` conda environment:
```bash
conda activate akveg
```

## Authentication Steps
The following two steps must be completed to enable full GCS and GEE access. This is especially important for GDAL/rasterio to read from `/vsigs/` paths.

### 1. Earth Engine Auth
Authenticates the `earthengine` CLI and `ee` Python module.
```bash
earthengine authenticate
```

### 2. Google Cloud ADC (Application Default Credentials)
**Required for GDAL, rasterio, and gsutil.** This allows tools to find credentials for GCS access.
```bash
gcloud auth application-default login
```

### 3. Environment Variables for GDAL
If GDAL/rasterio still fails to access `/vsigs/` paths, ensure these are set:
```bash
export GS_PROJECT_ID=akveg-map
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json
```

# Gemini CLI: Senior Engineer Workflow & Context Management

## Rendering & Documentation
- **Prefer Typst:** Always use Typst for PDF rendering in this project. Do not use LaTeX.
- **Quarto:** When rendering Quarto documents to PDF, ensure `pdf: { to: typst }` is set in the YAML header to avoid LaTeX defaults.

## 1. The "Save & Restart" Strategy (Context Management)
The Gemini CLI context window is a finite resource. As a session grows, the agent becomes slower and more prone to errors. Use the `/clear` command to reset the context while maintaining progress.

### The Workflow:
1.  **State Save:** Before a session gets too long, ask: *"Save the state and I'll restart."*
2.  **The Agent's Job:** I will update a `workflow_status.md` file with specific file paths, line numbers, and the next immediate sub-task.
3.  **Clear Context:** Type `/clear` to start a fresh, high-performance session.
4.  **The Resume Prompt:** Paste the provided "Resume Prompt" to "re-load" the agent instantly.

## 3. Infrastructure Engineering Standards (GCP Batch, GEE, etc.)

### 📋 Mandatory Documentation Discovery
Before initiating any new compute workflow, the agent **MUST** perform a recursive search for governing documentation.
*   **Protocol:** Search parent and current directories for `README.md`, `*BestPractices*.md`, or `*Standards*.md`.
*   **Priority:** Local project documentation takes absolute precedence over general technical knowledge (e.g., specific Spot retry codes or COG compression settings).

### 🛠️ Incremental Infrastructure Deployment
Follow a strict **"Connectivity -> Integrity -> Optimization"** path for all distributed compute tasks:
*   **Step 1 (Connectivity):** Verify basic GCS I/O and hardware access with a minimal "Hello World" run. Use standard, off-the-shelf environments (e.g., Google DLVMs) first. **Do not attempt custom container builds unless standard images are verified as insufficient.**
*   **Step 2 (Integrity):** Verify functional/mathematical correctness on a limited sample (e.g., `--limit-tiles 10`) before running a full strip.
*   **Step 3 (Optimization):** Layer on compute-saving features (blending, memmapping, parallelization) only *after* Step 2 is confirmed successful.
*   **Decoupling:** Favor pulling runner and inference scripts from GCS at runtime rather than baking logic into containers to enable near-instant iteration.

### 🏷️ Descriptive Naming & Tracking
All distributed jobs (GCP Batch, Cloud Workflows, GEE Tasks) **MUST** utilize descriptive IDs.
*   **Format:** Include the pipeline name, target site/strip, and a timestamp (e.g., `vhr-refl-navy-010-1774045198`). 
*   **Restriction:** Generic auto-assigned UUIDs (e.g., `job-bf4d88ff`) are prohibited for production-track runs.

### ⚡ Preemption & Resiliency Standards
The use of Spot/Preemptible instances is a project standard but requires a **Proactive Resiliency Assessment**:
*   **Resumability:** Confirm the task is partitioned or checkpointed. Default to Standard instances for initial verification if the task is long and atomic.
*   **Retry Compliance:** All Spot configurations **MUST** implement the project-standard retry policy (specifically retrying `exitCode 50001`) as documented in `01c_GCP_GEE_BestPractices.md`.
*   **I/O Robustness:** Favor `gcloud storage` over legacy `gsutil` for all scripted I/O to avoid legacy Python dependency conflicts in specialized environments.
