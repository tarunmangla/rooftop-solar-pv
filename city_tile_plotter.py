import geopandas as gpd
from shapely.geometry import Point, Polygon # <-- Added Polygon
import numpy as np
import osmnx as ox
import matplotlib.pyplot as plt
import contextily as ctx # For adding the map background
import sys
import os # Added for path joining
import glob # For listing files
import re # For extracting numbers from filenames
from tqdm import tqdm # For progress bars

# --- Configuration ---
# --- NEW: Use the Municipal Corporation boundary ---
CITY_NAME = "Jaipur Municipal Corporation, India"
# ---------------------
# Configs must match the download script
ZOOM = 19
TILE_SIZE_PX = 640
# STEP is now calculated automatically, not set here.
# ---------------------

# --- Tile Folder Location ---
# !! IMPORTANT: This must point to your NEW download folder !!
DOWNLOADED_TILES_FOLDER = "./Jaipur_Correct_City_Tiles" # <--- CHECK THIS PATH
# -----------------------------

# Output image filename (will save in the same directory as the script)
OUTPUT_IMAGE_FILE = "jaipur_correct_city_plot.png"
# Plot appearance
BOUNDARY_EDGE_COLOR = 'black'
BOUNDARY_LINE_WIDTH = 1.5
POINT_COLOR = 'red'
POINT_SIZE = 0.5 # Adjust for visibility
POINT_ALPHA = 0.5 # Semi-transparent
FIGURE_SIZE = (12, 12)
DPI = 300
BASEMAP_SOURCE = ctx.providers.OpenStreetMap.Mapnik
# ---------------------

# --- Helper Function to Scan Folders ---
def get_existing_indices(folder_path):
    """Scans a folder and returns a set of indices from tile_*.png files."""
    indices = set()
    if not os.path.isdir(folder_path):
        print(f"❌ Error: Directory not found: '{folder_path}'")
        return None # Indicate error

    print(f"🔍 Scanning '{folder_path}' for existing tiles...")
    search_pattern = os.path.join(folder_path, "tile_*.png")
    existing_files = glob.glob(search_pattern)
    tile_pattern = re.compile(r"tile_(\d+)\.png$")
    count = 0
    # Add progress bar for scanning
    for f_path in tqdm(existing_files, desc=f"Scanning {os.path.basename(folder_path)}", leave=False):
        match = tile_pattern.search(os.path.basename(f_path))
        if match:
            try:
                indices.add(int(match.group(1)))
                count += 1
            except ValueError:
                pass # Ignore files with non-integer numbers
    print(f"✅ Found {count} tiles in '{os.path.basename(folder_path)}'.")
    return indices
# ----------------------------------------

# --- Regenerate the full list of potential points (MATCHING DOWNLOAD SCRIPT) ---
print(f"🌍 Downloading boundary for: {CITY_NAME}")
try:
    gdf_city = ox.geocode_to_gdf(CITY_NAME)
except Exception as e:
    print(f"❌ Error downloading boundary: {e}")
    sys.exit()

if gdf_city.crs is None or 'epsg:4326' not in str(gdf_city.crs).lower():
    gdf_city = gdf_city.to_crs(epsg=4326)

polygon = gdf_city.union_all() if not gdf_city.empty else None
if polygon is None:
    print("❌ Could not create city polygon."); sys.exit()
minx, miny, maxx, maxy = polygon.bounds

# --- Calculate Disjoint Step Size (Same as download script) ---
print("Calculating tile step size based on latitude...")
avg_lat = (miny + maxy) / 2
avg_lat_rad = np.radians(avg_lat)
meters_per_pixel = (156543.03 * np.cos(avg_lat_rad)) / (2**ZOOM)
tile_size_meters = TILE_SIZE_PX * meters_per_pixel
STEP_Y_DEGREES = tile_size_meters / 111320.0
STEP_X_DEGREES = tile_size_meters / (111320.0 * np.cos(avg_lat_rad))
half_step_x = STEP_X_DEGREES / 2
half_step_y = STEP_Y_DEGREES / 2
print(f"   Calculated Step Y (Lat): {STEP_Y_DEGREES:.6f} degrees")
print(f"   Calculated Step X (Lon): {STEP_X_DEGREES:.6f} degrees")
# --- END STEP CALCULATION ---

