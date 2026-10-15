"""
Tải lịch sử nến BTCUSDT từ Binance và lưu ra CSV trong ml/data/.

CHẠY LẦN ĐẦU (tải toàn bộ lịch sử từ ~2017-08-17 đến hiện tại):
    python fetch_full_history.py --timeframe 1h

CHẠY LẠI SAU NÀY (vd: 1 tuần sau) để CẬP NHẬT nến mới mà KHÔNG tải lại từ đầu:
    python fetch_full_history.py --timeframe 1h
    (script tự phát hiện file CSV đã có, chỉ tải phần nến mới kể từ lần chạy trước,
     rồi nối thêm vào cuối file — nhanh hơn nhiều so với tải lại toàn bộ)

Muốn ép tải lại từ đầu (bỏ qua dữ liệu cũ, ví dụ nghi ngờ file bị lỗi):
    python fetch_full_history.py --timeframe 1h --force-full
"""
import argparse
import asyncio
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.binance_service import fetch_full_history, fetch_klines, BTCUSDT_LISTING_DATE  # noqa: E402

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def main(timeframe: str, start_str: str, force_full: bool):
    out_path = DATA_DIR / f"btcusdt_{timeframe}_full.csv"

    if out_path.exists() and not force_full:
        # ĐÃ CÓ DỮ LIỆU CŨ -> chỉ tải phần nến MỚI kể từ nến cuối cùng đã lưu
        old_df = pd.read_csv(out_path, parse_dates=["open_time"])
        last_time = old_df["open_time"].max()
        print(f"Đã có {len(old_df)} nến cũ, mới nhất tới: {last_time}")
        print("Đang tải các nến MỚI kể từ thời điểm đó...")

        new_candles = asyncio.run(
            fetch_klines(timeframe=timeframe, limit=1000, start_time=last_time)
        )
        new_df = pd.DataFrame(new_candles)

        # Gộp cũ + mới, loại trùng theo open_time, giữ thứ tự thời gian tăng dần
        combined = pd.concat([old_df, new_df]).drop_duplicates(subset="open_time")
        combined = combined.sort_values("open_time").reset_index(drop=True)

        added = len(combined) - len(old_df)
        print(f"-> Thêm được {added} nến mới.")
        df = combined
    else:
        # CHƯA CÓ DỮ LIỆU (hoặc ép --force-full) -> tải toàn bộ từ đầu
        print(f"Đang tải TOÀN BỘ lịch sử BTCUSDT khung {timeframe} từ {start_str} đến hiện tại...")
        print("(có thể mất 1-2 phút tuỳ khung thời gian, vì Binance giới hạn 1000 nến/lần gọi)")
        candles = asyncio.run(fetch_full_history(timeframe=timeframe, start_str=start_str))
        df = pd.DataFrame(candles)

    df.to_csv(out_path, index=False)
    print(f"-> Tổng cộng {len(df)} nến.")
    print(f"-> Khoảng thời gian: {df['open_time'].min()} -> {df['open_time'].max()}")
    print(f"-> Đã lưu vào: {out_path}")
    print()
    print("Lưu ý: sau khi cập nhật dữ liệu, nhớ TRAIN LẠI model để model học dữ liệu mới nhất:")
    print(f"    python train_linear_regression.py --timeframe {timeframe} --full")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tải/cập nhật lịch sử nến BTCUSDT từ Binance")
    parser.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d", "1w"])
    parser.add_argument(
        "--start",
        default=BTCUSDT_LISTING_DATE,
        help="Ngày bắt đầu lấy dữ liệu khi tải mới hoàn toàn, định dạng YYYY-MM-DD",
    )
    parser.add_argument(
        "--force-full",
        action="store_true",
        help="Bỏ qua dữ liệu CSV cũ (nếu có), tải lại toàn bộ từ đầu",
    )
    args = parser.parse_args()

    main(args.timeframe, args.start, args.force_full)
