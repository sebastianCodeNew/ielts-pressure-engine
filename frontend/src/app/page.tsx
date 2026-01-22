"use client";
import { useState, useEffect } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import TranslatorWidget from "../components/Translator";
import { ApiClient } from "@/lib/api";
import { Intervention } from "@/lib/types";
import ReactMarkdown from 'react-markdown';

export default function Home() {
  const {
    isRecording,
    startRecording,
    stopRecording,
    audioBlob,
    setAudioBlob,
  } = useAudioRecorder();
  const [feedback, setFeedback] = useState<Intervention | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-submit when audioBlob is ready
  useEffect(() => {
    if (audioBlob) {
      submitAudio(audioBlob);
    }
  }, [audioBlob]);

  const submitAudio = async (blob: Blob) => {
    setProcessing(true);
    setError(null);
    try {
      const data = await ApiClient.submitAudio(blob);
      setFeedback(data);
      setAudioBlob(null); // Reset for next turn
    } catch (e) {
      console.error(e);
      setError(
        "Connection to AI Engine failed. Please ensure the backend is running.",
      );
    } finally {
      setProcessing(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#0d0d12] text-zinc-100 font-sans selection:bg-red-500/30">
      {/* Background Gradients */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-red-900/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-blue-900/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 w-full max-w-2xl px-6 py-12 flex flex-col gap-8">
        {/* Header / Status */}
        <div className="flex flex-col items-center gap-2">
          <h1 className="text-sm font-bold tracking-[0.2em] text-zinc-500 uppercase">
            IELTS Pressure Engine
          </h1>
          <div
            className={`h-1 w-24 rounded-full transition-all duration-500 ${processing ? "bg-amber-500 animate-pulse w-32" : "bg-zinc-800"}`}
          />
          {error && (
            <p className="text-red-400 text-xs mt-2 bg-red-950/50 px-3 py-1 rounded border border-red-900">
              {error}
            </p>
          )}
        </div>

        {/* --- DYNAMIC PROMPT CARD --- */}
        <div className="relative group bg-zinc-900/40 backdrop-blur-xl border border-zinc-700/50 p-8 rounded-2xl shadow-2xl transition-all duration-300 hover:border-zinc-600/50">
          <h2 className="text-3xl md:text-4xl font-light leading-tight text-center text-zinc-100">
            {feedback?.next_task_prompt ||
              "Describe the room you are in right now."}
          </h2>

          {feedback?.constraints?.timer && (
            <div className="absolute top-4 right-4 text-xs font-mono text-zinc-500 border border-zinc-700 px-2 py-0.5 rounded">
              {feedback.constraints.timer}s LIMIT
            </div>
          )}
        </div>

        {/* --- VOCABULARY SCAFFOLDING (New) --- */}
        {feedback?.keywords && feedback.keywords.length > 0 && (
          <div className="flex flex-wrap justify-center gap-2 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {feedback.keywords.map((word, i) => (
              <span
                key={i}
                className="px-3 py-1 text-xs font-medium text-emerald-400 bg-emerald-950/30 border border-emerald-900/50 rounded-full"
              >
                {word}
              </span>
            ))}
          </div>
        )}

        {/* --- MAIN INTERACTION AREA --- */}
        <div className="flex flex-col items-center justify-center py-8">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={processing}
            className={`
                relative w-32 h-32 rounded-full flex items-center justify-center transition-all duration-300
                ${isRecording ? "scale-105" : "hover:scale-105 hover:bg-zinc-800/80"}
                ${processing ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
            `}
          >
            {/* Outer Ring */}
            <div
              className={`absolute inset-0 rounded-full border-2 transition-colors duration-300 ${isRecording ? "border-red-500/50 animate-ping" : "border-zinc-700"}`}
            />

            {/* Inner Circle */}
            <div
              className={`w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 shadow-[0_0_40px_rgba(0,0,0,0.5)] ${isRecording ? "bg-red-600 text-white shadow-[0_0_50px_rgba(220,38,38,0.4)]" : "bg-zinc-900 border border-zinc-700 text-zinc-400"}`}
            >
              {processing ? (
                <div className="h-2 w-2 bg-white rounded-full animate-bounce" />
              ) : isRecording ? (
                <div className="h-8 w-8 bg-white rounded-sm animate-pulse" />
              ) : (
                <svg
                  className="w-10 h-10 translate-x-1"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </div>
          </button>
          <p className="mt-6 text-zinc-600 text-xs tracking-widest uppercase font-medium">
            {isRecording
              ? "Recording..."
              : processing
                ? "Analyzing..."
                : "Tap to Speak"}
          </p>
        </div>

        {/* --- FEEDBACK SECTION (New) --- */}
        {feedback &&
          (feedback.ideal_response || feedback.feedback_markdown) && (
            <div className="grid gap-6 animate-in fade-in zoom-in-95 duration-500">
              {/* 1. Model Answer */}
              {feedback.ideal_response && (
                <div className="bg-blue-950/20 border border-blue-900/30 p-6 rounded-xl">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-blue-400 text-xs font-bold uppercase tracking-wider">
                      Band 7.0 Model Answer
                    </span>
                  </div>
                  <p className="text-blue-100/90 text-lg leading-relaxed italic">
                    "{feedback.ideal_response}"
                  </p>
                </div>
              )}

              {/* 2. Specific Feedback */}
              {feedback.feedback_markdown && (
                <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-xl space-y-3">
                  <span className="text-zinc-500 text-xs font-bold uppercase tracking-wider">
                    Examiner Notes
                  </span>
                  <div className="text-zinc-300 text-sm leading-relaxed prose prose-invert prose-p:my-1 prose-ul:my-2">
                    <ReactMarkdown>{feedback.feedback_markdown}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          )}
      </div>

      <div className="fixed bottom-6 right-6">
        <TranslatorWidget />
      </div>
    </main>
  );
}
