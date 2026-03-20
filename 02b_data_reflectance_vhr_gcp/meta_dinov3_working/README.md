# DINOv3 Canopy Height Model (CHMv2) - Working Directory

This directory contains research and Proof-of-Concept (PoC) scripts for integrating Meta's DINOv3 CHM model into the VHR pipeline.

## PoC Execution (GCP Deep Learning VM)

To run a test chip inference without modifying local environments:

### 1. Provision a GPU VM
Spin up a Google Deep Learning VM with an NVIDIA L4 GPU.

```bash
gcloud compute instances create dinov3-poc-vm \
    --zone=us-central1-a \
    --machine-type=g2-standard-4 \
    --maintenance-policy=TERMINATE \
    --accelerator=type=nvidia-l4,count=1 \
    --image-family=pytorch-latest-cu121 \
    --image-project=deeplearning-platform-release \
    --boot-disk-size=100GB \
    --scopes=https://www.googleapis.com/auth/cloud-platform
```

### 2. Setup and Run
SSH into the instance and run the following:

```bash
# Install minimal dependencies
pip install transformers rasterio

# Set credentials
export HF_TOKEN="your_hugging_face_token"
export GS_PROJECT_ID="akveg-map"

# Run the PoC script
# Note: Input can be a gs:// path
python dinov3_chm_poc.py \
    --input "gs://akveg-data/vhr/nome_beaver/processed/20220803_213641_WV03_104001007889BF00/PS_SRLite_00p50m_20220803_213641_WV03_104001007889BF00.tif" \
    --output "test_chm_chip.tif" \
    --size 1024
```

### 3. Cleanup
Don't forget to stop or delete the instance after testing to avoid costs.
```bash
gcloud compute instances delete dinov3-poc-vm --zone=us-central1-a
```

## Files
- `dinov3_chm_poc.py`: Script for single-chip inference supporting GCS paths.
