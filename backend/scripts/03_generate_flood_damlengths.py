#!/usr/bin/env python3
"""
Generate floodPolygons.js and damLengths.js
For each dam site and height, calculate:
- Flood polygon (inundation area)
- Dam length (distance between valley walls at FSL)
"""

import json
import numpy as np
import rasterio
from rasterio.transform import rowcol, xy
from rasterio.features import shapes
from scipy.ndimage import binary_fill_holes
from shapely.geometry import shape, mapping
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("Generating floodPolygons.js and damLengths.js")
print("="*60)

# Load candidates from GeoJSON
with open('output/dam_sites.geojson', 'r') as f:
    geojson = json.load(f)

candidates = []
for feature in geojson['features']:
    props = feature['properties']
    coords = feature['geometry']['coordinates']
    candidates.append({
        'id': props['id'],
        'lon': coords[0],
        'lat': coords[1],
        'bed': props['bed_elev']
    })

print(f"\nLoaded {len(candidates)} candidate sites")

# Load DEM
dem_path = 'data/dem/#Uc720#Uc5eddem.tif'
dem = rasterio.open(dem_path)
dem_array = dem.read(1)
dem_array = np.where(dem_array == dem.nodata, np.nan, dem_array)

print(f"DEM: {dem.width}x{dem.height}")

# Load profiles for dam length calculation
with open('output/profiles.js', 'r') as f:
    content = f.read()
    # Simple parsing - extract the dictionary
    # This is a simplified approach
    profiles_data = {}

def get_elevation(lon, lat):
    """Extract elevation from DEM"""
    try:
        row, col = rowcol(dem.transform, lon, lat)
        if 0 <= row < dem.height and 0 <= col < dem.width:
            elev = dem_array[row, col]
            if not np.isnan(elev):
                return float(elev)
    except:
        pass
    return None

def calculate_flood_polygon(lon, lat, fsl, buffer_km=10):
    """
    Generate flood polygon using flood-fill algorithm
    Simplified version: create polygon from DEM raster
    """
    try:
        # Convert buffer from km to degrees (rough)
        buffer_deg = buffer_km / 111
        
        # Get DEM subset around dam site
        min_lon = lon - buffer_deg
        max_lon = lon + buffer_deg
        min_lat = lat - buffer_deg
        max_lat = lat + buffer_deg
        
        # Get window in pixel coordinates
        row_start, col_start = rowcol(dem.transform, min_lon, max_lat)
        row_end, col_end = rowcol(dem.transform, max_lon, min_lat)
        
        row_start = max(0, row_start)
        row_end = min(dem.height, row_end)
        col_start = max(0, col_start)
        col_end = min(dem.width, col_end)
        
        # Extract subset
        subset = dem_array[row_start:row_end, col_start:col_end]
        
        # Create flood mask (areas below FSL)
        flood_mask = subset <= fsl
        
        # Fill holes
        filled_mask = binary_fill_holes(flood_mask)
        
        # Convert to polygon
        # Get the transform for the subset
        subset_transform = rasterio.transform.from_bounds(
            min_lon, min_lat, max_lon, max_lat,
            col_end - col_start, row_end - row_start
        )
        
        # Extract shapes
        polygons = []
        for geom, value in shapes(filled_mask.astype(np.uint8), transform=subset_transform):
            if value == 1:  # Flooded area
                polygons.append(shape(geom))
        
        if not polygons:
            return None
        
        # Merge all polygons
        from shapely.ops import unary_union
        merged = unary_union(polygons)
        
        # Simplify
        simplified = merged.simplify(0.001, preserve_topology=True)
        
        # Convert to GeoJSON format
        geom = mapping(simplified)
        
        return geom
    
    except Exception as e:
        print(f"    Warning: Failed to generate polygon - {e}")
        return None

def calculate_dam_length_from_profile(cross_profile, fsl):
    """
    Calculate dam length from cross profile
    Find intersection points where profile crosses FSL
    """
    if not cross_profile or len(cross_profile) < 2:
        return None
    
    # Extract distances and elevations
    distances = [p['d'] for p in cross_profile]
    elevations = [p['elev'] for p in cross_profile]
    
    # Find points above FSL
    above_fsl = [i for i, e in enumerate(elevations) if e > fsl]
    
    if not above_fsl:
        return None  # All points below FSL
    
    # Find leftmost and rightmost points above FSL
    left_idx = above_fsl[0]
    right_idx = above_fsl[-1]
    
    # Get the crossing points (linear interpolation)
    left_cross = None
    right_cross = None
    
    # Left crossing (from valley floor to hillside)
    if left_idx > 0:
        # Interpolate between left_idx-1 and left_idx
        d1, e1 = distances[left_idx-1], elevations[left_idx-1]
        d2, e2 = distances[left_idx], elevations[left_idx]
        if e1 <= fsl <= e2:
            # Linear interpolation
            ratio = (fsl - e1) / (e2 - e1) if e2 != e1 else 0
            left_cross = d1 + ratio * (d2 - d1)
    
    # Right crossing (from hillside to valley floor)
    if right_idx < len(distances) - 1:
        # Interpolate between right_idx and right_idx+1
        d1, e1 = distances[right_idx], elevations[right_idx]
        d2, e2 = distances[right_idx+1], elevations[right_idx+1]
        if e1 >= fsl >= e2:
            # Linear interpolation
            ratio = (fsl - e1) / (e2 - e1) if e2 != e1 else 0
            right_cross = d1 + ratio * (d2 - d1)
    
    # If we couldn't interpolate, use the boundary points
    if left_cross is None:
        left_cross = distances[left_idx]
    if right_cross is None:
        right_cross = distances[right_idx]
    
    # Dam length is the distance between crossings
    dam_length = abs(right_cross - left_cross)
    
    return dam_length

