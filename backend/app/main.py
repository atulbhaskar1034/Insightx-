"""
app/main.py -- InsightX Agentic API (Dual-AI Pipeline + ML Models).

Pipeline:
  User Question -> Vanna AI (Local ChromaDB + Groq LLM for SQL)
  -> Groq LLM (Executive Summary + Follow-ups)
  -> Unified JSON Response

ML Models:
  XGBoost Fraud Detection Classifier (with SHAP explainability)
  Prophet Time-Series Forecasting (30-day transaction volume prediction)

No external Vanna API key needed -- all training data lives in local ChromaDB.
"""

import json
import os
import base64
import tempfile
import sys

# Force UTF-8 stdout so unicode print statements work on Windows terminals
sys.stdout.reconfigure(encoding="utf-8")

import traceback

from app import chat_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

import numpy as np
import pandas as pd
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from groq import Groq
from openai import OpenAI
from pydantic import BaseModel
from vanna.legacy.chromadb.chromadb_vector import ChromaDB_VectorStore
from vanna.legacy.openai.openai_chat import OpenAI_Chat

# -- Path Resolution -----------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "data", "upi_transactions.db")
VECTOR_STORE_PATH = os.path.join(PROJECT_ROOT, "vector_store")

# -- Load Environment Variables ------------------------------------------------

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Create a .env file in backend/ (see .env.example).")


# -- Vanna AI -- Local ChromaDB + Groq (OpenAI-compatible) ---------------------

class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, client=None, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, client=client, config=config)


# Groq as OpenAI-compatible client for Vanna's SQL generation
vanna_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

vn = MyVanna(client=vanna_client, config={
    "model": GROQ_MODEL,
    "path": VECTOR_STORE_PATH,
})
vn.connect_to_sqlite(DB_PATH)
print(f"[OK] Vanna AI initialized (local ChromaDB: {VECTOR_STORE_PATH})")
print(f"[OK] Connected to SQLite: {DB_PATH}")

# Groq native client for answer synthesis
groq_client = Groq(api_key=GROQ_API_KEY)
print(f"[OK] Groq LLM initialized (model: {GROQ_MODEL})")

# -- ML Models -----------------------------------------------------------------

MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
fraud_model = None
fraud_encoders = None
forecast_data = None

try:
    import joblib
    fraud_model_path = os.path.join(MODEL_DIR, "fraud_model.joblib")
    fraud_encoders_path = os.path.join(MODEL_DIR, "fraud_encoders.joblib")
    if os.path.exists(fraud_model_path) and os.path.exists(fraud_encoders_path):
        fraud_model = joblib.load(fraud_model_path)
        fraud_encoders = joblib.load(fraud_encoders_path)
        print("[OK] Fraud detection model loaded")
    else:
        print("[!] Fraud model not found. Run: python scripts/train_fraud_model.py")
except Exception as e:
    print(f"[!] Fraud model load failed: {e}")

try:
    forecast_data_path = os.path.join(MODEL_DIR, "forecast_data.json")
    if os.path.exists(forecast_data_path):
        with open(forecast_data_path, "r") as f:
            forecast_data = json.load(f)
        print("[OK] Forecast data loaded")
    else:
        print("[!] Forecast data not found. Run: python scripts/train_forecast_model.py")
except Exception as e:
    print(f"[!] Forecast data load failed: {e}")

# -- Chat History DB -----------------------------------------------------------

chat_db.init_db()
print("[OK] Chat history database initialized")

# -- FastAPI App ---------------------------------------------------------------

app = FastAPI(title="InsightX Agentic API")

