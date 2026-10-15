from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import orm_models
from app.models.schemas import ChatRequest, ChatResponse
from app.services import gemini_service
from app.services.binance_service import fetch_klines
from app.services.indicator_service import compute_indicators, compute_trend

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    Chatbot đơn giản: gom context (giá hiện tại, RSI, trend, Fear&Greed,
    dự đoán gần nhất) rồi để Gemini trả lời câu hỏi của người dùng.
    """
    candles = await fetch_klines(timeframe="1h", limit=30)
    df = compute_indicators(candles)
    last = df.iloc[-1]
    trend = compute_trend(df)

    latest_sentiment = (
        db.query(orm_models.Sentiment).order_by(orm_models.Sentiment.captured_at.desc()).first()
    )
    latest_prediction = (
        db.query(orm_models.Prediction).order_by(orm_models.Prediction.predicted_at.desc()).first()
    )

    context = {
        "current_price": float(last["close"]),
        "rsi_14": float(last["rsi_14"]) if last["rsi_14"] == last["rsi_14"] else None,
        "trend": trend,
        "fear_greed_index": latest_sentiment.fear_greed_index if latest_sentiment else None,
        "sentiment_label": latest_sentiment.sentiment_label if latest_sentiment else None,
        "latest_prediction": {
            "predicted_price": latest_prediction.predicted_price,
            "trend": latest_prediction.trend,
            "explanation": latest_prediction.explanation,
        }
        if latest_prediction
        else None,
    }

    try:
        reply = await gemini_service.chat_with_context(payload.message, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    if payload.user_id:
        db.add(orm_models.ChatHistory(user_id=payload.user_id, role="user", message=payload.message))
        db.add(orm_models.ChatHistory(user_id=payload.user_id, role="assistant", message=reply))
        db.commit()

    return ChatResponse(reply=reply)
