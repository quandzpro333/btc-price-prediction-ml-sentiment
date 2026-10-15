"""
[TUỲ CHỌN] Huấn luyện Simple RNN (Keras/TensorFlow) — chỉ 1 lớp RNN đơn giản,
thay thế cho Linear Regression nếu muốn thử mô hình chuỗi thời gian.

Yêu cầu: pip install tensorflow

Chạy: python train_rnn.py --timeframe 1h --limit 1000 --window 24

Model + scaler lưu vào ml/artifacts/simple_rnn_{timeframe}.h5 / .joblib
"""
import argparse
import asyncio
import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import MinMaxScaler

sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.binance_service import fetch_klines  # noqa: E402
from app.services.indicator_service import compute_indicators  # noqa: E402
from features import build_feature_frame, split_features_target, FEATURE_COLUMNS  # noqa: E402

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)


def make_sequences(X: np.ndarray, y: np.ndarray, window: int):
    """Chuyển dữ liệu dạng bảng thành chuỗi (samples, window, features) cho RNN."""
    Xs, ys = [], []
    for i in range(window, len(X)):
        Xs.append(X[i - window : i])
        ys.append(y[i])
    return np.array(Xs), np.array(ys)


async def load_training_data(timeframe: str, limit: int):
    candles = await fetch_klines(timeframe=timeframe, limit=limit)
    df = compute_indicators(candles)
    df = build_feature_frame(df, sentiment_score=50.0)
    return df


def train(timeframe: str, limit: int, window: int, epochs: int):
    # Import trễ để người không dùng RNN không bắt buộc cài tensorflow
    from tensorflow import keras
    from tensorflow.keras import layers

    print(f"[1/5] Tải dữ liệu {limit} nến khung {timeframe} từ Binance...")
    df = asyncio.run(load_training_data(timeframe, limit))
    X, y = split_features_target(df)
    print(f"      -> {len(X)} mẫu.")

    print("[2/5] Chuẩn hoá dữ liệu (MinMaxScaler)...")
    scaler_X = MinMaxScaler()
    scaler_y = MinMaxScaler()
    X_scaled = scaler_X.fit_transform(X)
    y_scaled = scaler_y.fit_transform(y.reshape(-1, 1)).flatten()

    print(f"[3/5] Tạo chuỗi thời gian (window={window})...")
    X_seq, y_seq = make_sequences(X_scaled, y_scaled, window)
    split_idx = int(len(X_seq) * 0.8)
    X_train, X_test = X_seq[:split_idx], X_seq[split_idx:]
    y_train, y_test = y_seq[:split_idx], y_seq[split_idx:]

    print("[4/5] Xây dựng & huấn luyện Simple RNN (1 lớp)...")
    model = keras.Sequential(
        [
            layers.Input(shape=(window, len(FEATURE_COLUMNS))),
            layers.SimpleRNN(32, activation="tanh"),
            layers.Dense(16, activation="relu"),
            layers.Dense(1),
        ]
    )
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    model.fit(
        X_train,
        y_train,
        validation_data=(X_test, y_test),
        epochs=epochs,
        batch_size=32,
        verbose=1,
    )

    print("[5/5] Lưu model + scalers...")
    model.save(ARTIFACT_DIR / f"simple_rnn_{timeframe}.h5")
    joblib.dump(
        {"scaler_X": scaler_X, "scaler_y": scaler_y, "window": window},
        ARTIFACT_DIR / f"simple_rnn_{timeframe}_scalers.joblib",
    )
    print("      -> Hoàn tất.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Simple RNN cho dự đoán giá BTC")
    parser.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d", "1w"])
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--window", type=int, default=24, help="Số bước thời gian nhìn lại")
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()

    train(args.timeframe, args.limit, args.window, args.epochs)
