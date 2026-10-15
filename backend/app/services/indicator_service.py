"""
Tính toán các chỉ báo kỹ thuật đơn giản trên chuỗi nến (dùng pandas).

Lưu ý: các khái niệm nâng cao (SMC, Wyckoff, FVG, Order Book, Liquidity)
KHÔNG được tính ở đây — chúng chỉ được diễn giải bằng văn bản qua Gemini
trong AI Analysis, không đưa vào vector đặc trưng của mô hình ML.
"""
from typing import List, Dict, Tuple
import pandas as pd


def compute_indicators(candles: List[Dict]) -> pd.DataFrame:
    """
    Nhận list các nến (dict) đã sắp xếp tăng dần theo thời gian,
    trả về DataFrame có thêm cột EMA/RSI/Bollinger Bands.
    """
    df = pd.DataFrame(candles).sort_values("open_time").reset_index(drop=True)

    # EMA 12 & 26 — dùng cho xu hướng ngắn/dài hạn
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()

    # RSI 14 — Relative Strength Index
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Bollinger Bands (20, 2 độ lệch chuẩn)
    df["bb_middle"] = df["close"].rolling(window=20).mean()
    std20 = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_middle"] + 2 * std20
    df["bb_lower"] = df["bb_middle"] - 2 * std20

    return df


def compute_support_resistance(df: pd.DataFrame, window: int = 20) -> Tuple[float, float]:
    """
    Support/Resistance đơn giản = min/max của N nến gần nhất.
    Đủ dùng cho mục đích minh hoạ trong đồ án; không phải phân tích SMC/Wyckoff chuyên sâu.
    """
    recent = df.tail(window)
    support = float(recent["low"].min())
    resistance = float(recent["high"].max())
    return support, resistance


def compute_trend(df: pd.DataFrame) -> str:
    """
    """
    last = df.iloc[-1]
    if pd.isna(last["ema_12"]) or pd.isna(last["ema_26"]):
        return "neutral"
    if last["ema_12"] > last["ema_26"] * 1.001:
        return "bullish"
    if last["ema_12"] < last["ema_26"] * 0.999:
        return "bearish"
    return "neutral"
