import { motion } from "framer-motion";
import { ArrowRight, Mic, Shield, Workflow, TrendingUp, ScanSearch } from "lucide-react";
import { Link } from "react-router-dom";
import heroBg from "@/assets/hero-bg.jpg";
import SectionWrapper from "@/components/landing/SectionWrapper";
import LiveDemo from "@/components/landing/LiveDemo";
import HowItWorks from "@/components/landing/HowItWorks";
import UseCases from "@/components/landing/UseCases";
import FAQ from "@/components/landing/FAQ";
import Footer from "@/components/landing/Footer";

const features = [
  {
    icon: Mic,
    title: "Speech-to-Text",
    description: "Voice-powered queries via Whisper. Just speak your question naturally.",
  },
  {
    icon: Shield,
    title: "Fraud Detection",
    description: "XGBoost classifier with SHAP explainability for real-time transaction risk scoring.",
  },
  {
    icon: Workflow,
    title: "Dual-AI Pipeline",
    description: "Text-to-SQL + Smart Synthesis for precise analytics.",
  },
  {
    icon: TrendingUp,
    title: "Volume Forecasting",
    description: "Prophet time-series models predict 30-day transaction trends with confidence bands.",
  },
  {
    icon: ScanSearch,
    title: "OCR Intelligence",
    description: "Upload charts or screenshots — AI vision extracts and queries data instantly.",
  },
];

const Index = () => {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Hero Background */}
      <div className="absolute inset-0 z-0">
        <img
          src={heroBg}
          alt=""
          className="w-full h-full object-cover opacity-40"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-background/30 via-background/50 to-background" />
      </div>

      {/* Navbar */}
      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg glow-button flex items-center justify-center text-sm font-bold">
            IX
          </div>
          <span className="text-lg font-bold text-foreground">InsightX</span>
        </div>
        <Link
          to="/dashboard"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Dashboard →
        </Link>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 flex flex-col items-center justify-center text-center px-6 pt-20 pb-32 md:pt-32 md:pb-40">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl"
        >
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold leading-tight mb-6">
            Ask Questions.{" "}
            <span className="gradient-text">Get Instant Financial Insights.</span>
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-10">
            AI-powered analytics for UPI transaction data using Local LLMs.
            Transform natural language into actionable insights.
          </p>
          <Link to="/dashboard">
            <button className="glow-button px-8 py-4 rounded-xl text-primary-foreground font-semibold text-lg inline-flex items-center gap-3 group">
              Launch Dashboard
              <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
            </button>
          </Link>
        </motion.div>
      </section>

      {/* Features Grid */}
      <SectionWrapper>
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="glass-card-hover p-6"
            >
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                <feature.icon className="w-6 h-6 text-accent-foreground" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </SectionWrapper>

      {/* Live Demo */}
      <SectionWrapper
        title="See it in action."
        subtitle="Click a prompt to watch InsightX transform natural language into visual insights — instantly."
      >
        <LiveDemo />
      </SectionWrapper>

      {/* How It Works */}
      <SectionWrapper
        title="From natural language to deep insights."
        subtitle="Three simple steps. Zero SQL knowledge required."
      >
        <HowItWorks />
      </SectionWrapper>

      {/* Use Cases */}
      <SectionWrapper
        title="Built for everyone."
        subtitle="Whether you're tracking personal expenses or managing business payments."
      >
        <UseCases />
      </SectionWrapper>

      {/* FAQ */}
      <SectionWrapper
        title="Frequently asked questions."
        subtitle="Everything you need to know about InsightX."
      >
        <FAQ />
      </SectionWrapper>

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default Index;
