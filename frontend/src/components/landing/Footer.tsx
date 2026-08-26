import { Link } from "react-router-dom";
import { Shield } from "lucide-react";

const Footer = () => {
  return (
    <footer className="border-t border-gray-200 bg-gray-50">
      {/* Gradient accent bar */}
      <div className="h-1 landing-gradient-bar" />

      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg glow-button flex items-center justify-center text-[9px] font-bold">
                IX
              </div>
              <span className="text-base font-bold text-gray-900">
                InsightX
              </span>
            </div>
            <p className="text-sm text-gray-500 leading-relaxed">
              AI-powered UPI analytics that runs entirely on your machine.
            </p>
            <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-gray-200 bg-white text-xs text-gray-500">
              <Shield className="w-3 h-3 text-orange-500" />
              Built for local privacy
            </div>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">
              Product
            </h4>
            <ul className="space-y-2.5 text-sm text-gray-500">
              <li>
                <Link
                  to="/dashboard"
                  className="hover:text-gray-900 transition-colors"
                >
                  Dashboard
                </Link>
              </li>
              <li>
                <Link
                  to="/predictions"
                  className="hover:text-gray-900 transition-colors"
                >
                  Predictions
                </Link>
              </li>
              <li>
                <a href="#features" className="hover:text-gray-900 transition-colors">
                  Features
                </a>
              </li>
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">
              Resources
            </h4>
            <ul className="space-y-2.5 text-sm text-gray-500">
              <li>
                <a
                  href="https://github.com/atulbhaskar1034/Insightx-"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-gray-900 transition-colors"
                >
                  GitHub
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-gray-900 transition-colors">
                  Documentation
                </a>
              </li>
              <li>
                <a href="#tech-stack" className="hover:text-gray-900 transition-colors">
                  Tech Stack
                </a>
              </li>
            </ul>
          </div>

          {/* Tech */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-4">
              Powered By
            </h4>
            <ul className="space-y-2.5 text-sm text-gray-500">
              <li className="hover:text-gray-900 transition-colors">
                Vanna AI + ChromaDB
              </li>
              <li className="hover:text-gray-900 transition-colors">
                Groq LLaMA 3.3 70B
              </li>
              <li className="hover:text-gray-900 transition-colors">
                XGBoost + Prophet
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-gray-200 flex flex-col md:flex-row items-center justify-between gap-3">
          <p className="text-xs text-gray-400">
            © 2026 InsightX. Open-source & privacy-first. MIT License.
          </p>
          <p className="text-xs text-gray-400">
            Made with local LLMs 🤖
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
