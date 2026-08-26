import { motion } from "framer-motion";
import { MessageSquareText, Cpu, BarChart3 } from "lucide-react";

const steps = [
  {
    icon: MessageSquareText,
    title: "Ask",
    subtitle: "Natural Language",
    description:
      "Type your question in plain English — no SQL knowledge needed.",
  },
  {
    icon: Cpu,
    title: "Process",
    subtitle: "Vanna AI + Groq",
    description:
      "AI converts your query to SQL and executes it against your data.",
  },
  {
    icon: BarChart3,
    title: "Visualize",
    subtitle: "Auto-Selected Charts",
    description:
      "AI picks the best visualization and generates an executive summary.",
  },
];

const HowItWorks = () => {
  return (
    <div className="max-w-5xl mx-auto">
      <div className="grid md:grid-cols-3 gap-0 items-start relative">
        {steps.map((step, i) => (
          <div
            key={step.title}
            className="flex flex-col items-center text-center relative z-10"
          >
            {/* Step Icon */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: i * 0.15 }}
              className="relative"
            >
              <div className="w-20 h-20 rounded-2xl bg-white border-2 border-gray-100 shadow-lg flex items-center justify-center mb-5 hover:border-orange-200 transition-colors">
                <step.icon className="w-8 h-8 text-gray-900" />
              </div>
              <span className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-orange-500 flex items-center justify-center text-xs font-bold text-white shadow-md">
                {i + 1}
              </span>
            </motion.div>

            {/* Connecting Line */}
            {i < steps.length - 1 && (
              <motion.div
                className="hidden md:block absolute top-10 left-[calc(50%+40px)] w-[calc(100%-80px)] h-[2px]"
                style={{ background: "hsl(var(--border))" }}
                initial={{ scaleX: 0 }}
                whileInView={{ scaleX: 1 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.6, delay: 0.3 + i * 0.15 }}
              >
                <motion.div
                  className="h-full w-full origin-left"
                  style={{
                    background:
                      "linear-gradient(90deg, #f97316, #ec4899, #06b6d4)",
                  }}
                  initial={{ scaleX: 0 }}
                  whileInView={{ scaleX: 1 }}
                  viewport={{ once: true, margin: "-50px" }}
                  transition={{ duration: 0.8, delay: 0.5 + i * 0.2 }}
                />
              </motion.div>
            )}

            {/* Text */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ duration: 0.4, delay: 0.1 + i * 0.15 }}
            >
              <h3 className="text-xl font-bold text-gray-900">{step.title}</h3>
              <span className="text-xs font-mono text-orange-500 tracking-wider uppercase">
                {step.subtitle}
              </span>
              <p className="text-sm text-gray-500 mt-3 max-w-[220px] mx-auto leading-relaxed">
                {step.description}
              </p>
            </motion.div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HowItWorks;
