import { motion } from "framer-motion";
import {
  ArrowRight,
  Shield,
  Workflow,
  TrendingUp,
  BarChart3,
  FileText,
  Sparkles,
  Github,
} from "lucide-react";
import { Link } from "react-router-dom";
import SectionWrapper from "@/components/landing/SectionWrapper";
import LiveDemo from "@/components/landing/LiveDemo";
import HowItWorks from "@/components/landing/HowItWorks";
import PipelineDeep from "@/components/landing/PipelineDeep";
import StatsCounter from "@/components/landing/StatsCounter";
import TechStack from "@/components/landing/TechStack";
import UseCases from "@/components/landing/UseCases";
import FAQ from "@/components/landing/FAQ";
import Footer from "@/components/landing/Footer";

const features = [
  {
    icon: Sparkles,
    title: "Natural Language Queries",
    description:
      "Ask questions in plain English — Vanna AI converts them to SQL automatically. No database knowledge required.",
  },
  {
    icon: Shield,
    title: "Fraud Detection",
    description:
      "XGBoost classifier with SHAP explainability scores every transaction for real-time fraud risk assessment.",
  },
  {
    icon: Workflow,
    title: "Dual-AI Pipeline",
    description:
      "Vanna AI for Text-to-SQL + Groq LLaMA 3.3 70B for executive summaries, chart selection, and follow-ups.",
  },
  {
    icon: TrendingUp,
    title: "30-Day Forecasting",
    description:
      "Prophet time-series models predict transaction volumes and amounts with weekly seasonality and confidence bands.",
  },
  {
    icon: BarChart3,
    title: "Smart Visualizations",
    description:
      "AI auto-selects the best chart type — Bar, Line, Pie, KPI, or Table — rendered beautifully via Recharts.",
  },
  {
    icon: FileText,
    title: "1-Click Board Reports",
    description:
      "Export your entire analytics session as a clean, professional executive PDF document with a single click.",
  },
];

