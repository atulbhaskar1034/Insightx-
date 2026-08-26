import { motion } from "framer-motion";
import { Wallet, Store, Database } from "lucide-react";

const cases = [
  {
    icon: Wallet,
    title: "Personal Finance",
    description:
      "Track daily UPI spends, categorize expenses, and spot trends in your financial habits — all by asking questions in plain English.",
    span: "md:col-span-2",
  },
  {
    icon: Store,
    title: "Small Businesses",
    description:
      "Monitor customer payments, track revenue patterns, and manage cash flow effortlessly with AI-generated charts.",
    span: "md:col-span-1",
  },
  {
    icon: Database,
    title: "Data Enthusiasts",
    description:
      "Query SQLite databases directly with natural language. Export professional charts and tables for reports. Detect fraud patterns with XGBoost.",
    span: "md:col-span-3",
  },
];

const UseCases = () => {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="grid md:grid-cols-3 gap-5">
        {cases.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
            className={`landing-card-gradient-border p-7 bg-white transition-all duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-orange-100/50 cursor-default ${item.span}`}
          >
            <div className="w-12 h-12 rounded-xl bg-orange-50 flex items-center justify-center mb-4">
              <item.icon className="w-6 h-6 text-orange-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {item.title}
            </h3>
            <p className="text-sm text-gray-500 leading-relaxed">
              {item.description}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default UseCases;
