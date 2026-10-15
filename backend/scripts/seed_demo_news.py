"""
Script DEMO — chèn vài tin tức mẫu vào DB, tóm tắt bằng Gemini, để bạn có thể
xem ngay News Feed / AI Analysis mà không cần tích hợp NewsAPI/Twitter thật.

Chạy (từ thư mục backend/, sau khi đã tạo .env với GEMINI_API_KEY):
    python scripts/seed_demo_news.py
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, Base, engine  # noqa: E402
from app.models import orm_models  # noqa: E402
from app.services import gemini_service  # noqa: E402

SAMPLE_NEWS = [
    {
        "source": "CoinDesk",
        "title": "Bitcoin ETF inflows surge as institutional demand grows",
        "url": "https://example.com/news1",
        "content": (
            "Spot Bitcoin ETFs recorded significant net inflows this week as institutional "
            "investors increased exposure to BTC amid growing regulatory clarity."
        ),
    },
    {
        "source": "CoinTelegraph",
        "title": "Analysts warn of short-term BTC correction after rapid rally",
        "url": "https://example.com/news2",
        "content": (
            "Several market analysts caution that Bitcoin's recent rally may face a pullback "
            "as RSI indicators show overbought conditions on higher timeframes."
        ),
    },
    {
        "source": "The Block",
        "title": "Fed signals possible rate pause, crypto markets react cautiously",
        "url": "https://example.com/news3",
        "content": (
            "The Federal Reserve hinted at a pause in rate hikes, leading to mixed reactions "
            "across crypto markets as traders weigh macro implications."
        ),
    },
]


async def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for item in SAMPLE_NEWS:
            try:
                result = await gemini_service.summarize_and_classify_news(item["title"], item["content"])
            except Exception as exc:
                print(f"Bỏ qua (lỗi Gemini): {item['title']} -> {exc}")
                continue

            record = orm_models.News(
                source=item["source"],
                title=item["title"],
                url=item["url"],
                published_at=datetime.utcnow(),
                raw_content=item["content"],
                summary=result.get("summary"),
                sentiment_label=result.get("sentiment_label", "neutral"),
            )
            db.add(record)
            print(f"Đã thêm: {item['title']} -> {result.get('sentiment_label')}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())