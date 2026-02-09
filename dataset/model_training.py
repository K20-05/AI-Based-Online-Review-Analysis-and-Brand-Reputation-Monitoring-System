import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

print("\n========== MODEL TRAINING STARTED ==========\n")

# Load features and labels
X = pd.read_csv("dataset/tfidf_features.csv")
df = pd.read_csv("dataset/cleaned_reviews.csv")

# Create sentiment labels
df["sentiment"] = df["rating"].apply(
    lambda r: "Negative" if r <= 2 else "Neutral" if r == 3 else "Positive"
)
y = df["sentiment"]

print("Sentiment Distribution:")
print(y.value_counts(), "\n")

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Train Logistic Regression
model = LogisticRegression(max_iter=300)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(f"Model Accuracy : {accuracy_score(y_test, y_pred) * 100:.2f}%\n")
print("Classification Report:")
print(classification_report(y_test, y_pred))

# Save model
joblib.dump(model, "dataset/sentiment_model.pkl")

print("Model expects features :", model.coef_.shape[1])
print("Saved Model: sentiment_model.pkl")

print("\n========== MODEL TRAINING COMPLETED ==========\n")