# Load profiles for dam length
print("\nLoading profiles for dam length calculation...")
profiles = {}
try:
    with open('output/profiles.js', 'r') as f:
        content = f.read()
        # Extract the profiles object (simplified parsing)
        # We'll re-read from a JSON-like format
        import re
        
        # Find each site's cross profile
        for candidate in candidates:
            site_id = candidate['id']
            
            # Find the cross section for this site
            pattern = f'"{site_id}".*?"cross":\s*\[(.*?)\]'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                cross_str = '[' + match.group(1) + ']'
                # Convert to valid JSON
                cross_str = cross_str.replace("'", '"')
                try:
                    cross_data = json.loads(cross_str)
                    profiles[site_id] = {'cross': cross_data}
                except:
                    profiles[site_id] = {'cross': []}
            else:
                profiles[site_id] = {'cross': []}
    
    print(f"✓ Loaded profiles for {len(profiles)} sites")
except Exception as e:
    print(f"⚠️  Warning: Could not load profiles - {e}")
    profiles = {c['id']: {'cross': []} for c in candidates}

# Generate flood polygons and dam lengths
flood_polygons = {}
dam_lengths = {}

heights = [40, 50, 60, 70, 80, 90, 100, 110, 120]

print(f"\nGenerating flood polygons and dam lengths...")
print(f"Heights: {heights}")

total = len(candidates) * len(heights)
count = 0

for candidate in candidates:
    site_id = candidate['id']
    lon = candidate['lon']
    lat = candidate['lat']
    bed = candidate['bed']
    
    flood_polygons[site_id] = {}
    dam_lengths[site_id] = {}
    
    cross_profile = profiles.get(site_id, {}).get('cross', [])
    
    for height in heights:
        count += 1
        fsl = bed + height
        
        print(f"  [{count}/{total}] {site_id} @ H={height}m (FSL={fsl:.0f}m)...", end='\r')
        
        # Generate flood polygon
        polygon = calculate_flood_polygon(lon, lat, fsl, buffer_km=15)
        if polygon:
            flood_polygons[site_id][str(height)] = polygon
        else:
            flood_polygons[site_id][str(height)] = None
        
        # Calculate dam length
        if cross_profile:
            dam_length = calculate_dam_length_from_profile(cross_profile, fsl)
            dam_lengths[site_id][str(height)] = int(dam_length) if dam_length else None
        else:
            dam_lengths[site_id][str(height)] = None

print(f"\n✓ Generated flood polygons and dam lengths for {len(candidates)} sites")

# Save floodPolygons.js
print("\nSaving floodPolygons.js...")

output = "export const floodPolygons = {\n"

for site_id, heights_data in flood_polygons.items():
    output += f'  "{site_id}": {{\n'
    
    for i, (height, polygon) in enumerate(heights_data.items()):
        comma = ',' if i < len(heights_data) - 1 else ''
        if polygon:
            polygon_json = json.dumps(polygon, separators=(',', ': '))
            output += f'    "{height}": {polygon_json}{comma}\n'
        else:
            output += f'    "{height}": null{comma}\n'
    
    output += '  },\n'

output += "};\n"

with open('output/floodPolygons.js', 'w') as f:
    f.write(output)

print(f"✓ Saved: output/floodPolygons.js")

# Save damLengths.js
print("\nSaving damLengths.js...")

output = "export const damLengths = {\n"

for site_id, heights_data in dam_lengths.items():
    output += f'  "{site_id}": {{\n'
    
    for i, (height, length) in enumerate(heights_data.items()):
        comma = ',' if i < len(heights_data) - 1 else ''
        output += f'    "{height}": {length}{comma}\n'
    
    output += '  },\n'

output += "};\n"

with open('output/damLengths.js', 'w') as f:
    f.write(output)

print(f"✓ Saved: output/damLengths.js")

# Statistics
valid_polygons = sum(1 for site in flood_polygons.values() for p in site.values() if p is not None)
valid_lengths = sum(1 for site in dam_lengths.values() for l in site.values() if l is not None)

total_entries = len(candidates) * len(heights)

print(f"\nStatistics:")
print(f"  Total entries: {total_entries}")
print(f"  Valid flood polygons: {valid_polygons} ({valid_polygons*100//total_entries}%)")
print(f"  Valid dam lengths: {valid_lengths} ({valid_lengths*100//total_entries}%)")

print("\n" + "="*60)
print("floodPolygons.js and damLengths.js generation complete!")
print("="*60)
