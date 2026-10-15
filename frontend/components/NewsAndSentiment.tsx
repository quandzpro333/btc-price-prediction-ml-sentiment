"use client";

import { useState } from "react";
import { NewsItem, SentimentResponse, triggerNewsRefresh } from "@/lib/api";
import PanelEyebrow from "@/components/PanelEyebrow";
import { showToast } from "@/lib/toast";

const sentimentColor: Record<string, string> = {
  bullish: "text-bullish",
  bearish: "text-bearish",
  neutral: "text-ghost",
};

export function NewsFeed({
  news,
  loading = false,
  onRefresh,
}: {
  news: NewsItem[];
  loading?: boolean;
  onRefresh?: () => void;
}) {
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const result = await triggerNewsRefresh(5);
      onRefresh?.();
      if (result.added > 0) {
        showToast(`Đã thêm ${result.added} tin mới từ CoinDesk`, "success");
      } else {
        showToast("Không có tin mới (đã cập nhật gần đây)", "info");
      }
    } catch {
      showToast("Không lấy được tin — kiểm tra kết nối/backend", "error");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="border border-border bg-panel p-4 panel-fade-in panel-hover">
      <div className="flex items-center justify-between mb-1">
        <PanelEyebrow>News · CoinDesk (BTC)</PanelEyebrow>
        {onRefresh && (
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="text-[10px] font-mono uppercase border border-border text-ghost hover:text-bullish hover:border-bullish px-2 py-0.5 disabled:opacity-50"
          >
            {refreshing ? "..." : "↻"}
          </button>
        )}
      </div>
      <div className="space-y-3 max-h-80 overflow-y-auto mt-3">
        {loading && news.length === 0 && (
          <p className="text-xs text-ghost font-mono animate-pulse">Đang tải tin tức...</p>
        )}
        {!loading && news.length === 0 && (
          <p className="text-xs text-gray-500 font-mono">
            Chưa có tin tức — bấm nút ↻ để lấy tin mới nhất từ CoinDesk.
          </p>
        )}
        {news.map((n, i) => (
          <a
            key={i}
            href={n.url || undefined}
            target="_blank"
            rel="noopener noreferrer"
            className="block border-l-2 border-border pl-3 pb-2 last:pb-0 hover:border-bullish transition-colors"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm text-gray-200 line-clamp-2 font-sans">{n.title}</p>
              {n.sentiment_label && (
                <span
                  className={`text-[10px] font-mono uppercase shrink-0 border border-border px-1 ${sentimentColor[n.sentiment_label]}`}
                >
                  {n.sentiment_label}
                </span>
              )}
            </div>
            {n.summary && (
              <p className="text-xs text-gray-400 font-sans mt-1 line-clamp-2">{n.summary}</p>
            )}
            <p className="text-[10px] font-mono text-ghost mt-1">{n.source}</p>
          </a>
        ))}
      </div>
    </div>
  );
}

export function FearGreedGauge({ sentiment }: { sentiment?: SentimentResponse }) {
  const value = sentiment?.fear_greed_index ?? sentiment?.sentiment_score ?? 50;
  return (
    <div className="border border-border bg-panel p-4 panel-fade-in panel-hover">
      <PanelEyebrow>Fear &amp; Greed Index</PanelEyebrow>
      <div className="flex items-center gap-4 mt-3">
        <div className="text-3xl font-mono font-bold text-white">{value}</div>
        <div className="flex-1 h-1.5 bg-gradient-to-r from-bearish via-amber to-bullish relative">
          <div
            className="absolute top-[-3px] w-2.5 h-2.5 rounded-full bg-white border border-black"
            style={{ left: `calc(${value}% - 5px)` }}
          />
        </div>
      </div>
    </div>
  );
}
