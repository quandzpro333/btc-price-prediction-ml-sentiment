# Bitcoin Price Prediction — Đồ án học tập

Website dự đoán giá BTC (BTCUSDT) bằng Machine Learning (Linear Regression) kết hợp
phân tích sentiment (Gemini API). **Chỉ phục vụ mục đích học tập, không dùng để giao dịch thật.**

Xem `docs/ARCHITECTURE.md` để hiểu kiến trúc tổng thể trước khi cài đặt.

---

## 0. Yêu cầu hệ thống

| Thành phần | Phiên bản khuyến nghị |
|---|---|
| Python | 3.10 – 3.11 |
| Node.js | 18 hoặc 20 (LTS) |
| npm | đi kèm Node.js |
| Hệ điều hành | Windows / macOS / Linux đều được |

Kiểm tra đã cài đúng chưa:
```bash
python3 --version
node --version
npm --version
```

Bạn cũng cần **API key miễn phí của Gemini** (bắt buộc cho AI Analysis, sentiment, chatbot):
1. Vào https://aistudio.google.com/app/apikey
2. Đăng nhập Google → "Create API key" → copy key.

---

## 1. Tải mã nguồn về máy

Giải nén thư mục `btc-prediction/` (đã được tạo sẵn) vào nơi bạn muốn làm việc, ví dụ:
```
btc-prediction/
├── backend/     # FastAPI + services
├── frontend/    # Next.js
├── ml/          # training scripts (Linear Regression / RNN)
├── database/    # schema.sql
└── docs/        # kiến trúc, tài liệu
```

---

## 2. Cài đặt Backend (FastAPI)

### 2.1. Tạo môi trường ảo Python
```bash
cd btc-prediction/backend
python3 -m venv venv

# Kích hoạt venv:
source venv/bin/activate          # macOS/Linux
venv\Scripts\activate             # Windows (PowerShell/CMD)
```

### 2.2. Cài thư viện
```bash
pip install -r requirements.txt
```

### 2.3. Cấu hình biến môi trường
```bash
cp .env.example .env
```
Mở file `.env` vừa tạo và điền:
```
GEMINI_API_KEY=dán_api_key_bạn_vừa_lấy_ở_bước_0
```
Các biến còn lại (`NEWS_API_KEY`, `TWITTER_BEARER_TOKEN`, giá vàng, DXY) là **tuỳ chọn** —
để trống vẫn chạy được, chỉ là các trường đó sẽ trả về `null`/giá trị mặc định.

### 2.4. Database
Không cần làm gì thêm — SQLite sẽ tự tạo file `btc_prediction.db` và các bảng
(theo `database/schema.sql`) ngay khi backend khởi động lần đầu (xem `app/main.py`).

> Nếu muốn xem trước schema hoặc chạy bằng tay: `sqlite3 btc_prediction.db < ../database/schema.sql`

### 2.5. Chạy backend
```bash
uvicorn app.main:app --reload --port 8000
```
Kiểm tra:
- http://localhost:8000/health → `{"status": "ok"}`
- http://localhost:8000/docs → Swagger UI, thử trực tiếp các API tại đây.

**Giữ terminal này chạy** — mở terminal mới cho các bước tiếp theo.

---

## 3. Huấn luyện mô hình Machine Learning (bắt buộc trước khi dùng Prediction)

Mở terminal mới:
```bash
cd btc-prediction/ml
# Vẫn dùng venv của backend (đã có sklearn, pandas...):
source ../backend/venv/bin/activate     # macOS/Linux
..\backend\venv\Scripts\activate        # Windows

python train_linear_regression.py --timeframe 1h --limit 1000
```
Script sẽ:
1. Tải 1000 nến 1h gần nhất từ Binance (cần internet, không cần API key).
2. Tính chỉ báo kỹ thuật, xây feature matrix.
3. Train Linear Regression, in ra MAE/MAPE.
4. Lưu model vào `ml/artifacts/linear_regression_1h.joblib`.

Lặp lại cho các khung thời gian còn lại để Prediction Card hoạt động đủ cả 3 tab:
```bash
python train_linear_regression.py --timeframe 4h --limit 1000
python train_linear_regression.py --timeframe 1d --limit 1000
```

### 3.1. (Tuỳ chọn) Train trên TOÀN BỘ lịch sử BTCUSDT từ khi lên sàn (2017)

Mặc định script trên chỉ lấy 1000 nến gần nhất. Nếu muốn train trên **toàn bộ lịch sử**
(từ ~17/08/2017 đến hiện tại), làm 2 bước:

```bash
# Bước 1: tải toàn bộ lịch sử về, lưu ra CSV (chỉ cần chạy 1 lần, mất 1-2 phút/timeframe)
python fetch_full_history.py --timeframe 1h
python fetch_full_history.py --timeframe 4h
python fetch_full_history.py --timeframe 1d

# Bước 2: train dùng dữ liệu đầy đủ vừa tải (thêm cờ --full)
python train_linear_regression.py --timeframe 1h --full
python train_linear_regression.py --timeframe 4h --full
python train_linear_regression.py --timeframe 1d --full
```
File CSV được lưu tại `ml/data/btcusdt_{timeframe}_full.csv` — có thể mở bằng Excel để xem thử.
Lần sau train lại chỉ cần chạy lại bước 2 (không cần tải lại từ Binance).

