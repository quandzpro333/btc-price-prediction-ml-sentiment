# Kiến trúc hệ thống — Bitcoin Price Prediction (Đồ án học tập)

> Website chỉ phục vụ mục đích học tập, **không** dùng để giao dịch thật.

## 1. Tổng quan luồng dữ liệu

```
┌─────────────┐      ┌──────────────────┐      ┌───────────────────┐
│  Binance API │─────▶│  Data Ingestion   │─────▶│                    │
│  (OHLCV)     │      │  (backend/app/    │      │                    │
└─────────────┘      │   services/*)     │      │   SQLite / Postgres│
┌─────────────┐      │                   │─────▶│   (market_data,    │
│ Gold, DXY    │─────▶│  Indicator Engine │      │    news, sentiment,│
│ Fear&Greed   │      │  (EMA/RSI/BB)     │      │    predictions...) │
│ Google Trends│      │                   │      │                    │
│ Crypto News  │      │  Sentiment (Gemini│      └─────────┬──────────┘
│ X/Twitter    │      │  API)             │                │
└─────────────┘      └──────────────────┘                │
                              │                             │
                              ▼                             │
                     ┌──────────────────┐                  │
                     │  ML Service        │◀─────────────────┘
                     │  Linear Regression │
                     │  hoặc Simple RNN   │
                     └────────┬──────────┘
                              │ prediction
                              ▼
                     ┌──────────────────┐        ┌────────────────────┐
                     │  FastAPI REST API │◀──────▶│  Next.js Frontend   │
                     │  (backend/app)    │        │  (TradingView-style)│
                     └──────────────────┘        └────────────────────┘
```

## 2. Các thành phần chính

### 2.1 Data Ingestion (backend/app/services)
- `binance_service.py`: lấy OHLCV (Open, High, Low, Close, Volume) từ Binance REST API (`/api/v3/klines`) cho BTCUSDT, các khung thời gian 1h/4h/1d.
- `market_context_service.py`: lấy giá vàng (XAU/USD), chỉ số DXY (qua nguồn dữ liệu tài chính công khai), Fear & Greed Index (alternative.me API), Google Trends (pytrends), tin tức Crypto (RSS/News API), một số bài đăng X/Twitter (X API v2 — cần API key riêng).
- Dữ liệu được cache/lưu định kỳ vào bảng `market_data`, `news`.

### 2.2 Indicator Engine (ml/indicators.py)
Tính toán trên chuỗi giá: EMA(12/26), RSI(14), Bollinger Bands(20, 2σ), Volume trung bình.
Suy ra Support/Resistance đơn giản (dựa trên local min/max hoặc pivot points) và Trend (so sánh EMA ngắn/dài).

Các khái niệm nâng cao (SMC, Wyckoff, FVG, Order Book, Liquidity) **chỉ hiển thị dưới dạng diễn giải văn bản do Gemini sinh ra** trong phần AI Analysis — không đưa vào vector đặc trưng của mô hình ML.

### 2.3 Sentiment Analysis (backend/app/services/sentiment_service.py)
- Tổng hợp tin tức + tweet + Fear&Greed + Google Trends.
- Gọi Gemini API để: tóm tắt tin tức, phân loại Bullish/Bearish/Neutral, sinh Sentiment Score (0–100).
- Gemini **chỉ** dùng để phân tích nội dung, không được dùng để dự đoán giá số.

### 2.4 ML Service (ml/)
- `features.py`: xây dựng ma trận đặc trưng từ giá quá khứ, volume, EMA, RSI, Bollinger Bands, giá vàng, DXY, Fear&Greed, sentiment score.
- `train_linear_regression.py`: baseline model (scikit-learn `LinearRegression`), dễ giải thích, dùng cho báo cáo đồ án.
- `train_rnn.py` (tuỳ chọn): SimpleRNN 1 lớp bằng Keras/TensorFlow, dùng nếu muốn thử mô hình chuỗi thời gian.
- Model được lưu (`.pkl` hoặc `.h5`) và load lại trong FastAPI khi phục vụ dự đoán realtime.

### 2.5 Backend API (backend/app)
FastAPI, cấu trúc theo router:
- `/api/price` — dữ liệu giá & nến.
- `/api/prediction` — kết quả dự đoán theo khung thời gian.
- `/api/news` — tin tức đã tóm tắt.
- `/api/sentiment` — điểm sentiment tổng hợp.
- `/api/dashboard` — accuracy, win rate, lịch sử dự đoán, PnL mô phỏng.
- `/api/chat` — chatbot hỏi đáp (dùng Gemini + dữ liệu nội bộ làm context).

### 2.6 Frontend (frontend/)
Next.js + TypeScript + Tailwind CSS + TradingView Lightweight Charts.
Trang chủ dạng dashboard: biểu đồ nến, Prediction Card, AI Analysis panel, Support/Resistance, Trend badge, News feed, Fear & Greed gauge, Whale News, heatmap đơn giản.

## 3. Nguyên tắc thiết kế
1. Mô hình ML **chỉ** nhận đầu vào là số liệu định lượng (giá, volume, chỉ báo, sentiment score) — không nhận trực tiếp văn bản.
2. Gemini xử lý phần ngôn ngữ tự nhiên (tóm tắt, phân loại, giải thích) — không trực tiếp trả về con số giá.
3. Toàn bộ kết quả dự đoán được lưu vào `predictions` để tính accuracy/win-rate về sau (đánh giá offline, minh bạch cho báo cáo đồ án).
4. Có banner rõ ràng "Chỉ phục vụ mục đích học tập — không phải lời khuyên đầu tư" trên frontend.
