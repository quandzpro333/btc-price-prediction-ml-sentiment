"""
Xoá các tin tức DEMO (giả, link https://example.com/...) đã tạo trước đó bằng
seed_demo_news.py — chạy 1 lần để dọn sạch DB, sau đó dùng nút "↻ Cập nhật tin tức"
trên web (hoặc gọi POST /api/news/refresh) để lấy tin THẬT từ CoinDesk.

Chạy (từ thư mục backend/):
    python scripts/clear_demo_news.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.models import orm_models  # noqa: E402


def main():
    db = SessionLocal()
    try:
        deleted = (
            db.query(orm_models.News)
            .filter(orm_models.News.url.like("https://example.com/%"))
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"Đã xoá {deleted} tin demo/giả.")
        print("Bây giờ bấm nút '↻' trên panel News (hoặc gọi POST /api/news/refresh) để lấy tin thật từ CoinDesk.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
