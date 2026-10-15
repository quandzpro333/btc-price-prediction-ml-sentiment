"""
So sánh nhanh tất cả model đã train cho cùng 1 timeframe — đọc trực tiếp từ các file
artifact đã lưu, KHÔNG train lại, nên chạy rất nhanh. Dùng cho báo cáo Project 2.

Chạy (sau khi đã train xong các model muốn so sánh):
    python compare_all_models.py --timeframe 1h
"""
import argparse
from pathlib import Path

import joblib

ARTIFACT_DIR = Path(__file__).parent / "artifacts"


def main(timeframe: str):
    print("=" * 78)
    print(f"SO SÁNH MODEL — timeframe = {timeframe}")
    print("=" * 78)

    # ---- Linear Regression (regression, đo bằng MAE/MAPE) ----
    lr_path = ARTIFACT_DIR / f"linear_regression_{timeframe}.joblib"
    if lr_path.exists():
        a = joblib.load(lr_path)
        print(f"\n[Linear Regression]  (bài toán: regression — dự đoán GIÁ)")
        print(f"  MAE  : {a.get('mae', float('nan')):.2f} USD")
        print(f"  MAPE : {a.get('mape', float('nan')):.2f} %")
        print(f"  Số mẫu train/test: {a.get('n_train_samples', '?')}/{a.get('n_test_samples', '?')}")
    else:
        print(f"\n[Linear Regression]  Chưa train (thiếu {lr_path.name})")

    # ---- XGBoost (classification, đo bằng Accuracy/AUC) ----
    xgb_path = ARTIFACT_DIR / f"xgboost_{timeframe}.joblib"
    if xgb_path.exists():
        a = joblib.load(xgb_path)
        print(f"\n[XGBoost]  (bài toán: classification — dự đoán XU HƯỚNG, walk-forward CV)")
        print(f"  Accuracy TB : {a.get('cv_accuracy_mean', float('nan')):.2f} %")
        print(f"  AUC-ROC TB  : {a.get('cv_auc_mean', float('nan')):.4f}")
        print(f"  Số mẫu      : {a.get('n_samples', '?')}")
        top_features = a.get("feature_importance", [])[:3]
        if top_features:
            names = ", ".join(f['feature'] for f in top_features)
            print(f"  Top 3 đặc trưng quan trọng nhất: {names}")
    else:
        print(f"\n[XGBoost]  Chưa train (thiếu {xgb_path.name})")

    # ---- LSTM (classification, đo bằng Accuracy/AUC) ----
    lstm_meta_path = ARTIFACT_DIR / f"lstm_{timeframe}_meta.joblib"
    if lstm_meta_path.exists():
        a = joblib.load(lstm_meta_path)
        print(f"\n[LSTM]  (bài toán: classification — dự đoán XU HƯỚNG, walk-forward CV)")
        print(f"  Accuracy TB : {a.get('cv_accuracy_mean', float('nan')):.2f} %")
        print(f"  AUC-ROC TB  : {a.get('cv_auc_mean', float('nan')):.4f}")
        print(f"  Window      : {a.get('window', '?')} bước thời gian")
        print(f"  Số mẫu      : {a.get('n_samples', '?')}")
    else:
        print(f"\n[LSTM]  Chưa train (thiếu {lstm_meta_path.name})")

    print("\n" + "=" * 78)
    print("Lưu ý: Linear Regression đo bằng MAE/MAPE (sai số GIÁ), còn XGBoost/LSTM")
    print("đo bằng Accuracy/AUC-ROC (đúng/sai XU HƯỚNG) — không so sánh trực tiếp 2")
    print("loại chỉ số này với nhau. Muốn so Linear Regression theo Direction Accuracy,")
    print("xem lại phần Walk-Forward CV trong ml/analysis.ipynb (đã tính sẵn ~49.3%).")
    print("=" * 78)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="So sánh các model đã train")
    parser.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d", "1w"])
    args = parser.parse_args()
    main(args.timeframe)
