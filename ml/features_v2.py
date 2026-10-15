"""
Feature engineering PHIÊN BẢN 2 — cải tiến từ features.py gốc, áp dụng đúng bài học
rút ra từ notebook phân tích (analysis.ipynb):

1. Dự đoán LỢI SUẤT LOGARIT (log return) thay vì giá tuyệt đối — giá BTC không dừng
   (non-stationary), dự đoán giá tuyệt đối khiến model dễ đạt sai số thấp "giả tạo"
   bằng cách xấp xỉ giá hiện tại, mà không học được tín hiệu dự báo hướng thật sự.
2. Toàn bộ đặc trưng đều ở dạng TƯƠNG ĐỐI/DỪNG (stationary) — không dùng giá trị
   tuyệt đối (close, volume thô...) làm đặc trưng trực tiếp.
3. Bỏ hẳn các cột placeholder hằng số (gold_price, dxy_index, fear_greed,
   sentiment_score) — dữ liệu hiện chưa tích hợp API thật cho các cột này, đưa
   vào chỉ gây nhiễu (không có phương sai, không mang thông tin).

Dùng chung cho cả 2 hướng bài toán:
- Regression: dự đoán giá trị lợi suất logarit (target_return)
- Classification: dự đoán XÁC SUẤT tăng/giảm (target_direction, 1=tăng, 0=giảm)
  — khuyến nghị dùng cho XGBoost/LSTM vì đây mới là mục tiêu thực sự cần đo
  (Direction Accuracy), thay vì đi vòng qua regression rồi suy ra hướng.
"""
from typing import List, Tuple
import numpy as np
import pandas as pd

# 7 đặc trưng — toàn bộ đều là giá trị TƯƠNG ĐỐI, không phải giá/khối lượng tuyệt đối
FEATURE_COLUMNS_V2: List[str] = [
    "return_lag_1",
    "return_lag_2",
    "log_volume",
    "ema_12_dist",
    "ema_26_dist",
    "rsi_14",
    "bb_pct",
]


def build_v2_feature_frame(indicators_df: pd.DataFrame) -> pd.DataFrame:
    """
    Nhận DataFrame đã có sẵn cột indicator (ema_12, ema_26, rsi_14, bb_upper,
    bb_middle, bb_lower — từ indicator_service.compute_indicators), trả về
    DataFrame đã có đủ FEATURE_COLUMNS_V2 + target_return + target_direction.
    """
    df = indicators_df.copy().sort_values("open_time").reset_index(drop=True)

    # Lợi suất logarit mỗi nến — đại lượng "dừng" (stationary), khác hẳn giá thô
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["return_lag_1"] = df["log_return"].shift(1)
    df["return_lag_2"] = df["log_return"].shift(2)

    # Nén phân phối lệch phải của khối lượng giao dịch
    df["log_volume"] = np.log(df["volume"] + 1)

    # Độ lệch TƯƠNG ĐỐI so với EMA, thay vì dùng trực tiếp giá trị EMA tuyệt đối
    df["ema_12_dist"] = (df["close"] - df["ema_12"]) / df["ema_12"]
    df["ema_26_dist"] = (df["close"] - df["ema_26"]) / df["ema_26"]

    # RSI đã sẵn ở dạng chuẩn hoá 0-100, giữ nguyên
    # Vị trí tương đối trong dải Bollinger Bands (0 = chạm dải dưới, 1 = chạm dải trên)
    bb_range = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_pct"] = (df["close"] - df["bb_lower"]) / bb_range

    # Target: lợi suất logarit của nến KẾ TIẾP (dự đoán 1 bước tới)
    df["target_return"] = df["log_return"].shift(-1)
    # Target phân loại: 1 nếu nến kế tiếp TĂNG, 0 nếu GIẢM/đi ngang
    df["target_direction"] = (df["target_return"] > 0).astype(int)

    df = df.dropna(subset=FEATURE_COLUMNS_V2 + ["target_return"]).reset_index(drop=True)
    return df


def split_v2_regression(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Trả về (X, y) cho bài toán regression — y là lợi suất logarit."""
    X = df[FEATURE_COLUMNS_V2].values
    y = df["target_return"].values
    return X, y


def split_v2_classification(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Trả về (X, y) cho bài toán classification — y là 0/1 (giảm/tăng)."""
    X = df[FEATURE_COLUMNS_V2].values
    y = df["target_direction"].values
    return X, y
