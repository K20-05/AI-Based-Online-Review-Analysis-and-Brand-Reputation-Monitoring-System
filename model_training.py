import re
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
import warnings

warnings.filterwarnings("ignore", category=UndefinedMetricWarning)

REPORT_PATH = Path("dataset/model_report.txt")
HISTORY_PATH = Path("dataset/training_history.csv")
ACCURACY_TREND_PATH = Path("dataset/accuracy_trend.png")
ACCURACY_DELTA_PATH = Path("dataset/accuracy_delta.png")

print("\n========== MODEL TRAINING STARTED ==========")


def extract_previous_accuracy(report_path: Path):
    if not report_path.exists():
        return None
    content = report_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"Accuracy:\s*([0-9]+(?:\.[0-9]+)?)%", content)
    if not match:
        return None
    return float(match.group(1))


def convert_sentiment(r):
    if r <= 2:
        return "Negative"
    if r == 3:
        return "Neutral"
    return "Positive"


def plot_training_history(history_df: pd.DataFrame):
    if history_df.empty:
        return

    x_vals = list(range(1, len(history_df) + 1))

    plt.figure(figsize=(9, 4.8))
    plt.plot(x_vals, history_df["accuracy"], marker="o", linewidth=2)
    plt.xticks(x_vals)
    plt.xlabel("Training Run")
    plt.ylabel("Accuracy (%)")
    plt.title("Model Accuracy Trend")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(ACCURACY_TREND_PATH, dpi=300)
    plt.close()

    delta_series = pd.to_numeric(history_df["delta"], errors="coerce").fillna(0.0)
    colors = ["#2e7d32" if d > 0 else "#c62828" if d < 0 else "#616161" for d in delta_series]
    plt.figure(figsize=(9, 4.8))
    plt.bar(x_vals, delta_series, color=colors)
    plt.axhline(0, color="black", linewidth=1)
    plt.xticks(x_vals)
    plt.xlabel("Training Run")
    plt.ylabel("Accuracy Delta (%)")
    plt.title("Accuracy Gain/Loss Per Run")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(ACCURACY_DELTA_PATH, dpi=300)
    plt.close()


df = pd.read_csv("dataset/cleaned_reviews.csv")
df["cleaned_review"] = df["cleaned_review"].fillna("").astype(str)
df = df[df["cleaned_review"].str.strip() != ""]

if "sentiment" not in df.columns:
    print("Sentiment column not found -> generating from rating...")
    df["sentiment"] = df["rating"].apply(convert_sentiment)

y = df["sentiment"]
X_text = df["cleaned_review"]

previous_accuracy = extract_previous_accuracy(REPORT_PATH)
if previous_accuracy is not None:
    print(f"Previous recorded accuracy: {previous_accuracy:.2f}%")
else:
    print("Previous recorded accuracy: not found (first run)")

print("Splitting dataset...")
X_train_text, X_test_text, y_train, y_test = train_test_split(
    X_text, y, test_size=0.2, random_state=42, stratify=y
)

print("Building TF-IDF features...")
tfidf = TfidfVectorizer(
    analyzer="char_wb",
    ngram_range=(3, 5),
    min_df=2,
    max_features=30000,
    sublinear_tf=True,
)
X_train = tfidf.fit_transform(X_train_text)
X_test = tfidf.transform(X_test_text)

print("Training Logistic Regression...")
model = LogisticRegression(
    max_iter=3000,
    class_weight="balanced",
    solver="lbfgs",
    C=1.0,
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
accuracy_pct = round(accuracy * 100, 2)
macro_f1 = round(f1_score(y_test, y_pred, average="macro"), 4)
report = classification_report(y_test, y_pred, zero_division=0)

cm = confusion_matrix(y_test, y_pred, labels=["Positive", "Neutral", "Negative"])
plt.figure(figsize=(6, 5))
sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    xticklabels=["Positive", "Neutral", "Negative"],
    yticklabels=["Positive", "Neutral", "Negative"],
)
plt.xlabel("Predicted")
plt.ylabel("Actual")
plt.title("Confusion Matrix")
plt.tight_layout()
plt.savefig("dataset/confusion_matrix.png", dpi=300)
plt.close()

if previous_accuracy is None:
    delta_text = "N/A (no previous baseline)"
    trend = "BASELINE"
    delta_value = ""
else:
    delta = round(accuracy_pct - previous_accuracy, 2)
    delta_value = delta
    if delta > 0:
        trend = "GAIN"
        delta_text = f"+{delta:.2f}%"
    elif delta < 0:
        trend = "LOSS"
        delta_text = f"{delta:.2f}%"
    else:
        trend = "NO CHANGE"
        delta_text = "0.00%"

print("\n========== MODEL RESULTS ==========")
print("\nConfusion Matrix:\n", cm)
print(f"\nCurrent Accuracy: {accuracy_pct:.2f}%")
print(f"Current Macro-F1: {macro_f1:.4f}")
print(f"Accuracy Delta: {delta_text} ({trend})")
print("\nClassification report:\n")
print(report)

joblib.dump(model, "dataset/sentiment_model.pkl")
joblib.dump(tfidf, "dataset/tfidf_vectorizer.pkl")

with REPORT_PATH.open("w", encoding="utf-8") as f:
    f.write(f"Accuracy: {accuracy_pct:.2f}%\n")
    if previous_accuracy is not None:
        f.write(f"Previous Accuracy: {previous_accuracy:.2f}%\n")
    f.write(f"Accuracy Delta: {delta_text}\n")
    f.write(f"Trend: {trend}\n")
    f.write(f"Macro-F1: {macro_f1:.4f}\n")
    f.write("Best C (manual): 1.0\n\n")
    f.write("Classification report:\n\n")
    f.write(report)

history_columns = [
    "accuracy",
    "previous_accuracy",
    "delta",
    "trend",
    "macro_f1",
    "best_c",
    "best_cv_macro_f1",
]

history_row = {
    "accuracy": accuracy_pct,
    "previous_accuracy": previous_accuracy,
    "delta": delta_value,
    "trend": trend,
    "macro_f1": macro_f1,
    "best_c": 1.0,
    "best_cv_macro_f1": "",
}

history_df = pd.DataFrame([history_row])
if HISTORY_PATH.exists():
    existing = pd.read_csv(HISTORY_PATH)
    if "timestamp" in existing.columns:
        existing = existing.drop(columns=["timestamp"])
    for col in history_columns:
        if col not in existing.columns:
            existing[col] = ""
    existing = existing[history_columns]
    history_df = pd.concat([existing, history_df], ignore_index=True)

history_df = history_df[history_columns]
history_df.to_csv(HISTORY_PATH, index=False)

plot_training_history(history_df)

print("\nModel saved: dataset/sentiment_model.pkl")
print("Vectorizer saved: dataset/tfidf_vectorizer.pkl")
print("Report saved: dataset/model_report.txt")
print("History saved: dataset/training_history.csv")
print("Accuracy trend graph saved: dataset/accuracy_trend.png")
print("Accuracy delta graph saved: dataset/accuracy_delta.png")
print("\n========== MODEL TRAINING COMPLETED ==========")
