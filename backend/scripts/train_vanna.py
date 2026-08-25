"""
train_vanna.py — Train Vanna AI on the UPI Transactions SQLite Database.

This script:
  1. Initializes a local Vanna instance (Groq + ChromaDB)
  2. Connects to the local SQLite database (upi_transactions.db)
  3. Trains Vanna on DDL schema, data dictionary, business rules, and few-shot examples
"""

import os
import sys
from pathlib import Path

# Force UTF-8 stdout so unicode checkmarks print on Windows terminals
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from vanna.legacy.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.legacy.openai.openai_chat import OpenAI_Chat
from openai import OpenAI

# ── Path resolution (always relative to backend root) ────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = str(PROJECT_ROOT / "data" / "upi_transactions.db")
VECTOR_STORE_PATH = str(PROJECT_ROOT / "vector_store")

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv(PROJECT_ROOT / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Create a .env file in backend/.")


class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, client=None, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, client=client, config=config)


# ============================================================
# 1. INITIALIZE VANNA
# ============================================================

vanna_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

vn = MyVanna(client=vanna_client, config={
    "model": GROQ_MODEL,
    "path": VECTOR_STORE_PATH,
})

# ============================================================
# 2. CONNECT TO SQLITE DATABASE
# ============================================================

vn.connect_to_sqlite(DB_PATH)
print(f"[✓] Connected to {DB_PATH}")

# ============================================================
# 3. TRAIN ON DDL SCHEMA
# ============================================================

vn.train(ddl="""
CREATE TABLE transactions (
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
)
""")
print("[✓] Trained on DDL schema")

# ============================================================
# 4. TRAIN ON DATA DICTIONARY
# ============================================================

vn.train(documentation="""DATA DICTIONARY:

transaction_id: Unique transaction identifier. Example: TXN0000000001

timestamp: Date and time of the transaction. Example: 2024-10-08 15:17:28

transaction_type: Type of UPI transaction. Values: P2P, P2M, Bill Payment, Recharge

merchant_category: Category of merchant/purpose. Values: Food, Grocery, Shopping, Fuel, Utilities, Entertainment, Healthcare, Transport, Education, Other

amount_inr: Transaction amount in Indian Rupees.

transaction_status: Whether the transaction succeeded. Values: SUCCESS, FAILED

sender_age_group: Age bracket of the sender. Values: 18-25, 26-35, 36-45, 46-55, 56+

receiver_age_group: Age bracket of the receiver. Values: 18-25, 26-35, 36-45, 46-55, 56+

sender_state: Indian state of the sender. Examples: Delhi, Maharashtra, Karnataka

sender_bank: Sender bank. Examples: SBI, HDFC, ICICI, Axis, Kotak, PNB, Yes Bank, IndusInd

receiver_bank: Receiver bank. Same options as sender_bank.

device_type: Device used for the transaction. Values: Android, iOS, Web

network_type: Network used during transaction. Values: 3G, 4G, 5G, WiFi

fraud_flag: Whether flagged as fraud. Values: 0 (not fraud), 1 (fraud)

hour_of_day: Hour when transaction occurred (0-23).

day_of_week: Day of the week. Values: Monday - Sunday

is_weekend: Whether it was a weekend. Values: 0 (weekday), 1 (weekend)

day_part: Derived from hour_of_day. Values: Morning (6-11), Afternoon (12-17), Evening (18-21), Night (22-5)

amount_tier: Derived from amount_inr. Values: Small (<500), Medium (500-5000), Large (5000-50000)

sender_age_label: Derived from sender_age_group. Values: Young (18-25), Adult (26-55), Old (56+)

receiver_age_label: Derived from receiver_age_group. Values: Young (18-25), Adult (26-55), Old (56+)""")
print("[✓] Trained on Data Dictionary")

# ============================================================
# 5. TRAIN ON BUSINESS RULES
# ============================================================

vn.train(documentation="P2P transactions have a NULL merchant_category.")
print("[✓] Trained on business rule: P2P → NULL merchant_category")

vn.train(documentation="Non-P2P transactions have a NULL receiver_age_group and receiver_age_label.")
print("[✓] Trained on business rule: Non-P2P → NULL receiver fields")

