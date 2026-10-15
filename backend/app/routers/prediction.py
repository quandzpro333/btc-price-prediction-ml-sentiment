from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
import joblib
import time
from pathlib import Path
from typing import Dict, Tuple

from app.core.database import get_db
from app.core.config import settings
from app.models import orm_models
from app.models.schemas import PredictionResponse, AIAnalysisResponse, BacktestResponse, BacktestPoint, ModelInfoResponse
from app.services.prediction_service import predict_next_price, VALID_MODELS
from app.services import gemini_service
from app.services.binance_service import fetch_klines
from app.services.indicator_service import compute_indicators, compute_trend

router = APIRouter(prefix="/api/prediction", tags=["prediction"])

ARTIFACT_DIR = Path(settings.ML_MODEL_DIR)

_ai_analysis_cache: Dict[str, Tuple[float, dict]] = {}
_AI_ANALYSIS_CACHE_TTL_SECONDS = 300


def _load_artifact_or_404(timeframe: str) -> dict:
    path = ARTIFACT_DIR / f"linear_regression_{timeframe}.joblib"
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"Chưa có model cho timeframe={timeframe}. Hãy chạy: "
                f"python ml/train_linear_regression.py --timeframe {timeframe} --full"
            ),
        )
    return joblib.load(path)


@router.get("", response_model=PredictionResponse)
async def get_prediction(
    timeframe: str = Query("1h", pattern="^(1h|4h|1d|1w)$"),
    model: str = Query(
        "linear_regression",
        pattern="^(linear_regression|xgboost|lstm)$",
        description="Chọn model dự đoán: linear_regression (regression, dự đoán giá) "
                     "| xgboost / lstm (classification, dự đoán xu hướng)",
    ),
    db: Session = Depends(get_db),
):
    """
    Sinh dự đoán bằng model được chọn. linear_regression trả về cả predicted_price;
    xgboost/lstm chỉ trả về trend + confidence (predicted_price = null) vì đây là
    bài toán classification, không dự đoán một mức giá cụ thể.
    """
    latest_sentiment = (
        db.query(orm_models.Sentiment).order_by(orm_models.Sentiment.captured_at.desc()).first()
    )
    sentiment_score = latest_sentiment.sentiment_score if latest_sentiment else 50.0

    try:
        result = await predict_next_price(
            timeframe=timeframe, model_name=model, sentiment_score=sentiment_score
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Chỉ lưu vào lịch sử prediction (phục vụ Dashboard) nếu là linear_regression —
    # Dashboard/backfill hiện được thiết kế cho model regression (so sánh actual_price
    # với predicted_price). Có thể mở rộng sau nếu muốn Dashboard hỗ trợ cả classification.
    if model == "linear_regression":
        record = orm_models.Prediction(
            symbol=settings.SYMBOL,
            timeframe=timeframe,
            model_name=result["model_name"],
            predicted_at=result["predicted_at"],
            target_time=result["target_time"],
            current_price=result["current_price"],
            predicted_price=result["predicted_price"],
            trend=result["trend"],
            confidence=result["confidence"],
            explanation=result["explanation"],
        )
        db.add(record)
        db.commit()

    return PredictionResponse(symbol=settings.SYMBOL, timeframe=timeframe, **result)


@router.get("/ai-analysis", response_model=AIAnalysisResponse)
async def get_ai_analysis(
    timeframe: str = Query("1h", pattern="^(1h|4h|1d|1w)$"),
    db: Session = Depends(get_db),
):
    """
    Gọi Gemini để sinh báo cáo AI Analysis dựa trên dữ liệu thị trường hiện tại.
    Có cache 5 phút theo timeframe.
    """
    cached = _ai_analysis_cache.get(timeframe)
    if cached and (time.time() - cached[0]) < _AI_ANALYSIS_CACHE_TTL_SECONDS:
        return AIAnalysisResponse(**cached[1])

    candles = await fetch_klines(timeframe=timeframe, limit=60)
    df = compute_indicators(candles)
    trend = compute_trend(df)
    last = df.iloc[-1]

    latest_sentiment = (
        db.query(orm_models.Sentiment).order_by(orm_models.Sentiment.captured_at.desc()).first()
    )
    recent_news = (
        db.query(orm_models.News).order_by(orm_models.News.published_at.desc()).limit(5).all()
    )

    context = {
        "current_price": float(last["close"]),
        "trend": trend,
        "rsi_14": float(last["rsi_14"]) if last["rsi_14"] == last["rsi_14"] else None,
        "ema_12": float(last["ema_12"]),
        "ema_26": float(last["ema_26"]),
        "sentiment_score": latest_sentiment.sentiment_score if latest_sentiment else 50.0,
        "sentiment_label": latest_sentiment.sentiment_label if latest_sentiment else "neutral",
        "recent_news_summaries": [n.summary for n in recent_news if n.summary],
    }

    try:
        analysis = await gemini_service.generate_ai_analysis(context)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        if cached:
            return AIAnalysisResponse(**cached[1])
        raise HTTPException(status_code=503, detail=f"Gemini API lỗi: {exc}")

    _ai_analysis_cache[timeframe] = (time.time(), analysis)
    return AIAnalysisResponse(**analysis)


@router.get("/backtest", response_model=BacktestResponse)
async def get_backtest(timeframe: str = Query("1h", pattern="^(1h|4h|1d|1w)$")):
    """
    Backtest hiện chỉ hỗ trợ linear_regression (model duy nhất có target dạng giá
    liên tục, phù hợp để vẽ đường "dự đoán vs thực tế"). Với xgboost/lstm (classification),
    thước đo tương ứng là Accuracy/AUC-ROC — xem trong ml/artifacts/*.joblib hoặc
    chạy ml/compare_all_models.py.
    """
    artifact = _load_artifact_or_404(timeframe)
    dates = artifact.get("backtest_dates")
    actual = artifact.get("backtest_actual")
    predicted = artifact.get("backtest_predicted")

    if not dates:
        raise HTTPException(
            status_code=503,
            detail=(
                "Model này chưa lưu dữ liệu backtest. Hãy train lại: "
                f"python ml/train_linear_regression.py --timeframe {timeframe} --full"
            ),
        )

    points = [BacktestPoint(date=d, actual=a, predicted=p) for d, a, p in zip(dates, actual, predicted)]

    return BacktestResponse(
        symbol=settings.SYMBOL, timeframe=timeframe,
        mae=artifact["mae"], mape=artifact["mape"], points=points,
    )


@router.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info(timeframe: str = Query("1h", pattern="^(1h|4h|1d|1w)$")):
    """
    Model Explainability hiện chỉ hỗ trợ linear_regression (hệ số hồi quy). Với
    xgboost, thước đo tương đương là feature_importance (xem trong file .joblib).
    """
    artifact = _load_artifact_or_404(timeframe)
    if "coefficients" not in artifact:
        raise HTTPException(
            status_code=503,
            detail=(
                "Model này chưa lưu hệ số. Hãy train lại: "
                f"python ml/train_linear_regression.py --timeframe {timeframe} --full"
            ),
        )

    return ModelInfoResponse(
        timeframe=timeframe,
        feature_names=artifact["feature_names"],
        coefficients=artifact["coefficients"],
        intercept=artifact["intercept"],
        mae=artifact["mae"],
        mape=artifact["mape"],
        trained_at=artifact.get("trained_at"),
        n_train_samples=artifact.get("n_train_samples", 0),
        n_test_samples=artifact.get("n_test_samples", 0),
    )
