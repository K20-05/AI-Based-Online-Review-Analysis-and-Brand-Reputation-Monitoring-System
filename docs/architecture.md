# BrandPulse Architecture

## Overview

BrandPulse is organized as a Flask backend serving a role-aware analytics frontend.
The project is split so data processing, API routing, and UI rendering can evolve without forcing every change through one file.

## Backend Shape

- `backend/app.py` is the Flask composition root.
- `backend/auth_support.py` owns dashboard auth/session helpers and user-store behavior.
- `backend/auth_routes.py`, `backend/admin_routes.py`, `backend/dashboard_routes.py`, and `backend/core_routes.py` own route groups.
- `backend/dashboard_data.py` shapes analytics payloads for dashboard consumers.
- `backend/prediction_service.py` handles request parsing and single/batch prediction orchestration.
- `backend/realtime_reviews.py`, `backend/connectors.py`, and `backend/connector_scheduler.py` handle live ingestion.
- `backend/preprocessing.py`, `backend/feature_extraction.py`, `backend/model_training.py`, and `backend/brand_score.py` handle the ML and scoring pipeline.

## Frontend Shape

- `frontend/index.html` holds the shell and page markup.
- `frontend/app-shared.js` exposes shared constants and utility helpers.
- `frontend/app-dashboard.js` owns dashboard and summary presentation logic.
- `frontend/app-analysis.js` owns single-review and batch-analysis flows.
- `frontend/app-admin.js` owns admin-control, notifications, and user-management views.
- `frontend/app-history.js` owns local activity history rendering.
- `frontend/app-runtime-keywords.js` owns keyword-group loading and rendering.
- `frontend/app-runtime-customer-voice.js` owns customer-voice filters, complaint-topic hydration, and exports.
- `frontend/app-runtime-signals.js` owns trend, summary, export, and signal-panel analytics helpers.
- `frontend/app.js` remains the runtime coordinator for session state, routing, API calls, and cross-view orchestration.
- `frontend/premium-theme.css` is the theme entrypoint and imports the split premium theme partials.

## Data Flow

1. Raw CSV files enter through `backend/dataset/raw/` or `backend/dataset/csv/`.
2. The preprocessing and feature steps normalize reviews and prepare training data.
3. Generated datasets are written to `backend/dataset/processed/`, model artifacts to `backend/dataset/models/`, reports to `backend/dataset/reports/`, and runtime state to `backend/dataset/state/`.
   Legacy compatibility artifacts remain under `backend/dataset/models/`.
4. Prediction and scoring services shape API payloads for the dashboard.
5. The frontend runtime requests summary, brand, trend, keyword, and realtime endpoints and maps them into role-based workspaces.

## Why This Split

- Route blueprints keep backend concerns scoped by responsibility.
- Auth/session helpers are reusable without bloating the Flask entrypoint.
- Frontend feature modules reduce pressure on the main runtime file.
- Theme partials make visual maintenance safer than one large CSS sheet.
- The composition-root approach keeps startup and dependency wiring easy to follow.
