"""
Tích hợp Gemini API — CHỈ dùng để xử lý ngôn ngữ tự nhiên:
- Tóm tắt tin tức
- Phân loại sentiment (Bullish / Bearish / Neutral)
- Sinh báo cáo AI Analysis
- Trả lời chatbot

Gemini KHÔNG được dùng để dự đoán giá số — việc đó thuộc về ml/ (Linear Regression / RNN).

Dùng SDK mới `google-genai` (thư viện `google-generativeai` cũ đã bị Google khai tử).
"""
import asyncio
import json
from typing import Dict, List, Optional

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from app.core.config import settings

_client: Optional[genai.Client] = None

# Các mã lỗi HTTP tạm thời (server quá tải / rate limit) -> nên thử lại thay vì bỏ cuộc luôn
_RETRYABLE_STATUS_CODES = {429, 500, 503, 504}
_MAX_RETRIES = 3
_RETRY_BASE_DELAY_SECONDS = 5  # 5s, 10s, 20s (tăng dần)


def _get_client() -> genai.Client:
    global _client
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "Chưa cấu hình GEMINI_API_KEY trong backend/.env — xem .env.example."
        )
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _clean_json_text(text: str) -> str:
    """Gemini đôi khi bọc JSON trong ```json ... ``` — bóc ra trước khi parse."""
    return text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()


async def _generate_with_retry(prompt: str):
    """
    Gọi Gemini, tự động thử lại (exponential backoff) nếu gặp lỗi tạm thời
    (503 quá tải, 429 rate limit...). Sau _MAX_RETRIES lần vẫn lỗi thì raise ra ngoài
    để nơi gọi (router/script) tự quyết định xử lý tiếp (vd: bỏ qua bài tin đó).
    """
    client = _get_client()
    last_error = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return client.models.generate_content(model=settings.GEMINI_MODEL, contents=prompt)
        except genai_errors.ServerError as exc:
            last_error = exc
            status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if status_code not in _RETRYABLE_STATUS_CODES or attempt == _MAX_RETRIES:
                raise
            delay = _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            print(
                f"      [Gemini] Server đang quá tải ({status_code}), "
                f"thử lại lần {attempt}/{_MAX_RETRIES} sau {delay}s..."
            )
            await asyncio.sleep(delay)

    raise last_error


async def summarize_and_classify_news(title: str, content: str) -> Dict:
    """
    Tóm tắt 1 bài tin tức + phân loại sentiment.
    Trả về dict: {"summary": str, "sentiment_label": "bullish"|"bearish"|"neutral"}
    """
    prompt = f"""Bạn là chuyên gia phân tích thị trường crypto.
Đọc tin tức sau và trả lời CHỈ bằng JSON hợp lệ, không thêm chữ nào khác:
{{"summary": "tóm tắt 2-3 câu bằng tiếng Việt", "sentiment_label": "bullish|bearish|neutral"}}

Tiêu đề: {title}
Nội dung: {content[:2000]}
"""
    response = await _generate_with_retry(prompt)
    text = _clean_json_text(response.text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": text[:300], "sentiment_label": "neutral"}


async def generate_sentiment_score(
    fear_greed: Optional[int],
    news_items: List[Dict],
    trends_score: Optional[float],
) -> Dict:
    """
    Tổng hợp Fear&Greed + tóm tắt tin tức + Google Trends thành 1 điểm sentiment 0-100.
    """
    news_summary = "\n".join(f"- {n.get('summary', n.get('title',''))}" for n in news_items[:10])
    prompt = f"""Bạn là chuyên gia phân tích sentiment thị trường Bitcoin.
Dựa trên dữ liệu sau, hãy trả lời CHỈ bằng JSON hợp lệ:
{{"sentiment_score": số từ 0-100, "sentiment_label": "bullish|bearish|neutral"}}

Fear & Greed Index: {fear_greed}
Google Trends score: {trends_score}
Tóm tắt tin tức gần đây:
{news_summary}
"""
    response = await _generate_with_retry(prompt)
    text = _clean_json_text(response.text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"sentiment_score": 50, "sentiment_label": "neutral"}


async def generate_ai_analysis(context: Dict) -> Dict:
    """
    Sinh báo cáo AI Analysis ngắn gồm: tóm tắt thị trường, xu hướng, tin tức,
    sentiment, nhận xét chỉ báo kỹ thuật.
    `context` chứa: current_price, trend, rsi, ema_12, ema_26, sentiment_score,
    sentiment_label, recent_news_summaries.
    """
    prompt = f"""Bạn là chuyên gia phân tích kỹ thuật crypto, viết báo cáo ngắn gọn bằng tiếng Việt.
Trả lời CHỈ bằng JSON hợp lệ với các trường:
{{"summary": "...", "trend_comment": "...", "news_comment": "...",
  "sentiment_comment": "...", "indicator_comment": "..."}}
Mỗi trường 1-2 câu, súc tích, dễ hiểu cho sinh viên.

Dữ liệu thị trường hiện tại:
{json.dumps(context, ensure_ascii=False, indent=2)}

Lưu ý: đây là nội dung phục vụ mục đích học tập, không phải khuyến nghị đầu tư.
"""
    response = await _generate_with_retry(prompt)
    text = _clean_json_text(response.text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "summary": text[:300],
            "trend_comment": "",
            "news_comment": "",
            "sentiment_comment": "",
            "indicator_comment": "",
        }


async def chat_with_context(user_message: str, context: Dict) -> str:
    """
    Chatbot trả lời câu hỏi của người dùng dựa trên dữ liệu nội bộ hiện có
    (giá hiện tại, RSI, Fear&Greed, dự đoán gần nhất...).
    """
    prompt = f"""Bạn là trợ lý AI của website học tập về dự đoán giá Bitcoin.
Trả lời ngắn gọn, thân thiện, bằng tiếng Việt. Luôn nhắc rằng đây không phải lời khuyên đầu tư
khi câu hỏi liên quan đến quyết định mua/bán.

Dữ liệu hiện có:
{json.dumps(context, ensure_ascii=False, indent=2)}

Câu hỏi của người dùng: {user_message}
"""
    response = await _generate_with_retry(prompt)
    return response.text.strip()    