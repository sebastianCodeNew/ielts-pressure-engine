"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useTTS } from "@/hooks/useTTS";
import { Mic2, Square, Wand2, ArrowRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import AudioWaveform from "@/components/AudioWaveform";

import { ApiClient } from "@/lib/api";

interface FeedbackData {
  next_task_prompt?: string;
  feedback_markdown?: string;
  action_id?: string;
}

export default function ExamSimulator() {
  const {
    isRecording,
    startRecording,
    stopRecording,
    audioBlob,
    setAudioBlob,
    stream,
  } = useAudioRecorder();

  const { speak, isSpeaking } = useTTS();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [examPart, setExamPart] = useState<
    "INTRO" | "PART_1" | "PART_2" | "PART_3" | "FINISHED"
  >("INTRO");
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [processing, setProcessing] = useState(false);

  const startExam = async () => {
    try {
      const session = await ApiClient.startExam("default_user", "FULL_MOCK");
      setSessionId(session.id);
      setExamPart("PART_1");
      speak(
        "Welcome to the IELTS Speaking Mock Exam. I am your examiner. Let's begin with Part 1. Can you tell me about your hometown?",
      );
    } catch (e) {
      console.error(e);
    }
  };

  const router = useRouter();

  useEffect(() => {
    if (audioBlob && sessionId) {
      const submit = async () => {
        setProcessing(true);
        try {
          const data = await ApiClient.submitExamAudio(sessionId, audioBlob);
          setFeedback(data);

          if (data.next_task_prompt) {
            speak(data.next_task_prompt);
          }

          const session = await ApiClient.getExamStatus(sessionId);
          if (session.status === "COMPLETED") {
            setExamPart("FINISHED");
            router.push(`/exam/result/${sessionId}`);
          } else {
            setExamPart(session.current_part as any);
          }
        } catch (e) {
          console.error(e);
        } finally {
          setProcessing(false);
          setAudioBlob(null);
        }
      };
      submit();
    }
  }, [audioBlob, sessionId, speak, setAudioBlob, router]);

  if (examPart === "INTRO") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 animate-in fade-in zoom-in duration-500">
        <div className="w-24 h-24 bg-red-600 rounded-3xl flex items-center justify-center rotate-3 shadow-2xl">
          <Mic2 size={48} className="text-white" />
        </div>
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-black tracking-tight text-white uppercase">
            Ready for Pressure?
          </h1>
          <p className="text-zinc-500 max-w-md mx-auto">
            This 15-minute mock exam simulates real IELTS conditions with
            adaptive AI stress levels.
          </p>
        </div>
        <button
          onClick={startExam}
          className="px-8 py-4 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold flex items-center gap-2 group transition-all"
        >
          Begin Simulation{" "}
          <ArrowRight
            size={20}
            className="group-hover:translate-x-1 transition-transform"
          />
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-12 py-8">
      {/* Exam Status Bar */}
      <div className="flex justify-between items-center bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl">
        <div className="flex gap-4">
          <PartIndicator active={examPart === "PART_1"} label="Part 1" />
          <PartIndicator active={examPart === "PART_2"} label="Part 2" />
          <PartIndicator active={examPart === "PART_3"} label="Part 3" />
        </div>
        <div className="flex items-center gap-2 text-zinc-500 text-xs font-bold uppercase tracking-widest">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          Live AI Session
        </div>
      </div>

      {/* Examiner Prompt */}
      <div className="bg-[#12121a] border border-zinc-800/50 p-10 rounded-[40px] shadow-2xl relative overflow-hidden group">
        <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
          <Wand2 size={120} />
        </div>
        <div className="space-y-6 relative z-10">
          <span className="px-3 py-1 bg-zinc-800 text-zinc-400 rounded-full text-[10px] font-bold uppercase tracking-widest">
            Examiner
          </span>
          <div className="text-2xl font-medium text-zinc-100 leading-relaxed min-h-[100px]">
            {feedback?.next_task_prompt ||
              "Please describe the room you are in right now."}
          </div>
          {isSpeaking && (
            <div className="flex gap-1 items-end h-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="w-1 bg-red-500 animate-bounce"
                  style={{
                    animationDelay: `${i * 0.1}s`,
                    height: `${Math.random() * 100}%`,
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Waveform Visualization */}
      <div className="max-w-md mx-auto w-full mb-8">
        <AudioWaveform isRecording={isRecording} audioStream={stream} />
      </div>

      {/* Primary Controls */}
      <div className="flex flex-col items-center gap-8">
        {!isRecording ? (
          <button
            disabled={isSpeaking || processing}
            onClick={startRecording}
            className="group relative w-32 h-32 bg-red-600 disabled:bg-zinc-800 rounded-full flex items-center justify-center transition-all hover:scale-105 active:scale-95 shadow-[0_0_30px_rgba(220,38,38,0.4)] disabled:shadow-none"
          >
            {!isSpeaking && !processing && (
              <div className="absolute inset-0 rounded-full bg-red-600 animate-ping opacity-20 pointer-events-none" />
            )}
            {processing ? (
              <div className="w-10 h-10 border-4 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Mic2 size={48} className="text-white" />
            )}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="group w-32 h-32 bg-zinc-100 rounded-full flex items-center justify-center transition-all hover:scale-105 active:scale-95"
          >
            <Square size={48} className="text-zinc-950" />
          </button>
        )}

        <div className="text-center h-12">
          <p className="text-zinc-500 text-sm font-medium uppercase tracking-widest">
            {isRecording
              ? "Listening... Speak clearly"
              : isSpeaking
                ? "Examiner is speaking..."
                : "Tap to start responding"}
          </p>
        </div>
      </div>

      {/* Instant Feedback (Optional/Hidden in Exam) */}
      {feedback?.feedback_markdown && (
        <div className="p-6 bg-zinc-900/30 border border-zinc-800 rounded-3xl animate-in slide-in-from-bottom duration-500">
          <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4">
            Educational Feedback
          </h4>
          <div className="prose prose-invert prose-sm max-w-none prose-p:text-zinc-400">
            <ReactMarkdown>{feedback.feedback_markdown}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

function PartIndicator({ active, label }: { active: boolean; label: string }) {
  return (
    <div
      className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all ${
        active
          ? "bg-red-600/10 border-red-500/50 text-red-500"
          : "bg-transparent border-transparent text-zinc-600"
      }`}
    >
      <div
        className={`w-1.5 h-1.5 rounded-full ${active ? "bg-red-500" : "bg-zinc-800"}`}
      />
      <span className="text-xs font-black uppercase tracking-widest">
        {label}
      </span>
    </div>
  );
}
