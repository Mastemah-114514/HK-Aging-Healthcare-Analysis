try:
    import arcpy
except ImportError:
    arcpy = None
    print("Warning: arcpy not found. ArcGIS-specific functions will be disabled in this environment.")
import pandas as pd
import math
import os

# Task 2: Python Module Implementation for Facilities
# This module is used to read cleaned data of different facilities, convert it into ArcGIS feature classes, and perform simple spatial location queries.
class Facility:

    # Initialization method: Receive the path to the cleaned facility CSV file and define instance variables to record core attributes.
    def __init__(self, csv_filepath):
        # csv_filepath (str): The file path of the cleaned CSV facility data.
        self.csv_filepath = csv_filepath
        try:
            self.df = pd.read_csv(csv_filepath)
        except Exception as e:
            print(f"Error loading CSV data: {e}")
            self.df = pd.DataFrame()
            
        # Define instance variables to record attributes like facility location, type, and address
        # Assuming the cleaned CSV contains: Name_EN,Address_EN,Latitude,Longitude,Facility_Type
        if not self.df.empty:
            self.facility_type = self.df.get('Facility_Type', pd.Series(['Unknown_Facility'])).iloc[0]
            self.locations = list(zip(self.df['Latitude'], self.df['Longitude']))
            self.addresses = self.df['Address_EN'].unique().tolist()
            self.records = self.df.to_dict('records')
            print(f"Successfully loaded {len(self.records)} {self.facility_type} facilities.")
        else:
            self.facility_type = "Unknown_Facility"
            self.locations = []
            self.addresses = []
            self.records = []
            print("Warning: The loaded dataset is empty.")





    def to_feature_class(self, geodatabase_path):
        """
        Method:
            Convert the loaded facility information into a feature class and store it in an ArcGIS geodatabase.
        Parameters:
            geodatabase_path (str): The absolute path of the target .gdb geodatabase.
        Returns:
            Returns the full path of the created feature class.
        """
        fc_name = f"{self.facility_type}_FeatureClass"
        fc_path = os.path.join(geodatabase_path, fc_name)
        
        # Enable the overwrite environment setting to avoid errors upon multiple runs
        arcpy.env.overwriteOutput = True
        
        # Create a point feature class using the WGS1984 coordinate system (WKID 4326)
        sr = arcpy.SpatialReference(4326)
        arcpy.management.CreateFeatureclass(geodatabase_path, fc_name, "POINT", spatial_reference=sr)
        
        # Define fields to be added
        fields = ['facility_address', 'facility_name', 'facility_type', 'facility_location_WGS84']

        # Actually create fields in the feature class
        for field in fields:
            arcpy.management.AddField(fc_path, field, "TEXT")

        # Insert cursor, the first item in the insert list must be the spatial geometry shape token: 'SHAPE@XY'
        insert_fields = ['SHAPE@XY'] + fields
        
        with arcpy.da.InsertCursor(fc_path, insert_fields) as cursor:
            for row in self.records:
                row_values = []
                # Append latitude and longitude pair (longitude=X, latitude=Y)
                row_values.append((row.get('Longitude', 0), row.get('Latitude', 0)))
                
                lat_str = str(row.get('Latitude', 'N/A'))
                lon_str = str(row.get('Longitude', 'N/A'))
                
                # Custom map the CSV columns to the appropriate GDB fields
                field_mapping = {
                    'facility_address': row.get('Address_EN', 'N/A'),
                    'facility_name': row.get('Name_EN', 'N/A'),
                    'facility_type': self.facility_type,
                    'facility_location_WGS84': f"{lat_str}, {lon_str}"
                }
                
                # Append other field attribute contents
                for f in fields:
                    row_values.append(str(field_mapping.get(f, 'N/A')))
                        
                # Insert the constructed row into the GDB
                cursor.insertRow(row_values)
                
        print(f"Feature class created successfully, exported to: {fc_path}")
        return fc_path


    def find_nearest_facility(self, target_lat, target_lon):
        """
        Method: Receive a specified pair of latitude and longitude (WGS84), project them to HK 1980 Grid (Easting, Northing), 
        and return the facility record closest to this location based on legitimate Euclidean Distance in meters.
        
        Parameters:
            target_lat (float): Target point latitude
            target_lon (float): Target point longitude
            
        Returns:
            dict: A Python dictionary object containing the English name and coordinates of the nearest facility.
        """
        if not self.records:
            print("Currently no facility data available for calculation.")
            return None
            
        # Define Spatial References: WKID 4326 is WGS84, WKID 2326 is Hong Kong 1980 Grid
        sr_wgs84 = arcpy.SpatialReference(4326)
        sr_hk1980 = arcpy.SpatialReference(2326)
        
        # Project Target Point
        target_pt = arcpy.PointGeometry(arcpy.Point(target_lon, target_lat), sr_wgs84)
        target_pt_proj = target_pt.projectAs(sr_hk1980)
        target_easting = target_pt_proj.centroid.X
        target_northing = target_pt_proj.centroid.Y
            
        nearest_fac = None
        min_dist = float('inf')
        
        for fac in self.records:
            lat = fac['Latitude']
            lon = fac['Longitude']
            
            # Project Facility Point
            fac_pt = arcpy.PointGeometry(arcpy.Point(lon, lat), sr_wgs84)
            fac_pt_proj = fac_pt.projectAs(sr_hk1980)
            fac_easting = fac_pt_proj.centroid.X
            fac_northing = fac_pt_proj.centroid.Y
            
            # Calculate Euclidean distance using projected Easting and Northing (Result in meters)
            dist = math.sqrt((fac_easting - target_easting)**2 + (fac_northing - target_northing)**2)
            
            if dist < min_dist:
                min_dist = dist
                nearest_fac = fac
                
        if nearest_fac:
            # Assemble the return result object
            result = {
                'facility_name_en': nearest_fac.get('Name_EN', 'Unknown'),
                'latitude': nearest_fac.get('Latitude'),
                'longitude': nearest_fac.get('Longitude'),
                'address': nearest_fac.get('Address_EN', 'Unknown'),
                'relative_distance': min_dist
            }
            return result
        return None

    def find_k_nearest_facilities(self, target_lat, target_lon, k=3):
        """
        [Bonus Analysis] 
        Method: Receive a specified pair of latitude and longitude (WGS84), project them to HK 1980 Grid, 
        and return the top K facility records closest to this location based on Euclidean Distance in meters.
        
        Parameters:
            target_lat (float): Target point latitude
            target_lon (float): Target point longitude
            k (int): The number of nearest facilities to retrieve (default is 3)
            
        Returns:
            list: A list of length K containing dictionaries of the nearest facilities, sorted by distance.
        """
        if not self.records:
            print("Currently no facility data available for calculation.")
            return []
            
        # Define Spatial References: WKID 4326 is WGS84, WKID 2326 is Hong Kong 1980 Grid
        sr_wgs84 = arcpy.SpatialReference(4326)
        sr_hk1980 = arcpy.SpatialReference(2326)
        
        # Project Target Point
        target_pt = arcpy.PointGeometry(arcpy.Point(target_lon, target_lat), sr_wgs84)
        target_pt_proj = target_pt.projectAs(sr_hk1980)
        target_easting = target_pt_proj.centroid.X
        target_northing = target_pt_proj.centroid.Y
            
        distances_list = []
        
        for fac in self.records:
            lat = fac['Latitude']
            lon = fac['Longitude']
            
            # Project Facility Point
            fac_pt = arcpy.PointGeometry(arcpy.Point(lon, lat), sr_wgs84)
            fac_pt_proj = fac_pt.projectAs(sr_hk1980)
            fac_easting = fac_pt_proj.centroid.X
            fac_northing = fac_pt_proj.centroid.Y
            
            # Calculate Euclidean distance
            dist = math.sqrt((fac_easting - target_easting)**2 + (fac_northing - target_northing)**2)
            
            distances_list.append({
                'facility_name_en': fac.get('Name_EN', 'Unknown'),
                'latitude': lat,
                'longitude': lon,
                'address': fac.get('Address_EN', 'Unknown'),
                'relative_distance': dist
            })
            
        # Sort the entire list based on distance from nearest to furthest
        distances_list.sort(key=lambda x: x['relative_distance'])
        
        # Return only the top K records
        return distances_list[:k]

    def to_geojson(self):
        """
        [Bonus Analysis]
        Method: Convert facility records to a standard GeoJSON FeatureCollection.
        This allows the SilverGuard Web App to directly render the facilities on the frontend map.
        
        Returns:
            dict: A GeoJSON FeatureCollection dictionary.
        """
        features = []
        for row in self.records:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row.get('Longitude', 0)), float(row.get('Latitude', 0))]
                },
                "properties": {
                    "name": row.get('Name_EN', 'Unknown'),
                    "address": row.get('Address_EN', 'Unknown'),
                    "facility_type": self.facility_type
                }
            }
            features.append(feature)
            
        return {
            "type": "FeatureCollection",
            "features": features
        }
        print("Successfully converted facility records to geojson.")