FRONTEND_URL = os.getenv("FRONTEND_URL", "*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- Pydantic Models -----------------------------------------------------------

class ChatMessage(BaseModel):
    role: str       # "user" | "assistant"
    content: str

class QueryRequest(BaseModel):
    question: str
    chat_history: list[ChatMessage] = []
    session_id: str | None = None


# -- DB Schema (used to ground follow-up question generation) ------------------

DB_SCHEMA = """
Table: transactions
Columns:
  transaction_id TEXT       -- unique ID e.g. TXN0000000001
  timestamp TEXT            -- datetime e.g. 2024-10-08 15:17:28
  transaction_type TEXT     -- P2P | P2M | Bill Payment | Recharge
  merchant_category TEXT    -- Food | Grocery | Shopping | Fuel | Utilities | Entertainment | Healthcare | Transport | Education | Other (NULL for P2P)
  amount_inr INTEGER        -- transaction amount in INR
  transaction_status TEXT   -- SUCCESS | FAILED
  sender_age_group TEXT     -- 18-25 | 26-35 | 36-45 | 46-55 | 56+
  receiver_age_group TEXT   -- same as sender (NULL for non-P2P)
  sender_state TEXT         -- Indian state e.g. Delhi, Maharashtra, Karnataka
  sender_bank TEXT          -- SBI | HDFC | ICICI | Axis | Kotak | PNB | Yes Bank | IndusInd
  receiver_bank TEXT        -- same options as sender_bank
  device_type TEXT          -- Android | iOS | Web
  network_type TEXT         -- 3G | 4G | 5G | WiFi
  fraud_flag INTEGER        -- 0 (not fraud) | 1 (fraud)
  hour_of_day INTEGER       -- 0-23
  day_of_week TEXT          -- Monday - Sunday
  is_weekend INTEGER        -- 0 (weekday) | 1 (weekend)
  day_part TEXT             -- Morning | Afternoon | Evening | Night
  amount_tier TEXT          -- Small (<500) | Medium (500-5000) | Large (5000-50000)
  sender_age_label TEXT     -- Young (18-25) | Adult (26-55) | Old (56+)
  receiver_age_label TEXT   -- Young | Adult | Old (NULL for non-P2P)
"""

# -- Groq Synthesis Prompt -----------------------------------------------------

SYNTHESIS_PROMPT = """You are an elite data analyst for InsightX.
The user asked: "{question}".
The database returned this exact data:
{df_markdown}

--- DATABASE SCHEMA ---
{schema}
--- END SCHEMA ---

Task 1: Write a concise, highly professional executive summary (2-3 sentences).
STRICT RULES FOR SUMMARY:
- ALWAYS include rupee symbols (₹) for monetary values.
- NEVER invent, hallucinate, or assume numbers, units, or facts not explicitly in the data table (e.g., do NOT say "crores" or "millions" unless the data explicitly says so).
- NEVER add generic fluff like "This analysis can help identify trends..." or "This indicates a preference...". Just state the facts.

Task 2: Suggest exactly 3 logical follow-up questions. STRICT RULES:
- Every question MUST be answerable using only the columns and values listed in the schema.
- Reference real column names and real values (e.g. sender_bank = 'HDFC', transaction_type = 'P2P').
- Do NOT invent columns, tables, or data that are not in the schema.
- Questions should be a natural, different-angle continuation of the current analysis.

Task 3: Decide the best way to visualize this data. Choose ONE chart type: "bar", "line", "pie", or "kpi".
STRICT RULES FOR CHARTS:
- If the user's question contains words like "distribution", "breakdown", "share", or "percentage", you MUST output "pie".
- If the data is a single number, output "kpi".
- If the data shows a trend over time (days, hours, months), output "line".
- If comparing categories (e.g., banks, states, network types) and it is NOT a distribution, output "bar".

You MUST return your response as a valid JSON object.
Use exactly these keys:
"answer" (string),
"follow_up_questions" (list of strings),
"chart_type" (string: "bar", "line", "pie", or "kpi"),
"x_axis" (string: the EXACT column name from the data to use as the X-axis label/category. E.g., 'NETWORK TYPE'),
"y_axis" (string: the EXACT column name from the data to use as the Y-axis value. E.g., 'TXN COUNT')"""


# -- Core Endpoint: /api/ask ---------------------------------------------------

@app.post("/api/ask")
async def ask_insightx(request: QueryRequest):
    """
    Full Dual-AI Pipeline:
      Question -> Vanna (SQL + Data) -> Groq (Summary + Follow-ups) -> JSON
    """
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question cannot be empty.")

        # -- Step 0: Intent Guardrail ------------------------------------------
        intent_check = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    f"Is this a data or analytics question about UPI transactions or financial data? "
                    f"Reply with exactly one word: YES or NO.\n\nInput: \"{question}\""
                )
            }],
            temperature=0.0,
            max_tokens=1024,
        )
        intent = intent_check.choices[0].message.content.strip().upper()

        if not intent.startswith("YES"):
            # Not a data question -- friendly conversational response with history
            history_msgs = [
                {"role": msg.role, "content": msg.content}
                for msg in request.chat_history[-10:]
            ]
            chat_reply = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are InsightX, an AI assistant for UPI transaction analytics. "
                            "You remember everything the user has told you in this conversation. "
                            "If the user sends a greeting or off-topic message, reply briefly and "
                            "guide them to ask a data question. Keep it friendly and concise."
                        ),
                    },
                    *history_msgs,
                    {"role": "user", "content": question},
                ],
                temperature=0.7,
                max_tokens=150,
            )
            reply_text = chat_reply.choices[0].message.content.strip()
            response_payload = {
                "question": question,
                "sql": "",
                "data": [],
                "answer": reply_text,
                "follow_up_questions": [
                    "Show total UPI transaction volume",
                    "Which bank had the most transactions?",
                    "What are the top 5 transactions by amount?",
                ],
            }

            # Save to DB
            if request.session_id:
                try:
                    chat_db.add_message(request.session_id, "user", question)
                    chat_db.add_message(request.session_id, "assistant", reply_text)
                    msgs = chat_db.get_messages(request.session_id)
                    if len(msgs) <= 2:
                        chat_db.auto_title(request.session_id, question)
                except Exception as save_err:
                    print(f"[SAVE ERROR - conversational] {save_err}")
                    traceback.print_exc()

            return response_payload

        # -- Step A: Vanna AI -- Generate SQL & Execute ------------------------
        generated_sql = vn.generate_sql(question)

        if generated_sql is None or generated_sql.strip() == "":
            generated_sql = "-- Could not generate SQL"

        df = None
        if not generated_sql.startswith("--"):
            try:
                df = vn.run_sql(generated_sql)
            except Exception:
                df = None

        # -- Step B: Data Formatting -------------------------------------------
        if df is None or (isinstance(df, pd.DataFrame) and df.empty):
            df_markdown = "No data found."
            data_dict = []
        else:
            df_markdown = df.to_markdown(index=False)
            data_dict = df.fillna("None").to_dict(orient="records")

        # -- Step C: Groq Synthesis with chat history --------------------------
        prompt = SYNTHESIS_PROMPT.format(
            question=question,
            df_markdown=df_markdown,
            schema=DB_SCHEMA,
        )

        history_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.chat_history[-6:]
        ]

        groq_response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are InsightX, an expert data analyst for UPI transaction data. "
                        "You answer questions about the transactions SQLite database."
                    ),
                },
                *history_messages,
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        raw_content = groq_response.choices[0].message.content.strip()

        # -- Step D: Response Parsing ------------------------------------------
        try:
            llm_result = json.loads(raw_content)
        except json.JSONDecodeError:
            llm_result = {
                "answer": raw_content,
                "follow_up_questions": [
                    "Can you break this down by transaction type?",
                    "What does the trend look like over time?",
                    "Are there any anomalies in this data?",
                ],
            }

        answer = llm_result.get("answer", raw_content)
        follow_ups = llm_result.get("follow_up_questions", [])[:3]
        chart_type = llm_result.get("chart_type", "table")
        x_axis = llm_result.get("x_axis")
        y_axis = llm_result.get("y_axis")

        # -- Step E: Persist to DB & Return ------------------------------------
        response_payload = {
            "question": question,
            "sql": generated_sql,
            "data": data_dict,
            "answer": answer,
            "follow_up_questions": follow_ups,
            "chart_type": chart_type,
            "x_axis": x_axis,
            "y_axis": y_axis,
        }

        if request.session_id:
            try:
                chat_db.add_message(request.session_id, "user", question)
                chat_db.add_message(
                    session_id=request.session_id,
                    role="assistant",
                    content=answer,
                    sql_text=generated_sql,
                    data_json=json.dumps(response_payload, default=str),
                )
                msgs = chat_db.get_messages(request.session_id)
                if len(msgs) <= 2:
                    chat_db.auto_title(request.session_id, question)
            except Exception as save_err:
                print(f"[SAVE ERROR - data] {save_err}")
                traceback.print_exc()

        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -- ML: Fraud Prediction Endpoint ---------------------------------------------

