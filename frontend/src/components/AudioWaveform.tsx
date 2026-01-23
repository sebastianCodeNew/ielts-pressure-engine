"use client";
import { useEffect, useRef } from "react";

interface AudioWaveformProps {
  isRecording: boolean;
  audioStream: MediaStream | null;
}

export default function AudioWaveform({ isRecording, audioStream }: AudioWaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const analyzerRef = useRef<AnalyserNode | null>(null);

  useEffect(() => {
    if (!isRecording || !audioStream || !canvasRef.current) {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      return;
    }

    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const analyzer = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(audioStream);
    source.connect(analyzer);

    analyzer.fftSize = 256;
    analyzerRef.current = analyzer;

    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d")!;

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);
      analyzer.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const barWidth = (canvas.width / bufferLength) * 2.5;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;
        
        // Gradient effect
        const gradient = ctx.createLinearGradient(0, canvas.height, 0, 0);
        gradient.addColorStop(0, "#ef4444");
        gradient.addColorStop(1, "#3b82f6");

        ctx.fillStyle = gradient;
        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

        x += barWidth + 1;
      }
    };

    draw();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      audioContext.close();
    };
  }, [isRecording, audioStream]);

  return (
    <div className="w-full h-24 bg-zinc-900/20 backdrop-blur-sm rounded-2xl overflow-hidden flex items-center justify-center">
      <canvas 
        ref={canvasRef} 
        width={400} 
        height={80} 
        className="w-full h-full"
      />
    </div>
  );
}