# ============================================================
# 6. TRAIN ON FEW-SHOT QUESTION/SQL EXAMPLES
# ============================================================

# Q1
vn.train(question="What is the total transaction volume for SBI?",
         sql="SELECT SUM(amount_inr) FROM transactions WHERE sender_bank = 'SBI'")
print("[✓] Q1 trained")

# Q2
vn.train(question="What is the failure rate for Bill Payments?",
         sql="SELECT (SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) AS failure_rate FROM transactions WHERE transaction_type = 'Bill Payment'")
print("[✓] Q2 trained")

# Q3
vn.train(question="Which age group spends the most on food?",
         sql="SELECT sender_age_label, SUM(amount_inr) as total_spent FROM transactions WHERE merchant_category = 'Food' GROUP BY sender_age_label ORDER BY total_spent DESC LIMIT 1")
print("[✓] Q3 trained")

# Q4
vn.train(question="When are the peak hours for transactions?",
         sql="SELECT day_part, COUNT(*) as txn_count FROM transactions GROUP BY day_part ORDER BY txn_count DESC")
print("[✓] Q4 trained")

# Q5
vn.train(question="What percentage of Large transactions are flagged as fraud?",
         sql="SELECT (SUM(fraud_flag) * 100.0 / COUNT(*)) AS fraud_rate FROM transactions WHERE amount_tier = 'Large'")
print("[✓] Q5 trained")

# Q6
vn.train(question="Compare the failure rates between 3G and 5G networks.",
         sql="SELECT network_type, (SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as failure_rate FROM transactions WHERE network_type IN ('3G', '5G') GROUP BY network_type")
print("[✓] Q6 trained")

# Q7
vn.train(question="What is the most popular device type for P2P transfers?",
         sql="SELECT device_type, COUNT(*) as count FROM transactions WHERE transaction_type = 'P2P' GROUP BY device_type ORDER BY count DESC LIMIT 1")
print("[✓] Q7 trained")

# Q8
vn.train(question="Are transactions between different banks failing more often than same-bank transfers?",
         sql="SELECT CASE WHEN sender_bank != receiver_bank THEN 'Cross-Bank' ELSE 'Same-Bank' END as bank_routing, (SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as failure_rate FROM transactions GROUP BY bank_routing")
print("[✓] Q8 trained")

# Q9
vn.train(question="Do Young senders use UPI more than Old senders?",
         sql="SELECT sender_age_label, COUNT(*) as total_txns FROM transactions WHERE sender_age_label IN ('Young', 'Old') GROUP BY sender_age_label")
print("[✓] Q9 trained")

# Q10
vn.train(question="Is fraud more common on weekends?",
         sql="SELECT is_weekend, (SUM(fraud_flag) * 100.0 / COUNT(*)) as fraud_rate FROM transactions GROUP BY is_weekend")
print("[✓] Q10 trained")

# Q11
vn.train(question="Which state has the highest number of failed transactions?",
         sql="SELECT sender_state, COUNT(*) as failed_count FROM transactions WHERE transaction_status = 'FAILED' GROUP BY sender_state ORDER BY failed_count DESC LIMIT 1")
print("[✓] Q11 trained")

# Q12
vn.train(question="What is the average transaction amount for different merchant categories?",
         sql="SELECT merchant_category, AVG(amount_inr) as avg_amount FROM transactions WHERE transaction_type != 'P2P' GROUP BY merchant_category")
print("[✓] Q12 trained")

# Q13
vn.train(question="Who receives the most P2P money by age group?",
         sql="SELECT receiver_age_label, SUM(amount_inr) as total_received FROM transactions WHERE transaction_type = 'P2P' GROUP BY receiver_age_label ORDER BY total_received DESC LIMIT 1")
print("[✓] Q13 trained")

# Q14
vn.train(question="Show me the top 5 largest fraud transactions.",
         sql="SELECT transaction_id, amount_inr, sender_bank, receiver_bank FROM transactions WHERE fraud_flag = 1 ORDER BY amount_inr DESC LIMIT 5")
print("[✓] Q14 trained")

