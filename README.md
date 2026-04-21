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

- `backend/app.py` - Flask composition root and app startup
- `backend/auth_support.py` - shared dashboard auth, session, and user-store helpers
- `backend/config.py` - shared paths and runtime configuration
- `backend/core_routes.py` - core system, pipeline, prediction, realtime, and connector endpoints
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
- `frontend/app-dashboard.js` - dashboard, summary, and signal presentation helpers
- `frontend/app-history.js` - local activity history helpers and timeline rendering
- `frontend/app-admin.js` - admin-control rendering and user-management logic
- `frontend/app-analysis.js` - single-review and batch-analysis runtime logic
- `frontend/app-runtime-keywords.js` - dashboard keyword-group loading and sentiment keyword rendering
- `frontend/app-runtime-customer-voice.js` - customer-voice filters, complaint-topic loading, and export helpers
- `frontend/app-runtime-signals.js` - trend, export, summary, and signal-panel analytics helpers
- `frontend/app.js` - core dashboard runtime, API wiring, routing, and shared view orchestration
- `frontend/premium-ui.js` - UI enhancement layer for animation and presentation polish
- `docs/architecture.md` - project architecture overview for frontend/backend structure
- `docs/data-layout.md` - dataset folder layout and retained compatibility artifacts
- `docs/` - project notes and implementation references
- `tools/` - utility scripts such as report generation helpers

## Architecture Notes

- `backend/app.py` now acts as a composition root that wires blueprints together instead of directly owning every route.
- `backend/auth_support.py` keeps dashboard auth/session and user-store behavior out of the Flask entrypoint.
- Route responsibilities are split across auth, admin, dashboard analytics, and core system/pipeline endpoints.
- `frontend/app.js` remains the runtime coordinator, while feature slices such as dashboard, analysis, admin, history, keywords, customer voice, and analytics signals are separated into dedicated modules.
- Theme styling is layered through `premium-theme.css` plus focused partials so visual edits stay localized.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Copy `.env.example` to `.env` and update values as needed.

Important notes:

- Set `SECRET_KEY` to a long random value before running shared or deployed environments.
- Set `DASHBOARD_ADMIN_PASSWORD` to a strong password if you want the configured admin account to be auto-seeded on first run.
- `APP_HOST` defaults to `0.0.0.0` so the app can bind correctly in deployed environments.
- Port resolution is `APP_PORT`, then `PORT`, then `FLASK_RUN_PORT`, then `5000`.
- `ALLOWED_CORS_ORIGINS` should list the frontend origins that are allowed to make credentialed requests.
- Set `FRONTEND_API_BASE_URL` when the dashboard UI and API are deployed on different origins.
- `MONGO_URI` is optional. Leave it blank to run the project in CSV-only mode.
- `POST /api/auth/register` creates an account only. Users sign in separately through `POST /api/auth/login`.

### 3. Place raw review CSV files

Use `backend/dataset/` as the single canonical data root for all project data:

- `backend/dataset/raw/` for the preferred structure
- `backend/dataset/csv/` for backward compatibility
- `backend/dataset/processed/` for generated datasets and dashboard-ready machine-readable outputs
- `backend/dataset/models/` for trained model and TF-IDF artifacts
- `backend/dataset/reports/` for metrics, charts, and evaluation reports
- `backend/dataset/state/` for scheduler, connector, and dashboard runtime state

See `docs/data-layout.md` for the maintained folder map and compatibility notes.

Raw datasets and runtime artifacts under `backend/dataset/` are intended to stay local to your machine or deployment environment. They are ignored by git and should not be committed; use `tests/fixtures/` for lightweight repo-safe sample data.

Generated files like predictions, metrics, trends, and realtime review logs are not treated as raw input.

### 4. Run the backend locally

```bash
python backend/app.py
```

Open the dashboard at:

- `http://127.0.0.1:5000`

## Deployment

For production-style serving, use Waitress instead of Flask's built-in development server:

```bash
python -m backend.serve
```

Deployment notes:

- `backend/serve.py` uses Waitress and the same shared runtime config as local development.
- The app binds to `0.0.0.0` by default when no host is configured.
- The runtime port honors `APP_PORT` first and `PORT` second, which fits common deployment platforms.
- Set `SESSION_COOKIE_SECURE=1` when the app is behind HTTPS.
- If the frontend is hosted on a different origin, set `ALLOWED_CORS_ORIGINS` to that public origin.
- If the frontend and API are on different origins, set `FRONTEND_API_BASE_URL` to the backend public origin (for example `https://api.example.com`).

## End-to-End Pipeline

Run these if you want to rebuild artifacts from raw CSV files:

```bash
python backend/preprocessing.py
python backend/feature_extraction.py
python backend/model_training.py
python backend/predict.py
python backend/brand_score.py
```

Generated outputs are written under the structured `backend/dataset/` folders:

- `backend/dataset/processed/cleaned_reviews.csv`
- `backend/dataset/processed/feature_dataset.csv`
- `backend/dataset/processed/final_predictions.csv`
- `backend/dataset/processed/brand_score.json`
- `backend/dataset/processed/brand_reputation_by_brand.csv`
- `backend/dataset/processed/sentiment_trends.csv`
- `backend/dataset/processed/platform_summary.csv`
- `backend/dataset/models/sentiment_model.pkl`
- `backend/dataset/models/tfidf_vectorizer.pkl`
- `backend/dataset/reports/model_metrics.csv`
- `backend/dataset/reports/model_report.txt`

Raw source files are primarily expected in `backend/dataset/raw/` or `backend/dataset/csv/`. The backend still supports legacy flat CSVs inside `backend/dataset/` for compatibility.
Legacy model compatibility files such as `tfidf_vectorizer_legacy.pkl` and `X_tfidf_legacy.pkl` are intentionally retained under `backend/dataset/models/`.

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

Auth flow note:
Create an account with `POST /api/auth/register`, then authenticate with `POST /api/auth/login` to start a session.

## Testing

Run the lightweight unit test suite with:

```bash
python -m unittest discover -s tests -v
```

## Environment Variables

Supported configuration:

- `APP_HOST`
- `APP_PORT`
- `PORT`
- `SECRET_KEY`
- `DASHBOARD_ADMIN_EMAIL`
- `DASHBOARD_ADMIN_PASSWORD`
- `ALLOWED_CORS_ORIGINS`
- `SESSION_COOKIE_SECURE`
- `FRONTEND_API_BASE_URL`
- `MONGO_URI`
- `MONGO_DB_NAME`
- `MONGO_REVIEWS_COLLECTION`
- `MONGO_PREDICTIONS_COLLECTION`
- `MONGO_REALTIME_REVIEWS_COLLECTION`
- `MONGO_CONNECT_TIMEOUT_MS`

## Notes

- MongoDB integration is optional.
- `backend/dataset/` is the only canonical dataset folder for this project.
- `backend/dataset/raw/`, `processed/`, `models/`, `reports/`, and `state/` now separate raw inputs from generated runtime artifacts.
- Raw datasets, generated datasets, model artifacts, reports, and runtime state under `backend/dataset/` are intentionally local and should not be committed to git.
- `frontend/styles.css` is still required because `frontend/premium-theme.css` imports it before the modular premium theme partials.
- Current model performance and dashboard outputs depend on the datasets present in `backend/dataset/`.
