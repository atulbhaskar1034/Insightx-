import React from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

// -- Types --------------------------------------------------------------------

interface DataVisualizerProps {
  /** Raw data rows from the backend (array of objects) */
  data: Record<string, unknown>[];
  /** LLM-chosen chart type */
  chartType: string;
  /** Column name for X-axis / label */
  xAxis: string | null;
  /** Column name for Y-axis / value */
  yAxis: string | null;
  /** Optional: for text-only fallback */
  textContent?: string;
}

// -- Light-mode color palette -------------------------------------------------

const CHART_COLORS = [
  "#f97316", // orange-500
  "#06b6d4", // cyan-500
  "#ec4899", // pink-500
  "#8b5cf6", // violet-500
  "#10b981", // emerald-500
  "#3b82f6", // blue-500
  "#f59e0b", // amber-500
  "#f43f5e", // rose-500
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

const AXIS_TICK = { fill: "#9ca3af", fontSize: 12 };
const GRID_STROKE = "#f3f4f6";

// -- Helpers ------------------------------------------------------------------

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "\u2014";
  if (typeof val === "number") return val.toLocaleString("en-IN");
  return String(val);
}

function isCurrencyKey(key: string): boolean {
  return /amount|value|total|sum|credit|debit|inr|revenue|cost/i.test(key);
}

function formatCell(key: string, val: unknown): string {
  if (val === null || val === undefined) return "\u2014";
  if (typeof val === "number") {
    const formatted = val.toLocaleString("en-IN");
    return isCurrencyKey(key) ? `\u20b9${formatted}` : formatted;
  }
  return String(val);
}

// -- Component ----------------------------------------------------------------

