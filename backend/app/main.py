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

import asyncio
import hashlib
import json
import os
import base64
import tempfile
import sys

# Force UTF-8 stdout so unicode print statements work on Windows terminals
sys.stdout.reconfigure(encoding="utf-8")

import traceback

from cachetools import TTLCache

from app import chat_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

import numpy as np
import pandas as pd
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
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
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Create a .env file in backend/ (see .env.example).")


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Groq as OpenAI-compatible client for Vanna's SQL generation
vanna_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

if PINECONE_API_KEY:
    # Use Pinecone (Production/Managed)
    from vanna.legacy.pinecone.pinecone_vector import PineconeDB_VectorStore
    
    class MyVanna(PineconeDB_VectorStore, OpenAI_Chat):
        def __init__(self, client=None, config=None):
            PineconeDB_VectorStore.__init__(self, config=config)
            OpenAI_Chat.__init__(self, client=client, config=config)
            
    vn = MyVanna(client=vanna_client, config={
        "model": GROQ_MODEL,
        "pinecone_api_key": PINECONE_API_KEY,
        "pinecone_index_name": "insightx-index",
    })
    print("[OK] Vanna AI initialized (Pinecone Vector Store)")
else:
    # Use ChromaDB (Local Dev)
    from vanna.legacy.chromadb.chromadb_vector import ChromaDB_VectorStore
    
    class MyVanna(ChromaDB_VectorStore, OpenAI_Chat):
        def __init__(self, client=None, config=None):
            ChromaDB_VectorStore.__init__(self, config=config)
            OpenAI_Chat.__init__(self, client=client, config=config)
            
    vn = MyVanna(client=vanna_client, config={
        "model": GROQ_MODEL,
        "path": VECTOR_STORE_PATH,
    })
    print(f"[OK] Vanna AI initialized (local ChromaDB: {VECTOR_STORE_PATH})")

# Connect to Postgres (production) or SQLite (local dev)
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    pg_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
    if "&channel_binding=require" in pg_url:
        pg_url = pg_url.replace("&channel_binding=require", "")
    elif "?channel_binding=require&" in pg_url:
        pg_url = pg_url.replace("channel_binding=require&", "")
    elif "?channel_binding=require" in pg_url:
        pg_url = pg_url.replace("?channel_binding=require", "")
    from urllib.parse import urlparse
    result = urlparse(pg_url)
    vn.connect_to_postgres(
        host=result.hostname,
        dbname=result.path[1:] if result.path.startswith("/") else result.path,
        user=result.username,
        password=result.password,
        port=result.port or 5432,
    )
    print(f"[OK] Vanna AI connected to PostgreSQL (Neon)")
else:
    vn.connect_to_sqlite(DB_PATH)
    print(f"[OK] Vanna AI connected to SQLite: {DB_PATH}")
print(f"[OK] Vanna AI initialized (local ChromaDB: {VECTOR_STORE_PATH})")

# Groq native client for answer synthesis
groq_client = Groq(api_key=GROQ_API_KEY)

# ── Performance: In-Memory TTL Caches ($0 Redis alternative) ──────────────────
# Cache identical query responses to avoid redundant LLM calls and DB queries.

# Cache up to 200 recent /api/ask responses for 15 minutes
ask_cache = TTLCache(maxsize=200, ttl=900)

# Cache fraud statistics for 5 minutes (data changes rarely)
fraud_stats_cache = TTLCache(maxsize=5, ttl=300)

# Cache forecast data for 1 hour (static until model retrain)
forecast_cache = TTLCache(maxsize=10, ttl=3600)