const Index = () => {
  return (
    <div className="min-h-screen bg-white relative overflow-hidden">
      {/* ── Navbar ───────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 md:px-12 py-4 bg-white/80 backdrop-blur-xl border-b border-gray-100">
        <div className="flex items-center gap-8">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg glow-button flex items-center justify-center text-sm font-bold">
              IX
            </div>
            <span className="text-lg font-bold text-gray-900">InsightX</span>
          </div>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-6">
            <a
              href="#features"
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              How It Works
            </a>
            <Link
              to="/predictions"
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors font-medium"
            >
              Predictions
            </Link>
            <a
              href="#tech-stack"
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              Tech Stack
            </a>
            <a
              href="#faq"
              className="text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              FAQ
            </a>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="https://github.com/atulbhaskar1034/Insightx-"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg text-gray-400 hover:text-gray-900 transition-colors"
          >
            <Github className="w-5 h-5" />
          </a>
          <Link
            to="/dashboard"
            className="landing-btn-primary text-xs px-5 py-2.5"
          >
            Launch Dashboard
          </Link>
        </div>
      </nav>

      {/* ── Gradient Decoration Bars ─────────────────────────────────── */}
      <div className="absolute top-[60px] left-0 right-0 h-[3px] landing-gradient-bar opacity-60" />

      {/* ── Hero Section ─────────────────────────────────────────────── */}
      <section className="relative z-10 flex flex-col items-center justify-center text-center px-6 pt-24 pb-16 md:pt-36 md:pb-24">
        {/* Decorative gradient blobs */}
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-orange-100 rounded-full blur-3xl opacity-30 pointer-events-none" />
        <div className="absolute top-40 right-1/4 w-80 h-80 bg-cyan-100 rounded-full blur-3xl opacity-30 pointer-events-none" />
        <div className="absolute top-32 left-1/2 w-72 h-72 bg-pink-100 rounded-full blur-3xl opacity-20 pointer-events-none" />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-4xl relative"
        >
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold leading-[1.08] mb-6 text-gray-900 tracking-tight">
            Transform Natural Language
            <br />
            <span className="gradient-text">
              Into Instant Financial Insights
            </span>
          </h1>
          <p className="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-10">
            AI-powered analytics for UPI transaction data. Ask questions in
            plain English, get dynamic visualizations, detect fraud, and
            forecast trends — all running locally on your machine.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link to="/dashboard">
              <button className="landing-btn-primary group">
                Try InsightX
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </button>
            </Link>
            <a
              href="https://github.com/atulbhaskar1034/Insightx-"
              target="_blank"
              rel="noopener noreferrer"
            >
              <button className="landing-btn-outline">
                <Github className="w-4 h-4" />
                View on GitHub
              </button>
            </a>
          </div>
        </motion.div>
      </section>

      {/* ── Stats Section ────────────────────────────────────────────── */}
      <SectionWrapper className="pb-10 md:pb-16">
        <StatsCounter />
      </SectionWrapper>

      {/* ── Gradient Bar Divider ──────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6">
        <div className="h-[2px] landing-gradient-bar rounded-full opacity-30" />
      </div>

      {/* ── Features Grid ────────────────────────────────────────────── */}
      <SectionWrapper
        id="features"
        label="Features"
        title="Unrivaled performance across UPI analytics"
        subtitle="Every tool you need to understand, predict, and report on your transaction data."
      >
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="bg-white p-6 rounded-xl border border-gray-200 hover:border-orange-200 hover:shadow-lg hover:shadow-orange-50 transition-all duration-300 hover:-translate-y-0.5"
            >
              <div className="w-12 h-12 rounded-xl bg-orange-50 flex items-center justify-center mb-4">
                <feature.icon className="w-6 h-6 text-orange-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </SectionWrapper>

      {/* ── Predictive AI Deep Showcase (PROMINENT SECTION) ──────────── */}
      <SectionWrapper
        id="predictions-showcase"
        label="Predictive AI Suite"
        title="Unlock Future Trends & Secure Transactions"
        subtitle="InsightX brings machine learning directly to your UPI data. Detect threats using XGBoost and forecast volumes with Facebook Prophet."
        className="bg-gray-50/50"
      >
        <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-8 items-stretch">
          {/* Card 1: Fraud Detection */}
          <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-sm flex flex-col justify-between hover:border-red-200 hover:shadow-md transition-all duration-300">
            <div>
              <div className="w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center mb-6">
                <Shield className="w-6 h-6 text-red-500" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">XGBoost Fraud Detection</h3>
              <p className="text-sm text-gray-500 leading-relaxed mb-6">
                Evaluate single-transaction safety metrics instantly. Our tree-based XGBoost model scores risk using parameters like transaction amount, timestamp, bank networks, and client hardware. Coupled with <strong>SHAP explanation metrics</strong> to let you drill down into exactly what variables triggered the warning.
              </p>
              <ul className="space-y-2 text-xs text-gray-500 mb-8">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> Real-time risk probability output
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500" /> SHAP value feature-contribution breakdowns
                </li>
              </ul>
            </div>
            <Link to="/predictions" className="landing-btn-outline w-full justify-center text-center py-3">
              Explore Fraud Detector →
            </Link>
          </div>

          {/* Card 2: Prophet Forecasting */}
          <div className="bg-white rounded-2xl p-8 border border-gray-200 shadow-sm flex flex-col justify-between hover:border-cyan-200 hover:shadow-md transition-all duration-300">
            <div>
              <div className="w-12 h-12 rounded-xl bg-cyan-50 flex items-center justify-center mb-6">
                <TrendingUp className="w-6 h-6 text-cyan-500" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Prophet Volume Forecasting</h3>
              <p className="text-sm text-gray-500 leading-relaxed mb-6">
                Run time-series predictive modeling on your transaction counts and values. Leveraging Facebook Prophet, InsightX forecasts a 30-day window, resolving weekly cycles, seasonal intervals, and generating confidence ranges so you can manage resources effectively.
              </p>
              <ul className="space-y-2 text-xs text-gray-500 mb-8">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" /> Captures complex seasonality trends
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" /> Lower and upper confidence band charts
                </li>
              </ul>
            </div>
            <Link to="/predictions" className="landing-btn-primary w-full justify-center text-center py-3">
              Launch Forecasting Suite →
            </Link>
          </div>
        </div>
      </SectionWrapper>

      {/* ── CTA Banner ───────────────────────────────────────────────── */}
      <div className="max-w-5xl mx-auto px-6 mt-12">
        <div className="landing-card-gradient-border">
          <div className="bg-white rounded-2xl p-8 md:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
                Get started with InsightX for free
              </h3>
              <p className="text-sm text-gray-500">
                Open-source, privacy-first, runs entirely on your machine.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row items-center gap-4 text-sm text-gray-600">
              <ul className="space-y-1.5">
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-orange-500" />
                  250,000 transactions ready to query
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-pink-500" />
                  Real-time fraud detection with XGBoost
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-500" />
                  30-day Prophet forecasting
                </li>
                <li className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-500" />
                  1-click PDF board reports
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* ── Live Demo ────────────────────────────────────────────────── */}
      <SectionWrapper
        label="Interactive Demo"
        title="See it in action"
        subtitle="Click a prompt to watch InsightX transform natural language into visual insights — instantly."
      >
        <LiveDemo />
      </SectionWrapper>

      {/* ── How It Works (simple) ────────────────────────────────────── */}
      <SectionWrapper
        id="how-it-works"
        label="How It Works"
        title="From natural language to deep insights"
        subtitle="Three simple steps. Zero SQL knowledge required."
      >
        <HowItWorks />
      </SectionWrapper>

      {/* ── Deep Pipeline ────────────────────────────────────────────── */}
      <SectionWrapper
        label="Under The Hood"
        title="We process your most complex queries"
        subtitle="A 5-stage AI pipeline from question to actionable insight."
        className="bg-gray-50"
      >
        <PipelineDeep />
      </SectionWrapper>

      {/* ── Use Cases ────────────────────────────────────────────────── */}
      <SectionWrapper
        label="Use Cases"
        title="Built for everyone"
        subtitle="Whether you're tracking personal expenses or managing business payments."
      >
        <UseCases />
      </SectionWrapper>

      {/* ── Tech Stack ───────────────────────────────────────────────── */}
      <SectionWrapper
        id="tech-stack"
        label="Tech Stack"
        title="Powered by best-in-class AI"
        subtitle="16 technologies working together to deliver instant insights."
        className="bg-gray-50"
      >
        <TechStack />
      </SectionWrapper>

      {/* ── FAQ ──────────────────────────────────────────────────────── */}
      <SectionWrapper
        id="faq"
        label="FAQ"
        title="Frequently asked questions"
        subtitle="Everything you need to know about InsightX."
      >
        <FAQ />
      </SectionWrapper>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <Footer />
    </div>
  );
};

export default Index;
