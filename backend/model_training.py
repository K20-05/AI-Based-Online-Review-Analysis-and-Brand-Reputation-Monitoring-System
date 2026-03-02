from __future__ import annotations

from pathlib import Path
import sys

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import FeatureUnion
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import (
    CONFUSION_MATRIX_PATH,
    MODEL_ACCURACY_CHART_PATH,
    MODEL_METRICS_PATH,
    MODEL_PATH,
    MODEL_REPORT_PATH,
    TRAINING_HISTORY_CHART_PATH,
    TRAINING_HISTORY_PATH,
    TRAINING_SAMPLE_LIMIT_PER_DATASET,
    VECTORIZER_PATH,
)
from backend.preprocessing import label_from_rating, load_cleaned_reviews
from backend.preprocessing import sample_reviews_per_dataset


def evaluate_model(name: str, model, x_train, x_test, y_train, y_test) -> dict:
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    return {
        "model": name,
        "model_object": model,
        "predictions": predictions,
        "accuracy": round(accuracy_score(y_test, predictions) * 100, 2),
        "precision_macro": round(precision_score(y_test, predictions, average="macro", zero_division=0), 4),
        "recall_macro": round(recall_score(y_test, predictions, average="macro", zero_division=0), 4),
        "f1_macro": round(f1_score(y_test, predictions, average="macro"), 4),
    }


def build_search_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        (
                            "word_tfidf",
                            TfidfVectorizer(
                                analyzer="word",
                                ngram_range=(1, 2),
                                min_df=2,
                                max_features=40000,
                                sublinear_tf=True,
                            ),
                        ),
                        (
                            "char_tfidf",
                            TfidfVectorizer(
                                analyzer="char_wb",
                                ngram_range=(3, 5),
                                min_df=2,
                                sublinear_tf=True,
                            ),
                        ),
                    ]
                ),
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=5000,
                    solver="saga",
                ),
            ),
        ]
    )


def tune_model(x_train_text, y_train) -> tuple[Pipeline, dict]:
    pipeline = build_search_pipeline()
    search = GridSearchCV(
        estimator=pipeline,
        param_grid={
            "features__word_tfidf__ngram_range": [(1, 1), (1, 2), (1, 3)],
            "features__word_tfidf__max_features": [30000, 40000, 60000],
            "features__word_tfidf__min_df": [2, 3],
            "features__char_tfidf__ngram_range": [(3, 5), (4, 6)],
            "model__C": [0.5, 1.0, 2.0, 4.0],
            "model__class_weight": [None, "balanced"],
        },
        scoring="accuracy",
        cv=3,
        n_jobs=-1,
        verbose=0,
    )
    search.fit(x_train_text, y_train)
    return search.best_estimator_, search.best_params_


def build_training_history(model, x_train, x_test, y_train, y_test) -> pd.DataFrame:
    labels = sorted(y_train.astype(str).unique())
    rows = []
    train_sizes = [0.2, 0.4, 0.6, 0.8, 1.0]
    for fraction in train_sizes:
        size = max(2, int(len(y_train) * fraction))
        x_subset = x_train[:size]
        y_subset = y_train.iloc[:size]
        if y_subset.nunique() < 2:
            continue
        fitted = clone(model)
        fitted.fit(x_subset, y_subset)
        train_pred = fitted.predict(x_subset)
        test_pred = fitted.predict(x_test)
        train_proba = fitted.predict_proba(x_subset)
        test_proba = fitted.predict_proba(x_test)
        rows.append(
            {
                "train_size": size,
                "train_accuracy": round(accuracy_score(y_subset, train_pred) * 100, 2),
                "validation_accuracy": round(accuracy_score(y_test, test_pred) * 100, 2),
                "train_loss": round(log_loss(y_subset, train_proba, labels=labels), 4),
                "validation_loss": round(log_loss(y_test, test_proba, labels=labels), 4),
            }
        )
    return pd.DataFrame(rows)


