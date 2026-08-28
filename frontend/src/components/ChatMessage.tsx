import { motion } from "framer-motion";
import { Download } from "lucide-react";
import DataVisualizer from "@/components/DataVisualizer";
import { ErrorBoundary } from "./ErrorBoundary";

export interface Message {
  id: string;
  role: "user" | "ai";
  content: string;
  data?: {
    title: string;
    summary?: string;
    // Raw data from backend
    rawData?: Record<string, unknown>[];
    // LLM-chosen visualization
    chartType?: string;
    xAxis?: string | null;
    yAxis?: string | null;
    // Text-only content
    textContent?: string;
    // SQL (collapsible detail)
    sql?: string;
    // Follow-up questions
    followUpQuestions?: string[];
  };
  onFollowUp?: (question: string) => void;
}

interface ChatMessageProps {
  message: Message;
}

const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.role === "user";

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(message.data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `insightx-export-${message.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-3 print-avoid-break break-inside-avoid ${isUser ? "justify-end" : "items-start"}`}
    >
      {!isUser && (
        <div className="w-8 h-8 rounded-lg glow-button flex items-center justify-center text-[10px] font-bold shrink-0 mt-1">
          IX
        </div>
      )}

      <div className={`max-w-[85%] ${isUser ? "px-4 py-3 bg-gray-900 text-white rounded-2xl rounded-br-md" : "space-y-3"}`}>
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <>
            {message.data && (
              <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md p-4 space-y-3 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">
                    {message.data.title}
                  </span>
                  <button
                    onClick={handleExport}
                    className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors"
                    title="Export data"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Dynamic Data Visualizer */}
                <ErrorBoundary>
                  <DataVisualizer
                    data={message.data.rawData ?? []}
                    chartType={message.data.chartType ?? "table"}
                    xAxis={message.data.xAxis ?? null}
                    yAxis={message.data.yAxis ?? null}
                    textContent={message.data.textContent}
                  />
                </ErrorBoundary>

                {/* Summary (for non-text chart types) */}
                {message.data.summary &&
                  message.data.chartType !== "text" &&
                  (message.data.rawData?.length ?? 0) > 0 && (
                    <p className="text-sm text-gray-500 pt-2 border-t border-gray-100">
                      {message.data.summary}
                    </p>
                  )}

                {/* Follow-up questions */}
                {message.data.followUpQuestions && message.data.followUpQuestions.length > 0 && (
                  <div className="pdf-exclude pt-2 border-t border-gray-100">
                    <p className="text-xs text-gray-400 mb-2 uppercase tracking-wider">Suggested follow-ups</p>
                    <div className="flex flex-wrap gap-2">
                      {message.data.followUpQuestions.map((q) => (
                        <button
                          key={q}
                          onClick={() => message.onFollowUp?.(q)}
                          className="px-3 py-1.5 rounded-lg text-xs border border-gray-200 bg-gray-50 text-gray-500 hover:text-gray-900 hover:border-orange-200 hover:bg-orange-50/50 transition-all text-left"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* SQL Disclosure */}
                {message.data.sql && (
                  <details className="pdf-exclude pt-1">
                    <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600 transition-colors">
                      View SQL
                    </summary>
                    <pre className="mt-2 text-xs bg-gray-50 rounded-lg p-3 overflow-x-auto text-gray-600 font-mono border border-gray-100">
                      {message.data.sql}
                    </pre>
                  </details>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  );
};

export default ChatMessage;
