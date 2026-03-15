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
Using `ee.Image.loadGeoTIFF('gs://...')` reads data directly from GCS with no registration. While convenient for quick visualization, it is a **trap for heavy workloads** (e.g., extracting 10,000 random points). Workers spend most of their time idle waiting for GCS network requests, leading to massive EECU-second billing.

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
*   **Window Processing:** For massive rasters, consider using `rasterio.block_windows()` and a `ProcessPoolExecutor` to process small windows in parallel. This can optimize memory usage and throughput.
*   **GDAL Cache:** On high-RAM instances, set `--config GDAL_CACHEMAX` (e.g., 32768) to maximize throughput during COG conversion.

### COG Standards
To maintain consistency across the AKVEG stack, follow these Cloud Optimized GeoTIFF (COG) guidelines:
*   **Tiling:** Use `BLOCKXSIZE=512`, `BLOCKYSIZE=512` as the project standard. For extremely high-resolution statewide datasets (e.g., 5m IFSAR), consider `1024` to optimize spatial index performance.
*   **Compression:** `COMPRESS=DEFLATE` is preferred for storage efficiency.
*   **Predictor:** Use `PREDICTOR=2` for **Integer** (`Int16`, `Int32`) data. **Never** use Predictor 2 for Float32 data.
*   **Overviews:** Generate a **full pyramid depth**. Use `RESAMPLING=AVERAGE` for continuous variables and `RESAMPLING=MODE` for categorical variables.

## 4. General Cost Management and Monitoring

*   **Watch for Bottlenecks:** If an Earth Engine task takes hours instead of minutes and accumulates massive EECU-seconds, **cancel it**. It is likely hitting an I/O bottleneck.
*   **Batch Processing:** For massive raster operations that do not strictly require GEE APIs (e.g., mathematical scaling), use Google Cloud Batch or local parallelization.
