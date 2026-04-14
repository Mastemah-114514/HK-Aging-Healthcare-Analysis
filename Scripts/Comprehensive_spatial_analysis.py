import arcpy
import pandas as pd
import os

class Comprehensive_spatial_analysis:
    """
    Task 3: Core spatial analysis class for Question 1 and Question 2.
    Implements facility spatial join statistics and population coverage normalization model,
    and automatically outputs a layer for heatmap/symbology rendering.
    """
    def __init__(self, data_gdb, viz_gdb, district_shp, census_csv):
        self.data_gdb = data_gdb
        self.viz_gdb = viz_gdb
        self.district_shp = district_shp
        
        arcpy.env.workspace = self.data_gdb
        arcpy.env.overwriteOutput = True
        
        # Parse census dataset exactly as specified
        try:
            # Read CSV without headers to access specific rows/columns directly
            raw_df = pd.read_csv(census_csv, header=None)
            
            # The column names requested by the user
            self.district_col_in_csv = "Name of District Council district  (in English)"
            self.pop_col_in_csv = "65+"
            
            # Extract row 6 to 23 (index 5 to 22), first column (0) and last column (-1)
            # This perfectly isolates the district name data and the elderly population data
            self.census_df = raw_df.iloc[5:23, [0, -1]].copy()
            self.census_df.columns = [self.district_col_in_csv, self.pop_col_in_csv]
            
            # Clean population data (convert to numeric, handle commas nicely if any exist)
            self.census_df[self.pop_col_in_csv] = pd.to_numeric(
                self.census_df[self.pop_col_in_csv].astype(str).str.replace(',', '', regex=False),
                errors='coerce'
            )
            
            # Standardize district names to match SHP 'ENAME' (Uppercase and '&' mapping)
            self.census_df[self.district_col_in_csv] = self.census_df[self.district_col_in_csv].astype(str).str.strip().str.upper()
            self.census_df[self.district_col_in_csv] = self.census_df[self.district_col_in_csv].str.replace(' AND ', ' & ', regex=False)
            
            print("Successfully loaded the population census data.")
        except Exception as e:
            print(f"Error loading census data: {e}")
            self.census_df = pd.DataFrame()

    def analyze_distribution(self, facility_fc, output_markdown):
        out_fc = os.path.join(self.data_gdb, f"{facility_fc}_District_Join")
        
        arcpy.analysis.SpatialJoin(
            target_features=self.district_shp, 
            join_features=facility_fc, 
            out_feature_class=out_fc, 
            join_operation="JOIN_ONE_TO_ONE", 
            join_type="KEEP_ALL", 
            match_option="CONTAINS"
        )
        dist_field = 'ENAME'
        distribution_data = []
        with arcpy.da.SearchCursor(out_fc, [dist_field, 'Join_Count']) as cursor:
            for row in cursor:
                if row[0]: 
                    distribution_data.append({"District_Name": row[0], "Facility_Count": row[1]})
                
        df = pd.DataFrame(distribution_data)
        sorted_df = df.sort_values(by="Facility_Count", ascending=False)
        print("\nDistribution Statistics Table across 18 Districts:")
        print(sorted_df.to_string(index=False))
        
        # Write to the markdown file in the Results folder
        try:
            with open(output_markdown, 'a', encoding='utf-8') as f:
                f.write(f"# Spatial Distribution of {facility_fc}\n\n")
                
                # Manually build Markdown table to avoid pandas 'tabulate' dependency issues
                md_table = "| District Name | Facility Count |\n|---|---|\n"
                for _, r in sorted_df.iterrows():
                    md_table += f"| {r['District_Name']} | {r['Facility_Count']} |\n"
                    
                f.write(md_table)
                f.write("\n\n---\n\n")
            print(f"Results have been appended to {output_markdown}")
        except Exception as e:
            print(f"Failed to write markdown file: {e}")
        
        return df, out_fc

    def evaluate_normalized_coverage(self, dist_df, spatial_join_fc, output_name="Coverage_Heatmap_Layer"):
        """
        [Question 2] Calculate facility coverage based on population density, and normalize it for a heatmap layer
        """
        print(f"\nCalculating population density coverage index and generating heatmap feature layer...")
        
        district_col = getattr(self, "district_col_in_csv", None)
        pop_col = getattr(self, "pop_col_in_csv", None)
        
        if not self.census_df.empty and district_col and pop_col:
            # Join parsed census table
            merged_df = pd.merge(dist_df, self.census_df, left_on='District_Name', right_on=district_col, how='left')
            pop_values = merged_df[pop_col].fillna(1)
        else:
            pop_values = 100000 
            
        dist_df['Density_Per_10k'] = (dist_df['Facility_Count'] / pop_values) * 10000
        
        min_den = dist_df['Density_Per_10k'].min()
        max_den = dist_df['Density_Per_10k'].max()
        
        if max_den == min_den: 
            dist_df['Normalized_Score'] = 0.5 
        else:
            dist_df['Normalized_Score'] = (dist_df['Density_Per_10k'] - min_den) / (max_den - min_den)
            
        print("\nCoverage sufficiency evaluation results (0 = extreme scarcity, 1 = abundant):")
        print(dist_df[['District_Name', 'Facility_Count', 'Density_Per_10k', 'Normalized_Score']]
              .sort_values(by="Normalized_Score", ascending=False)
              .to_string(index=False, float_format="%.4f"))
        
        output_fc = os.path.join(self.viz_gdb, output_name)
        arcpy.management.CopyFeatures(spatial_join_fc, output_fc)
        
        arcpy.management.AddField(output_fc, "Density", "DOUBLE")
        arcpy.management.AddField(output_fc, "Norm_Score", "DOUBLE")
        
        dist_field = 'ENAME'
        
        with arcpy.da.UpdateCursor(output_fc, [dist_field, "Density", "Norm_Score"]) as cursor:
            for row in cursor:
                d_name = row[0]
                match_row = dist_df[dist_df['District_Name'] == d_name]
                if not match_row.empty:
                    row[1] = float(match_row['Density_Per_10k'].iloc[0])
                    row[2] = float(match_row['Normalized_Score'].iloc[0])
                else:
                    row[1], row[2] = 0.0, 0.0
                cursor.updateRow(row)
                
        print(f"\nHeatmap visualization layer successfully exported to: {output_fc}")
        return output_fc


