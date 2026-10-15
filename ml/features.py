"""
Xây dựng đặc trưng (features) đầu vào cho mô hình dự đoán giá Bitcoin.

Đầu vào mô hình (đúng theo yêu cầu đồ án):
- Giá BTC trong quá khứ     
- Volume
- EMA (12, 26)
- RSI (14)
- Bollinger Bands (upper, middle, lower)
- Giá vàng (gold_price)      -> có thể NaN nếu chưa cấu hình API, sẽ được fillna
- DXY (dxy_index)            -> tương tự
- Fear & Greed Index
- Sentiment score tổng hợp

Đầu ra: giá Bitcoin dự đoán ở bước thời gian kế tiếp (target = close.shift(-1)).
"""
from typing import List, Tuple
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "close",
    "close_lag_1",
    "close_lag_2",
    "close_lag_3",
    "volume",
    "ema_12",
    "ema_26",
    "rsi_14",
    "bb_upper",
    "bb_middle",
    "bb_lower",
    "gold_price",
    "dxy_index",
    "fear_greed",
    "sentiment_score",
]


def build_feature_frame(df: pd.DataFrame, sentiment_score: float = 50.0) -> pd.DataFrame:
    """
    Nhận DataFrame market_data (đã có indicator) + điểm sentiment,
    trả về DataFrame đầy đủ FEATURE_COLUMNS + cột target.

    df cần có tối thiểu các cột: open_time, close, volume, ema_12, ema_26,
    rsi_14, bb_upper, bb_middle, bb_lower. gold_price/dxy_index/fear_greed
    có thể thiếu -> sẽ được điền giá trị mặc định hợp lý.
    """
    df = df.copy().sort_values("open_time").reset_index(drop=True)

    df["close_lag_1"] = df["close"].shift(1)
    df["close_lag_2"] = df["close"].shift(2)
    df["close_lag_3"] = df["close"].shift(3)

    for col in ["gold_price", "dxy_index", "fear_greed"]:
        if col not in df.columns:
            df[col] = np.nan
        if df[col].notna().any():
            # Có ít nhất 1 giá trị thật -> điền giá trị thiếu bằng ffill rồi lấy trung bình
            df[col] = df[col].ffill().fillna(df[col].mean())
        else:
            # Cột toàn NaN (chưa tích hợp API giá vàng/DXY/Fear&Greed thật)
            # -> điền giá trị mặc định trung lập, KHÔNG dùng .mean() vì mean() của
            #    toàn NaN cũng ra NaN, khiến dropna() sau đó xoá sạch dữ liệu.
            default_value = 50.0 if col == "fear_greed" else 0.0
            df[col] = default_value

    df["sentiment_score"] = sentiment_score

    # Target: giá đóng cửa của nến kế tiếp (dự đoán 1 bước tới)
    df["target"] = df["close"].shift(-1)

    df = df.dropna(subset=FEATURE_COLUMNS + ["target"]).reset_index(drop=True)
    return df


def split_features_target(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    X = df[FEATURE_COLUMNS].values
    y = df["target"].values
    return X, y
