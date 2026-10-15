"""
Lấy dữ liệu nến (OHLCV) BTCUSDT từ Binance public REST API.
Không cần API key vì đây là endpoint public (market data).
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx

from app.core.config import settings

# Binance chỉ chấp nhận các mã interval riêng của họ
_INTERVAL_MAP = {"1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w"}

# BTCUSDT bắt đầu có dữ liệu trên Binance từ khoảng thời điểm này
BTCUSDT_LISTING_DATE = "2017-08-17"


def _parse_klines(raw: list) -> List[Dict]:
    candles = []
    for row in raw:
        # Định dạng Binance kline: [open_time, open, high, low, close, volume, close_time, ...]
        # Binance trả về mốc thời gian UTC (epoch ms). Luôn parse tường minh sang UTC
        # (tz-aware) thay vì fromtimestamp() mặc định (phụ thuộc timezone máy chủ) —
        # để giá trị luôn đúng bất kể server chạy ở đâu. Frontend sẽ tự quy đổi
        # sang giờ Việt Nam (GMT+7) khi hiển thị.
        candles.append(
            {
                "open_time": datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
        )
    return candles


async def fetch_klines(
    symbol: str = None,
    timeframe: str = "1h",
    limit: int = 500,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> List[Dict]:
    """
    Gọi GET /api/v3/klines của Binance (tối đa 1000 nến/lần theo giới hạn của Binance).
    Trả về danh sách dict đã parse: open_time, open, high, low, close, volume.

    start_time/end_time (tuỳ chọn): giới hạn khoảng thời gian lấy dữ liệu.
    Không truyền gì -> mặc định lấy `limit` nến gần nhất tính đến hiện tại.
    """
    symbol = symbol or settings.SYMBOL
    interval = _INTERVAL_MAP.get(timeframe, "1h")

    url = f"{settings.BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if start_time is not None:
        params["startTime"] = int(start_time.timestamp() * 1000)
    if end_time is not None:
        params["endTime"] = int(end_time.timestamp() * 1000)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        raw = resp.json()

    return _parse_klines(raw)


async def fetch_full_history(
    symbol: str = None,
    timeframe: str = "1h",
    start_str: str = BTCUSDT_LISTING_DATE,
) -> List[Dict]:
    """
    Lấy TOÀN BỘ lịch sử nến từ `start_str` (mặc định: ngày BTCUSDT lên sàn Binance)
    cho đến hiện tại, bằng cách gọi lặp lại fetch_klines() theo từng lô 1000 nến
    (giới hạn của Binance) rồi ghép lại.

    Cảnh báo: với khung 1h có thể mất vài chục lần gọi API (~1-2 phút).
    Nên chạy 1 lần rồi lưu ra file (xem ml/fetch_full_history.py) thay vì gọi lại
    mỗi lần train, để tránh tốn thời gian và tránh bị Binance giới hạn tần suất.
    """
    symbol = symbol or settings.SYMBOL
    cursor = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    all_candles: List[Dict] = []

    while True:
        batch = await fetch_klines(symbol=symbol, timeframe=timeframe, limit=1000, start_time=cursor)
        if not batch:
            break

        all_candles.extend(batch)
        last_open_time = batch[-1]["open_time"]

        # Nếu lô trả về ít hơn 1000 nến, nghĩa là đã lấy tới nến gần nhất hiện tại -> dừng
        if len(batch) < 1000:
            break

        # Nến kế tiếp bắt đầu ngay sau nến cuối cùng vừa lấy
        cursor = last_open_time

        # Nghỉ nhẹ giữa các lần gọi để tránh bị Binance giới hạn tần suất (rate limit)
        await asyncio.sleep(0.3)

    # Loại bỏ trùng lặp (nếu có) theo open_time, giữ thứ tự tăng dần
    seen = set()
    deduped = []
    for c in sorted(all_candles, key=lambda x: x["open_time"]):
        if c["open_time"] not in seen:
            seen.add(c["open_time"])
            deduped.append(c)

    return deduped
