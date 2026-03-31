# AI-Based Online Review Analysis and Brand Reputation Monitoring System

BrandPulse is a Flask-based review analytics project that preprocesses ecommerce reviews, trains a sentiment model, predicts review polarity, calculates brand reputation scores, and serves an interactive dashboard for admins, analysts, and marketing users.

## Current Status

This project is close to feature-complete for an academic/demo build:

- End-to-end ML pipeline is implemented.
- Flask backend APIs are implemented.
- Interactive frontend dashboard is implemented.
- Auth, role-based views, realtime review ingestion, and connector polling are implemented.
- Unit tests now cover core preprocessing, prediction-guard, and scoring logic.

## Project Structure

- `backend/app.py` - Flask entry point, API routes, auth/session wiring
- `backend/config.py` - shared paths and runtime configuration
- `backend/aspect_analysis.py` - aspect-level sentiment extraction for single, batch, and realtime flows
- `backend/preprocessing.py` - review normalization and cleaning
- `backend/feature_extraction.py` - TF-IDF feature dataset creation
- `backend/model_training.py` - model training, metrics, and reports
- `backend/predict.py` - single/batch sentiment prediction pipeline
- `backend/prediction_service.py` - API-facing prediction orchestration and payload shaping
- `backend/brand_score.py` - overall and per-brand reputation scoring
- `backend/dashboard_data.py` - cached dashboard data shaping
- `backend/dashboard_routes.py` - dashboard analytics endpoints
- `backend/realtime_reviews.py` - realtime ingestion and storage
- `backend/connectors.py` - realtime connector implementations
- `backend/connector_scheduler.py` - automatic polling scheduler
- `frontend/index.html` - dashboard markup
- `frontend/styles.css` - base dashboard layout, components, and responsive rules
- `frontend/premium-theme.css` - active theme entrypoint that imports the modular premium theme partials
- `frontend/premium-theme-*.css` - split premium theme layers for foundation, shell, dashboard, about, workspace, and responsive rules
- `frontend/app-shared.js` - shared frontend constants and stateless helpers loaded before the main runtime
- `frontend/app-history.js` - local activity history helpers and timeline rendering
- `frontend/app-admin.js` - admin-control rendering and user-management logic
- `frontend/app-analysis.js` - single-review and batch-analysis runtime logic
- `frontend/app.js` - core dashboard runtime, API wiring, routing, and shared view orchestration
- `frontend/premium-ui.js` - UI enhancement layer for animation and presentation polish
- `docs/` - project notes and implementation references
- `tools/` - utility scripts such as report generation helpers

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and update values as needed.

Important notes:

- `MONGO_URI` is optional. Leave it blank to run the project in CSV-only mode.
- The dashboard seeds a default admin account using `DASHBOARD_ADMIN_EMAIL` and `DASHBOARD_ADMIN_PASSWORD` on first run.

### 3. Place raw review CSV files

Use `backend/dataset/` as the single canonical data root for all project data:

- `backend/dataset/raw/` for the preferred structure
- `backend/dataset/csv/` for backward compatibility

Generated files like predictions, metrics, trends, and realtime review logs are not treated as raw input.

### 4. Run the backend

```bash
python backend/app.py
```

Open the dashboard at:

- `http://127.0.0.1:5000`

## End-to-End Pipeline

Run these if you want to rebuild artifacts from raw CSV files:

```bash
python backend/preprocessing.py
python backend/feature_extraction.py
python backend/model_training.py
python backend/predict.py
python backend/brand_score.py
```

Generated outputs are written to `backend/dataset/`, including:

- `cleaned_reviews.csv`
- `feature_dataset.csv`
- `sentiment_model.pkl`
- `tfidf_vectorizer.pkl`
- `model_metrics.csv`
- `model_report.txt`
- `final_predictions.csv`
- `brand_score.json`
- `brand_reputation_by_brand.csv`
- `sentiment_trends.csv`
- `platform_summary.csv`

Raw source files are primarily expected in `backend/dataset/raw/` or `backend/dataset/csv/`. The backend still supports legacy flat CSVs inside `backend/dataset/` for compatibility.

## Main API Endpoints

- `GET /api/health`
- `GET /api/docs`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/preprocess`
- `POST /api/features`
- `POST /api/train`
- `POST /api/predict`
- `POST /api/predict/batch`
- `POST /api/brand-score`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/trends`
- `GET /api/dashboard/keywords`
- `GET /api/dashboard/platforms`
- `POST /api/dashboard/refresh`
- `POST /api/reviews/realtime`
- `GET /api/connectors`
- `POST /api/connectors/poll`
- `GET /api/connectors/scheduler`
- `POST /api/connectors/scheduler`

## Testing

Run the lightweight unit test suite with:

```bash
python -m unittest discover -s tests -v
```

## Environment Variables

Supported configuration:

- `SECRET_KEY`
- `DASHBOARD_ADMIN_EMAIL`
- `DASHBOARD_ADMIN_PASSWORD`
- `MONGO_URI`
- `MONGO_DB_NAME`
- `MONGO_REVIEWS_COLLECTION`
- `MONGO_PREDICTIONS_COLLECTION`
- `MONGO_REALTIME_REVIEWS_COLLECTION`
- `MONGO_CONNECT_TIMEOUT_MS`

## Notes

- MongoDB integration is optional.
- `backend/dataset/` is the only canonical dataset folder for this project.
- Generated datasets and model artifacts are intentionally not committed when ignored by `.gitignore`.
- `frontend/styles.css` is still required because `frontend/premium-theme.css` imports it before the modular premium theme partials.
- Current model performance and dashboard outputs depend on the datasets present in `backend/dataset/`.
