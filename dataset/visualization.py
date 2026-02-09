import pandas as pd
import matplotlib.pyplot as plt

print("\n========== VISUALIZATION STARTED ==========\n")

# Load final predictions
df = pd.read_csv("dataset/final_with_sentiment.csv")

# Count sentiments
sentiment_counts = df["predicted_sentiment"].value_counts()

print("Sentiment Counts:")
print(sentiment_counts, "\n")

# ---------------- PIE CHART ----------------
plt.figure(figsize=(6, 6))
plt.pie(
    sentiment_counts,
    labels=sentiment_counts.index,
    autopct="%1.1f%%",
    startangle=140
)
plt.title("Sentiment Distribution of Reviews")
plt.tight_layout()
plt.show()

# ---------------- BAR CHART ----------------
plt.figure(figsize=(6, 4))
plt.bar(
    sentiment_counts.index,
    sentiment_counts.values
)
plt.title("Sentiment Count Comparison")
plt.xlabel("Sentiment Type")
plt.ylabel("Number of Reviews")
plt.tight_layout()
plt.show()

print("\n========== VISUALIZATION COMPLETED ==========\n")
 