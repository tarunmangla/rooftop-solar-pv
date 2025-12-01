import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np
import requests 
import os
import osmnx as ox
import time
import random
import asyncio 
import aiohttp 
import glob
import re
import sys
from tqdm import tqdm 
from tqdm.asyncio import tqdm_asyncio 

# --- CONFIGURATION ---
API_KEY = "AIzaSyAAS5r2kygbpj26WxvzndrYxI2RnTansRk"  # <--- YOUR API KEY
# Changed to specific campus name for accurate geocoding
CITY_NAME = "Indian Institute of Technology Delhi" 
ZOOM = 19
SIZE_STR = "640x640" 
TILE_SIZE_PX = 640 
MAPTYPE = "satellite"

# --- RADIUS CONFIG ---
# Reduced to 1.5 km. IIT Delhi is approx 1.3 sq km, so 1.5 km radius 
# covers the campus + immediate surroundings perfectly.
RADIUS_KM = 1.5 

# --- PERFORMANCE CONFIG ---
MAX_CONCURRENT_DOWNLOADS = 30
REQUEST_TIMEOUT = 25
MAX_BACKOFF_DELAY = 60 
MAX_RETRIES = 3 

# --- SAVE LOCATIONS ---
# Updated folder name for clarity
LOCAL_SAVE_FOLDER = "./IIT_Delhi_Tiles" 
# ----------------------------------------

async def fetch_tile(session, semaphore, args):
    """
    Asynchronously fetches a single tile using aiohttp with semaphore control.
    """
    async with semaphore: 
        i, total_to_download_count, lat, lon, local_folder = args
        tile_filepath = os.path.join(local_folder, f"tile_{i}.png")

        # Check existence
        if os.path.exists(tile_filepath):
             return "skipped_local", f"Skipped tile {i+1} (already in {os.path.basename(local_folder)})"

        center = f"{lat},{lon}"
        url = (
            f"https://maps.googleapis.com/maps/api/staticmap?"
            f"center={center}&zoom={ZOOM}&size={SIZE_STR}&maptype={MAPTYPE}&key={API_KEY}"
        )

        for attempt in range(MAX_RETRIES):
            error_message_for_retry = ""
            should_retry = False
            try:
                async with session.get(url, timeout=REQUEST_TIMEOUT) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Ensure folder exists (async safe-ish)
                        os.makedirs(local_folder, exist_ok=True)
                        with open(tile_filepath, "wb") as f:
                            f.write(content)
                        return "downloaded", f"Downloaded tile {i+1}" 

                    elif response.status in [403, 429, 500, 503]:
                        error_message_for_retry = f"Status {response.status}"
                        should_retry = True
                    else:
                        print(f"\r❌ Tile {i+1}: Failed with permanent status {response.status}. Giving up.")
                        return "failed", f"Failed tile {i+1} status {response.status}" 
            except asyncio.TimeoutError:
                error_message_for_retry = "Timed out"
                should_retry = True
            except aiohttp.ClientError as e:
                error_message_for_retry = f"Network error ({e})"
                should_retry = True
            except Exception as e:
                 print(f"\r❌ Tile {i+1}: Unexpected error: {e}. Giving up.")
                 return "failed", f"Failed tile {i+1} unexpected error: {e}" 

            if should_retry:
                wait_time = min(((2 ** attempt)) + random.random(), MAX_BACKOFF_DELAY)
                # Simple print to show retry is happening
                # print(f"\r⏳ Retry tile {i+1} in {wait_time:.1f}s...", end="")
                await asyncio.sleep(wait_time)
        
        return "failed", f"Failed tile {i+1} after {MAX_RETRIES} attempts."


def get_existing_indices(folder_path):
    """Scans a folder and returns a set of indices from tile_*.png files."""
    indices = set()
    if not os.path.isdir(folder_path):
        print(f"ℹ️ Directory not found or skipped checking: '{folder_path}'")
        return indices
    print(f"🔍 Scanning '{folder_path}' for existing tiles...")
    search_pattern = os.path.join(folder_path, "tile_*.png")
    existing_files = glob.glob(search_pattern)
    tile_pattern = re.compile(r"tile_(\d+)\.png$")
    count = 0
    for f_path in tqdm(existing_files, desc=f"Scanning {os.path.basename(folder_path)}", leave=False, ncols=100):
        match = tile_pattern.search(os.path.basename(f_path))
        if match:
            try:
                indices.add(int(match.group(1)))
                count += 1
            except ValueError: pass
    print(f"✅ Found {count} valid tiles in '{os.path.basename(folder_path)}'.")
    return indices


