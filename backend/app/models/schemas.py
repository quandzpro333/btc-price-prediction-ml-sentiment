"""
Pydantic schemas — định nghĩa shape dữ liệu trả về cho frontend.
(Chỉ trích phần liên quan tới Prediction — các schema khác giữ nguyên như cũ,
sao chép nguyên các phần News/Sentiment/Dashboard/... từ file gốc nếu bạn đang
ghi đè toàn bộ file.)
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class Candle(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    rsi_14: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None

    class Config:
        from_attributes = True


class PriceResponse(BaseModel):
    symbol: str
    timeframe: str
    candles: List[Candle]
    support: Optional[float] = None
    resistance: Optional[float] = None
    trend: Optional[str] = None


class PredictionResponse(BaseModel):
    symbol: str
    timeframe: str
    model_name: str
    # "regression" (Linear Regression, dự đoán giá) hoặc "classification"
    # (XGBoost/LSTM, chỉ dự đoán xu hướng) — frontend dùng field này để quyết định
    # có hiển thị "giá dự đoán" hay không.
    model_type: str = "regression"
    predicted_at: datetime
    target_time: datetime
    current_price: float
    # None với model classification (XGBoost/LSTM) — các model này không dự đoán
    # một mức giá cụ thể, chỉ dự đoán xác suất tăng/giảm.
    predicted_price: Optional[float] = None
    trend: str
    confidence: float
    explanation: str
    actual_price: Optional[float] = None

    class Config:
        from_attributes = True


class NewsItem(BaseModel):
    source: str
    title: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    sentiment_label: Optional[str] = None

    class Config:
        from_attributes = True


class SentimentResponse(BaseModel):
    captured_at: datetime
    fear_greed_index: Optional[int] = None
    google_trends_score: Optional[float] = None
    news_sentiment_avg: Optional[float] = None
    twitter_sentiment_avg: Optional[float] = None
    sentiment_score: float
    sentiment_label: str


class AIAnalysisResponse(BaseModel):
    summary: str
    trend_comment: str
    news_comment: str
    sentiment_comment: str
    indicator_comment: str


class DashboardResponse(BaseModel):
    accuracy: float
    win_rate: float
    total_predictions: int
    directional_predictions: int
    neutral_predictions: int
    recent_predictions: List[PredictionResponse]
    simulated_pnl: float


class BacktestPoint(BaseModel):
    date: datetime
    actual: float
    predicted: float


class BacktestResponse(BaseModel):
    symbol: str
    timeframe: str
    mae: float
    mape: float
    points: List[BacktestPoint]


class ModelInfoResponse(BaseModel):
    timeframe: str
    model_type: str = "linear_regression"
    feature_names: List[str]
    coefficients: List[float]
    intercept: float
    mae: float
    mape: float
    trained_at: Optional[datetime] = None
    n_train_samples: int
    n_test_samples: int


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
