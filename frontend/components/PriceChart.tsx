"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  IChartApi,
  ISeriesApi,
  IPriceLine,
} from "lightweight-charts";
import { Candle, Timeframe } from "@/lib/api";

interface Props {
  candles: Candle[];
  support?: number;
  resistance?: number;
  timeframe: Timeframe;
  symbol?: string; // mặc định BTCUSDT
}

// Kline WebSocket public của Binance — không cần API key, ai cũng gọi được.
// Docs: https://binance-docs.github.io/apidocs/spot/en/#kline-candlestick-streams
function buildBinanceWsUrl(symbol: string, timeframe: Timeframe) {
  return `wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${timeframe}`;
}

const VN_TIMEZONE = "Asia/Ho_Chi_Minh";

// Luôn định dạng theo giờ Việt Nam (GMT+7), KHÔNG phụ thuộc timezone của máy/trình
// duyệt người xem — dùng Intl.DateTimeFormat với timeZone cố định thay vì để trình
// duyệt tự suy ra giờ local (dễ sai nếu máy cài nhầm múi giờ khác).
const vnTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VN_TIMEZONE,
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const vnDateTimeFormatter = new Intl.DateTimeFormat("vi-VN", {
  timeZone: VN_TIMEZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

export default function PriceChart({ candles, support, resistance, timeframe, symbol = "BTCUSDT" }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const supportLineRef = useRef<IPriceLine | null>(null);
  const resistanceLineRef = useRef<IPriceLine | null>(null);
  const [isLive, setIsLive] = useState(false);

  // ===== EFFECT 1: Khởi tạo chart — CHỈ CHẠY 1 LẦN DUY NHẤT khi component mount =====
  // Đây là điểm mấu chốt để chart mượt: không huỷ/tạo lại canvas mỗi khi đổi timeframe,
  // chỉ tạo object chart + series một lần, giữ nguyên suốt vòng đời component.
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
      height: 420,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: (time: number) => vnTimeFormatter.format(new Date(time * 1000)),
      },
      localization: {
        timeFormatter: (time: number) => vnDateTimeFormatter.format(new Date(time * 1000)),
      },
    });
    chartRef.current = chart;

    candleSeriesRef.current = chart.addCandlestickSeries({
      upColor: "#00FF9C",
      downColor: "#FF3B5C",
      borderVisible: false,
      wickUpColor: "#00FF9C",
      wickDownColor: "#FF3B5C",
    });

    emaSeriesRef.current = chart.addLineSeries({ color: "#FFB020", lineWidth: 1 });

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
      candleSeriesRef.current = null;
      emaSeriesRef.current = null;
      supportLineRef.current = null;
      resistanceLineRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // <-- mount duy nhất 1 lần, KHÔNG phụ thuộc candles/timeframe

  // ===== EFFECT 2: Cập nhật DỮ LIỆU khi candles/support/resistance đổi =====
  // Chỉ gọi setData() trên series đã có sẵn — mượt hơn nhiều so với tạo lại chart.
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const emaSeries = emaSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !emaSeries || !chart) return;

    candleSeries.setData(
      candles.map((c) => ({
        time: (new Date(c.open_time).getTime() / 1000) as any,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    emaSeries.setData(
      candles
        .filter((c) => c.ema_12 !== undefined && c.ema_12 !== null)
        .map((c) => ({ time: (new Date(c.open_time).getTime() / 1000) as any, value: c.ema_12! }))
    );

    // Xoá price line cũ trước khi vẽ line mới — nếu không sẽ bị cộng dồn qua mỗi lần đổi timeframe
    if (supportLineRef.current) {
      candleSeries.removePriceLine(supportLineRef.current);
      supportLineRef.current = null;
    }
    if (resistanceLineRef.current) {
      candleSeries.removePriceLine(resistanceLineRef.current);
      resistanceLineRef.current = null;
    }
    if (support) {
      supportLineRef.current = candleSeries.createPriceLine({
        price: support,
        color: "#00FF9C",
        lineStyle: 2,
        title: "Support",
      });
    }
    if (resistance) {
      resistanceLineRef.current = candleSeries.createPriceLine({
        price: resistance,
        color: "#FF3B5C",
        lineStyle: 2,
        title: "Resistance",
      });
    }

    // Tự động fit lại phạm vi hiển thị cho vừa dữ liệu mới (vd đổi từ 1h sang 1w,
    // khoảng giá/thời gian rất khác nhau) — nếu không chart sẽ giữ zoom cũ, nhìn sai lệch.
    chart.timeScale().fitContent();
  }, [candles, support, resistance]);

  // ===== EFFECT 3: Kết nối WebSocket Binance để cập nhật nến hiện tại theo thời gian thực =====
  useEffect(() => {
    const ws = new WebSocket(buildBinanceWsUrl(symbol, timeframe));

    ws.onopen = () => setIsLive(true);
    ws.onclose = () => setIsLive(false);
    ws.onerror = () => setIsLive(false);

    let lastBarTime = candles.length > 0
      ? Math.floor(new Date(candles[candles.length - 1].open_time).getTime() / 1000)
      : 0;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      const k = msg.k;
      if (!k || !candleSeriesRef.current) return;

      const barTime = Math.floor(k.t / 1000);

      // lightweight-charts chỉ chấp nhận update() cho nến CÓ time >= nến cuối cùng
      // đã vẽ. Nếu WebSocket trả về 1 nến cũ hơn (lệch timezone, hoặc do vừa đổi
      // timeframe khiến dữ liệu cũ/mới lẫn lộn), bỏ qua thay vì để lỗi crash UI.
      if (barTime < lastBarTime) return;
      lastBarTime = barTime;

      candleSeriesRef.current.update({
        time: barTime as any,
        open: parseFloat(k.o),
        high: parseFloat(k.h),
        low: parseFloat(k.l),
        close: parseFloat(k.c),
      });
    };

    return () => {
      ws.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, timeframe]);

  return (
    <div className="relative">
      <div
        className={`absolute top-2 right-2 z-10 flex items-center gap-1.5 bg-panel/90 backdrop-blur px-2 py-1 border text-[10px] font-mono uppercase tracking-wider ${
          isLive ? "border-bullish shadow-glow" : "border-border"
        }`}
      >
        <span
          className={`w-1.5 h-1.5 rounded-full ${isLive ? "bg-bullish animate-pulse" : "bg-ghost"}`}
        />
        <span className={isLive ? "text-bullish" : "text-ghost"}>{isLive ? "LIVE" : "ĐANG KẾT NỐI..."}</span>
      </div>
      <div ref={containerRef} className="w-full overflow-hidden border border-border panel-hover" />
    </div>
  );
}
