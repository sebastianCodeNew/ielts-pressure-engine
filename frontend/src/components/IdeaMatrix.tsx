"use client";
import React, { useState, useEffect } from 'react';
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { BrainCircuit, Mic2, Timer, Zap } from "lucide-react";

interface IdeaMatrixProps {
  onExit: () => void;
}

const TOPICS = [
    { name: "A Crowded Place", type: "Noun" },
    { name: "An Inspiring Person", type: "Adjective" },
    { name: "A Difficult Decision", type: "Event" },
    { name: "Public Transport", type: "Issue" }
];

const PROMPTS = [
    "Give me 3 Adjectives quickly!",
    "Give me 1 Sound, 1 Smell, 1 Sight!",
    "Give me a related idiom!",
    "What is the OPPOSITE of this?"
];

export function IdeaMatrix({ onExit }: IdeaMatrixProps) {
  const { isRecording, startRecording, stopRecording, audioBlob, setAudioBlob } = useAudioRecorder();
  
  const [phase, setPhase] = useState<"INTRO" | "GAME" | "RESULT">("INTRO");
  const [topic, setTopic] = useState(TOPICS[0]);
  const [prompt, setPrompt] = useState(PROMPTS[0]);
  const [timeLeft, setTimeLeft] = useState(10);
  const [score, setScore] = useState(0);

  // Timer Logic
  useEffect(() => {
    if (phase === "GAME" && timeLeft > 0) {
        const t = setTimeout(() => setTimeLeft(l => l - 1), 1000);
        return () => clearTimeout(t);
    } else if (phase === "GAME" && timeLeft === 0) {
        setPhase("RESULT");
    }
  }, [phase, timeLeft]);

  const startGame = () => {
      const randomTopic = TOPICS[Math.floor(Math.random() * TOPICS.length)];
      const randomPrompt = PROMPTS[Math.floor(Math.random() * PROMPTS.length)];
      setTopic(randomTopic);
      setPrompt(randomPrompt);
      setTimeLeft(10);
      setPhase("GAME");
      startRecording();
  };

  const finishRound = () => {
      stopRecording();
      setPhase("RESULT");
      // Simulate analysis (since we don't have a specific backend for this yet)
      // In real implementation, send audio to LLM to count valid ideas
      setScore(Math.floor(Math.random() * 3) + 1); 
  };

  return (
    <div className="bg-[#18181b] p-8 rounded-3xl border border-zinc-800 max-w-xl w-full mx-auto text-center relative overflow-hidden">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8 relative z-10">
            <h3 className="text-sm font-black text-blue-500 uppercase tracking-widest flex items-center gap-2">
                <BrainCircuit size={16} /> Idea Matrix
            </h3>
            <button onClick={onExit} className="text-zinc-600 hover:text-white transition-colors">Exit</button>
        </div>

        {phase === "INTRO" && (
            <div className="space-y-6 py-8">
                <div className="w-24 h-24 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-blue-500/20">
                    <Zap size={40} className="text-blue-500" />
                </div>
                <h2 className="text-3xl font-black text-white uppercase tracking-tighter">Brainstorm Speed Run</h2>
                <p className="text-zinc-400 max-w-sm mx-auto">
                    You have 10 seconds to generate ideas based on the prompt. Don't worry about grammar—just SPEED.
                </p>
                <button 
                    onClick={startGame}
                    className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl uppercase tracking-widest transition-all shadow-lg hover:scale-105"
                >
                    Start Game
                </button>
            </div>
        )}

        {phase === "GAME" && (
            <div className="space-y-8 py-4">
                <div className="space-y-2">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Topic</span>
                    <h2 className="text-4xl font-black text-white">{topic.name}</h2>
                </div>
                
                <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl animate-in zoom-in duration-300">
                    <p className="text-lg font-bold text-blue-400">{prompt}</p>
                </div>

                <div className="flex justify-center items-center gap-4">
                    <div className={`text-6xl font-black tabular-nums transition-colors ${timeLeft < 4 ? 'text-red-500 scale-110' : 'text-zinc-700'}`}>
                        {timeLeft}
                    </div>
                </div>

                <div className="flex justify-center">
                    <div className="flex items-center gap-2 px-4 py-2 bg-red-600/10 text-red-500 rounded-full animate-pulse border border-red-500/20">
                        <Mic2 size={16} /> Recording...
                    </div>
                </div>

                <button 
                  onClick={finishRound}
                  className="w-full py-4 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-bold rounded-xl uppercase tracking-widest transition-colors"
                >
                    Done (Stop Timer)
                </button>
            </div>
        )}

        {phase === "RESULT" && (
            <div className="space-y-6 py-8 animate-in slide-in-from-bottom">
                 <h2 className="text-2xl font-black text-white">Round Complete!</h2>
                 
                 <div className="flex justify-center gap-2">
                    {[...Array(3)].map((_, i) => (
                        <Zap key={i} size={32} className={i < score ? "text-yellow-500 fill-current" : "text-zinc-800"} />
                    ))}
                 </div>
                 
                 <p className="text-zinc-400">
                    {score === 3 ? "Blazing Fast! 🔥" : score === 2 ? "Good Speed!" : "Keep Practicing!"}
                 </p>

                 <div className="flex gap-4 justify-center mt-8">
                     <button onClick={startGame} className="px-6 py-3 bg-white text-black font-bold rounded-xl hover:scale-105 transition-transform">
                         Next Round
                     </button>
                 </div>
            </div>
        )}

    </div>
  );
}
