from fastapi import APIRouter
import geopandas as gpd
import pandas as pd
import os
import json

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "Data")
SHP_PATH = os.path.join(DATA_DIR, "HK_District", "HKDistrict18.shp")
POP_CSV_PATH = os.path.join(DATA_DIR, "Population_Census_2021.CSV")
ELDERLY_CSV_PATH = os.path.join(DATA_DIR, "LocationofResidentialCareHomesfortheElderlyinHongKong_cleaned.csv")

@router.get("/geojson")
def get_geojson():
    """
    Returns the HK Districts GeoJSON with pre-calculated Capacity Gap (Static).
    """
    try:
        # Load Shapefile and project to WGS84 for Mapbox
        gdf = gpd.read_file(SHP_PATH)
        if gdf.crs is None or gdf.crs.to_string() != 'EPSG:4326':
            gdf = gdf.to_crs(epsg=4326)

        # Load Population Data
        df_pop = pd.read_csv(POP_CSV_PATH, header=4)
        df_pop = df_pop.dropna(subset=['dc_eng'])
        
        # Load all 6 facility types instead of just Elderly Homes
        import glob
        csv_files = glob.glob(os.path.join(DATA_DIR, "*_cleaned.csv"))
        all_facilities = []
        for file in csv_files:
            df = pd.read_csv(file)
            df = df.dropna(subset=['Latitude', 'Longitude'])
            all_facilities.append(df)
            
        df_all = pd.concat(all_facilities, ignore_index=True)
        gdf_all_facilities = gpd.GeoDataFrame(
            df_all, geometry=gpd.points_from_xy(df_all.Longitude, df_all.Latitude), crs="EPSG:4326"
        )
        
        # Spatial Join to count all facilities per district
        sj = gpd.sjoin(gdf_all_facilities, gdf, how="inner", predicate="intersects")
        fac_counts = sj.groupby('index_right').size()
        gdf['RCHE_Count'] = fac_counts
        gdf['RCHE_Count'] = gdf['RCHE_Count'].fillna(0)

        # Merge Population
        def match_population(row):
            district_name = str(row.get('ENAME', '')).upper().replace('&', 'AND')
            for idx, pop_row in df_pop.iterrows():
                pop_district = str(pop_row['dc_eng']).upper().replace('&', 'AND')
                if pop_district in district_name or district_name in pop_district:
                    return pd.Series({
                        'pop_總人數': pop_row['t_pop'],
                        'pop_65歲以上': pop_row['age_5']
                    })
            return pd.Series({
                'pop_總人數': 0,
                'pop_65歲以上': 0
            })
            
        merged = gdf.apply(match_population, axis=1)
        gdf = pd.concat([gdf, merged], axis=1)
        
        # Real-time computed index based on ACTUAL spatial join!
        # Severity Index = Elderly Population / Total Count of Facilities
        # Meaning: "How many elderly people share one facility in this district?"
        def calculate_severity(row):
            pop_65 = float(row['pop_65歲以上']) if pd.notnull(row['pop_65歲以上']) else 0
            homes_count = int(row['RCHE_Count'])
            if pop_65 == 0: return 0
            # Higher number = more people per home = worse shortage
            return pop_65 / max(1, homes_count)
            
        gdf['Gap_Index'] = gdf.apply(calculate_severity, axis=1)
        
        # Convert to GeoJSON string and parse back to dict
        geojson_str = gdf.to_json()
        geojson_dict = json.loads(geojson_str)
        
        return {"status": "success", "data": geojson_dict}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

import glob

FACILITIES_CACHE = None

@router.get("/facilities")
def get_facilities():
    """
    Returns a unified GeoJSON FeatureCollection of all 6 medical facility datasets.
    It reads all CSVs, builds the features and caches the result for fast access.
    """
    global FACILITIES_CACHE
    if FACILITIES_CACHE is not None:
        return {"status": "success", "data": FACILITIES_CACHE}
        
    try:
        csv_files = glob.glob(os.path.join(DATA_DIR, "*_cleaned.csv"))
        features = []
        
        for file in csv_files:
            df = pd.read_csv(file)
            df = df.dropna(subset=['Latitude', 'Longitude'])
            
            for _, row in df.iterrows():
                try:
                    lat = float(row['Latitude'])
                    lon = float(row['Longitude'])
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "properties": {
                            "name": str(row.get('Name_EN', 'Unknown')),
                            "type": str(row.get('Facility_Type', 'Facility')),
                            "address": str(row.get('Address_EN', 'Not provided'))
                        }
                    })
                except ValueError:
                    # Skip rows with malformed coordinates
                    continue
                
        FACILITIES_CACHE = {
            "type": "FeatureCollection",
            "features": features
        }
        return {"status": "success", "data": FACILITIES_CACHE}
    except Exception as e:
        return {"status": "error", "message": str(e)}

