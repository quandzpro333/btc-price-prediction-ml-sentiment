"""
Load model đã huấn luyện và sinh dự đoán realtime — hỗ trợ 3 loại model:
- linear_regression: regression, dự đoán GIÁ (mô hình gốc)
- xgboost: classification, dự đoán XÁC SUẤT tăng/giảm
- lstm: classification, dự đoán XÁC SUẤT tăng/giảm (cần chuỗi window nến gần nhất)

2 model classification (xgboost/lstm) dùng chung tập đặc trưng cải tiến (features_v2.py,
log-return/stationary) — khác với linear_regression vẫn dùng features.py gốc (15 đặc
trưng, dự đoán giá tuyệt đối) để không phá vỡ khả năng tương thích ngược.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np
import pandas as pd

from app.core.config import settings
from app.services.indicator_service import compute_indicators
from app.services.binance_service import fetch_klines

import sys

_ML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ml"
sys.path.append(str(_ML_DIR))
from features import FEATURE_COLUMNS  # noqa: E402
from features_v2 import FEATURE_COLUMNS_V2, build_v2_feature_frame  # noqa: E402

ARTIFACT_DIR = Path(settings.ML_MODEL_DIR)

_TIMEFRAME_DELTA = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
}

VALID_MODELS = ("linear_regression", "xgboost", "lstm")


def _load_artifact(timeframe: str, model_name: str) -> Dict:
    path = ARTIFACT_DIR / f"{model_name}_{timeframe}.joblib"
    if not path.exists():
        raise FileNotFoundError(
            f"Chưa có model '{model_name}' cho timeframe={timeframe}. Hãy chạy: "
            f"python ml/train_{model_name.replace('linear_regression', 'linear_regression').replace('xgboost','xgboost').replace('lstm','lstm')}.py --timeframe {timeframe}"
        )
    return joblib.load(path)


# ============================================================
# Linear Regression — GIỮ NGUYÊN logic gốc (regression, dự đoán giá)
# ============================================================
async def _predict_linear_regression(timeframe: str, sentiment_score: float,
                                      gold_price, dxy_index, fear_greed) -> Dict:
    artifact = _load_artifact(timeframe, "linear_regression")
    model, scaler = artifact["model"], artifact["scaler"]
    mape = artifact.get("mape", 5.0)
    mae = artifact.get("mae", None)

    candles = await fetch_klines(timeframe=timeframe, limit=60)
    df = compute_indicators(candles)
    last = df.iloc[-1].copy()

    row = {
        "close": last["close"],
        "close_lag_1": df.iloc[-2]["close"],
        "close_lag_2": df.iloc[-3]["close"],
        "close_lag_3": df.iloc[-4]["close"],
        "volume": last["volume"],
        "ema_12": last["ema_12"],
        "ema_26": last["ema_26"],
        "rsi_14": last["rsi_14"],
        "bb_upper": last["bb_upper"],
        "bb_middle": last["bb_middle"],
        "bb_lower": last["bb_lower"],
        "gold_price": gold_price if gold_price is not None else 0.0,
        "dxy_index": dxy_index if dxy_index is not None else 0.0,
        "fear_greed": fear_greed if fear_greed is not None else 50,
        "sentiment_score": sentiment_score,
    }

    X = pd.DataFrame([row])[FEATURE_COLUMNS].values
    X_scaled = scaler.transform(X)
    predicted_price = float(model.predict(X_scaled)[0])
    current_price = float(last["close"])

    change_pct = (predicted_price - current_price) / current_price * 100

    if change_pct > 0:
        trend = "bullish"
    elif change_pct < 0:
        trend = "bearish"
    else:
        trend = "neutral"

    noise_threshold_pct = max(0.02, (mae / current_price) * 100 * 0.5) if mae else 0.15
    signal_ratio = abs(change_pct) / noise_threshold_pct
    base_confidence = max(0.4, min(0.95, 1 - (mape / 100)))
    signal_factor = max(0.3, min(1.0, signal_ratio))
    confidence = max(0.3, min(0.95, base_confidence * signal_factor))

    explanation = (
        f"[Linear Regression] Dự đoán giá {'tăng' if trend == 'bullish' else 'giảm' if trend == 'bearish' else 'đi ngang'} "
        f"khoảng {abs(change_pct):.3f}% so với giá hiện tại. RSI={last['rsi_14']:.1f}, "
        f"sentiment={sentiment_score:.0f}/100. Model dự đoán trực tiếp GIÁ (regression)."
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return {
        "model_name": "linear_regression",
        "model_type": "regression",
        "predicted_at": now,
        "target_time": now + _TIMEFRAME_DELTA[timeframe],
        "current_price": current_price,
        "predicted_price": predicted_price,
        "trend": trend,
        "confidence": round(confidence, 2),
        "explanation": explanation,
    }


# ============================================================
# Tiện ích dùng chung cho XGBoost/LSTM — xây feature v2 từ nến gần nhất
# ============================================================
async def _build_v2_features(timeframe: str, limit: int) -> pd.DataFrame:
    candles = await fetch_klines(timeframe=timeframe, limit=limit)
    df = compute_indicators(candles)
    feature_df = build_v2_feature_frame(df)
    return feature_df


def _trend_from_proba(proba_up: float) -> str:
    if proba_up > 0.5:
        return "bullish"
    if proba_up < 0.5:
        return "bearish"
    return "neutral"


# ============================================================
# XGBoost — classification, dự đoán XÁC SUẤT tăng/giảm
# ============================================================
async def _predict_xgboost(timeframe: str) -> Dict:
    artifact = _load_artifact(timeframe, "xgboost")
    model, scaler = artifact["model"], artifact["scaler"]
    feature_names = artifact["feature_names"]

    feature_df = await _build_v2_features(timeframe, limit=100)
    if len(feature_df) == 0:
        raise ValueError("Không đủ dữ liệu để tính đặc trưng (cần tối thiểu ~30 nến).")

    last_row = feature_df.iloc[[-1]][feature_names].values
    X_scaled = scaler.transform(last_row)
    proba_up = float(model.predict_proba(X_scaled)[0][1])

    current_price = float(feature_df.iloc[-1]["close"])
    trend = _trend_from_proba(proba_up)
    confidence = max(proba_up, 1 - proba_up)  # xác suất của lớp được chọn

    explanation = (
        f"[XGBoost] Xác suất giá TĂNG ở nến kế tiếp: {proba_up * 100:.1f}%. "
        f"Model dự đoán trực tiếp XU HƯỚNG (classification), không dự đoán giá cụ thể. "
        f"CV Accuracy khi train: {artifact.get('cv_accuracy_mean', float('nan')):.1f}%."
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return {
        "model_name": "xgboost",
        "model_type": "classification",
        "predicted_at": now,
        "target_time": now + _TIMEFRAME_DELTA[timeframe],
        "current_price": current_price,
        "predicted_price": None,
        "trend": trend,
        "confidence": round(confidence, 2),
        "explanation": explanation,
    }


# ============================================================
# LSTM — classification, cần chuỗi `window` nến gần nhất
# ============================================================
async def _predict_lstm(timeframe: str) -> Dict:
    meta_path = ARTIFACT_DIR / f"lstm_{timeframe}_meta.joblib"
    model_path = ARTIFACT_DIR / f"lstm_{timeframe}.keras"
    if not meta_path.exists() or not model_path.exists():
        raise FileNotFoundError(
            f"Chưa có model LSTM cho timeframe={timeframe}. Hãy chạy: "
            f"python ml/train_lstm.py --timeframe {timeframe}"
        )

    meta = joblib.load(meta_path)
    scaler = meta["scaler"]
    feature_names = meta["feature_names"]
    window = meta["window"]

    # Cần tối thiểu window + vài chục nến để feature engineering (EMA26, RSI14...) ổn định
    feature_df = await _build_v2_features(timeframe, limit=window + 60)
    if len(feature_df) < window:
        raise ValueError(f"Không đủ dữ liệu để tạo chuỗi {window} bước cho LSTM.")

    # Import trễ để không bắt buộc cài tensorflow nếu chỉ dùng linear_regression/xgboost
    from tensorflow import keras

    model = keras.models.load_model(model_path)

    X_window = feature_df.iloc[-window:][feature_names].values
    X_scaled = scaler.transform(X_window)
    X_seq = X_scaled.reshape(1, window, len(feature_names))

    proba_up = float(model.predict(X_seq, verbose=0).flatten()[0])

    current_price = float(feature_df.iloc[-1]["close"])
    trend = _trend_from_proba(proba_up)
    confidence = max(proba_up, 1 - proba_up)

    explanation = (
        f"[LSTM] Xác suất giá TĂNG ở nến kế tiếp: {proba_up * 100:.1f}% (dựa trên "
        f"chuỗi {window} nến gần nhất). Model dự đoán trực tiếp XU HƯỚNG (classification). "
        f"CV Accuracy khi train: {meta.get('cv_accuracy_mean', float('nan')):.1f}%."
    )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return {
        "model_name": "lstm",
        "model_type": "classification",
        "predicted_at": now,
        "target_time": now + _TIMEFRAME_DELTA[timeframe],
        "current_price": current_price,
        "predicted_price": None,
        "trend": trend,
        "confidence": round(confidence, 2),
        "explanation": explanation,
    }


# ============================================================
# Hàm điều phối chính — router gọi vào đây
# ============================================================
async def predict_next_price(
    timeframe: str,
    model_name: str = "linear_regression",
    sentiment_score: float = 50.0,
    gold_price=None,
    dxy_index=None,
    fear_greed=None,
) -> Dict:
    if model_name not in VALID_MODELS:
        raise ValueError(f"model_name phải là 1 trong {VALID_MODELS}, nhận được: {model_name}")

    if model_name == "linear_regression":
        return await _predict_linear_regression(timeframe, sentiment_score, gold_price, dxy_index, fear_greed)
    elif model_name == "xgboost":
        return await _predict_xgboost(timeframe)
    else:
        return await _predict_lstm(timeframe)
