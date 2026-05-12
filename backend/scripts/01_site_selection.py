#!/usr/bin/env python3
"""
Dam Site Selection Analysis - Main Script
Nam Ngiep Basin, Laos

Author: Dam Analysis System
Date: 2024
"""

import os
import sys
import yaml
import json
import numpy as np
import rasterio
from rasterio.transform import rowcol, xy
from rasterio.warp import transform_geom
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import linemerge, nearest_points
from scipy.ndimage import binary_fill_holes
from scipy.interpolate import interp1d
from scipy.integrate import trapezoid
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("Dam Site Selection Analysis System")
print("Nam Ngiep Basin, Laos")
print("="*60)

# Load configuration
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("\n[1/8] Loading data...")

# Load DEM
dem_path = config['paths']['dem']
dem = rasterio.open(dem_path)
dem_array = dem.read(1)
dem_array = np.where(dem_array == dem.nodata, np.nan, dem_array)

print(f"✓ DEM loaded: {dem.width}x{dem.height}, CRS: {dem.crs}")

# Load rivers
import glob
rivers_path = config['paths']['rivers']
if os.path.isdir(rivers_path):
    # 폴더인 경우 .shp 파일 찾기
    shp_files = glob.glob(os.path.join(rivers_path, "*.shp"))
    if shp_files:
        rivers_gdf = gpd.read_file(shp_files[0])
    else:
        raise FileNotFoundError("No .shp file found in rivers directory")
else:
    rivers_gdf = gpd.read_file(rivers_path)

print(f"✓ Rivers loaded: {len(rivers_gdf)} segments, CRS: {rivers_gdf.crs}")

# Load boundary
boundary_gdf = gpd.read_file(config['paths']['boundary'])
print(f"✓ Boundary loaded: {len(boundary_gdf)} features")

# CRS transformation
print("\n[2/8] Coordinate system transformation...")
working_crs = config['crs']['working_crs']
output_crs = config['crs']['output_crs']

# Transform DEM CRS metadata (for coordinate conversion)
# Note: We'll work in DEM's native coordinates and convert points later
print(f"✓ Working CRS: {working_crs}")
print(f"✓ Output CRS: {output_crs}")

# Transform rivers to WGS84 for processing
rivers_wgs84 = rivers_gdf.to_crs(output_crs)

print("\n[3/8] Filtering rivers...")

# Filter rivers by criteria
rc = config['river_filters']

# Convert DSContArea from m² to km²
rivers_wgs84['DSContArea_km2'] = rivers_wgs84['DSContArea'] / 1e6

filtered_rivers = rivers_wgs84[
    (rivers_wgs84['Order'] >= rc['min_order']) &
    (rivers_wgs84['Order'] <= rc['max_order']) &
    (rivers_wgs84['DSContArea'] >= rc['min_drainage_area_m2']) &
    (rivers_wgs84['DSContArea'] <= rc['max_drainage_area_m2']) &
    (rivers_wgs84['Slope'] >= rc['min_slope']) &
    (rivers_wgs84['Slope'] <= rc['max_slope'])
].copy()

print(f"✓ Filtered rivers: {len(filtered_rivers)} / {len(rivers_wgs84)} segments")
print(f"  Order {rc['min_order']}-{rc['max_order']}: {len(filtered_rivers[filtered_rivers['Order'].between(rc['min_order'], rc['max_order'])])}")
print(f"  Drainage area: {rc['min_drainage_area_m2']/1e6:.0f}-{rc['max_drainage_area_m2']/1e6:.0f} km²")

if len(filtered_rivers) == 0:
    print("❌ No rivers meet the criteria!")
    sys.exit(1)

print("\n[4/8] Generating candidate points...")

# Generate points along rivers
sc = config['spatial_criteria']
search_interval = sc['search_interval']

candidate_points = []

for idx, river in filtered_rivers.iterrows():
    geom = river.geometry
    
    # Handle MULTILINESTRING
    if geom.geom_type == 'MultiLineString':
        line = linemerge(geom)
        if line.geom_type == 'MultiLineString':
            # Take longest segment
            lines = list(line.geoms)
            line = max(lines, key=lambda x: x.length)
    else:
        line = geom
    
    # Generate points along line
    length = line.length
    num_points = int(length / (search_interval / 111000))  # rough conversion to degrees
    
    if num_points < 1:
        continue
    
    for i in range(num_points):
        distance = i * (search_interval / 111000)
        if distance > length:
            break
        
        point = line.interpolate(distance)
        
        candidate_points.append({
            'geometry': point,
            'river_id': river['LINKNO'],
            'order': river['Order'],
            'drainage_area_km2': river['DSContArea_km2'],
            'slope': river['Slope']
        })

print(f"✓ Generated {len(candidate_points)} candidate points")

# Convert to GeoDataFrame
candidates_gdf = gpd.GeoDataFrame(candidate_points, crs=output_crs)

print("\n[5/8] Extracting elevation at candidate points...")

