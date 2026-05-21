# Continuous Foliar Cover Maps for Alaska and Yukon

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](#)
[![Python Version](https://img.shields.io/badge/Python-3.7+-blue.svg)](#)
[![R Version](https://img.shields.io/badge/R-4.0+-blue.svg)](#)

Continuous foliar cover maps of diagnostic species sets for Alaska and adjacent Yukon circa 2023

*Author*: Timm W. Nawrocki, Alaska Center for Conservation Science, University of Alaska Anchorage
              Matthew J. Macander, ABR, Inc.—Environmental Research & Services

*Created On*: 2019-10-22

*Last Updated*: 2026-05-21

*Description*: Scripts for data acquisition, statistical modeling, raster post-processing, and performance assessments to map 10 m resolution foliar cover for 32 diagnostic species sets.

## About the Project
This repository contains the processing scripts, workflows, and spatial algorithms to develop continuous 10 m resolution foliar cover maps for 32 diagnostic species sets across four bioclimatic zones in Alaska and adjacent Yukon. These data are part of the Alaska Vegetation (AKVEG) Map and relate to groups and alliances in the U.S. National Vegetation Classification (USNVC). To produce the maps, we statistically associated foliar cover field observations queried from a multi-project database, the [AKVEG Database](https://github.com/akveg-map/akveg-database), with a suite of remotely sensed covariates using hurdle models that combined a classifier and a regressor. The classifiers and regressors consisted of gradient boosting models implemented in LightGBM with Bayesian hyperparameter tuning and presence-absence threshold tuning. To assess the performance of the resulting maps, we conducted a nested, spatially gridded cross validation. We calculated individual performance metrics for each diagnostic species set by comparing observed and predicted values from the merged test partitions of all cross-validation iterations. We assessed the combined performance of the stack of foliar cover maps in relation to the compositional variation represented by subregional vegetation clusters, which represented an alliance level of ecological detail in the absence of a consistent and comprehensive set of alliances in USNVC at the time of this analysis.

This workflow is a core component of the AKVEG Map, which parses spatial distributions of vegetation types from continuous foliar cover maps and maps of surficial features (abiotic surfaces, disturbance regimes, and ecological settings). This approach mirrors the conceptual relationship between ecological gradients and discrete types in vegetation classifications. Our mapping framework aligns with the USNVC. The methods that we present are largely automated to facilitate repeat mapping at regular intervals for change detection. By uniting continuous and categorical data models, this suite of maps promotes flexibility for multiple applications, including quantitative statistical analyses, conservation planning, and natural resource management.

## Getting Started

These instructions will enable you to run scripts to map continuous foliar cover for a selected suite of diagnostic species sets. The scripts integrate multiple systems: Google Earth Engine, Python, and R. The diagnostic species sets must be manually defined in a schema.csv file. Some manually delineated data, such as a map domain, may need to be created or updated in GIS software. Reproducing the results will require creating comparable processing environments; however, we suggest that all software and packages be updated to the most recent available version. Field data used to train the models are queried from the publicly available [AKVEG Database](https://github.com/akveg-map/akveg-database). For more information on the AKVEG Map, see the project website at [https://akveg.org](https://akveg.org) 

### Prerequisites

To execute the code successfully, you will need the following standard and third-party libraries for Python and R computing environments. This workflow requires a valid user account and project within Google Earth Engine. We recommend a setting up a Python geospatial processing environment in a [MiniForge installation](https://github.com/conda-forge/miniforge). While we prioritized open source software to improve reproducibility, a subset of the covariate processing scripts to generate hydrographic flowlines depend on proprietary ArcGIS Pro software, which will require a license through ESRI.

#### Python 3.12+

##### Standard Packages
* `os`
* `random`
* `json`
* `glob`

##### Third-Party Data Science & Geospatial Packages (Latest stable versions):

* `numpy` (v2.0.0+) — *For foundational array and matrix manipulation.*
* `scikit-learn` — *Used for evaluating map performance.*
* `lightgbm` — *Used for gradient boosting statistical models.*
* `pandas` (v2.2.0+) — *Used for tabular data manipulation and generating summary statistics.*
* `geopandas` (v1.0.0+) — *For vector data processing and coordinate reference system management.*
* `rasterio` (v1.3.10+) — *Used for raster manipulation, masking, and feature extraction.*
* `rio-cogeo` (v5.3.0+) — *For Cloud Optimized GeoTIFF (COG) creation and translation.*
* `shapely` (v2.0.4+) — *For geometric operations, defining spatial rules, and creating spatial objects.*
* `pyproj` (v3.6.0+) — *For cartographic projections and coordinate transformations.*
* `rasterstats` (v0.19.0+) — *For summarizing geospatial raster datasets based on vector geometries.*
* `dbf` (v0.99.0+) — *For reading and writing DBF files.*
* `plotly` (v5.20.0+) — *For interactive graphing and visualizations.*
* `kaleido` (v0.2.1+) — *For static image export of Plotly visualizations.*
* `earthengine-api` (v0.1.400+) — *For Google Earth Engine integration and remote sensing workflows.*
* `google-cloud-api` / `google-api-core` (v2.18.0+) — *For interacting with Google Cloud Storage and services.*
* `akutils` (v1.2.4) — *Utilities to simplify processing scripts.*

#### R 4.5.2+

* `sf` (v1.1-1) — *For reading, writing, and handling spatial vector features.*
* `terra` (v1.9-25) — *For efficient handling and processing of spatial raster layers.*
* `tidyterra` (v1.1.0) — *For tidyverse integration and plotting of terra raster objects.*
* `dplyr` (v1.2.1) — *For attribute data manipulation and piping workflows.*
* `ggplot2` (v4.0.3) — *For advanced map composition and plotting.*
* `ggpubr` (v0.6.3) — *For creating publication-ready plot arrangements.*
* `cowplot` (v1.2.0) — *For arranging multiple plots and maps into a single grid.*
* `ggspatial` (v1.1.10) — *For spatial data visualization annotations (e.g., scale bars, north arrows).*
* `fs` (v2.1.0) — *For robust, cross-platform file system operations.*

* `dplyr`
* `raster`
* `rgdal`
* `sp`
* `stringr`
* `tidyr`

## Usage

This repository houses the code necessary to recreate the remotely sensed indicators and sample designs outlined in the monitoring plan. Folders and scripts are numbered to indicate the order of operations necessary to successful execution of the workflow. Key programmatic workflows include:

### 0. Cloud Management

The files in this folder provide detailed instructions to set up cloud and local Python computing environments to conduct geospatial processing and statistical modeling. These instructions assume a valid Google Cloud Compute project and billing account. Alternatively, the described environments could be set up in another system, but the user would need to adapt the instructions outside of Google Cloud.

### 1. Data Grids

These scripts prepare data grids to facilitate mapping. Grids include those used for covariate development (e.g., hydrographic processing units), cross-validation, and statistical model predictions.

### 2. Data Reflectance

Compile Sentinel-1 and -2 reflectance composites through Google Earth Engine

### 3. Data Topography

Download topographic data Process topographic covariates

### 4. Data Hydrography

Compute flow accumulation and flow lines and create hydrographic covariates.

### 5. Data Climate

Download climate data from [Scenarios Network for Alaska and Arctic Planning](https://uaf-snap.org/) and create climate covariates

## Credits
If you use this repository, the algorithms, or the associated foliar cover maps in your work, please cite the corresponding manuscript:

> Nawrocki, T.W., M.J. Macander, A.F. Wells, A. Droghini, G.V. Frost, L.A. Flagstad, M.L. Carlson, H.A. Gravley, M. Hannam, A.E. Miller, C. Roland, C.B. Heslop, T.V. Boucher, K.C. Baer, B.T. Spellman, M. Patz, L.B. Saperstein, D. Gordon, C. Willier, and E.M. Powers. 2026. Plant foliar cover maps predict the variation that drives community classification across four bioclimatic zones. Ecosphere.

### Acknowledgements

Funding support to complete this work was provided by the U.S. Fish and Wildlife Service (grant number F23AC02253) and Bureau of Land Management (grant numbers L22AC00519, L23AC00710). University of Alaska Anchorage provided funding to cover the costs associated with manuscript and data publication. The AKVEG Map is coordinated by the Alaska Vegetation Working Group of the Alaska Geospatial Council.

### License

This project is provided under the GNU General Public License v3.0. It is free to use and modify in part or in whole.

