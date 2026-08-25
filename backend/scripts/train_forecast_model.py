"""
scripts/train_forecast_model.py -- Train a Prophet Time-Series Forecasting Model.

Pipeline:
  1. Load UPI transaction data from SQLite.
  2. Aggregate to daily transaction counts and total amounts.
  3. Train Prophet model with weekly seasonality.
  4. Generate 30-day forecast.
  5. Save model and forecast data to backend/models/.
"""

import os
import json
import sqlite3
import warnings

import pandas as pd
import joblib

warnings.filterwarnings("ignore")

# -- Paths ---------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "upi_transactions.db")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

COUNT_MODEL_PATH = os.path.join(MODEL_DIR, "forecast_count_model.joblib")
AMOUNT_MODEL_PATH = os.path.join(MODEL_DIR, "forecast_amount_model.joblib")
FORECAST_DATA_PATH = os.path.join(MODEL_DIR, "forecast_data.json")


def load_and_aggregate():
    """Load transaction data and aggregate to daily level."""
    print("[1/4] Loading and aggregating data...")

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT DATE(timestamp) as date,
               COUNT(*) as txn_count,
               SUM(amount_inr) as total_amount,
               SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) as failed_count,
               SUM(fraud_flag) as fraud_count
        FROM transactions
        GROUP BY DATE(timestamp)
        ORDER BY date
        """,
        conn,
    )
    conn.close()

    df["date"] = pd.to_datetime(df["date"])
    print(f"       Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"       Total days: {len(df)}")
    print(f"       Avg daily txns: {df['txn_count'].mean():.0f}")
    print(f"       Avg daily amount: INR {df['total_amount'].mean():,.0f}")

    return df


def train_prophet_model(df, target_col, model_name):
    """Train a Prophet model for a specific target metric."""
    from prophet import Prophet

    print(f"\n[*] Training Prophet model for '{target_col}'...")

    # Prophet requires columns named 'ds' and 'y'
    prophet_df = df[["date", target_col]].rename(
        columns={"date": "ds", target_col: "y"}
    )

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_mode="multiplicative",
    )

    model.fit(prophet_df)
    print(f"       {model_name} model trained successfully!")

    return model, prophet_df


def generate_forecast(model, prophet_df, periods=30):
    """Generate future forecast."""
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    # Get only the future predictions
    last_date = prophet_df["ds"].max()
    future_forecast = forecast[forecast["ds"] > last_date][
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].copy()

    future_forecast["ds"] = future_forecast["ds"].dt.strftime("%Y-%m-%d")

    return future_forecast, forecast


def main():
    print("=" * 60)
    print("  InsightX — Time-Series Forecasting Model Training")
    print("=" * 60 + "\n")

    # 1. Load and aggregate
    daily_df = load_and_aggregate()

    # 2. Train transaction count model
    print("\n[2/4] Training transaction count forecaster...")
    count_model, count_df = train_prophet_model(
        daily_df, "txn_count", "Transaction Count"
    )

    # 3. Train transaction amount model
    print("[3/4] Training transaction amount forecaster...")
    amount_model, amount_df = train_prophet_model(
        daily_df, "total_amount", "Transaction Amount"
    )

    # 4. Generate forecasts
    print("\n[4/4] Generating 30-day forecasts...")

    count_forecast, count_full = generate_forecast(count_model, count_df, periods=30)
    amount_forecast, amount_full = generate_forecast(
        amount_model, amount_df, periods=30
    )

    # Save models
    joblib.dump(count_model, COUNT_MODEL_PATH)
    print(f"       Count model saved to: {COUNT_MODEL_PATH}")

    joblib.dump(amount_model, AMOUNT_MODEL_PATH)
    print(f"       Amount model saved to: {AMOUNT_MODEL_PATH}")

    # Prepare historical data for the frontend
    historical = daily_df[["date", "txn_count", "total_amount"]].copy()
    historical["date"] = historical["date"].dt.strftime("%Y-%m-%d")

    # Save forecast data as JSON
    forecast_data = {
        "historical": historical.to_dict(orient="records"),
        "count_forecast": count_forecast.to_dict(orient="records"),
        "amount_forecast": amount_forecast.to_dict(orient="records"),
        "metadata": {
            "forecast_days": 30,
            "training_days": len(daily_df),
            "date_range": {
                "start": daily_df["date"].min().strftime("%Y-%m-%d"),
                "end": daily_df["date"].max().strftime("%Y-%m-%d"),
            },
            "avg_daily_count": round(daily_df["txn_count"].mean(), 0),
            "avg_daily_amount": round(daily_df["total_amount"].mean(), 0),
        },
    }

    with open(FORECAST_DATA_PATH, "w") as f:
        json.dump(forecast_data, f, indent=2, default=str)
    print(f"       Forecast data saved to: {FORECAST_DATA_PATH}")

    # Print forecast summary
    print("\n" + "=" * 60)
    print("FORECAST SUMMARY (Next 30 Days)")
    print("=" * 60)
    print(f"  Transaction Count:")
    print(f"    Predicted avg: {count_forecast['yhat'].mean():.0f} txns/day")
    print(
        f"    Range: {count_forecast['yhat_lower'].mean():.0f} - {count_forecast['yhat_upper'].mean():.0f}"
    )
    print(f"  Transaction Amount:")
    print(f"    Predicted avg: INR {amount_forecast['yhat'].mean():,.0f}/day")
    print(
        f"    Range: INR {amount_forecast['yhat_lower'].mean():,.0f} - INR {amount_forecast['yhat_upper'].mean():,.0f}"
    )
    print("=" * 60)

    print("\n[OK] Forecasting model training complete!")


if __name__ == "__main__":
    main()
