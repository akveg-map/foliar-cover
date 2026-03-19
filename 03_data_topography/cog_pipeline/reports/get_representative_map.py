import ee
import requests
import PIL.Image
import io
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
import matplotlib as mpl

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

# 1. Configuration
asset_id = "projects/akveg-map/assets/covariates/aksdb/aksdb_topo_v20250422_scaled_i32/tpi_32_10k"
img = ee.Image(asset_id)

# View Extent (Matching extents map - 10% total buffer)
view_extent = {
    'xmin': -2361901.1,
    'ymin': 306328.0,
    'xmax': 1736885.8,
    'ymax': 2482964.0
}
extent_geom = ee.Geometry.Rectangle(
    coords=[view_extent['xmin'], view_extent['ymin'], view_extent['xmax'], view_extent['ymax']],
    proj='EPSG:3338', geodesic=False
)

# 2. Dynamic Stretch (1% - 99%)
print("Calculating percentiles...")
stats = img.reduceRegion(
    reducer=ee.Reducer.percentile([1, 99]),
    geometry=extent_geom,
    scale=1000, 
    maxPixels=1e9
).getInfo()

p1 = stats.get('tpi_32_10k_p1', -5000)
p99 = stats.get('tpi_32_10k_p99', 5000)
print(f"Stretch: {p1} to {p99}")

# 3. Robust Basemap
landmask_fc = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
landmask_img = ee.Image.constant(1).clipToCollection(landmask_fc).mask()
topo = ee.Image("USGS/GMTED2010")
hillshade = ee.Terrain.hillshade(topo).resample('bilinear')
ocean = ee.Image.constant(1).visualize(palette=['#add8e6'])
land = hillshade.visualize(min=0, max=255, palette=['#cccccc', '#ffffff'])
background = ocean.blend(land.updateMask(landmask_img))

# 4. Composite Overlay
viz = {'min': p1, 'max': p99, 'palette': ['#0000ff', '#ffffff', '#ff0000']} 
overlay = img.visualize(**viz).updateMask(img.neq(-2147483648))
composite = ee.ImageCollection([background, overlay]).mosaic()

# 5. Download Thumbnail
url = composite.getThumbURL({
    'region': extent_geom,
    'crs': 'EPSG:3338',
    'dimensions': 1800,
    'format': 'png'
})

print(f"Downloading composite from: {url}")
response = requests.get(url)
main_img = PIL.Image.open(io.BytesIO(response.content))

# 6. Final Assemble with Matplotlib (Add Legend)
fig, ax = plt.subplots(figsize=(14, 10))
ax.imshow(main_img)
ax.axis('off')

# Add Colorbar (Legend)
cmap = mpl.colors.LinearSegmentedColormap.from_list('tpi', ['#0000ff', '#ffffff', '#ff0000'])
norm = mpl.colors.Normalize(vmin=p1/10000.0, vmax=p99/10000.0) 
# Move colorbar slightly more inward
cax = fig.add_axes([0.88, 0.25, 0.02, 0.5]) 
cb = mpl.colorbar.ColorbarBase(cax, cmap=cmap, norm=norm, orientation='vertical')
cb.set_label('Topographic Position Index', fontsize=12)

ax.set_title('Representative Variable: Topographic Position Index (Window: 32)', fontsize=18, pad=20)

plt.savefig('03_data_topography/cog_pipeline/reports/representative_variable.png', dpi=150, bbox_inches='tight')
print("Final representative map updated.")
