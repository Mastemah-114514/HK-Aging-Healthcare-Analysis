# 🛡️ Guarding the Silver Age — Hong Kong Aging Healthcare Analysis

> **A Comprehensive GIS Spatial Study & Interactive Dashboard of Hong Kong's Aging Healthcare Facilities**

![Project Status](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![ArcGIS](https://img.shields.io/badge/ArcGIS-Pro-red)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)
![Vue/React](https://img.shields.io/badge/Frontend-Vite-646CFF)

This repository contains the full workflow and final application for our spatial study on Hong Kong's aging healthcare infrastructure. It is divided into two major components: the GIS spatial analysis tasks and the interactive SilverGuard web application.

---

## 📑 Table of Contents

- [Part 1: Spatial Analysis Project Structure (Prerequisite Task)](#%EF%B8%8F-part-1-spatial-analysis-project-structure-prerequisite-task)
- [Part 2: SilverGuard App Project Structure](#-part-2-silverguard-app-project-structure)
- [Part 3: SilverGuard App Usage Instructions](#-part-3-silverguard-app-usage-instructions)
  - [1. Running Locally (Recommended)](#1-running-locally-recommended)
  - [2. Manual Execution (Optional)](#2-manual-execution-optional)
- [License](#-license)

---

## 🗺️ Part 1: Spatial Analysis Project Structure (Prerequisite Task)

The first phase of the project focused on data engineering, object-oriented modeling, and spatial analysis using Python and `arcpy`.

* **`📁 Data/`**
  * The core data packages for the spatial analysis. Contains raw CSV datasets of six types of healthcare and elderly facilities, demographic data, and the cleaned subsets used for geodatabase creation.
* **`📁 Scripts/`**
  * Contains all pure Python files driving the spatial automation. Key files include:
    * `Facility_initializer.py`: Initializes and cleans raw healthcare data using Object-Oriented modeling.
    * `Facility_distribution_analysis.py`: Calculates spatial distribution statistics and population-normalized heatmap coverage.
    * `Facility_overlay_distribution_analysis.py` & `Bonus_residential_overlay_analysis.py`: Performs overlay spatial analysis between facilities and residential areas.
    * `Buffer_analysis.py`: Analyzes the service area buffers of healthcare facilities.
* **`📁 Results/`**
  * Stores the final analytical outputs. This includes:
    * **GDB Layers (`.gdb`)**: The geodatabase containing feature classes, buffer zones, and heatmap layers.
    * **Distribution Data**: Statistical results, gap analysis, and distribution summaries such as `Distribution_Statistics_All.md`.

---

## 💻 Part 2: SilverGuard App Project Structure

The second phase involved building an interactive web dashboard to visualize the spatial insights dynamically.

* **`📁 SilverGuard_App/`**
  * The root directory for the interactive web application.
  * **`📁 frontend/`**
    * The modern web interface built with **Vite**. It contains the UI components, interactive maps, and data fetching logic to communicate with the backend.
  * **`📁 backend/`**
    * The **FastAPI** server that acts as the bridge between our local data/scripts and the frontend. It provides RESTful APIs to serve facility data (in GeoJSON format) and statistical results to the dashboard.
  * **`📜 Start_SilverGuard.bat`**
    * A batch script that automatically launches both the FastAPI backend and the Vite frontend simultaneously for local development and viewing.

---

## 🚀 Part 3: SilverGuard App Usage Instructions

Follow these steps to run the SilverGuard Dashboard on your local machine.

### 1. Running Locally (Recommended)

To display the dashboard on your local machine instantly:

1. Open **File Explorer** and navigate to the project root directory.
2. Go to the `SilverGuard_App` folder.
3. Double-click the **`Start_SilverGuard.bat`** file.
4. Two command prompt windows will open automatically:
   - One starting the **FastAPI Backend** on port `8000`.
   - One starting the **Vite Frontend** on port `5173`.
5. Your default web browser should open automatically to `http://127.0.0.1:5173`. If it does not, manually click the link to view the dashboard.

> **Note:** Do not close the command prompt windows while you are using the app. Closing them will stop the server.

### 2. Manual Execution (Optional)

If you prefer to use the terminal/command line instead of the batch files, you can start the services manually. Open two separate terminal windows from the root directory:

**Terminal 1 (Backend):**
```bash
cd SilverGuard_App/backend
python -m uvicorn main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd SilverGuard_App/frontend
npm run dev
```

---

## 📄 License

This project was developed for the LSGI3315 GIS Engineering course. All rights reserved by the project team.
