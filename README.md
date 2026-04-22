# Project Overview
This project is focused on providing solutions for aging healthcare through data analysis. It integrates advanced data processing techniques with a user-friendly interface for various stakeholders.

# Repository Structure
```
HK-Aging-Healthcare-Analysis/
├── backend/
│   ├── main.py
│   ├── spatial_api.py
│   └── live_data.py
└── frontend/
    ├── src/
    └── public/
```

# Technology Stack
- **Backend**: Python (Flask)
- **Frontend**: React, TypeScript, Vite

# Backend Components
### `main.py`
Responsible for initializing the Flask application and setting up routing. It connects to the database and handles incoming requests.

### `spatial_api.py`
This module provides APIs for spatial analytics. It processes geographic data relevant to aging healthcare.

### `live_data.py`
Manages the collection and processing of live data for real-time analysis.

# Frontend Components
The frontend is developed using React and TypeScript to enhance maintainability and scalability. Vite is used for development to ensure fast reloads.

# Installation Guide
## Backend
1. Clone the repository.
2. Navigate to the `backend` directory.
3. Install the dependencies using `pip install -r requirements.txt`.

## Frontend
1. Clone the repository.
2. Navigate to the `frontend` directory.
3. Install the dependencies using `npm install`.

# Running Instructions
## Backend
Run the command `python main.py` to start the backend server.

## Frontend
Run `npm run dev` in the `frontend` directory to start the frontend.

# API Endpoints Documentation
- **GET /api/spatial**: Retrieve spatial data for analysis.
- **POST /api/live**: Send live data to the server for processing.

# Scripts Description
- `main.py`: Main entry point for running the application.
- `spatial_api.py`: Contains logic for handling spatial data requests.
- `live_data.py`: Dedicated to live data handling.

# Contributing Guidelines
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add a new feature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a pull request.

# License
This project is licensed under the MIT License.