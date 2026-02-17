import pandas as pd

print("\n========== BRAND REPUTATION SCORING ==========")

df = pd.read_csv("dataset/final_predictions.csv")
total = len(df)

if total == 0:
    print("No reviews found in dataset/final_predictions.csv")
    with open("dataset/brand_score.txt", "w") as f:
        f.write("No reviews found. Brand Reputation Score: 0.00\n")
    print("Saved -> dataset/brand_score.txt")
    print("\n========== COMPLETED ==========")
    raise SystemExit(0)

positive = len(df[df["predicted_sentiment"] == "Positive"])
neutral = len(df[df["predicted_sentiment"] == "Neutral"])
negative = len(df[df["predicted_sentiment"] == "Negative"])

pos_pct = (positive / total) * 100
neu_pct = (neutral / total) * 100
neg_pct = (negative / total) * 100

brand_score = ((positive - negative) / total) * 100

print("Total Reviews:", total)
print("Positive:", positive)
print("Neutral:", neutral)
print("Negative:", negative)

print("\nSentiment Percentages:")
print(f"Positive: {pos_pct:.2f}%")
print(f"Neutral: {neu_pct:.2f}%")
print(f"Negative: {neg_pct:.2f}%")

print(f"\nBrand Reputation Score: {brand_score:.2f}")

with open("dataset/brand_score.txt", "w") as f:
    f.write(f"Total Reviews: {total}\n")
    f.write(f"Positive: {positive}\n")
    f.write(f"Neutral: {neutral}\n")
    f.write(f"Negative: {negative}\n\n")
    f.write(f"Positive %: {pos_pct:.2f}\n")
    f.write(f"Neutral %: {neu_pct:.2f}\n")
    f.write(f"Negative %: {neg_pct:.2f}\n\n")
    f.write(f"Brand Reputation Score: {brand_score:.2f}")

print("\nSaved -> dataset/brand_score.txt")
print("\n========== COMPLETED ==========")