const DataVisualizer: React.FC<DataVisualizerProps> = ({
  data,
  chartType,
  xAxis,
  yAxis,
  textContent,
}) => {
  // Guard: no data
  if (!data || data.length === 0) {
    if (textContent) {
      return (
        <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
          {textContent}
        </p>
      );
    }
    return null;
  }

  // ── KPI ─────────────────────────────────────────────────────────────────────
  if (chartType === "kpi" || data.length === 1) {
    const row = data[0];
    const keys = Object.keys(row);
    // Try to show label + value, or just the single value
    const labelKey = keys.length > 1 ? keys[0] : null;
    const valueKey = yAxis || keys[keys.length - 1];
    const rawValue = row[valueKey];

    return (
      <div className="flex flex-col items-center justify-center py-6 px-4">
        {labelKey && (
          <span className="text-xs text-gray-400 uppercase tracking-wider mb-2">
            {String(row[labelKey])}
          </span>
        )}
        <span className="text-6xl font-extrabold landing-stat-gradient-orange drop-shadow-sm">
          {typeof rawValue === "number" && isCurrencyKey(valueKey)
            ? `\u20b9${rawValue.toLocaleString("en-IN")}`
            : formatValue(rawValue)}
        </span>
        <span className="text-xs text-gray-400 mt-2 uppercase tracking-wider">
          {valueKey.replace(/_/g, " ")}
        </span>
      </div>
    );
  }

  // ── Column Resolution (handles LLM vs data key mismatches) ────────────────
  const dataKeys = Object.keys(data[0]);

  function resolveColumn(name: string | null): string | null {
    if (!name) return null;
    // 1. Exact match
    if (dataKeys.includes(name)) return name;
    // 2. Case-insensitive match
    const lower = name.toLowerCase();
    const ciMatch = dataKeys.find((k) => k.toLowerCase() === lower);
    if (ciMatch) return ciMatch;
    // 3. Normalized match (strip spaces/underscores, lowercase)
    const normalize = (s: string) => s.toLowerCase().replace(/[\s_-]+/g, "");
    const normMatch = dataKeys.find((k) => normalize(k) === normalize(name));
    if (normMatch) return normMatch;
    return null;
  }

  let resolvedX = resolveColumn(xAxis);
  let resolvedY = resolveColumn(yAxis);

  // Auto-detect if LLM chose a chart but axes didn't resolve
  const isChartType = chartType === "bar" || chartType === "line" || chartType === "pie";
  if (isChartType && (!resolvedX || !resolvedY) && dataKeys.length >= 2) {
    // First column = labels, first numeric column = values
    if (!resolvedX) resolvedX = dataKeys[0];
    if (!resolvedY) {
      const numericKey = dataKeys.find(
        (k) => k !== resolvedX && typeof data[0][k] === "number"
      );
      resolvedY = numericKey ?? dataKeys[1];
    }
  }

  // ── Charts (bar/line/pie) ───────────────────────────────────────────────────
  if (isChartType && resolvedX && resolvedY) {
    // Ensure numeric y-axis values
    const chartData = data.map((row) => ({
      ...row,
      [resolvedY!]: typeof row[resolvedY!] === "number" ? row[resolvedY!] : Number(row[resolvedY!]) || 0,
    }));

    return (
      <div className="w-full bg-gray-50 border border-gray-100 rounded-xl p-4">
        <ResponsiveContainer width="100%" height={400}>
          {chartType === "bar" ? (
            <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
              <XAxis
                dataKey={resolvedX}
                tick={AXIS_TICK}
                axisLine={{ stroke: "#e5e7eb" }}
                tickLine={false}
              />
              <YAxis
                tick={AXIS_TICK}
                axisLine={{ stroke: "#e5e7eb" }}
                tickLine={false}
                tickFormatter={(v: number) => v.toLocaleString("en-IN")}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value: number) => [value.toLocaleString("en-IN"), resolvedY!.replace(/_/g, " ")]}
                cursor={{ fill: "rgba(249, 115, 22, 0.04)" }}
              />
              <Legend wrapperStyle={{ color: "#6b7280", fontSize: "12px" }} />
              <Bar
                dataKey={resolvedY!}
                fill={CHART_COLORS[0]}
                radius={[6, 6, 0, 0]}
                name={resolvedY!.replace(/_/g, " ")}
              />
            </BarChart>
          ) : chartType === "line" ? (
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
              <XAxis
                dataKey={resolvedX}
                tick={AXIS_TICK}
                axisLine={{ stroke: "#e5e7eb" }}
                tickLine={false}
              />
              <YAxis
                tick={AXIS_TICK}
                axisLine={{ stroke: "#e5e7eb" }}
                tickLine={false}
                tickFormatter={(v: number) => v.toLocaleString("en-IN")}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value: number) => [value.toLocaleString("en-IN"), resolvedY!.replace(/_/g, " ")]}
              />
              <Legend wrapperStyle={{ color: "#6b7280", fontSize: "12px" }} />
              <Line
                type="monotone"
                dataKey={resolvedY!}
                stroke={CHART_COLORS[0]}
                strokeWidth={2.5}
                dot={{ fill: CHART_COLORS[0], strokeWidth: 0, r: 4 }}
                activeDot={{ r: 7, fill: CHART_COLORS[0], stroke: "#fff", strokeWidth: 2 }}
                name={resolvedY!.replace(/_/g, " ")}
              />
            </LineChart>
          ) : (
            // Pie chart
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={120}
                dataKey={resolvedY!}
                nameKey={resolvedX!}
                stroke="none"
                paddingAngle={2}
                label={({ name, percent }: { name: string; percent: number }) =>
                  `${name} (${(percent * 100).toFixed(1)}%)`
                }
                labelLine={{ stroke: "#9ca3af", strokeWidth: 1 }}
              >
                {chartData.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value: number) => [value.toLocaleString("en-IN"), resolvedY!.replace(/_/g, " ")]}
              />
              <Legend wrapperStyle={{ color: "#6b7280", fontSize: "12px" }} />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    );
  }

  // ── Table Fallback ──────────────────────────────────────────────────────────
  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50">
            {columns.map((col) => (
              <th
                key={col}
                className="text-left px-4 py-3 text-gray-500 font-medium text-xs uppercase tracking-wider whitespace-nowrap"
              >
                {col.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={i}
              className="border-b border-gray-100 hover:bg-orange-50/30 transition-colors"
            >
              {columns.map((col) => (
                <td
                  key={col}
                  className="px-4 py-2.5 text-gray-700 whitespace-nowrap"
                >
                  {formatCell(col, row[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataVisualizer;
