import pandas as pd
import matplotlib.pyplot as plt

print("\n========== VISUALIZATION STARTED ==========\n")

file_path = "dataset/final_predictions.csv"
df = pd.read_csv(file_path)

# ---------------- 2) Ensure predicted_sentiment exists ----------------
if "predicted_sentiment" not in df.columns:
    raise KeyError(
        "Column 'predicted_sentiment' not found in final_with_sentiment.csv.\n"
        "Make sure predict.py created this column."
    )

df["predicted_sentiment"] = df["predicted_sentiment"].fillna("Unknown").astype(str).str.strip()

mapping = {
    "positive": "Positive",
    "pos": "Positive",
    "1": "Positive",

    "neutral": "Neutral",
    "neu": "Neutral",
    "0": "Neutral",

    "negative": "Negative",
    "neg": "Negative",
    "-1": "Negative",

    "unknown": "Unknown"
}
df["predicted_sentiment"] = df["predicted_sentiment"].str.lower().map(mapping).fillna("Unknown")

# ---------------- 4) Force order + include missing classes ----------------
order = ["Positive", "Neutral", "Negative", "Unknown"]
sentiment_counts = df["predicted_sentiment"].value_counts().reindex(order, fill_value=0)

print("Sentiment Counts:")
print(sentiment_counts, "\n")

plot_counts = sentiment_counts.drop(labels=["Unknown"], errors="ignore")

# If all are zero (just in case)
if plot_counts.sum() == 0:
    raise ValueError("No valid sentiment values found to plot.")

plt.figure(figsize=(7, 7))
wedges, texts, autotexts = plt.pie(
    plot_counts.values,
    labels=plot_counts.index,
    autopct="%1.1f%%",
    startangle=140
)

plt.title("Sentiment Distribution of Reviews")
plt.tight_layout()
plt.savefig("dataset/sentiment_pie.png", dpi=300)
plt.show()

plt.figure(figsize=(7, 5))
bars = plt.bar(plot_counts.index, plot_counts.values)

plt.title("Sentiment Count Comparison")
plt.xlabel("Sentiment Type")
plt.ylabel("Number of Reviews")

for bar in bars:
    height = bar.get_height()
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        str(int(height)),
        ha="center",
        va="bottom"
    )

plt.tight_layout()
plt.savefig("dataset/sentiment_bar.png", dpi=300)
plt.show()

print("\nSaved charts:")
print(" - dataset/sentiment_pie.png")
print(" - dataset/sentiment_bar.png")
print("\n========== VISUALIZATION COMPLETED ==========\n")
