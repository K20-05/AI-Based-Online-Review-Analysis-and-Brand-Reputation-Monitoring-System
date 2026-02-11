import pandas as pd
import joblib
import warnings

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.exceptions import UndefinedMetricWarning

warnings.filterwarnings("ignore", category=UndefinedMetricWarning)

print("\n========== MODEL TRAINING STARTED ==========\n")

df = pd.read_csv("dataset/cleaned_reviews.csv")

# Safety cleaning
df["cleaned_review"] = df["cleaned_review"].fillna("").astype(str)
df = df[df["cleaned_review"].str.strip() != ""]

if "sentiment" not in df.columns:

    print("Sentiment column not found → generating from rating...")

    def convert_sentiment(r):
        if r <= 2:
            return "Negative"
        elif r == 3:
            return "Neutral"
        else:
            return "Positive"

    df["sentiment"] = df["rating"].apply(convert_sentiment)

y = df["sentiment"]

print("Loading TF-IDF features...")
X_tfidf = joblib.load("dataset/X_tfidf.pkl")

# Split dataset
print("Splitting dataset...")
X_train, X_test, y_train, y_test = train_test_split(
    X_tfidf,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("Training Logistic Regression...")
model = LogisticRegression(max_iter=300, class_weight="balanced")
model.fit(X_train, y_train)

print("\n========== MODEL RESULTS ==========")

y_pred = model.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
report = classification_report(y_test, y_pred, zero_division=0)

print(f"\nAccuracy: {accuracy * 100:.2f}%\n")
print("Classification report:\n\n ", report)

joblib.dump(model, "dataset/sentiment_model.pkl")

with open("dataset/model_report.txt", "w") as f:
    f.write(f"Accuracy: {accuracy * 100:.2f}%\n\n")
    f.write(f"Classification report:\n\n{report}")

print("\nModel saved: sentiment_model.pkl")
print("Report saved: model_report.txt")

print("\n========== MODEL TRAINING COMPLETED ==========\n")
