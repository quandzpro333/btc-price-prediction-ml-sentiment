"""
Huấn luyện mô hình LSTM (Keras/TensorFlow) để DỰ ĐOÁN XU HƯỚNG (tăng/giảm) giá BTC —
bài toán phân loại nhị phân, cùng cách đặt bài toán với train_xgboost.py để so sánh
công bằng giữa 2 model.

Vì sao LSTM thay vì Simple RNN (đã dùng ở train_rnn.py):
- Simple RNN gặp vấn đề vanishing gradient khi chuỗi dài — đã quan sát được trong
  notebook phân tích trước đó (RNN không vượt trội hơn Linear Regression).
- LSTM có cơ chế cổng (gate: forget/input/output) giúp giữ được thông tin qua chuỗi
  dài hơn, là bước nâng cấp kiến trúc hợp lý tiếp theo.

Chạy:
    python train_lstm.py --timeframe 1h --full --window 24 --epochs 20
    python train_lstm.py --timeframe 1h --limit 2000 --window 24 --epochs 15   (nhanh)

Model (.keras) + scaler được lưu vào ml/artifacts/lstm_{timeframe}.*
"""
import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # ẩn bớt log noise của TensorFlow

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import MinMaxScaler

sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.binance_service import fetch_klines, fetch_full_history  # noqa: E402
from app.services.indicator_service import compute_indicators  # noqa: E402
from features_v2 import build_v2_feature_frame, split_v2_classification, FEATURE_COLUMNS_V2  # noqa: E402
from walk_forward import walk_forward_splits  # noqa: E402

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)
DATA_DIR = Path(__file__).parent / "data"


def generate_synthetic_ohlcv(n=3000, start_price=40000.0, seed=42) -> pd.DataFrame:
    """Dữ liệu MÔ PHỎNG — chỉ dùng khi không tải được dữ liệu thật."""
    rng = np.random.default_rng(seed)
    dt = pd.date_range(end=pd.Timestamp.now("UTC").tz_localize(None), periods=n, freq="h")
    returns = rng.normal(loc=0.00005, scale=0.008, size=n)
    shock_idx = rng.choice(n, size=n // 40, replace=False)
    returns[shock_idx] *= rng.uniform(3, 6, size=len(shock_idx))
    close = start_price * np.exp(np.cumsum(returns))
    open_ = np.r_[close[0], close[:-1]]
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.004, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.004, n))
    volume = rng.uniform(500, 5000, n) * (1 + np.abs(returns) * 50)
    return pd.DataFrame({"open_time": dt, "open": open_, "high": high, "low": low,
                          "close": close, "volume": volume})


async def load_candles(timeframe: str, full: bool, limit: int) -> pd.DataFrame:
    try:
        if full:
            csv_path = DATA_DIR / f"btcusdt_{timeframe}_full.csv"
            if csv_path.exists():
                print(f"[1/5] Đọc dữ liệu đầy đủ từ cache: {csv_path}")
                return pd.read_csv(csv_path, parse_dates=["open_time"])
            print("[1/5] Chưa có cache, tải toàn bộ lịch sử từ Binance...")
            candles = await fetch_full_history(timeframe=timeframe)
        else:
            print(f"[1/5] Tải {limit} nến gần nhất từ Binance...")
            candles = await fetch_klines(timeframe=timeframe, limit=limit)
        df = pd.DataFrame(candles)
        print(f"      -> Đã tải {len(df)} nến THẬT từ Binance.")
        return df
    except Exception as exc:
        print(f"      ⚠️  Không tải được dữ liệu thật ({type(exc).__name__}: {exc})")
        print("      -> Dùng dữ liệu MÔ PHỎNG để pipeline vẫn chạy được.")
        return generate_synthetic_ohlcv()


def make_sequences(X: np.ndarray, y: np.ndarray, window: int):
    """Chuyển dữ liệu dạng bảng thành chuỗi (samples, window, features) cho LSTM."""
    Xs, ys = [], []
    for i in range(window, len(X)):
        Xs.append(X[i - window: i])
        ys.append(y[i])
    return np.array(Xs), np.array(ys)