# Q15
vn.train(question="What is the average transaction amount during the Night vs Morning?",
         sql="SELECT day_part, AVG(amount_inr) as avg_amount FROM transactions WHERE day_part IN ('Night', 'Morning') GROUP BY day_part")
print("[✓] Q15 trained")

# ============================================================
# 7. EXPANDED FEW-SHOT EXAMPLES (Date/Time Filtering)
# ============================================================

# Q16
vn.train(question="How many transactions happened in January 2024?",
         sql="SELECT COUNT(*) as txn_count FROM transactions WHERE strftime('%m', timestamp) = '01' AND strftime('%Y', timestamp) = '2024'")
print("[✓] Q16 trained")

# Q17
vn.train(question="What is the total amount transacted in July?",
         sql="SELECT SUM(amount_inr) as total_amount FROM transactions WHERE strftime('%m', timestamp) = '07'")
print("[✓] Q17 trained")

# Q18
vn.train(question="Show monthly transaction volume trend.",
         sql="SELECT strftime('%Y-%m', timestamp) as month, COUNT(*) as txn_count, SUM(amount_inr) as total_amount FROM transactions GROUP BY month ORDER BY month")
print("[✓] Q18 trained")

# Q19
vn.train(question="Which month had the highest number of fraud cases?",
         sql="SELECT strftime('%m', timestamp) as month, SUM(fraud_flag) as fraud_count FROM transactions GROUP BY month ORDER BY fraud_count DESC LIMIT 1")
print("[✓] Q19 trained")

# Q20
vn.train(question="What is the daily average transaction count?",
         sql="SELECT AVG(daily_count) as avg_daily_txns FROM (SELECT strftime('%Y-%m-%d', timestamp) as day, COUNT(*) as daily_count FROM transactions GROUP BY day)")
print("[✓] Q20 trained")

# ============================================================
# 8. EXPANDED FEW-SHOT EXAMPLES (Advanced Aggregations)
# ============================================================

# Q21
vn.train(question="Which banks have more than 10000 transactions?",
         sql="SELECT sender_bank, COUNT(*) as txn_count FROM transactions GROUP BY sender_bank HAVING COUNT(*) > 10000 ORDER BY txn_count DESC")
print("[✓] Q21 trained")

# Q22
vn.train(question="Which states have a fraud rate above 1%?",
         sql="SELECT sender_state, (SUM(fraud_flag) * 100.0 / COUNT(*)) as fraud_rate FROM transactions GROUP BY sender_state HAVING fraud_rate > 1.0 ORDER BY fraud_rate DESC")
print("[✓] Q22 trained")

# Q23
vn.train(question="What is the median transaction amount?",
         sql="SELECT amount_inr as median_amount FROM transactions ORDER BY amount_inr LIMIT 1 OFFSET (SELECT COUNT(*) / 2 FROM transactions)")
print("[✓] Q23 trained")

# Q24
vn.train(question="What percentage of total transactions does each transaction type represent?",
         sql="SELECT transaction_type, COUNT(*) as count, (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM transactions)) as percentage FROM transactions GROUP BY transaction_type ORDER BY percentage DESC")
print("[✓] Q24 trained")

# Q25
vn.train(question="What is the total and average transaction amount per state?",
         sql="SELECT sender_state, COUNT(*) as txn_count, SUM(amount_inr) as total_amount, AVG(amount_inr) as avg_amount FROM transactions GROUP BY sender_state ORDER BY total_amount DESC")
print("[✓] Q25 trained")

# ============================================================
# 9. EXPANDED FEW-SHOT EXAMPLES (Multi-Condition & Complex WHERE)
# ============================================================

# Q26
vn.train(question="Show failed P2P transactions above 5000 rupees.",
         sql="SELECT transaction_id, amount_inr, sender_bank, receiver_bank FROM transactions WHERE transaction_type = 'P2P' AND transaction_status = 'FAILED' AND amount_inr > 5000 ORDER BY amount_inr DESC")
print("[✓] Q26 trained")

# Q27
vn.train(question="How many fraud transactions happened on weekends during the Night?",
         sql="SELECT COUNT(*) as fraud_count FROM transactions WHERE fraud_flag = 1 AND is_weekend = 1 AND day_part = 'Night'")
print("[✓] Q27 trained")

