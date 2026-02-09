import pandas as pd
import joblib

print("\n========== SENTIMENT PREDICTION STARTED ==========\n")

# Load saved model and vectorizer
model = joblib.load("dataset/sentiment_model.pkl")
tfidf = joblib.load("dataset/tfidf_vectorizer.pkl")
feature_names = joblib.load("dataset/feature_names.pkl")

print("Model and TF-IDF Vectorizer Loaded Successfully\n")

# Load cleaned dataset
df = pd.read_csv("dataset/cleaned_reviews.csv")
df["cleaned_review"] = df["cleaned_review"].fillna("")

print(f"Total Reviews for Prediction : {len(df)}\n")

# Create review length feature
df["review_length"] = df["cleaned_review"].apply(lambda x: len(x.split()))

# Apply TF-IDF (DO NOT fit again)
X_tfidf = tfidf.transform(df["cleaned_review"])

# Convert to DataFrame with correct feature names
tfidf_df = pd.DataFrame(
    X_tfidf.toarray(),
    columns=tfidf.get_feature_names_out()
)

# Combine TF-IDF + review_length
X_final = pd.concat([tfidf_df, df["review_length"]], axis=1)

# Align feature order exactly as training
X_final = X_final[feature_names]

# Predict sentiment
df["predicted_sentiment"] = model.predict(X_final)

# Save predictions
df.to_csv("dataset/predicted_reviews.csv", index=False)

# ================= OUTPUT SUMMARY =================

print("========== PREDICTION SUMMARY ==========\n")
print("Sentiment Distribution:")
print(df["predicted_sentiment"].value_counts(), "\n")

print("Saved Output File:")
print("- predicted_reviews.csv")

print("\n========== SENTIMENT PREDICTION COMPLETED ==========\n")
