"""
ORM models — ánh xạ 1-1 với database/schema.sql
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class MarketData(Base):
    __tablename__ = "market_data"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, default="BTCUSDT", nullable=False)
    timeframe = Column(String, nullable=False)
    open_time = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    ema_12 = Column(Float)
    ema_26 = Column(Float)
    rsi_14 = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)

    gold_price = Column(Float)
    dxy_index = Column(Float)
    fear_greed = Column(Integer)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("symbol", "timeframe", "open_time"),)


class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    title = Column(String, nullable=False)
    url = Column(String)
    published_at = Column(DateTime)
    raw_content = Column(String)
    summary = Column(String)
    sentiment_label = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Sentiment(Base):
    __tablename__ = "sentiment"
    id = Column(Integer, primary_key=True, index=True)
    captured_at = Column(DateTime, nullable=False)
    fear_greed_index = Column(Integer)
    google_trends_score = Column(Float)
    news_sentiment_avg = Column(Float)
    twitter_sentiment_avg = Column(Float)
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, default="BTCUSDT", nullable=False)
    timeframe = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    predicted_at = Column(DateTime, nullable=False)
    target_time = Column(DateTime, nullable=False)
    current_price = Column(Float, nullable=False)
    predicted_price = Column(Float, nullable=False)
    trend = Column(String)
    confidence = Column(Float)
    explanation = Column(String)
    actual_price = Column(Float)
    created_at = Column(DateTime, server_default=func.now())


class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
