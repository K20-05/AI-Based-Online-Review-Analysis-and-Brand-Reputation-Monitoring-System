import pandas as pd
from collections import Counter
import matplotlib.pyplot as plt

# Load cleaned dataset
df = pd.read_csv("dataset/cleaned_reviews.csv")

# Use the correct column name
all_words = " ".join(df["cleaned_review"].astype(str))

# Split into words
words = all_words.split()

# Count most common 20 words
word_counts = Counter(words).most_common(20)

# Prepare labels and counts
labels = [word for word, count in word_counts]
values = [count for word, count in word_counts]

# Plot bar graph
plt.figure(figsize=(12, 6))
plt.bar(labels, values)
plt.xticks(rotation=45, ha='right')
plt.title("Top 20 Most Frequent Words in Reviews")
plt.xlabel("Words")
plt.ylabel("Frequency")
plt.tight_layout()

# Save graph for PPT
plt.savefig("dataset/word_frequency.png", dpi=300)

print("Graph saved: dataset/word_frequency.png")
