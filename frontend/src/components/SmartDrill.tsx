"use client";
import React, { useState, useEffect } from 'react';
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { Mic2, RefreshCw, CheckCircle, XCircle, Trophy } from "lucide-react";
import { ApiClient } from "@/lib/api";

interface SmartDrillProps {
  errorType: string;
  onComplete: (score: number) => void;
  onExit: () => void;
}

interface DrillItem {
  prompt: string;
  target: string;
  hint: string;
}

const SAMPLE_DRILLS: Record<string, DrillItem[]> = {
  "Subject-Verb Agreement": [
      { prompt: "She _ (go) to the store every day.", target: "She goes to the store every day", hint: "Third person singular" },
      { prompt: "The group of students _ (is/are) studying.", target: "The group of students is studying", hint: "Group is singular here" },
      { prompt: "He don't like it.", target: "He doesn't like it", hint: "He/She/It DOES" },
  ],
  "Article Usage": [
      { prompt: "I saw _ elephant.", target: "I saw an elephant", hint: "Vowel sound" },
      { prompt: "He is _ doctor.", target: "He is a doctor", hint: "Countable noun" },
      { prompt: "I went to _ Paris.", target: "I went to Paris", hint: "No article for cities" },
  ],
  "Tense Consistency": [
      { prompt: "Yesterday I _ (go) to the bank.", target: "Yesterday I went to the bank", hint: "Past simple" },
      { prompt: "I have _ (live) here for 5 years.", target: "I have lived here for 5 years", hint: "Present perfect" },
  ]
};

