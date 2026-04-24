import math
import os
import re
from pathlib import Path

import arcpy
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.patches import Patch
from matplotlib.collections import PatchCollection


# Fixed input configuration supplied by the user.
FACILITY_GDB = r"E:\CoderE\HkHealthElderCareFacilityGISAnalysis\Cleaned Data\Facility_Output.gdb"
FACILITY_LAYER_NAMES = [
    "Cleaned_Clinics_Health_Centres_under_the_Department_of_Health",
    "Cleaned_Clinics_registered_under_Cap_34",
    "Cleaned_Day_Care_Centres_for_the_Elderly",
    "Cleaned_Hospital_Authority_Hospital_Institution_List_gdb_convert",
    "Cleaned_Location_of_Residential_Care_Homes_for_the_Elderly_in_Ho",
    "Cleaned_Private_healthcare_facilities_with_valid_licence_letter_",
]
DISTRICT_SHP = (
    r"E:\CoderE\HkHealthElderCareFacilityGISAnalysis\Raw Data\hk map\Hong_Kong_18_Districts-shp\HKDistrict18.shp"
)
POP_FIELD = "pop"
TARGET_EPSG = 2326

# Output configuration.
PROJECT_ROOT = Path(r"E:\CoderE\HkHealthElderCareFacilityGISAnalysis")
OUTPUT_DIR = PROJECT_ROOT / "Analysis_Outputs"
MAP_DIR = OUTPUT_DIR / "maps"
CHART_DIR = OUTPUT_DIR / "charts"
LAYER_DIR = OUTPUT_DIR / "layers"
OUTPUT_GDB = FACILITY_GDB


def ensure_directories():
    for folder in (OUTPUT_DIR, MAP_DIR, CHART_DIR, LAYER_DIR):
        folder.mkdir(parents=True, exist_ok=True)


def sanitize_name(name, max_len=64):
    safe_name = re.sub(r"[^0-9A-Za-z_]", "_", str(name).strip())
    safe_name = re.sub(r"_+", "_", safe_name).strip("_")
    if not safe_name:
        safe_name = "item"
    if safe_name[0].isdigit():
        safe_name = "N_{}".format(safe_name)
    return safe_name[:max_len]


def get_spatial_reference():
    return arcpy.SpatialReference(TARGET_EPSG)


def validate_inputs():
    if not arcpy.Exists(FACILITY_GDB):
        raise FileNotFoundError("Facility geodatabase not found: {}".format(FACILITY_GDB))
    if not arcpy.Exists(DISTRICT_SHP):
        raise FileNotFoundError("District shapefile not found: {}".format(DISTRICT_SHP))

    arcpy.env.workspace = FACILITY_GDB
    existing_feature_classes = set(arcpy.ListFeatureClasses() or [])
    missing = [name for name in FACILITY_LAYER_NAMES if name not in existing_feature_classes]
    if missing:
        raise ValueError("Missing facility feature classes: {}".format(", ".join(missing)))

    district_fields = [field.name for field in arcpy.ListFields(DISTRICT_SHP)]
    if POP_FIELD not in district_fields:
        raise ValueError("Population field '{}' not found in district shapefile.".format(POP_FIELD))


def detect_district_name_field():
    district_fields = [field.name for field in arcpy.ListFields(DISTRICT_SHP)]
    for candidate in ("ENAME", "CNAME", "CNAME_S", "DISTRICT", "NAME"):
        if candidate in district_fields:
            return candidate
    raise ValueError("Unable to detect district name field in {}".format(DISTRICT_SHP))


def detect_district_id_field():
    district_fields = [field.name for field in arcpy.ListFields(DISTRICT_SHP)]
    for candidate in ("ID", "OBJECTID", "FID"):
        if candidate in district_fields:
            return candidate
    raise ValueError("Unable to detect district id field in {}".format(DISTRICT_SHP))


