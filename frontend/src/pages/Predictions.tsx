import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Shield,
  TrendingUp,
  ArrowLeft,
  AlertTriangle,
  CheckCircle,
  Info,
  ChevronDown,
  Loader2,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  ComposedChart,
  Line,
} from "recharts";
import { predictFraud, getForecast, getFraudStats } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

interface FraudResult {
  fraud_probability: number;
  prediction: string;
  risk_level: string;
  shap_contributions: Record<string, number>;
  input_features: Record<string, unknown>;
}

interface ForecastData {
  historical: { date: string; txn_count: number; total_amount: number }[];
  count_forecast: { ds: string; yhat: number; yhat_lower: number; yhat_upper: number }[];
  amount_forecast: { ds: string; yhat: number; yhat_lower: number; yhat_upper: number }[];
  metadata: {
    forecast_days: number;
    training_days: number;
    avg_daily_count: number;
    avg_daily_amount: number;
  };
}

interface FraudStats {
  overall_fraud_rate: number;
  total_transactions: number;
  fraud_count: number;
  by_bank: { bank: string; fraud_rate: number; fraud_count: number; total: number }[];
  by_day_part: { day_part: string; fraud_rate: number; fraud_count: number; total: number }[];
  by_network: { network: string; fraud_rate: number; fraud_count: number; total: number }[];
}

// ── Select Options ──────────────────────────────────────────────────────────

const TRANSACTION_TYPES = ["P2P", "P2M", "Bill Payment", "Recharge"];
const BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "PNB", "Yes Bank", "IndusInd"];
const DEVICES = ["Android", "iOS", "Web"];
const NETWORKS = ["3G", "4G", "5G", "WiFi"];
const STATES = [
  "Delhi", "Maharashtra", "Karnataka", "Tamil Nadu", "Telangana",
  "Gujarat", "Rajasthan", "West Bengal", "Uttar Pradesh", "Kerala",
  "Punjab", "Haryana", "Madhya Pradesh", "Bihar", "Odisha",
];
const DAY_PARTS = ["Morning", "Afternoon", "Evening", "Night"];
const AMOUNT_TIERS = ["Small (<500)", "Medium (500-5000)", "Large (5000-50000)"];
const AGE_LABELS = ["Young (18-25)", "Adult (26-55)", "Old (56+)"];

const TOOLTIP_STYLE: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: "12px",
  color: "#111827",
  fontSize: "12px",
  padding: "10px 14px",
  boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
};

// ── Component ────────────────────────────────────────────────────────────────

