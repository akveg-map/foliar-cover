# Full Environment Setup for Maxar OTB Pipeline (OTB v9.1.1)

This is the comprehensive, start-to-finish guide to installing Orfeo ToolBox and resolving the Python 3.13 symbol conflicts on 'mason'.

## 1. Install System & Build Dependencies
```bash
# Check dependencies
dpkg -l libgl1-mesa-dev libglu1-mesa libx11-6 libxext6 libxrender1 libice6 libsm6 cmake python3-dev libpython3-dev

# Install if missing
sudo apt-get update && sudo apt-get install libgl1-mesa-dev libglu1-mesa libx11-6 libxext6 libxrender1 libice6 libsm6 cmake python3-dev libpython3-dev -y
```

## 2. Download OTB and Geoid Data
OTB binaries and Geoid files are downloaded separately.

```bash
sudo mkdir -p /opt/otb
cd /opt/otb

# 2a. Download and extract OTB v9.1.1
sudo curl [https://www.orfeo-toolbox.org/packages/OTB-9.1.1-Linux.tar.gz](https://www.orfeo-toolbox.org/packages/OTB-9.1.1-Linux.tar.gz) -o OTB-9.1.1-Linux.tar.gz
sudo mkdir -p /opt/otb/OTB-9.1.1-Linux
sudo tar -xf /opt/otb/OTB-9.1.1-Linux.tar.gz -C /opt/otb/OTB-9.1.1-Linux --strip-components=1
sudo rm OTB-9.1.1-Linux.tar.gz

# 2b. Download EGM96 Geoid (Required for Maxar Ortho)
# Using the corrected raw GitLab source for the EGM96 grid file
sudo mkdir -p /opt/otb/OTB-9.1.1-Linux/share/otb/geoid
sudo curl [https://gitlab.orfeo-toolbox.org/orfeotoolbox/data/-/raw/main/Input/DEM/egm96.grd](https://gitlab.orfeo-toolbox.org/orfeotoolbox/data/-/raw/main/Input/DEM/egm96.grd) -o /opt/otb/OTB-9.1.1-Linux/share/otb/geoid/egm96.grd
sudo curl [https://gitlab.orfeo-toolbox.org/orfeotoolbox/data/-/raw/main/Input/DEM/egm96.grd.hdr](https://gitlab.orfeo-toolbox.org/orfeotoolbox/data/-/raw/main/Input/DEM/egm96.grd.hdr) -o /opt/otb/OTB-9.1.1-Linux/share/otb/geoid/egm96.grd.hdr
```

## 3. Mandatory One-Time Initialization
```bash
sudo /bin/bash /opt/otb/OTB-9.1.1-Linux/otbenv.profile
```

## 4. Configure the Conda Environment
```bash
conda remove -n otb_env --all -y
conda create -n otb_env python=3.12 "numpy<2" rasterio pandas -y
conda activate otb_env
pip install pyotb
```

## 5. Recompile OTB Python Bindings
This fixes the symbol errors by linking OTB to your Conda environment.

```bash
conda activate otb_env
export OTB_ROOT="/opt/otb/OTB-9.1.1-Linux"
cd $OTB_ROOT
sudo -E env "PATH=$PATH" ./recompile_bindings.sh
```

## 6. Final Symlink Hack
```bash
sudo ln -sf $(python -c "import sys; print(sys.base_prefix)")/lib/libpython3.12.so.1.0 $OTB_ROOT/lib/libpython3.12.so.1.0
```

## 7. Set Final Environment Variables
Add to `~/.bashrc`:
```bash
export OTB_ROOT="/opt/otb/OTB-9.1.1-Linux"
export OTB_APPLICATION_PATH=$OTB_ROOT/lib/otb/applications
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$OTB_ROOT/lib:$LD_LIBRARY_PATH
export PYTHONPATH=$OTB_ROOT/lib/python:$PYTHONPATH
export PATH=$OTB_ROOT/bin:$PATH
export OTB_PYTHON_EXE=$(which python)
```

## 8. Verification
```bash
source ~/.bashrc
conda activate otb_env
python -c "import pyotb; print('Success! Applications loaded:', len(pyotb.get_available_applications()))"