def prepare_districts():
    district_name_field = detect_district_name_field()
    district_id_field = detect_district_id_field()
    sr = get_spatial_reference()
    desc = arcpy.Describe(DISTRICT_SHP)
    projected_fc = os.path.join(OUTPUT_GDB, "HKDistrict18_2326")

    if arcpy.Exists(projected_fc):
        arcpy.management.Delete(projected_fc)

    if getattr(desc.spatialReference, "factoryCode", None) == TARGET_EPSG:
        arcpy.management.CopyFeatures(DISTRICT_SHP, projected_fc)
    else:
        arcpy.management.Project(DISTRICT_SHP, projected_fc, sr)

    return projected_fc, district_id_field, district_name_field


def build_base_district_dataframe(projected_fc, district_id_field, district_name_field):
    rows = []
    with arcpy.da.SearchCursor(projected_fc, [district_id_field, district_name_field, POP_FIELD]) as cursor:
        for district_id, district_name, pop_value in cursor:
            rows.append(
                {
                    "district_id": district_id,
                    "district_name": district_name,
                    "pop": float(pop_value) if pop_value not in (None, "") else 0.0,
                }
            )
    df = pd.DataFrame(rows)
    df = df.sort_values("district_name").reset_index(drop=True)
    return df


def summarize_facility_count_by_district(projected_fc, district_id_field, facility_fc):
    temp_join = os.path.join(arcpy.env.scratchGDB, sanitize_name("{}_district_join".format(Path(facility_fc).name)))
    if arcpy.Exists(temp_join):
        arcpy.management.Delete(temp_join)

    arcpy.analysis.SpatialJoin(
        target_features=projected_fc,
        join_features=facility_fc,
        out_feature_class=temp_join,
        join_operation="JOIN_ONE_TO_ONE",
        join_type="KEEP_ALL",
        match_option="INTERSECT",
    )

    counts = {}
    with arcpy.da.SearchCursor(temp_join, [district_id_field, "Join_Count"]) as cursor:
        for district_id, join_count in cursor:
            counts[district_id] = int(join_count or 0)
    return counts


def build_analysis_dataframe(projected_fc, district_id_field, district_name_field):
    df = build_base_district_dataframe(projected_fc, district_id_field, district_name_field)

    for facility_name in FACILITY_LAYER_NAMES:
        facility_fc = os.path.join(FACILITY_GDB, facility_name)
        count_map = summarize_facility_count_by_district(projected_fc, district_id_field, facility_fc)
        df[facility_name] = df["district_id"].map(count_map).fillna(0).astype(int)

    type_columns = FACILITY_LAYER_NAMES
    df["total_facilities"] = df[type_columns].sum(axis=1)
    df["facility_type_richness"] = (df[type_columns] > 0).sum(axis=1)
    df["facilities_per_10000"] = df.apply(
        lambda row: (row["total_facilities"] / row["pop"]) * 10000.0 if row["pop"] else 0.0,
        axis=1,
    )
    return df


def add_fields_if_needed(feature_class, field_specs):
    existing = {field.name for field in arcpy.ListFields(feature_class)}
    for field_name, field_type in field_specs:
        if field_name not in existing:
            arcpy.management.AddField(feature_class, field_name, field_type)


def write_analysis_feature_class(projected_fc, district_id_field, df):
    output_fc = os.path.join(OUTPUT_GDB, "HK18_District_Facility_Analysis")
    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)
    arcpy.management.CopyFeatures(projected_fc, output_fc)

    field_specs = [
        ("total_facilities", "LONG"),
        ("facilities_per_10000", "DOUBLE"),
        ("facility_type_richness", "SHORT"),
    ]
    add_fields_if_needed(output_fc, field_specs)

    value_map = {
        row["district_id"]: (
            int(row["total_facilities"]),
            float(row["facilities_per_10000"]),
            int(row["facility_type_richness"]),
        )
        for _, row in df.iterrows()
    }

    with arcpy.da.UpdateCursor(
        output_fc, [district_id_field, "total_facilities", "facilities_per_10000", "facility_type_richness"]
    ) as cursor:
        for row in cursor:
            district_id = row[0]
            if district_id in value_map:
                total_facilities, facilities_per_10000, richness = value_map[district_id]
                row[1] = total_facilities
                row[2] = facilities_per_10000
                row[3] = richness
                cursor.updateRow(row)
    return output_fc


