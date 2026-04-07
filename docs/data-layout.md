# Data Layout

`backend/dataset/` is the canonical data root for BrandPulse.

## Folder Map

- `backend/dataset/raw/`
  Preferred location for raw source CSV files.
- `backend/dataset/csv/`
  Legacy-compatible raw CSV location that the app still reads.
- `backend/dataset/processed/`
  Generated datasets, predictions, trend outputs, and dashboard-ready machine-readable files.
- `backend/dataset/models/`
  Trained models, active vectorizers, and compatibility model artifacts.
- `backend/dataset/reports/`
  Metrics, reports, charts, and evaluation outputs.
- `backend/dataset/state/`
  Runtime state for dashboard users, connector cursors, and scheduler settings.

## Compatibility Notes

- `backend/dataset/models/tfidf_vectorizer_legacy.pkl`
- `backend/dataset/models/X_tfidf_legacy.pkl`

These legacy TF-IDF artifacts are intentionally kept for compatibility. `backend/feature_extraction.py` still refreshes them, so they are part of the supported project layout and should not be treated as junk files.

## Cleanup Guidance

- Safe cleanup targets are temporary caches regenerated from processed data.
- Raw CSVs and runtime artifacts in `backend/dataset/` are local-only project data and should not be committed to git.
- Keep local raw CSVs, active model artifacts, reports, and runtime state unless you are doing a deliberate reset.
