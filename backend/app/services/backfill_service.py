"""
Backfill actual_price cho các prediction đã tới target_time nhưng chưa có kết quả thật.

Thay vì cần 1 worker chạy nền riêng (APScheduler + luôn phải chạy song song), cách
đơn giản và đủ dùng cho đồ án học tập là chạy backfill này "lazy" — mỗi khi có ai
gọi GET /api/dashboard, hệ thống tự tranh thủ tìm và điền các prediction đã đến hạn.
Luôn cho kết quả mới nhất mỗi khi người dùng mở Dashboard, không cần quản lý thêm
1 tiến trình nền phức tạp.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import orm_models
from app.services.binance_service import fetch_klines

# Giới hạn số lượng xử lý mỗi lần gọi — tránh 1 lần load Dashboard phải gọi Binance
# hàng trăm lần nếu tồn đọng quá nhiều prediction chưa backfill.
MAX_BACKFILL_PER_CALL = 50


async def get_actual_price_at(timeframe: str, at_time: datetime) -> Optional[float]:
    """
    Lấy giá đóng cửa THẬT gần nhất với thời điểm `at_time` — dùng làm "kết quả thực tế"
    để so sánh với giá đã dự đoán trước đó.

    Toàn bộ datetime trong app này là naive nhưng theo QUY ƯỚC luôn đại diện cho giờ UTC
    (xem prediction_service.py dùng datetime.utcnow()). Khi gọi Binance cần timestamp
    tuyệt đối, nên phải gắn tzinfo=UTC một cách tường minh trước khi tính epoch —
    nếu không, .timestamp() sẽ hiểu nhầm theo giờ local của máy chủ (lỗi lệch múi giờ
    tương tự đã gặp trước đây).
    """
    if at_time.tzinfo is None:
        at_time = at_time.replace(tzinfo=timezone.utc)

    try:
        candles = await fetch_klines(timeframe=timeframe, limit=2, start_time=at_time)
    except Exception:
        return None

    if not candles:
        return None

    # Nến đầu tiên có open_time >= at_time -> giá `close` của nến này là xấp xỉ tốt
    # nhất cho "giá thực tế tại thời điểm target_time".
    return candles[0]["close"]


async def backfill_matured_predictions(db: Session) -> int:
    """
    Tìm các prediction đã tới target_time nhưng actual_price còn NULL, gọi Binance
    để lấy giá thật tại thời điểm đó, rồi cập nhật vào DB.

    Trả về số lượng prediction đã backfill thành công trong lần gọi này.
    """
    now = datetime.utcnow()  # naive, theo quy ước đại diện cho UTC (giống nơi khác trong app)

    pending = (
        db.query(orm_models.Prediction)
        .filter(
            orm_models.Prediction.actual_price.is_(None),
            orm_models.Prediction.target_time <= now,
        )
        .order_by(orm_models.Prediction.target_time.asc())
        .limit(MAX_BACKFILL_PER_CALL)
        .all()
    )

    updated = 0
    for pred in pending:
        actual = await get_actual_price_at(pred.timeframe, pred.target_time)
        if actual is not None:
            pred.actual_price = actual
            updated += 1

    if updated:
        db.commit()

    return updated
