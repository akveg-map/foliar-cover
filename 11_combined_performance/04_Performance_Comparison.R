# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Performance comparison
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Performance comparison" creates a 3-axis NMDS ordination of plant community composition data and models the deviance explained across the three ordination axes relative to the results of a selected set of clusters. The deviance explained by the clusters then provides a baseline to compare the deviance predicted by the AKVEG foliar cover maps, the Alaska Vegetation and Wetland Composite, and the Landfire 2023 EVT.
# ---------------------------------------------------------------------------

# Import required libraries
library(dplyr)
library(fs)
library(ggplot2)
library(metR)
library(janitor)
library(lubridate)
library(readr)
library(readxl)
library(writexl)
library(stringr)
library(tibble)
library(tidyr)
library(sf)
library(cluster)
library(vegan)
library(vegan3d)
library(vegclust)
library(rgl)
library(indicspecies)
library(viridis)
library(mgcv)

# Set random seed
set.seed(314)

# Set round date
round_date = 'round_20241124'

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set root directory (modify to your folder structure)
drive = 'C:'
root_folder = 'ACCS_Work'

# Define input folders (modify to your folder structure)
project_folder = path(drive, root_folder, 'Projects/VegetationEcology/AKVEG_Map/Data')
input_folder = path(project_folder, 'Data_Input/ordination_data')

# Define input files
taxa_input = path(input_folder, '00_taxonomy.csv')
site_visit_input = path(input_folder, '03_site_visit.csv')
vegetation_input = path(input_folder, '05_vegetation.csv')
centers_input = path(project_folder, 'Data_Output/ordination_results', round_date, '00_Cluster_Centers.xlsx')

# Read cluster centers
cluster_centers = read_xlsx(centers_input, sheet = 'hardc') # Centers should be set manually be evaluating cluster comparisons

# Identify group number
site_data = read_csv(site_visit_input)
group_number = max(site_data$group_id)

#### COMPARE PERFORMANCE FOR EACH GROUP
####____________________________________________________

