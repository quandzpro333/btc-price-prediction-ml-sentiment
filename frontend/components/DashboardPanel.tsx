"use client";

import { useState } from "react";
import { DashboardResponse, triggerBackfill } from "@/lib/api";
import PanelEyebrow from "@/components/PanelEyebrow";
import { showToast } from "@/lib/toast";

const VN_TIMEZONE = "Asia/Ho_Chi_Minh";
const vnDateTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VN_TIMEZONE,
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

function StatTile({
  label,
  value,
  colorClass = "text-white",
  sublabel,
}: {
  label: string;
  value: string;
  colorClass?: string;
  sublabel?: string;
}) {
  return (
    <div className="border border-border p-3">
      <p className="text-[10px] font-mono uppercase tracking-wider text-ghost mb-1">{label}</p>
      <p className={`text-xl font-mono font-bold ${colorClass}`}>{value}</p>
      {sublabel && <p className="text-[10px] font-mono text-ghost mt-0.5">{sublabel}</p>}
    </div>
  );
}

export default function DashboardPanel({
  dashboard,
  onRefresh,
}: {
  dashboard: DashboardResponse;
  onRefresh: () => void;
}) {
  const [refreshing, setRefreshing] = useState(false);

  const handleBackfill = async () => {
    setRefreshing(true);
    try {
      const result = await triggerBackfill();
      onRefresh();
      if (result.backfilled > 0) {
        showToast(`Đã cập nhật kết quả cho ${result.backfilled} prediction`, "success");
      } else {
        showToast("Chưa có prediction nào đủ thời gian để cập nhật", "info");
      }
    } catch {
      showToast("Không cập nhật được — kiểm tra kết nối/backend", "error");
    } finally {
      setRefreshing(false);
    }
  };

  const pnlColor = dashboard.simulated_pnl >= 0 ? "text-bullish" : "text-bearish";
  const neutralPct =
    dashboard.total_predictions > 0
      ? ((dashboard.neutral_predictions / dashboard.total_predictions) * 100).toFixed(0)
      : "0";

  return (
    <div className="border border-border bg-panel p-4 panel-fade-in panel-hover">
      <div className="flex items-center justify-between mb-3">
        <PanelEyebrow>Dashboard · Lịch sử &amp; Hiệu suất dự đoán</PanelEyebrow>
        <button
          onClick={handleBackfill}
          disabled={refreshing}
          className="text-[10px] font-mono uppercase border border-border text-ghost hover:text-bullish hover:border-bullish px-2 py-1 disabled:opacity-50"
        >
          {refreshing ? "Đang cập nhật..." : "↻ Cập nhật kết quả"}
        </button>
      </div>

      {/* Tách bạch rõ 2 khái niệm khác nhau: độ chính xác GIÁ vs độ chính xác XU HƯỚNG.
          Trước đây 2 con số này bị gộp lẫn gây hiểu nhầm — giờ hiển thị riêng, kèm giải
          thích ngắn ngay dưới mỗi ô để không ai nhầm "sai số giá thấp" với "đoán đúng hướng". */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-2">
        <StatTile
          label="Độ chính xác GIÁ"
          value={`${dashboard.accuracy.toFixed(1)}%`}
          sublabel="1 − sai số giá TB"
        />
        <StatTile
          label="Độ chính xác XU HƯỚNG"
          value={dashboard.directional_predictions > 0 ? `${dashboard.win_rate.toFixed(1)}%` : "—"}
          sublabel={`trên ${dashboard.directional_predictions} lần có tín hiệu rõ`}
          colorClass={dashboard.win_rate >= 50 ? "text-bullish" : "text-bearish"}
        />
        <StatTile
          label="Tín hiệu yếu"
          value={`${neutralPct}%`}
          sublabel={`${dashboard.neutral_predictions}/${dashboard.total_predictions} lần confidence < 50%`}
        />
        <StatTile
          label="PnL mô phỏng"
          value={`${dashboard.simulated_pnl >= 0 ? "+" : ""}${dashboard.simulated_pnl.toFixed(2)}%`}
          colorClass={pnlColor}
          sublabel="chỉ tính lần có tín hiệu rõ"
        />
      </div>

      <p className="text-[10px] text-gray-500 font-sans mb-4 border-l-2 border-border pl-2">
        <strong className="text-gray-300">Độ chính xác GIÁ</strong> đo model dự đoán giá gần đúng
        thực tế tới mức nào (sai số tuyệt đối) — với dữ liệu tài chính, số này thường CAO một
        cách "giả tạo" vì giá hiện tại luôn là chỉ báo tốt cho giá kế tiếp. Vì vậy{" "}
        <strong className="text-gray-300">Win Rate/PnL chỉ tính trên các lần model có độ tin
        cậy (confidence) từ 50% trở lên</strong> — model LUÔN xác định hướng tăng/giảm theo dấu
        giá dự đoán, nhưng khi biên độ thay đổi quá nhỏ (trong phạm vi sai số điển hình của
        model), confidence sẽ thấp và bị loại khỏi tính toán, giống việc đứng ngoài khi tín
        hiệu không đủ rõ.
      </p>

      {dashboard.total_predictions === 0 ? (
        <p className="text-xs text-ghost font-mono border border-border p-3">
          Chưa có dữ liệu — Dashboard chỉ tính được sau khi ít nhất 1 prediction đã "chín"
          (qua target_time) và được tự động điền giá thực tế. Hãy dùng Prediction Card một vài
          lần rồi quay lại đây sau (vd: 1 giờ sau với timeframe 1h).
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-ghost uppercase text-[10px] border-b border-border">
                <th className="text-left py-1.5 pr-3">Thời điểm</th>
                <th className="text-left py-1.5 pr-3">TF</th>
                <th className="text-right py-1.5 pr-3">Giá lúc dự đoán</th>
                <th className="text-right py-1.5 pr-3">Giá dự đoán</th>
                <th className="text-right py-1.5 pr-3">Giá thực tế</th>
                <th className="text-center py-1.5 pr-3">Tín hiệu</th>
                <th className="text-center py-1.5">Kết quả</th>
              </tr>
            </thead>
            <tbody>
              {dashboard.recent_predictions.map((p, i) => {
                const hasActual = p.actual_price !== null && p.actual_price !== undefined;
                // Khớp với MIN_CONFIDENCE_FOR_SIGNAL ở backend (dashboard.py) — trend giờ
                // hầu như luôn có hướng (bullish/bearish), nên dùng confidence để xác định
                // đây có phải "tín hiệu đủ mạnh để tính vào win-rate/PnL" hay không.
                const isDirectional = p.confidence >= 0.5;
                const actualUp = hasActual ? p.actual_price! > p.current_price : null;
                const correct =
                  hasActual && isDirectional ? (p.trend === "bullish") === actualUp : null;

                return (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-1.5 pr-3 text-gray-300">
                      {vnDateTimeFormatter.format(new Date(p.predicted_at))}
                    </td>
                    <td className="py-1.5 pr-3 text-ghost">{p.timeframe}</td>
                    <td className="py-1.5 pr-3 text-right text-gray-300">
                      ${p.current_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-1.5 pr-3 text-right text-gray-300">
                      ${p.predicted_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-1.5 pr-3 text-right text-gray-300">
                      {hasActual ? `$${p.actual_price!.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
                    </td>
                    <td className="py-1.5 pr-3 text-center">
                      <span className={p.trend === "bullish" ? "text-bullish" : p.trend === "bearish" ? "text-bearish" : "text-ghost"}>
                        {p.trend === "bullish" ? "▲ TĂNG" : p.trend === "bearish" ? "▼ GIẢM" : "· —"}
                      </span>
                      <span className="text-ghost ml-1">({(p.confidence * 100).toFixed(0)}%)</span>
                    </td>
                    <td className="py-1.5 text-center">
                      {!hasActual ? (
                        <span className="text-ghost">Chờ kết quả</span>
                      ) : !isDirectional ? (
                        <span className="text-ghost">Tín hiệu yếu</span>
                      ) : correct ? (
                        <span className="text-bullish">✓ ĐÚNG</span>
                      ) : (
                        <span className="text-bearish">✗ SAI</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-[10px] text-gray-600 mt-3 font-sans">
        PnL mô phỏng giả lập việc "đặt lệnh" theo các lần model đưa ra tín hiệu tăng/giảm rõ ràng
        — chỉ mang tính minh hoạ học thuật, không phải lời khuyên đầu tư.
      </p>
    </div>
  );
}
