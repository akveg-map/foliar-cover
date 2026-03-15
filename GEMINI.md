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

## 2. Project Hygiene & State Persistence
*   **`workflow_status.md`**: Keep this file in your project root or year folder. It is the "source of truth" for the current session.
*   **`plans/` folder**: Archive all approved design documents and implementation plans here.
*   **Audit Artifacts**: Frequently delete or move intermediate images, logs, and temporary test files to reduce noise in file searches.
