"use client";

import { useEffect, useRef, useState } from "react";
import AnimatedNumber from "@/components/AnimatedNumber";

interface TickerData {
  price: number;
  changePercent: number;
  high: number;
  low: number;
  volume: number;
}

// Signature element của giao diện — dải ticker chạy ngang kiểu bảng điện sàn giao dịch
// thật (Bloomberg/Binance), kết nối trực tiếp WebSocket 24hr ticker của Binance —
// không qua backend, không cần API key.
export default function TickerTape({ symbol = "BTCUSDT" }: { symbol?: string }) {
  const [data, setData] = useState<TickerData | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const prevPriceRef = useRef<number | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@ticker`);

    ws.onmessage = (event) => {
      const t = JSON.parse(event.data);
      const price = parseFloat(t.c);

      if (prevPriceRef.current !== null) {
        if (price > prevPriceRef.current) setFlash("up");
        else if (price < prevPriceRef.current) setFlash("down");
        setTimeout(() => setFlash(null), 600);
      }
      prevPriceRef.current = price;

      setData({
        price,
        changePercent: parseFloat(t.P),
        high: parseFloat(t.h),
        low: parseFloat(t.l),
        volume: parseFloat(t.v),
      });
    };

    return () => ws.close();
  }, [symbol]);

  if (!data) {
    return (
      <div className="w-full bg-panel border-b border-border h-9 flex items-center px-4">
        <span className="text-xs font-mono text-ghost">Đang kết nối ticker...</span>
      </div>
    );
  }

  const isUp = data.changePercent >= 0;

  const Segment = () => (
    <div className="flex items-center gap-8 px-6 whitespace-nowrap shrink-0">
      <span className="font-mono text-xs text-ghost">{symbol}</span>
      <span
        className={`font-mono text-sm font-bold ${isUp ? "text-bullish" : "text-bearish"} ${
          flash === "up" ? "flash-up" : flash === "down" ? "flash-down" : ""
        }`}
      >
        <AnimatedNumber value={data.price} decimals={2} prefix="$" durationMs={400} />
      </span>
      <span className={`font-mono text-xs ${isUp ? "text-bullish" : "text-bearish"}`}>
        {isUp ? "▲" : "▼"} {Math.abs(data.changePercent).toFixed(2)}% (24H)
      </span>
      <span className="font-mono text-xs text-ghost">
        24H CAO <span className="text-gray-200">${data.high.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
      </span>
      <span className="font-mono text-xs text-ghost">
        24H THẤP <span className="text-gray-200">${data.low.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
      </span>
      <span className="font-mono text-xs text-ghost">
        KL <span className="text-gray-200">{data.volume.toLocaleString(undefined, { maximumFractionDigits: 0 })} BTC</span>
      </span>
    </div>
  );

  return (
    <div className="w-full bg-panel border-b border-border overflow-hidden h-9 flex items-center">
      <div className="flex ticker-scroll">
        <Segment />
        <Segment />
      </div>
    </div>
  );
}
