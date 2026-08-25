"""
scripts/generate_database.py -- Generate the UPI Transactions SQLite Database.

Creates backend/data/upi_transactions.db with 250,000 synthetic UPI transactions
matching the exact schema used by InsightX.
"""

import os
import random
import sqlite3
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# -- Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "upi_transactions.db")

# -- Configuration
NUM_TRANSACTIONS = 250_000
SEED = 42

# -- Domain Values
TRANSACTION_TYPES = ["P2P", "P2M", "Bill Payment", "Recharge"]
TRANSACTION_TYPE_WEIGHTS = [0.35, 0.35, 0.20, 0.10]

MERCHANT_CATEGORIES = ["Food", "Grocery", "Shopping", "Fuel", "Utilities",
                       "Entertainment", "Healthcare", "Transport", "Education", "Other"]

BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "PNB", "Yes Bank", "IndusInd"]

STATES = ["Delhi", "Maharashtra", "Karnataka", "Tamil Nadu", "Telangana",
          "Gujarat", "Rajasthan", "West Bengal", "Uttar Pradesh", "Kerala",
          "Punjab", "Haryana", "Madhya Pradesh", "Bihar", "Odisha"]

DEVICE_TYPES = ["Android", "iOS", "Web"]
DEVICE_WEIGHTS = [0.65, 0.25, 0.10]

NETWORK_TYPES = ["3G", "4G", "5G", "WiFi"]
NETWORK_WEIGHTS = [0.05, 0.45, 0.30, 0.20]

AGE_GROUPS = ["18-25", "26-35", "36-45", "46-55", "56+"]
AGE_WEIGHTS = [0.20, 0.35, 0.25, 0.15, 0.05]

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def classify_age(age_group):
    if age_group == "18-25":
        return "Young (18-25)"
    elif age_group in ("26-35", "36-45", "46-55"):
        return "Adult (26-55)"
    else:
        return "Old (56+)"


def classify_amount(amount):
    if amount < 500:
        return "Small (<500)"
    elif amount <= 5000:
        return "Medium (500-5000)"
    else:
        return "Large (5000-50000)"


def get_day_part(hour):
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"


def compute_fraud_probability(txn_type, amount, hour, network, device, is_weekend):
    """Realistic fraud probability based on feature combinations."""
    base = 0.02  # 2% base fraud rate

    # Higher amounts are more fraud-prone
    if amount > 20000:
        base += 0.08
    elif amount > 10000:
        base += 0.04

    # Night transactions are riskier
    if hour < 5 or hour > 22:
        base += 0.05

    # 3G networks are riskier
    if network == "3G":
        base += 0.03

    # Web transactions are riskier
    if device == "Web":
        base += 0.02

    # Weekend slightly riskier
    if is_weekend:
        base += 0.01

    # P2P large amounts riskier
    if txn_type == "P2P" and amount > 15000:
        base += 0.03

    return min(base, 0.30)  # Cap at 30%


def generate():
    random.seed(SEED)
    np.random.seed(SEED)

    print(f"Generating {NUM_TRANSACTIONS:,} transactions...")

    # Date range: 1 year (Oct 2023 - Oct 2024)
    start_date = datetime(2023, 10, 1)
    end_date = datetime(2024, 10, 1)
    date_range_seconds = int((end_date - start_date).total_seconds())

    rows = []
    for i in range(NUM_TRANSACTIONS):
        # Random timestamp
        ts = start_date + timedelta(seconds=random.randint(0, date_range_seconds))

        txn_type = random.choices(TRANSACTION_TYPES, TRANSACTION_TYPE_WEIGHTS)[0]

        # Amount based on type
        if txn_type == "P2P":
            amount = random.choice([
                random.randint(50, 500),
                random.randint(500, 5000),
                random.randint(5000, 50000),
            ])
        elif txn_type == "Recharge":
            amount = random.choice([49, 99, 149, 199, 299, 399, 499, 599, 799, 999])
        elif txn_type == "Bill Payment":
            amount = random.randint(100, 15000)
        else:  # P2M
            amount = random.randint(20, 25000)

        device = random.choices(DEVICE_TYPES, DEVICE_WEIGHTS)[0]
        network = random.choices(NETWORK_TYPES, NETWORK_WEIGHTS)[0]
        sender_state = random.choice(STATES)
        sender_bank = random.choice(BANKS)
        receiver_bank = random.choice(BANKS)
        sender_age = random.choices(AGE_GROUPS, AGE_WEIGHTS)[0]

        hour = ts.hour
        day_name = DAYS_OF_WEEK[ts.weekday()]
        is_weekend = 1 if ts.weekday() >= 5 else 0

        # Merchant category (only for non-P2P)
        merchant_cat = None if txn_type == "P2P" else random.choice(MERCHANT_CATEGORIES)

        # Receiver age (only for P2P)
        receiver_age = random.choices(AGE_GROUPS, AGE_WEIGHTS)[0] if txn_type == "P2P" else None

        # Transaction status
        fail_prob = 0.05 if network == "3G" else 0.02
        status = "FAILED" if random.random() < fail_prob else "SUCCESS"

        # Fraud flag
        fraud_prob = compute_fraud_probability(txn_type, amount, hour, network, device, is_weekend)
        fraud = 1 if random.random() < fraud_prob else 0

        rows.append({
            "transaction_id": f"TXN{i+1:010d}",
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "transaction_type": txn_type,
            "merchant_category": merchant_cat,
            "amount_inr": amount,
            "transaction_status": status,
            "sender_age_group": sender_age,
            "receiver_age_group": receiver_age,
            "sender_state": sender_state,
            "sender_bank": sender_bank,
            "receiver_bank": receiver_bank,
            "device_type": device,
            "network_type": network,
            "fraud_flag": fraud,
            "hour_of_day": hour,
            "day_of_week": day_name,
            "is_weekend": is_weekend,
            "day_part": get_day_part(hour),
            "amount_tier": classify_amount(amount),
            "sender_age_label": classify_age(sender_age),
            "receiver_age_label": classify_age(receiver_age) if receiver_age else None,
        })

        if (i + 1) % 50000 == 0:
            print(f"  Generated {i+1:,} / {NUM_TRANSACTIONS:,}")

    df = pd.DataFrame(rows)
    print(f"\nDataset shape: {df.shape}")
    print(f"Fraud rate: {df['fraud_flag'].mean() * 100:.2f}%")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Save to SQLite
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("transactions", conn, index=False, if_exists="replace")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fraud ON transactions(fraud_flag)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bank ON transactions(sender_bank)")
    conn.close()

    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"\n[OK] Database saved to: {DB_PATH} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    generate()