print("🔍 Calculating all potential tile locations (using INTERSECTS)...")
potential_points_map = {}
x_vals = np.arange(minx, maxx, STEP_X_DEGREES)
y_vals = np.arange(miny, maxy, STEP_Y_DEGREES)
current_index = 0
total_grid_points = len(x_vals) * len(y_vals)

with tqdm(total=total_grid_points, desc="Generating Potential Points") as pbar_points:
    for lat in y_vals:
        for lon in x_vals:
            pbar_points.update(1)
            # --- Create the bounding box for this tile ---
            min_lon, max_lon = lon - half_step_x, lon + half_step_x
            min_lat, max_lat = lat - half_step_y, lat + half_step_y
            tile_box = Polygon([
                (min_lon, min_lat), (min_lon, max_lat),
                (max_lon, max_lat), (max_lon, min_lat)
            ])
            # --- Check for INTERSECTION ---
            if polygon.intersects(tile_box):
                potential_points_map[current_index] = Point(lon, lat) # Map index to CENTER point
                current_index += 1

total_potential_tiles = len(potential_points_map)
if total_potential_tiles == 0:
    print(f"❌ No potential points found inside the boundary for '{CITY_NAME}'.")
    sys.exit()
print(f"✅ Calculated {total_potential_tiles} total potential tile locations.")
# --- END POINT GENERATION ---


# --- Scan ONLY the new local download folder ---
drive_indices = get_existing_indices(DOWNLOADED_TILES_FOLDER)

if drive_indices is None: sys.exit() # Folder not found
if not drive_indices:
    print(f"❌ No downloaded tiles found in '{DOWNLOADED_TILES_FOLDER}'. Cannot create plot.")
    sys.exit()

num_total_downloaded = len(drive_indices)
print(f"\n✅ Plotting based on {num_total_downloaded} tiles found in the folder.")


# --- Filter potential points based ONLY on folder contents ---
print(" Filtering points to match downloaded files...")
downloaded_points_geom = []
for index in drive_indices:
    if index in potential_points_map:
        downloaded_points_geom.append(potential_points_map[index])
    else:
        print(f"⚠️ Warning: Found file for index {index}, but it was not in the calculated grid. Check STEP/CITY_NAME.")


if not downloaded_points_geom:
    print("❌ No matching coordinates found for the downloaded files. Check config.")
    sys.exit()

print(f"✅ Matched {len(downloaded_points_geom)} downloaded tiles to coordinates.")

# --- Create GeoDataFrames for plotting ---
print("📊 Creating GeoDataFrames...")
gdf_points_downloaded = gpd.GeoDataFrame(geometry=downloaded_points_geom, crs="EPSG:4326")

# --- Reproject to Web Mercator (EPSG:3857) ---
print("🌐 Reprojecting data to Web Mercator (EPSG:3857)...")
gdf_city_proj = gdf_city.to_crs(epsg=3857)
gdf_points_proj = gdf_points_downloaded.to_crs(epsg=3857)

# --- Create the Plot ---
print(f"📈 Generating plot with basemap for {len(downloaded_points_geom)} downloaded tiles...")
fig, ax = plt.subplots(1, 1, figsize=FIGURE_SIZE)

gdf_city_proj.plot(ax=ax, facecolor='none', edgecolor=BOUNDARY_EDGE_COLOR, linewidth=BOUNDARY_LINE_WIDTH, zorder=2)
gdf_points_proj.plot(
    ax=ax,
    marker='o',
    color=POINT_COLOR,
    markersize=POINT_SIZE,
    alpha=POINT_ALPHA,
    zorder=3
)

print(f"   Adding basemap from {BASEMAP_SOURCE.name}...")
try:
    ctx.add_basemap(ax, source=BASEMAP_SOURCE, zoom='auto')
    print("   Basemap added.")
except Exception as e:
    print(f"⚠️ Warning: Could not add basemap. Plotting without it. Error: {e}")

ax.set_title(f'Downloaded Tile Locations ({len(downloaded_points_geom)} points) for "{CITY_NAME}"')
ax.set_axis_off()
plt.tight_layout(pad=0)

# --- Save the Plot ---
try:
    plt.savefig(OUTPUT_IMAGE_FILE, dpi=DPI, bbox_inches='tight', pad_inches=0)
    print(f"\n✅ Plot successfully saved as '{OUTPUT_IMAGE_FILE}' in the current directory.")
except Exception as e:
    print(f"\n❌ Error saving plot: {e}")

# plt.show()