if __name__ == "__main__":
    # 1. Automatically create and assign GDB workspace
    # Define project data root directory
    # You can change the path below to your own path
    data_dir = r"D:\Course_materials\LSGI3315_GIS_Engineering\Group_Project\HK-Aging-Healthcare-Analysis\Data"
    
    # Set the required output GDB name
    gdb_name = "HK_Aging_Healthcare_Analysis.gdb"
    geodatabase_path = os.path.join(data_dir, gdb_name)
    
    print(f"Checking and configuring geodatabase: {geodatabase_path}")
    try:
        # Create GDB if it does not exist
        if not arcpy.Exists(geodatabase_path):
            arcpy.management.CreateFileGDB(data_dir, gdb_name)
            print(f"Successfully created new GDB geodatabase in the Data folder: {gdb_name}")
        else:
            print("Found existing matching GDB geodatabase, will use it directly.")
        arcpy.env.workspace = geodatabase_path
    except Exception as e:
        print(f"Issue occurred while configuring ArcGIS database environment (Please ensure arcpy environment is set up), details: {e}")

    # 2. Configuration for 6 types of elderly and healthcare facilities basic data lists
    # Pointing to the absolute paths of the six cleaned files prefixed with Cleaned_ in the Data folder
    csv_file_path = [
        os.path.join(data_dir, "ClinicsHealthCentresundertheDepartmentofHealth_cleaned.csv"),
        os.path.join(data_dir, "ClinicsregisteredunderCap343_cleaned.csv"),
        os.path.join(data_dir, "DayCareCentresfortheElderly_cleaned.csv"),
        os.path.join(data_dir, "HospitalAuthorityHospitalInstitutionList_cleaned.csv"),
        os.path.join(data_dir, "LocationofResidentialCareHomesfortheElderlyinHongKong_cleaned.csv"),
        os.path.join(data_dir, "PrivatehealthcarefacilitiesunderCap633_cleaned.csv")
    ]
    
    # 3. Batch reading CSV data and converting to six distinct ArcGIS Point Feature Classes
    print("\nStarting batch processing and generating six types of facility feature classes")
    
    # Temporarily used to store all instantiated Facility objects
    facilities_list = []

    for idx, csv_path in enumerate(csv_file_path, 1):
        print(f"\n[{idx}/6] Reading facility data: {os.path.basename(csv_path)}")
        
        # Instantiate Facility object
        facility_obj = Facility(csv_path)
        
        if not facility_obj.records:
            print(f"Warning: Failed to load data from {os.path.basename(csv_path)}, skipping this file.")
            continue
            
        # Attempt to generate ArcGIS feature class
        try:
            out_fc = facility_obj.to_feature_class(geodatabase_path)
            print(f"Feature class created successfully and saved to: {out_fc}")
        except Exception as e:
            print(f"Failed: ArcGIS feature class creation error: {e}")
            
        facilities_list.append(facility_obj)

    # 4. Spatial query basic functionality test sample
    # Enter your own coordinates to test the function
    test_latitude = 22.2800  
    test_longitude = 114.1600
    
    # Perform a validation to see if the function works
    if facilities_list:
        test_facility = facilities_list[0]
        
        # Original Test: Find 1 Nearest
        print(f"\n[Test 1] Searching for the nearest facility to target coordinates ({test_latitude}, {test_longitude}) within the category [{test_facility.facility_type}]...")
        nearest_result = test_facility.find_nearest_facility(test_latitude, test_longitude)
        if nearest_result:
            print(f"Found nearest facility: {nearest_result['facility_name_en']} (located in {nearest_result['address']})")
            print(f"Approximate straight-line distance: {nearest_result['relative_distance']:.2f} meters")

        # Bonus Feature Test: Find Top 3 Nearest
        print(f"\n[Bonus Feature Test] Searching for the Top 3 nearest facilities to target coordinates...")
        k_results = test_facility.find_k_nearest_facilities(test_latitude, test_longitude, k=3)
        if k_results:
            for i, res in enumerate(k_results, 1):
                print(f"   => Top {i} Nearest: {res['facility_name_en']}")
                print(f"      Address: {res['address']}")
                print(f"      Distance: {res['relative_distance']:.2f} meters\n")

    print("\nEntire process completed.")
