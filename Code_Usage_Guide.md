# 🩺 SilverGuard System: Code Usage Guide

This document provides a concise, one-page guide on how to run the spatial analysis scripts (`Scripts`), how to modify input parameters, and how to start the interactive web dashboard (SilverGuard App).

---

## 🗺️ Part 1: Spatial Analysis Scripts (`Scripts/` Folder)

The `Scripts` folder contains the core automated Python code used for GIS analysis. Key files include:
- `Facility_initializer.py`: Initializes and cleans raw healthcare/elderly facility data using Object-Oriented modeling.
- `Facility_distribution_analysis.py`: Calculates the spatial distribution of facilities and generates heatmap coverage layers based on census population data.
- `Facility_overlay_distribution_analysis.py` / `Bonus_residential_overlay_analysis.py`: Performs overlay spatial analysis between facilities and residential areas.
- `Buffer_analysis.py`: Analyzes the service area buffers of healthcare facilities.

### 1. Environment Requirements
These scripts rely on ArcGIS's geoprocessing library `arcpy` and **must be executed within the ArcGIS Pro Python environment**.
- **Recommended**: Find and open the **Python Command Prompt (ArcGIS Pro)** from your computer's Start menu.
- Alternatively, run them inside the Python Window within the ArcGIS Pro software.

### 2. How to Configure Data Inputs / Parameters
To achieve one-click automation, all input datasets (CSV, SHP) are placed in the `Data/` folder at the project root. You **do not** need to specify individual input files. **You only need to update the project root directory path.**

Open the script you want to run (e.g., `Facility_distribution_analysis.py`) with any text editor, scroll to the very bottom, and locate the `root_dir` variable:
```python
if __name__ == "__main__":
    # 💥 Please change this path to the actual absolute path of this project folder on your PC
    root_dir = r"D:\Course_materials\LSGI3315_GIS_Engineering\Group_Project\HK-Aging-Healthcare-Analysis"
    ...
```
- **Input Modification**: Replace the value of `root_dir`. The script will automatically read the `.shp` (district map) and `.CSV` (census data) from the `Data/` directory based on this path.
- **Output Results**: After execution, the script will automatically generate/update Markdown statistical reports in the `Results/` folder. Spatial analysis layers will be automatically saved to the `Data/HK_Aging_Healthcare_Analysis.gdb` geodatabase for direct rendering in ArcGIS Pro.

### 3. Execution Method
After updating the path and saving the file, type the following command in the ArcGIS Pro Python Command Prompt to run the analysis:
```bash
python D:\Your_Actual_Path\Scripts\Facility_distribution_analysis.py
```

---

## 💻 Part 2: Starting the SilverGuard Interactive App

Once the spatial analysis is complete, or if you simply want to preview the final Web Visualization Dashboard, follow these steps to launch the app:

### 1. One-Click Launch (Recommended for Windows)
The project includes a batch file to automatically start both the backend and frontend simultaneously:
1. Open File Explorer and navigate to the **`SilverGuard_App`** folder.
2. Double-click the **`Start_SilverGuard.bat`** file.
3. Two black terminal windows will pop up automatically:
   - One for the **FastAPI Backend** service (running on port 8000).
   - One for the **Vite + React Frontend** service (running on port 5173).
4. Upon successful startup, your default web browser will automatically open and navigate to `http://127.0.0.1:5173`.

> ⚠️ **Note**: While using the Web Dashboard, **please DO NOT close the two black terminal windows**, otherwise the webpage will lose connection to the data and display a blank screen.

### 2. Manual Launch (If the Bat file fails or for Mac users)
If you encounter any issues, you can open two separate terminals and launch the services manually:

**Terminal 1 (Start Data Backend):**
```bash
cd SilverGuard_App/backend
pip install -r requirements.txt  # Install dependencies for the first run
python -m uvicorn main:app --reload
```

**Terminal 2 (Start Page Frontend):**
```bash
cd SilverGuard_App/frontend
npm install  # Install dependencies for the first run
npm run dev
```
After starting, manually copy the `Local: http://localhost:5173/` link printed in Terminal 2 and open it in your browser.
