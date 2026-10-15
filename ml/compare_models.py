"""
So sánh MAE/MAPE giữa các model đã train ở 3 khung thời gian (1h/4h/1d) —
dùng cho báo cáo/thuyết trình đồ án. Đọc trực tiếp từ file .joblib đã lưu,
KHÔNG train lại, nên chạy rất nhanh.

Chạy (sau khi đã train xong cả 3 timeframe):
    python compare_models.py

Kết quả in ra console dạng bảng, và lưu thêm 1 file Markdown
ml/artifacts/model_comparison.md để copy thẳng vào báo cáo.
"""
from pathlib import Path
import joblib

ARTIFACT_DIR = Path(__file__).parent / "artifacts"
TIMEFRAMES = ["1h", "4h", "1d"]


def main():
    rows = []
    for tf in TIMEFRAMES:
        path = ARTIFACT_DIR / f"linear_regression_{tf}.joblib"
        if not path.exists():
            print(f"[Bỏ qua] Chưa có model cho timeframe={tf} (thiếu file {path.name})")
            continue

        artifact = joblib.load(path)
        rows.append(
            {
                "timeframe": tf,
                "mae": artifact.get("mae", float("nan")),
                "mape": artifact.get("mape", float("nan")),
                "n_train": artifact.get("n_train_samples", "?"),
                "n_test": artifact.get("n_test_samples", "?"),
                "trained_at": artifact.get("trained_at", "?"),
            }
        )

    if not rows:
        print("Chưa train model nào cả. Hãy chạy train_linear_regression.py trước.")
        return

    # In bảng ra console
    print("\n" + "=" * 72)
    print(f"{'Timeframe':<10}{'MAE (USD)':<15}{'MAPE (%)':<12}{'Train':<10}{'Test':<10}")
    print("-" * 72)
    for r in rows:
        print(
            f"{r['timeframe']:<10}{r['mae']:<15,.2f}{r['mape']:<12.2f}"
            f"{str(r['n_train']):<10}{str(r['n_test']):<10}"
        )
    print("=" * 72)

    best = min(rows, key=lambda r: r["mape"])
    print(f"\n-> Timeframe có MAPE thấp nhất (dự đoán chính xác nhất): {best['timeframe']} "
          f"({best['mape']:.2f}%)")

    # Xuất file Markdown để dán thẳng vào báo cáo/slide
    md_lines = [
        "# So sánh model Linear Regression theo khung thời gian",
        "",
        "| Timeframe | MAE (USD) | MAPE (%) | Số mẫu train | Số mẫu test | Thời điểm train |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['timeframe']} | {r['mae']:,.2f} | {r['mape']:.2f} | "
            f"{r['n_train']} | {r['n_test']} | {r['trained_at']} |"
        )
    md_lines.append("")
    md_lines.append(
        f"**Nhận xét:** Khung thời gian **{best['timeframe']}** cho MAPE thấp nhất "
        f"({best['mape']:.2f}%), nghĩa là mô hình Linear Regression dự đoán chính xác nhất "
        f"ở khung này trên tập test (20% dữ liệu cuối, model chưa từng nhìn thấy khi train)."
    )

    out_path = ARTIFACT_DIR / "model_comparison.md"
    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n-> Đã lưu bảng Markdown vào: {out_path}")
    print("   (Mở file này bằng Notepad/VS Code, copy thẳng vào báo cáo Word/Slide)")


if __name__ == "__main__":
    main()