if __name__ == "__main__":
    import sys
    
    root_dir = r"D:\Course_materials\LSGI3315_GIS_Engineering\Group_Project\HK-Aging-Healthcare-Analysis"
    
    # Create the Results folder alongside Data
    results_dir = os.path.join(root_dir, "Results")
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    data_gdb = os.path.join(root_dir, "Data", "HK_Aging_Healthcare_Analysis.gdb")
    # Directly use the same geodatabase for visualization data to prevent ERROR 000210 since the separate viz_gdb doesn't exist
    viz_gdb = data_gdb
    district_shp = os.path.join(root_dir, "Data", "HK_District", "HKDistrict18.shp")
    census_csv = os.path.join(root_dir, "Data", "Population_Census_2021.CSV")
    
    analysis = Comprehensive_spatial_analysis(data_gdb, viz_gdb, district_shp, census_csv)
    
    target_facility_fcs = [
        "ClinicsHealthCentresundertheDepartmentofHealth_FeatureClass",
        "ClinicsregisteredunderCap343_FeatureClass",
        "DayCareCentresfortheElderly_FeatureClass",
        "HospitalAuthorityHospitalInstitutionList_FeatureClass",
        "LocationofResidentialCareHomesfortheElderlyinHongKong_FeatureClass",
        "PrivatehealthcarefacilitiesunderCap633_FeatureClass"
    ]
    
    print("\n" + "="*60)
    print("Starting ArcPy comprehensive spatial analysis engine for all 6 facilities...")
    print("="*60)
    
    # Define a single markdown file to collect all statistics
    md_output_path = os.path.join(results_dir, "Distribution_Statistics_All.md")
    if os.path.exists(md_output_path):
        os.remove(md_output_path) # Clean old run data
        
    for fc in target_facility_fcs:
        if arcpy.Exists(os.path.join(data_gdb, fc)):
            print(f"\n" + "-"*50)
            print(f"Processing Facility: {fc}")
            print("-"*50)
            result_df, output_shp_layer = analysis.analyze_distribution(fc, output_markdown=md_output_path)
            
            # Shorten the feature name to prevent GDB path length explosion errors
            short_name = fc.split('_')[0][:25] 
            analysis.evaluate_normalized_coverage(result_df, output_shp_layer, output_name=f"Heatmap_{short_name}")
            print(f"\nSuccessfully finished analyzing {fc}.")
        else:
            print(f"\nAnalysis aborted for {fc}: Could not find feature class in {data_gdb}.")
