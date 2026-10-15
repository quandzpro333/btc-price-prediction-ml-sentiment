"""
Thiết lập SQLAlchemy engine/session cho SQLite.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency dùng trong FastAPI route: yield 1 session rồi tự đóng."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
