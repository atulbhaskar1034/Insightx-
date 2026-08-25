"""
scripts/train_fraud_model.py -- Train an XGBoost Fraud Detection Classifier.

Pipeline:
  1. Load UPI transaction data from SQLite.
  2. Feature-engineer and encode categorical columns.
  3. Handle class imbalance via scale_pos_weight.
  4. Train XGBClassifier with hyperparameter tuning.
  5. Evaluate with Precision, Recall, F1, AUC-ROC, Confusion Matrix.
  6. Generate SHAP feature importance.
  7. Save model + encoders to backend/models/.
"""

import os
import sys
import json
import sqlite3
import warnings

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_fscore_support,
)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# -- Paths ---------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "upi_transactions.db")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, "fraud_model.joblib")
ENCODERS_PATH = os.path.join(MODEL_DIR, "fraud_encoders.joblib")
REPORT_PATH = os.path.join(MODEL_DIR, "fraud_eval_report.json")

# -- Feature Configuration -----------------------------------------------------

# Columns used as input features for the model
FEATURE_COLS = [
    "transaction_type",
    "amount_inr",
    "sender_bank",
    "receiver_bank",
    "device_type",
    "network_type",
    "sender_state",
    "hour_of_day",
    "is_weekend",
    "day_part",
    "amount_tier",
    "sender_age_label",
]

# Categorical columns that need label encoding
CATEGORICAL_COLS = [
    "transaction_type",
    "sender_bank",
    "receiver_bank",
    "device_type",
    "network_type",
    "sender_state",
    "day_part",
    "amount_tier",
    "sender_age_label",
]

TARGET_COL = "fraud_flag"


def load_data():
    """Load transaction data from SQLite."""
    print(f"[1/6] Loading data from {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    print(f"       Loaded {len(df):,} rows, {len(df.columns)} columns")
    print(f"       Fraud rate: {df[TARGET_COL].mean() * 100:.2f}%")
    return df


def preprocess(df):
    """Feature engineering and encoding."""
    print("[2/6] Preprocessing and encoding features...")

    # Select only the features we need + target
    df_model = df[FEATURE_COLS + [TARGET_COL]].copy()

    # Handle any NaN in categorical columns
    for col in CATEGORICAL_COLS:
        df_model[col] = df_model[col].fillna("Unknown")

    # Label-encode categorical columns
    encoders = {}
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df_model[col] = le.fit_transform(df_model[col].astype(str))
        encoders[col] = le
        print(f"       Encoded '{col}': {len(le.classes_)} classes")

    X = df_model[FEATURE_COLS].values
    y = df_model[TARGET_COL].values

    return X, y, encoders


def train_model(X_train, y_train):
    """Train XGBoost with class imbalance handling."""
    print("[3/6] Training XGBoost classifier...")

    # Calculate scale_pos_weight for class imbalance
    n_neg = np.sum(y_train == 0)
    n_pos = np.sum(y_train == 1)
    scale_pos_weight = n_neg / n_pos
    print(f"       Class distribution: {n_neg:,} negative, {n_pos:,} positive")
    print(f"       scale_pos_weight: {scale_pos_weight:.2f}")

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train, verbose=False)
    print("       Training complete!")
    return model


def evaluate_model(model, X_test, y_test):
    """Evaluate model performance."""
    print("[4/6] Evaluating model...")

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Classification report
    report = classification_report(y_test, y_pred, target_names=["Legitimate", "Fraud"])
    print("\n" + "=" * 60)
    print("CLASSIFICATION REPORT")
    print("=" * 60)
    print(report)

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("Confusion Matrix:")
    print(f"  TN={cm[0][0]:,}  FP={cm[0][1]:,}")
    print(f"  FN={cm[1][0]:,}  TP={cm[1][1]:,}")

    # AUC-ROC
    auc = roc_auc_score(y_test, y_prob)
    print(f"\nAUC-ROC: {auc:.4f}")

    # Precision, Recall, F1 for fraud class
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, pos_label=1, average="binary"
    )
    print(f"Fraud Precision: {precision:.4f}")
    print(f"Fraud Recall:    {recall:.4f}")
    print(f"Fraud F1-Score:  {f1:.4f}")
    print("=" * 60 + "\n")

    # Save evaluation report as JSON
    eval_report = {
        "auc_roc": round(auc, 4),
        "fraud_precision": round(precision, 4),
        "fraud_recall": round(recall, 4),
        "fraud_f1": round(f1, 4),
        "confusion_matrix": {
            "true_negatives": int(cm[0][0]),
            "false_positives": int(cm[0][1]),
            "false_negatives": int(cm[1][0]),
            "true_positives": int(cm[1][1]),
        },
        "test_size": len(y_test),
        "fraud_rate_test": round(float(np.mean(y_test)) * 100, 2),
    }

    return eval_report


def compute_shap(model, X_test, feature_names):
    """Compute SHAP values for model explainability."""
    print("[5/6] Computing SHAP feature importance...")

    try:
        import shap

        explainer = shap.TreeExplainer(model)
        # Use a sample for speed
        sample_size = min(1000, len(X_test))
        X_sample = X_test[:sample_size]
        shap_values = explainer.shap_values(X_sample)

        # Mean absolute SHAP value per feature
        mean_shap = np.abs(shap_values).mean(axis=0)
        importance = dict(zip(feature_names, [round(float(v), 4) for v in mean_shap]))
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

        print("       SHAP Feature Importance (Top 5):")
        for i, (feat, val) in enumerate(importance.items()):
            if i >= 5:
                break
            print(f"         {i+1}. {feat}: {val:.4f}")

        return importance
    except Exception as e:
        print(f"       SHAP computation skipped: {e}")
        return {}


def save_model(model, encoders, eval_report, shap_importance):
    """Save trained model and artifacts."""
    print("[6/6] Saving model artifacts...")

    joblib.dump(model, MODEL_PATH)
    print(f"       Model saved to: {MODEL_PATH}")

    joblib.dump(encoders, ENCODERS_PATH)
    print(f"       Encoders saved to: {ENCODERS_PATH}")

    eval_report["shap_importance"] = shap_importance
    eval_report["feature_columns"] = FEATURE_COLS
    eval_report["categorical_columns"] = CATEGORICAL_COLS

    with open(REPORT_PATH, "w") as f:
        json.dump(eval_report, f, indent=2)
    print(f"       Eval report saved to: {REPORT_PATH}")


def main():
    print("=" * 60)
    print("  InsightX — Fraud Detection Model Training")
    print("=" * 60 + "\n")

    # 1. Load data
    df = load_data()

    # 2. Preprocess
    X, y, encoders = preprocess(df)

    # 3. Split (stratified to maintain fraud class ratio)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"       Train: {len(X_train):,} | Test: {len(X_test):,}")

    # 4. Train
    model = train_model(X_train, y_train)

    # 5. Evaluate
    eval_report = evaluate_model(model, X_test, y_test)

    # 6. SHAP
    shap_importance = compute_shap(model, X_test, FEATURE_COLS)

    # 7. Save
    save_model(model, encoders, eval_report, shap_importance)

    print("\n[OK] Fraud detection model training complete!")
    print(f"     AUC-ROC: {eval_report['auc_roc']}")
    print(f"     Recall:  {eval_report['fraud_recall']}")


if __name__ == "__main__":
    main()
