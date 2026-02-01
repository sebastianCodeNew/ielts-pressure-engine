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
         const result = await ApiClient.analyzeShadowing(currentDrill.target, audioBlob!);
         
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
    <div className="bg-[#18181b] p-8 rounded-3xl border border-zinc-800 max-w-xl w-full mx-auto relative overflow-hidden">
        {/* Progress Bar */}
        <div className="absolute top-0 left-0 w-full h-1 bg-zinc-800">
            <div 
                className="h-full bg-emerald-500 transition-all duration-500"
                style={{ width: `${((currentIndex) / drillSet.length) * 100}%` }}
            />
        </div>

        <div className="flex justify-between items-center mb-8">
            <h3 className="text-sm font-black text-zinc-400 uppercase tracking-widest flex items-center gap-2">
                <RefreshCw size={16} /> Rapid Fire: {errorType}
            </h3>
            <button onClick={onExit} className="text-zinc-600 hover:text-white transition-colors">Exit</button>
        </div>

        <div className="text-center space-y-6">
             <div className="text-2xl font-medium text-white break-words leading-relaxed">
                 {currentDrill.prompt.split('_').map((part, i, arr) => (
                    <span key={i}>
                        {part}
                        {i < arr.length - 1 && (
                            <span className="inline-block w-12 border-b-2 border-emerald-500 mx-1">{/* Blank */}</span>
                        )}
                    </span>
                 ))}
             </div>
             
             <p className="text-sm text-zinc-500 italic">Target: "{currentDrill.target}"</p>

             {/* Feedback Status */}
             <div className="h-8 flex justify-center items-center">
                 {status === "SUCCESS" && <span className="text-emerald-500 font-bold flex items-center gap-2 animate-in zoom-in"><CheckCircle size={16}/> Correct!</span>}
                 {status === "FAIL" && <span className="text-red-500 font-bold flex items-center gap-2 animate-in shake"><XCircle size={16}/> Try Again</span>}
                 {status === "PROCESSING" && <span className="text-zinc-500 animate-pulse">Analyzing...</span>}
             </div>

             <div className="flex justify-center pt-4">
                 <button
                    onMouseDown={() => {
                        setStatus("RECORDING");
                        startRecording();
                    }}
                    onMouseUp={() => stopRecording()}
                    onMouseLeave={() => isRecording && stopRecording()}
                    disabled={status === "PROCESSING" || status === "SUCCESS"}
                    className={`w-24 h-24 rounded-full flex flex-col items-center justify-center gap-2 transition-all ${
                        isRecording 
                        ? 'bg-red-600 scale-110 shadow-[0_0_30px_rgba(220,38,38,0.5)]' 
                        : status === "SUCCESS" 
                            ? 'bg-emerald-500 cursor-default'
                            : 'bg-zinc-800 hover:bg-zinc-700 hover:scale-105 border border-zinc-700'
                    }`}
                 >
                    <Mic2 size={32} className={isRecording ? "text-white animate-pulse" : "text-zinc-400"} />
                    <span className="text-[10px] font-black uppercase text-zinc-500 tracking-widest">
                        {isRecording ? "Listening" : "Hold"}
                    </span>
                 </button>
             </div>
        </div>
    </div>
  );
}
