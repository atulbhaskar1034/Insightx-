import os
import sqlite3
import pandas as pd

CSV_PATH = r"c:\Users\ATUL\Desktop\Insightx-\upi_transactions_2024.csv"
DATA_DIR = r"c:\Users\ATUL\Desktop\Insightx-\backend\data"
DB_PATH = os.path.join(DATA_DIR, "upi_transactions.db")

os.makedirs(DATA_DIR, exist_ok=True)

print(f"Loading CSV from {CSV_PATH}...")
df = pd.read_csv(CSV_PATH)

print("Preprocessing column names...")
df.rename(columns={
    "transaction id": "transaction_id",
    "transaction type": "transaction_type",
    "amount (INR)": "amount_inr"
}, inplace=True)

print("Synthesizing missing features...")

def classify_age(age_group):
    if pd.isna(age_group):
        return None
    if age_group == "18-25":
        return "Young (18-25)"
    elif age_group in ("26-35", "36-45", "46-55"):
        return "Adult (26-55)"
    else:
        return "Old (56+)"

def classify_amount(amount):
    if pd.isna(amount):
        return None
    if amount < 500:
        return "Small (<500)"
    elif amount <= 5000:
        return "Medium (500-5000)"
    else:
        return "Large (5000-50000)"

def get_day_part(hour):
    if pd.isna(hour):
        return None
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"

df["sender_age_label"] = df["sender_age_group"].apply(classify_age)
df["receiver_age_label"] = df["receiver_age_group"].apply(classify_age)
df["amount_tier"] = df["amount_inr"].apply(classify_amount)
df["day_part"] = df["hour_of_day"].apply(get_day_part)

print(f"Saving to SQLite {DB_PATH}...")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
df.to_sql("transactions", conn, index=False, if_exists="replace")

# Create indices matching the schema we need
conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON transactions(timestamp)")
try:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fraud ON transactions(fraud_flag)")
except sqlite3.OperationalError:
    print("Warning: fraud_flag column might not exist in CSV")
try:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bank ON transactions(sender_bank)")
except sqlite3.OperationalError:
    pass

conn.close()
print("Done!")
