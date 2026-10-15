"""
Huấn luyện mô hình XGBoost để DỰ ĐOÁN XU HƯỚNG (tăng/giảm) giá BTC — bài toán phân
loại nhị phân, thay vì regression rồi suy ra hướng như Linear Regression cũ.

Vì sao XGBoost cho đồ án môn học:
- Chạy nhanh trên CPU (vài giây - vài chục giây), không cần GPU.
- Không bị ảnh hưởng bởi đa cộng tuyến (multicollinearity) giữa các chỉ báo kỹ thuật
  như model tuyến tính — đúng vấn đề ablation study trước đây đã phát hiện.
- Có sẵn feature_importances_, dễ diễn giải cho báo cáo.

Chạy:
    python train_xgboost.py --timeframe 1h --full
    python train_xgboost.py --timeframe 1h --limit 1000   (nhanh, dữ liệu gần nhất)

Model + kết quả walk-forward CV được lưu vào ml/artifacts/xgboost_{timeframe}.joblib
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.binance_service import fetch_klines, fetch_full_history  # noqa: E402
from app.services.indicator_service import compute_indicators  # noqa: E402
from features_v2 import build_v2_feature_frame, split_v2_classification, FEATURE_COLUMNS_V2  # noqa: E402
from walk_forward import walk_forward_splits  # noqa: E402

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
ARTIFACT_DIR.mkdir(exist_ok=True)
DATA_DIR = Path(__file__).parent / "data"


def generate_synthetic_ohlcv(n=3000, start_price=40000.0, seed=42) -> pd.DataFrame:
    """Dữ liệu MÔ PHỎNG — chỉ dùng khi không tải được dữ liệu thật, để pipeline vẫn
    chạy được end-to-end (xem giải thích tương tự trong ml/analysis.ipynb)."""
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
                print(f"[1/4] Đọc dữ liệu đầy đủ từ cache: {csv_path}")
                return pd.read_csv(csv_path, parse_dates=["open_time"])
            print("[1/4] Chưa có cache, tải toàn bộ lịch sử từ Binance...")
            candles = await fetch_full_history(timeframe=timeframe)
        else:
            print(f"[1/4] Tải {limit} nến gần nhất từ Binance...")
            candles = await fetch_klines(timeframe=timeframe, limit=limit)
        df = pd.DataFrame(candles)
        print(f"      -> Đã tải {len(df)} nến THẬT từ Binance.")
        return df
    except Exception as exc:
        print(f"      ⚠️  Không tải được dữ liệu thật ({type(exc).__name__}: {exc})")
        print("      -> Dùng dữ liệu MÔ PHỎNG để pipeline vẫn chạy được.")
        return generate_synthetic_ohlcv()


def evaluate_walk_forward(X: np.ndarray, y: np.ndarray, n_splits: int = 5) -> pd.DataFrame:
    results = []
    for fold, (train_idx, test_idx) in enumerate(walk_forward_splits(len(X), n_splits=n_splits), 1):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        scaler = StandardScaler().fit(X_train)
        model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            random_state=42,
        )
        model.fit(scaler.transform(X_train), y_train)

        y_pred = model.predict(scaler.transform(X_test))
        y_proba = model.predict_proba(scaler.transform(X_test))[:, 1]

        results.append({
            "fold": fold,
            "n_train": len(train_idx),
            "n_test": len(test_idx),
            "Accuracy (%)": accuracy_score(y_test, y_pred) * 100,
            "Precision": precision_score(y_test, y_pred, zero_division=0),
            "Recall": recall_score(y_test, y_pred, zero_division=0),
            "F1": f1_score(y_test, y_pred, zero_division=0),
            "AUC-ROC": roc_auc_score(y_test, y_proba) if len(set(y_test)) > 1 else float("nan"),
        })
    return pd.DataFrame(results)


def train(timeframe: str, full: bool, limit: int, n_splits: int):
    candles_df = asyncio.run(load_candles(timeframe, full, limit))

    print("[2/4] Tính chỉ báo kỹ thuật + xây dựng đặc trưng (log-return, stationary)...")
    indicators_df = compute_indicators(candles_df.to_dict("records"))
    feature_df = build_v2_feature_frame(indicators_df)
    print(f"      -> {len(feature_df)} mẫu sau khi làm sạch dữ liệu.")

    X, y = split_v2_classification(feature_df)
    up_ratio = y.mean() * 100
    print(f"      -> Phân phối nhãn: {up_ratio:.1f}% TĂNG / {100 - up_ratio:.1f}% GIẢM")

    print(f"[3/4] Walk-forward cross-validation ({n_splits} fold)...")
    cv_results = evaluate_walk_forward(X, y, n_splits=n_splits)
    print(cv_results.round(4).to_string(index=False))
    print("\n      Trung bình qua các fold:")
    avg = cv_results[["Accuracy (%)", "Precision", "Recall", "F1", "AUC-ROC"]].mean()
    print(avg.round(4).to_string())

    print("[4/4] Huấn luyện model cuối cùng trên toàn bộ dữ liệu + lưu artifact...")
    scaler_full = StandardScaler().fit(X)
    model_full = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, eval_metric="logloss", random_state=42,
    )
    model_full.fit(scaler_full.transform(X), y)

    importance_df = pd.DataFrame({
        "feature": FEATURE_COLUMNS_V2,
        "importance": model_full.feature_importances_,
    }).sort_values("importance", ascending=False)
    print("\n      Feature importance:")
    print(importance_df.to_string(index=False))

    artifact_path = ARTIFACT_DIR / f"xgboost_{timeframe}.joblib"
    joblib.dump({
        "model": model_full,
        "scaler": scaler_full,
        "feature_names": FEATURE_COLUMNS_V2,
        "cv_accuracy_mean": float(avg["Accuracy (%)"]),
        "cv_auc_mean": float(avg["AUC-ROC"]),
        "cv_results": cv_results.to_dict("records"),
        "feature_importance": importance_df.to_dict("records"),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(X),
    }, artifact_path)
    print(f"      -> Đã lưu: {artifact_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost cho dự đoán xu hướng BTC")
    parser.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d", "1w"])
    parser.add_argument("--full", action="store_true", help="Dùng toàn bộ lịch sử (cần fetch_full_history.py trước, hoặc tự tải)")
    parser.add_argument("--limit", type=int, default=1000, help="Số nến gần nhất nếu không dùng --full")
    parser.add_argument("--n-splits", type=int, default=5, help="Số fold walk-forward CV")
    args = parser.parse_args()

    train(args.timeframe, args.full, args.limit, args.n_splits)