count = 1
while (count <= group_number) {
  
  # Define input and output files
  if (count < 10) {
    noise_input = path(project_folder, 'Data_Output/ordination_results', round_date,
                       paste('0', toString(count), '_noise_membership.xlsx', sep = ''))
    hardc_input = path(project_folder, 'Data_Output/ordination_results', round_date,
                       paste('0', toString(count), '_hardc_clusters.xlsx', sep = ''))
    performance_output = path(project_folder, 'Data_Output/ordination_results', round_date,
                             paste('0', toString(count), '_performance.xlsx', sep = ''))
    stress_output = path(project_folder, 'Data_Output/ordination_results', round_date,
                         paste('0', toString(count), '_stress.jpg', sep = ''))
  } else {
    noise_input = path(project_folder, 'Data_Output/ordination_results', round_date,
                       paste(toString(count), '_noise_membership.xlsx', sep = ''))
    hardc_input = path(project_folder, 'Data_Output/ordination_results', round_date,
                       paste(toString(count), '_hardc_clusters.xlsx', sep = ''))
    performance_output = path(project_folder, 'Data_Output/ordination_results', round_date,
                             paste(toString(count), '_performance.xlsx', sep = ''))
    stress_output = path(project_folder, 'Data_Output/ordination_results', round_date,
                         paste(toString(count), '_stress.jpg', sep = ''))
  }
  
  if (!file.exists(performance_output)) {
    print(count)
    
    #### CONDUCT CLUSTERING
    ####____________________________________________________
    
    # Read cluster comparison
    hardc_comparison = read_xlsx(hardc_input, sheet = 'hardc')
    
    # Select outlier sites
    outlier_data = read_xlsx(noise_input, sheet = 'noise') %>%
      filter(N >= 0.8)
    
    # Read site visit data
    site_data = read_csv(site_visit_input) %>%
      filter(group_id == count) %>%
      anti_join(outlier_data, by = 'site_visit_code') %>%
      arrange(site_visit_code)
    
    # Create list of site visits
    site_visit_list = site_data %>%
      distinct(site_visit_code) %>%
      pull(site_visit_code)
    
    # Read and select vegetation data
    vegetation_data = read_csv(vegetation_input) %>%
      filter(site_visit_code %in% site_visit_list) %>%
      select(site_visit_code, taxon_code, cover_percent)
    
    # Convert vegetation data to matrix
    revised_matrix = vegetation_data %>%
      # Convert to wide format
      pivot_wider(names_from = taxon_code, values_from = cover_percent) %>%
      # Convert NA values to zero
      replace(is.na(.), 0) %>%
      # Arrange data
      arrange(site_visit_code) %>%
      # Convert st_vst column to row names
      column_to_rownames(var='site_visit_code')
    
    # Normalize vegetation matrix
    revised_normalized = decostand(revised_matrix, method='normalize')
    
    # Identify the manually determined cluster number
    cluster_number = cluster_centers %>%
      filter(group_id == count) %>%
      pull(cluster_n)
    
    # Conduct clustering with n clusters
    print(paste('Conducting hard c-medoid clustering for group ', toString(count), '...', sep = ''))
    hardc_results = vegclust(x = revised_normalized,
                          mobileCenters = cluster_number, 
                          method = 'KMdd',
                          m = 1.2,
                          nstart = 50)
    
    # Format cluster membership
    cluster_data = revised_normalized %>%
      rownames_to_column('site_visit_code') %>%
      select('site_visit_code') %>%
      cbind(., tibble(hardc_results$memb)) %>%
      pivot_longer(!site_visit_code, names_to = 'cluster') %>%
      filter(value == 1) %>%
      mutate(cluster_int = as.integer(str_replace(cluster, 'M', ''))) %>%
      select(site_visit_code, cluster, cluster_int)
    
    # Bind clusters and membership to site data
    ordination_data = site_data %>%
      inner_join(cluster_data, by = 'site_visit_code')
    
    #### CONDUCT ORDINATION
    ####____________________________________________________
    
    # Calculate bray dissimilarity on normalized vegetation matrix
    bray_normalized = vegdist(revised_normalized, method="bray")
    
    # Calculate NMDS ordination on dissimilarity matrix
    nmds_normalized = metaMDS(bray_normalized,
                              distance = "bray",
                              k = 3,
                              maxit = 50, 
                              trymax = 100,
                              wascores = TRUE)
    
    # Compare stress plots
    stressplot(nmds_normalized)
    
    # Assign scores from NMDS axes
    analysis_data = ordination_data %>%
      mutate(nmds_axis_1 = scores(nmds_normalized, display = "sites")[, 1],
             nmds_axis_2 = scores(nmds_normalized, display = "sites")[, 2],
             nmds_axis_3 = scores(nmds_normalized, display = "sites")[, 3])
    
    #### ASSESS CLUSTER PERFORMANCE RELATIVE TO ORDINATION
    ####____________________________________________________

    # Create one hot encoded variables for cluster membership
    print(paste('Calculating cluster performance for group ', toString(count), '...', sep = ''))
    one_hot_data = as_tibble(model.matrix(~ cluster - 1, analysis_data))
    cluster_data = cbind(analysis_data, one_hot_data)
    
    # Create equation for clusters
    cluster_names = tail(names(cluster_data), cluster_number)
    cluster_equation = ''
    for (cluster in cluster_names) {
      cluster_equation = paste(cluster_equation, cluster, ' + ', sep = '')
    }
    cluster_equation = str_sub(cluster_equation, end = -4)
    
    # Calculate the amount of information explained by the clusters
    cluster_gam = gam(list(as.formula(paste('nmds_axis_1 ~ ', cluster_equation, sep = '')),
                           as.formula(paste('nmds_axis_2 ~ ', cluster_equation, sep = '')),
                           as.formula(paste('nmds_axis_3 ~ ', cluster_equation, sep = ''))
    ),
    data = cluster_data, family = mvn(d = 3))
    cluster_summary = summary(cluster_gam)
    summary(cluster_gam)
    
    #### ASSESS FOLIAR COVER PERFORMANCE RELATIVE TO ORDINATION
    ####____________________________________________________

    # Calculate foliar cover predictions > 3%
    print(paste('Calculating foliar cover performance for group ', toString(count), '...', sep = ''))
    prediction_numbers = analysis_data %>%
      select(site_visit_code, alnus, betshr, bettre, brotre, dryas, dsalix, empnig, erivag, mwcalama,
             ndsalix, nerishr, picgla, picmar, picsit, poptre, populbt, rhoshr, rubspe,
             sphagn, tsumer, vaculi, vacvit, wetsed) %>%
      pivot_longer(!site_visit_code, names_to = 'indicator', values_to = 'prediction') %>%
      mutate(presence = case_when(prediction >= 3 ~ 1,
                                  TRUE ~ 0)) %>%
      group_by(indicator) %>%
      summarize(number = sum(presence)) %>%
      mutate(smooth = case_when(number >= sqrt(nrow(analysis_data)) ~ 1,
                                TRUE ~ 0)) %>%
      mutate(smooth = case_when(number < 20 ~ 0,
                                TRUE ~ smooth))
    
    # Pull non-linear indicators
    smooth_indicators = prediction_numbers %>%
      filter(smooth == 1) %>%
      pull(indicator)
    
    # Pull linear indicators
    linear_indicators = prediction_numbers %>%
      filter(smooth == 0 & number >= 8) %>%
      pull(indicator)
    
    # Create non-linear equation for indicators
    smooth_equation = ''
    for (indicator in smooth_indicators) {
      smooth_equation = paste(smooth_equation, 's(', indicator, ') + ', sep = '')
    }
    smooth_equation = str_sub(smooth_equation, end = -4)
    
    # Create linear equation for indicators
    if (length(linear_indicators) > 0) {
      linear_equation = ''
      for (indicator in linear_indicators) {
        linear_equation = paste(linear_equation, indicator, ' + ', sep = '')
      }
      linear_equation = str_sub(linear_equation, end = -4)
      gam_equation = paste(smooth_equation, ' + ', linear_equation, sep = '')
    } else {
      gam_equation = smooth_equation
    }
    equation_data = tibble(gam_equation)
    
    # Calculate the amount of information predicted by the foliar cover maps
    indicator_gam = gam(list(as.formula(paste('nmds_axis_1 ~ ', gam_equation, sep = '')),
                             as.formula(paste('nmds_axis_2 ~ ', gam_equation, sep = '')),
                             as.formula(paste('nmds_axis_3 ~ ', gam_equation, sep = ''))
    ),
    data = analysis_data, family = mvn(d = 3))
    indicator_summary = summary(indicator_gam)
    summary(indicator_gam)
    
    #### ASSESS AKVWC PERFORMANCE RELATIVE TO ORDINATION
    ####____________________________________________________
    
    # Create one hot encoded variables for akvwc fine classes
    print(paste('Calculating AKVWC performance for group ', toString(count), '...', sep = ''))
    one_hot_data = as_tibble(model.matrix(~ akvwc_fine - 1, analysis_data))
    akvwc_data = cbind(analysis_data, one_hot_data)
    
    # Create equation for akvwc
    akvwc_types = analysis_data %>%
      distinct(akvwc_fine) %>%
      mutate(akvwc_fine = paste('akvwc_fine', akvwc_fine, sep = '')) %>%
      pull(akvwc_fine)
    akvwc_equation = ''
    for (veg_type in akvwc_types) {
      akvwc_equation = paste(akvwc_equation, veg_type, ' + ', sep = '')
    }
    akvwc_equation = str_sub(akvwc_equation, end = -4)
    
    # Calculate the amount of information explained by the akvwc fine classes
    akvwc_gam = gam(list(as.formula(paste('nmds_axis_1 ~ ', akvwc_equation, sep = '')),
                         as.formula(paste('nmds_axis_2 ~ ', akvwc_equation, sep = '')),
                         as.formula(paste('nmds_axis_3 ~ ', akvwc_equation, sep = ''))
    ),
    data = akvwc_data, family = mvn(d = 3))
    akvwc_summary = summary(akvwc_gam)
    summary(akvwc_gam)
    
    #### ASSESS LANDFIRE PERFORMANCE RELATIVE TO ORDINATION
    ####____________________________________________________
    
    # Create one hot encoded variables for landfire classes
    print(paste('Calculating Landfire performance for group ', toString(count), '...', sep = ''))
    one_hot_data = as_tibble(model.matrix(~ landfire_evt - 1, analysis_data))
    landfire_data = cbind(analysis_data, one_hot_data)
    
    # Create equation for landfire
    landfire_types = analysis_data %>%
      filter(landfire_evt != 'm-9999') %>%
      distinct(landfire_evt) %>%
      mutate(landfire_evt = paste('landfire_evt', landfire_evt, sep = '')) %>%
      pull(landfire_evt)
    landfire_equation = ''
    for (veg_type in landfire_types) {
      landfire_equation = paste(landfire_equation, veg_type, ' + ', sep = '')
    }
    landfire_equation = str_sub(landfire_equation, end = -4)
    
    # Calculate the amount of information explained by the landfire classes
    landfire_gam = gam(list(as.formula(paste('nmds_axis_1 ~ ', landfire_equation, sep = '')),
                            as.formula(paste('nmds_axis_2 ~ ', landfire_equation, sep = '')),
                            as.formula(paste('nmds_axis_3 ~ ', landfire_equation, sep = ''))
    ),
    data = landfire_data, family = mvn(d = 3))
    landfire_summary = summary(landfire_gam)
    summary(landfire_gam)
    
    #### EXPORT RESULTS TABLE
    ####____________________________________________________
    
    # Extract information
    mean_variance = hardc_comparison %>%
      filter(cluster_n == cluster_number) %>%
      pull(mean_variance)
    mean_silhouette = hardc_comparison %>%
      filter(cluster_n == cluster_number) %>%
      pull(mean_sil)
    
    # Prepare summary data for export
    export_data = tibble(group_id = count,
                         selected_n = nrow(analysis_data),
                         cluster_n = cluster_number,
                         mean_var = round(mean_variance, 3),
                         mean_sil = round(mean_silhouette, 3),
                         nmds_stress = round(nmds_normalized$stress, 3),
                         gam_clust = round(cluster_summary$dev.expl, 3),
                         gam_ind = round(indicator_summary$dev.expl, 3),
                         gam_akvwc = round(akvwc_summary$dev.expl, 3),
                         gam_lf = round(landfire_summary$dev.expl, 3),
                         scaled_ind = round((indicator_summary$dev.expl/cluster_summary$dev.expl), 3),
                         scaled_akvwc = round((akvwc_summary$dev.expl/cluster_summary$dev.expl), 3),
                         scaled_lf = round((landfire_summary$dev.expl/cluster_summary$dev.expl), 3))
    
    # Export data to xlsx
    sheets = list('summary' = export_data, 'equation' = equation_data)
    write_xlsx(sheets, performance_output)
    
    # Create a tibble that contains the data from stressplot
    stress_results = tibble(x = stressplot(nmds_normalized)$x,
                            y = stressplot(nmds_normalized)$y,
                            yf = stressplot(nmds_normalized)$yf) %>%
      # Change data to long format
      pivot_longer(cols = c(y, yf),
                   names_to = 'var')
    
    # Create plot
    stress_plot = stress_results %>%
      ggplot(aes(x = x,
                 y = value)) +
      # Add points just for y values
      geom_point(data = stress_results %>%
                   filter(var == 'y'),
                 size = 0.5, alpha=0.2) +
      # Add line just for yf values
      geom_step(data = stress_results %>%
                  filter(var == 'yf'),
                col = 'red',
                direction = 'vh') +
      # Change axis labels
      labs(title = paste('NMDS stress plot for group ', count, sep = ' '),
           x = "Observed Dissimilarity",
           y = "Ordination Distance") +
      # Add bw theme
      theme_bw()
    
    # Export plot
    ggsave(stress_output,
           plot = stress_plot,
           device = 'jpeg',
           path = NULL,
           scale = 1,
           width = 6.5,
           height = 3.5,
           units = 'in',
           dpi = 600,
           limitsize = TRUE)
  }
  
  count = count + 1
}
