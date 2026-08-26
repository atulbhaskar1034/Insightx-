import { motion } from "framer-motion";

const techs = [
  { name: "FastAPI", category: "Backend" },
  { name: "Vanna AI", category: "Text-to-SQL" },
  { name: "ChromaDB", category: "Vector Store" },
  { name: "Groq", category: "LLM Inference" },
  { name: "XGBoost", category: "Fraud Detection" },
  { name: "SHAP", category: "Explainability" },
  { name: "Prophet", category: "Forecasting" },
  { name: "SQLite", category: "Database" },
  { name: "React 18", category: "Frontend" },
  { name: "TypeScript", category: "Type Safety" },
  { name: "Vite 5", category: "Build Tool" },
  { name: "Recharts", category: "Visualization" },
  { name: "Framer Motion", category: "Animations" },
  { name: "html2pdf.js", category: "PDF Export" },
  { name: "Pandas", category: "Data Processing" },
  { name: "shadcn/ui", category: "UI Library" },
];

const TechStack = () => {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-4 lg:grid-cols-8 gap-4">
        {techs.map((tech, i) => (
          <motion.div
            key={tech.name}
            initial={{ opacity: 0, y: 15 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.3, delay: i * 0.03 }}
            className="flex flex-col items-center text-center p-4 rounded-xl bg-gray-50 border border-gray-100 hover:border-orange-200 hover:bg-orange-50/30 transition-all duration-300 group"
          >
            <span className="text-sm font-bold text-gray-900 group-hover:text-orange-600 transition-colors">
              {tech.name}
            </span>
            <span className="text-[10px] text-gray-400 mt-1 uppercase tracking-wider">
              {tech.category}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default TechStack;
