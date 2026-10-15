# So sánh mô hình cho bài toán dự đoán Bitcoin

## 1) Linear Regression (dự đoán giá)

| Timeframe | MAE (USD) | MAPE (%) | Số mẫu train | Số mẫu test | Thời điểm train |
|---|---|---|---|---|---|
| 1h | 285.73 | 0.32 | 62138 | 15535 | 2026-07-04T07:41:41.155267 |
| 4h | 579.23 | 0.65 | 15536 | 3884 | 2026-07-04T07:41:43.693401 |
| 1d | 1,486.13 | 1.67 | 2578 | 645 | 2026-07-04T07:41:52.118360 |

**Nhận xét:** Khung thời gian **1h** cho MAPE thấp nhất (0.32%), nghĩa là mô hình Linear Regression dự đoán giá khá tốt về mặt sai số tuyệt đối trên tập test. Tuy nhiên, điều này không đồng nghĩa với khả năng dự báo xu hướng giao dịch.

## 2) XGBoost và LSTM (dự đoán xu hướng tăng/giảm)

| Model | Accuracy TB (%) | AUC-ROC TB | Ghi chú |
|---|---:|---:|---|
| XGBoost | 53.34 | 0.5454 | Bài toán phân loại nhị phân: tăng/giảm | 
| LSTM | 51.29 | 0.5180 | Bài toán phân loại nhị phân: tăng/giảm |

**Nhận xét:** Hai mô hình phi tuyến tính này được đánh giá theo Accuracy và AUC-ROC, tập trung vào khả năng dự báo hướng giá (up/down), không thể so sánh trực tiếp với MAE/MAPE của Linear Regression vì mục tiêu khác nhau. Kết quả thực tế cho thấy **XGBoost** đạt độ chính xác hướng gần mức **53.34%**, **LSTM** đạt **51.29%** — cả hai đều chỉ nâng nhẹ so với ngưỡng ngẫu nhiên 50%, cho thấy bài toán BTC vẫn rất khó và đặc trưng thị trường không đủ mạnh để tạo ra tín hiệu có ý nghĩa giao dịch.

**Kết luận chung:** Mô hình hồi quy tuyến tính có sai số giá thấp nhưng không nắm được đúng xu hướng; XGBoost và LSTM cải thiện rất ít trong bài toán phân loại xu hướng, cho thấy thị trường tiền điện tử ở khung 1h vẫn có tính ngẫu nhiên và nhiễu cao. Đây là bằng chứng thực tế cho định hướng báo cáo: cần thêm dữ liệu ngoại sinh, thiết kế chiến lược backtest và tối ưu hóa mô hình theo lợi nhuận, không chỉ dựa trên lỗi thống kê đơn thuần.