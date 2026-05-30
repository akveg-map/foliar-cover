# Continuous Foliar Cover Maps for Alaska and Yukon

[![Project Status: Active](https://img.shields.io/badge/Project%20Status-Active-brightgreen.svg)](#)
[![Python Version](https://img.shields.io/badge/Python-3.7+-blue.svg)](#)
[![R Version](https://img.shields.io/badge/R-4.0+-blue.svg)](#)

Continuous foliar cover maps of diagnostic species sets for Alaska and adjacent Yukon circa 2023

*Author*: Timm W. Nawrocki, Alaska Center for Conservation Science, University of Alaska Anchorage

​              Matthew J. Macander, ABR, Inc.—Environmental Research & Services

*Created On*: 2019-10-22

*Last Updated*: 2026-05-21

*Description*: Scripts for data acquisition, statistical modeling, raster post-processing, and performance assessments to map 10 m resolution foliar cover for 32 diagnostic species sets.

## About the Project
This repository contains the processing scripts, workflows, and spatial algorithms to develop continuous 10 m resolution foliar cover maps for 32 diagnostic species sets across four bioclimatic zones in Alaska and adjacent Yukon. These data are part of the Alaska Vegetation (AKVEG) Map and relate to groups and alliances in the U.S. National Vegetation Classification (USNVC). To produce the maps, we statistically associated foliar cover field observations queried from a multi-project database, the [AKVEG Database](https://github.com/akveg-map/akveg-database), with a suite of remotely sensed covariates using hurdle models that combined a classifier and a regressor. The classifiers and regressors consisted of gradient boosting models implemented in LightGBM with Bayesian hyperparameter tuning and presence-absence threshold tuning. To assess the performance of the resulting maps, we conducted a nested, spatially gridded cross validation. We calculated individual performance metrics for each diagnostic species set by comparing observed and predicted values from the merged test partitions of all cross-validation iterations. We assessed the combined performance of the stack of foliar cover maps in relation to the compositional variation represented by subregional vegetation clusters, which represented an alliance level of ecological detail in the absence of a consistent and comprehensive set of alliances in USNVC at the time of this analysis.

This workflow is a core component of the AKVEG Map, which parses spatial distributions of vegetation types from continuous foliar cover maps and maps of surficial features (abiotic surfaces, disturbance regimes, and ecological settings). This approach mirrors the conceptual relationship between ecological gradients and discrete types in vegetation classifications. Our mapping framework aligns with the USNVC. The methods that we present are largely automated to facilitate repeat mapping at regular intervals for change detection. By uniting continuous and categorical data models, this suite of maps promotes flexibility for multiple applications, including quantitative statistical analyses, conservation planning, and natural resource management.

## Getting Started

These instructions will enable you to run scripts to map continuous foliar cover for a selected suite of diagnostic species sets. The scripts integrate multiple systems: Google Earth Engine, Python, and R. The diagnostic species sets must be manually defined in a schema.csv file. Some manually delineated data, such as a map domain, may need to be created or updated in GIS software. Reproducing the results will require creating comparable processing environments; however, we suggest that all software and packages be updated to the most recent available version. Field data used to train the models are queried from the publicly available [AKVEG Database](https://github.com/akveg-map/akveg-database). For more information on the AKVEG Map, see the project website at [https://akveg.org](https://akveg.org) 

### Prerequisites

To execute the code successfully, you will need the following standard and third-party libraries for Python and R computing environments. This workflow requires a valid user account and project within Google Earth Engine. We recommend a setting up a Python geospatial processing environment in a [MiniForge installation](https://github.com/conda-forge/miniforge). While we prioritized open source software to improve reproducibility, a subset of the covariate processing scripts to calculate topographic and hydrographic covariates depend on proprietary ArcGIS Pro software, which will require a license through ESRI. Software versions provided are the minimum tested version for this workflow, but we suggest updating to the most recent available versions.

#### Python 3.12

##### Data Management and Manipulation Packages

* `numpy` (v2.3.5) — *Foundational array and matrix manipulation.*
* `pandas` (v2.3.3) — *Tabular data manipulation and generating summary statistics.*
* `google-api-python-client` (v2.187.0) — *Python interface to Google Cloud for data management and transfers.*
* `akutils` (v1.2.4) — *Utilities to simplify processing scripts.*

##### Geospatial Data Packages

* `geopandas` (v1.1.1) — *Vector data processing and coordinate reference system management.*
* `gdal` (v3.10.3) — *Raster data processing in C++ with streaming to and from disk.*
* `rasterio` (v1.4.4) — *Raster manipulation, masking, and post-processing.*
* `rasterstats` (v0.20.0) — *Summarizing geospatial raster datasets based on vector geometries.*
* `rio-cogeo` (v5.3.0) — *For Cloud Optimized GeoTIFF (COG) creation and translation.*
* `shapely` (v2.1.2) — *Geometric operations, defining spatial rules, and creating spatial objects.*
* `pyproj` (v3.6.0) — *For cartographic projections and coordinate transformations.*
* `earthengine-api` (v1.7.4) — *Python interface to Google Earth Engine to conduct covariate processing and extraction.*
* `akgeomorph` (v1.0) — *Topographic and hydrographic calculations using arcpy.*

##### ArcGIS Pro Package for Hydrologic Computations

- `arcpy` (v3.6.0) — *Calculate topographic and hydrographic covariates.*

##### Statistical Modeling and Visualization Packages

* `scikit-learn` (v1.8.0) — *Statistical modeling framework and calculating map performance.*
* `imbalanced-learn` (v0.14.0) — *Rapid prototyping and testing for imbalanced classification tasks.*
* `lightgbm` (v4.6.0) — *Gradient boosting implementation for statistical learning models.*
* `bayesian-optimization` (v3.1.0) — Hyperparameter tuning using Gaussian Process.
* `joblib` (v1.5.3) — *Model export and permanence.*
* `plotly` (v6.5.0) — *For interactive graphing and visualizations.*
* `kaleido` (v1.0.0) — *For static image export of Plotly visualizations.*

#### R 4.5.2+

**Data Management and Manipulation Libraries**

* `fs` (v2.1.0) — *Robust, cross-platform file system operations.*
* `dplyr` (v1.2.1) — *Attribute data manipulation and piping workflows.*
* `tidyverse` (v2.0.0) — *Suite of interoperable libraries for tabular data manipulation.*
* `writexl` (v1.5.4) — *Write excel format output tables.*
* `dbplyr` (v2.5.1) — *PostgreSQL database connection.*
* `RPostgres` (v1.4.8) — *PostgreSQL database connection.*
* `janitor` (v2.2.1) — *Tabular data manipulations.*
* `flextable` (v0.9.10) — *Generating tabular outputs for automated process reporting.*
* `ftExtra` (v0.6.4) — *Generating tabular outputs for automated process reporting.*
* `spsurvey` (v5.6.0) — *Spatially balanced sample generation.*

##### Geospatial Data Libraries

* `sf` (v1.1-23) — *Reading, writing, and handling spatial vector features.*
* `terra` (v1.8-86) — *Raster data manipulations.*
* `tidyterra` (v1.1.0) — *Tidyverse integration and plotting of terra raster objects.*
* `exactextractr` (v0.10.1) — *Extraction of raster values.*
* `gdalUtilities` (v1.2.5) — *Utilities to aid geospatial data access and processing.*
* `mapview` (v2.11.4) — *Interactive viewing of geospatial data.*
* `solrad` (v1.0.0) — *Imagery calibrations and solar corrections.*

##### Statistics and Visualization Libraries

* `cluster` (v2.1.8.1) — *Clustering statistical analyses.*
* `vegclust` (v2.0.3) — *Clustering statistical analyses.*
* `mgcv` (v1.9-4) — *Generalized additive models.*
* `ranger` (v0.17.0) — *Implementation of Random Forests.*
* `vegan` (v2.7-2) — *Statistical analyses for ecological community data, including non-metric multidimensional scaling (NMDS).*
* `ggplot2` (v4.0.3) — *Advanced map composition for plotting.*
* `ggpattern` (v1.2.3.) — *Plot styling.*
* `ggrepel` (v0.9.6) — *Plot styling.*
* `ggtext` (v0.1.2) — *Plot styling.*
* `magick` (v2.9.0) — *Plot styling.*
* `metR` (v0.18.3) — *Plot styling.*
* `RColorBrewer` (v1.1-3) — *Plot styling.*
* `viridis` (v0.6.5) — *Plot styling.*
* `ggpubr` (v0.6.3) — *Creation of publication-ready plot arrangements.*
* `cowplot` (v1.2.0) — *Arranging multiple plots and maps into a grid.*
* `ggspatial` (v1.1.10) — *Spatial data visualization annotations (e.g., scale bars, north arrows).*

## Methods

This repository contains the scripted workflow to develop continuous foliar cover maps of diagnostic species sets. Folders and scripts are numbered to indicate the order of operations necessary to successful execution of the workflow. In this "Methods" section, we describe the technical logic of the workflow organized according to the numbered folders. The technical methods describe the flow of the numbered scripts, rather than address each script individually.

### 0. Cloud Management

Scripts in this folder provide detailed instructions to set up cloud and local Python computing environments to conduct geospatial processing and statistical modeling. These instructions assume a valid Google Cloud Compute project and billing account. Alternatively, the described environments could be set up in another system, but the user would need to adapt the instructions outside of Google Cloud.

#### Technical Methods

Several portions of the processing workflow are computationally intensive. We addressed computational scaling challenges by using Google Earth Engine for covariate development and extraction and custom processing environments on Google Cloud Compute for model training, prediction, and raster processing. Technical details for each of these steps are addressed in the subsequent numbered folders described below.

### 1. Data Grids

Scripts in this folder prepare data regular spatial grids across the map domain to facilitate geospatial data processing and map validation. Grids include those used for covariate development (e.g., hydrographic processing units), cross-validation, and statistical model predictions.

- **Covariate Development**: We organized covariate development by 50 km grid to enable spatial parallelization of data processing. For the processing of flow accumulation and flow lines, we additionally buffered the 50 km grids to mitigate edge effects from one grid to the next.
- **Cross-validation**: We used 100 km grids as the spatial units for a gridded cross-validation wherein all sample site visits within the same grid were simultaneously left out. This mitigated optimistic bias in the performance assessments caused by spatial autocorrelation.
- **Model Predictions**: We used 10 km grids as the spatial units for model predictions to reduce memory and storage requirements for cloud-based model predictions.

### 2. Data Reflectance

Scripts in this folder produce multi-seasonal composites from Sentinel-1 synthetic aperture radar data and Sentinel-2 surface reflectance data. We processed radiometric data using Google Earth Engine (GEE; Gorelick et al. 2017) with interfaces in Javascript, R 4.5.2 (R Core Team 2025), and Python 3.12. We address the technical details of radiometric covariates in subheadings dedicated to Sentinel-1 and Sentinel-2, respectively.

#### Sentinel-1 Synthetic Aperture Radar

We developed four surface texture covariates for three seasonal windows across the entire year (for a total of 12 textural covariates) by calculating different polarity (vertical versus horizontal) combinations of synthetic aperture radar (SAR) acquisitions from the Sentinel-1 platform. For the AKVEG Map v2.1, the Sentinel-1 data represent the years 2022 and 2023. The numerical identifier and seasons that we used were as follows:

1. Growing Season consisting of July and August (2022)
2. Early Winter season consisting of November and December (2022)
3. Mid-winter season consisting of January and February (2023)

#### Sentinel-2 Multispectral Reflectances

We developed 16 spectral covariates for each of five seasonal windows within the snow-free season, defined using per pixel statistics, for a total of 80 spectral covariates across all seasons. For AKVEG Map v2.1, we calculated all spectral covariates from geometric median composites using available acquisitions from 2019–2023. Phenological timing varies drastically across the AKVEG Map domain. We therefore defined seasonal windows for the snow-free season (except in areas of perennial snow and glacier) based on per pixel central dates calculated from the distribution of snow-free observations in the Sentinel-2 record. First, we excluded dates when the sun angle at solar noon was lower than 40° (in spring) or 25° (in fall). These solar angle thresholds eliminated data with poor illumination properties in early April or November, although the exact threshold dates varied according to geographic position. We then extracted the day-of-year for remaining observations flagged as 'cloud-free, cloud-shadow-free, and snow-free' based on image metadata. From this distribution of image dates in each pixel, we selected the 5th percentile day-of-year to define the center of the 'Green-up' window and the 95th percentile to define the center of the 'Senescence' window. The numerical identifiers and spatially variable seasons that we defined were as follows:
1. Green-up: Geometric median composite of all quality-screened observations within +/- 7 days of central day-of-year, defined per pixel as the 5th percentile day-of-year.
2. Early Summer: Geometric median composite of all quality-screened observations within +/- 10 days of central day-of-year, defined per pixel as the date 25% of the way between Green-up and Midsummer.
3. Midsummer: Geometric median composite of all quality-screened observations within +/- 14 days of July 31 (i.e., no spatial variation).
4. Late Summer: Geometric median composite of all quality-screened observations within +/- 14 days of central day-of-year, defined per pixel as the date 50% of the way between Midsummer and Senescence.
5. Senescence: Geometric median composite of all quality-screened observations within +/- 14 days of central day-of-year, defined per pixel as the 95th percentile day-of-year.

Differences in the length of the temporal windows for each Sentinel-2 season accounted for phenological differences (e.g., green-up tends to occur more rapidly than senescence) and weather variability (e.g., the proportion of cloud-obscured observations increases later in the snow-free season). To help account for fire-related disturbances that occurred from 2019–2023, we omitted images collected prior to the disturbance. Thus, the composite images represent conditions for circa 2023 except after disturbances (i.e., because no alternate data was available to mask out 2023 fires). For pixels with fewer than three filtered contributing images, we repeated the analysis without filtering. This helped fill missing data regions for perennial snow and recent fires. 

Finally, we also developed a Sentinel-2 median composite representing May-September 2019–2023 with cloud masking using cloud probability score but no additional filtering. The resulting Sentinel-2 growing season composite enabled us to fill missing data in the Sentinel-2 individual seasonal composites, primarily in unvegetated areas. In addition to the bands collected by the Sentinel-2 platform, we calculated six normalized difference metrics for each of the five seasonal windows. Table 1 provides the calculation and methodological reference for each metric.

Table 1. Normalized Difference (Norm. Diff.) metrics, equations, and methodological references.

| **Norm. Diff.  Metric**              | **Calculation**                 | **Reference**        |
| ------------------------------------ | ------------------------------- | -------------------- |
| Norm. Burn  Ration (NBR)             | (NIR −  SWIR2)/(NIR + SWIR2)    | Key and  Benson 1999 |
| Norm.  Green Red Diff. Index (NGRDI) | (Green -  Red)/(Green + Red)    | Hunt et  al. 2005    |
| Norm. Diff. Moisture Index (NDMI)    | (NIR − SWIR1)/(NIR + SWIR1)     | Gao 1996             |
| Norm. Diff. Snow Index (NDSI)        | (Green − SWIR1)/(Green + SWIR1) | Hall et al. 1995     |
| Norm. Diff. Vegetation Index  (NDVI) | (NIR − Red)/(NIR + Red)         | Tucker 1979          |
| Norm. Diff. Water Index (NDWI)       | (Green − NIR)/(Green + NIR)     | McFeeters 1996       |

### 3. Data Topography

Scripts in this folder generated eight topographic covariates. We processed an initial elevation composite raster using GDAL (Rouault et al. 2025) and rasterio (Gillies et al. 2025) in Python 3.12. We relied on ArcGIS Pro 3.5 (ESRI 2025) with Python 3.11 to process topographic covariate data from the initial elevation composite raster. The topographic and hydrographic data derived from a combination of two source datasets to cover Alaska and adjacent Canada:

- **Alaska InSAR 5 m Digital Terrain Model:** The Alaska InSAR 5 m DTM developed through the USGS 3-D Elevation Program provided comprehensive coverage of Alaska. We include scripts to download these data from the Alaska Department of Natural Resources Division of Geological & Geophysical Surveys. We resampled these data to 10 m resolution to match the target resolution of the AKVEG Map.
- **ESA/Copernicus GLO-30 Digital Surface Model:** The ESA GLO-30 (30 m) DSM developed by European Space Agency provides comprehensive global coverage and was the best publicly available elevation data covering adjacent Canada, where the coverage of the Alaska InSAR 5 m DTM lapsed. We include scripts to download these data from the European Union Copernicus Program. We resampled these data to 10 m resolution using bilinear interpolation to match the target resolution of the AKVEG Map.

We did not attempt to reconcile the differences between the two elevation datasets at their boundary, nor did we reconcile differences related to terrain versus surface elevation models. We calculated a suite of topographic covariates from the AKVEG elevation composite following the equations provided by Evans et al. (2014). We list additional notes and calculation references for specific topographic covariates below:

- **Aspect:** Used a quadratic interpretation (ESRI 2025).
- **Slope:** Used a quadratic interpretation (ESRI 2025).
- **Heatload:** Calculated following McCune and Keon (2002). The heat load index calculation is calibrated for latitudes 0–60°N latitudes. Much of the AKVEG Map domain extends north of 60°N, where the heat load index is not suitable for linear interpretations. We include the heat load index, however, because our models make no assumptions of linear relationships between the covariates and response variables.
- **Position:** Calculated within a 10 × 10 km moving window. Topographic position represents the difference between the local (i.e., pixel) elevation and the average elevation of the moving window.
- **Relief:** Calculated within a 5 × 5 cell moving window.
- **Roughness:** Calculated within a 5 × 5 cell moving window as the square of the standard deviation in elevation (Riley et al. 1999).

### 4. Data Hydrography

Scripts in this folder generated four hydrographic covariates. We relied on ArcGIS Pro 3.5 (ESRI 2025) with Python 3.11 to process flow accumulation and flow lines and create hydrographic covariates. All hydrographic covariates except distance to coast derived from a flow network and flow accumulation calculated using the “Derive Continuous Flow” (ESRI 2025) algorithm with multi-directional flow implemented in ArcGIS Pro. We converted the flow network to approximate representations of streams and rivers by applying flow accumulation thresholds of 10,000 and 1,000,000, respectively. We selected the flow accumulation thresholds by comparing results to the Alaska High Resolution Imagery 2020 composite (© Vantor) to ensure that the streams corresponded to visible linear waterways in the imagery and rivers corresponded to visible linear waterways with clearly developed floodplains in the imagery. We calculated the topographic wetness index based on Gessler et al. (1995; see compound topographic index) with additional weighting to reduce the values for high-gradient streams and drainages. Finally, we also calculated distance to coast based on a 1:63,000 scale map of the landmass of northwestern North America.

### 5. Data Climate

Scripts in this folder downloaded historical climate data from [Scenarios Network for Alaska and Arctic Planning](https://uaf-snap.org/) (SNAP) and processed three climate covariates: total annual precipitation (mm), summer warmth index (°C), and minimum January temperature (°C) using SNAP CRU TS 4.8 and 4.0 historical data (SNAP 2025). These covariates represented the period from 2006 to 2015, approximately one decade prior to the target date of the AKVEG Map v2.1 (circa 2023). We included data one decade prior to the map timeframe to account for the lagged responses of vegetation to climate and based on the availability of historical climate data.

We calculated total annual precipitation and minimum January temperature as per pixel averages of raster values representing each year. To calculate summer warmth index, we first summed mean temperature rasters for May through September for each year and then calculated the per pixel average of the sum raster values. The historical climate data had an original resolution of 2 km for the majority of our map domain. Additionally, we relied on SNAP data with 15 km resolution to cover the included portion of Northwest Territories, which did not overlap the 2 km resolution SNAP data. To avoid resolution artifacts in the foliar cover maps, we resampled the climate data to a 10 m resolution using bilinear interpolation.

### 7. Data Ingestion

Scripts in this folder converted the topographic, hydrographic, and climate covariate rasters to cloud-optimized geotiffs and ingested them into Google Earth Engine to support model development, specifically extraction of area-weighted means to geometries representing site visits. The radiometric covariates were initially developed within Google Earth Engine and therefore did not need to be separately ingested.

### 8. Data Model

Scripts in this folder queried field data from the AKVEG Database, combined the field data with randomly generated absences, prepared these combined data for modeling, and extracted area-weighted covariate means to geometries representing site visits. Two ancillary datasets were required for the filtering steps in the field data preparation workflow:

- **ESA World Cover v2.0:** This 10 m resolution land cover map developed by European Space Agency enabled us to filter site centroids that occurred within predicted water. This step was necessary because some centroids were within large aerial polygons that included apparent surface water at a 10 m resolution. We also used these data in post-processing of the foliar cover maps to enforce water, barrens, and snow/ice for particular diagnostic species sets.
- **Burn Year**: These data were assembled from fire history polygons and rasters for Alaska and adjacent Canada to represent the most recent year (yyyy) of recently burned areas. We used these data to filter out site visits that were observed prior to burning or within 10 years of burning.

To arrive at a set of field observations that could train, validate, and test foliar cover models, we balanced the need for the highest possible sample size with limitations of individual project datasets. We created a series of variable filters and checks to query and summarize field observations from the AKVEG Database, assigning an observed foliar cover value of -1 to signify the exclusion of site visits that did not meet our filter criteria for a particular diagnostic species set. The perspective and cover definitions for data in the AKVEG Database warrant explanation because they affect the error structure of the map results. Survey perspectives were either aerial or ground. Aerial observations were made from above the site, typically from a hovering helicopter, and therefore had limited taxonomic resolution. Ground observations were made by personnel on the ground surface and could include high taxonomic resolution. The AKVEG Database incorporated data collected according to four cover definitions:

1. **Absolute foliar cover:** proportional area of ground covered by above-ground plant parts across all vertical strata of the community relative to the total surveyed area.
2. **Absolute canopy cover:** proportional area of ground covered by above-ground plant silhouettes across all vertical strata of the community relative to the total surveyed area.
3. **Top foliar cover:** proportional area of ground covered by above-ground plant parts within only the uppermost canopy vertical stratum of the community relative to the total surveyed area.
4. **Top canopy cover:** proportional area of ground covered by above-ground plant silhouettes within only the uppermost canopy vertical stratum of the community relative to the total surveyed area.

We intended our maps to represent absolute foliar cover because multi-strata community composition and structure are important factors in determining USNVC alliances and are often ecologically important. Additionally, absolute foliar cover can correspond better to remote sensing measurements than top foliar cover for perennial vegetation (see “any-hit cover” in Karl et al. 2017). The exclusion of top cover (foliar or canopy) and absolute canopy cover data, however, would have removed a substantial portion of available training data from our analyses, resulting in large data gaps in both physical and covariate space. Therefore, we pooled data from all cover types, sacrificing data consistency and increasing model error to maximize the amount and coverage of training data.

To mitigate inconsistencies in the interpretation of absences associated with pooling data collected according to various methods and cover definitions, we established data filtering criteria unique to each diagnostic species set. We considered diagnostic species sets to be absent from each site visit where none of the constituent taxa were observed or where summed cover was less than 3%. Cover less than 3% often reflects microsite characteristics not appropriate to our intended map resolution. Where individual diagnostic species occur at less than 3% cover, the aggregation of ecologically similar diagnostic species into sets (e.g., wetland sedges) partially mitigates potential omissions. Additionally, the 3% cover threshold enables future compatibility with U.S. Forest Service Forest Inventory and Analysis data, which we were unable to include in this mapping iteration. We omitted site visits where the survey methods precluded the observation of the diagnostic species set. For example, we removed site visits from the training data for *Sphagnum* mosses where the observers did not record cover values for bryophyte taxa. Similarly, we omitted absences for site visits where the survey did not include all or most species occurrences. For example, we omitted absences at site visits where the observers recorded cover values only for high-cover species. In combination, our filtering steps provided validation of absences to avoid conflating a lack of observation data with observed absences.

Widespread vegetation change occurred throughout the map domain from 2000 to 2024, including abrupt changes often related to fire disturbances and gradual changes related to climate. We made no adjustments to account for gradual shifts. The discrepancy between our covariate dates and 25-years of accumulated gradual changes in vegetation observations contributed to model error. To account for abrupt changes related to wildfires, we removed site visits where the observation occurred prior to an overlapping burn recorded by fire extent polygons for Alaska (Hrobak and Schmunk 2024) and adjacent Canada. After the completion of all filtering steps, we generated a set of 750 absence points within constrained geometries that represented unvegetated surfaces (e.g., persistent deep water) and additional absence observations for birch and spruce trees (e.g., at sites beyond the Arctic treeline). The data preparation steps described above resulted in presence-absence and percentage cover data for each diagnostic species set that we deemed to be reasonable representations of current (circa 2023) vegetation conditions despite known inconsistencies that contributed to model errors.

To associate covariate values with the spatial geometries of each field site visit, we calculated area-weighted means within circular spatial features approximating the variable plot sizes and shapes. First, we assigned radii based on site metadata describing the plot dimensions. Second, we ingested all covariate datasets and the point representation of site visits into Google Earth Engine. We buffered the points based on the variable radii and calculated area-weighted means within those radii. To improve scalability for spatial geometries of aerial observations, we summarized covariates to 20 m radius circles originating from observation polygon centroids.

The result of the scripts in this folder is a csv table containing all available data in the AKVEG Database with summarized diagnostic species foliar cover values and extracted covariate values. Not all site visits provide valid data for all diagnostic species sets. Where the value of a particular diagnostic species foliar cover is coded as -1, the site visit must be omitted from the train-validate-test data.

### 9. Train Foliar Cover Models

Scripts in this folder train and test foliar cover models as hurdle models combining a classifier predicting presence-absence with a regressor predicting percentage foliar cover. Not all diagnostic species sets are suitable for foliar cover modeling (e.g., diagnostic species that typically occur at low abundances). We therefore also provide a version of the training and prediction scripts that trains only the presence-absence component model. We include several variations of the training script:

- **01a_Validate_Train_Abundance_RF.py:** This script uses Random Forest models in place of the Bayesian-optimized gradient boosting models. Random Forests are much faster and less computationally intensive to train. This script provides a rapid approach to prototype development and testing. We avoided using this script for production mapping for two related reasons: 1) gradient boosting is unanimously more accurate, and 2) Random Forest models tend to more strongly emphasize the central values in the statistical distribution of percentage foliar cover.
- **01b_Validate_Train_Abundance_LGBM.py:** This script provides the production modeling workflow using Bayesian-optimized gradient boosting models. The Bayesian optimization of hyperparameters using Gaussian Processes is slow and computationally intensive with this script taking many hours to complete.
- **01d_Validate_Train_Distribution_LGBM.py:** This script provides the production modeling workflow for diagnostic species sets that do not warrant an abundance component (or for which not enough data exist to accurately map the abundance component).

We conducted statistical modeling and individual performance tests for the development of foliar cover maps in Python 3.12 based on the modeling framework provided through scikit-learn (Pedregosa et al. 2011). The prototype models in our workflow included balanced Random Forest classifiers in imbalanced-learn (Lemaître et al. 2017) and Random Forest regressors in scikit-learn (Pedregosa et al. 2011). The production models in our workflow were gradient boosting classifiers and regressors implemented in LightGBM (Ke et al. 2017). Because gradient boosting models are highly sensitive to hyperparameters, we tuned our gradient boosting models using Gaussian process models in bayesian-optimization (Nogueira et al. 2025). We converted model outputs to tree text strings to test model predictions in GEE (Gorelick et al. 2017). Finally, we post-processed cloud-optimized geotiffs using GDAL and rasterio. We provide a subfolder that contains a script to ingest trained component models into Google Earth Engine to enable generating rapid test predictions.

### 10. Predict Foliar Cover

Scripts in this folder create output continuous foliar cover maps as cloud-optimized geotiff single band 8 bit signed rasters with nodata values of -128. To optimize the prediction step for speed, cost, and memory-efficiency, we first pre-process the covariate rasters into 10 km tiles with one band per covariate. The tiled covariate rasters allow efficient streaming of predictions to and from cloud storage. The prediction scripts include download of the covariate rasters and upload of the predicted raster without storing results locally.

To produce the final maps, the predicted rasters are assembled into one contiguous raster. If the diagnostic species set is associated with a valid range, then predictions beyond that range are set to 0. Similarly, particular diagnostic species sets have water, barrens, and snow/ice enforced based on the ESA World Cover v2.0 dataset.

### 11. Combined Performance

Scripts in this folder conduct the combined performance assessment for the stack of foliar cover maps. Combined performance is assessed relative to the compositional variation represented by subregional vegetation clusters, which represent an alliance level of ecological detail in the U.S. National Vegetation Classification. R 4.5.2 (R Core Team 2025) and and tidyverse (Wickham et al. 2019) supported compilation of tabular benchmark datasets for the combined performance assessments. We conducted ordination analyses using vegan (Oksanen et al. 2025), fuzzy noise clustering using vegclust (De Cáceres et al. 2010), and hard-c medoid clustering using cluster (Maechler et al. 2025). We ran generalized additive models in mgcv (Wood 2017).

#### Subregion Assignment

To ensure that we conducted clustering and ordination at an eco-spatial scale appropriate to alliances, we defined 18 subregions corresponding to high density sampling areas based on unique combinations of vegetation regions, Major Land Resource Areas (MLRAs; NRCS 2025), unified ecoregions (Nowacki et al. 2001), or manually delineated zones corresponding to areas of high-density samples sharing similar environmental characteristics. The MLRA and Unified Ecoregions datasets are publicly available for download.

#### Data Filters

We queried detailed vegetation composition data appropriate to clustering and ordination from the AKVEG Database for each subregion according to the following criteria:

1. The site was surveyed from the ground perspective.
2. Cover measurements were absolute foliar or canopy cover.
3. Observers targeted exhaustive or non-trace species lists for at least vascular plants (it is uncommon in Alaska for surveys to include complete species lists for bryophytes and lichens).

We merged vascular plant observations into species (or genera where species were not determined) and bryophyte and lichen observations into genera (or functional groups where genera were not determined) to avoid artificial taxonomic duplication and standardize typical identification resolutions.

#### Foliar Cover Prediction Extraction

To ensure statistical independence between the foliar cover predictions and the ordination and clustering analyses, we extracted predicted cover values for benchmark sites from the merged test partitions of the outer cross-validation iterations. For site visits that did not contribute to the development of a particular diagnostic species map and were therefore statistically independent from model training and validation, we instead extracted the predicted cover value from the raster map to the site coordinates. Thus, all foliar cover predictions that we used to evaluate the combined performance of the foliar cover maps were statistically independent from the vegetation composition data that we used in ordination and clustering analyses. We also extracted the fine classes (i.e., the most detailed classes) of the Alaska Vegetation and Wetland Composite (AKVWC; Flagstad et al. 2018) and the LANDFIRE 2023 Existing Vegetation Types (EVT; La Puma 2023) to the site coordinates to support comparison to these traditional categorical vegetation maps. For the categorical maps, we converted memberships for each map class to individual variables with Boolean values so that we could evaluate all maps using GAMs.

#### Clustering Stages

For each subregion unit, we conducted two stages of clustering. For both clustering approaches, we compared mean within-cluster variance and mean silhouette width across a range of cluster numbers. We selected the final cluster numbers using an algorithmic approach that selected the best combination of ordinal rankings, balancing the highest mean silhouette widths against the lowest mean within-cluster variances. In cases of ties, we defaulted to the lower number of clusters.

1. **Fuzzy noise clustering:** We conducted fuzzy noise clustering (Davé and Krishnapuram 1997) to remove data that caused high stress (i.e., lower reliability) in the ordinations. We removed all site visits that had greater than or equal to 85% membership to the noise cluster. We compared solutions across a range of cluster numbers Fuzzy noise clustering is highly computationally intensive for large sample sizes (> 200 samples), which is why we only relied on this method for elimination of outliers that caused problems in the ordinations.
2. **Hard c-medoid clustering:** We developed subregional vegetation types (which we call "preliminary alliances") using hard c-medoid (Krishnapuram et al. 1999) clustering because of its computational efficiency, at least relative to fuzzy noise clustering. This enabled better computational efficiency for large sample sizes, especially when the cluster number exceeded 20. Initial methodological experimentation (results not reported) revealed that the deviance explained by preliminary alliances was not highly sensitive to the selection of clustering algorithm or cluster number among multiple options with relatively good combinations of mean silhouette width and mean within-cluster variance.

### 12. Summary Tables and Figures

Scripts in this folder produce summary tables, figures, and text files for an associated manuscript and data repository. We developed chart and plot figures using Plotly (Krutchen et al. 2025) in Python 3.12. We developed map figures using R 4.5.2 (R Core Team 2025) with ggplot2 (Wickham 2016) and ggspatial (Dunnington 2025).

## Covariates

This section provides a list of the abbreviations and full names of the remotely sensed covariates used to develop the continuous foliar cover maps (Table 2). See the "Usage" section above for descriptions of how these covariates were calculated and the source datasets used.

Table 2. Covariate types, abbreviations (Abbr.), and names. Covariate abbreviations are also the variable names in modeling scripts and plot outputs (e.g., covariate importance plots)

| **Covariate Type** | **Abbr.**   | **Covariate Name**                                 |
| ------------------ | ----------- | -------------------------------------------------- |
| Climate            | summer      | Summer warmth index                                |
| Climate            | january     | January minimum air temperature                    |
| Climate            | precip      | Total annual precipitation                         |
| Topography         | elevation   | Elevation (AKVEG elevation  composite)             |
| Topography         | exposure    | Slope-weighted solar exposure                      |
| Topography         | heatload    | Heat load index                                    |
| Topography         | position    | Topographic position                               |
| Topography         | aspect      | Aspect                                             |
| Topography         | relief      | Surface relief ration                              |
| Topography         | roughness   | Roughness                                          |
| Topography         | slope       | Slope                                              |
| Hydrography        | coast       | Distance to marine coast                           |
| Hydrography        | stream      | Distance to stream or river                        |
| Hydrography        | river       | Distance to river                                  |
| Hydrography        | wetness     | Slope-adjusted topographic wetness  index          |
| Radiometry         | s1_1_vha    | Growing season SAR  vertical-horizontal ascending  |
| Radiometry         | s1_1_vhd    | Growing season SAR  vertical-horizontal descending |
| Radiometry         | s1_1_vva    | Growing season SAR  vertical-vertical ascending    |
| Radiometry         | s1_1_vvd    | Growing season SAR  vertical-vertical descending   |
| Radiometry         | s1_2_vha    | Autumn SAR vertical-horizontal  ascending          |
| Radiometry         | s1_2_vhd    | Autumn SAR vertical-horizontal  descending         |
| Radiometry         | s1_2_vva    | Autumn SAR vertical-vertical  ascending            |
| Radiometry         | s1_2_vvd    | Autumn SAR vertical-vertical  descending           |
| Radiometry         | s1_3_vha    | Winter SAR vertical-horizontal  ascending          |
| Radiometry         | s1_3_vhd    | Winter SAR vertical-horizontal  descending         |
| Radiometry         | s1_3_vva    | Winter SAR vertical-vertical  ascending            |
| Radiometry         | s1_3_vvd    | Autumn SAR vertical-vertical  descending           |
| Radiometry         | s2_1_blue   | Green-up multispectral blue                        |
| Radiometry         | s2_1_green  | Green-up multispectral green                       |
| Radiometry         | s2_1_red    | Green-up multispectral red                         |
| Radiometry         | s2_1_redge1 | Green-up multispectral red edge 1                  |
| Radiometry         | s2_1_redge2 | Green-up multispectral red edge 2                  |
| Radiometry         | s2_1_redge3 | Green-up multispectral red edge 3                  |
| Radiometry         | s2_1_nir    | Green-up multispectral NIR                         |
| Radiometry         | s2_1_redge4 | Green-up multispectral red edge 4                  |
| Radiometry         | s2_1_swir1  | Green-up multispectral SWIR 1                      |
| Radiometry         | s2_1_swir2  | Green-up multispectral SWIR 2                      |
| Radiometry         | s2_1_nbr    | Green-up NBR                                       |
| Radiometry         | s2_1_ngrdi  | Green-up NGRDI                                     |
| Radiometry         | s2_1_ndmi   | Green-up NDMI                                      |
| Radiometry         | s2_1_ndsi   | Green-up NDSI                                      |
| Radiometry         | s2_1_ndvi   | Green-up NDVI                                      |
| Radiometry         | s2_1_ndwi   | Green-up NDWI                                      |
| Radiometry         | s2_2_blue   | Early summer multispectral blue                    |
| Radiometry         | s2_2_green  | Early summer multispectral green                   |
| Radiometry         | s2_2_red    | Early summer multispectral red                     |
| Radiometry         | s2_2_redge1 | Early summer multispectral red  edge 1             |
| Radiometry         | s2_2_redge2 | Early summer multispectral red  edge 2             |
| Radiometry         | s2_2_redge3 | Early summer multispectral red  edge 3             |
| Radiometry         | s2_2_nir    | Early summer multispectral NIR                     |
| Radiometry         | s2_2_redge4 | Early summer multispectral red  edge 4             |
| Radiometry         | s2_2_swir1  | Early summer multispectral SWIR 1                  |
| Radiometry         | s2_2_swir2  | Early summer multispectral SWIR 2                  |
| Radiometry         | s2_2_nbr    | Early summer NBR                                   |
| Radiometry         | s2_2_ngrdi  | Early summer NGRDI                                 |
| Radiometry         | s2_2_ndmi   | Early summer NDMI                                  |
| Radiometry         | s2_2_ndsi   | Early summer NDSI                                  |
| Radiometry         | s2_2_ndvi   | Early summer NDVI                                  |
| Radiometry         | s2_2_ndwi   | Early summer NDWI                                  |
| Radiometry         | s2_3_blue   | Midsummer multispectral blue                       |
| Radiometry         | s2_3_green  | Midsummer multispectral green                      |
| Radiometry         | s2_3_red    | Midsummer multispectral red                        |
| Radiometry         | s2_3_redge1 | Midsummer multispectral red edge 1                 |
| Radiometry         | s2_3_redge2 | Midsummer multispectral red edge 2                 |
| Radiometry         | s2_3_redge3 | Midsummer multispectral red edge 3                 |
| Radiometry         | s2_3_nir    | Midsummer multispectral NIR                        |
| Radiometry         | s2_3_redge4 | Midsummer multispectral red edge 4                 |
| Radiometry         | s2_3_swir1  | Midsummer multispectral SWIR 1                     |
| Radiometry         | s2_3_swir2  | Midsummer multispectral SWIR 2                     |
| Radiometry         | s2_3_nbr    | Midsummer NBR                                      |
| Radiometry         | s2_3_ngrdi  | Midsummer NGRDI                                    |
| Radiometry         | s2_3_ndmi   | Midsummer NDMI                                     |
| Radiometry         | s2_3_ndsi   | Midsummer NDSI                                     |
| Radiometry         | s2_3_ndvi   | Midsummer NDVI                                     |
| Radiometry         | s2_3_ndwi   | Midsummer NDWI                                     |
| Radiometry         | s2_4_blue   | Late summer multispectral blue                     |
| Radiometry         | s2_4_green  | Late summer multispectral green                    |
| Radiometry         | s2_4_red    | Late summer multispectral red                      |
| Radiometry         | s2_4_redge1 | Late summer multispectral red edge  1              |
| Radiometry         | s2_4_redge2 | Late summer multispectral red edge  2              |
| Radiometry         | s2_4_redge3 | Late summer multispectral red edge  3              |
| Radiometry         | s2_4_nir    | Late summer multispectral NIR                      |
| Radiometry         | s2_4_redge4 | Late summer multispectral red edge  4              |
| Radiometry         | s2_4_swir1  | Late summer multispectral SWIR 1                   |
| Radiometry         | s2_4_swir2  | Late summer multispectral SWIR 2                   |
| Radiometry         | s2_4_nbr    | Late summer NBR                                    |
| Radiometry         | s2_4_ngrdi  | Late summer NGRDI                                  |
| Radiometry         | s2_4_ndmi   | Late summer NDMI                                   |
| Radiometry         | s2_4_ndsi   | Late summer NDSI                                   |
| Radiometry         | s2_4_ndvi   | Late summer NDVI                                   |
| Radiometry         | s2_4_ndwi   | Late summer NDWI                                   |
| Radiometry         | s2_5_blue   | Senescence multispectral blue                      |
| Radiometry         | s2_5_green  | Senescence multispectral green                     |
| Radiometry         | s2_5_red    | Senescence multispectral red                       |
| Radiometry         | s2_5_redge1 | Senescence multispectral red edge  1               |
| Radiometry         | s2_5_redge2 | Senescence multispectral red edge  2               |
| Radiometry         | s2_5_redge3 | Senescence multispectral red edge  3               |
| Radiometry         | s2_5_nir    | Senescence multispectral NIR                       |
| Radiometry         | s2_5_redge4 | Senescence multispectral red edge  4               |
| Radiometry         | s2_5_swir1  | Senescence multispectral SWIR 1                    |
| Radiometry         | s2_5_swir2  | Senescence multispectral SWIR 2                    |
| Radiometry         | s2_5_nbr    | Senescence NBR                                     |
| Radiometry         | s2_5_ngrdi  | Senescence NGRDI                                   |
| Radiometry         | s2_5_ndmi   | Senescence NDMI                                    |
| Radiometry         | s2_5_ndsi   | Senescence NDSI                                    |
| Radiometry         | s2_5_ndvi   | Senescence NDVI                                    |
| Radiometry         | s2_5_ndwi   | Senescence NDWI                                    |

## Credits
If you use this repository, the algorithms, or the associated foliar cover maps in your work, please cite the corresponding manuscript:

> Nawrocki, T.W., M.J. Macander, A.F. Wells, A. Droghini, G.V. Frost, L.A. Flagstad, M.L. Carlson, H.A. Gravley, M. Hannam, A.E. Miller, C. Roland, C.B. Heslop, T.V. Boucher, K.C. Baer, B.T. Spellman, M. Patz, L.B. Saperstein, D. Gordon, C. Willier, and E.M. Powers. 2026. Continuous foliar cover maps of diagnostic species sets for Alaska and adjacent Yukon circa 2023. Version 2.1. Code Repository. Available: [DOI]

### Acknowledgements

Funding support to complete this work was provided by the U.S. Fish and Wildlife Service (grant number F23AC02253) and Bureau of Land Management (grant numbers L22AC00519, L23AC00710). University of Alaska Anchorage provided funding to cover the costs associated with manuscript and data publication. The AKVEG Map is coordinated by the Alaska Vegetation Working Group of the Alaska Geospatial Council.

### License

This project is provided under the GNU General Public License v3.0. It is free to use and modify in part or in whole.

### Software References

**We provide the following references to software and packages that we used to develop the AKVEG Map continuous foliar cover maps. Please refer to the "Prerequisites" section for a complete list of software and versions.**

Appelhans, T., F. Detsch, C. Reudenbach, and S. Woellauer. 2025. mapview: Interactive Viewing of Spatial Data in R. R package. Available: https://github.com/r-spatial/mapview

Baston, D. 2024. exactextractr: Fast Extraction from Raster Datasets using Polygons. R package. Available: https://isciences.gitlab.io/exactextractr/

Campitelli, E. 2021. metR: Tools for Easier Analysis of Meteorological Fields. R package. Available: https://eliocamp.github.io/metR/

De Cáceres, M., and P. Legendre. 2009. Associations between species and groups of sites: indices and statistical inference. Ecology. 90:3566–3574.

De Cáceres, M., X. Font, and F. Oliva. 2010. The management of vegetation classifications with fuzzy clustering. Journal of Vegetation Science. 21:1138–1151.

den Bossche, J.V., K. Jordahl, M. Fleischmann, M. Richards, J. McBride, J. Wasserman, A.G. Badaracco, A.D. Snow, P. Roggemans, B. Ward, et al. 2025. geopandas. Python package. Available: https://doi.org/10.5281/zenodo.2585848

Dumelle, M., T. Kincaid, A.R. Olsen, and M. Weber. 2023. spsurvey: Spatial Sampling Design and Analysis in R. Journal of Statistical Software. 105:1–29.

Dunnington, D. 2025. ggspatial: Spatial Data Framework for ggplot2. R package. Available: https://paleolimbot.github.io/ggspatial/

ESRI. 2025. ArcGIS Pro (Version 3.x). Computer Software. ESRI. Redlands, CA.

FC, M., and T.L. Davis. 2025. ggpattern: 'ggplot2' Pattern Geoms. R package. Available: https://github.com/trevorld/ggpattern

Firke, S. 2024. janitor: Simple Tools for Examining and Cleaning Dirty Data. R package. Available: https://sfirke.github.io/janitor/

Garnier, S., N. Ross, R. Rudis, A.P. Camargo, M. Sciaini, and C. Scherer. 2024. viridis(Lite) - Colorblind-Friendly Color Maps for R. R package. Available: https://sjmgarnier.github.io/viridis/

Gillies, S., C. van der Well, J.V. den Bossche, M.W. Taves, J. Arnott, B.C. Ward, et al. 2025. shapely: Manipulation and analysis of geometric objects in the Cartesian plane. Python package. Available: https://doi.org/10.5281/zenodo.5597138

Gillies, S., et al. 2025. rasterio: geospatial raster I/O for Python programmers. Python package. Available: https://github.com/rasterio/rasterio

Gohel, D., and P. Skintzos. 2025. flextable: Functions for Tabular Reporting. R package. Available: https://github.com/davidgohel/flextable

Google. 2026. Google API Client Library for Python (Version 2.x). Python package. Available: https://github.com/googleapis/google-api-python-client

Gorelick, N., M. Hancher, M. Dixon, S. Ilyushchenko, D. Thau, and R. Moore. 2017. Google earth engine: planetary-scale geospatial analysis for everyone. Remote Sensing of Environment 202:18–27.

Harris, C.R., K.J. Millman, S.J. van der Walt, R. Gommers, P. Virtanen, D. Cournapeau, E. Wieser, J. Taylor, S. Berg, N.J. Smith, et al. 2020. Array programming with NumPy. Nature. 585:357–362.

Hernangómez, D. 2023. Using the tidyverse with terra objects: the tidyterra package. Journal of Open Source Software. 8:5751.

Hijmans, R. 2025. terra: Spatial Data Analysis. R package. Available: https://github.com/rspatial/terra

Joblib contributors. 2025. joblib. Python package. Available: https://doi.org/10.5281/zenodo.14915601

Kassambara, A. 2025. ggpubr: 'ggplot2' Based Publication Ready Plots. R package. Available: https://rpkgs.datanovia.com/ggpubr/

Ke, G., Q. Meng, T. Finley, T. Wang, W. Chen, W. Ma, Q. Ye, T. Liu. 2017. LightGBM: a highly efficient gradient boosting decision tree. NIPS’17: Proceedings of the 31st International Conference on Neural Information Processing Systems. 3149–3157.

Kruchten, N., A. Seier, and C. Parmer. 2025. plotly.py: an interactive, open-source, and browser-based graphing library for Python. Python package. Plotly Technologies, Inc. Available: https://github.com/plotly/plotly.py

Lemaître, G., F. Nogueira, and C.K. Aridas. 2017. Imbalanced-learn: A Python Toolbox to Tackle the Curse of Imbalanced Datasets in Machine Learning. Journal of Machine Learning Research. 18:1–5.

Maechler, M., P. Rousseeuw, A. Struyf, M. Hubert, and K. Hornik. 2025. cluster: Cluster Analysis Basics and Extensions. R package. Available: https://CRAN.R-project.org/package=cluster

Maechler, M., P. Rousseeuw, A. Struyf, M. Hubert, and K. Hornik. 2025. cluster: Cluster Analysis Basics and Extensions. R package. Available: https://CRAN.R-project.org/package=cluster

McKinney, W. 2010. Data Structures for Statistical Computing in Python. Proceedings of the 9th Python in Science Conference. 56–61.

Nawrocki, T.W. 2026a. akutils. Python package. Available: https://github.com/accs-uaa/akutils

Nawrocki, T.W. 2026b. akgeomorph. Python package. Available: https://github.com/accs-uaa/akgeomorph

Neuwirth, E. 2022. RColorBrewer: ColorBrewer Palettes. R package. Available: https://CRAN.R-project.org/package=RColorBrewer

Nogueira, F., et al. 2025. Bayesian Optimization: open source constrained global optimization tool for Python. Python package. Available: https://github.com/bayesian-optimization/BayesianOptimization

O'Brien, J. 2023. gdalUtilities: Wrappers for 'GDAL' Utilities Executables. R package. Available: https://github.com/joshobrien/gdalutilities

Oksanen, J., G.L. Simpson, F.G. Blanchet, R. Kindt, P. Legendre, P.R. Minchin, R.B. O'Hara, P. Solymos, M.H. Stevens, E. Szoecs, et al. 2025. vegan: Community Ecology Package. R package. Available: https://vegandevs.github.io/vegan/

Ooms, J. 2025. magick: Advanced Graphics and Image-Processing in R. R package. Available: https://github.com/ropensci/magick

Ooms, J., and B. Denney. 2025. writexl: Export Data Frames to Excel 'xlsx' Format. R package. Available: https://ropensci.r-universe.dev/writexl

Pebesma, E. 2018. Simple Features for R: Standardized Support for Spatial Vector Data. The R Journal. 10:439–446.

Pedregosa, F., G. Varoquaux, A. Gramfort, V. Michel, B. Thirion, O. Grisel, M. Blondel, P. Prettenhofer, R. Weiss, V. Duborg, et al. 2011. Scikit-learn: machine learning in python. Journal of Machine Learning Research. 12:2825–2830.

Perry, M., et al. 2025. rasterstats: summary statistics of geospatial raster datasets based on vector geometries. Python package. Available: https://github.com/perrygeo/python-rasterstats

Plotly. 2025. Kaleido: the Next Generation of Static Image Export for Web-Based Visualization Libraries. Python package. Plotly Technologies, Inc. Available: https://github.com/plotly/Kaleido

R Core Team. 2025. R: A language and environment for statistical computing. R Foundation for Statistical Computing, Vienna, Austria. Available: https://www.R-project.org/

Rouault, E., F. Warmerdam, K. Schwehr, A. Kiselev, H. Butler, M. Łoskot, T. Szekeres, E. Tourigny, M. Landa, I. Miara, et al. 2025. Geospatial Data Abstraction Library. Python package. Open Source Geospatial Foundation. Available: https://doi.org/10.5281/zenodo.5884351

Seyednasrollah, B., M. Kumar, and T.E. Link. 2013. On the role of vegetation density on net snow cover radiation at the forest floor. Journal of Geophysical Research: Atmospheres. 118:8359–8374.

Slowikowski, K. 2024. ggrepel: Automatically Position Non-Overlapping Text Labels with 'ggplot2'. R package. Available: https://ggrepel.slowkow.com/

Wickham, H. 2016. ggplot2: Elegant Graphics for Data Analysis. Springer-Verlag. New York, New York. 213 pp.

Wickham, H., J. Ooms, and K. Müller. 2025b. RPostgres: C++ Interface to PostgreSQL. R package. Available: https://rpostgres.r-dbi.org

Wickham, H., M. Averick, J. Bryan, W. Chang, L. D’Agostino McGowan, R. François, G. Grolemund, A. Hayes, L. Henry, J. Hester, et al. 2019. Welcome to the Tidyverse. Journal of Open Source Software. 4:1686.

Wickham, H., M. Girlich, and E. Ruiz. 2025a. dbplyr: A 'dplyr' Back End for Databases. R package. Available: https://dbplyr.tidyverse.org

Wilke, C., and B. Wiernik. 2022. ggtext: Improved Text Rendering Support for 'ggplot2'. R package. Available: https://github.com/wilkelab/ggtext

Wood, S.N. 2017. Generalized Additive Models: An Introduction with R. 2nd Edition. Chapman and Hall/CRC. New York, New York. 496 pp.

Wright, M.N., and A. Ziegler. 2017. ranger: A Fast Implementation of Random Forests for High Dimensional Data in C++ and R. Journal of Statistical Software. 77:1–17.

Yasumoto, A. 2025. ftExtra: Extensions for Flextable. R package. Available: https://github.com/atusy/ftExtra

## Methods References

**We provide the following references to the methods and data sources that we used to develop the AKVEG Map continuous foliar cover maps. Please refer to the "Usage" section for descriptions of covariate processing and data sources.**

ESRI. 2025. ArcGIS Pro (Version 3.x). Computer Software. ESRI. Redlands, CA.

Evans, J.S., J. Oakleaf, and S.A. Cushman. 2014. An ArcGIS Toolbox for Surface Gradient and Geomorphometric Modeling, version 2.0-0. Available: https://github.com/jeffreyevans/GradientMetrics

Gao, B. 1996. NDWI—a normalized difference water index for remote sensing of vegetation liquid water from space. Remote Sensing of the Environment. 58: 257–266.

Gessler, P.E., I.D. Moore, N.J. McKenzie, and P.J. Ryan. 1995. Soil-landscape modeling and spatial prediction of soil attributes. International Journal of GIS. 9. 421–432.

Gorelick, N., M. Hancher, M. Dixon, S. Ilyushchenko, D. Thau, and R. Moore. 2017. Google earth engine: planetary-scale geospatial analysis for everyone. Remote Sensing of Environment 202:18–27.

Hall, D.K., G.A. Riggs, and V.V. Salomonson. 1995. Development of methods for mapping global snow cover using moderate resolution imaging spectroradiometer data. Remote Sensing of Environment. 54:127–140.

Hrobak, J.L., and G. Schmunk. 2024. Alaska Large Fire Database. Alaska Interagency Coordination Center. Fairbanks, Alaska. Available: https://www.frames.gov/catalog/10465

Hunt, E.R., M. Cavigelli, C.S.T. Daughtry, J.E. Mcmurtrey, and C.L. Walthall. 2005. Evaluation of Digital Photography from Model Aircraft for Remote Sensing of Crop Biomass and Nitrogen Status. Precision Agriculture. 6:359–378.

Karl, J.W., S.E. McCord, and B.C. Hadley. 2017. A comparison of cover calculation techniques for relating point-intercept vegetation sampling to remote sensing imagery. Ecological Indicators. 73:156–165.

Key, C.H., and N.C. Benson. 1999. The normalized burn ratio (NBR): a Landsat TM radiometric measure of burn severity. Northern Rocky Mountain Science Center, U.S. Geological Survey, U.S. Department of the Interior. Bozeman, Montana.

McCune, B., and D. Keon. 2002. Equations for potential annual direct incident radiation and heat load index. Journal of Vegetation Science. 13. 603–606.

McFeeters, S.K. 1996. The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features. Remote Sensing Letters. 17:1425–1432.

Nawrocki, T.W., M.L. Carlson, J.L.D. Osnas, E.J. Trammell, and F.D.W. Witmer. 2020. Regional mapping of species-level continuous foliar cover: beyond categorical vegetation mapping. Ecological Applications. 30:e02081.

Riley, S.J., S.D. DeGloria, and R. Elliot. 1999. A terrain ruggedness index that quantifies topographic heterogeneity. Intermountain Journal of Sciences. 5:23–27.

SNAP. 2025. SNAP Data. Scenarios Network for Alaska and Arctic Planning, University of Alaska Fairbanks. Fairbanks, Alaska. Available: https://uaf-snap.org

Tucker, C.J. 1979. Red and photographic infrared linear combinations for monitoring vegetation. Remote Sensing of Environment. 8:127–150.

