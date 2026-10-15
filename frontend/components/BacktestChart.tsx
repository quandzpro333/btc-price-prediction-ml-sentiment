"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType, IChartApi, ISeriesApi } from "lightweight-charts";
import { BacktestResponse } from "@/lib/api";
import PanelEyebrow from "@/components/PanelEyebrow";

interface Props {
  backtest: BacktestResponse;
}

const VN_TIMEZONE = "Asia/Ho_Chi_Minh";
const vnDateTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VN_TIMEZONE,
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export default function BacktestChart({ backtest }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const actualSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const predictedSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Tạo chart 1 lần duy nhất khi mount — tránh huỷ/tạo lại gây giật (giống PriceChart)
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#10151C" },
        textColor: "#E8EDF2",
        fontFamily: "var(--font-mono)",
      },
      grid: {
        vertLines: { color: "#1E2630" },
        horzLines: { color: "#1E2630" },
      },
      width: containerRef.current.clientWidth,
      height: 320,
      timeScale: { timeVisible: true, secondsVisible: false },
      localization: {
        timeFormatter: (time: number) => vnDateTimeFormatter.format(new Date(time * 1000)),
      },
    });
    chartRef.current = chart;

    // Đường giá THỰC TẾ (Ghost Gray) — dữ liệu thật, model chưa từng "nhìn thấy"
    actualSeriesRef.current = chart.addLineSeries({
      color: "#6B7785",
      lineWidth: 2,
      title: "Giá thực tế",
    });
    // Đường giá DỰ ĐOÁN (Amber Alert) — output của model
    predictedSeriesRef.current = chart.addLineSeries({
      color: "#FFB020",
      lineWidth: 2,
      title: "Giá dự đoán",
    });

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      actualSeriesRef.current = null;
      predictedSeriesRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Chỉ cập nhật dữ liệu khi backtest đổi (đổi timeframe) — không tạo lại chart
  useEffect(() => {
    const actualSeries = actualSeriesRef.current;
    const predictedSeries = predictedSeriesRef.current;
    const chart = chartRef.current;
    if (!actualSeries || !predictedSeries || !chart) return;

    const sorted = [...backtest.points].sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );

    actualSeries.setData(
      sorted.map((p) => ({ time: (new Date(p.date).getTime() / 1000) as any, value: p.actual }))
    );
    predictedSeries.setData(
      sorted.map((p) => ({ time: (new Date(p.date).getTime() / 1000) as any, value: p.predicted }))
    );

    chart.timeScale().fitContent();
  }, [backtest]);

  return (
    <div className="border border-border bg-panel p-4 panel-fade-in panel-hover">
      <div className="flex items-center justify-between mb-1">
        <PanelEyebrow>
          Backtest: Dự đoán vs Thực tế · {backtest.timeframe} · {backtest.points.length} mẫu test
        </PanelEyebrow>
        <div className="flex gap-4 text-xs font-mono text-ghost">
          <span>MAE: <span className="text-gray-200">${backtest.mae.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span></span>
          <span>MAPE: <span className="text-gray-200">{backtest.mape.toFixed(2)}%</span></span>
        </div>
      </div>
      <div className="flex gap-4 mb-2 mt-3 text-xs font-mono text-ghost">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-ghost inline-block" /> Giá thực tế
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-amber inline-block" /> Giá dự đoán (model)
        </span>
      </div>
      <div ref={containerRef} className="w-full overflow-hidden" />
      <p className="text-xs text-gray-500 mt-2 font-sans">
        Biểu đồ này so sánh trên tập test (20% dữ liệu cuối, giữ nguyên thứ tự thời gian) —
        model hoàn toàn chưa "nhìn thấy" các điểm này khi huấn luyện, nên đây là thước đo
        khách quan cho khả năng dự đoán thực tế.
      </p>
    </div>
  );
}
