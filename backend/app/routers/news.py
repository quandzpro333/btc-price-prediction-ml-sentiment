from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import orm_models
from app.models.schemas import NewsItem
from app.services import gemini_service, market_context_service

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("", response_model=List[NewsItem])
async def get_news(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Trả về danh sách tin tức đã thu thập + tóm tắt/sentiment (lưu trong bảng `news`,
    được nạp bằng cách gọi POST /api/news/refresh — xem hàm bên dưới).
    """
    items = (
        db.query(orm_models.News)
        .order_by(orm_models.News.published_at.desc())
        .limit(limit)
        .all()
    )
    return items


@router.post("/refresh")
async def refresh_news(
    limit: int = Query(5, ge=1, le=20, description="Số bài tin mới tối đa lấy về mỗi lần"),
    db: Session = Depends(get_db),
):
    """
    Lấy tin tức MỚI từ RSS công khai của CoinDesk (chỉ giữ bài về Bitcoin/BTC),
    tóm tắt + phân loại sentiment bằng Gemini, rồi lưu vào bảng `news`.

    - Bỏ qua các bài đã có trong DB (kiểm tra theo URL, tránh trùng lặp).
    - Mặc định chỉ lấy 5 bài/lần để tiết kiệm quota Gemini (mỗi bài mới = 1 lần gọi
      Gemini để tóm tắt) — tăng lên tối đa 20 nếu cần qua query param `limit`.
    """
    articles = await market_context_service.fetch_coindesk_btc_news(limit=limit)

    added = 0
    skipped_existing = 0
    for item in articles:
        if item["url"]:
            exists = db.query(orm_models.News).filter(orm_models.News.url == item["url"]).first()
            if exists:
                skipped_existing += 1
                continue

        try:
            result = await gemini_service.summarize_and_classify_news(item["title"], item["raw_content"])
        except Exception:
            # Gemini lỗi/hết quota -> vẫn lưu bài tin (không có summary/sentiment) thay vì bỏ hẳn
            result = {"summary": None, "sentiment_label": "neutral"}

        record = orm_models.News(
            source=item["source"],
            title=item["title"],
            url=item["url"],
            published_at=item["published_at"],
            raw_content=item["raw_content"],
            summary=result.get("summary"),
            sentiment_label=result.get("sentiment_label", "neutral"),
        )
        db.add(record)
        added += 1

    if added:
        db.commit()

    return {
        "fetched_from_coindesk": len(articles),
        "added": added,
        "skipped_existing": skipped_existing,
    }
