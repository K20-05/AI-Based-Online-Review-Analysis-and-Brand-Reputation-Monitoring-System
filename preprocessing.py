import pandas as pd
import re

df = pd.read_csv("dataset/7817_1.csv")
print("\nAvailable columns:", df.columns.tolist())

rename_map = {
    "id": "review_id",
    "reviews.text": "review_text",
    "reviews.rating": "rating",
    "reviews.date": "review_date",
    "reviews.sourceURLs": "platform"
}
df = df.rename(columns={c: rename_map[c] for c in rename_map if c in df.columns})

cols_needed = ["review_id", "review_text", "rating", "review_date", "platform"]
cols_available = [c for c in cols_needed if c in df.columns]
df = df[cols_available]

if "review_text" in df.columns:
    df["review_text"] = df["review_text"].fillna("Unknown")

if "review_date" in df.columns:
    df["review_date"] = df["review_date"].fillna("Unknown")

if "platform" in df.columns:
    df["platform"] = df["platform"].fillna("Unknown")

# Rating: convert to numeric, drop missing ratings
if "rating" in df.columns:
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df = df.dropna(subset=["rating"])

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)     
    text = re.sub(r"\s+", " ", text).strip()     
    return text

df["cleaned_review"] = df["review_text"].apply(clean_text)

# remove empty cleaned reviews
df = df[df["cleaned_review"].str.strip() != ""]
df = df.drop(columns=["review_text"])

df.to_csv("dataset/cleaned_reviews.csv", index=False)

print("\nPreprocessing done (ONLY cleaning + missing filled).")
print("Saved: dataset/cleaned_reviews.csv")
print("Rows:", len(df))
