import arcpy
import os


class FacilityAnalyzer:
    """
    Task 3: A class focused strictly on spatial analysis (Buffers) for healthcare facilities.
    """

    def __init__(self, file_path):
        self.facility_type = os.path.basename(file_path).replace("_cleaned.csv", "")

    def create_coverage_buffer(self, gdb_path, fc_path, distance_meters=500):
        """
        Creates a buffer around the facilities to analyze coverage area.
        Takes distance as an input parameter.
        """
        arcpy.env.overwriteOutput = True
        out_buffer = os.path.join(gdb_path, f"{self.facility_type}_Buffer_{distance_meters}m")

        # Buffer analysis. Using "ALL" dissolves overlapping buffers into one continuous area
        arcpy.analysis.Buffer(
            in_features=fc_path,
            out_feature_class=out_buffer,
            buffer_distance_or_field=f"{distance_meters} Meters",
            dissolve_option="ALL"
        )
        return out_buffer


# ---------------------------------------------------------------------------
# Task 3 Workflow
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 1. Define Paths (Same as Task 2)
    project_root = r"C:\Users\Lenovo\PycharmProjects\Arc_py\LSGI3315 Group Project"
    cleaned_dir = os.path.join(project_root, "cleaned data")
    aprx_path = r"C:\Users\Lenovo\Documents\ArcGIS\Projects\LSGI3315_Group_Project\LSGI3315_Group_Project.aprx"
    gdb_path = os.path.join(project_root, "Healthcare_Facilities.gdb")

    if not arcpy.Exists(gdb_path):
        print("[ERROR] Geodatabase not found! Please run Task_2.py first.")
        exit()

    arcpy.env.overwriteOutput = True
    aprx = arcpy.mp.ArcGISProject(aprx_path)
    target_map = aprx.listMaps()[0]

    files = [
        "HospitalAuthorityHospitalInstitutionList_cleaned.csv",
        "ClinicsHealthCentresundertheDepartmentofHealth_cleaned.csv",
        "ClinicsregisteredunderCap343_cleaned.csv",
        "PrivatehealthcarefacilitiesunderCap633_cleaned.csv",
        "DayCareCentresfortheElderly_cleaned.csv",
        "LocationofResidentialCareHomesfortheElderlyinHongKong_cleaned.csv"
    ]

    # 2. Process Spatial Analysis (Buffers)
    walking_distance = 500  # Set the user-specified distance here

    for f_name in files:
        full_path = os.path.join(cleaned_dir, f_name)

        if os.path.exists(full_path):
            analyzer = FacilityAnalyzer(full_path)

            # Locate the feature class created by Task 2
            fc_path = os.path.join(gdb_path, analyzer.facility_type)

            if arcpy.Exists(fc_path):
                # TASK 3: Create Coverage Buffer
                buffer_path = analyzer.create_coverage_buffer(gdb_path, fc_path, distance_meters=walking_distance)
                target_map.addDataFromPath(buffer_path)
                print(f"  -> Generated {walking_distance}m walking coverage buffer for {analyzer.facility_type}.")
            else:
                print(f"  -> [WARNING] Feature class for {analyzer.facility_type} not found in GDB. Skipping.")

    # Save and Cleanup
    aprx.save()
    del aprx
    print("[FINISH] Task 3 Execution complete.")