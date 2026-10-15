"""
Entry point của backend FastAPI.

Chạy dev server:  uvicorn app.main:app --reload --port 8000
Tài liệu Swagger:  http://localhost:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.routers import price, prediction, news, sentiment, dashboard, chat

# Tạo bảng nếu chưa tồn tại (dev only — production nên dùng Alembic migration)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bitcoin Price Prediction API",
    description=(
        "API phục vụ đồ án học tập: dự đoán giá BTC bằng Machine Learning "
        "kết hợp phân tích sentiment. KHÔNG dùng cho giao dịch thật."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(price.router)
app.include_router(prediction.router)
app.include_router(news.router)
app.include_router(sentiment.router)
app.include_router(dashboard.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "message": "Bitcoin Price Prediction API — đồ án học tập, không phải lời khuyên đầu tư.",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
