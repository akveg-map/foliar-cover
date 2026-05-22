# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# Define function to compare noise clusters
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a R 4.4.3+ installation.
# Description: "Define function to compare noise clusters" defines a function that iterates through sequential integer cluster numbers using fuzzy noise clustering to produce results that can be summarized to mean variance and mean silhouette width for evaluation of the most appropriate cluster number.
# ---------------------------------------------------------------------------

# Define a function to compare variance and silhouette widths across multiple cluster numbers for fuzzy clustering with noise
fuzzy_nc_compare = function(vegetation_matrix, initial_n, final_n) {
  # Calculate bray dissimilarity
  bray_distance = vegdist(vegetation_matrix, method="bray")
  
  # Create empty data frame to store results
  cluster_results = tibble(
    cluster_n = numeric(),
    cluster = character(),
    variance = double(),
    avg_sil = double()
  )
  
  # Loop through cluster values to test cluster variance
  while (initial_n <= final_n) {
    print(paste('Conducting clustering with', {initial_n}, 'clusters...', sep = ' '))
    
    # Conduct clustering with n clusters
    nc_results = vegclust(x = vegetation_matrix,
                          mobileCenters = initial_n, 
                          method = 'NC',
                          m = 1.2,
                          dnoise = 0.8,
                          nstart = 50)
    
    # Assign hard clusters
    nc_clusters = tibble(defuzzify(nc_results)$cluster) %>%
      rename(cluster = `defuzzify(nc_results)$cluster`) %>%
      mutate(cluster_int = case_when(cluster == 'N' ~ -1.0,
                                     cluster != 'N' ~ as.double(str_replace(cluster, 'M', '')),
                                     TRUE ~ -999))
    
    # Calculate silhouette widths
    sil_widths = silhouette(nc_clusters$cluster_int, bray_distance)
    sil_width = tibble(sil_widths[, "sil_width"]) %>%
      rename(sil_width = `sil_widths[, "sil_width"]`)
    sil_data = cbind(nc_clusters, sil_width) %>%
      group_by(cluster) %>%
      summarize(avg_sil = mean(sil_width))
    
    # Calculate cluster variance
    clust_var = enframe(clustvar(bray_distance, nc_clusters$cluster)) %>%
      rename(cluster = name, variance = value) %>%
      mutate(cluster_n = initial_n) %>%
      left_join(sil_data, by = 'cluster')
    
    # Bind rows to cluster results
    cluster_results = rbind(cluster_results, clust_var)
    
    # Increase counter
    initial_n = initial_n + 1
  }
  
  # Return cluster results
  return(cluster_results)
  
}