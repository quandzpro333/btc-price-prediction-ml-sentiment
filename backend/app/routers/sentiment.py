from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import orm_models
from app.models.schemas import SentimentResponse
from app.services import gemini_service, market_context_service

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])


@router.get("/latest", response_model=SentimentResponse)
async def get_latest_sentiment(db: Session = Depends(get_db)):
    """Trả về bản ghi sentiment tổng hợp gần nhất trong DB."""
    latest = (
        db.query(orm_models.Sentiment).order_by(orm_models.Sentiment.captured_at.desc()).first()
    )
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="Chưa có dữ liệu sentiment. Hãy gọi POST /api/sentiment/refresh trước.",
        )
    return latest


@router.post("/refresh", response_model=SentimentResponse)
async def refresh_sentiment(db: Session = Depends(get_db)):
    """
    Thu thập Fear&Greed mới nhất + tin tức gần đây trong DB, gọi Gemini để
    sinh điểm sentiment tổng hợp, rồi lưu 1 bản ghi mới vào bảng `sentiment`.
    """
    fear_greed = await market_context_service.fetch_fear_greed_index()

    recent_news = (
        db.query(orm_models.News).order_by(orm_models.News.published_at.desc()).limit(10).all()
    )
    news_items = [{"title": n.title, "summary": n.summary} for n in recent_news]

    try:
        result = await gemini_service.generate_sentiment_score(
            fear_greed=fear_greed, news_items=news_items, trends_score=None
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    from datetime import datetime

    record = orm_models.Sentiment(
        captured_at=datetime.utcnow(),
        fear_greed_index=fear_greed,
        google_trends_score=None,
        news_sentiment_avg=None,
        twitter_sentiment_avg=None,
        sentiment_score=result.get("sentiment_score", 50),
        sentiment_label=result.get("sentiment_label", "neutral"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