# Extract elevation from DEM
def get_elevation(lon, lat, dem, dem_array):
    """Extract elevation from DEM at given coordinates"""
    try:
        row, col = rowcol(dem.transform, lon, lat)
        if 0 <= row < dem.height and 0 <= col < dem.width:
            elev = dem_array[row, col]
            if not np.isnan(elev):
                return float(elev)
    except:
        pass
    return None

candidates_gdf['bed_elev'] = candidates_gdf.geometry.apply(
    lambda p: get_elevation(p.x, p.y, dem, dem_array)
)

# Remove points without elevation
candidates_gdf = candidates_gdf[candidates_gdf['bed_elev'].notna()].copy()
print(f"✓ {len(candidates_gdf)} points with valid elevation")

print("\n[6/8] Analyzing dam sites...")

# Extract cross profiles and check valley shape
tc = config['terrain_criteria']
dc = config['dam_criteria']

def extract_cross_profile(lon, lat, dem, dem_array, width=6000, sampling=30):
    """Extract cross profile perpendicular to flow direction"""
    # Simplified: extract E-W profile
    # In production, should use actual flow direction
    
    half_width_deg = (width / 2) / 111000  # rough conversion
    
    lons = np.arange(lon - half_width_deg, lon + half_width_deg, sampling / 111000)
    elevs = []
    distances = []
    
    for i, sample_lon in enumerate(lons):
        elev = get_elevation(sample_lon, lat, dem, dem_array)
        if elev is not None:
            distances.append((sample_lon - lon) * 111000)  # convert to meters
            elevs.append(elev)
    
    return distances, elevs

def calculate_valley_narrowness(distances, elevs, bed_elev, target_height=60):
    """Calculate valley narrowness ratio"""
    if len(distances) < 10:
        return None
    
    fsl = bed_elev + target_height
    
    # Find valley width at FSL
    above_fsl = np.array(elevs) > fsl
    if not any(above_fsl):
        return None  # FSL above all terrain
    
    # Find left and right intersection
    left_idx = None
    right_idx = None
    
    for i in range(len(elevs) - 1):
        if elevs[i] <= fsl and elevs[i+1] > fsl:
            left_idx = i
        if elevs[i] > fsl and elevs[i+1] <= fsl:
            right_idx = i
            break
    
    if left_idx is None or right_idx is None:
        return None
    
    valley_width = abs(distances[right_idx] - distances[left_idx])
    valley_depth = target_height
    narrowness = valley_width / valley_depth if valley_depth > 0 else 999
    
    return narrowness, valley_width

# Analyze each candidate
results = []
total = len(candidates_gdf)
print_interval = max(1, total // 20)

for idx, candidate in candidates_gdf.iterrows():
    if idx % print_interval == 0:
        print(f"  Progress: {idx}/{total} ({idx*100//total}%)", end='\r')
    
    lon, lat = candidate.geometry.x, candidate.geometry.y
    bed_elev = candidate['bed_elev']
    
    # Extract cross profile
    distances, elevs = extract_cross_profile(lon, lat, dem, dem_array)
    
    if len(distances) < 10:
        continue
    
    # Check for suitable dam heights
    best_height = None
    best_volume = 0
    best_dam_length = None
    
    for height in range(dc['height_min'], dc['height_max'] + 1, dc['height_step']):
        # Calculate valley properties
        valley_info = calculate_valley_narrowness(distances, elevs, bed_elev, height)
        
        if valley_info is None:
            continue
        
        narrowness, valley_width = valley_info
        
        # Check constraints
        if narrowness > dc['valley_narrowness_max']:
            continue
        
        if valley_width > dc['max_dam_length']:
            continue
        
        # Estimate volume (simplified - use cross-sectional area * upstream length)
        # In production, use proper flood-fill algorithm
        fsl = bed_elev + height
        
        # Cross-sectional area
        elevs_array = np.array(elevs)
        depths = np.maximum(fsl - elevs_array, 0)
        cross_area = trapezoid(depths, distances) if len(depths) > 1 else 0
        
        # Estimate volume (very rough)
        # Assume reservoir extends 10km upstream with similar cross-section
        reservoir_length = 10000  # 10km
        volume_m3 = cross_area * reservoir_length * 0.5  # tapering factor
        volume_mm3 = volume_m3 / 1e6
        
        # Check if meets minimum volume
        if volume_mm3 >= dc['min_volume_mm3']:
            if volume_mm3 > best_volume:
                best_height = height
                best_volume = volume_mm3
                best_dam_length = valley_width
    
    # If found suitable height
    if best_height is not None:
        results.append({
            'lat': lat,
            'lon': lon,
            'bed': bed_elev,
            'height': best_height,
            'volume': best_volume,
            'dam_length': best_dam_length,
            'order': candidate['order'],
            'drainage_area_km2': candidate['drainage_area_km2']
        })

print(f"\n✓ Found {len(results)} suitable dam sites")

if len(results) == 0:
    print("\n❌ No sites meet all criteria. Try relaxing constraints.")
    print("\nSuggestions:")
    print("  - Increase max_dam_length")
    print("  - Increase valley_narrowness_max")
    print("  - Decrease min_volume_mm3")
    print("  - Expand stream order range")
    sys.exit(1)

print("\n[7/8] Removing duplicate sites...")

# Sort by volume (descending)
results_sorted = sorted(results, key=lambda x: x['volume'], reverse=True)

# Remove sites too close to each other
min_distance = sc['min_distance_between_sites'] / 111000  # rough conversion to degrees
final_results = []

for result in results_sorted:
    too_close = False
    result_point = Point(result['lon'], result['lat'])
    
    for existing in final_results:
        existing_point = Point(existing['lon'], existing['lat'])
        distance = result_point.distance(existing_point)
        
        if distance < min_distance:
            too_close = True
            break
    
    if not too_close:
        final_results.append(result)

print(f"✓ {len(final_results)} unique sites after removing duplicates")

# Assign IDs
for i, result in enumerate(final_results):
    result['id'] = f"S{i+1}"

print("\n[8/8] Saving results...")

# Create output directory
output_dir = config['paths']['output_dir']
os.makedirs(output_dir, exist_ok=True)

# Save GeoJSON
if config['output']['export_geojson']:
    features = []
    for r in final_results:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [r['lon'], r['lat']]
            },
            'properties': {
                'id': r['id'],
                'bed_elev': round(r['bed'], 1),
                'height_m': r['height'],
                'volume_mm3': round(r['volume'], 2),
                'dam_length_m': round(r['dam_length'], 0),
                'stream_order': r['order'],
                'drainage_area_km2': round(r['drainage_area_km2'], 1)
            }
        })
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    with open(f'{output_dir}/dam_sites.geojson', 'w') as f:
        json.dump(geojson, f, indent=2)
    print(f"✓ Saved: dam_sites.geojson")

