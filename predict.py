import pandas as pd
import joblib

print("\n========== PREDICTION STARTED ==========\n")

df = pd.read_csv("dataset/cleaned_reviews.csv")

if "sentiment" not in df.columns:
    print("Sentiment column missing → creating from rating...")

    def rating_to_sentiment(r):
        try:
            r = float(r)
        except:
            return "Unknown"

        if r <= 2:
            return "Negative"
        elif r == 3:
            return "Neutral"
        elif r >= 4:
            return "Positive"
        return "Unknown"

    df["sentiment"] = df["rating"].apply(rating_to_sentiment)

print("Loading model + TF-IDF...")
model = joblib.load("dataset/sentiment_model.pkl")
tfidf = joblib.load("dataset/tfidf_vectorizer.pkl")

print("Predicting sentiments...")
df["cleaned_review"] = df["cleaned_review"].fillna("").astype(str)
X = tfidf.transform(df["cleaned_review"])
df["predicted_sentiment"] = model.predict(X)

def clean_platform(x):
    if pd.isna(x):
        return "Unknown"
    x = str(x).lower()
    if "amazon" in x:
        return "Amazon"
    elif "flipkart" in x:
        return "Flipkart"
    elif "myntra" in x:
        return "Myntra"
    else:
        return "Other"

if "platform" in df.columns:
    df["platform"] = df["platform"].apply(clean_platform)

if "review_date" in df.columns:
    df["review_date"] = df["review_date"].astype(str).str.split("T").str[0]

final_cols = [c for c in [
    "review_id", "rating", "review_date", "platform",
    "cleaned_review", "sentiment", "predicted_sentiment"
] if c in df.columns]

df[final_cols].to_csv("dataset/final_predictions.csv", index=False)

print("\nSaved: dataset/final_predictions.csv")
print("Columns saved:", final_cols)
print("\n========== PREDICTION COMPLETED ==========\n")
