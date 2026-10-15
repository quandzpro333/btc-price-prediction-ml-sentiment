"""
Cấu hình ứng dụng — đọc từ biến môi trường (.env).
Sinh viên cần tự tạo file backend/.env dựa trên .env.example.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Luôn nạp file backend/.env theo đường dẫn tuyệt đối (không phụ thuộc vào việc
# script được chạy từ thư mục nào — vd: chạy từ backend/, backend/scripts/, hay ml/).
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./btc_prediction.db")

    # Binance
    BINANCE_BASE_URL: str = "https://api.binance.com"
    SYMBOL: str = "BTCUSDT"
    TIMEFRAMES: dict = {"1h": "1h", "4h": "4h", "1d": "1d"}

    # Gemini (Google Generative AI) — dùng cho tóm tắt tin tức, sentiment, chat
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Các API bổ trợ (tuỳ chọn — điền nếu muốn dữ liệu thật)
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    TWITTER_BEARER_TOKEN: str = os.getenv("TWITTER_BEARER_TOKEN", "")

    # Fear & Greed Index — API công khai, miễn phí
    FEAR_GREED_URL: str = "https://api.alternative.me/fng/"

    # ML model paths
    ML_MODEL_DIR: str = os.getenv("ML_MODEL_DIR", "../ml/artifacts")
    ML_DATA_DIR: str = os.getenv("ML_DATA_DIR", "../ml/data")

    # CORS — origin của frontend Next.js khi chạy local
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")


settings = Settings()