> Muốn thử **Simple RNN** thay vì Linear Regression: `pip install tensorflow` rồi chạy
> `python train_rnn.py --timeframe 1h --limit 1000`. Lưu ý: backend hiện đọc model
> `linear_regression_*`; nếu dùng RNN, cần sửa `app/services/prediction_service.py`
> để load `.h5` tương ứng (phần này để mở cho sinh viên tự mở rộng theo đồ án).

---

## 4. (Tuỳ chọn) Nạp dữ liệu tin tức + sentiment mẫu

Để News Feed / AI Analysis có dữ liệu ngay khi demo (thay vì tích hợp NewsAPI/Twitter thật):
```bash
cd btc-prediction/backend
python scripts/seed_demo_news.py      # chèn 3 tin mẫu, tóm tắt bằng Gemini
```
Sau đó gọi 1 lần để sinh sentiment tổng hợp:
```bash
curl -X POST http://localhost:8000/api/sentiment/refresh
```

---

## 5. Cài đặt Frontend (Next.js)

Mở terminal mới:
```bash
cd btc-prediction/frontend
npm install
```

Frontend mặc định gọi backend qua proxy rewrite (`/backend-api/*` → `http://localhost:8000/api/*`,
xem `next.config.js`), nên **không bắt buộc** phải tạo `.env.local`. Nếu bạn deploy backend
ở nơi khác, xem `.env.local.example`.

Chạy dev server:
```bash
npm run dev
```
Mở trình duyệt: http://localhost:3000

---

## 6. Thứ tự chạy tổng hợp (mỗi lần mở máy lên)

```bash
# Terminal 1 — Backend
cd btc-prediction/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd btc-prediction/frontend
npm run dev
```
Truy cập http://localhost:3000 — nếu mọi thứ đúng, bạn sẽ thấy:
- Biểu đồ nến BTCUSDT thật từ Binance.
- Prediction Card (nếu đã train model ở bước 3).
- AI Analysis (nếu đã điền `GEMINI_API_KEY`).
- News Feed (nếu đã seed dữ liệu ở bước 4).
- Fear & Greed gauge (tự lấy từ alternative.me, không cần key).
- AI Chat ở cuối trang.

---

## 7. Các lỗi thường gặp

| Triệu chứng | Nguyên nhân & cách sửa |
|---|---|
| Trang trắng, lỗi CORS trong console | Backend chưa chạy, hoặc `FRONTEND_ORIGIN` trong `.env` không khớp `http://localhost:3000` |
| Prediction Card báo "chưa khả dụng" | Chưa chạy `train_linear_regression.py` cho timeframe đang chọn (bước 3) |
| AI Analysis / AI Chat báo lỗi 503 | Chưa điền `GEMINI_API_KEY` trong `backend/.env`, hoặc key sai/hết quota |
| `ModuleNotFoundError` khi chạy backend | Quên `source venv/bin/activate` trước khi `pip install` / `uvicorn` |
| Biểu đồ không hiện nến | Kiểm tra http://localhost:8000/api/price?timeframe=1h trực tiếp — nếu lỗi là do Binance API bị chặn ở mạng bạn đang dùng (một số quốc gia/ISP chặn Binance), thử VPN |
| `npm install` báo lỗi phiên bản Node | Cài Node 18/20 LTS qua https://nodejs.org hoặc dùng `nvm` |

---

## 8. Các bước tiếp theo bạn có thể tự mở rộng cho đồ án

Phần khung (scaffold) này đã hoàn chỉnh về kiến trúc, DB, API, ML baseline và giao diện —
đủ để chạy demo. Các phần sau **để mở** cho sinh viên tự làm sâu hơn tuỳ đồ án:

1. Tích hợp NewsAPI/X (Twitter) thật thay vì dữ liệu mẫu (`app/services/market_context_service.py`, `scripts/seed_demo_news.py`).
2. Tích hợp API giá vàng/DXY thật (GoldAPI.io, Twelve Data...).
3. Google Trends (thư viện `pytrends`).
4. Worker nền (APScheduler đã có trong `requirements.txt`) để tự động: cào tin tức mỗi giờ,
   refresh sentiment, điền `actual_price` vào bảng `predictions` sau khi `target_time` trôi qua
   (để Dashboard tính accuracy/win-rate chính xác theo thời gian thực).
5. Trang đăng nhập/đăng ký người dùng (bảng `users` đã có sẵn).
6. Heatmap đơn giản, Whale News (hiện chưa có UI riêng, có thể thêm component mới trong `frontend/components/`).
7. Nếu muốn thử Simple RNN thay Linear Regression: xem ghi chú ở mục 3.

Chúc bạn hoàn thành đồ án tốt! 🚀