# Q28
vn.train(question="What is the failure rate for HDFC to SBI transfers?",
         sql="SELECT (SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as failure_rate FROM transactions WHERE sender_bank = 'HDFC' AND receiver_bank = 'SBI'")
print("[✓] Q28 trained")

# Q29
vn.train(question="Show transactions from Delhi on Android devices that failed.",
         sql="SELECT transaction_id, amount_inr, transaction_type, sender_bank FROM transactions WHERE sender_state = 'Delhi' AND device_type = 'Android' AND transaction_status = 'FAILED' ORDER BY amount_inr DESC")
print("[✓] Q29 trained")

# Q30
vn.train(question="How many Young senders from Maharashtra made Shopping transactions?",
         sql="SELECT COUNT(*) as txn_count FROM transactions WHERE sender_age_label = 'Young' AND sender_state = 'Maharashtra' AND merchant_category = 'Shopping'")
print("[✓] Q30 trained")

# ============================================================
# 10. EXPANDED FEW-SHOT EXAMPLES (NULL Handling & Edge Cases)
# ============================================================

# Q31
vn.train(question="How many P2P transactions have no merchant category?",
         sql="SELECT COUNT(*) as count FROM transactions WHERE transaction_type = 'P2P' AND merchant_category IS NULL")
print("[✓] Q31 trained")

# Q32
vn.train(question="Show non-P2P transactions where receiver age is missing.",
         sql="SELECT transaction_type, COUNT(*) as count FROM transactions WHERE transaction_type != 'P2P' AND receiver_age_group IS NULL GROUP BY transaction_type")
print("[✓] Q32 trained")

# Q33
vn.train(question="What is the total number of transactions in the database?",
         sql="SELECT COUNT(*) as total_transactions FROM transactions")
print("[✓] Q33 trained")

# Q34
vn.train(question="What are all the distinct merchant categories?",
         sql="SELECT DISTINCT merchant_category FROM transactions WHERE merchant_category IS NOT NULL ORDER BY merchant_category")
print("[✓] Q34 trained")

# Q35
vn.train(question="List all the unique sender states.",
         sql="SELECT DISTINCT sender_state FROM transactions ORDER BY sender_state")
print("[✓] Q35 trained")

# ============================================================
# 11. EXPANDED FEW-SHOT EXAMPLES (CASE WHEN & Bucketing)
# ============================================================

# Q36
vn.train(question="Categorize transactions as High Risk or Low Risk based on fraud flag and amount.",
         sql="SELECT CASE WHEN fraud_flag = 1 AND amount_inr > 5000 THEN 'High Risk' WHEN fraud_flag = 1 THEN 'Medium Risk' ELSE 'Low Risk' END as risk_category, COUNT(*) as count FROM transactions GROUP BY risk_category")
print("[✓] Q36 trained")

# Q37
vn.train(question="Compare success rates across all device types.",
         sql="SELECT device_type, COUNT(*) as total, SUM(CASE WHEN transaction_status = 'SUCCESS' THEN 1 ELSE 0 END) as success_count, (SUM(CASE WHEN transaction_status = 'SUCCESS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as success_rate FROM transactions GROUP BY device_type ORDER BY success_rate DESC")
print("[✓] Q37 trained")

# Q38
vn.train(question="What is the failure rate breakdown by network type and device type?",
         sql="SELECT network_type, device_type, COUNT(*) as total, (SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as failure_rate FROM transactions GROUP BY network_type, device_type ORDER BY failure_rate DESC")
print("[✓] Q38 trained")

# Q39
vn.train(question="Label each hour of day as peak or off-peak based on transaction count.",
         sql="SELECT hour_of_day, COUNT(*) as txn_count, CASE WHEN COUNT(*) > (SELECT COUNT(*) / 24 FROM transactions) THEN 'Peak' ELSE 'Off-Peak' END as hour_label FROM transactions GROUP BY hour_of_day ORDER BY hour_of_day")
print("[✓] Q39 trained")

# ============================================================
# 12. EXPANDED FEW-SHOT EXAMPLES (Cross-Column Analytics)
# ============================================================

