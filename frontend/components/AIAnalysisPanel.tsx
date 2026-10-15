import { AIAnalysisResponse } from "@/lib/api";
import PanelEyebrow from "@/components/PanelEyebrow";

export default function AIAnalysisPanel({ analysis }: { analysis: AIAnalysisResponse }) {
  const rows: Array<[string, string]> = [
    ["Tóm tắt thị trường", analysis.summary],
    ["Xu hướng hiện tại", analysis.trend_comment],
    ["Phân tích tin tức", analysis.news_comment],
    ["Sentiment", analysis.sentiment_comment],
    ["Chỉ báo kỹ thuật", analysis.indicator_comment],
  ];

  return (
    <div className="border border-border bg-panel p-4 panel-fade-in panel-hover">
      <PanelEyebrow>AI Analysis · Gemini</PanelEyebrow>
      <div className="space-y-3 mt-3">
        {rows.map(([label, text]) => (
          <div key={label} className="border-l-2 border-border pl-3">
            <p className="text-[10px] font-mono uppercase tracking-wide text-ghost mb-0.5">{label}</p>
            <p className="text-sm text-gray-200 font-sans">{text || "—"}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
