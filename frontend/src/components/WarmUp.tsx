"use client";

import { useState, useEffect } from "react";
import { Zap, Volume2, Mic2, ArrowRight, X, Sparkles } from "lucide-react";

interface WarmUpProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete: () => void;
  dueWords: { word: string; definition: string }[];
}

export function WarmUp({ isOpen, onClose, onComplete, dueWords }: WarmUpProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [timeLeft, setTimeLeft] = useState(60);
  const [isActivated, setIsActivated] = useState(false);

  // Countdown timer
  useEffect(() => {
    if (!isOpen || isActivated) return;
    
    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          setIsActivated(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(timer);
  }, [isOpen, isActivated]);

  if (!isOpen) return null;

  const words = dueWords.length > 0 ? dueWords : [
    { word: "nevertheless", definition: "in spite of that; notwithstanding" },
    { word: "meticulous", definition: "showing great attention to detail" },
    { word: "encompass", definition: "surround and have within" }
  ];

  const handleSpeak = (text: string) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      speechSynthesis.speak(utterance);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-700 rounded-3xl w-full max-w-2xl p-8 relative overflow-hidden">
        {/* Background Effect */}
        <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/5 via-transparent to-amber-500/5 pointer-events-none" />
        
        <button onClick={onClose} className="absolute top-6 right-6 text-zinc-500 hover:text-white transition-colors z-10">
          <X size={24} />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6 relative z-10">
          <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
            <Zap className="text-emerald-500" size={24} />
          </div>
          <div>
            <h2 className="text-xl font-black text-white">Pre-Flight Activation</h2>
            <p className="text-zinc-500 text-sm">Prime your brain before takeoff</p>
          </div>
        </div>

        {/* Timer */}
        <div className="flex justify-center mb-8">
          <div className={`w-24 h-24 rounded-full border-4 flex items-center justify-center transition-all duration-500 ${
            isActivated ? 'border-emerald-500 bg-emerald-500/10' : 'border-zinc-700'
          }`}>
            {isActivated ? (
              <Sparkles className="text-emerald-500 animate-pulse" size={32} />
            ) : (
              <span className="text-3xl font-black text-white">{timeLeft}</span>
            )}
          </div>
        </div>

        {/* Word Cards */}
        <div className="space-y-4 mb-8">
          <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest">Today's Target Vocabulary</h3>
          {words.map((w, i) => (
            <div 
              key={i}
              className={`p-4 bg-zinc-800/50 border rounded-xl flex justify-between items-center transition-all ${
                currentStep === i ? 'border-emerald-500 shadow-[0_0_20px_rgba(16,185,129,0.2)]' : 'border-zinc-700'
              }`}
            >
              <div>
                <span className="text-white font-bold text-lg">{w.word}</span>
                <p className="text-zinc-500 text-sm">{w.definition}</p>
              </div>
              <button 
                onClick={() => {
                  handleSpeak(w.word);
                  setCurrentStep(i);
                }}
                className="p-3 bg-zinc-700 hover:bg-emerald-600 rounded-xl transition-all"
              >
                <Volume2 size={18} className="text-white" />
              </button>
            </div>
          ))}
        </div>

        {/* Prompt */}
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 mb-6">
          <h4 className="text-amber-500 font-black uppercase text-xs tracking-widest mb-2">Quick Challenge</h4>
          <p className="text-white font-medium">
            Say a sentence using "<span className="text-amber-400">{words[currentStep]?.word || 'nevertheless'}</span>"
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button 
            onClick={onClose}
            className="flex-1 py-3 bg-zinc-800 text-zinc-400 rounded-xl font-bold text-sm uppercase tracking-widest hover:bg-zinc-700 transition-all"
          >
            Skip
          </button>
          <button 
            onClick={onComplete}
            className="flex-1 py-3 bg-emerald-600 text-white rounded-xl font-bold text-sm uppercase tracking-widest hover:bg-emerald-500 transition-all flex items-center justify-center gap-2"
          >
            I'm Ready <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
