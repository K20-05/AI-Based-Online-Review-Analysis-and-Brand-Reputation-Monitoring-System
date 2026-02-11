import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

print("\n========== FEATURE EXTRACTION STARTED ==========\n")

df = pd.read_csv("dataset/cleaned_reviews.csv")

df["cleaned_review"] = df["cleaned_review"].fillna("").astype(str)
df = df[df["cleaned_review"].str.strip() != ""]

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

tfidf_df = pd.DataFrame(
    X_tfidf.toarray(),
    columns=tfidf.get_feature_names_out()
)

tfidf_df["review_length"] = df["cleaned_review"].apply(len)

tfidf_df["sentiment"] = df["sentiment"].values

tfidf_df.to_csv("dataset/feature_dataset.csv", index=False)
joblib.dump(X_tfidf, "dataset/X_tfidf.pkl")
joblib.dump(tfidf, "dataset/tfidf_vectorizer.pkl")

print("\nSaved Files:")
print("dataset/feature_dataset.csv")
print("dataset/X_tfidf.pkl")
print("dataset/tfidf_vectorizer.pkl")

print("\n========== FEATURE EXTRACTION COMPLETED ==========\n")
