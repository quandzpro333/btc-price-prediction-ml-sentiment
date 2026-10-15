-- =========================================================
-- Bitcoin Price Prediction - Database Schema (SQLite)
-- Đồ án học tập — không dùng cho giao dịch thật
-- =========================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------
-- users: người dùng đăng nhập website (đơn giản)
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------
-- market_data: dữ liệu nến OHLCV + chỉ báo kỹ thuật + dữ liệu bổ trợ
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS market_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL DEFAULT 'BTCUSDT',
    timeframe       TEXT NOT NULL CHECK (timeframe IN ('1h', '4h', '1d', '1w')),
    open_time       DATETIME NOT NULL,
    open            REAL NOT NULL,
    high            REAL NOT NULL,
    low             REAL NOT NULL,
    close           REAL NOT NULL,
    volume          REAL NOT NULL,

    -- Chỉ báo kỹ thuật (tính sẵn để phục vụ ML + hiển thị)
    ema_12          REAL,
    ema_26          REAL,
    rsi_14          REAL,
    bb_upper        REAL,
    bb_middle       REAL,
    bb_lower        REAL,

    -- Dữ liệu bổ trợ thị trường (join theo thời điểm gần nhất)
    gold_price      REAL,
    dxy_index       REAL,
    fear_greed      INTEGER,

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, open_time)
);

CREATE INDEX IF NOT EXISTS idx_market_data_lookup
    ON market_data (symbol, timeframe, open_time DESC);

-- ---------------------------------------------------------
-- news: tin tức crypto đã thu thập + tóm tắt bởi Gemini
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS news (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,           -- vd: 'CoinDesk', 'X/Twitter'
    title           TEXT NOT NULL,
    url             TEXT,
    published_at    DATETIME,
    raw_content     TEXT,
    summary         TEXT,                    -- tóm tắt do Gemini sinh ra
    sentiment_label TEXT CHECK (sentiment_label IN ('bullish','bearish','neutral')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news (published_at DESC);

-- ---------------------------------------------------------
-- sentiment: điểm sentiment tổng hợp theo thời điểm
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS sentiment (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at         DATETIME NOT NULL,
    fear_greed_index    INTEGER,
    google_trends_score REAL,
    news_sentiment_avg  REAL,   -- -1..1
    twitter_sentiment_avg REAL, -- -1..1
    sentiment_score     REAL NOT NULL,  -- điểm tổng hợp 0..100
    sentiment_label      TEXT CHECK (sentiment_label IN ('bullish','bearish','neutral')),
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sentiment_time ON sentiment (captured_at DESC);

-- ---------------------------------------------------------
-- predictions: kết quả dự đoán của mô hình ML
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS predictions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol              TEXT NOT NULL DEFAULT 'BTCUSDT',
    timeframe           TEXT NOT NULL CHECK (timeframe IN ('1h', '4h', '1d', '1w')),
    model_name          TEXT NOT NULL,      -- 'linear_regression' | 'simple_rnn'
    predicted_at        DATETIME NOT NULL,  -- thời điểm sinh dự đoán
    target_time         DATETIME NOT NULL,  -- thời điểm dự đoán hướng tới
    current_price       REAL NOT NULL,
    predicted_price      REAL NOT NULL,
    trend               TEXT CHECK (trend IN ('bullish','bearish','neutral')),
    confidence          REAL,               -- 0..1
    explanation         TEXT,               -- giải thích ngắn (rule-based hoặc Gemini)
    actual_price         REAL,              -- điền sau khi tới target_time, dùng để tính accuracy
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_predictions_lookup
    ON predictions (symbol, timeframe, predicted_at DESC);

-- ---------------------------------------------------------
-- chat_history: lịch sử hội thoại với AI Chat
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER REFERENCES users(id),
    role            TEXT NOT NULL CHECK (role IN ('user','assistant')),
    message         TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history (user_id, created_at);