def save_metric_charts(accuracy: float, history_df: pd.DataFrame) -> None:
    plt.figure(figsize=(7, 4.5))
    plt.bar(["Logistic Regression"], [accuracy], color="#2a9d8f")
    plt.title("Model Accuracy")
    plt.xlabel("Model")
    plt.ylabel("Accuracy (%)")
    plt.tight_layout()
    plt.savefig(MODEL_ACCURACY_CHART_PATH, dpi=300)
    plt.close()

    if history_df.empty:
        return

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(history_df["train_size"], history_df["train_accuracy"], marker="o", label="Train Accuracy")
    axes[0].plot(history_df["train_size"], history_df["validation_accuracy"], marker="o", label="Validation Accuracy")
    axes[0].set_title("Accuracy vs Train Size")
    axes[0].set_xlabel("Training Samples")
    axes[0].set_ylabel("Accuracy (%)")
    axes[0].legend()

    axes[1].plot(history_df["train_size"], history_df["train_loss"], marker="o", label="Train Loss")
    axes[1].plot(history_df["train_size"], history_df["validation_loss"], marker="o", label="Validation Loss")
    axes[1].set_title("Loss vs Train Size")
    axes[1].set_xlabel("Training Samples")
    axes[1].set_ylabel("Log Loss")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(TRAINING_HISTORY_CHART_PATH, dpi=300)
    plt.close()


def train_models() -> pd.DataFrame:
    df = load_cleaned_reviews()
    df = sample_reviews_per_dataset(df, TRAINING_SAMPLE_LIMIT_PER_DATASET)
    df["sentiment_label"] = df["rating"].apply(label_from_rating)

    x_text = df["cleaned_review"]
    y = df["sentiment_label"]

    if y.nunique() < 2:
        raise ValueError("Training requires at least two sentiment classes.")

    stratify_target = y if y.value_counts().min() >= 2 else None
    x_train_text, x_test_text, y_train, y_test = train_test_split(
        x_text,
        y,
        test_size=0.2,
        random_state=42,
        stratify=stratify_target,
    )

    best_pipeline, best_params = tune_model(x_train_text, y_train)
    vectorizer = best_pipeline.named_steps["features"]
    logistic_model = best_pipeline.named_steps["model"]
    x_train = vectorizer.fit_transform(x_train_text)
    x_test = vectorizer.transform(x_test_text)
    result = evaluate_model("Logistic Regression", logistic_model, x_train, x_test, y_train, y_test)

    metrics_df = pd.DataFrame(
        [{key: value for key, value in result.items() if key not in {"model_object", "predictions"}}]
    )
    metrics_df.to_csv(MODEL_METRICS_PATH, index=False)

    best_model = result["model_object"]
    best_predictions = result["predictions"]
    accuracy = result["accuracy"]
    history_df = build_training_history(best_model, x_train, x_test, y_train, y_test)

    joblib.dump(best_model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    history_df.to_csv(TRAINING_HISTORY_PATH, index=False)
    save_metric_charts(accuracy, history_df)

    labels = ["Positive", "Neutral", "Negative"]
    cm = confusion_matrix(y_test, best_predictions, labels=labels)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", xticklabels=labels, yticklabels=labels, cmap="Blues")
    plt.title("Confusion Matrix - Logistic Regression")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.tight_layout()
    plt.savefig(CONFUSION_MATRIX_PATH, dpi=300)
    plt.close()

    report = classification_report(y_test, best_predictions, zero_division=0)
    with MODEL_REPORT_PATH.open("w", encoding="utf-8") as handle:
        handle.write("Model: Logistic Regression\n")
        handle.write(f"Accuracy: {accuracy:.2f}%\n")
        handle.write(f"Best Params: {best_params}\n")
        handle.write(f"Precision Macro: {result['precision_macro']:.4f}\n")
        handle.write(f"Recall Macro: {result['recall_macro']:.4f}\n")
        handle.write(f"F1 Macro: {result['f1_macro']:.4f}\n\n")
        handle.write("Classification Report:\n")
        handle.write(report)

    print("Training complete")
    print(f"Training rows used: {len(df)}")
    if "source_file" in df.columns:
        counts = df["source_file"].value_counts().sort_index()
        print("Training samples per dataset:")
        print(counts.to_string())
    print(f"Accuracy: {accuracy:.2f}%")
    print(f"Best params: {best_params}")
    print(metrics_df.to_string(index=False))
    print(f"Best model saved: {MODEL_PATH}")
    print(f"Vectorizer saved: {VECTORIZER_PATH}")
    print(f"Metrics saved: {MODEL_METRICS_PATH}")
    print(f"Accuracy chart saved: {MODEL_ACCURACY_CHART_PATH}")
    print(f"Training history saved: {TRAINING_HISTORY_PATH}")
    print(f"Training history chart saved: {TRAINING_HISTORY_CHART_PATH}")
    print(f"Report saved: {MODEL_REPORT_PATH}")
    return metrics_df


def main():
    train_models()


if __name__ == "__main__":
    main()
