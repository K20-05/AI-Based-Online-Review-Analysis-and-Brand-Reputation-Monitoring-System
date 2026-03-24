from __future__ import annotations

from pathlib import Path
import sys
import warnings

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.base import clone
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score, log_loss
from sklearn.model_selection import train_test_split

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.config import (
    CALIBRATION_REPORT_PATH,
    CLEANED_DATA_PATH,
    LANGUAGE_EVALUATION_PATH,
    MODEL_METRICS_CHART_PATH,
    MODEL_METRICS_PATH,
    MODEL_PATH,
    MODEL_REPORT_PATH,
    TRAINING_HISTORY_CHART_PATH,
    TRAINING_HISTORY_PATH,
    VECTORIZER_PATH,
)
from backend.model_evaluation import (
    build_calibration_frame,
    build_language_evaluation_frame,
    expected_calibration_error,
)
from backend.preprocessing import STOP_WORDS, label_from_rating

warnings.filterwarnings("ignore", category=ConvergenceWarning)

RANDOM_STATE = 42


def _resolve_text_column(df: pd.DataFrame) -> str:
    for candidate in ("cleaned_review", "clean_text", "review_text"):
        if candidate in df.columns:
            return candidate
    raise ValueError(
        "Training dataset must contain one of: cleaned_review, clean_text, review_text"
    )


def _load_training_frame() -> tuple[pd.DataFrame, str]:
    if not CLEANED_DATA_PATH.exists():
        raise FileNotFoundError(f"{CLEANED_DATA_PATH} not found. Run preprocessing first.")

    df = pd.read_csv(CLEANED_DATA_PATH, low_memory=False)
    text_column = _resolve_text_column(df)

    if "sentiment_label" not in df.columns:
        if "rating" not in df.columns:
            raise ValueError("Training dataset requires either sentiment_label or rating column.")
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df = df.dropna(subset=["rating"])
        df["sentiment_label"] = df["rating"].apply(label_from_rating)

    df[text_column] = df[text_column].fillna("").astype(str)
    df["sentiment_label"] = df["sentiment_label"].fillna("").astype(str)
    if "source_language" not in df.columns:
        df["source_language"] = "unknown"
    df["source_language"] = df["source_language"].fillna("unknown").astype(str)
    df = df[df[text_column].str.strip() != ""].copy()
    df = df[df["sentiment_label"].str.strip() != ""].copy()
    if df.empty:
        raise ValueError("No valid rows available for training after cleaning.")

    class_counts = df["sentiment_label"].value_counts()
    if class_counts.shape[0] < 2:
        raise ValueError("Training requires at least two sentiment classes.")
    if (class_counts < 2).any():
        raise ValueError(
            "Each sentiment class needs at least 2 rows for train/test split. "
            f"Current counts: {class_counts.to_dict()}"
        )

    return df, text_column


