import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib

print("\n========== FEATURE EXTRACTION STARTED ==========\n")

# Load cleaned dataset
df = pd.read_csv("dataset/cleaned_reviews.csv")

print(f"Total Cleaned Reviews : {len(df)}\n")

# -------------------------------
# ADD SENTIMENT LABEL HERE ✅
# -------------------------------
df["sentiment"] = df["rating"].apply(
    lambda r: "Negative" if r <= 2 else "Neutral" if r == 3 else "Positive"
)

# Extra feature
df["review_length"] = df["cleaned_review"].apply(lambda x: len(x.split()))

# TF-IDF
tfidf = TfidfVectorizer(max_features=3000, stop_words="english")
X_tfidf = tfidf.fit_transform(df["cleaned_review"])

tfidf_df = pd.DataFrame(
    X_tfidf.toarray(),
    columns=tfidf.get_feature_names_out()
)

# Combine features + sentiment
final_df = pd.concat(
    [tfidf_df, df["review_length"], df["sentiment"]],
    axis=1
)

# Save final feature dataset
final_df.to_csv("dataset/feature_dataset.csv", index=False)

joblib.dump(tfidf, "dataset/tfidf_vectorizer.pkl")

print("========== FEATURE EXTRACTION SUMMARY ==========\n")
print(f"TF-IDF Features : {X_tfidf.shape[1]}")
print("Additional Feature : review_length")
print("Label : sentiment\n")

print("Saved Files:")
print("- feature_dataset.csv")
print("- tfidf_vectorizer.pkl")

print("\n========== FEATURE EXTRACTION COMPLETED ==========\n")
