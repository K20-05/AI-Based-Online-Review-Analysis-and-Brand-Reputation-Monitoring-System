<<<<<<< HEAD
# AI-Based Online Review Analysis and Brand Reputation Monitoring

This project analyzes customer reviews with NLP + machine learning, predicts sentiment, and computes a brand reputation score.

## Current Project Structure
- `preprocessing.py`: Cleans raw dataset and writes `dataset/cleaned_reviews.csv`
- `feature_extraction.py`: Builds TF-IDF feature files (legacy/offline analysis)
- `model_training.py`: Trains the classifier and saves model artifacts
- `predict.py`: Generates file-based predictions to `dataset/final_predictions.csv`
- `brand_score.py`: Computes reputation score from `dataset/final_predictions.csv`
- `backend_api.py`: REST backend interface for prediction + scoring

## Backend API Interface

### 1. Install dependencies
=======
# AI-Based Online Review Analysis and Brand Reputation Monitoring System

This project has been rebuilt from scratch according to the project planner. It implements a full academic pipeline for online review analysis with Flask, MongoDB integration, TF-IDF feature extraction, supervised sentiment classification, brand reputation scoring, and an interactive dashboard.

## Planner-Aligned Architecture

### Backend
- `backend/app.py`: Flask API and dashboard backend
- `backend/preprocessing.py`: Multi-source review preprocessing and sentiment label generation
- `backend/feature_extraction.py`: TF-IDF feature dataset generation
- `backend/model_training.py`: Train/test split, Logistic Regression and Naive Bayes training, evaluation
- `backend/predict.py`: Batch sentiment prediction and prediction export
- `backend/brand_score.py`: Brand reputation score and trend summaries
- `backend/visualization.py`: Sentiment, trend, keyword, and platform charts
- `backend/database.py`: MongoDB read/write helpers
- `backend/config.py`: Paths and environment configuration

### Frontend
- `frontend/index.html`: Interactive dashboard using HTML, CSS, and JavaScript

### Dataset
Place raw CSV review datasets in `backend/dataset/`. The current rebuild supports both:
- Amazon-style review schema
- App-review schema using `reviewId`, `content`, `score`, `at`, `appName`

## Planner Workflow

1. Review Data Collection
2. Data Preprocessing
3. Feature Extraction
4. Dataset Splitting
5. Sentiment Model Training
6. Model Evaluation
7. Brand Reputation Scoring
8. Backend Processing
9. Visualization and Dashboard Output

## Installation

>>>>>>> 98618ec (Update project files)
```bash
pip install -r requirements.txt
```

<<<<<<< HEAD
### 2. Ensure model artifacts exist
Run training once if needed:
```bash
python model_training.py
```
This creates:
- `dataset/sentiment_model.pkl`
- `dataset/tfidf_vectorizer.pkl`

### 3. Run backend server
```bash
uvicorn backend_api:app --reload --host 0.0.0.0 --port 8000
```

API docs:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## API Endpoints
- `GET /health`: Check API and model artifact status
- `POST /predict`: Predict one review sentiment
- `POST /predict/batch`: Predict multiple reviews and optionally save `dataset/final_predictions.csv`
- `GET /brand-score`: Compute score from saved `dataset/final_predictions.csv`

## Example Request

### `POST /predict`
```json
{
  "review_text": "Delivery was quick and product quality is excellent",
  "rating": 5,
  "platform": "Amazon"
}
```

### `POST /predict/batch`
```json
{
  "save_to_dataset": true,
  "reviews": [
    {
      "review_id": 1,
      "review_text": "Very good product",
      "rating": 5,
      "platform": "Amazon",
      "review_date": "2026-02-16"
    },
    {
      "review_id": 2,
      "review_text": "Bad fitting and poor quality",
      "rating": 1,
      "platform": "Flipkart",
      "review_date": "2026-02-16"
    }
  ]
}
```
=======
Optional MongoDB environment variables:

```bash
set MONGO_URI=mongodb://localhost:27017/
set MONGO_DB_NAME=brand_review_analysis
```

## End-to-End Run

### 1. Preprocess all raw datasets
```bash
python backend/preprocessing.py
```

### 2. Build feature dataset
```bash
python backend/feature_extraction.py
```

### 3. Train classifiers
```bash
python backend/model_training.py
```

### 4. Generate predictions
```bash
python backend/predict.py
```

### 5. Compute brand reputation score
```bash
python backend/brand_score.py
```

### 6. Start the Flask backend
```bash
python backend/app.py
```

Open the dashboard in a browser:
- `http://127.0.0.1:5000`

## API Endpoints

- `GET /api/health`
- `POST /api/preprocess`
- `POST /api/train`
- `POST /api/predict`
- `POST /api/predict/batch`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/trends`
- `GET /api/dashboard/keywords`
- `GET /api/dashboard/platforms`
- `POST /api/dashboard/refresh`

## Output Files

Generated inside `backend/dataset/`:
- `cleaned_reviews.csv`
- `feature_dataset.csv`
- `sentiment_model.pkl`
- `tfidf_vectorizer.pkl`
- `model_metrics.csv`
- `model_report.txt`
- `final_predictions.csv`
- `brand_score.json`
- `sentiment_trends.csv`
- `platform_summary.csv`
- `confusion_matrix.png`
- `sentiment_distribution.png`
- `review_trends.png`
- `keyword_frequency.png`
- `platform_distribution.png`

## Planner Coverage

This rebuild covers:
- preprocessing of raw review text
- TF-IDF feature extraction
- train/test splitting
- Logistic Regression and Naive Bayes classification
- accuracy, precision, recall, and F1-score evaluation
- brand reputation scoring
- sentiment trend analysis
- keyword frequency analysis
- HTML/CSS/JavaScript dashboard
- MongoDB integration for processed reviews and predictions
>>>>>>> 98618ec (Update project files)
