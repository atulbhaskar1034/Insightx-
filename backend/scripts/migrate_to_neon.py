"""
migrate_to_neon.py -- Migrate upi_transactions.db (SQLite) to NeonTech PostgreSQL.

Usage:
    DATABASE_URL=postgresql://... python scripts/migrate_to_neon.py

This script:
  1. Reads all rows from the local SQLite database.
  2. Creates the 'transactions' table in Neon Postgres (if it doesn't exist).
  3. Inserts all rows in batches for performance.
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Add it to your .env or export it.")
    sys.exit(1)

import psycopg2
from psycopg2.extras import execute_values

# Fix Render postgres:// -> postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if "&channel_binding=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&channel_binding=require", "")
elif "?channel_binding=require&" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("channel_binding=require&", "")
elif "?channel_binding=require" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?channel_binding=require", "")

# --- SQLite Source ---
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "upi_transactions.db")

if not os.path.exists(SQLITE_PATH):
    print(f"ERROR: SQLite database not found at: {SQLITE_PATH}")
    sys.exit(1)

print(f"[1/4] Reading from SQLite: {SQLITE_PATH}")
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()

# Get schema info
cursor.execute("PRAGMA table_info(transactions)")
columns_info = cursor.fetchall()
column_names = [col["name"] for col in columns_info]
print(f"       Found {len(column_names)} columns: {', '.join(column_names[:5])}...")

# Read all data
cursor.execute("SELECT * FROM transactions")
rows = cursor.fetchall()
total_rows = len(rows)
print(f"       Found {total_rows:,} rows")
sqlite_conn.close()

# --- Postgres Target ---
print(f"[2/4] Connecting to Neon PostgreSQL...")
pg_conn = psycopg2.connect(DATABASE_URL)
pg_cur = pg_conn.cursor()

# Create table
print(f"[3/4] Creating 'transactions' table (if not exists)...")
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT,
    timestamp TEXT,
    transaction_type TEXT,
    merchant_category TEXT,
    amount_inr INTEGER,
    transaction_status TEXT,
    sender_age_group TEXT,
    receiver_age_group TEXT,
    sender_state TEXT,
    sender_bank TEXT,
    receiver_bank TEXT,
    device_type TEXT,
    network_type TEXT,
    fraud_flag INTEGER,
    hour_of_day INTEGER,
    day_of_week TEXT,
    is_weekend INTEGER,
    day_part TEXT,
    amount_tier TEXT,
    sender_age_label TEXT,
    receiver_age_label TEXT
);
"""
pg_cur.execute(CREATE_TABLE)

# Check if data already exists
pg_cur.execute("SELECT COUNT(*) FROM transactions")
existing_count = pg_cur.fetchone()[0]
if existing_count > 0:
    print(f"       WARNING: 'transactions' table already has {existing_count:,} rows.")
    answer = input("       Do you want to TRUNCATE and re-insert? (yes/no): ").strip().lower()
    if answer != "yes":
        print("       Aborting migration.")
        pg_conn.close()
        sys.exit(0)
    pg_cur.execute("TRUNCATE TABLE transactions")
    print("       Table truncated.")

pg_conn.commit()

# Insert in batches
print(f"[4/4] Inserting {total_rows:,} rows into Neon PostgreSQL...")
BATCH_SIZE = 5000
insert_sql = f"INSERT INTO transactions ({', '.join(column_names)}) VALUES %s"

data_tuples = [tuple(dict(row).values()) for row in rows]

for i in range(0, total_rows, BATCH_SIZE):
    batch = data_tuples[i:i + BATCH_SIZE]
    execute_values(pg_cur, insert_sql, batch, page_size=BATCH_SIZE)
    pg_conn.commit()
    progress = min(i + BATCH_SIZE, total_rows)
    pct = (progress / total_rows) * 100
    print(f"       {progress:,} / {total_rows:,} ({pct:.1f}%)")

# Create index on transaction_id for faster lookups
pg_cur.execute("CREATE INDEX IF NOT EXISTS idx_txn_id ON transactions(transaction_id)")
pg_conn.commit()

pg_cur.close()
pg_conn.close()

print(f"\nMigration complete! {total_rows:,} rows inserted into Neon PostgreSQL.")
print("   Your backend will now use Postgres automatically when DATABASE_URL is set.")
