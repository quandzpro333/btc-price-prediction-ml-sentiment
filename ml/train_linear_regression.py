"""
Huấn luyện mô hình Linear Regression để dự đoán giá đóng cửa BTC bước kế tiếp.

Chạy với 1000 nến gần nhất (nhanh, gọi trực tiếp Binance):
    python train_linear_regression.py --timeframe 1h --limit 1000

Chạy với TOÀN BỘ lịch sử (cần chạy fetch_full_history.py --timeframe 1h trước):
    python train_linear_regression.py --timeframe 1h --full

Model + scaler được lưu vào ml/artifacts/linear_regression_{timeframe}.joblib
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Cho phép import từ backend/app khi chạy script này độc lập
sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.binance_service import fetch_klines  # noqa: E402
from app.services.indicator_service import compute_indicators  # noqa: E402
from features import build_feature_frame, split_features_target, FEATURE_COLUMNS  # noqa: E402

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)
DATA_DIR = Path(__file__).parent / "data"


async def load_training_data(timeframe: str, limit: int, full: bool):
    if full:
        csv_path = DATA_DIR / f"btcusdt_{timeframe}_full.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"Chưa có file {csv_path}. Hãy chạy trước:\n"
                f"    python fetch_full_history.py --timeframe {timeframe}"
            )
        candles_df = pd.read_csv(csv_path, parse_dates=["open_time"])
        candles = candles_df.to_dict("records")
    else:
        candles = await fetch_klines(timeframe=timeframe, limit=limit)

    df = compute_indicators(candles)
    # sentiment_score mặc định 50 (trung lập) khi train offline;
    # khi phục vụ dự đoán realtime, backend sẽ truyền sentiment_score thật.
    df = build_feature_frame(df, sentiment_score=50.0)
    return df


def train(timeframe: str, limit: int, full: bool):
    source_desc = "TOÀN BỘ lịch sử (file CSV)" if full else f"{limit} nến gần nhất (Binance API)"
    print(f"[1/4] Tải dữ liệu {source_desc}, khung {timeframe}...")
    df = asyncio.run(load_training_data(timeframe, limit, full))
    print(f"      -> {len(df)} mẫu sau khi làm sạch dữ liệu.")

    X, y = split_features_target(df)

    print("[2/4] Chia tập train/test (80/20, giữ thứ tự thời gian)...")
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print("[3/4] Chuẩn hoá đặc trưng và huấn luyện Linear Regression...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LinearRegression()
    model.fit(X_train_scaled, y_train)

    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    mape = mean_absolute_percentage_error(y_test, y_pred) * 100

    print(f"      -> MAE  = {mae:,.2f} USD")
    print(f"      -> MAPE = {mape:.2f} %")

    print("[4/4] Lưu model + scaler + dữ liệu backtest (test set thực tế vs dự đoán)...")
    # Lưu thêm ngày/giá thực/giá dự đoán của TẬP TEST (20% dữ liệu cuối, model chưa
    # từng "nhìn thấy" khi train) — dùng để vẽ biểu đồ "Dự đoán vs Thực tế" trên web,
    # và lưu hệ số (coef_/intercept_) để phục vụ trang giải thích model (Model Explainability).
    test_dates = df["open_time"].iloc[split_idx:].reset_index(drop=True)

    artifact_path = ARTIFACT_DIR / f"linear_regression_{timeframe}.joblib"
    joblib.dump(
        {
            "model": model,
            "scaler": scaler,
            "mae": mae,
            "mape": mape,
            "feature_names": FEATURE_COLUMNS,
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
            "trained_at": datetime.utcnow().isoformat(),
            "n_train_samples": len(X_train),
            "n_test_samples": len(X_test),
            "backtest_dates": test_dates.astype(str).tolist(),
            "backtest_actual": y_test.tolist(),
            "backtest_predicted": y_pred.tolist(),
        },
        artifact_path,
    )
    print(f"      -> Đã lưu: {artifact_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Linear Regression cho dự đoán giá BTC")
    parser.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d", "1w"])
    parser.add_argument("--limit", type=int, default=1000, help="Số nến lấy từ Binance (tối đa 1000, bỏ qua nếu dùng --full)")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Dùng toàn bộ lịch sử đã tải sẵn bằng fetch_full_history.py thay vì gọi Binance trực tiếp",
    )
    args = parser.parse_args()

    train(args.timeframe, args.limit, args.full)
