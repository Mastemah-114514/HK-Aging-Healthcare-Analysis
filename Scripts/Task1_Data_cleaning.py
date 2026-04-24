import pandas as pd
import os

# 1. Set the base directory path
base_dir = r"C:\Users\Lenovo\PycharmProjects\Arc_py\LSGI3315 Group Project\Raw Data"

# 2. Define schema mapping for each file (Extracting ONLY English names, addresses, and coordinates)
file_mappings = {
    "HospitalAuthorityHospitalInstitutionList.csv": {
        "NAME_EN": "Name_EN", "ADDRESS_EN": "Address_EN",
        "LATITUDE": "Latitude", "LONGITUDE": "Longitude"
    },
    "ClinicsHealthCentresundertheDepartmentofHealth.csv": {
        "NameEN": "Name_EN", "AddressEN": "Address_EN",
        "Latitude": "Latitude", "Longitude": "Longitude"
    },
    "ClinicsregisteredunderCap343.csv": {
        "Clinic_name": "Name_EN", "Clinic_address": "Address_EN",
        "Latitude": "Latitude", "Longitude": "Longitude"
    },
    "PrivatehealthcarefacilitiesunderCap633.csv": {
        "PHF_name": "Name_EN", "PHF_address": "Address_EN",
        "Latitude": "Latitude", "Longitude": "Longitude"
    },
    "DayCareCentresfortheElderly.csv": {
        "NAME_EN": "Name_EN", "ADDRESS_EN": "Address_EN",
        "LATITUDE": "Latitude", "LONGITUDE": "Longitude"
    },
    "LocationofResidentialCareHomesfortheElderlyinHongKong.csv": {
        "NameEN": "Name_EN", "AddressEN": "Address_EN",
        "Latitude": "Latitude", "Longitude": "Longitude"
    }
}


def clean_healthcare_datasets():
    print("Starting data cleaning and standardization process...\n" + "-" * 50)

    for filename, mapping in file_mappings.items():
        input_path = os.path.join(base_dir, filename)

        # Check if file exists in the directory
        if not os.path.exists(input_path):
            print(f"[WARNING] File not found: {filename}")
            continue

        try:
            # Read CSV (using utf-8-sig to handle potential BOM characters gracefully)
            df = pd.read_csv(input_path, encoding='utf-8-sig', low_memory=False)

            # Rename columns based on the dictionary mapping
            df_cleaned = df.rename(columns=mapping)

            # Keep only the standardized target columns defined in the mapping
            target_cols = list(mapping.values())
            df_cleaned = df_cleaned[target_cols].copy()

            # Add 'Facility_Type' column using the filename (without extension) for GIS categorization
            dataset_name = os.path.splitext(filename)[0]
            df_cleaned['Facility_Type'] = dataset_name

            # Drop records that are missing spatial coordinates
            df_cleaned = df_cleaned.dropna(subset=['Latitude', 'Longitude'])

            # Generate the output file path with the '_cleaned' suffix
            output_filename = f"{dataset_name}_cleaned.csv"
            output_path = os.path.join(base_dir, output_filename)

            # Export the cleaned dataframe to CSV
            df_cleaned.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"[SUCCESS] Exported: {output_filename} ({len(df_cleaned)} records)")

        except Exception as e:
            print(f"[ERROR] Failed to process {filename}: {e}")

    print("-" * 50 + "\nData cleaning completed successfully!")


if __name__ == "__main__":
    clean_healthcare_datasets()