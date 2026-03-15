import json
import subprocess
import os

def get_sizes(url):
    print(f"Listing {url}...")
    output = subprocess.check_output(['gsutil', 'ls', '-l', url]).decode().split('\n')
    sizes = {}
    for line in output:
        if '.tif' in line:
            parts = line.split()
            if len(parts) >= 3:
                size = int(parts[0])
                name = parts[2].split('/')[-1].replace('.tif', '')
                sizes[name] = size
    return sizes

def main():
    raw_url = 'gs://akveg-data/aksdb_dem_covars_v20250422/'
    scaled_url = 'gs://akveg-data/aksdb_dem_covars_v20250422_scaled_cog/cogs/'
    
    data = {
        'raw': get_sizes(raw_url),
        'scaled': get_sizes(scaled_url)
    }
    
    out_path = '03_data_topography/cog_pipeline/reports/file_sizes.json'
    with open(out_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Updated {out_path} with {len(data['raw'])} raw and {len(data['scaled'])} scaled sizes.")

if __name__ == "__main__":
    main()
