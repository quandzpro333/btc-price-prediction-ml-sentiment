import { PredictionResponse } from "@/lib/api";
import PanelEyebrow from "@/components/PanelEyebrow";
import AnimatedNumber from "@/components/AnimatedNumber";

const trendStyle: Record<string, string> = {
  bullish: "text-bullish",
  bearish: "text-bearish",
  neutral: "text-ghost",
};

const trendLabel: Record<string, string> = {
  bullish: "TĂNG (BULLISH)",
  bearish: "GIẢM (BEARISH)",
  neutral: "ĐI NGANG (NEUTRAL)",
};

const MODEL_LABEL: Record<string, string> = {
  linear_regression: "Linear Regression",
  xgboost: "XGBoost",
  lstm: "LSTM",
};

export default function PredictionCard({ prediction }: { prediction: PredictionResponse }) {
  const isClassification = prediction.model_type === "classification" || prediction.predicted_price === null;
  const changePct =
    !isClassification && prediction.predicted_price !== null
      ? ((prediction.predicted_price - prediction.current_price) / prediction.current_price) * 100
      : null;

  return (
    <div className="border border-border bg-panel p-4 panel-fade-in panel-hover rounded-lg flex flex-col gap-4">
      <PanelEyebrow>
        Prediction · {prediction.timeframe} · {MODEL_LABEL[prediction.model_name] || prediction.model_name}
      </PanelEyebrow>

      {isClassification ? (
        // Sử dụng grid-cols-2 để chia đôi màn hình 50-50
        <div className="grid grid-cols-2 gap-4 items-start">
          
          {/* CỘT 1: GIÁ HIỆN TẠI */}
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-mono uppercase text-ghost tracking-wider">Giá hiện tại</span>
            {/* Cập nhật lên text-2xl để bằng cỡ với bên dự đoán */}
            <span className="text-2xl font-mono font-bold text-white">
              <AnimatedNumber value={prediction.current_price} decimals={2} prefix="$" />
            </span>
          </div>
          
          {/* CỘT 2: DỰ ĐOÁN */}
          <div className={`flex flex-col gap-1 ${trendStyle[prediction.trend]}`}>
            <span className="text-[10px] font-mono uppercase opacity-70 tracking-wider text-ghost">Dự đoán</span>
            <div className="flex items-center gap-1">
              <span className="text-2xl leading-none">
                {prediction.trend === "bullish" ? "▲" : prediction.trend === "bearish" ? "▼" : "·"}
              </span>
              <span className="text-2xl font-mono font-bold leading-none">
                {(prediction.confidence * 100).toFixed(1)}%
              </span>
            </div>
            <span className="text-[10px] font-bold tracking-wide mt-1">
              {trendLabel[prediction.trend]}
            </span>
          </div>

        </div>
      ) : (
        // Khối dành cho Regression (Giữ nguyên cấu trúc grid-cols-2 như trên)
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase text-ghost tracking-wider">Giá hiện tại</span>
              <span className="text-xl font-mono font-bold text-white">
                <AnimatedNumber value={prediction.current_price} decimals={2} prefix="$" />
              </span>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase text-ghost tracking-wider">Giá dự đoán</span>
              <span className={`text-xl font-mono font-bold ${trendStyle[prediction.trend]}`}>
                <AnimatedNumber value={prediction.predicted_price!} decimals={2} prefix="$" />
              </span>
            </div>
          </div>
          
          <div className="flex items-center justify-between font-mono mt-1 pt-3 border-t border-border/50">
            <span className={`text-xs font-bold tracking-wide ${trendStyle[prediction.trend]}`}>
              {trendLabel[prediction.trend]} 
              {changePct !== null && ` (${changePct >= 0 ? "+" : ""}${changePct.toFixed(2)}%)`}
            </span>
            <span className="text-[10px] text-ghost">
              ĐỘ TIN CẬY: {(prediction.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}