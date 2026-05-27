# ---------------------------------------------------------------------------
# Compile Python packages
# Author: Timm Nawrocki, Alaska Center for Conservation Science
# Last Updated: 2025-12-16
# Usage: Must be executed in a Python 3.12+ installation.
# Description: "Compile Python packages" compiles a list of Python packages and versions into a csv table.
# ---------------------------------------------------------------------------

# Import libraries
import importlib.metadata
import pandas as pd
import os

#### SET UP DIRECTORIES, FILES, AND FIELDS
####____________________________________________________

# Set round date
round_date = 'round_20241124'

# Set root directory
drive = 'C:/'
root_folder = 'ACCS_Work/Projects/VegetationEcology/AKVEG_Map'

# Define output folder
output_folder = os.path.join(drive,
                             root_folder,
                             'Documents/Manuscript_FoliarCover_FloristicGradients/appendix_s2/data_output')

# Define output file
package_output = os.path.join(output_folder, 'AppendixS2_Python_Packages.csv')

#### COMPILE AND EXPORT LIST OF PACKAGES AND VERSIONS
####____________________________________________________

# Create empty list to store package data
installed_packages = []

# Get list of all installed packages
packages = importlib.metadata.distributions()

for package in packages:
    name = package.metadata['Name']
    version = package.version
    installed_packages.append(f"{name}=={version}")

# Convert list to dataframe
package_data = pd.DataFrame(installed_packages)

# Split packages to multiple columns
package_data[['Name', 'Version']] = package_data[0].str.split('==', expand=True)

# Sort the dataframe by name
package_data = package_data[['Name', 'Version']].sort_values(by="Name", key=lambda col: col.str.lower())

# Export dataframe
package_data.to_csv(package_output, index=False, encoding='utf-8')
