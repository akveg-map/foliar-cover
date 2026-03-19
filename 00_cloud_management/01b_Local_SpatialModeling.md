# Local Server env with Scikit-Learn

*Author*: Matt Macander, ABR

*Last Updated*: 2025-09-30

*Description*: Recipe to create conda env on local server, configured to run statistical learning scripts in the scikit-learn framework. Adapted from 01_Cloud_SpatialModeling.md

## 1. Configure project
ak-veg project and storage bucket already created

ubuntu with miniconda set up already
screen -r

```bash
conda create -n akveg -c conda-forge
conda activate akveg
```

Install the necessary packages for geospatial processing and predictive modeling. In the example below, we install packages to support interactions with Earth Engine and statistical learning with LightGBM and Bayesian Optimization. We also install the "akutils" helper functions.

```bash
conda install -c conda-forge numpy openpyxl pandas gdal geopandas rasterio scikit-learn imbalanced-learn lightgbm bayesian-optimization joblib earthengine-api geemap pyarrow fastparquet
python3 -m pip install git+https://github.com/accs-uaa/akutils
```


```bash {lgbm_gpu lgbm with gpu support}
conda deactivate
conda remove -n lgbm_gpu --all -y

conda create -n lgbm_gpu -y \
  -c rapidsai -c nvidia -c conda-forge -c defaults \
  python=3.11 \
  "lightgbm>=4.4.0" \
  "cuda-version=12.2" \
  numpy \
  pandas \
  scikit-learn \
  optuna \
  joblib \
  matplotlib \
  cmake \
  libopenblas \
  ocl-icd-system \
  cudf \
  cupy

conda activate lgbm_gpu

python3 -m pip install git+https://github.com/accs-uaa/akutils

```


# # Core dependencies
# conda install -y -c conda-forge numpy pandas scikit-learn optuna joblib \
#                        matplotlib cmake libopenblas ocl-icd-system
#                        
# conda install -y -c conda-forge lightgbm
# 
# conda remove --yes lightgbm
# conda install --yes -c conda-forge lightgbm cudatoolkit=12.1
# 
# conda install -c rapidsai -c nvidia -c conda-forge cudf cupy

```

##1a. akveg-tf for tensorflow tests
conda create -n akveg-tf -c conda-forge
conda activate akveg-tf

#Install the necessary packages for geospatial processing, TensorFlow, and its dependencies. Using the conda-forge channel is recommended for compatibility, especially for GPU support with CUDA.

conda install -c nvidia -c conda-forge cuda tensorflow numpy openpyxl pandas gdal geopandas rasterio scikit-learn imbalanced-learn joblib earthengine-api geemap pyarrow fastparquet

Finally, install the "akutils" helper functions using pip.

python3 -m pip install git+https://github.com/accs-uaa/akutils
python3 -m pip install keras-tuner -q

#If upgrade needed later
python3 -m pip install --upgrade --force-reinstall git+https://github.com/accs-uaa/akutils

#Not needed with nvidia cuda
#export XLA_FLAGS=--xla_gpu_cuda_data_dir=$CONDA_PREFIX/

### Download files to the virtual machine:

Create the data directories referenced in the script. The example below includes directories to validate and train models.

```bash
akveg_home=/data/gis/raster_base/Alaska/AKVegMap/akveg-working

mkdir -p $akveg_home/scripts
mkdir -p $akveg_home/Data_Input
mkdir -p $akveg_home/Data_Input/extract_data
mkdir -p $akveg_home/Data_Input/species_data
mkdir -p $akveg_home/Data_Output
mkdir -p $akveg_home/Data_Output/model_results
mkdir -p $akveg_home/Data_Output/model_results/20250930
```

Use Google Cloud SDK commands from the terminal to download data and scripts for the storage bucket to the vm.

```
gcloud storage rsync gs://akveg-data/extract_data $akveg_home/Data_Input/extract_data --recursive
gcloud storage rsync gs://akveg-data/species_data $akveg_home/Data_Input/species_data --recursive
gcloud storage rsync gs://akveg-data/scripts $akveg_home/scripts --recursive
```

Use vim to update the scripts as necessary. To begin editing a file once it has been opened in vim, press "i". To save and close a file after editing it in vim, press ":wq".

```bash
vim ~/scripts/01b_Validate_Train_Abundance_LGBM.py
i
:wq
```


## 3. Run scripts
To run a script, first make sure the target vm is running and then open terminal in a browser using ssh. Run the script using the python command. Adding "nohup" to the command will prevent ssh interruptions from stopping the script. The script will run as long as the vm is running and store printed statements in a nohup file (otherwise terminal interruptions will stop the script). When running scripts using "nohup", print statements will not appear in the terminal.

```bash
nohup python3 ~/scripts/01b_Validate_Train_Abundance_LGBM.py
```

