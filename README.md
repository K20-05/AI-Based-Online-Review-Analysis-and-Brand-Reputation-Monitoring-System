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
```bash
pip install -r requirements.txt
```

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