async def main():
    os.makedirs(LOCAL_SAVE_FOLDER, exist_ok=True)

    # --- CHANGED: Radius Logic Starts Here ---
    print(f"🌍 Locating center point for: {CITY_NAME}")
    try:
        # 1. Get Center Point
        center_lat, center_lon = ox.geocode(CITY_NAME)
        print(f"✅ Found center at: {center_lat:.5f}, {center_lon:.5f}")
    except Exception as e:
        print(f"❌ Error locating city: {e}")
        print("⚠️ Attempting fallback coordinates for IIT Delhi...")
        # Fallback to hardcoded IIT Delhi coordinates if OSM fails
        center_lat, center_lon = 28.5450, 77.1926
        print(f"✅ Using fallback center at: {center_lat:.5f}, {center_lon:.5f}")

    print(f"📐 Creating {RADIUS_KM} km radius buffer around the center...")
    
    # 2. Create Buffer (Circle)
    # Create a Point in WGS84
    df_point = gpd.GeoDataFrame(geometry=[Point(center_lon, center_lat)], crs="EPSG:4326")
    # Project to Meters (EPSG:3857) to do distance calculation
    df_projected = df_point.to_crs(epsg=3857)
    # Buffer by Radius in Meters
    circle_geometry = df_projected.buffer(RADIUS_KM * 1000)
    # Project back to Lat/Lon (EPSG:4326)
    gdf_boundary = gpd.GeoDataFrame(geometry=circle_geometry, crs="EPSG:3857").to_crs(epsg=4326)
    
    # Get the polygon from the GDF
    polygon = gdf_boundary.geometry.iloc[0]
    minx, miny, maxx, maxy = polygon.bounds
    
    print(f"✅ Created Circular Boundary covering ~{int(gdf_boundary.to_crs(epsg=3857).area.iloc[0] / 1e6)} sq km.")
    # --- END Radius Logic ---

    # --- Calculate Disjoint Step Size ---
    print("Calculating tile step size based on latitude...")
    avg_lat = (miny + maxy) / 2
    avg_lat_rad = np.radians(avg_lat)
    meters_per_pixel = (156543.03 * np.cos(avg_lat_rad)) / (2**ZOOM)
    tile_size_meters = TILE_SIZE_PX * meters_per_pixel
    STEP_Y_DEGREES = tile_size_meters / 111320.0
    STEP_X_DEGREES = tile_size_meters / (111320.0 * np.cos(avg_lat_rad))
    
    half_step_x = STEP_X_DEGREES / 2
    half_step_y = STEP_Y_DEGREES / 2

    print(f"   Tile size: ~{tile_size_meters:.2f} meters")
    print(f"   Calculated Step Y (Lat): {STEP_Y_DEGREES:.6f} degrees")
    print(f"   Calculated Step X (Lon): {STEP_X_DEGREES:.6f} degrees")
    # --- END STEP CALCALCULATION ---

    # --- Generate All Potential Points ---
    print("🔍 Calculating all potential tile locations (using INTERSECTS)...")
    potential_points_map = {}
    x_vals = np.arange(minx, maxx, STEP_X_DEGREES)
    y_vals = np.arange(miny, maxy, STEP_Y_DEGREES)
    current_index = 0
    total_grid_points = len(x_vals) * len(y_vals)
    
    print(f"   Grid dimensions: {len(x_vals)} (lon) x {len(y_vals)} (lat) = {total_grid_points} total grid points")

    with tqdm(total=total_grid_points, desc="Generating Points", ncols=100) as pbar_points:
        for lat in y_vals:
            for lon in x_vals:
                pbar_points.update(1)
                
                min_lon, max_lon = lon - half_step_x, lon + half_step_x
                min_lat, max_lat = lat - half_step_y, lat + half_step_y
                tile_box = Polygon([
                    (min_lon, min_lat), (min_lon, max_lat),
                    (max_lon, max_lat), (max_lon, min_lat)
                ])
                
                # Check intersection with our Circle Polygon
                if polygon.intersects(tile_box):
                    potential_points_map[current_index] = (lat, lon)
                    current_index += 1

    total_potential_tiles = len(potential_points_map)
    print(f"✅ Calculated {total_potential_tiles} potential tile locations inside the {RADIUS_KM}km radius.")
    if total_potential_tiles == 0: sys.exit()

    # --- Pre-Check Existing Files ---
    all_existing_indices = get_existing_indices(LOCAL_SAVE_FOLDER)
    print(f"✅ Total unique existing tiles found in '{LOCAL_SAVE_FOLDER}': {len(all_existing_indices)}")

    # --- Create List of Tasks ---
    tasks_to_run = []
    print("📝 Creating list of tiles to download...")
    for index, (lat, lon) in potential_points_map.items():
        if index not in all_existing_indices:
            tasks_to_run.append((index, 0, lat, lon, LOCAL_SAVE_FOLDER))

    total_to_download_count = len(tasks_to_run)
    if total_to_download_count == 0:
        print("\n✅ No new tiles need to be downloaded.")
        sys.exit()

    tasks_to_run = [(t[0], total_to_download_count, t[2], t[3], t[4]) for t in tasks_to_run]
    print(f"🎯 Need to download {total_to_download_count} new tiles.")
    print(f"💾 Downloads will be saved to local folder: '{LOCAL_SAVE_FOLDER}'")

    # --- Run Async Downloads ---
    print(f"\n🚀 Starting async download using up to {MAX_CONCURRENT_DOWNLOADS} concurrent connections...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    download_count = 0; fail_count = 0; skip_local_count = 0

    async with aiohttp.ClientSession() as session:
        coroutines = [fetch_tile(session, semaphore, task) for task in tasks_to_run]
        for future in tqdm_asyncio(asyncio.as_completed(coroutines), total=total_to_download_count, desc="Downloading Tiles", ncols=100):
            try:
                result = await future
                if isinstance(result, tuple) and len(result) == 2:
                    status, message = result
                    if status == "downloaded": download_count += 1
                    elif status == "failed": fail_count += 1; print(message)
                    elif status == "skipped_local": skip_local_count += 1
                else: fail_count += 1; print(f"❗️ Unexpected result: {result}")
            except Exception as exc:
                fail_count += 1; print(f"❗️ Task processing error: {exc}")

    # --- Final Summary ---
    print("\n🎉 Async processing complete!")
    print(f"--- Summary ---")
    print(f"Total potential tiles for '{CITY_NAME}': {total_potential_tiles}")
    print(f"Tiles needed: {total_to_download_count}")
    print(f"Tiles successfully downloaded: {download_count}")
    print(f"Tiles skipped (local): {skip_local_count}")
    print(f"Tiles failed: {fail_count}")
    print(f"-------------")
    if fail_count > 0: print(f"⚠️ Note: {fail_count} tiles failed.")
    print(f"✅ All downloaded tiles are in: '{LOCAL_SAVE_FOLDER}'")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())