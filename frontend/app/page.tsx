"use client";

import { useEffect, useState } from "react";
import {
  fetchPrice,
  fetchPrediction,
  fetchAIAnalysis,
  fetchNews,
  fetchSentiment,
  fetchBacktest,
  fetchDashboard,
  Timeframe,
  ModelName,
  PriceResponse,
  PredictionResponse,
  AIAnalysisResponse,
  NewsItem,
  SentimentResponse,
  BacktestResponse,
  DashboardResponse,
} from "@/lib/api";
import PriceChart from "@/components/PriceChart";
import PredictionCard from "@/components/PredictionCard";
import AIAnalysisPanel from "@/components/AIAnalysisPanel";
import { NewsFeed, FearGreedGauge } from "@/components/NewsAndSentiment";
import AIChat from "@/components/AIChat";
import BacktestChart from "@/components/BacktestChart";
import DashboardPanel from "@/components/DashboardPanel";

const TIMEFRAMES: Timeframe[] = ["1h", "4h", "1d", "1w"];
const MODELS: ModelName[] = ["linear_regression", "xgboost", "lstm"];
const MODEL_LABEL: Record<ModelName, string> = {
  linear_regression: "Linear Regression",
  xgboost: "XGBoost",
  lstm: "LSTM",
};

export default function HomePage() {
  const [timeframe, setTimeframe] = useState<Timeframe>("1h");
  const [selectedModel, setSelectedModel] = useState<ModelName>("linear_regression");
  const [price, setPrice] = useState<PriceResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null | undefined>(undefined);
  const [analysis, setAnalysis] = useState<AIAnalysisResponse | null | undefined>(undefined);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(true);
  const [sentiment, setSentiment] = useState<SentimentResponse | undefined>(undefined);
  const [backtest, setBacktest] = useState<BacktestResponse | null | undefined>(undefined);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [showFullHistory, setShowFullHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = async () => {
    try {
      setDashboard(await fetchDashboard());
    } catch {
      setDashboard(null);
    }
  };

  const loadNews = async () => {
    setNewsLoading(true);
    try {
      setNews(await fetchNews(10));
    } catch {
      setNews([]);
    } finally {
      setNewsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    setPrediction(undefined);
    setAnalysis(undefined);
    setBacktest(undefined);
    setError(null);

    (async () => {
      try {
        const p = await fetchPrice(timeframe, 500, showFullHistory);
        if (!cancelled) setPrice(p);
      } catch {
        if (!cancelled)
          setError(
            showFullHistory
              ? `Chưa có dữ liệu lịch sử đầy đủ cho ${timeframe}. Hãy chạy: python ml/fetch_full_history.py --timeframe ${timeframe}`
              : "Không lấy được dữ liệu giá từ backend/Binance."
          );
      }
    })();

    (async () => {
      try {
        const res = await fetchPrediction(timeframe, selectedModel);
        if (!cancelled) setPrediction(res);
      } catch {
        if (!cancelled) setPrediction(null);
      }
    })();

    (async () => {
      try {
        const res = await fetchAIAnalysis(timeframe);
        if (!cancelled) setAnalysis(res);
      } catch {
        if (!cancelled) setAnalysis(null);
      }
    })();

    (async () => {
      await loadNews();
    })();

    (async () => {
      try {
        const res = await fetchSentiment();
        if (!cancelled) setSentiment(res);
      } catch {
        if (!cancelled) setSentiment(undefined);
      }
    })();

    (async () => {
      try {
        const res = await fetchBacktest(timeframe);
        if (!cancelled) setBacktest(res);
      } catch {
        if (!cancelled) setBacktest(null);
      }
    })();

    loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [timeframe, showFullHistory, selectedModel]);

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        {TIMEFRAMES.map((tf) => (
          <button
            key={tf}
            onClick={() => setTimeframe(tf)}
            className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wider border ${
              tf === timeframe
                ? "bg-bullish/10 border-bullish text-bullish"
                : "border-border text-ghost hover:text-white hover:border-gray-500"
            }`}
          >
            {tf}
          </button>
        ))}

        <div className="w-px h-6 bg-border mx-1" />

        <button
          onClick={() => setShowFullHistory((v) => !v)}
          title="Hiện toàn bộ nến từ khi BTCUSDT lên sàn Binance (2017), đọc từ dữ liệu đã tải sẵn"
          className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wider border ${
            showFullHistory
              ? "bg-amber/10 border-amber text-amber"
              : "border-border text-ghost hover:text-white hover:border-gray-500"
          }`}
        >
          {showFullHistory ? "✓ TOÀN BỘ LỊCH SỬ" : "TOÀN BỘ LỊCH SỬ"}
        </button>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] font-mono uppercase text-ghost mr-1">Model:</span>
        {MODELS.map((m) => (
          <button
            key={m}
            onClick={() => setSelectedModel(m)}
            className={`px-3 py-1.5 text-xs font-mono uppercase tracking-wider border ${
              m === selectedModel
                ? "bg-amber/10 border-amber text-amber"
                : "border-border text-ghost hover:text-white hover:border-gray-500"
            }`}
          >
            {MODEL_LABEL[m]}
          </button>
        ))}
      </div>

      {showFullHistory && (
        <p className="text-xs text-ghost font-mono">
          Đang hiện toàn bộ nến từ ~17/08/2017 (ngày BTCUSDT lên sàn Binance) đến hiện tại —
          dữ liệu đọc từ file đã tải sẵn (<code>ml/fetch_full_history.py</code>), không gọi
          trực tiếp Binance mỗi lần load trang. Khung <strong>1 tuần (1w)</strong> phù hợp nhất
          để xem toàn bộ lịch sử vì số lượng nến ít, tải nhanh và dễ nhìn xu hướng dài hạn.
        </p>
      )}

      {error && (
        <div className="text-xs font-mono text-bearish bg-bearish/10 border border-bearish/40 px-3 py-2">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          {price ? (
            <PriceChart
              candles={price.candles}
              support={price.support}
              resistance={price.resistance}
              timeframe={timeframe}
            />
          ) : (
            <div className="h-[420px] border border-border bg-panel animate-pulse" />
          )}
          {analysis === undefined ? (
            <div className="border border-border bg-panel p-4 text-xs text-ghost font-mono animate-pulse">
              Đang tải AI Analysis...
            </div>
          ) : analysis ? (
            <AIAnalysisPanel analysis={analysis} />
          ) : (
            <div className="border border-border bg-panel p-4 text-xs text-ghost font-mono">
              AI Analysis chưa khả dụng — cần cấu hình GEMINI_API_KEY trong backend/.env.
            </div>
          )}
        </div>

        <div className="space-y-4">
          {prediction === undefined ? (
            <div className="border border-border bg-panel p-4 text-xs text-ghost font-mono animate-pulse">
              Đang tải Prediction...
            </div>
          ) : prediction ? (
            <PredictionCard prediction={prediction} />
          ) : (
            <div className="border border-border bg-panel p-4 text-xs text-ghost font-mono">
              Prediction chưa khả dụng — cần train model &quot;{MODEL_LABEL[selectedModel]}&quot; trước
              (xem README, mục ML).
            </div>
          )}
          <FearGreedGauge sentiment={sentiment} />
          <NewsFeed news={news} loading={newsLoading} onRefresh={loadNews} />
        </div>
      </div>

      {/* Model Explainability đã bị xoá — Backtest Chart giờ chiếm full width thay vì
          chia cột với Model Info như trước */}
      {backtest === undefined ? (
        <div className="border border-border bg-panel p-4 text-xs text-ghost font-mono animate-pulse">
          Đang tải Backtest...
        </div>
      ) : backtest ? (
        <BacktestChart backtest={backtest} />
      ) : (
        <div className="border border-border bg-panel p-4 text-xs text-ghost font-mono">
          Backtest chưa khả dụng — cần train lại model bằng phiên bản mới nhất của
          train_linear_regression.py (đã lưu thêm dữ liệu backtest).
        </div>
      )}

      {dashboard && <DashboardPanel dashboard={dashboard} onRefresh={loadDashboard} />}

      <AIChat />
    </div>
  );
}