export function SmartDrill({ errorType, onComplete, onExit }: SmartDrillProps) {
  const { isRecording, startRecording, stopRecording, audioBlob, setAudioBlob } = useAudioRecorder();
  
  const [drillSet, setDrillSet] = useState<DrillItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [status, setStatus] = useState<"IDLE" | "RECORDING" | "PROCESSING" | "SUCCESS" | "FAIL">("IDLE");
  const [feedback, setFeedback] = useState("");
  const [score, setScore] = useState(0);
  const isMounted = React.useRef(true);

  useEffect(() => {
      return () => { isMounted.current = false; };
  }, []);

  useEffect(() => {
    // Load drills or fallback
    const drills = SAMPLE_DRILLS[errorType] || SAMPLE_DRILLS["Subject-Verb Agreement"] || [];
    setDrillSet(drills);
  }, [errorType]);

  const currentDrill = drillSet[currentIndex];

  useEffect(() => {
    if (audioBlob && status === "RECORDING") {
        verifyAudio();
    }
  }, [audioBlob]);

  const verifyAudio = async () => {
     setStatus("PROCESSING");
     try {
         // Use existing shadowing analyzer for simplicity
         const result = await ApiClient.analyzeShadowing(currentDrill.target, audioBlob!, errorType);
         
         if (!isMounted.current) return;

         if (result.is_passed) {
             setStatus("SUCCESS");
             setScore(s => s + 1);
             setFeedback(`Correct! accuracy: ${(result.mastery_score * 100).toFixed(0)}%`);
             
             // Auto advance
             setTimeout(() => {
                 if (!isMounted.current) return;
                 
                 if (currentIndex < drillSet.length - 1) {
                     setCurrentIndex(i => i + 1);
                     setStatus("IDLE");
                     setFeedback("");
                     setAudioBlob(null);
                 } else {
                     onComplete(score + 1);
                 }
             }, 1500);
         } else {
             setStatus("FAIL");
             setFeedback("Try again. Listen closely.");
             setAudioBlob(null);
         }
     } catch (e) {
         console.error(e);
         if (isMounted.current) setStatus("FAIL");
     }
  };

  if (!currentDrill) return <div className="p-8 text-center">Loading Drills...</div>;

  return (
    <div className="bg-[#18181b] p-8 rounded-3xl border border-zinc-700 max-w-xl w-full mx-auto relative overflow-hidden shadow-2xl animate-in zoom-in-95 duration-300">
        {/* Progress Bar */}
        <div className="absolute top-0 left-0 w-full h-1.5 bg-zinc-800">
            <div 
                className={`h-full transition-all duration-500 ${status === "SUCCESS" ? "bg-emerald-400" : "bg-blue-500"}`}
                style={{ width: `${((currentIndex) / drillSet.length) * 100}%` }}
            />
        </div>

        <div className="flex justify-between items-center mb-10">
            <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-emerald-500/10 text-emerald-500 rounded-lg flex items-center justify-center">
                   <RefreshCw size={16} />
                </div>
                <div>
                   <h3 className="text-xs font-black text-white uppercase tracking-widest">
                       Rapid Fire: {errorType}
                   </h3>
                   <p className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">
                       Step {currentIndex + 1} of {drillSet.length}
                   </p>
                </div>
            </div>
            <button 
              onClick={onExit} 
              className="w-8 h-8 flex items-center justify-center rounded-full bg-zinc-900 text-zinc-500 hover:text-white hover:bg-zinc-800 transition-all"
            >
              <XCircle size={20} />
            </button>
        </div>

        <div className="text-center space-y-8">
             <div className="bg-black/20 p-6 rounded-2xl border border-zinc-800/50">
               <div className="text-2xl font-medium text-white break-words leading-relaxed font-serif">
                   {currentDrill.prompt.split('_').map((part, i, arr) => (
                      <span key={i}>
                          {part}
                          {i < arr.length - 1 && (
                              <span className="inline-block w-16 border-b-2 border-emerald-500 mx-1">{/* Blank */}</span>
                          )}
                      </span>
                   ))}
               </div>
             </div>
             
             <div className="flex flex-col items-center gap-2">
               <p className="text-xs text-zinc-500 uppercase font-black tracking-widest">Target Phrasing</p>
               <p className="text-zinc-300 text-sm font-bold italic bg-zinc-900 px-4 py-2 rounded-lg border border-zinc-800">
                 "{currentDrill.target}"
               </p>
             </div>

             {/* Feedback Status */}
             <div className="h-10 flex justify-center items-center">
                 {status === "SUCCESS" && (
                   <div className="flex flex-col items-center gap-1 animate-in zoom-in">
                     <span className="text-emerald-500 font-bold flex items-center gap-2">
                       <CheckCircle size={18}/> Correct!
                     </span>
                     <span className="text-[10px] text-emerald-500/60 font-black uppercase tracking-widest">{feedback}</span>
                   </div>
                 )}
                 {status === "FAIL" && (
                   <div className="flex flex-col items-center gap-1 animate-in shake">
                     <span className="text-red-500 font-bold flex items-center gap-2">
                       <XCircle size={18}/> Try Again
                     </span>
                     <span className="text-[10px] text-red-500/60 font-black uppercase tracking-widest">Focus on the grammar!</span>
                   </div>
                 )}
                 {status === "PROCESSING" && (
                   <div className="flex flex-col items-center gap-2">
                     <div className="w-4 h-4 border-2 border-zinc-500 border-t-transparent rounded-full animate-spin" />
                     <span className="text-[10px] text-zinc-500 font-black uppercase tracking-widest animate-pulse">Analyzing Voice...</span>
                   </div>
                 )}
                 {status === "IDLE" && (
                   <span className="text-[10px] text-zinc-600 font-black uppercase tracking-widest transition-opacity duration-300">
                     Ready for your response
                   </span>
                 )}
             </div>

             <div className="flex justify-center pt-2">
                 <button
                    onMouseDown={() => {
                        if (status === "PROCESSING" || status === "SUCCESS") return;
                        setStatus("RECORDING");
                        startRecording();
                    }}
                    onMouseUp={() => {
                      if (isRecording) stopRecording();
                    }}
                    onMouseLeave={() => {
                      if (isRecording) stopRecording();
                    }}
                    disabled={status === "PROCESSING" || status === "SUCCESS"}
                    className={`w-28 h-28 rounded-full flex flex-col items-center justify-center gap-2 transition-all relative ${
                        isRecording 
                        ? 'bg-red-600 scale-110 shadow-[0_0_40px_rgba(220,38,38,0.6)]' 
                        : status === "SUCCESS" 
                            ? 'bg-emerald-500 cursor-default shadow-[0_0_30px_rgba(16,185,129,0.4)]'
                            : 'bg-zinc-800 hover:bg-zinc-700 hover:scale-105 border border-zinc-700'
                    }`}
                 >
                    {isRecording && (
                      <div className="absolute inset-0 rounded-full border-4 border-white/20 animate-ping" />
                    )}
                    
                    {status === "SUCCESS" ? (
                      <Trophy size={40} className="text-white" />
                    ) : (
                      <Mic2 size={36} className={isRecording ? "text-white" : "text-zinc-100"} />
                    )}
                    
                    <span className="text-[10px] font-black uppercase text-white/70 tracking-widest">
                        {isRecording ? "Listening" : status === "SUCCESS" ? "Passed" : "Hold to Speak"}
                    </span>
                 </button>
             </div>
             
             <p className="text-[9px] text-zinc-600 font-bold uppercase tracking-widest">
               Hint: {currentDrill.hint}
             </p>
        </div>
    </div>
  );
}
