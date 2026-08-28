/**
 * InsightX API Service
 * Typed client for the FastAPI backend.
 */

export interface ApiResponse {
    question: string;
    sql: string;
    data: Record<string, unknown>[];
    answer: string;
    follow_up_questions: string[];
    chart_type?: string;
    x_axis?: string | null;
    y_axis?: string | null;
}

export interface ChatHistoryMessage {
    role: "user" | "assistant";
    content: string;
}

export interface ChatSession {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface StoredMessage {
    id: number;
    role: "user" | "assistant";
    content: string;
    sql_text: string;
    data: Record<string, unknown>;
    created_at: string;
}

const BASE_URL = import.meta.env.VITE_API_URL || "/api";

export async function checkHealth(): Promise<boolean> {
    try {
        const res = await fetch(`${BASE_URL}/health`);
        return res.ok;
    } catch {
        return false;
    }
}

// -- Text Query ---------------------------------------------------------------

export async function askQuestion(
    question: string,
    chatHistory: ChatHistoryMessage[] = [],
    sessionId?: string | null,
): Promise<ApiResponse> {
    const res = await fetch(`${BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            question,
            chat_history: chatHistory,
            session_id: sessionId ?? null,
        }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Request failed (${res.status})`);
    }
    return res.json();
}

// -- SSE Streaming Query ------------------------------------------------------

export interface StreamEvent {
    event: string;
    data: string;
}

export async function askQuestionStream(
    question: string,
    chatHistory: ChatHistoryMessage[] = [],
    sessionId?: string | null,
    onEvent?: (event: StreamEvent) => void,
): Promise<ApiResponse> {
    const res = await fetch(`${BASE_URL}/ask-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            question,
            chat_history: chatHistory,
            session_id: sessionId ?? null,
        }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Request failed (${res.status})`);
    }

    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalPayload: ApiResponse | null = null;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse complete SSE events (separated by double newlines)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
            if (!part.trim()) continue;
            const lines = part.split("\n");
            let eventType = "";
            let eventData = "";

            for (const line of lines) {
                if (line.startsWith("event: ")) {
                    eventType = line.slice(7);
                } else if (line.startsWith("data: ")) {
                    eventData = line.slice(6);
                }
            }

            if (!eventType) continue;

            // Unescape newlines that were escaped on the backend
            const unescaped = eventData.replace(/\\n/g, "\n");

            if (eventType === "error") {
                const err = JSON.parse(unescaped);
                throw new Error(err.detail ?? "Stream error");
            }

            if (eventType === "complete") {
                finalPayload = JSON.parse(unescaped);
            }

            onEvent?.({ event: eventType, data: unescaped });
        }
    }

    if (!finalPayload) {
        throw new Error("Stream ended without a complete response");
    }

    return finalPayload;
}

// -- ML: Fraud Prediction -----------------------------------------------------

export async function predictFraud(
    features: Record<string, string | number>,
): Promise<{
    fraud_probability: number;
    prediction: string;
    risk_level: string;
    shap_contributions: Record<string, number>;
    input_features: Record<string, unknown>;
}> {
    const res = await fetch(`${BASE_URL}/predict-fraud`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(features),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Fraud prediction failed (${res.status})`);
    }
    return res.json();
}

// -- ML: Forecast -------------------------------------------------------------

export async function getForecast(params?: {
    horizon?: number;
    metric?: string;
    whatIfFactor?: number;
}): Promise<{
    historical: { date: string; txn_count: number; total_amount: number }[];
    count_forecast: { ds: string; yhat: number; yhat_lower: number; yhat_upper: number }[];
    amount_forecast: { ds: string; yhat: number; yhat_lower: number; yhat_upper: number }[];
    metadata: Record<string, unknown>;
}> {
    const searchParams = new URLSearchParams();
    if (params?.horizon) searchParams.set("horizon", String(params.horizon));
    if (params?.metric) searchParams.set("metric", params.metric);
    if (params?.whatIfFactor !== undefined) searchParams.set("what_if_factor", String(params.whatIfFactor));
    const qs = searchParams.toString();
    const url = `${BASE_URL}/forecast${qs ? `?${qs}` : ""}`;
    const res = await fetch(url);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Forecast request failed (${res.status})`);
    }
    return res.json();
}

// -- ML: Fraud Stats ----------------------------------------------------------

export async function getFraudStats(): Promise<{
    overall_fraud_rate: number;
    total_transactions: number;
    fraud_count: number;
    by_bank: { bank: string; fraud_rate: number; fraud_count: number; total: number }[];
    by_day_part: { day_part: string; fraud_rate: number; fraud_count: number; total: number }[];
    by_network: { network: string; fraud_rate: number; fraud_count: number; total: number }[];
}> {
    const res = await fetch(`${BASE_URL}/fraud-stats`);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `Fraud stats failed (${res.status})`);
    }
    return res.json();
}

// -- Session CRUD -------------------------------------------------------------

export async function listSessions(): Promise<ChatSession[]> {
    const res = await fetch(`${BASE_URL}/sessions`);
    if (!res.ok) throw new Error("Failed to load sessions");
    return res.json();
}

export async function createSession(): Promise<ChatSession> {
    const res = await fetch(`${BASE_URL}/sessions`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to create session");
    return res.json();
}

export async function getSessionMessages(sessionId: string): Promise<StoredMessage[]> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}/messages`);
    if (!res.ok) throw new Error("Failed to load messages");
    return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
    const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete session");
}

// -- Helpers ------------------------------------------------------------------

export function dataToTable(
    data: Record<string, unknown>[],
): { columns: string[]; rows: string[][] } | null {
    if (!data || data.length === 0) return null;
    const columns = Object.keys(data[0]);
    const rows = data.map((row) =>
        columns.map((col) => {
            const v = row[col];
            if (v === null || v === undefined) return "\u2014";
            if (typeof v === "number") {
                const formatted = v.toLocaleString("en-IN");
                return /amount|value|total|sum|credit|debit/i.test(col)
                    ? `\u20b9${formatted}`
                    : formatted;
            }
            return String(v);
        }),
    );
    return { columns, rows };
}

