import requests
import pandas as pd
import os
from fastapi import APIRouter

router = APIRouter()

HA_AED_API_URL = "https://www.ha.org.hk/opendata/aed/aedwtdata2-en.json"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOSPITALS_CSV_PATH = os.path.join(BASE_DIR, "Data", "HospitalAuthorityHospitalInstitutionList_cleaned.csv")

# Load coordinates once on startup to fast memory
try:
    df_hospitals = pd.read_csv(HOSPITALS_CSV_PATH)
    # create a dict mapping english name to lat lon
    hosp_dict = {}
    for _, row in df_hospitals.iterrows():
        name = str(row['Name_EN']).strip().lower()
        hosp_dict[name] = {'lat': row['Latitude'], 'lon': row['Longitude']}
except Exception as e:
    print(f"Error loading hospital csv: {e}")
    hosp_dict = {}

@router.get("/aed_wait_times")
def get_aed_wait_times():
    """
    Fetches real-time A&E waiting time data from the Hong Kong Hospital Authority
    and joins geographical coordinates.
    """
    try:
        response = requests.get(HA_AED_API_URL)
        response.raise_for_status()
        data = response.json()
        
        if "waitTime" in data:
            wait_times = data["waitTime"]
            processed = []
            for hosp in wait_times:
                name = hosp.get("hospName", "").strip()
                t45_wait = hosp.get("t45p95", "0 hours")
                
                # Transform "10.5 hours" to "over X hours" format for the frontend
                try:
                    hrs = float(t45_wait.split(' ')[0])
                    if hrs >= 8: top_wait = "over 8 hours"
                    elif hrs >= 5: top_wait = "over 5 hours"
                    elif hrs >= 3: top_wait = "over 3 hours"
                    else: top_wait = f"{hrs} hours"
                except:
                    top_wait = t45_wait
                
                # Filter strictly: only append if it matches the local CSV mapping
                name_low = name.lower()
                if name_low in hosp_dict:
                    # Determine severity color based on t45p95 numeric value
                    try:
                        hrs = float(t45_wait.split(' ')[0])
                        if hrs < 3:
                            color = "green"
                        elif hrs < 5:
                            color = "yellow"
                        else:
                            color = "red"
                    except:
                        # Fallback heuristic if float parsing fails
                        wait_low = t45_wait.lower()
                        if "over 8" in wait_low or "over 5" in wait_low:
                            color = "red"
                        elif "over 3" in wait_low:
                            color = "yellow"
                        else:
                            color = "green"
                            
                    item = {
                        "hospNameE": name,
                        "topWait": top_wait,
                        "severity_color": color,
                        "lat": hosp_dict[name_low]["lat"],
                        "lon": hosp_dict[name_low]["lon"]
                    }
                    processed.append(item)
            
            return {"status": "success", "data": processed, "updateTime": data.get("updateTime")}
        return {"status": "error", "message": "Unexpected data format from HA API"}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}