def train_models() -> pd.DataFrame:
    print("\n========== MODEL TRAINING STARTED ==========")
    df, text_column = _load_training_frame()

    X = df[text_column]
    y = df["sentiment_label"]
    languages = df["source_language"]
    print(f"Dataset size: {len(df)}")

    X_train_val, X_test, y_train_val, y_test, language_train_val, language_test = train_test_split(
        X,
        y,
        languages,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    X_train, X_val, y_train, y_val, language_train, language_val = train_test_split(
        X_train_val,
        y_train_val,
        language_train_val,
        test_size=0.1,
        random_state=RANDOM_STATE,
        stratify=y_train_val,
    )

    print(f"Training samples: {len(X_train_val)}")
    print(f"Testing samples: {len(X_test)}")
    print(f"Validation samples: {len(X_val)}")

    vectorizer = TfidfVectorizer(
        max_features=50000,
        ngram_range=(1, 2),
        stop_words=sorted(STOP_WORDS),
        min_df=2,
        max_df=0.98,
        sublinear_tf=True,
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)

    candidates = [
        (
            "LogReg C=1.0",
            LogisticRegression(
                max_iter=3000,
                solver="lbfgs",
                C=1.0,
                class_weight=None,
            ),
        ),
        (
            "LogReg C=2.0",
            LogisticRegression(
                max_iter=3000,
                solver="lbfgs",
                C=2.0,
                class_weight=None,
            ),
        ),
        (
            "LogReg C=4.0",
            LogisticRegression(
                max_iter=3000,
                solver="lbfgs",
                C=4.0,
                class_weight=None,
            ),
        ),
        (
            "LogReg Balanced C=2.0",
            LogisticRegression(
                max_iter=3000,
                solver="lbfgs",
                C=2.0,
                class_weight="balanced",
            ),
        ),
    ]

    best_name = ""
    best_model = None
    best_val_accuracy = -1.0
    best_val_f1 = -1.0
    model_scores = []
    for name, estimator in candidates:
        estimator.fit(X_train_vec, y_train)
        val_pred = estimator.predict(X_val_vec)
        val_accuracy = float(accuracy_score(y_val, val_pred))
        val_f1 = float(f1_score(y_val, val_pred, average="macro"))
        model_scores.append((name, val_accuracy, val_f1))
        if (val_accuracy > best_val_accuracy) or (
            val_accuracy == best_val_accuracy and val_f1 > best_val_f1
        ):
            best_name = name
            best_model = clone(estimator)
            best_val_accuracy = val_accuracy
            best_val_f1 = val_f1

    # Refit best pipeline on full train+validation split
    vectorizer = TfidfVectorizer(
        max_features=50000,
        ngram_range=(1, 2),
        stop_words=sorted(STOP_WORDS),
        min_df=2,
        max_df=0.98,
        sublinear_tf=True,
    )
    X_train_val_vec = vectorizer.fit_transform(X_train_val)
    X_test_vec = vectorizer.transform(X_test)
    model = CalibratedClassifierCV(
        estimator=clone(best_model),
        method="sigmoid",
        cv=3,
    )
    model.fit(X_train_val_vec, y_train_val)
    y_train_pred = model.predict(X_train_val_vec)
    y_pred = model.predict(X_test_vec)

    train_accuracy = float(accuracy_score(y_train_val, y_train_pred))
    accuracy = float(accuracy_score(y_test, y_pred))
    train_macro_f1 = float(f1_score(y_train_val, y_train_pred, average="macro"))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
    metrics_row = {
        "model": best_name,
        "validation_accuracy": best_val_accuracy,
        "validation_f1_macro": best_val_f1,
        "train_accuracy": train_accuracy,
        "accuracy": accuracy,
        "train_f1_macro": train_macro_f1,
        "f1_macro": macro_f1,
    }

    train_loss = None
    test_loss = None
    train_ece = None
    test_ece = None
    language_eval_df = build_language_evaluation_frame(y_test, y_pred, language_test)
    language_eval_df.to_csv(LANGUAGE_EVALUATION_PATH, index=False)

    calibration_df = pd.DataFrame()
    if hasattr(model, "predict_proba"):
        y_train_proba = model.predict_proba(X_train_val_vec)
        y_proba = model.predict_proba(X_test_vec)
        train_loss = float(log_loss(y_train_val, y_train_proba, labels=model.classes_))
        test_loss = float(log_loss(y_test, y_proba, labels=model.classes_))
        train_ece = expected_calibration_error(y_train_val, y_train_proba, model.classes_)
        test_ece = expected_calibration_error(y_test, y_proba, model.classes_)
        calibration_df = build_calibration_frame(y_test, y_proba, model.classes_)
        calibration_df.to_csv(CALIBRATION_REPORT_PATH, index=False)
        metrics_row["train_log_loss"] = train_loss
        metrics_row["log_loss"] = test_loss
        metrics_row["train_ece"] = train_ece
        metrics_row["ece"] = test_ece
        metrics_row["probability_calibration"] = "sigmoid_cv3"

    metrics_df = pd.DataFrame([metrics_row])
    metrics_df.to_csv(MODEL_METRICS_PATH, index=False)

    history_df = pd.DataFrame(
        [
            {
                "split": "train",
                "accuracy": train_accuracy,
                "f1_macro": train_macro_f1,
                "log_loss": train_loss,
            },
            {
                "split": "test",
                "accuracy": accuracy,
                "f1_macro": macro_f1,
                "log_loss": test_loss,
            },
        ]
    )
    history_df.to_csv(TRAINING_HISTORY_PATH, index=False)

    # Gain graph (accuracy + macro F1)
    plt.figure(figsize=(8, 5))
    gain_labels = ["Train Accuracy", "Test Accuracy", "Train Macro F1", "Test Macro F1"]
    gain_values = [train_accuracy, accuracy, train_macro_f1, macro_f1]
    gain_colors = ["#63e6be", "#22b8cf", "#74c0fc", "#4dabf7"]
    plt.bar(gain_labels, gain_values, color=gain_colors)
    plt.ylim(0, 1)
    plt.ylabel("Score")
    plt.title("Model Gain Metrics")
    plt.xticks(rotation=12)
    plt.tight_layout()
    plt.savefig(MODEL_METRICS_CHART_PATH, dpi=140)
    plt.close()

    # Loss graph (train vs test log loss)
    if train_loss is not None and test_loss is not None:
        plt.figure(figsize=(7, 4.5))
        plt.plot(["Train", "Test"], [train_loss, test_loss], marker="o", linewidth=2.5, color="#ff6b8d")
        plt.ylabel("Log Loss")
        plt.title("Loss Graph")
        plt.grid(alpha=0.2)
        plt.tight_layout()
        plt.savefig(TRAINING_HISTORY_CHART_PATH, dpi=140)
        plt.close()

    report = classification_report(y_test, y_pred, zero_division=0)
    language_report = (
        language_eval_df.to_string(index=False)
        if not language_eval_df.empty
        else "No language metadata available."
    )
    calibration_report = (
        calibration_df.to_string(index=False)
        if not calibration_df.empty
        else "Calibration probabilities unavailable."
    )

    ranked_models = sorted(model_scores, key=lambda item: (item[1], item[2]), reverse=True)
    best_val_name, best_val_acc, best_val_f1 = ranked_models[0]
    print("\nModel Selection: " + best_val_name + f" (val_acc={best_val_acc:.4f}, val_f1={best_val_f1:.4f})")
    print(
        "Summary: "
        + f"train_acc={train_accuracy:.4f} | "
        + f"val_acc={best_val_accuracy:.4f} | "
        + f"test_acc={accuracy:.4f} | "
        + f"test_f1={macro_f1:.4f}"
    )
    print(f"Train Accuracy: {train_accuracy:.4f}")
    print(f"Validation Accuracy: {best_val_accuracy:.4f}")
    print(f"Test Accuracy: {accuracy:.4f}")
    if train_loss is not None and test_loss is not None:
        print(f"Loss: train={train_loss:.4f} | test={test_loss:.4f}")
    if train_ece is not None and test_ece is not None:
        print(f"Calibration ECE: train={train_ece:.4f} | test={test_ece:.4f}")
    print("\nClassification Report (Test):")
    print(report)
    print("\nLanguage Evaluation (Test):")
    print(language_report)

    MODEL_REPORT_PATH.write_text(
        "Train Accuracy: " + str(train_accuracy) + "\n"
        + "Test Accuracy: " + str(accuracy) + "\n"
        + "Train Macro F1: " + str(train_macro_f1) + "\n"
        + "Test Macro F1: " + str(macro_f1) + "\n"
        + ("Train Log Loss: " + str(train_loss) + "\n" if train_loss is not None else "")
        + ("Test Log Loss: " + str(test_loss) + "\n" if test_loss is not None else "")
        + ("Train ECE: " + str(train_ece) + "\n" if train_ece is not None else "")
        + ("Test ECE: " + str(test_ece) + "\n" if test_ece is not None else "")
        + "\n"
        + report
        + "\n\nLanguage Evaluation (Test)\n"
        + language_report
        + "\n\nCalibration Report (Test)\n"
        + calibration_report,
        encoding="utf-8",
    )

    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)

    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved vectorizer: {VECTORIZER_PATH}")
    print(f"Saved metrics: {MODEL_METRICS_PATH}")
    print(f"Saved history: {TRAINING_HISTORY_PATH}")
    print(f"Saved language evaluation: {LANGUAGE_EVALUATION_PATH}")
    if not calibration_df.empty:
        print(f"Saved calibration report: {CALIBRATION_REPORT_PATH}")
    print(f"Saved gain graph: {MODEL_METRICS_CHART_PATH}")
    if train_loss is not None and test_loss is not None:
        print(f"Saved loss graph: {TRAINING_HISTORY_CHART_PATH}")
    print(f"Saved report: {MODEL_REPORT_PATH}")
    print("========== MODEL TRAINING COMPLETED ==========\n")
    return metrics_df


def main() -> None:
    train_models()


if __name__ == "__main__":
    main()
