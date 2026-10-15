import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/backend-api",
});

export type Timeframe = "1h" | "4h" | "1d" | "1w";
// Model dự đoán: linear_regression (regression, có predicted_price) hoặc
// xgboost/lstm (classification, predicted_price = null, chỉ có trend + confidence)
export type ModelName = "linear_regression" | "xgboost" | "lstm";

export interface Candle {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema_12?: number;
  ema_26?: number;
  rsi_14?: number;
  bb_upper?: number;
  bb_middle?: number;
  bb_lower?: number;
}

export interface PriceResponse {
  symbol: string;
  timeframe: string;
  candles: Candle[];
  support?: number;
  resistance?: number;
  trend?: string;
}

export interface PredictionResponse {
  symbol: string;
  timeframe: string;
  model_name: string;
  model_type: "regression" | "classification";
  predicted_at: string;
  target_time: string;
  current_price: number;
  predicted_price: number | null; // null với model classification (xgboost/lstm)
  trend: "bullish" | "bearish" | "neutral";
  confidence: number;
  explanation: string;
  actual_price?: number | null;
}

export interface AIAnalysisResponse {
  summary: string;
  trend_comment: string;
  news_comment: string;
  sentiment_comment: string;
  indicator_comment: string;
}

export interface NewsItem {
  source: string;
  title: string;
  url?: string;
  published_at?: string;
  summary?: string;
  sentiment_label?: string;
}

export interface SentimentResponse {
  captured_at: string;
  fear_greed_index?: number;
  sentiment_score: number;
  sentiment_label: string;
}

export interface DashboardResponse {
  accuracy: number;
  win_rate: number;
  total_predictions: number;
  directional_predictions: number;
  neutral_predictions: number;
  recent_predictions: PredictionResponse[];
  simulated_pnl: number;
}

export interface BacktestPoint {
  date: string;
  actual: number;
  predicted: number;
}

export interface BacktestResponse {
  symbol: string;
  timeframe: string;
  mae: number;
  mape: number;
  points: BacktestPoint[];
}

export interface ModelInfoResponse {
  timeframe: string;
  model_type: string;
  feature_names: string[];
  coefficients: number[];
  intercept: number;
  mae: number;
  mape: number;
  trained_at?: string;
  n_train_samples: number;
  n_test_samples: number;
}

export const fetchPrice = (timeframe: Timeframe, limit = 200, full = false) =>
  api.get<PriceResponse>("/price", { params: { timeframe, limit, full } }).then((r) => r.data);

// Thêm tham số `model` — mặc định linear_regression để tương thích ngược
export const fetchPrediction = (timeframe: Timeframe, model: ModelName = "linear_regression") =>
  api.get<PredictionResponse>("/prediction", { params: { timeframe, model } }).then((r) => r.data);

export const fetchAIAnalysis = (timeframe: Timeframe) =>
  api.get<AIAnalysisResponse>("/prediction/ai-analysis", { params: { timeframe } }).then((r) => r.data);

export const fetchNews = (limit = 20) =>
  api.get<NewsItem[]>("/news", { params: { limit } }).then((r) => r.data);

export const triggerNewsRefresh = (limit = 5) =>
  api
    .post<{ fetched_from_coindesk: number; added: number; skipped_existing: number }>(
      "/news/refresh",
      null,
      { params: { limit } }
    )
    .then((r) => r.data);

export const fetchSentiment = () =>
  api.get<SentimentResponse>("/sentiment/latest").then((r) => r.data);

export const fetchDashboard = () =>
  api.get<DashboardResponse>("/dashboard").then((r) => r.data);

export const triggerBackfill = () =>
  api.post<{ backfilled: number }>("/dashboard/backfill").then((r) => r.data);

export const fetchBacktest = (timeframe: Timeframe) =>
  api.get<BacktestResponse>("/prediction/backtest", { params: { timeframe } }).then((r) => r.data);

export const fetchModelInfo = (timeframe: Timeframe) =>
  api.get<ModelInfoResponse>("/prediction/model-info", { params: { timeframe } }).then((r) => r.data);

export const sendChatMessage = (message: string) =>
  api.post<{ reply: string }>("/chat", { message }).then((r) => r.data.reply);

export default api;
