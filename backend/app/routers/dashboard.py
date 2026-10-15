from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import orm_models
from app.models.schemas import DashboardResponse
from app.services.backfill_service import backfill_matured_predictions

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Ngưỡng confidence tối thiểu để coi 1 prediction là "đủ tin cậy để đặt lệnh"
# (dùng để tính win_rate/PnL). Xem giải thích chi tiết trong get_dashboard().
MIN_CONFIDENCE_FOR_SIGNAL = 0.5


@router.post("/backfill")
async def trigger_backfill(db: Session = Depends(get_db)):
    """
    Kích hoạt tay việc điền actual_price cho các prediction đã tới target_time.
    GET /api/dashboard cũng tự gọi hàm này mỗi lần load, nên endpoint này chủ yếu
    dùng để test/kiểm tra nhanh mà không cần load lại toàn bộ Dashboard.
    """
    updated = await backfill_matured_predictions(db)
    return {"backfilled": updated}


@router.get("", response_model=DashboardResponse)
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Tính accuracy/win-rate/PnL mô phỏng dựa trên các prediction đã có actual_price.

    QUAN TRỌNG — cách tính đã sửa lại để hợp lý hơn với đặc thù của model Linear
    Regression: vì giá tài chính gần giống random walk, model hồi quy thường dự đoán
    giá kế tiếp RẤT GẦN giá hiện tại (sai số tuyệt đối nhỏ), nhưng điều đó không có
    nghĩa là suy luận hướng tăng/giảm từ 2 con số gần nhau đó là đáng tin cậy.

    Từ khi sửa prediction_service.py, `trend` LUÔN xác định theo dấu +/- của giá dự
    đoán (hầu như không còn "neutral" nữa) — nên không thể dùng trend để lọc tín hiệu
    yếu như trước. Thay vào đó, dùng CONFIDENCE (đã phản ánh biên độ thay đổi so với
    sai số điển hình của model — xem prediction_service.py) làm tiêu chí: chỉ tính
    WIN RATE và PNL trên các prediction có confidence >= MIN_CONFIDENCE_FOR_SIGNAL,
    coi các prediction confidence thấp là "tín hiệu yếu, không đủ để đặt lệnh" —
    giống nhà đầu tư thực tế sẽ đứng ngoài khi tín hiệu không rõ ràng.
    """
    await backfill_matured_predictions(db)

    all_preds = (
        db.query(orm_models.Prediction)
        .filter(orm_models.Prediction.actual_price.isnot(None))
        .all()
    )

    total = len(all_preds)
    if total == 0:
        recent = (
            db.query(orm_models.Prediction)
            .order_by(orm_models.Prediction.predicted_at.desc())
            .limit(10)
            .all()
        )
        return DashboardResponse(
            accuracy=0.0,
            win_rate=0.0,
            total_predictions=0,
            directional_predictions=0,
            neutral_predictions=0,
            recent_predictions=recent,
            simulated_pnl=0.0,
        )

    # --- Độ chính xác GIÁ (accuracy) — tính trên TOÀN BỘ prediction đã có kết quả ---
    total_error_pct = sum(
        abs(p.actual_price - p.predicted_price) / p.current_price for p in all_preds
    )
    accuracy = 1 - (total_error_pct / total)  # 1 - MAPE trung bình, càng gần 1 càng tốt

    # --- Độ chính xác XU HƯỚNG (win_rate) + PnL — chỉ tính trên prediction đủ tin cậy ---
    directional_preds = [p for p in all_preds if (p.confidence or 0) >= MIN_CONFIDENCE_FOR_SIGNAL]
    neutral_count = total - len(directional_preds)

    correct_direction = 0
    simulated_pnl = 0.0

    for p in directional_preds:
        actual_up = p.actual_price > p.current_price
        predicted_up = p.trend == "bullish"

        if predicted_up == actual_up:
            correct_direction += 1

        # PnL mô phỏng: giả lập "đặt lệnh" theo hướng model đã chốt, chỉ với các
        # prediction đủ tin cậy (confidence >= ngưỡng) — bỏ qua tín hiệu yếu.
        direction = 1 if predicted_up else -1
        simulated_pnl += direction * (p.actual_price - p.current_price) / p.current_price

    win_rate = (correct_direction / len(directional_preds)) if directional_preds else 0.0

    recent = (
        db.query(orm_models.Prediction)
        .order_by(orm_models.Prediction.predicted_at.desc())
        .limit(10)
        .all()
    )

    return DashboardResponse(
        accuracy=round(max(0.0, accuracy) * 100, 2),
        win_rate=round(win_rate * 100, 2),
        total_predictions=total,
        directional_predictions=len(directional_preds),
        neutral_predictions=neutral_count,
        recent_predictions=recent,
        simulated_pnl=round(simulated_pnl * 100, 2),  # đơn vị: %
    )
