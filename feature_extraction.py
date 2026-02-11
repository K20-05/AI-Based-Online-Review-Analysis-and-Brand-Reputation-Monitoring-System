import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

print("\n========== FEATURE EXTRACTION STARTED ==========\n")

# Load cleaned dataset
df = pd.read_csv("dataset/cleaned_reviews.csv")

# Safety cleaning
df["cleaned_review"] = df["cleaned_review"].fillna("").astype(str)
df = df[df["cleaned_review"].str.strip() != ""]

# Generate sentiment from rating (if needed)
def rating_to_sentiment(r):
    r = float(r)
    if r <= 2:
        return "Negative"
    elif r == 3:
        return "Neutral"
    else:
        return "Positive"

df["sentiment"] = df["rating"].apply(rating_to_sentiment)

print("Applying TF-IDF Vectorization...")

tfidf = TfidfVectorizer(max_features=5000)
X_tfidf = tfidf.fit_transform(df["cleaned_review"])

# Convert TF-IDF to DataFrame (for academic record)
tfidf_df = pd.DataFrame(
    X_tfidf.toarray(),
    columns=tfidf.get_feature_names_out()
)

# Add extra feature: review length
tfidf_df["review_length"] = df["cleaned_review"].apply(len)

# Add sentiment label
tfidf_df["sentiment"] = df["sentiment"].values

# Save outputs
tfidf_df.to_csv("dataset/feature_dataset.csv", index=False)
joblib.dump(X_tfidf, "dataset/X_tfidf.pkl")
joblib.dump(tfidf, "dataset/tfidf_vectorizer.pkl")

print("\nSaved Files:")
print("dataset/feature_dataset.csv")
print("dataset/X_tfidf.pkl")
print("dataset/tfidf_vectorizer.pkl")

print("\n========== FEATURE EXTRACTION COMPLETED ==========\n")
