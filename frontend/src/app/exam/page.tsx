"use client";
import { useState, useEffect } from "react";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useTTS } from "@/hooks/useTTS";
import { Mic2, Square, Wand2, ArrowRight } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { ApiClient } from "@/lib/api";

export default function ExamSimulator() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [examPart, setExamPart] = useState<"READY" | "PART_1" | "PART_2" | "PART_3" | "FINISHED">("READY");
  const [currentPrompt, setCurrentPrompt] = useState("Are you ready to begin your mock exam?");
  const [feedback, setFeedback] = useState<any>(null);
  const [processing, setProcessing] = useState(false);
  const { isRecording, startRecording, stopRecording, audioBlob, setAudioBlob } = useAudioRecorder();
  const { speak } = useTTS();

  const handleStartExam = async () => {
    setProcessing(true);
    try {
        const session = await ApiClient.startExam();
        setSessionId(session.id);
        setExamPart("PART_1");
        const firstPrompt = "Let's start with Part 1. Can you tell me your full name and where you are from?";
        setCurrentPrompt(firstPrompt);
        speak(firstPrompt);
    } catch (e) {
        console.error(e);
    } finally {
        setProcessing(false);
    }
  };

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
            // Auto-update part if returned (WIP: Backend transition is server-side)
            // For now, we manually check or assume the engine handles it
        } catch (e) {
            console.error(e);
        } finally {
            setProcessing(false);
            setAudioBlob(null);
        }
      };
      submit();
    }
  }, [audioBlob, sessionId]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-64px)] p-8 max-w-4xl mx-auto">
      
      {/* Progress Stepper */}
      <div className="w-full max-w-2xl flex items-center justify-between mb-16 relative">
          <Step active={examPart === "PART_1"} completed={["PART_2", "PART_3", "FINISHED"].includes(examPart)} num="1" label="Introduction" />
          <div className="flex-1 h-[2px] bg-zinc-800 mx-4" />
          <Step active={examPart === "PART_2"} completed={["PART_3", "FINISHED"].includes(examPart)} num="2" label="Cue Card" />
          <div className="flex-1 h-[2px] bg-zinc-800 mx-4" />
          <Step active={examPart === "PART_3"} completed={examPart === "FINISHED"} num="3" label="Discussion" />
      </div>

      <div className="w-full bg-[#12121a] border border-zinc-800 p-12 rounded-3xl shadow-2xl relative overflow-hidden group">
          
          {/* Status Badge */}
          <div className="absolute top-6 left-6">
              <span className="px-3 py-1 rounded-full bg-red-500/10 text-red-500 text-[10px] font-bold uppercase tracking-widest border border-red-500/20">
                  {examPart === "READY" ? "Initial State" : `Section: ${examPart.replace("_", " ")}`}
              </span>
          </div>

          <div className="flex flex-col items-center gap-8 text-center min-h-[300px] justify-center">
              
              {examPart === "READY" ? (
                  <>
                    <h2 className="text-4xl font-light text-zinc-100 uppercase tracking-tight">The Simulator</h2>
                    <p className="text-zinc-500 max-w-md">Complete a full 15-minute mock exam with instant analysis in all four IELTS criteria.</p>
                    <button 
                        onClick={handleStartExam}
                        className="mt-4 px-8 py-4 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold flex items-center gap-2 transition-all hover:scale-105 shadow-[0_0_30px_rgba(239,68,68,0.3)]"
                    >
                        Begin Examination <ArrowRight size={20} />
                    </button>
                  </>
              ) : (
                  <>
                    <h2 className="text-3xl font-light text-zinc-100 leading-relaxed max-w-2xl">
                        {feedback?.next_task_prompt || currentPrompt}
                    </h2>

                    <div className="flex flex-col items-center gap-4 py-8">
                        <button
                            onClick={isRecording ? stopRecording : startRecording}
                            disabled={processing}
                            className={`w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 relative ${
                                isRecording ? "bg-red-600 scale-110 shadow-[0_0_40px_rgba(220,38,38,0.4)]" : "bg-zinc-900 border border-zinc-800 text-zinc-500 hover:text-white hover:border-zinc-700"
                            }`}
                        >
                            {isRecording ? <Square size={32} fill="white" /> : <Mic2 size={32} />}
                            {isRecording && <div className="absolute inset-[-8px] border-2 border-red-600/30 rounded-full animate-ping" />}
                        </button>
                        <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">{isRecording ? "Listening..." : "Tap to Answer"}</p>
                    </div>

                    {/* Feedback Preview */}
                    {feedback && (
                        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6 text-left w-full border-t border-zinc-800/50 pt-8 animate-in fade-in slide-in-from-bottom-4">
                            <div className="space-y-2">
                                <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest flex items-center gap-2">
                                    <Wand2 size={12} /> Pro Tip
                                </span>
                                <p className="text-zinc-400 text-sm italic">"{feedback.ideal_response}"</p>
                            </div>
                            <div className="space-y-2">
                                <span className="text-[10px] font-bold text-amber-400 uppercase tracking-widest">Examiner Notes</span>
                                <div className="text-zinc-500 text-xs leading-relaxed">
                                    <ReactMarkdown>{feedback.feedback_markdown}</ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    )}
                  </>
              )}
          </div>
      </div>
    </div>
  );
}

function Step({ active, completed, num, label }: any) {
    return (
        <div className="flex flex-col items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all duration-500 ${
                active ? "bg-red-600 border-red-600 text-white" : 
                completed ? "bg-zinc-800 border-zinc-800 text-emerald-500" : "bg-transparent border-zinc-800 text-zinc-600"
            }`}>
                {completed ? "✓" : num}
            </div>
            <span className={`text-[10px] font-bold uppercase tracking-wider ${active ? "text-zinc-100" : "text-zinc-600"}`}>{label}</span>
        </div>
    );
}
