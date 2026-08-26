import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

const faqs = [
  {
    q: "Does my data leave my computer?",
    a: "No. InsightX runs entirely locally on your machine. Your transaction data, queries, and results never leave your device. Privacy is built into the architecture, not bolted on.",
  },
  {
    q: "Do I need to know SQL?",
    a: 'Not at all. Simply type your question in plain English — like "What did I spend on food last month?" — and InsightX converts it to SQL automatically using Vanna AI.',
  },
  {
    q: "Which AI models are used?",
    a: "InsightX uses a dual-AI pipeline: Vanna AI for Text-to-SQL conversion with ChromaDB vector embeddings, and Groq-powered LLaMA 3.3 70B for natural language synthesis, chart type selection, and follow-up generation.",
  },
  {
    q: "How does fraud detection work?",
    a: "InsightX uses an XGBoost classifier trained on transaction features (amount, time, network, device, bank) to predict fraud probability. SHAP values explain exactly which features drove the prediction — making it fully transparent and interpretable.",
  },
  {
    q: "What is volume forecasting?",
    a: "Using Facebook Prophet time-series models, InsightX predicts transaction volumes and amounts for the next 30 days. The model captures weekly seasonality patterns and provides confidence bands around each prediction.",
  },
  {
    q: "What databases are supported?",
    a: "Currently, InsightX is optimized for SQLite databases containing UPI transaction data. Support for PostgreSQL and CSV imports is on the roadmap.",
  },
  {
    q: "Is InsightX free to use?",
    a: "Yes, InsightX is open-source and free under the MIT License. Since everything runs locally, there are no API costs or subscription fees — you only need a free Groq API key.",
  },
];

const FAQ = () => {
  return (
    <div className="max-w-2xl mx-auto">
      <Accordion type="single" collapsible className="space-y-2">
        {faqs.map((faq, i) => (
          <AccordionItem
            key={i}
            value={`item-${i}`}
            className="bg-white px-6 border border-gray-200 rounded-xl hover:border-orange-200 transition-colors data-[state=open]:border-orange-300 data-[state=open]:shadow-md data-[state=open]:shadow-orange-50"
          >
            <AccordionTrigger className="text-gray-900 font-semibold text-left hover:no-underline py-5">
              {faq.q}
            </AccordionTrigger>
            <AccordionContent className="text-gray-500 text-sm leading-relaxed pb-5">
              {faq.a}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
};

export default FAQ;