def create_gdb_table(table_name, dataframe):
    output_table = os.path.join(OUTPUT_GDB, sanitize_name(table_name))
    if arcpy.Exists(output_table):
        arcpy.management.Delete(output_table)

    arcpy.management.CreateTable(OUTPUT_GDB, sanitize_name(table_name))
    field_order = []

    for column in dataframe.columns:
        field_name = sanitize_name(column)
        field_order.append((column, field_name))
        series = dataframe[column]
        if pd.api.types.is_integer_dtype(series):
            arcpy.management.AddField(output_table, field_name, "LONG")
        elif pd.api.types.is_float_dtype(series):
            arcpy.management.AddField(output_table, field_name, "DOUBLE")
        else:
            max_length = max(50, min(255, int(series.astype(str).str.len().max() or 50)))
            arcpy.management.AddField(output_table, field_name, "TEXT", field_length=max_length)

    insert_fields = [field_name for _, field_name in field_order]
    with arcpy.da.InsertCursor(output_table, insert_fields) as cursor:
        for _, row in dataframe.iterrows():
            values = []
            for column, _ in field_order:
                value = row[column]
                if pd.isna(value):
                    values.append(None)
                elif isinstance(value, pd.Timestamp):
                    values.append(value.to_pydatetime())
                else:
                    values.append(value.item() if hasattr(value, "item") else value)
            cursor.insertRow(values)
    return output_table


def create_analysis_tables(df):
    total_table = create_gdb_table("district_total_facilities_tbl", df[["district_name", "pop", "total_facilities"]])
    per_capita_table = create_gdb_table(
        "district_facilities_per_10000_tbl", df[["district_name", "pop", "total_facilities", "facilities_per_10000"]]
    )
    richness_columns = ["district_name"] + FACILITY_LAYER_NAMES + ["facility_type_richness"]
    richness_table = create_gdb_table("district_facility_richness_tbl", df[richness_columns])
    return total_table, per_capita_table, richness_table


def create_bar_chart(dataframe, value_field, title, output_png, color):
    chart_df = dataframe.sort_values(value_field, ascending=False)
    plt.figure(figsize=(12, 7))
    plt.bar(chart_df["district_name"], chart_df[value_field], color=color)
    plt.title(title)
    plt.xlabel("District")
    plt.ylabel(value_field)
    plt.xticks(rotation=60, ha="right")
    plt.tight_layout()
    plt.savefig(output_png, dpi=200)
    plt.close()


def jenks_breaks(values, n_classes):
    sorted_values = sorted(float(value) for value in values)
    if not sorted_values:
        return [0.0, 1.0]

    unique_values = sorted(set(sorted_values))
    if len(unique_values) <= n_classes:
        return unique_values

    n_data = len(sorted_values)
    lower = [[0] * (n_classes + 1) for _ in range(n_data + 1)]
    variance = [[float("inf")] * (n_classes + 1) for _ in range(n_data + 1)]

    for i in range(1, n_classes + 1):
        lower[1][i] = 1
        variance[1][i] = 0.0
        for j in range(2, n_data + 1):
            variance[j][i] = float("inf")

    for l in range(2, n_data + 1):
        s1 = s2 = w = 0.0
        for m in range(1, l + 1):
            i3 = l - m + 1
            val = sorted_values[i3 - 1]
            s2 += val * val
            s1 += val
            w += 1
            v = s2 - (s1 * s1) / w
            i4 = i3 - 1
            if i4 != 0:
                for j in range(2, n_classes + 1):
                    if variance[l][j] >= v + variance[i4][j - 1]:
                        lower[l][j] = i3
                        variance[l][j] = v + variance[i4][j - 1]
        lower[l][1] = 1
        variance[l][1] = v

    breaks = [0.0] * (n_classes + 1)
    breaks[n_classes] = sorted_values[-1]
    count_num = n_classes
    k = n_data
    while count_num > 1:
        idx = int(lower[k][count_num] - 2)
        breaks[count_num - 1] = sorted_values[idx]
        k = int(lower[k][count_num] - 1)
        count_num -= 1
    breaks[0] = sorted_values[0]
    return breaks


