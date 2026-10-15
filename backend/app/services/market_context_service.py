"""
Lấy các dữ liệu bổ trợ để phân tích xu hướng/sentiment:
- Fear & Greed Index: API công khai alternative.me (miễn phí, không cần key)
- Tin tức: RSS công khai của CoinDesk (miễn phí, không cần key), lọc riêng tin về Bitcoin/BTC
- Giá vàng (XAU/USD) & chỉ số DXY: cần API tài chính riêng (vd: Twelve Data, Alpha Vantage).
  Ở đây để dạng "pluggable" — sinh viên điền API key thật vào .env nếu muốn dữ liệu live;
  nếu không có key, hàm trả về None và hệ thống vẫn hoạt động bình thường (bỏ qua feature đó).

Lưu ý về Fear & Greed: Binance KHÔNG có API công khai riêng cho chỉ số này — chỉ số
"Crypto Fear & Greed Index" phổ biến nhất (được hầu hết app, bot, kể cả các trang tham
chiếu tới "Binance-style" F&G) đều lấy từ alternative.me, nên đây vẫn là nguồn chuẩn nhất.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional

import httpx

from app.core.config import settings

COINDESK_RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"
# Từ khoá dùng để lọc riêng tin về Bitcoin/BTC trong feed chung của CoinDesk
# (CoinDesk đưa tin nhiều loại coin khác nhau, không phải feed riêng cho BTC)
_BTC_KEYWORDS = ("bitcoin", "btc")


def _strip_html(text: str) -> str:
    """Bỏ tag HTML còn lẫn trong <description> của RSS, chỉ giữ text thuần."""
    return re.sub(r"<[^>]+>", "", text or "").strip()


async def fetch_fear_greed_index() -> Optional[int]:
    """Trả về giá trị Fear & Greed hiện tại (0-100), hoặc None nếu lỗi."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(settings.FEAR_GREED_URL, params={"limit": 1})
            resp.raise_for_status()
            data = resp.json()
            return int(data["data"][0]["value"])
    except Exception:
        return None


async def fetch_coindesk_btc_news(limit: int = 10) -> List[Dict]:
    """
    Lấy tin tức từ RSS công khai của CoinDesk (https://www.coindesk.com/arc/outboundfeeds/rss/),
    chỉ giữ lại các bài có nhắc tới Bitcoin/BTC (kiểm tra title, description, category).

    Trả về list dict: {source, title, url, published_at, raw_content}
    Không cần API key — đây là RSS feed công khai chính thức của CoinDesk.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(COINDESK_RSS_URL)
            resp.raise_for_status()
            xml_text = resp.text
    except Exception:
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    results: List[Dict] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = _strip_html(item.findtext("description") or "")
        categories = [c.text.strip().lower() for c in item.findall("category") if c.text]
        pub_date_raw = item.findtext("pubDate")

        haystack = f"{title} {description} {' '.join(categories)}".lower()
        if not any(kw in haystack for kw in _BTC_KEYWORDS):
            continue  # bỏ qua tin không liên quan Bitcoin (ETH, altcoin, chính sách chung...)

        try:
            published_at = parsedate_to_datetime(pub_date_raw) if pub_date_raw else None
            if published_at and published_at.tzinfo:
                published_at = published_at.replace(tzinfo=None)  # đồng bộ naive-UTC như phần còn lại của app
        except Exception:
            published_at = None

        results.append(
            {
                "source": "CoinDesk",
                "title": title,
                "url": link,
                "published_at": published_at or datetime.utcnow(),
                "raw_content": description[:2000],
            }
        )
        if len(results) >= limit:
            break

    return results


async def fetch_gold_price() -> Optional[float]:
    """
    Placeholder — cần tích hợp API tài chính thật (vd: Twelve Data, GoldAPI.io).
    Trả về None nếu chưa cấu hình, để không làm crash hệ thống.
    """
    # TODO (sinh viên): tích hợp GoldAPI.io hoặc Twelve Data ở đây bằng API key riêng.
    return None


async def fetch_dxy_index() -> Optional[float]:
    """
    Placeholder — chỉ số DXY thường lấy từ nguồn dữ liệu tài chính trả phí/miễn phí có giới hạn.
    """
    # TODO (sinh viên): tích hợp Twelve Data / Alpha Vantage ở đây.
    return None
