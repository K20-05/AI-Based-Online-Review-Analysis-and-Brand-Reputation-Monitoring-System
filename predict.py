import re

import joblib
import pandas as pd

print("\n========== PREDICTION STARTED ==========")


def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def rating_to_sentiment(r):
    try:
        r = float(r)
    except Exception:
        return "Unknown"

    if r <= 2:
        return "Negative"
    if r == 3:
        return "Neutral"
    if r >= 4:
        return "Positive"
    return "Unknown"


def clean_platform(x):
    if pd.isna(x):
        return "Unknown"
    x = str(x).lower()
    if "amazon" in x:
        return "Amazon"
    if "flipkart" in x:
        return "Flipkart"
    if "myntra" in x:
        return "Myntra"
    return "Other"


df = pd.read_csv("dataset/cleaned_reviews.csv")

if "sentiment" not in df.columns:
    print("Sentiment column missing -> creating from rating...")
    df["sentiment"] = df["rating"].apply(rating_to_sentiment)

print("Loading model + TF-IDF...")
model = joblib.load("dataset/sentiment_model.pkl")
tfidf = joblib.load("dataset/tfidf_vectorizer.pkl")

print("Predicting sentiments...")
if "cleaned_review" not in df.columns:
    if "review_text" not in df.columns:
        raise ValueError("Input file must contain 'cleaned_review' or 'review_text'.")
    df["cleaned_review"] = df["review_text"].fillna("").astype(str).apply(clean_text)
else:
    df["cleaned_review"] = df["cleaned_review"].fillna("").astype(str).apply(clean_text)

X = tfidf.transform(df["cleaned_review"])
df["predicted_sentiment"] = model.predict(X)

if "platform" in df.columns:
    df["platform"] = df["platform"].apply(clean_platform)

if "review_date" in df.columns:
    df["review_date"] = df["review_date"].astype(str).str.split("T").str[0]

final_cols = [
    c
    for c in [
        "review_id",
        "rating",
        "review_date",
        "platform",
        "cleaned_review",
        "sentiment",
        "predicted_sentiment",
    ]
    if c in df.columns
]

df[final_cols].to_csv("dataset/final_predictions.csv", index=False)

print("\nSaved: dataset/final_predictions.csv")
print("Columns saved:", final_cols)
print("\n========== PREDICTION COMPLETED ==========")
