import { motion } from "framer-motion";
import { MessageSquareText, Database, Cpu, BarChart3, FileText } from "lucide-react";

const steps = [
  {
    icon: MessageSquareText,
    num: "01",
    title: "Ask in Plain English",
    tech: "Intent Classification → Groq LLM",
    description:
      "Type your question naturally — like \"What's my total spend on food?\" — the system first runs intent classification via Groq to ensure it's a valid data query, preventing hallucinated SQL for greetings or off-topic input.",
    detail: "Supports text input with smart guardrails.",
  },
  {
    icon: Database,
    num: "02",
    title: "AI Converts to SQL",
    tech: "Vanna AI + ChromaDB Vector Embeddings",
    description:
      "Vanna AI searches its ChromaDB vector store for semantically similar trained queries and schema definitions, then generates precise SQL tuned to your exact database structure — no generic guessing.",
    detail: "Trained on your schema with example queries for 95%+ accuracy.",
  },
  {
    icon: Cpu,
    num: "03",
    title: "Execute & Process",
    tech: "SQLite + Pandas DataFrame",
    description:
      "The generated SQL runs against a local 250,000-row SQLite database of UPI transactions. Results are processed into structured DataFrames, handling nulls, type coercion, and currency formatting automatically.",
    detail: "All data stays on your machine — zero cloud exposure.",
  },
  {
    icon: BarChart3,
    num: "04",
    title: "Smart Visualization",
    tech: "Groq LLaMA 3.3 70B → Recharts",
    description:
      "The LLM analyzes the result shape — single value? time series? categories? — and auto-selects the best visualization: KPI card, Line chart, Bar chart, Pie chart, or Table. Rendered beautifully via Recharts.",
    detail: "No manual chart selection — the AI decides what works best.",
  },
  {
    icon: FileText,
    num: "05",
    title: "Summary & Follow-ups",
    tech: "LLaMA 3.3 70B + Schema Grounding",
    description:
      "An executive-quality natural language summary is generated alongside schema-grounded follow-up questions — meaning every suggested question maps to real columns in your database, preventing hallucinated queries.",
    detail: "Export your entire session as a polished PDF board report.",
  },
];

const PipelineDeep = () => {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="space-y-0">
        {steps.map((step, i) => (
          <motion.div
            key={step.num}
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
            className="relative flex gap-6 pb-12 last:pb-0"
          >
            {/* Vertical connector line */}
            {i < steps.length - 1 && (
              <div
                className="absolute left-6 top-16 w-[2px] h-[calc(100%-40px)]"
                style={{
                  background:
                    "linear-gradient(180deg, #f97316 0%, #ec4899 50%, #06b6d4 100%)",
                  opacity: 0.2,
                }}
              />
            )}

            {/* Step number circle */}
            <div className="relative shrink-0">
              <div className="w-12 h-12 rounded-2xl bg-gray-900 flex items-center justify-center">
                <step.icon className="w-5 h-5 text-white" />
              </div>
              <span className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-orange-500 text-white text-[9px] font-bold flex items-center justify-center">
                {step.num}
              </span>
            </div>

            {/* Content */}
            <div className="flex-1 pt-0.5">
              <h3 className="text-lg font-bold text-gray-900 mb-1">
                {step.title}
              </h3>
              <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono font-medium text-orange-600 bg-orange-50 border border-orange-100 mb-3">
                {step.tech}
              </span>
              <p className="text-sm text-gray-600 leading-relaxed mb-2">
                {step.description}
              </p>
              <p className="text-xs text-gray-400 italic">{step.detail}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default PipelineDeep;
