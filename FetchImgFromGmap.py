import geopandas as gpd
from shapely.geometry import Point, mapping, shape
import numpy as np
import requests
import os
import dotenv


def drop_z(geom):
    """Drops Z from shapely geometries"""
    if geom.is_empty:
        return geom
    return shape({
        "type": geom.geom_type,
        "coordinates": [[(x, y) for x, y, *_ in part] for part in mapping(geom)["coordinates"]]
    })

dotenv.load_dotenv()
API_KEY = os.getenv("ANKIT_GMAPS_API_Key", "")  
ZOOM = 19
SIZE = "640x640"
MAPTYPE = "satellite"
STEP = 0.001  # appx 100 m 

gdf = gpd.read_file("/home/ankit/BTP/data/Gurugram_Sec23.kml")
gdf = gdf.to_crs(epsg=4326)


gdf["geometry"] = gdf["geometry"].apply(drop_z)
polygon = gdf.union_all()  # combines everything into one Polygon

print(polygon.geom_type)   # should be "Polygon" or "MultiPolygon"
print(polygon.bounds)      # should match your bbox

minx, miny, maxx, maxy = polygon.bounds

print("Bounding box:", minx, miny, maxx, maxy)

x_vals = np.arange(minx, maxx, STEP)
y_vals = np.arange(miny, maxy, STEP)

points_inside = []
for lat in y_vals:
    for lon in x_vals:
        pt = Point(lon, lat)
        if polygon.contains(pt):
            points_inside.append((lat, lon)) 

print(f" {len(points_inside)} points found inside polygon.")

# output
output_folder = "/home/ankit/BTP/data/Gurugram_Sec23_tiles"
os.makedirs(output_folder, exist_ok=True)

max_tiles = 100

for i, (lat, lon) in enumerate(points_inside):
    if i >= max_tiles:
        break
    center = f"{lat},{lon}"
    url = (
        f"https://maps.googleapis.com/maps/api/staticmap?"
        f"center={center}&zoom={ZOOM}&size={SIZE}&maptype={MAPTYPE}&key={API_KEY}"
    )
    response = requests.get(url)
    if response.status_code == 200:
        with open(f"{output_folder}/tile_{i}.png", "wb") as f:
            f.write(response.content)
        print(f"🛰️ Downloaded tile {i} at ({lat:.5f}, {lon:.5f})")
    else:
        print(f" Failed to download tile {i} at ({lat:.5f}, {lon:.5f})")

print(f" All {len(points_inside)} satellite tiles downloaded to '{output_folder}/'")