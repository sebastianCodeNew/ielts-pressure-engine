"use client";
import React, { useEffect, useState } from 'react';
import { Gauge, Zap } from "lucide-react";

interface FlowGaugeProps {
  isRecording: boolean;
  silenceTimer: number; // Seconds of silence
}

export function FlowGauge({ isRecording, silenceTimer }: FlowGaugeProps) {
  // Mock WPM simulation for visual feedback since we don't have real-time WPM from backend stream yet
  // In a real app, this would be driven by the audio analyzer
  const [wpm, setWpm] = useState(0);
  const [trend, setTrend] = useState<"STABLE" | "DROPPING" | "CRITICAL">("STABLE");

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
          setWpm(prev => {
              // If silent, drop fast. If speaking (silence < 1), fluctuate high.
              if (silenceTimer > 1) return Math.max(0, prev - 10);
              if (silenceTimer === 0) return Math.min(160, Math.max(110, prev + Math.random() * 20 - 5));
              return prev;
          });
      }, 500);
    } else {
        setWpm(0);
    }
    return () => clearInterval(interval);
  }, [isRecording, silenceTimer]);

  useEffect(() => {
     if (wpm < 60 && isRecording) setTrend("CRITICAL");
     else if (wpm < 100 && isRecording) setTrend("DROPPING");
     else setTrend("STABLE");
  }, [wpm, isRecording]);

  if (!isRecording) return null;

  return (
    <div className={`fixed bottom-32 left-1/2 -translate-x-1/2 transform transition-all duration-500 ${
        trend === "CRITICAL" ? "scale-110" : "scale-100"
    }`}>
        <div className={`backdrop-blur-xl border-2 px-6 py-3 rounded-full flex items-center gap-4 shadow-2xl transition-colors duration-300 ${
            trend === "CRITICAL" ? "bg-red-950/80 border-red-500 shadow-red-900/50" :
            trend === "DROPPING" ? "bg-amber-950/80 border-amber-500 shadow-amber-900/50" :
            "bg-emerald-950/60 border-emerald-500/30 shadow-emerald-900/20"
        }`}>
            <div className="relative">
                <Gauge size={24} className={
                    trend === "CRITICAL" ? "text-red-500 animate-pulse" :
                    trend === "DROPPING" ? "text-amber-500" :
                    "text-emerald-500"
                } />
                <div className={`absolute -top-1 -right-1 w-2 h-2 rounded-full ${
                    trend === "STABLE" ? "bg-emerald-400 animate-ping" : "bg-transparent"
                }`} />
            </div>

            <div className="flex flex-col">
                <span className="text-[10px] font-black uppercase tracking-widest text-zinc-400">
                    Flow Rate
                </span>
                <span className={`text-2xl font-black tabular-nums leading-none ${
                     trend === "CRITICAL" ? "text-red-500" :
                     trend === "DROPPING" ? "text-amber-500" :
                     "text-white"
                }`}>
                    {Math.round(wpm)} <span className="text-xs font-bold text-zinc-600">WPM</span>
                </span>
            </div>

            {trend === "CRITICAL" && (
                <div className="flex items-center gap-1 text-red-500 font-bold text-xs animate-in slide-in-from-left-2">
                    <Zap size={14} fill="currentColor"/> KEEP GOING!
                </div>
            )}
        </div>
    </div>
  );
}