# Q40
vn.train(question="Which bank pair has the highest failure rate?",
         sql="SELECT sender_bank, receiver_bank, COUNT(*) as total, (SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as failure_rate FROM transactions GROUP BY sender_bank, receiver_bank HAVING total > 100 ORDER BY failure_rate DESC LIMIT 5")
print("[✓] Q40 trained")

# Q41
vn.train(question="Which age group and device type combination has the most transactions?",
         sql="SELECT sender_age_label, device_type, COUNT(*) as txn_count FROM transactions GROUP BY sender_age_label, device_type ORDER BY txn_count DESC LIMIT 5")
print("[✓] Q41 trained")

# Q42
vn.train(question="What is the average transaction amount by day of week, sorted from highest to lowest?",
         sql="SELECT day_of_week, AVG(amount_inr) as avg_amount, COUNT(*) as txn_count FROM transactions GROUP BY day_of_week ORDER BY avg_amount DESC")
print("[✓] Q42 trained")

# Q43
vn.train(question="Show the top 3 states by number of successful large transactions.",
         sql="SELECT sender_state, COUNT(*) as large_success_count FROM transactions WHERE amount_tier = 'Large' AND transaction_status = 'SUCCESS' GROUP BY sender_state ORDER BY large_success_count DESC LIMIT 3")
print("[✓] Q43 trained")

# Q44
vn.train(question="Compare weekend vs weekday fraud rates for each bank.",
         sql="SELECT sender_bank, CASE WHEN is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END as period, (SUM(fraud_flag) * 100.0 / COUNT(*)) as fraud_rate FROM transactions GROUP BY sender_bank, period ORDER BY sender_bank, period")
print("[✓] Q44 trained")

# ============================================================
# 13. EXPANDED FEW-SHOT EXAMPLES (Ranking & Limits)
# ============================================================

# Q45
vn.train(question="Show the bottom 5 states by transaction volume.",
         sql="SELECT sender_state, COUNT(*) as txn_count FROM transactions GROUP BY sender_state ORDER BY txn_count ASC LIMIT 5")
print("[✓] Q45 trained")

# Q46
vn.train(question="Which are the top 3 merchant categories by revenue?",
         sql="SELECT merchant_category, SUM(amount_inr) as total_revenue FROM transactions WHERE merchant_category IS NOT NULL GROUP BY merchant_category ORDER BY total_revenue DESC LIMIT 3")
print("[✓] Q46 trained")

# Q47
vn.train(question="What are the 10 most recent transactions?",
         sql="SELECT transaction_id, timestamp, transaction_type, amount_inr, sender_bank FROM transactions ORDER BY timestamp DESC LIMIT 10")
print("[✓] Q47 trained")

# Q48
vn.train(question="How does each bank rank by total transaction amount?",
         sql="SELECT sender_bank, SUM(amount_inr) as total_amount, COUNT(*) as txn_count FROM transactions GROUP BY sender_bank ORDER BY total_amount DESC")
print("[✓] Q48 trained")

# Q49
vn.train(question="Which hour has the highest fraud rate?",
         sql="SELECT hour_of_day, (SUM(fraud_flag) * 100.0 / COUNT(*)) as fraud_rate, COUNT(*) as total FROM transactions GROUP BY hour_of_day ORDER BY fraud_rate DESC LIMIT 1")
print("[✓] Q49 trained")

# Q50
vn.train(question="Give me a summary of transactions by type showing count, total amount, average amount, and failure rate.",
         sql="SELECT transaction_type, COUNT(*) as count, SUM(amount_inr) as total_amount, AVG(amount_inr) as avg_amount, (SUM(CASE WHEN transaction_status = 'FAILED' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as failure_rate FROM transactions GROUP BY transaction_type ORDER BY count DESC")
print("[✓] Q50 trained")

# ============================================================
# DONE
# ============================================================


print("\n" + "=" * 50)
print("  Vanna training complete!")
print(f"  Model: {GROQ_MODEL} (Groq)")
print(f"  Vector Store: ChromaDB ({VECTOR_STORE_PATH})")
print(f"  Database: {DB_PATH}")
print("  Training items: DDL + Data Dictionary + 2 Business Rules + 15 Few-Shot Examples")
print("=" * 50)
