import pandas as pd

df = pd.read_csv("dataset/final_predictions.csv")

pos = (df["predicted_sentiment"] == "Positive").sum()
neg = (df["predicted_sentiment"] == "Negative").sum()
neu = (df["predicted_sentiment"] == "Neutral").sum()
total = len(df)

brand_score = ((pos - neg) / total) * 100

print("\n===== BRAND REPUTATION SUMMARY =====")
print("Total Reviews   :", total)
print("Positive Reviews:", pos)
print("Negative Reviews:", neg)
print("Neutral Reviews :", neu)
print("Brand Score     :", round(brand_score, 2), "%")

if brand_score > 20:
    print("Interpretation  : Strong brand reputation")
elif brand_score >= 0:
    print("Interpretation  : Average / stable brand reputation")
else:
    print("Interpretation  : Weak brand reputation (needs improvement)")
