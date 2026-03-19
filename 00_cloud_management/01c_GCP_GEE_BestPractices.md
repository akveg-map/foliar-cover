# Google Cloud Platform (GCP) & Earth Engine (GEE) Best Practices

This document outlines mandatory practices for all scripts interacting with GCP and Google Earth Engine within this project. Adhering to these guidelines ensures proper billing, avoids runaway costs, and maximizes computational performance.

## 1. Explicit Project Initialization & Billing

Never rely on the local environment's default credentials to infer the correct billing project. The default project might be a personal account or an outdated configuration, leading to incorrect billing or permission errors.

*   **Rule:** Always define a `PROJECT_ID` variable and **explicitly pass it** to initialization functions.
*   **Earth Engine (Python):** `ee.Initialize(project=PROJECT_ID)`
*   **Google Cloud Clients:** `client = storage.Client(project=PROJECT_ID)`

## 2. Reading Data: Choosing the Right GEE Access Method

Earth Engine offers three ways to access Cloud-Optimized GeoTIFFs (COGs) stored in GCS. Choosing the wrong one for heavy workloads can lead to massive I/O penalties and runaway costs.

### A. Native GEE Assets (Best Performance)
Formal **ingestion** copies data into Earth Engine's internal, highly-distributed format. This provides the lowest latency and is recommended for production model training and global-scale analytics.
*   **Method:** `earthengine upload image ...`

### B. COG-backed Assets / ImageCollections (Good Middle Ground)
You can register GCS-hosted COGs as Earth Engine assets without a full copy. This is significantly more efficient than on-the-fly loading because Earth Engine caches metadata and optimizes tile requests.
*   **Method:** `ee.data.createAsset({'type': 'IMAGE', 'gcs_location': ...})`

### C. On-the-Fly (OTF) Loading (The "Trap")
Using `ee.Image.loadGeoTIFF('gs://...')` reads data directly from GCS with no registration. 

*   **Rule (Be Proactive):** You **must evaluate** the intensity of your workload before using this pattern. Do not naively run sampling or analytics scripts with OTF loading just because it is convenient to code.
*   **The Trap:** For heavy workloads (e.g., extracting 10,000+ points across a large stack), OTF loading is a major bottleneck. Workers spend most of their time idle waiting for GCS network requests, leading to massive, unnecessary EECU-second billing.
*   **When to use:** Only for quick visualizations or very small subsets (e.g., < 100 points). For anything larger, proactively register the data as a COG-backed asset (Method B).

## 3. Google Cloud Batch: Massive Raster Processing

### Resiliency and Cost
*   **Provisioning Model:** Always consider **SPOT** instances for substantial cost savings (60-90%).
    *   **Caveat:** SPOT is best suited for jobs that are **relatively quick** (under a few hours) or can be **resumed** from where they left off.
    *   **Intermediate Work:** For long-running jobs using SPOT, the processing logic must periodically save intermediate state/data to persistent storage (e.g., GCS) to avoid losing all progress upon preemption.
*   **Automatic Retries:** Set `maxRetryCount` to at least **3** to handle SPOT preemption. Google Cloud Batch will automatically restart the task on a new instance.
*   **Disk Capacity:** For large raster processing (source files > 50GB), ensure the boot disk is at least **500 GB**.

### Resource Allocation
*   **CPU/RAM:** Aim for at least **4GB of RAM per vCPU** for block-based raster operations. `n2-standard-16` (16 vCPU / 64GB RAM) is a recommended baseline for stable performance.

### GDAL & Parallelism
*   **Parallel Window Processing:** For massive rasters, consider using `rasterio.block_windows()` and a `ProcessPoolExecutor` to process small windows in parallel. This can optimize memory usage and throughput.
*   **Writing Congestion:** When writing results of parallel calculations to a single large GeoTIFF, unthrottled submission of futures may lead to memory pressure as blocks queue in RAM. Throttling the queue (e.g., `num_workers * 4`) is an approach being evaluated to stabilize memory footprint during the write phase.
*   **GDAL Cache:** On high-RAM instances, set `--config GDAL_CACHEMAX` (e.g., 16384) to balance throughput while leaving RAM for the system's write-back cache.

### COG Standards
To maintain consistency across the AKVEG stack, follow these Cloud Optimized GeoTIFF (COG) guidelines:
*   **Tiling:** Use `BLOCKXSIZE=512`, `BLOCKYSIZE=512` as the project standard. For extremely high-resolution statewide datasets (e.g., 5m IFSAR), consider `1024` to optimize spatial index performance.
*   **Compression:** `COMPRESS=DEFLATE` is preferred for storage efficiency.
*   **Predictor:** Use `PREDICTOR=2` for **Integer** (`Int16`, `Int32`) data. **Never** use Predictor 2 for Float32 data.
*   **Overviews:** Generate a **full pyramid depth**. Use `RESAMPLING=AVERAGE` for continuous variables and `RESAMPLING=MODE` for categorical variables.

## 4. General Cost Management and Monitoring

*   **Watch for Bottlenecks:** If an Earth Engine task takes hours instead of minutes and accumulates massive EECU-seconds, **cancel it**. It is likely hitting an I/O bottleneck.
*   **Batch Processing:** For massive raster operations that do not strictly require GEE APIs (e.g., mathematical scaling), use Google Cloud Batch or local parallelization.

## 5. Troubleshooting & Smart Retries

When running massive parallel workloads on Google Cloud Batch, proactive error handling and monitoring are essential to avoid runaway costs.

### Avoiding Chronological Confusion
*   **Verify Creation Time:** When monitoring jobs via CLI, always cross-reference the `createTime` with the current system clock (`date`). 
*   **Use Descriptive Suffixes:** Include a date and precise time in the job name (e.g., `-[YYYYMMDD-HHMMSS]`). 
*   **Filter Aggressively:** Use `--filter="name ~ [job-timestamp]"` to isolate the current batch and avoid noise from legacy jobs.

### Robust Job Monitoring
*   **Task-Level Detail:** If a job seems stuck or you suspect failures, inspect the specific task history using:
    `gcloud batch tasks list --job [JOB_URI] --format="json"`
*   **OOM Signatures:** Note that an `exitCode 137` accompanied by a `Killed` message in the `batch_task_logs` is typically indicative of an Out of Memory error.

### Smart Lifecycle Policies (Preemption-Only Retry)
*   **The Rule:** Avoid using a blanket `maxRetryCount` without a `lifecyclePolicy` for deterministic application errors.
*   **Spot Preemption:** Google Cloud Batch reserves `exitCode: 50001` for Spot preemption. 
*   **The Configuration:** You can configure the job to *only* retry on `50001`. This ensures that if the node is taken away, the job restarts, but if your Python code crashes (e.g., OOM), it fails immediately for diagnosis.

### I/O and Memory Observations
*   **Python vs. CLI Tools:** For downloading very large files (>50GB), native CLI tools like `gsutil cp` or `gcloud storage cp` via a subprocess are currently being evaluated as potentially more stable streaming methods than the Python `google-cloud-storage` client library.
