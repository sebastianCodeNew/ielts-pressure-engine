"use client";
import { useState, useEffect } from "react";
import { useAudioRecorder } from "../hooks/useAudioRecorder";
import TranslatorWidget from "../components/Translator"; // <--- Import

export default function Home() {
  const { isRecording, startRecording, stopRecording, audioBlob, setAudioBlob } = useAudioRecorder();
  const [feedback, setFeedback] = useState<any>(null);
  const [processing, setProcessing] = useState(false);

  // Auto-submit when audioBlob is ready
  useEffect(() => {
    if (audioBlob) {
      submitAudio(audioBlob);
    }
  }, [audioBlob]);

  const submitAudio = async (blob: Blob) => {
    setProcessing(true);
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    // We send task_id manually for now
    formData.append("task_id", "task_001"); 

    try {
      const res = await fetch("http://127.0.0.1:8000/api/submit-audio", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setFeedback(data);
      setAudioBlob(null); // Reset for next turn
    } catch (e) { 
      console.error(e);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-200 font-mono">
      <div className="w-full max-w-xl p-8 border border-zinc-800 rounded-lg text-center">
        
        {/* Status Indicator */}
        <div className={`mb-8 text-sm tracking-widest uppercase ${processing ? "animate-pulse text-yellow-500" : "text-zinc-600"}`}>
          {processing ? "Analyzing Cognitive Load..." : "System Ready"}
        </div>

        {/* The Prompt */}
        <div className="mb-12">
          <h2 className="text-3xl font-light mb-4">
            {feedback ? feedback.next_task_prompt : "Describe the room you are in right now."}
          </h2>
          {feedback && (
            <div className="inline-block px-3 py-1 bg-red-900/30 text-red-400 text-xs border border-red-900 rounded">
               CONSTRAINT: {feedback.action_id}
            </div>
          )}
        </div>

        {/* The Pressure Button */}
        <button
          onClick={isRecording ? stopRecording : startRecording} // <--- NEW LOGIC
          disabled={processing}
          className={`
            w-32 h-32 rounded-full border-4 transition-all duration-100 flex items-center justify-center
            ${isRecording 
              ? "bg-red-600 border-red-500 scale-95 shadow-[0_0_30px_rgba(220,38,38,0.5)]" 
              : "bg-zinc-900 border-zinc-700 hover:border-zinc-500"}
          `}
        >
          {isRecording ? (
            <div className="w-8 h-8 bg-white rounded animate-pulse" />
          ) : (
            // Microphone Icon or Play Triangle
            <div className="w-0 h-0 border-l-[15px] border-l-transparent border-r-[15px] border-r-transparent border-b-[26px] border-b-zinc-400 rotate-90 ml-1" />
          )}
        </button>

        <p className="mt-6 text-zinc-500 text-xs uppercase">
          {isRecording ? "Click to Submit" : "Click to Speak"} {/* Updated Label */}
        </p>
      </div>
      <TranslatorWidget />
    </main>
  );
}