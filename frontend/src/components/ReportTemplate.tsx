import React from 'react';
import {
    BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';

export interface ReportTemplateProps {
    messages: any[];
}

const COLORS = [
    '#4f46e5', '#0ea5e9', '#8b5cf6', '#ec4899',
    '#f59e0b', '#10b981', '#3b82f6', '#f43f5e', '#6366f1'
];

export const ReportTemplate: React.FC<ReportTemplateProps> = ({ messages }) => {
    const date = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    // Filter out user messages
    const aiMessages = messages.filter(m => m.role === 'assistant' || m.role === 'ai');

    // Helper to extract data
    const processMessage = (msg: any, idx: number) => {
        let userQuestion = "Insight";
        const msgIndex = messages.findIndex(m => m.id === msg.id);
        for (let i = msgIndex - 1; i >= 0; i--) {
            if (messages[i].role === 'user') {
                userQuestion = messages[i].content;
                break;
            }
        }
        if (userQuestion.startsWith('🎤 "')) {
            userQuestion = userQuestion.replace('🎤 "', '').replace('"', '');
        }

        const data = msg.data;
        if (!data) return null;

        let chartType = data.chartType;
        const chartData = data.rawData || [];
        let resolvedX = data.xAxis;
        let resolvedY = data.yAxis;

        const isChartType = chartType === "bar" || chartType === "line" || chartType === "pie";

        if (isChartType && chartData.length > 0) {
            const dataKeys = Object.keys(chartData[0]);
            if ((!resolvedX || !resolvedY) && dataKeys.length >= 2) {
                if (!resolvedX) resolvedX = dataKeys[0];
                if (!resolvedY) {
                    const numericKey = dataKeys.find((k) => k !== resolvedX && typeof chartData[0][k] === "number");
                    resolvedY = numericKey ?? dataKeys[1];
                }
            }
        }

        const isKpi = chartType === "kpi" || (chartType !== "text" && chartData.length === 1 && !isChartType);
        if (isKpi) chartType = 'kpi';
        // Treat tables as full width if not a chart or kpi
        if (chartType === 'table' || (chartData.length > 1 && !isChartType)) chartType = 'table';

        return { ...msg, userQuestion, chartType, chartData, resolvedX, resolvedY, summary: msg.content || data.summary };
    };

    const processedMessages = aiMessages.map(processMessage).filter(Boolean);

    // Groupings
    const kpiMessages = processedMessages.filter(m => m.chartType === 'kpi');
    const gridCharts = processedMessages.filter(m => m.chartType === 'pie' || m.chartType === 'line');
    const fullWidthCharts = processedMessages.filter(m => m.chartType === 'bar' || m.chartType === 'table');

    return (
        <>
            <style>{`
        @media print {
          body { -webkit-print-color-adjust: exact; }
          #insightx-corporate-report { background-color: white !important; }
        }
      `}</style>

            <div id="insightx-corporate-report" className="bg-white text-slate-900 mx-auto font-sans w-[794px] min-h-[1123px] p-12 box-border">
                {/* Professional Header */}
                <header className="flex justify-between items-end border-b-2 border-slate-300 pb-4 mb-8">
                    <div>
                        <h2 className="text-xl font-extrabold tracking-tight text-slate-900 uppercase">InsightX Analytics</h2>
                        <h1 className="text-3xl font-light text-slate-500 mt-1">Executive Transaction Briefing</h1>
                    </div>
                    <div className="text-right">
                        <p className="text-sm font-medium text-slate-500">{date}</p>
                    </div>
                </header>

                {/* Section 1: Top-Level KPIs */}
                {kpiMessages.length > 0 && (
                    <div className="flex flex-wrap gap-4 mb-10">
                        {kpiMessages.map(item => {
                            const row = item.chartData && item.chartData[0];
                            if (!row) return null;
                            const keys = Object.keys(row);
                            const valKey = item.resolvedY || keys[keys.length - 1];
                            const val = row[valKey];
                            const displayVal = typeof val === "number" && (valKey.includes("amount") || valKey.includes("balance") || valKey.includes("inr"))
                                ? `₹${val.toLocaleString("en-IN")}`
                                : val;
                            const label = valKey.replace(/_/g, " ");

                            return (
                                <div key={item.id} className="flex-1 bg-slate-50 border border-slate-200 rounded-lg p-5 border-l-4 border-l-violet-600 print-avoid-break">
                                    <div className="text-3xl font-bold text-slate-800">{displayVal}</div>
                                    <div className="text-xs uppercase text-slate-500 mt-1 font-semibold tracking-wider">{label}</div>
                                    {item.summary && item.summary !== displayVal?.toString() && (
                                        <p className="text-[10px] text-slate-400 mt-2 leading-tight">{item.summary}</p>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Section 2: Grid Insights (Pie/Line) */}
                {gridCharts.length > 0 && (
                    <div className="grid grid-cols-2 gap-8 mb-10">
                        {gridCharts.map(item => (
                            <div key={item.id} className="print-avoid-break">
                                <h3 className="text-sm font-bold text-slate-800 mb-4 border-b border-slate-100 pb-2">{item.userQuestion}</h3>

                                <div className="flex justify-center items-center h-[200px]">
                                    {item.chartType === 'pie' && (
                                        <PieChart width={300} height={200}>
                                            <Pie
                                                data={item.chartData} cx="50%" cy="50%" innerRadius={40} outerRadius={80}
                                                dataKey={item.resolvedY} nameKey={item.resolvedX} stroke="none"
                                            >
                                                {item.chartData.map((_, i) => (
                                                    <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip formatter={(val) => [Number(val).toLocaleString("en-IN"), item.resolvedY!.replace(/_/g, " ")]} />
                                            <Legend wrapperStyle={{ fontSize: 10, paddingTop: 10 }} />
                                        </PieChart>
                                    )}

                                    {item.chartType === 'line' && (
                                        <LineChart width={320} height={200} data={item.chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                            <XAxis dataKey={item.resolvedX} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                                            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => v.toLocaleString("en-IN")} width={40} />
                                            <Tooltip formatter={(val) => [Number(val).toLocaleString("en-IN"), item.resolvedY!.replace(/_/g, " ")]} />
                                            <Line type="monotone" dataKey={item.resolvedY} stroke="#4f46e5" strokeWidth={2} dot={{ r: 2, fill: '#4f46e5' }} />
                                        </LineChart>
                                    )}
                                </div>

                                <p className="text-xs text-slate-600 leading-relaxed text-justify mt-4">
                                    {item.summary}
                                </p>
                            </div>
                        ))}
                    </div>
                )}

                {/* Section 3: Deep Dives (Bar/Table) */}
                {fullWidthCharts.length > 0 && (
                    <div className="flex flex-col gap-10">
                        {fullWidthCharts.map(item => (
                            <div key={item.id} className="print-avoid-break">
                                <h3 className="text-sm font-bold text-slate-800 mb-4 border-b border-slate-100 pb-2">{item.userQuestion}</h3>

                                {item.chartType === 'bar' && item.resolvedX && item.resolvedY && (
                                    <div className="flex justify-center mb-4">
                                        <BarChart width={680} height={250} data={item.chartData} margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                            <XAxis dataKey={item.resolvedX} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                                            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => v.toLocaleString("en-IN")} />
                                            <Tooltip cursor={{ fill: '#f8fafc' }} formatter={(val) => [Number(val).toLocaleString("en-IN"), item.resolvedY!.replace(/_/g, " ")]} />
                                            <Legend wrapperStyle={{ fontSize: 11 }} />
                                            <Bar dataKey={item.resolvedY} fill="#4f46e5" radius={[2, 2, 0, 0]} name={item.resolvedY.replace(/_/g, " ")} maxBarSize={50} />
                                        </BarChart>
                                    </div>
                                )}

                                {item.chartType === 'table' && (
                                    <div className="mb-4 overflow-hidden rounded-md border border-slate-200">
                                        <table className="w-full text-left text-xs text-slate-600">
                                            <thead className="bg-slate-50 text-slate-800 font-semibold border-b border-slate-200 uppercase tracking-wide">
                                                <tr>
                                                    {Object.keys(item.chartData[0] || {}).map((key) => (
                                                        <th key={key} className="px-3 py-2">{key.replace(/_/g, " ")}</th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100">
                                                {item.chartData.slice(0, 8).map((row: any, i: number) => (
                                                    <tr key={i} className="hover:bg-slate-50">
                                                        {Object.values(row).map((val: any, j: number) => (
                                                            <td key={j} className="px-3 py-2">
                                                                {typeof val === 'number' ? val.toLocaleString("en-IN") : String(val)}
                                                            </td>
                                                        ))}
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                        {item.chartData.length > 8 && (
                                            <div className="bg-slate-50 px-3 py-1.5 text-[10px] text-slate-400 text-center border-t border-slate-100">
                                                Showing top 8 corresponding rows.
                                            </div>
                                        )}
                                    </div>
                                )}

                                <div className="bg-violet-50 text-violet-900 text-xs p-4 rounded-md mt-4 border border-violet-100 shadow-sm">
                                    <span className="font-semibold block mb-1">Executive Summary:</span>
                                    {item.summary}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </>
    );
};
