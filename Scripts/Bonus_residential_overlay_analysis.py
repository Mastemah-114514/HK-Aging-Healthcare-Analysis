import arcpy
import os
import pandas as pd


def run_bonus_analysis():
    """
    Task 3 Bonus:
    1. Extracts residential areas from the 2021 Land Utilization raster.
    2. Converts them to polygons.
    3. Identifies residential zones OUTSIDE the 500m healthcare facility buffer.
    4. Calculates the coverage ratio for EVERY DISTRICT and exports to Excel.
    """
    # 1. Check out the Spatial Analyst extension (required for raster processing)
    try:
        arcpy.CheckOutExtension("Spatial")
        print("[INFO] Spatial Analyst extension checked out successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to get Spatial Analyst license: {e}")
        return

    arcpy.env.overwriteOutput = True

    # 2. Define Paths based on your specific directory structure
    project_root = r"C:\Users\Lenovo\PycharmProjects\Arc_py\LSGI3315 Group Project"
    gdb_path = os.path.join(project_root, "Healthcare_Facilities.gdb")

    # Inputs
    raster_folder = os.path.join(project_root, "LUMHK_RasterGrid_2021")
    raster_path = os.path.join(raster_folder, "LUM_end2021.tif")
    buffer_fc = os.path.join(gdb_path, "DayCareCentresfortheElderly_Buffer_500m")
    districts_shp = os.path.join(project_root, r"Raw Data\hk map\Hong_Kong_18_Districts-shp\HKDistrict18.shp")

    # Outputs
    residential_polygon = os.path.join(gdb_path, "Residential_Areas_2021")
    poor_coverage_fc = os.path.join(gdb_path, "Residential_Poor_Coverage")
    output_excel = os.path.join(project_root, "District_Coverage_Ratio.xlsx")

    # Verify prerequisites exist
    if not arcpy.Exists(raster_path):
        print(f"[ERROR] Raster not found at: {raster_path}")
        return
    if not arcpy.Exists(buffer_fc):
        print(f"[ERROR] Buffer feature class not found at: {buffer_fc}. Please run Task 3 first.")
        return
    if not arcpy.Exists(districts_shp):
        print(f"[ERROR] District shapefile not found at: {districts_shp}")
        return

    # ==========================================
    # Step A: Extract Residential Pixels & Convert
    # ==========================================
    print("\n[INFO] Step 1: Extracting residential pixels from LUM_end2021.tif...")
    # 1 = Private Residential, 2 = Public Residential 3 = Rural Settlement, 11 = Commercial/Business and Office
    extracted_raster = arcpy.sa.ExtractByAttributes(raster_path, "VALUE IN (1, 2, 3, 11)")

    print("[INFO] Step 2: Converting Raster to Polygon (This may take a couple of minutes)...")
    arcpy.conversion.RasterToPolygon(
        in_raster=extracted_raster,
        out_polygon_features=residential_polygon,
        simplify="SIMPLIFY",
        raster_field="Value"
    )
    print(f"[SUCCESS] Residential vector polygons saved to: {residential_polygon}")

    # ==========================================
    # Step B: Identify Poor Coverage Areas
    # ==========================================
    print("\n[INFO] Step 3: Analyzing residential areas lacking 500m healthcare coverage...")

    # Create a temporary Feature Layer for selection operations
    arcpy.management.MakeFeatureLayer(residential_polygon, "Res_Layer")

    # Select by Location: Find residential areas intersecting the buffer, then INVERT the selection
    # This leaves ONLY the residential areas outside the 500m buffer selected
    arcpy.management.SelectLayerByLocation(
        in_layer="Res_Layer",
        overlap_type="INTERSECT",
        select_features=buffer_fc,
        invert_spatial_relationship="INVERT"
    )

    # Export the selected (poor coverage) residential areas to a permanent feature class
    arcpy.management.CopyFeatures("Res_Layer", poor_coverage_fc)
    arcpy.management.Delete("Res_Layer")  # Clean up temporary layer
    print(f"[SUCCESS] Poor coverage areas saved to: {poor_coverage_fc}")

    # ==========================================
    # Step C: District Intersection & Calculate Ratios
    # ==========================================
    print("\n[INFO] Step 4: Calculating Coverage Ratio by District...")

    # Use 'memory' workspace to process intersections quickly without filling up the GDB
    mem_total_res = r"memory\total_res_intersect"
    mem_poor_res = r"memory\poor_res_intersect"

    # Cut the residential areas and poor coverage areas using the 18 District boundaries
    arcpy.analysis.PairwiseIntersect([residential_polygon, districts_shp], mem_total_res)
    arcpy.analysis.PairwiseIntersect([poor_coverage_fc, districts_shp], mem_poor_res)

    dist_stats = {}

    # Initialize dictionary using the ENAME field from the District Shapefile
    with arcpy.da.SearchCursor(districts_shp, ['ENAME']) as cursor:
        for row in cursor:
            dist_stats[row[0]] = {'total_sqm': 0, 'uncovered_sqm': 0}

    # Sum total residential area (in square meters) by district
    with arcpy.da.SearchCursor(mem_total_res, ['ENAME', 'SHAPE@AREA']) as cursor:
        for row in cursor:
            dist_stats[row[0]]['total_sqm'] += row[1]

    # Sum uncovered residential area (in square meters) by district
    with arcpy.da.SearchCursor(mem_poor_res, ['ENAME', 'SHAPE@AREA']) as cursor:
        for row in cursor:
            dist_stats[row[0]]['uncovered_sqm'] += row[1]

    # Clean up memory layers
    arcpy.management.Delete(mem_total_res)
    arcpy.management.Delete(mem_poor_res)

    # ==========================================
    # Step D: Format and Export to Excel
    # ==========================================
    print("[INFO] Step 5: Generating Excel Report...")
    results = []

    for dist, stats in dist_stats.items():
        tot_sqm = stats['total_sqm']
        uncov_sqm = stats['uncovered_sqm']
        cov_sqm = tot_sqm - uncov_sqm

        if tot_sqm > 0:
            cov_pct = (cov_sqm / tot_sqm)
            uncov_pct = (uncov_sqm / tot_sqm)
            ratio = (cov_sqm / uncov_sqm) if uncov_sqm > 0 else float('inf')
        else:
            cov_pct = uncov_pct = ratio = 0

        results.append({
            'District': dist,
            'Total_Residential_sqkm': round(tot_sqm / 1_000_000, 3),
            'Covered_Area_sqkm': round(cov_sqm / 1_000_000, 3),
            'Uncovered_Area_sqkm': round(uncov_sqm / 1_000_000, 3),
            'Coverage_Percentage': f"{cov_pct * 100:.2f}%",
            'Covered_to_Uncovered_Ratio': "Perfect Coverage" if ratio == float('inf') else f"{ratio:.2f} : 1"
        })

    # Create a Pandas DataFrame
    df = pd.DataFrame(results)

    # Sort the table so the districts with the LOWEST coverage percentage are at the top
    df = df.sort_values(by='Coverage_Percentage')
    df.to_excel(output_excel, index=False)

    print("\n" + "=" * 65)
    print(" DISTRICT COVERAGE ANALYSIS COMPLETE ")
    print("=" * 65)
    print(df.to_string(index=False))
    print("=" * 65)
    print(f"\n[SUCCESS] Detailed district report exported to: {output_excel}")

    # Return the Spatial Analyst license
    arcpy.CheckInExtension("Spatial")


if __name__ == "__main__":
    run_bonus_analysis()