const Predictions = () => {
  const [activeTab, setActiveTab] = useState<"fraud" | "forecast">("fraud");

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <Link
              to="/dashboard"
              className="flex items-center gap-2 text-gray-400 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm">Dashboard</span>
            </Link>
            <div className="h-5 w-px bg-gray-200" />
            <h1 className="text-lg font-semibold text-gray-900">Predictive AI</h1>
          </div>

          {/* Tab Switcher */}
          <div className="flex items-center gap-1 p-1 rounded-xl bg-gray-100 border border-gray-200">
            <button
              onClick={() => setActiveTab("fraud")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${activeTab === "fraud"
                  ? "bg-white text-red-600 border border-red-100 shadow-sm"
                  : "text-gray-400 hover:text-gray-700"
                }`}
            >
              <Shield className="w-4 h-4" />
              Fraud Detector
            </button>
            <button
              onClick={() => setActiveTab("forecast")}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                ${activeTab === "forecast"
                  ? "bg-white text-cyan-600 border border-cyan-100 shadow-sm"
                  : "text-gray-400 hover:text-gray-700"
                }`}
            >
              <TrendingUp className="w-4 h-4" />
              Volume Forecast
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          {activeTab === "fraud" ? (
            <motion.div
              key="fraud"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
            >
              <FraudDetector />
            </motion.div>
          ) : (
            <motion.div
              key="forecast"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
            >
              <ForecastView />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
};

// ── Fraud Detector ───────────────────────────────────────────────────────────

const FraudDetector = () => {
  const [formData, setFormData] = useState({
    transaction_type: "P2M",
    amount_inr: 5000,
    sender_bank: "SBI",
    receiver_bank: "HDFC",
    device_type: "Android",
    network_type: "4G",
    sender_state: "Delhi",
    hour_of_day: 14,
    is_weekend: 0,
    day_part: "Afternoon",
    amount_tier: "Medium (500-5000)",
    sender_age_label: "Adult (26-55)",
  });
  const [result, setResult] = useState<FraudResult | null>(null);
  const [stats, setStats] = useState<FraudStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(true);

  useEffect(() => {
    getFraudStats()
      .then(setStats)
      .catch(console.error)
      .finally(() => setStatsLoading(false));
  }, []);

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      const res = await predictFraud(formData);
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const updateField = (field: string, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Left: Input Form */}
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">Transaction Analysis</h2>
          <p className="text-sm text-gray-500">
            Enter transaction details to predict fraud probability using XGBoost + SHAP.
          </p>
        </div>

        <div className="space-y-4 p-6 rounded-2xl border border-gray-200 bg-white shadow-sm">
          {/* Row 1: Type + Amount */}
          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label="Transaction Type"
              value={formData.transaction_type}
              options={TRANSACTION_TYPES}
              onChange={(v) => updateField("transaction_type", v)}
            />
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Amount (₹)</label>
              <input
                type="number"
                value={formData.amount_inr}
                onChange={(e) => updateField("amount_inr", parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-900 text-sm
                           focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 transition-all"
              />
            </div>
          </div>

          {/* Row 2: Banks */}
          <div className="grid grid-cols-2 gap-4">
            <SelectField label="Sender Bank" value={formData.sender_bank} options={BANKS} onChange={(v) => updateField("sender_bank", v)} />
            <SelectField label="Receiver Bank" value={formData.receiver_bank} options={BANKS} onChange={(v) => updateField("receiver_bank", v)} />
          </div>

          {/* Row 3: Device + Network */}
          <div className="grid grid-cols-2 gap-4">
            <SelectField label="Device" value={formData.device_type} options={DEVICES} onChange={(v) => updateField("device_type", v)} />
            <SelectField label="Network" value={formData.network_type} options={NETWORKS} onChange={(v) => updateField("network_type", v)} />
          </div>

          {/* Row 4: State + Hour */}
          <div className="grid grid-cols-2 gap-4">
            <SelectField label="Sender State" value={formData.sender_state} options={STATES} onChange={(v) => updateField("sender_state", v)} />
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1.5">Hour (0-23)</label>
              <input
                type="number"
                min={0}
                max={23}
                value={formData.hour_of_day}
                onChange={(e) => updateField("hour_of_day", parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-900 text-sm
                           focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 transition-all"
              />
            </div>
          </div>

          {/* Row 5: Day Part + Weekend */}
          <div className="grid grid-cols-2 gap-4">
            <SelectField label="Day Part" value={formData.day_part} options={DAY_PARTS} onChange={(v) => updateField("day_part", v)} />
            <SelectField label="Weekend?" value={String(formData.is_weekend)} options={["0", "1"]} onChange={(v) => updateField("is_weekend", parseInt(v))} />
          </div>

          {/* Row 6: Amount Tier + Age */}
          <div className="grid grid-cols-2 gap-4">
            <SelectField label="Amount Tier" value={formData.amount_tier} options={AMOUNT_TIERS} onChange={(v) => updateField("amount_tier", v)} />
            <SelectField label="Sender Age" value={formData.sender_age_label} options={AGE_LABELS} onChange={(v) => updateField("sender_age_label", v)} />
          </div>

          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="w-full mt-2 py-3 rounded-xl font-semibold text-sm transition-all duration-200
                       bg-gradient-to-r from-red-500 to-orange-500 text-white
                       hover:from-red-600 hover:to-orange-600 hover:shadow-lg hover:shadow-red-100
                       disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            {isLoading ? "Analyzing..." : "Analyze Transaction"}
          </button>
        </div>
      </div>

      {/* Right: Results */}
      <div className="space-y-6">
        {result ? (
          <FraudResultCard result={result} />
        ) : (
          <div className="flex flex-col items-center justify-center h-64 rounded-2xl border border-gray-200 bg-white shadow-sm">
            <Shield className="w-12 h-12 text-gray-300 mb-3" />
            <p className="text-gray-400 text-sm">Enter transaction details and click Analyze</p>
          </div>
        )}

        {/* Fraud Stats Dashboard */}
        {stats && !statsLoading && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-gray-900">Fraud Landscape</h3>
            {/* KPI Row */}
            <div className="grid grid-cols-3 gap-4">
              <KpiCard label="Overall Fraud Rate" value={`${stats.overall_fraud_rate}%`} color="red" />
              <KpiCard label="Total Flagged" value={stats.fraud_count.toLocaleString("en-IN")} color="orange" />
              <KpiCard label="Total Transactions" value={stats.total_transactions.toLocaleString("en-IN")} color="cyan" />
            </div>
            {/* Fraud by Bank */}
            <div className="p-4 rounded-2xl border border-gray-200 bg-white shadow-sm">
              <p className="text-xs font-medium text-gray-500 mb-3">Fraud Rate by Bank</p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={stats.by_bank} layout="vertical" margin={{ left: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                  <XAxis type="number" tick={{ fill: "#9ca3af", fontSize: 11 }} />
                  <YAxis dataKey="bank" type="category" tick={{ fill: "#374151", fontSize: 11 }} width={55} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} />
                  <Bar dataKey="fraud_rate" fill="url(#fraudGradient)" radius={[0, 4, 4, 0]} />
                  <defs>
                    <linearGradient id="fraudGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#ef4444" />
                      <stop offset="100%" stopColor="#f97316" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ── Fraud Result Card ────────────────────────────────────────────────────────

const FraudResultCard = ({ result }: { result: FraudResult }) => {
  const isHigh = result.risk_level === "High";
  const isMedium = result.risk_level === "Medium";
  const probability = (result.fraud_probability * 100).toFixed(1);

  const shapEntries = Object.entries(result.shap_contributions).slice(0, 8);
  const maxAbsShap = Math.max(...shapEntries.map(([, v]) => Math.abs(v)), 0.001);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="space-y-4"
    >
      {/* Risk Meter */}
      <div className={`p-6 rounded-2xl border shadow-sm ${
        isHigh ? "border-red-200 bg-red-50" :
        isMedium ? "border-orange-200 bg-orange-50" :
        "border-emerald-200 bg-emerald-50"
      }`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {isHigh ? <AlertTriangle className="w-6 h-6 text-red-500" /> :
             isMedium ? <AlertTriangle className="w-6 h-6 text-orange-500" /> :
             <CheckCircle className="w-6 h-6 text-emerald-500" />}
            <div>
              <p className="text-lg font-bold text-gray-900">{result.prediction}</p>
              <p className={`text-xs font-medium ${
                isHigh ? "text-red-500" : isMedium ? "text-orange-500" : "text-emerald-500"
              }`}>
                {result.risk_level} Risk
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-3xl font-black text-gray-900">{probability}%</p>
            <p className="text-xs text-gray-400">Fraud Probability</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 rounded-full bg-white/60 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${probability}%` }}
            transition={{ duration: 1, ease: "easeOut" }}
            className={`h-full rounded-full ${
              isHigh ? "bg-gradient-to-r from-red-500 to-red-400" :
              isMedium ? "bg-gradient-to-r from-orange-500 to-yellow-400" :
              "bg-gradient-to-r from-emerald-500 to-green-400"
            }`}
          />
        </div>
      </div>

      {/* SHAP Feature Importance */}
      {shapEntries.length > 0 && (
        <div className="p-5 rounded-2xl border border-gray-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-4 h-4 text-orange-500" />
            <p className="text-sm font-semibold text-gray-900">SHAP Feature Impact</p>
          </div>
          <div className="space-y-2.5">
            {shapEntries.map(([feature, value]) => {
              const isPositive = value > 0;
              const width = (Math.abs(value) / maxAbsShap) * 100;
              return (
                <div key={feature} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-32 truncate text-right">{feature}</span>
                  <div className="flex-1 flex items-center gap-2">
                    <div className="flex-1 h-4 rounded bg-gray-100 overflow-hidden relative">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${width}%` }}
                        transition={{ duration: 0.6, delay: 0.1 }}
                        className={`h-full rounded ${isPositive ? "bg-red-400/60" : "bg-emerald-400/60"}`}
                      />
                    </div>
                    <span className={`text-xs font-mono w-14 text-right ${isPositive ? "text-red-500" : "text-emerald-500"}`}>
                      {value > 0 ? "+" : ""}{value.toFixed(3)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-gray-400 mt-3">
            Red = increases fraud risk · Green = decreases fraud risk
          </p>
        </div>
      )}
    </motion.div>
  );
};

// ── Forecast View ────────────────────────────────────────────────────────────

const ForecastView = () => {
  const [data, setData] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);
  const [metric, setMetric] = useState<"count" | "amount">("count");

  useEffect(() => {
    getForecast()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 text-orange-400 animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center h-96 rounded-2xl border border-gray-200 bg-white shadow-sm">
        <TrendingUp className="w-12 h-12 text-gray-300 mb-3" />
        <p className="text-gray-400 text-sm">Forecast data not available</p>
        <p className="text-gray-300 text-xs mt-1">Run: python scripts/train_forecast_model.py</p>
      </div>
    );
  }

  const forecast = metric === "count" ? data.count_forecast : data.amount_forecast;
  const historicalKey = metric === "count" ? "txn_count" : "total_amount";

  // Combine last 30 historical days + forecast
  const historical = data.historical.slice(-30).map((h) => ({
    date: h.date,
    actual: h[historicalKey],
    type: "historical",
  }));
  const forecastPoints = forecast.map((f) => ({
    date: f.ds,
    predicted: Math.round(f.yhat),
    lower: Math.round(f.yhat_lower),
    upper: Math.round(f.yhat_upper),
    type: "forecast",
  }));

  const chartData = [...historical, ...forecastPoints];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-1">30-Day Volume Forecast</h2>
          <p className="text-sm text-gray-500">
            Prophet time-series model with weekly seasonality decomposition.
          </p>
        </div>
        <div className="flex items-center gap-1 p-1 rounded-lg bg-gray-100 border border-gray-200">
          <button
            onClick={() => setMetric("count")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              metric === "count" ? "bg-white text-orange-600 shadow-sm" : "text-gray-400"
            }`}
          >
            Txn Count
          </button>
          <button
            onClick={() => setMetric("amount")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              metric === "amount" ? "bg-white text-cyan-600 shadow-sm" : "text-gray-400"
            }`}
          >
            Txn Amount
          </button>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard label="Training Days" value={String(data.metadata.training_days)} color="violet" />
        <KpiCard label="Forecast Days" value={String(data.metadata.forecast_days)} color="cyan" />
        <KpiCard
          label="Avg Daily Count"
          value={data.metadata.avg_daily_count.toLocaleString("en-IN")}
          color="emerald"
        />
        <KpiCard
          label="Avg Daily Amount"
          value={`₹${data.metadata.avg_daily_amount.toLocaleString("en-IN")}`}
          color="amber"
        />
      </div>

      {/* Main Chart */}
      <div className="p-6 rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex items-center gap-4 mb-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-500" />
            <span className="text-xs text-gray-500">Historical</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-cyan-400" />
            <span className="text-xs text-gray-500">Predicted</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-3 rounded bg-cyan-100" />
            <span className="text-xs text-gray-500">Confidence Band</span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={380}>
          <ComposedChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#9ca3af", fontSize: 10 }}
              tickFormatter={(v) => {
                const d = new Date(v);
                return `${d.getDate()}/${d.getMonth() + 1}`;
              }}
              interval="preserveStartEnd"
            />
            <YAxis
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              tickFormatter={(v) =>
                metric === "amount" ? `₹${(v / 1000).toFixed(0)}k` : v.toLocaleString()
              }
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value: number, name: string) => {
                const formatted = metric === "amount"
                  ? `₹${value.toLocaleString("en-IN")}`
                  : value.toLocaleString("en-IN");
                return [formatted, name];
              }}
            />
            {/* Confidence band */}
            <Area dataKey="upper" stroke="none" fill="rgba(6, 182, 212, 0.1)" />
            <Area dataKey="lower" stroke="none" fill="rgba(255, 255, 255, 1)" />
            {/* Historical */}
            <Line
              dataKey="actual"
              stroke="#f97316"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
            />
            {/* Predicted */}
            <Line
              dataKey="predicted"
              stroke="#06b6d4"
              strokeWidth={2}
              strokeDasharray="6 3"
              dot={false}
              connectNulls={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// ── Shared UI Components ─────────────────────────────────────────────────────

const SelectField = ({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) => (
  <div>
    <label className="block text-xs font-medium text-gray-500 mb-1.5">{label}</label>
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-lg bg-gray-50 border border-gray-200 text-gray-900 text-sm
                   appearance-none cursor-pointer focus:outline-none focus:border-orange-300 focus:ring-2 focus:ring-orange-100 transition-all"
      >
        {options.map((opt) => (
          <option key={opt} value={opt} className="bg-white">
            {opt}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
    </div>
  </div>
);

const KpiCard = ({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) => {
  const colorMap: Record<string, string> = {
    red: "bg-red-50 border-red-100 text-red-600",
    orange: "bg-orange-50 border-orange-100 text-orange-600",
    cyan: "bg-cyan-50 border-cyan-100 text-cyan-600",
    violet: "bg-violet-50 border-violet-100 text-violet-600",
    emerald: "bg-emerald-50 border-emerald-100 text-emerald-600",
    amber: "bg-amber-50 border-amber-100 text-amber-600",
  };
  const classes = colorMap[color] || colorMap.violet;

  return (
    <div className={`p-4 rounded-xl border ${classes}`}>
      <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-xl font-bold">{value}</p>
    </div>
  );
};

export default Predictions;
