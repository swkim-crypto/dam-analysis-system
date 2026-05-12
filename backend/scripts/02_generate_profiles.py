#!/usr/bin/env python3
"""
Generate profiles.js - Cross and Longitudinal Profiles
For each dam site, extract elevation profiles from DEM
"""

import json
import numpy as np
import rasterio
from rasterio.transform import rowcol
from scipy.interpolate import interp1d
import warnings
warnings.filterwarnings('ignore')

print("="*60)
print("Generating profiles.js")
print("="*60)

# Load candidates from GeoJSON (more reliable)
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

print(f"DEM: {dem.width}x{dem.height}, Resolution: {dem.res[0]:.6f}°")

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

def extract_cross_profile(lon, lat, width=6000, sampling=30):
    """
    Extract cross profile perpendicular to river
    Simplified: E-W transect
    """
    # Convert width from meters to degrees (rough)
    half_width_deg = (width / 2) / 111000
    sampling_deg = sampling / 111000
    
    profile = []
    
    # Sample from west to east
    num_samples = int(width / sampling)
    
    for i in range(num_samples + 1):
        # Distance from center (-3000m to +3000m)
        distance = (i * sampling) - (width / 2)
        
        # Longitude offset (E-W direction)
        sample_lon = lon + (distance / 111000)
        
        # Get elevation
        elev = get_elevation(sample_lon, lat)
        
        if elev is not None:
            profile.append({
                "d": int(distance),
                "elev": round(elev, 1)
            })
    
    return profile

def extract_long_profile(lon, lat, length=70000, sampling=200):
    """
    Extract longitudinal profile upstream
    Simplified: assumes northward flow
    """
    # Convert to degrees
    sampling_deg = sampling / 111000
    
    profile = []
    
    # Start from dam location (d=0)
    num_samples = int(length / sampling)
    
    for i in range(num_samples + 1):
        # Distance upstream (0 to 70km)
        distance = i * sampling
        
        # Latitude offset (assume upstream = north)
        # In reality, should follow actual river path
        sample_lat = lat + (distance / 111000)
        
        # Get elevation
        elev = get_elevation(lon, sample_lat)
        
        if elev is not None:
            profile.append({
                "d": int(distance),
                "elev": round(elev, 1)
            })
    
    return profile

# Generate profiles for all sites
profiles = {}

print("\nGenerating profiles...")
total = len(candidates)

for idx, candidate in enumerate(candidates):
    site_id = candidate['id']
    lon = candidate['lon']
    lat = candidate['lat']
    
    print(f"  [{idx+1}/{total}] {site_id}...", end='\r')
    
    # Cross profile
    cross = extract_cross_profile(lon, lat, width=6000, sampling=30)
    
    # Longitudinal profile
    long = extract_long_profile(lon, lat, length=70000, sampling=200)
    
    # Store
    profiles[site_id] = {
        "cross": cross,
        "long": long
    }

print(f"\n✓ Generated profiles for {len(profiles)} sites")

# Save as JavaScript
print("\nSaving profiles.js...")

output = "export const profiles = {\n"

for site_id, data in profiles.items():
    output += f'  "{site_id}": {{\n'
    
    # Cross section
    output += '    "cross": [\n'
    for i, point in enumerate(data['cross']):
        comma = ',' if i < len(data['cross']) - 1 else ''
        output += f'      {{"d": {point["d"]}, "elev": {point["elev"]}}}{comma}\n'
    output += '    ],\n'
    
    # Longitudinal section
    output += '    "long": [\n'
    for i, point in enumerate(data['long']):
        comma = ',' if i < len(data['long']) - 1 else ''
        output += f'      {{"d": {point["d"]}, "elev": {point["elev"]}}}{comma}\n'
    output += '    ]\n'
    
    output += '  },\n'

output += "};\n"

with open('output/profiles.js', 'w') as f:
    f.write(output)

print(f"✓ Saved: output/profiles.js")

# Statistics
total_cross_points = sum(len(p['cross']) for p in profiles.values())
total_long_points = sum(len(p['long']) for p in profiles.values())

print(f"\nProfile Statistics:")
print(f"  Total cross profile points: {total_cross_points:,}")
print(f"  Total long profile points: {total_long_points:,}")
print(f"  Avg cross points per site: {total_cross_points // len(profiles)}")
print(f"  Avg long points per site: {total_long_points // len(profiles)}")

print("\n" + "="*60)
print("profiles.js generation complete!")
print("="*60)