def build_lstm_model(window: int, n_features: int):
    from tensorflow import keras
    from tensorflow.keras import layers

    model = keras.Sequential([
        layers.Input(shape=(window, n_features)),
        layers.LSTM(32, activation="tanh", return_sequences=False),
        layers.Dropout(0.2),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="sigmoid"),  # xác suất tăng giá
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def evaluate_walk_forward(X, y, window: int, n_splits: int, epochs: int) -> pd.DataFrame:
    results = []
    for fold, (train_idx, test_idx) in enumerate(walk_forward_splits(len(X), n_splits=n_splits), 1):
        seq_start = max(0, train_idx[0])
        X_fold = X[seq_start: test_idx[-1] + 1]
        y_fold = y[seq_start: test_idx[-1] + 1]

        scaler = MinMaxScaler().fit(X_fold[: len(train_idx)])
        X_scaled = scaler.transform(X_fold)

        X_seq, y_seq = make_sequences(X_scaled, y_fold, window)
        split_point = len(train_idx) - window
        if split_point <= 0 or split_point >= len(X_seq):
            print(f"      [fold {fold}] Bỏ qua — không đủ dữ liệu cho window={window}.")
            continue

        X_train, X_test = X_seq[:split_point], X_seq[split_point:]
        y_train, y_test = y_seq[:split_point], y_seq[split_point:]
        if len(X_test) == 0 or len(X_train) == 0:
            continue

        model = build_lstm_model(window, X.shape[1])
        model.fit(X_train, y_train, epochs=epochs, batch_size=32, verbose=0)

        y_proba = model.predict(X_test, verbose=0).flatten()
        y_pred = (y_proba > 0.5).astype(int)

        results.append({
            "fold": fold,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "Accuracy (%)": accuracy_score(y_test, y_pred) * 100,
            "Precision": precision_score(y_test, y_pred, zero_division=0),
            "Recall": recall_score(y_test, y_pred, zero_division=0),
            "F1": f1_score(y_test, y_pred, zero_division=0),
            "AUC-ROC": roc_auc_score(y_test, y_proba) if len(set(y_test)) > 1 else float("nan"),
        })
    return pd.DataFrame(results)


def train(timeframe: str, full: bool, limit: int, window: int, epochs: int, n_splits: int):
    candles_df = asyncio.run(load_candles(timeframe, full, limit))

    print("[2/5] Tính chỉ báo kỹ thuật + xây dựng đặc trưng (log-return, stationary)...")
    indicators_df = compute_indicators(candles_df.to_dict("records"))
    feature_df = build_v2_feature_frame(indicators_df)
    print(f"      -> {len(feature_df)} mẫu sau khi làm sạch dữ liệu.")

    X, y = split_v2_classification(feature_df)
    up_ratio = y.mean() * 100
    print(f"      -> Phân phối nhãn: {up_ratio:.1f}% TĂNG / {100 - up_ratio:.1f}% GIẢM")

    print(f"[3/5] Walk-forward cross-validation ({n_splits} fold, window={window}, epochs={epochs})...")
    print("      (huấn luyện mạng nơ-ron tốn thời gian hơn XGBoost nhiều, hãy kiên nhẫn chờ)")
    cv_results = evaluate_walk_forward(X, y, window=window, n_splits=n_splits, epochs=epochs)

    if len(cv_results) == 0:
        print("      ⚠️  Không đủ dữ liệu để chạy walk-forward CV với window/n_splits này.")
        print("          Hãy giảm --n-splits hoặc --window, hoặc tăng --limit/dùng --full.")
        return

    print(cv_results.round(4).to_string(index=False))
    print("\n      Trung bình qua các fold:")
    avg = cv_results[["Accuracy (%)", "Precision", "Recall", "F1", "AUC-ROC"]].mean()
    print(avg.round(4).to_string())

    print("[4/5] Huấn luyện model cuối cùng trên toàn bộ dữ liệu...")
    scaler_full = MinMaxScaler().fit(X)
    X_scaled_full = scaler_full.transform(X)
    X_seq_full, y_seq_full = make_sequences(X_scaled_full, y, window)

    model_full = build_lstm_model(window, X.shape[1])
    model_full.fit(X_seq_full, y_seq_full, epochs=epochs, batch_size=32, verbose=0)

    print("[5/5] Lưu model + scaler...")
    model_path = ARTIFACT_DIR / f"lstm_{timeframe}.keras"
    model_full.save(model_path)

    meta_path = ARTIFACT_DIR / f"lstm_{timeframe}_meta.joblib"
    joblib.dump({
        "scaler": scaler_full,
        "feature_names": FEATURE_COLUMNS_V2,
        "window": window,
        "cv_accuracy_mean": float(avg["Accuracy (%)"]),
        "cv_auc_mean": float(avg["AUC-ROC"]),
        "cv_results": cv_results.to_dict("records"),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(X),
    }, meta_path)

    print(f"      -> Đã lưu model: {model_path}")
    print(f"      -> Đã lưu metadata: {meta_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LSTM cho dự đoán xu hướng BTC")
    parser.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d", "1w"])
    parser.add_argument("--full", action="store_true", help="Dùng toàn bộ lịch sử")
    parser.add_argument("--limit", type=int, default=2000, help="Số nến gần nhất nếu không dùng --full")
    parser.add_argument("--window", type=int, default=24, help="Số bước thời gian nhìn lại")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--n-splits", type=int, default=3, help="Số fold walk-forward CV (LSTM chậm hơn XGBoost nhiều, nên để thấp)")
    args = parser.parse_args()

    train(args.timeframe, args.full, args.limit, args.window, args.epochs, args.n_splits)
