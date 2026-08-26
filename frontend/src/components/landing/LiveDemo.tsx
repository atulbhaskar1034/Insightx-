import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const prompts = [
  {
    label: "📊 Show my monthly food spend",
    chartType: "bar" as const,
    data: [
      { name: "Jan", value: 4200 },
      { name: "Feb", value: 3800 },
      { name: "Mar", value: 5100 },
      { name: "Apr", value: 4600 },
      { name: "May", value: 3900 },
      { name: "Jun", value: 4400 },
    ],
    response: "Here's your monthly food spend breakdown for 2024.",
  },
  {
    label: "📈 Top 5 transactions this week",
    chartType: "line" as const,
    data: [
      { name: "Mon", value: 1200 },
      { name: "Tue", value: 3400 },
      { name: "Wed", value: 890 },
      { name: "Thu", value: 2100 },
      { name: "Fri", value: 4500 },
    ],
    response: "Your top 5 transactions for this week, ranked by value.",
  },
  {
    label: "💰 Total spent this month",
    chartType: "bar" as const,
    data: [
      { name: "Food", value: 8200 },
      { name: "Travel", value: 3400 },
      { name: "Shopping", value: 5600 },
      { name: "Bills", value: 4100 },
      { name: "Other", value: 1800 },
    ],
    response: "Your total spend this month is ₹23,100 across all categories.",
  },
];

const TOOLTIP_STYLE: React.CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: "10px",
  color: "#111827",
  fontSize: "13px",
  padding: "10px 14px",
  boxShadow: "0 4px 20px rgba(0,0,0,0.08)",
};

const LiveDemo = () => {
  const [activePrompt, setActivePrompt] = useState<number | null>(null);
  const [phase, setPhase] = useState<"idle" | "typing" | "loading" | "result">(
    "idle"
  );

  const handleClick = (index: number) => {
    if (phase !== "idle" && phase !== "result") return;
    setActivePrompt(index);
    setPhase("typing");
    setTimeout(() => setPhase("loading"), 800);
    setTimeout(() => setPhase("result"), 2000);
  };

  const prompt = activePrompt !== null ? prompts[activePrompt] : null;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Mock Chat Window */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-xl overflow-hidden min-h-[340px] flex flex-col">
        {/* Chat Header */}
        <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-100 bg-gray-50/50">
          <div className="w-6 h-6 rounded-md glow-button flex items-center justify-center text-[8px] font-bold">
            IX
          </div>
          <span className="text-sm font-medium text-gray-900">
            InsightX Agent
          </span>
          <span className="ml-auto w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        </div>

        {/* Chat Body */}
        <div className="flex-1 p-5 space-y-4 bg-gray-50/30">
          <AnimatePresence mode="wait">
            {phase === "idle" && (
              <motion.p
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.5 }}
                className="text-sm text-gray-400 text-center pt-16"
              >
                Click a prompt below to see InsightX in action ↓
              </motion.p>
            )}

            {(phase === "typing" ||
              phase === "loading" ||
              phase === "result") &&
              prompt && (
                <motion.div
                  key="user"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex justify-end"
                >
                  <div className="px-4 py-2.5 max-w-[75%] bg-gray-900 text-white rounded-2xl rounded-br-md">
                    <p className="text-sm">
                      {prompt.label.replace(/^.{2} /, "")}
                    </p>
                  </div>
                </motion.div>
              )}

            {phase === "loading" && (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex gap-3"
              >
                <div className="w-6 h-6 rounded-md glow-button flex items-center justify-center text-[8px] font-bold shrink-0">
                  IX
                </div>
                <div className="space-y-2 flex-1 max-w-[75%]">
                  <div className="skeleton-shimmer h-4 rounded-md w-3/4" />
                  <div className="skeleton-shimmer h-4 rounded-md w-1/2" />
                  <div className="skeleton-shimmer h-32 rounded-lg w-full mt-2" />
                </div>
              </motion.div>
            )}

            {phase === "result" && prompt && (
              <motion.div
                key="result"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="flex gap-3"
              >
                <div className="w-6 h-6 rounded-md glow-button flex items-center justify-center text-[8px] font-bold shrink-0">
                  IX
                </div>
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md p-4 flex-1 max-w-[80%] space-y-3 shadow-sm">
                  <p className="text-sm text-gray-700">{prompt.response}</p>
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.2, duration: 0.4 }}
                  >
                    <div className="h-44">
                      <ResponsiveContainer width="100%" height="100%">
                        {prompt.chartType === "line" ? (
                          <LineChart data={prompt.data}>
                            <CartesianGrid
                              strokeDasharray="3 3"
                              stroke="#f3f4f6"
                            />
                            <XAxis
                              dataKey="name"
                              tick={{ fill: "#9ca3af", fontSize: 11 }}
                            />
                            <YAxis
                              tick={{ fill: "#9ca3af", fontSize: 11 }}
                            />
                            <Tooltip contentStyle={TOOLTIP_STYLE} />
                            <Line
                              type="monotone"
                              dataKey="value"
                              stroke="#f97316"
                              strokeWidth={2}
                              dot={{ fill: "#f97316", r: 3 }}
                            />
                          </LineChart>
                        ) : (
                          <BarChart data={prompt.data}>
                            <CartesianGrid
                              strokeDasharray="3 3"
                              stroke="#f3f4f6"
                            />
                            <XAxis
                              dataKey="name"
                              tick={{ fill: "#9ca3af", fontSize: 11 }}
                            />
                            <YAxis
                              tick={{ fill: "#9ca3af", fontSize: 11 }}
                            />
                            <Tooltip contentStyle={TOOLTIP_STYLE} />
                            <Bar
                              dataKey="value"
                              fill="#f97316"
                              radius={[4, 4, 0, 0]}
                            />
                          </BarChart>
                        )}
                      </ResponsiveContainer>
                    </div>
                  </motion.div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Prompt Pills */}
      <div className="flex flex-wrap justify-center gap-3 mt-6">
        {prompts.map((p, i) => (
          <button
            key={i}
            onClick={() => handleClick(i)}
            className={`px-5 py-2.5 rounded-full text-sm font-medium border transition-all duration-300 cursor-pointer ${
              activePrompt === i
                ? "border-orange-300 bg-orange-50 text-orange-700 shadow-md shadow-orange-100"
                : "border-gray-200 bg-white text-gray-500 hover:border-orange-200 hover:bg-orange-50/50 hover:text-gray-700"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default LiveDemo;
