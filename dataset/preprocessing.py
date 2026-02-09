import pandas as pd
import re

print("\n================ PREPROCESSING STARTED ================\n")

# Load dataset
df = pd.read_csv("dataset/7817_1.csv")

print("✔ Dataset Loaded")
print(f"Total Records : {len(df)}")
print(f"Total Columns : {df.shape[1]}\n")

# Rename columns
df.rename(columns={
    "id": "review_id",
    "reviews.text": "review_text",
    "reviews.rating": "rating",
    "reviews.date": "review_date",
    "reviews.sourceURLs": "platform"
}, inplace=True)

# Keep only required columns
df = df[[c for c in ["review_id", "review_text", "rating", "review_date", "platform"] if c in df.columns]]

initial_rows = len(df)

# Remove missing values
df.dropna(subset=["review_text", "rating"], inplace=True)

# Handle missing dates
df["review_date"] = df["review_date"].fillna("Unknown")

# Standardize platform name
df["platform"] = "Amazon"

# Clean text
def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

df["cleaned_review"] = df["review_text"].apply(clean_text)

# Remove short/noisy reviews
df = df[df["cleaned_review"].str.len() > 5]

# ❌ REMOVE ORIGINAL review_text COLUMN (IMPORTANT)
df.drop(columns=["review_text"], inplace=True)

final_rows = len(df)

# Save cleaned dataset
df.to_csv("dataset/cleaned_reviews.csv", index=False)

# Summary
print("================ PREPROCESSING SUMMARY ================\n")
print(f"Records before cleaning : {initial_rows}")
print(f"Records after cleaning  : {final_rows}")
print(f"Records removed         : {initial_rows - final_rows}")
print(f"Removal percentage      : {((initial_rows - final_rows) / initial_rows) * 100:.2f}%\n")

print("Final Columns in cleaned_reviews.csv:")
print(df.columns.tolist(), "\n")

print(" cleaned_reviews.csv saved successfully")
print("\n================ PREPROCESSING COMPLETED ================\n")
