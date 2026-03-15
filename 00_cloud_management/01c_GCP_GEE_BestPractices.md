# Google Cloud Platform (GCP) & Earth Engine (GEE) Best Practices

This document outlines mandatory practices for all scripts interacting with GCP and Google Earth Engine within this project. Adhering to these guidelines ensures proper billing, avoids runaway costs, and maximizes computational performance.

## 1. Explicit Project Initialization & Billing

Never rely on the local environment's default credentials to infer the correct billing project. The default project might be a personal account or an outdated configuration, leading to incorrect billing or permission errors.

*   **Rule:** Always define a `PROJECT_ID` variable and **explicitly pass it** to initialization functions.
*   **Earth Engine (Python):**
    ```python
    import ee
    
    PROJECT_ID = "akveg-map"
    
    # WRONG: ee.Initialize()  <- Defaults to local auth context
    # RIGHT:
    ee.Initialize(project=PROJECT_ID)
    ```
*   **Google Cloud Clients (Storage, Batch, etc.):**
    ```python
    from google.cloud import storage
    
    PROJECT_ID = "akveg-map"
    
    # WRONG: client = storage.Client()
    # RIGHT:
    client = storage.Client(project=PROJECT_ID)
    ```

## 2. Reading Data: Cloud Storage vs. Native GEE Assets

Earth Engine allows you to read Cloud-Optimized GeoTIFFs (COGs) directly from Google Cloud Storage (GCS) on the fly, but this is often a trap for heavy workloads.

### The "On-the-Fly" I/O Penalty
Using `ee.Image.loadGeoTIFF('gs://bucket/file.tif')` is convenient for quickly viewing a single image or doing a simple summary. 

**The Problem:** When you run complex spatial queries—such as extracting 10,000 random points across Alaska (`reduceRegions`) from a stack of 111 COGs—Earth Engine has to make hundreds of thousands of individual HTTP network requests to GCS. 
*   GEE spins up hundreds of compute workers.
*   Those workers spend 99% of their time idle, waiting for data to travel over the network from GCS.
*   **You are billed for the idle wait time.** This is how a simple extraction can accidentally consume 500,000+ EECU-seconds.

### The Solution: Ingesting to an Image Collection
For production models, large-scale sampling, or intensive processing, data must be **ingested** into Earth Engine.

**What does "Ingesting" mean?**
Ingestion is the process of formally importing data from a GCS bucket (`gs://...`) into a native Earth Engine Asset (`projects/akveg-map/assets/...`). During ingestion, Earth Engine copies your GeoTIFF and restructures it into its proprietary, highly distributed, and heavily tiled internal format.

**Why is it necessary?**
1.  **Speed:** Native assets sit directly next to Earth Engine's compute nodes. Network latency drops to near zero.
2.  **Cost:** Because data retrieval is instantaneous, compute workers actually compute. An operation that takes 500,000 EECU-seconds reading from GCS might take 500 EECU-seconds reading from a native asset.
3.  **Parallelism:** Native assets are pre-optimized for GEE's specific brand of MapReduce distributed computing.

**How to Ingest:**
Instead of `ee.Image.loadGeoTIFF()`, you use the `earthengine` CLI or the Python API's upload manifest system to create the asset:
```bash
earthengine upload image --asset_id projects/akveg-map/assets/my_collection/my_image gs://akveg-data/my_image.tif
```
Once ingested, you load it instantly:
```python
img = ee.Image('projects/akveg-map/assets/my_collection/my_image')
```

## 3. General Cost Management and Monitoring

*   **Watch for Bottlenecks:** If an Earth Engine task feels like it is taking an exceptionally long time (hours instead of minutes) and accumulating massive EECU-seconds, **cancel it**. It is almost certainly hitting an I/O bottleneck.
*   **Batch Processing:** For massive raster operations that do not strictly require Earth Engine's specific APIs (e.g., applying mathematical scaling to millions of pixels), use Google Cloud Batch or local parallelization. It is often much cheaper and faster to process the files as standard rasters before interacting with GEE.