FRAUD_FEATURE_COLS = [
    "transaction_type", "amount_inr", "sender_bank", "receiver_bank",
    "device_type", "network_type", "sender_state", "hour_of_day",
    "is_weekend", "day_part", "amount_tier", "sender_age_label",
]

FRAUD_CATEGORICAL_COLS = [
    "transaction_type", "sender_bank", "receiver_bank", "device_type",
    "network_type", "sender_state", "day_part", "amount_tier", "sender_age_label",
]


class FraudPredictionRequest(BaseModel):
    transaction_type: str = "P2M"
    amount_inr: int = 5000
    sender_bank: str = "SBI"
    receiver_bank: str = "HDFC"
    device_type: str = "Android"
    network_type: str = "4G"
    sender_state: str = "Delhi"
    hour_of_day: int = 14
    is_weekend: int = 0
    day_part: str = "Afternoon"
    amount_tier: str = "Medium (₹500-5000)"
    sender_age_label: str = "Adult (26-55)"


@app.post("/api/predict-fraud")
async def predict_fraud(request: FraudPredictionRequest):
    """Predict fraud probability for a transaction using XGBoost + SHAP."""
    if fraud_model is None or fraud_encoders is None:
        raise HTTPException(
            status_code=503,
            detail="Fraud model not available. Run: python scripts/train_fraud_model.py",
        )

    try:
        # Build feature vector
        input_data = {
            "transaction_type": request.transaction_type,
            "amount_inr": request.amount_inr,
            "sender_bank": request.sender_bank,
            "receiver_bank": request.receiver_bank,
            "device_type": request.device_type,
            "network_type": request.network_type,
            "sender_state": request.sender_state,
            "hour_of_day": request.hour_of_day,
            "is_weekend": request.is_weekend,
            "day_part": request.day_part,
            "amount_tier": request.amount_tier,
            "sender_age_label": request.sender_age_label,
        }

        # Encode categorical features
        encoded = input_data.copy()
        for col in FRAUD_CATEGORICAL_COLS:
            le = fraud_encoders.get(col)
            if le is not None:
                val = str(encoded[col])
                if val in le.classes_:
                    encoded[col] = le.transform([val])[0]
                else:
                    encoded[col] = 0  # Unknown category fallback

        # Create feature array
        features = np.array([[encoded[col] for col in FRAUD_FEATURE_COLS]])

        # Predict
        probability = float(fraud_model.predict_proba(features)[0][1])
        prediction = int(probability >= 0.5)

        # SHAP explanation
        shap_contributions = {}
        try:
            import shap
            explainer = shap.TreeExplainer(fraud_model)
            shap_values = explainer.shap_values(features)
            for i, col in enumerate(FRAUD_FEATURE_COLS):
                shap_contributions[col] = round(float(shap_values[0][i]), 4)
            # Sort by absolute impact
            shap_contributions = dict(
                sorted(shap_contributions.items(), key=lambda x: abs(x[1]), reverse=True)
            )
        except Exception:
            pass

        risk_level = "Low" if probability < 0.3 else "Medium" if probability < 0.7 else "High"

        return {
            "fraud_probability": round(probability, 4),
            "prediction": "FRAUD" if prediction else "LEGITIMATE",
            "risk_level": risk_level,
            "shap_contributions": shap_contributions,
            "input_features": input_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Fraud prediction failed: {str(e)}")


@app.get("/api/fraud-stats")
async def fraud_stats():
    """Return pre-computed fraud statistics for the dashboard."""
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        stats = {}

        # Overall fraud rate
        row = conn.execute(
            "SELECT COUNT(*) as total, SUM(fraud_flag) as fraud_count FROM transactions"
        ).fetchone()
        stats["overall_fraud_rate"] = round(row["fraud_count"] / row["total"] * 100, 2)
        stats["total_transactions"] = row["total"]
        stats["fraud_count"] = row["fraud_count"]

        # Fraud rate by bank
        rows = conn.execute(
            "SELECT sender_bank, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
            "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
            "FROM transactions GROUP BY sender_bank ORDER BY fraud_rate DESC"
        ).fetchall()
        stats["by_bank"] = [{"bank": r["sender_bank"], "total": r["total"],
                             "fraud_count": r["fraud_count"], "fraud_rate": r["fraud_rate"]} for r in rows]

        # Fraud rate by time of day
        rows = conn.execute(
            "SELECT day_part, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
            "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
            "FROM transactions GROUP BY day_part ORDER BY fraud_rate DESC"
        ).fetchall()
        stats["by_day_part"] = [{"day_part": r["day_part"], "total": r["total"],
                                 "fraud_count": r["fraud_count"], "fraud_rate": r["fraud_rate"]} for r in rows]

        # Fraud rate by network
        rows = conn.execute(
            "SELECT network_type, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
            "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
            "FROM transactions GROUP BY network_type ORDER BY fraud_rate DESC"
        ).fetchall()
        stats["by_network"] = [{"network": r["network_type"], "total": r["total"],
                                "fraud_count": r["fraud_count"], "fraud_rate": r["fraud_rate"]} for r in rows]

        conn.close()
        return stats

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -- ML: Forecast Endpoint -----------------------------------------------------

@app.get("/api/forecast")
async def get_forecast():
    """Return 30-day transaction volume forecast."""
    if forecast_data is None:
        raise HTTPException(
            status_code=503,
            detail="Forecast data not available. Run: python scripts/train_forecast_model.py",
        )
    return forecast_data


# -- Session CRUD Endpoints ----------------------------------------------------

@app.get("/api/sessions")
async def list_sessions():
    """List all chat sessions, newest first."""
    return chat_db.list_sessions()

@app.post("/api/sessions")
async def create_session():
    """Create a new chat session."""
    return chat_db.create_session()

@app.get("/api/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    """Get all messages for a session."""
    return chat_db.get_messages(session_id)

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session and all its messages."""
    deleted = chat_db.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


# -- Health Check --------------------------------------------------------------

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "InsightX Agentic API"}


# -- Run -----------------------------------------------------------------------

if __name__ == "__main__":
    print("[OK] Starting InsightX Agentic API on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