def _cache_key(*args) -> str:
    """Generate a stable cache key from arguments."""
    return hashlib.md5(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()
print(f"[OK] Groq LLM initialized (model: {GROQ_MODEL})")

# -- ML Models -----------------------------------------------------------------

MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
fraud_model = None
fraud_encoders = None
fraud_explainer = None  # Pre-computed SHAP explainer (initialized once at startup)
forecast_data = None

try:
    import joblib
    import shap as shap_module
    fraud_model_path = os.path.join(MODEL_DIR, "fraud_model.joblib")
    fraud_encoders_path = os.path.join(MODEL_DIR, "fraud_encoders.joblib")
    if os.path.exists(fraud_model_path) and os.path.exists(fraud_encoders_path):
        fraud_model = joblib.load(fraud_model_path)
        fraud_encoders = joblib.load(fraud_encoders_path)
        # Pre-compute SHAP TreeExplainer ONCE at startup instead of per-request.
        # This saves ~200-500ms of CPU time on every /api/predict-fraud call.
        fraud_explainer = shap_module.TreeExplainer(fraud_model)
        print("[OK] Fraud detection model loaded + SHAP explainer pre-computed")
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

# -- FastAPI Setup -------------------------------------------------------------

app = FastAPI(title="InsightX Backend API")

@app.on_event("startup")
async def startup_event():
    chat_db.init_db()

@app.get("/api/health")
async def health_check():
    """Simple health check endpoint for cold-start detection."""
    return {"status": "ok"}

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

        # -- Check ask_cache first (avoids redundant LLM calls) ----------------
        cache_key = _cache_key(question, [(m.role, m.content) for m in request.chat_history[-6:]])
        cached = ask_cache.get(cache_key)
        if cached is not None:
            # Serve from cache — 0 LLM calls, 0 DB queries, ~4ms response
            return cached

        # -- Step 0: Intent Guardrail ------------------------------------------
        # Wrapped in asyncio.to_thread to avoid blocking the event loop
        intent_check = await asyncio.to_thread(
            groq_client.chat.completions.create,
            model=GROQ_MODEL,
            messages=[{
                "role": "user",
                "content": (
                    f"Is this a data or analytics question about UPI transactions or financial data? "
                    f"Reply with exactly one word: YES or NO.\n\nInput: \"{question}\""
                )
            }],
            temperature=0.0,
            max_tokens=5,  # Only needs YES/NO — was wasting 1024 tokens before
        )
        intent = intent_check.choices[0].message.content.strip().upper()

        if not intent.startswith("YES"):
            # Not a data question -- friendly conversational response with history
            history_msgs = [
                {"role": msg.role, "content": msg.content}
                for msg in request.chat_history[-10:]
            ]
            chat_reply = await asyncio.to_thread(
                groq_client.chat.completions.create,
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
        # Wrapped in asyncio.to_thread — Vanna calls are sync and block the event loop
        generated_sql = await asyncio.to_thread(vn.generate_sql, question)

        if generated_sql is None or generated_sql.strip() == "":
            generated_sql = "-- Could not generate SQL"

        df = None
        if not generated_sql.startswith("--"):
            try:
                df = await asyncio.to_thread(vn.run_sql, generated_sql)
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

        groq_response = await asyncio.to_thread(
            groq_client.chat.completions.create,
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

        # Cache this response for future identical questions
        ask_cache[cache_key] = response_payload

        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -- SSE Streaming Endpoint: /api/ask-stream -----------------------------------

def _sse(event: str, data: str) -> str:
    """Format a Server-Sent Event line pair."""
    # Escape newlines in data to keep SSE protocol valid
    safe_data = data.replace("\n", "\\n")
    return f"event: {event}\ndata: {safe_data}\n\n"


@app.post("/api/ask-stream")
async def ask_stream(request: QueryRequest):
    """
    SSE-streaming version of /api/ask.
    Emits events: status, sql, data, complete, error.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    def generate():
        try:
            # -- Step 0: Intent Guardrail ------------------------------------------
            yield _sse("status", "Analyzing your question…")

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
                max_tokens=5,  # Only needs YES/NO
            )
            intent = intent_check.choices[0].message.content.strip().upper()

            if not intent.startswith("YES"):
                # ── Conversational (non-data) reply ──
                yield _sse("status", "Generating response…")

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

                payload = {
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

                # Persist
                if request.session_id:
                    try:
                        chat_db.add_message(request.session_id, "user", question)
                        chat_db.add_message(request.session_id, "assistant", reply_text)
                        msgs = chat_db.get_messages(request.session_id)
                        if len(msgs) <= 2:
                            chat_db.auto_title(request.session_id, question)
                    except Exception as save_err:
                        print(f"[SAVE ERROR - conversational stream] {save_err}")
                        traceback.print_exc()

                yield _sse("complete", json.dumps(payload, default=str))
                return

            # -- Step A: Generate SQL ----------------------------------------------
            yield _sse("status", "Writing SQL query…")
            generated_sql = vn.generate_sql(question)
            if generated_sql is None or generated_sql.strip() == "":
                generated_sql = "-- Could not generate SQL"
            yield _sse("sql", generated_sql)

            # -- Step B: Execute SQL -----------------------------------------------
            yield _sse("status", "Querying database…")
            df = None
            if not generated_sql.startswith("--"):
                try:
                    df = vn.run_sql(generated_sql)
                except Exception:
                    df = None

            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                df_markdown = "No data found."
                data_dict = []
            else:
                df_markdown = df.to_markdown(index=False)
                data_dict = df.fillna("None").to_dict(orient="records")

            yield _sse("data", json.dumps(data_dict[:50], default=str))

            # -- Step C: Groq Synthesis --------------------------------------------
            yield _sse("status", "Generating insights…")

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

            # -- Step D: Final payload ---------------------------------------------
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

            # Persist
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
                    print(f"[SAVE ERROR - data stream] {save_err}")
                    traceback.print_exc()

            yield _sse("complete", json.dumps(response_payload, default=str))

        except Exception as e:
            traceback.print_exc()
            yield _sse("error", json.dumps({"detail": str(e)}))

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

        # Predict — wrapped in asyncio.to_thread to avoid blocking the event loop
        pred_result = await asyncio.to_thread(fraud_model.predict_proba, features)
        probability = float(pred_result[0][1])
        prediction = int(probability >= 0.5)

        # SHAP explanation — uses pre-computed explainer (initialized at startup)
        shap_contributions = {}
        try:
            if fraud_explainer is not None:
                shap_values = await asyncio.to_thread(fraud_explainer.shap_values, features)
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
    """Return pre-computed fraud statistics for the dashboard.
    
    Results are cached in-memory for 5 minutes to avoid redundant DB queries.
    """
    # Check cache first
    cached = fraud_stats_cache.get("stats")
    if cached is not None:
        return cached

    try:
        stats = {}

        def _fetch_fraud_stats_sync():
            """Synchronous function to fetch fraud stats, run via asyncio.to_thread."""
            _stats = {}
            if DATABASE_URL:
                # Production: Neon PostgreSQL — use connection pool via chat_db.DBConn
                with chat_db.DBConn() as db:
                    db.execute("SELECT COUNT(*) as total, SUM(fraud_flag) as fraud_count FROM transactions")
                    row = db.cursor.fetchone()
                    _stats["overall_fraud_rate"] = round(row["fraud_count"] / row["total"] * 100, 2)
                    _stats["total_transactions"] = row["total"]
                    _stats["fraud_count"] = row["fraud_count"]

                    db.execute(
                        "SELECT sender_bank, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
                        "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
                        "FROM transactions GROUP BY sender_bank ORDER BY fraud_rate DESC"
                    )
                    _stats["by_bank"] = [{"bank": r["sender_bank"], "total": r["total"],
                                         "fraud_count": r["fraud_count"], "fraud_rate": float(r["fraud_rate"])} for r in db.fetchall()]

                    db.execute(
                        "SELECT day_part, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
                        "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
                        "FROM transactions GROUP BY day_part ORDER BY fraud_rate DESC"
                    )
                    _stats["by_day_part"] = [{"day_part": r["day_part"], "total": r["total"],
                                             "fraud_count": r["fraud_count"], "fraud_rate": float(r["fraud_rate"])} for r in db.fetchall()]

                    db.execute(
                        "SELECT network_type, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
                        "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
                        "FROM transactions GROUP BY network_type ORDER BY fraud_rate DESC"
                    )
                    _stats["by_network"] = [{"network": r["network_type"], "total": r["total"],
                                            "fraud_count": r["fraud_count"], "fraud_rate": float(r["fraud_rate"])} for r in db.fetchall()]
            else:
                # Local dev: SQLite
                import sqlite3
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row

                row = conn.execute(
                    "SELECT COUNT(*) as total, SUM(fraud_flag) as fraud_count FROM transactions"
                ).fetchone()
                _stats["overall_fraud_rate"] = round(row["fraud_count"] / row["total"] * 100, 2)
                _stats["total_transactions"] = row["total"]
                _stats["fraud_count"] = row["fraud_count"]

                rows = conn.execute(
                    "SELECT sender_bank, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
                    "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
                    "FROM transactions GROUP BY sender_bank ORDER BY fraud_rate DESC"
                ).fetchall()
                _stats["by_bank"] = [{"bank": r["sender_bank"], "total": r["total"],
                                     "fraud_count": r["fraud_count"], "fraud_rate": r["fraud_rate"]} for r in rows]

                rows = conn.execute(
                    "SELECT day_part, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
                    "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
                    "FROM transactions GROUP BY day_part ORDER BY fraud_rate DESC"
                ).fetchall()
                _stats["by_day_part"] = [{"day_part": r["day_part"], "total": r["total"],
                                         "fraud_count": r["fraud_count"], "fraud_rate": r["fraud_rate"]} for r in rows]

                rows = conn.execute(
                    "SELECT network_type, COUNT(*) as total, SUM(fraud_flag) as fraud_count, "
                    "ROUND(SUM(fraud_flag) * 100.0 / COUNT(*), 2) as fraud_rate "
                    "FROM transactions GROUP BY network_type ORDER BY fraud_rate DESC"
                ).fetchall()
                _stats["by_network"] = [{"network": r["network_type"], "total": r["total"],
                                        "fraud_count": r["fraud_count"], "fraud_rate": r["fraud_rate"]} for r in rows]

                conn.close()
            return _stats

        stats = await asyncio.to_thread(_fetch_fraud_stats_sync)

        # Cache for 5 minutes
        fraud_stats_cache["stats"] = stats

        return stats

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -- ML: Forecast Endpoint -----------------------------------------------------

@app.get("/api/forecast")
async def get_forecast(
    horizon: int = 30,
    metric: str = "count",
    what_if_factor: float = 1.0,
):
    """
    Dynamic transaction volume forecast using Prophet.
    
    Query params:
        horizon:        Number of days to forecast (7, 14, 30, 60, 90). Default: 30.
        metric:         'count' (transaction count) or 'amount' (total amount). Default: 'count'.
        what_if_factor: Scaling multiplier for predictions (e.g. 0.9 = 10% drop). Default: 1.0.
    """
    # Clamp horizon to reasonable range
    horizon = max(7, min(horizon, 90))

    # Check forecast cache first
    fc_key = _cache_key("forecast", horizon, metric, what_if_factor)
    cached = forecast_cache.get(fc_key)
    if cached is not None:
        return cached

    # Try dynamic inference if Prophet model files exist
    count_model_path = os.path.join(MODEL_DIR, "forecast_count_model.joblib")
    amount_model_path = os.path.join(MODEL_DIR, "forecast_amount_model.joblib")

    if os.path.exists(count_model_path) and os.path.exists(amount_model_path):
        try:
            import joblib as jl

            # Load the appropriate model
            model_path = count_model_path if metric == "count" else amount_model_path
            model = jl.load(model_path)

            # Generate forecast with custom horizon — wrapped in asyncio.to_thread
            # because Prophet .predict() is CPU-bound and blocks the event loop
            def _run_prophet():
                future = model.make_future_dataframe(periods=horizon)
                return model.predict(future)

            full_forecast = await asyncio.to_thread(_run_prophet)

            # Split into historical fit and future predictions
            training_end = model.history["ds"].max()
            future_only = full_forecast[full_forecast["ds"] > training_end][
                ["ds", "yhat", "yhat_lower", "yhat_upper"]
            ].copy()

            # Apply what-if scaling
            if what_if_factor != 1.0:
                for col in ["yhat", "yhat_lower", "yhat_upper"]:
                    future_only[col] = future_only[col] * what_if_factor

            future_only["ds"] = future_only["ds"].dt.strftime("%Y-%m-%d")

            # Load historical data from the static forecast_data for the chart
            historical = []
            if forecast_data and "historical" in forecast_data:
                historical = forecast_data["historical"]

            # Build dynamic response
            result = {
                "historical": historical,
                "count_forecast": future_only.to_dict(orient="records") if metric == "count" else (
                    forecast_data.get("count_forecast", []) if forecast_data else []
                ),
                "amount_forecast": future_only.to_dict(orient="records") if metric == "amount" else (
                    forecast_data.get("amount_forecast", []) if forecast_data else []
                ),
                "metadata": {
                    "forecast_days": horizon,
                    "training_days": len(model.history),
                    "what_if_factor": what_if_factor,
                    "metric": metric,
                    "avg_daily_count": forecast_data["metadata"]["avg_daily_count"] if forecast_data else 0,
                    "avg_daily_amount": forecast_data["metadata"]["avg_daily_amount"] if forecast_data else 0,
                },
            }
            # Cache the result for 1 hour
            forecast_cache[fc_key] = result
            return result
        except Exception as e:
            print(f"[!] Dynamic forecast failed, falling back to static: {e}")
            traceback.print_exc()

    # Fallback: return static forecast_data.json
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
