import ee
import requests
import PIL.Image
import io

PROJECT_ID = "akveg-map"
ee.Initialize(project=PROJECT_ID)

# 1. Precise Bounding Box Calculation (EPSG:3338)
xmin, ymin, xmax, ymax = -2175592.6, 405266.0, 1550577.3, 2384026.0
width = xmax - xmin
height = ymax - ymin

# 10% total buffer (5% on each side) for a less cramped feel
x_buf = width * 0.05
y_buf = height * 0.05

target_extent = [xmin - x_buf, ymin - y_buf, xmax + x_buf, ymax + y_buf]
print(f"Target Extent: {target_extent}")

extent_geom = ee.Geometry.Rectangle(coords=target_extent, proj='EPSG:3338', geodesic=False)

# 2. Robust Basemap
# Use LSIB (International Boundaries) to get a clean, high-performance global landmask
landmask_fc = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
landmask_img = ee.Image.constant(1).clipToCollection(landmask_fc).mask()

# Terrain
topo = ee.Image("USGS/GMTED2010")
hillshade = ee.Terrain.hillshade(topo).resample('bilinear')

# Colors
# Ocean: Light Blue (#add8e6)
# Land: Light Grey (#f0f0f0) with hillshade
ocean = ee.Image.constant(1).visualize(palette=['#add8e6'])
land = hillshade.visualize(min=0, max=255, palette=['#cccccc', '#ffffff'])

# Composite: Use the landmask image to blend
background = ocean.blend(land.updateMask(landmask_img))

# 3. Download
url = background.getThumbURL({
    'region': extent_geom,
    'crs': 'EPSG:3338',
    'dimensions': 1800, # Higher resolution for audit
    'format': 'png'
})

print(f"Downloading basemap from: {url}")
response = requests.get(url)
img = PIL.Image.open(io.BytesIO(response.content))
img.save('03_data_topography/cog_pipeline/reports/background_final.png')
print("Basemap saved.")
