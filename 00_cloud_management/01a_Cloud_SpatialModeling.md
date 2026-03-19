# Google Cloud Virtual Machine with Scikit-Learn

*Author*: Timm Nawrocki, Alaska Center for Conservation Science

*Last Updated*: 2024-09-06

*Description*: Generalized instructions to create one or multiple virtual machine (vm) instances on Google Cloud Compute configured to run statistical learning scripts in the scikit-learn framework. Users should download and install the [Google Cloud SDK](https://cloud.google.com/sdk/) to support some of the described operations (e.g., batch uploads and downloads).

## 1. Configure project
Create a new project if necessary and enable API access for Google Cloud Compute Engine.

### Create a storage bucket for the project
Create a new storage bucket. Select "regional" and make the region the same as the region that your virtual machine will be in. If your virtual machines must be in multiple regions, it is not necessary to have a bucket for each region if you will just be uploading and downloading files between the two.

The storage bucket in this example is named "akveg-data".

Use the "gsutil cp -r" command in Google Cloud SDK to copy data to and from the storage bucket. Example:

```bash
gsutil cp -r gs://akveg-data/example/* ~/example/
```

The "*" is a wildcard and "-r" indicates that the operation should apply to all subdirectories. The target directory should already exist in the virtual machine or local machine. If the storage bucket is the target, then the bucket will create a new directory from the copy command. Load all necessary data for analysis into the storage bucket.

## 2. Configure a new vm instance
The following steps will provision a new virtual machine (vm) that will enable the creation of an image template, which can then be copied to new vms. The software and data loaded on the template vm are exported as a custom disk image along with the operating system. Each additional instance can use the custom disk image rather than requiring independent software installation and data upload.

### Create a new instance with the following features:

Use the guidelines below to create a new vm instance. Once the instance has been created and started, then launch a terminal in a browser window using ssh. There is no need to assign a static IP address to the vm.

*Name*: <name>

*Region*: <region>

*Zone*: Any

*Machine type*: <select based on computational needs>

*VM provisioning model*: Standard

*Boot disk operating system*: Ubuntu

*Boot disk*: Ubuntu 24.04 LTS x86/64

*Boot disk type*: Balanced Persistent Disk

*Size (GB)*: <select based on data size>

*Service account*: Compute Engine default service account

*Access scopes*: Allow full access to all Cloud APIs

*Firewall*: None required

### Set up the system environment:

Update the system prior to installing software and then install necessary base packages.

```bash
sudo apt-get update
sudo apt-get install vim
```

Install the latest Miniconda release. The version referenced in the example below may need to be updated. The repository version should match the Ubuntu Linux release version.

```bash
mkdir ~/miniforge
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O ~/miniforge/miniforge.sh

bash ~/miniforge/miniforge.sh -b -u -p ~/miniforge
rm -rf ~/miniforge/miniforge.sh
~/miniforge/bin/conda init bash
~/miniforge/bin/conda init zsh
source ~/.bashrc
conda create -n akveg -c conda-forge
conda activate akveg
```

Install the necessary packages for geospatial processing and predictive modeling. In the example below, we install packages to support interactions with Earth Engine and statistical learning with LightGBM and Bayesian Optimization. We also install the "akutils" helper functions.

```bash
conda install -c conda-forge numpy openpyxl pandas gdal geopandas rasterio scikit-learn imbalanced-learn lightgbm bayesian-optimization joblib earthengine-api geemap pyarrow fastparquet
python3 -m pip install git+https://github.com/accs-uaa/akutils
```

### Download files to the virtual machine:

Create the data directories referenced in the script. The example below includes directories to validate and train models.

```bash
mkdir ~/scripts
mkdir ~/Data_Input
mkdir ~/Data_Input/extract_data
mkdir ~/Data_Input/species_data
mkdir ~/Data_Output
mkdir ~/Data_Output/model_results
mkdir ~/Data_Output/model_results/<round_date>
```

Use Google Cloud SDK commands from the terminal to download data and scripts for the storage bucket to the vm.

```
gcloud storage rsync gs://akveg-data/extract_data ~/Data_Input/extract_data --recursive
gcloud storage rsync gs://akveg-data/species_data ~/Data_Input/species_data --recursive
gcloud storage rsync gs://akveg-data/scripts ~/scripts --recursive
```

Use vim to update the scripts as necessary. To begin editing a file once it has been opened in vim, press "i". To save and close a file after editing it in vim, press ":wq".

```bash
vim ~/scripts/01b_Validate_Train_Abundance_LGBM.py
i
:wq
```

### Create a custom disk image from template vm:

Creating a custom disk image will allow additional vms to be created that are identical to the template including all files and installed software. This can save much time when creating clusters of vms.
1. Stop the vm
2. Select Compute Engine -> Images
3. Click 'Create Image'
4. Name the image
5. Leave 'Family' blank
6. Select the template vm as the 'Source disk'

Once the image creates successfully, other vm can be created using the custom image, obviating the need to install software and load files for each vm independently.

## 3. Run scripts
To run a script, first make sure the target vm is running and then open terminal in a browser using ssh. Run the script using the python command. Adding "nohup" to the command will prevent ssh interruptions from stopping the script. The script will run as long as the vm is running and store printed statements in a nohup file (otherwise terminal interruptions will stop the script). When running scripts using "nohup", print statements will not appear in the terminal.

```bash
nohup python3 ~/scripts/01b_Validate_Train_Abundance_LGBM.py
```

