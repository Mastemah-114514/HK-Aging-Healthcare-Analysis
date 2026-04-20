import pandas as pd
import geopandas as gpd
import glob
import os

DATA_DIR = r'D:\Course_materials\LSGI3315_GIS_Engineering\Group_Project\HK-Aging-Healthcare-Analysis\Data'
gdf = gpd.read_file(os.path.join(DATA_DIR, 'HK_District', 'HKDistrict18.shp')).to_crs(epsg=4326)
df_pop = pd.read_csv(os.path.join(DATA_DIR, 'Population_Census_2021.CSV'), header=4).dropna(subset=['dc_eng'])
csvs = glob.glob(os.path.join(DATA_DIR, '*_cleaned.csv'))
all_fac = pd.concat([pd.read_csv(f).dropna(subset=['Latitude', 'Longitude']) for f in csvs])
gdf_fac = gpd.GeoDataFrame(all_fac, geometry=gpd.points_from_xy(all_fac.Longitude, all_fac.Latitude), crs='EPSG:4326')
sj = gpd.sjoin(gdf_fac, gdf, how='inner', predicate='intersects')
counts = sj.groupby('index_right').size()
gdf['fac_count'] = counts
gdf['fac_count'] = gdf['fac_count'].fillna(0)
res = []
for i, r in gdf.iterrows():
    n = str(r['ENAME']).upper().replace('&', 'AND')
    p = 0
    for _, row in df_pop.iterrows():
        n2 = str(row['dc_eng']).upper().replace('&', 'AND')
        if n2 in n or n in n2:
            p = float(row['age_5'])
            break
    gap = p / max(1, r['fac_count'])
    res.append((n, p, r['fac_count'], gap))
res.sort(key=lambda x: x[3])
for r in res:
    print(r)
