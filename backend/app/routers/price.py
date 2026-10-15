from pathlib import Path
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.services.binance_service import fetch_klines
from app.services.indicator_service import compute_indicators, compute_support_resistance, compute_trend
from app.models.schemas import PriceResponse
from app.core.config import settings

router = APIRouter(prefix="/api/price", tags=["price"])

DATA_DIR = Path(settings.ML_DATA_DIR)


@router.get("", response_model=PriceResponse)
async def get_price(
    timeframe: str = Query("1h", pattern="^(1h|4h|1d|1w)$"),
    limit: int = Query(200, ge=50, le=1000),
    full: bool = Query(
        False,
        description=(
            "True = đọc TOÀN BỘ lịch sử từ file CSV cache (ml/data/, tạo bằng "
            "fetch_full_history.py) thay vì chỉ lấy `limit` nến gần nhất từ Binance."
        ),
    ),
):
    """
    Trả về chuỗi nến BTCUSDT kèm chỉ báo kỹ thuật, support/resistance, trend.

    - full=false (mặc định): gọi Binance trực tiếp, lấy `limit` nến gần nhất (nhanh, luôn mới).
    - full=true: đọc từ file CSV đã tải sẵn bằng `python ml/fetch_full_history.py --timeframe {tf}`
      (không gọi Binance mỗi lần load trang — tránh chậm và tránh bị giới hạn tần suất khi
      hiển thị toàn bộ lịch sử, vốn có thể lên tới hàng chục nghìn nến với khung 1h).
    """
    if full:
        csv_path = DATA_DIR / f"btcusdt_{timeframe}_full.csv"
        if not csv_path.exists():
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Chưa có dữ liệu lịch sử đầy đủ cho timeframe={timeframe}. Hãy chạy trước:\n"
                    f"python ml/fetch_full_history.py --timeframe {timeframe}"
                ),
            )
        candles_df = pd.read_csv(csv_path, parse_dates=["open_time"])
        candles = candles_df.to_dict("records")
    else:
        try:
            candles = await fetch_klines(timeframe=timeframe, limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Không lấy được dữ liệu từ Binance: {exc}")

    df = compute_indicators(candles)
    support, resistance = compute_support_resistance(df)
    trend = compute_trend(df)

    return PriceResponse(
        symbol=settings.SYMBOL,
        timeframe=timeframe,
        candles=df.to_dict("records"),
        support=support,
        resistance=resistance,
        trend=trend,
    )