def classify_values(values, mode):
    clean_values = [float(v) for v in values]
    if mode == "natural_breaks":
        unique_values = sorted(set(clean_values))
        if len(unique_values) == 1:
            return [(unique_values[0], unique_values[0])], ["{:.2f}".format(unique_values[0])]
        if len(unique_values) <= 5:
            bins = [(value, value) for value in unique_values]
            labels = ["{:.2f}".format(value) for value in unique_values]
            return bins, labels

        breaks = jenks_breaks(clean_values, 5)
        labels = []
        bins = []
        for i in range(len(breaks) - 1):
            lower = breaks[i]
            upper = breaks[i + 1]
            bins.append((lower, upper))
            labels.append("{:.2f} - {:.2f}".format(lower, upper))
        return bins, labels

    if mode == "richness":
        unique_values = sorted(set(int(v) for v in clean_values))
        bins = [(value, value) for value in unique_values]
        labels = ["{} types".format(value) for value in unique_values]
        return bins, labels

    min_value = min(clean_values)
    max_value = max(clean_values)
    if math.isclose(min_value, max_value):
        return [(min_value, max_value)], ["{:.2f}".format(min_value)]

    class_count = min(5, len(set(clean_values)))
    step = (max_value - min_value) / class_count
    bins = []
    labels = []
    for i in range(class_count):
        lower = min_value + step * i
        upper = max_value if i == class_count - 1 else min_value + step * (i + 1)
        bins.append((lower, upper))
        labels.append("{:.2f} - {:.2f}".format(lower, upper))
    return bins, labels


def value_to_class_index(value, bins, discrete=False):
    if discrete:
        for idx, (lower, upper) in enumerate(bins):
            if int(value) == int(lower) == int(upper):
                return idx
        return 0
    all_discrete = all(lower == upper for lower, upper in bins)
    if all_discrete:
        for idx, (lower, upper) in enumerate(bins):
            if float(value) == float(lower) == float(upper):
                return idx
        return 0
    for idx, (lower, upper) in enumerate(bins):
        is_last = idx == len(bins) - 1
        if (lower <= value <= upper) if is_last else (lower <= value < upper):
            return idx
    return len(bins) - 1


def geometry_to_patches(geometry):
    patches = []
    for part in geometry:
        ring = []
        for point in part:
            if point:
                ring.append((point.X, point.Y))
            elif ring:
                if len(ring) >= 3:
                    patches.append(MplPolygon(ring, closed=True))
                ring = []
        if ring and len(ring) >= 3:
            patches.append(MplPolygon(ring, closed=True))
    return patches


def export_thematic_map(feature_class, district_name_field, value_field, title, output_png, scheme):
    rows = []
    with arcpy.da.SearchCursor(feature_class, [district_name_field, value_field, "SHAPE@"]) as cursor:
        for district_name, value, geometry in cursor:
            rows.append((district_name, float(value or 0), geometry))

    bins, labels = classify_values([row[1] for row in rows], scheme)
    colors = plt.get_cmap("YlOrRd", len(bins))
    discrete = scheme == "richness"

    fig, ax = plt.subplots(figsize=(12, 10))
    legend_handles = []

    for class_index, label in enumerate(labels):
        legend_handles.append(Patch(facecolor=colors(class_index), edgecolor="black", label=label))

    for district_name, value, geometry in rows:
        class_index = value_to_class_index(value, bins, discrete=discrete)
        district_patches = geometry_to_patches(geometry)
        collection = PatchCollection(
            district_patches, facecolor=colors(class_index), edgecolor="black", linewidths=0.6
        )
        ax.add_collection(collection)

        centroid = geometry.centroid
        ax.text(centroid.X, centroid.Y, district_name, fontsize=6, ha="center", va="center", color="black")

    extent = arcpy.Describe(feature_class).extent
    ax.set_xlim(extent.XMin, extent.XMax)
    ax.set_ylim(extent.YMin, extent.YMax)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(handles=legend_handles, title=value_field, loc="lower left", fontsize=8, title_fontsize=9)
    ax.set_title(title, fontsize=14)
    ax.text(
        0.99,
        0.01,
        "Coordinate System: EPSG:2326",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
    )
    plt.tight_layout()
    plt.savefig(output_png, dpi=220, bbox_inches="tight")
    plt.close(fig)


