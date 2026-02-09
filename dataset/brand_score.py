import pandas as pd

print("\n========== BRAND REPUTATION ANALYSIS STARTED ==========\n")

# Load prediction results
df = pd.read_csv("dataset/predicted_reviews.csv")

print(f"Total Reviews Analysed : {len(df)}\n")

# Count sentiments
positive_count = (df["predicted_sentiment"] == "Positive").sum()
neutral_count  = (df["predicted_sentiment"] == "Neutral").sum()
negative_count = (df["predicted_sentiment"] == "Negative").sum()

total_reviews = positive_count + neutral_count + negative_count

# Brand reputation score formula
brand_score = ((positive_count - negative_count) / total_reviews) * 100

# ================= OUTPUT SUMMARY =================

print("Sentiment Distribution:")
print(f"Positive Reviews : {positive_count}")
print(f"Neutral Reviews  : {neutral_count}")
print(f"Negative Reviews : {negative_count}\n")

print(f"Brand Reputation Score : {brand_score:.2f}%\n")

# Simple interpretation
if brand_score > 50:
    status = "Excellent Brand Reputation"
elif brand_score > 20:
    status = "Good Brand Reputation"
elif brand_score > 0:
    status = "Average Brand Reputation"
else:
    status = "Poor Brand Reputation"

print(f"Brand Health Status : {status}")

print("\n========== BRAND REPUTATION ANALYSIS COMPLETED ==========\n")