# Save CSV
if config['output']['export_csv']:
    import csv
    with open(f'{output_dir}/dam_sites.csv', 'w', newline='') as f:
        fieldnames = ['id', 'lat', 'lon', 'bed_elev', 'height_m', 'volume_mm3', 
                      'dam_length_m', 'stream_order', 'drainage_area_km2']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in final_results:
            writer.writerow({
                'id': r['id'],
                'lat': round(r['lat'], 5),
                'lon': round(r['lon'], 5),
                'bed_elev': round(r['bed'], 1),
                'height_m': r['height'],
                'volume_mm3': round(r['volume'], 2),
                'dam_length_m': round(r['dam_length'], 0),
                'stream_order': r['order'],
                'drainage_area_km2': round(r['drainage_area_km2'], 1)
            })
    print(f"✓ Saved: dam_sites.csv")

# Save candidates.js
if config['output']['export_js']:
    js_output = "export const candidates = [\n"
    for r in final_results:
        js_output += "  {\n"
        js_output += f"    id: '{r['id']}',\n"
        js_output += f"    lat: {r['lat']:.5f},\n"
        js_output += f"    lon: {r['lon']:.5f},\n"
        js_output += f"    bed: {r['bed']:.0f},\n"
        js_output += f"    region: 'Nam Ngiep Basin',\n"
        js_output += f"    priority: '검토필요',\n"
        js_output += f"    baseFsl: {r['bed'] + r['height']:.0f},\n"
        js_output += f"    baseH: {r['height']},\n"
        js_output += f"    baseV: {r['volume']:.1f},\n"
        js_output += f"    baseArea: 0,  // To be calculated\n"
        js_output += f"    damLength: {r['dam_length']:.0f},\n"
        js_output += f"    streamOrder: {r['order']},\n"
        js_output += f"    drainageArea: {r['drainage_area_km2']:.1f},\n"
        js_output += f"    hMin5: {r['height']},\n"
        js_output += f"    note: 'Auto-generated candidate site'\n"
        js_output += "  },\n"
    js_output += "];\n"
    
    with open(f'{output_dir}/candidates.js', 'w') as f:
        f.write(js_output)
    print(f"✓ Saved: candidates.js")

print("\n" + "="*60)
print("Analysis Complete!")
print("="*60)
print(f"\nFound {len(final_results)} dam sites:")
for r in final_results:
    print(f"  {r['id']}: {r['lat']:.4f}, {r['lon']:.4f} - " +
          f"{r['volume']:.1f} Mm³ at H={r['height']}m (L={r['dam_length']:.0f}m)")

print(f"\nOutput files saved to: {output_dir}/")
print("  - dam_sites.geojson")
print("  - dam_sites.csv")
print("  - candidates.js")
print("\nNext steps:")
print("  1. Review results in QGIS using dam_sites.geojson")
print("  2. Run detailed analysis: python 02_generate_profiles.py")
print("  3. Visualize in web app using candidates.js")