def save_layer_file(feature_class, layer_name):
    layer = arcpy.management.MakeFeatureLayer(feature_class, sanitize_name(layer_name))
    output_lyrx = LAYER_DIR / "{}.lyrx".format(sanitize_name(layer_name))
    arcpy.management.SaveToLayerFile(layer, str(output_lyrx), "RELATIVE")
    return str(output_lyrx)


def export_products(analysis_fc, district_name_field, df):
    total_chart = CHART_DIR / "district_total_facilities.png"
    per_capita_chart = CHART_DIR / "district_facilities_per_10000.png"
    richness_chart = CHART_DIR / "district_facility_type_richness.png"

    create_bar_chart(df, "total_facilities", "Hong Kong 18 Districts: Total Facilities", total_chart, "#4c78a8")
    create_bar_chart(
        df, "facilities_per_10000", "Hong Kong 18 Districts: Facilities per 10,000 Population", per_capita_chart, "#f58518"
    )
    create_bar_chart(
        df, "facility_type_richness", "Hong Kong 18 Districts: Facility Type Richness", richness_chart, "#54a24b"
    )

    total_map = MAP_DIR / "district_total_facilities_map.png"
    per_capita_map = MAP_DIR / "district_facilities_per_10000_map.png"
    richness_map = MAP_DIR / "district_facility_type_richness_map.png"

    export_thematic_map(
        analysis_fc,
        district_name_field,
        "total_facilities",
        "Hong Kong 18 Districts: Total Facility Count",
        total_map,
        scheme="equal_interval",
    )
    export_thematic_map(
        analysis_fc,
        district_name_field,
        "facilities_per_10000",
        "Hong Kong 18 Districts: Facilities per 10,000 Population",
        per_capita_map,
        scheme="natural_breaks",
    )
    export_thematic_map(
        analysis_fc,
        district_name_field,
        "facility_type_richness",
        "Hong Kong 18 Districts: Facility Type Richness",
        richness_map,
        scheme="richness",
    )

    total_lyrx = save_layer_file(analysis_fc, "district_total_facilities_layer")
    per_capita_lyrx = save_layer_file(analysis_fc, "district_facilities_per_10000_layer")
    richness_lyrx = save_layer_file(analysis_fc, "district_facility_richness_layer")

    return {
        "charts": [str(total_chart), str(per_capita_chart), str(richness_chart)],
        "maps": [str(total_map), str(per_capita_map), str(richness_map)],
        "layers": [total_lyrx, per_capita_lyrx, richness_lyrx],
    }


def run_analysis():
    arcpy.env.overwriteOutput = True
    arcpy.env.workspace = FACILITY_GDB
    ensure_directories()
    validate_inputs()

    projected_fc, district_id_field, district_name_field = prepare_districts()
    analysis_df = build_analysis_dataframe(projected_fc, district_id_field, district_name_field)
    analysis_fc = write_analysis_feature_class(projected_fc, district_id_field, analysis_df)
    total_table, per_capita_table, richness_table = create_analysis_tables(analysis_df)
    products = export_products(analysis_fc, district_name_field, analysis_df)

    print("Common facility fields: Name, Type, Lat_WGS84, Lon_WGS84")
    print("Analysis feature class: {}".format(analysis_fc))
    print("Total facilities table: {}".format(total_table))
    print("Per-capita table: {}".format(per_capita_table))
    print("Richness table: {}".format(richness_table))
    print("Exported charts:")
    for path in products["charts"]:
        print("  {}".format(path))
    print("Exported maps:")
    for path in products["maps"]:
        print("  {}".format(path))
    print("Exported layer files:")
    for path in products["layers"]:
        print("  {}".format(path))


if __name__ == "__main__":
    run_analysis()
