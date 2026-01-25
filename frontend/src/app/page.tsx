"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useTTS } from "@/hooks/useTTS";
import { Mic2, Square, Wand2, Play, Users, BarChart3, HelpCircle, X, ArrowRight, Bookmark } from "lucide-react";
import ReactMarkdown from "react-markdown";
import AudioWaveform from "@/components/AudioWaveform";
import { ApiClient } from "@/lib/api";

interface FeedbackData {
  next_task_prompt?: string;
  feedback_markdown?: string;
  ideal_response?: string;
  action_id?: string;
}

export default function TrainingCockpit() {
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
  const [examPart, setExamPart] = useState<"INTRO" | "PART_1" | "PART_2" | "PART_3" | "FINISHED">("INTRO");
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [processing, setProcessing] = useState(false);
  const [showStats, setShowStats] = useState(false);
  const [targetBand, setTargetBand] = useState("7.5");
  const [finalScore, setFinalScore] = useState<number | null>(null);
  
  // Vault State
  const [showVault, setShowVault] = useState(false);
  const [loadingVault, setLoadingVault] = useState(false);
  
  interface VocabularyItem {
    id: number;
    word: string;
    definition: string;
    context_sentence?: string;
    mastery_level: number;
  }
  const [vocabList, setVocabList] = useState<VocabularyItem[]>([]);

  // Hint State
  const [showHint, setShowHint] = useState(false);
  const [hintData, setHintData] = useState<{ vocabulary: string[]; starter: string; grammar_tip: string } | null>(null);

  // Initial Load
  useEffect(() => {
    ApiClient.getStats().then(s => {
        if(s.target_band) setTargetBand(s.target_band);
    }).catch(e => console.error(e));
  }, []);

  const startExam = async () => {
    try {
      const session = await ApiClient.startExam("default_user", "FULL_MOCK");
      setSessionId(session.id);
      setExamPart("PART_1");
      const initialPrompt = "Welcome to the IELTS Speaking Mock Exam. Let's begin with Part 1. Can you tell me about your hometown?";
      setFeedback({ next_task_prompt: initialPrompt });
      speak(initialPrompt);
    } catch (e) {
      console.error(e);
    }
  };

  const handleGetHint = async () => {
    if (!sessionId) return;
    try {
      const data = await ApiClient.getHint(sessionId);
      setHintData(data);
      setShowHint(true);
    } catch (e) {
      console.error(e);
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

          const session = await ApiClient.getExamStatus(sessionId);
          
          if (session.status === "COMPLETED") {
            setExamPart("FINISHED");
            if (session.overall_band_score) setFinalScore(session.overall_band_score);
            setShowStats(true); 
          } else {
             const validParts = ["PART_1", "PART_2", "PART_3"];
             if (validParts.includes(session.current_part)) {
               setExamPart(session.current_part as any);
             }
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
  }, [audioBlob, sessionId, speak, setAudioBlob]);

  // IDLE STATE
  if (examPart === "INTRO" || examPart === "FINISHED") {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-[#0d0d12] p-6 relative overflow-hidden">
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-red-600/5 rounded-full blur-[100px]" />
            </div>

            <div className="z-10 text-center space-y-12">
                <div>
                    <h1 className="text-5xl font-black text-white tracking-tighter uppercase mb-4">
                        IELTS <span className="text-red-600">Cockpit</span>
                    </h1>
                    <p className="text-zinc-500 font-medium">Target Band {targetBand} • Ready to train?</p>
                </div>

                <div className="group relative w-48 h-48 mx-auto">
                    <div className="absolute inset-0 bg-red-600/20 rounded-full blur-xl group-hover:bg-red-600/30 transition-all duration-500" />
                    <button 
                        onClick={startExam}
                        className="relative w-full h-full bg-[#12121a] border-2 border-red-600 rounded-full flex flex-col items-center justify-center hover:scale-105 transition-all cursor-pointer shadow-[0_0_40px_rgba(220,38,38,0.2)]"
                    >
                        <Play size={48} className="text-white fill-white ml-2" />
                        <span className="text-xs font-black text-red-500 uppercase tracking-widest mt-4">Start Mock</span>
                    </button>
                </div>

                <div className="flex gap-4 justify-center">
                    <button onClick={() => setShowStats(true)} className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-zinc-500 hover:text-white hover:border-zinc-600 transition-all group relative">
                        <BarChart3 size={24} />
                        <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-black text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">Stats</span>
                    </button>
                    <button onClick={() => {
                        setShowVault(true);
                        setLoadingVault(true);
                        ApiClient.getVocabulary()
                            .then((data) => {
                                setVocabList(data);
                                setLoadingVault(false);
                            })
                            .catch((err) => {
                                console.error(err);
                                setLoadingVault(false);
                            });
                    }} className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-zinc-500 hover:text-white hover:border-zinc-600 transition-all group relative">
                        <Bookmark size={24} />
                        <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-black text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">My Vault</span>
                    </button>
                    <button className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 text-zinc-500 hover:text-white hover:border-zinc-600 transition-all group relative">
                        <Users size={24} />
                         <span className="absolute -top-10 left-1/2 -translate-x-1/2 bg-black text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">Community</span>
                    </button>
                </div>
            </div>

            {/* Vocabulary Vault Modal */}
            {showVault && (
                <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in">
                    <div className="bg-[#18181b] w-full max-w-4xl h-[80vh] rounded-3xl border border-zinc-800 flex flex-col relative overflow-hidden">
                        <div className="p-8 border-b border-zinc-800 flex justify-between items-center">
                            <div>
                                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                                    <Bookmark className="fill-emerald-500 text-emerald-500"/> Word Vault
                                </h2>
                                <p className="text-zinc-500 text-sm mt-1">Your active collection of high-band vocabulary.</p>
                            </div>
                            <button onClick={() => setShowVault(false)} className="text-zinc-500 hover:text-white"><X size={24}/></button>
                        </div>
                        
                        <div className="flex-1 overflow-y-auto p-8 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 custom-scrollbar">
                            {loadingVault ? (
                                <div className="col-span-full flex flex-col items-center justify-center h-full">
                                    <div className="w-8 h-8 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mb-4"/>
                                    <p className="text-zinc-500 text-sm">Opening Vault...</p>
                                </div>
                            ) : vocabList.length === 0 ? (
                                <div className="col-span-full flex flex-col items-center justify-center text-zinc-600 py-20">
                                    <Bookmark size={48} className="mb-4 opacity-20"/>
                                    <p>Your vault is empty.</p>
                                    <p className="text-sm">Use the "Idea Generator" during exams to save words.</p>
                                </div>
                            ) : (
                                vocabList.map((item, idx) => (
                                    <div key={idx} className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-xl hover:border-zinc-600 transition-all group">
                                        <div className="flex justify-between items-start mb-2">
                                            <h3 className="text-lg font-bold text-white">{item.word}</h3>
                                            <span className="text-[10px] font-black text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded uppercase">
                                                Lvl {item.mastery_level || 1}
                                            </span>
                                        </div>
                                        <p className="text-zinc-500 text-sm italic mb-4">"{item.context_sentence}"</p>
                                        <p className="text-zinc-400 text-xs line-clamp-2">{item.definition}</p>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Stats Modal Overlay */}
            {showStats && (
                <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
                    <div className="bg-[#18181b] w-full max-w-2xl rounded-3xl border border-zinc-800 p-8 relative">
                        <button onClick={() => setShowStats(false)} className="absolute top-4 right-4 text-zinc-500 hover:text-white">
                            <X size={24} />
                        </button>
                        <h2 className="text-2xl font-bold text-white mb-4">Performance Monitor</h2>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="p-6 bg-zinc-900 rounded-2xl border border-zinc-800">
                                <p className="text-zinc-500 text-xs uppercase font-bold">Latest Session</p>
                                <p className="text-4xl font-black text-white mt-2">
                                    {finalScore ? finalScore.toFixed(1) : "Incomplete"}
                                </p>
                            </div>
                            <div className="p-6 bg-zinc-900 rounded-2xl border border-zinc-800">
                                <p className="text-zinc-500 text-xs uppercase font-bold">Target Gap</p>
                                <p className={`text-4xl font-black mt-2 ${finalScore && finalScore >= parseFloat(targetBand) ? 'text-emerald-500' : 'text-red-500'}`}>
                                    {finalScore ? (finalScore - parseFloat(targetBand)).toFixed(1) : "..."} 
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
  }

  // ACTIVE EXAM STATE
  return (
    <div className="min-h-screen bg-[#0d0d12] flex flex-col relative overflow-hidden">
        
        {/* TOP HUD */}
        <div className="w-full h-16 border-b border-zinc-900 flex justify-between items-center px-6 bg-[#0d0d12]/80 backdrop-blur-md z-20">
            <div className="flex items-center gap-4">
                <span className="text-xs font-black text-red-600 uppercase tracking-widest px-2 py-1 bg-red-600/10 rounded">Live Session</span>
                <span className="text-zinc-500 text-sm font-medium">Target: Band {targetBand}</span>
            </div>
            <div className="flex gap-2">
                <PartBadge part="PART_1" current={examPart} label="Interview" />
                <PartBadge part="PART_2" current={examPart} label="Long Turn" />
                <PartBadge part="PART_3" current={examPart} label="Discussion" />
            </div>
        </div>

        {/* MAIN COCKPIT AREA */}
        <div className="flex-1 flex flex-col relative">
            
            {/* BACKGROUND EXAMINER VISUAL */}
            <div className="absolute inset-0 flex items-center justify-center opacity-30">
                 <div className={`w-96 h-96 border border-zinc-800 rounded-full flex items-center justify-center transition-all duration-500 ${isSpeaking ? 'scale-110 border-red-500/50' : 'scale-100'}`}>
                    <div className={`w-64 h-64 bg-zinc-900 rounded-full flex items-center justify-center transition-all duration-300 ${isSpeaking ? 'bg-red-900/20' : ''}`}>
                        <Wand2 size={64} className="text-zinc-700" />
                    </div>
                 </div>
            </div>

            {/* STRUCTURE MAP (Rules of Engagement) */}
            <div className="absolute top-8 left-8 max-w-xs space-y-2 opacity-50 hover:opacity-100 transition-opacity">
                <h3 className="text-zinc-400 text-xs font-bold uppercase tracking-widest">Current Mission</h3>
                <p className="text-zinc-500 text-xs leading-relaxed">
                    {examPart === "PART_1" && "Answer directly and naturally. Keep fluency high. Don't overthink."}
                    {examPart === "PART_2" && "Speak continuously for 2 minutes. Structure your story: Beginning, Middle, End."}
                    {examPart === "PART_3" && "Develop abstract ideas. Use examples. Contrast opinions."}
                </p>
            </div>

            {/* MAIN INTERACTION ZONE */}
            <div className="relative z-10 flex-1 flex flex-col items-center justify-center p-8 space-y-12">
                
                {/* PROMPT */}
                <div className="text-center space-y-6 max-w-2xl">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-800 bg-zinc-900/50 text-zinc-400 text-[10px] font-bold uppercase tracking-widest">
                        Examiner Question
                    </div>
                    <h2 className="text-3xl md:text-4xl font-medium text-white leading-tight">
                        {feedback?.next_task_prompt || "Listening..."}
                    </h2>
                </div>

                {/* AUDIO VISUALIZER */}
                <div className="h-24 w-full max-w-md flex items-center justify-center">
                    <AudioWaveform isRecording={isRecording} audioStream={stream} />
                </div>

                {/* CONTROLS */}
                <div className="flex items-center gap-8">
                    {!isRecording ? (
                        <button 
                            disabled={isSpeaking || processing}
                            onClick={startRecording}
                            className="w-24 h-24 bg-red-600 hover:bg-red-500 text-white rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(220,38,38,0.4)] transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {processing ? <div className="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin"/> : <Mic2 size={32} />}
                        </button>
                    ) : (
                        <button 
                            onClick={stopRecording}
                            className="w-24 h-24 bg-zinc-100 hover:bg-white text-black rounded-full flex items-center justify-center shadow-2xl transition-all hover:scale-105 active:scale-95"
                        >
                            <Square size={32} fill="currentColor" />
                        </button>
                    )}
                </div>

                {/* PANIC BUTTON / HINT */}
                <button 
                    onClick={handleGetHint}
                    className="absolute bottom-12 right-12 flex items-center gap-2 px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-full text-zinc-500 hover:text-white hover:border-zinc-700 transition-all text-xs font-bold uppercase tracking-widest"
                >
                    <HelpCircle size={16} /> Idea Generator
                </button>

                {/* HINT CARD POPUP */}
                {showHint && hintData && (
                    <div className="absolute bottom-24 right-12 w-80 bg-zinc-900 border border-zinc-800 p-6 rounded-3xl shadow-2xl animate-in slide-in-from-bottom-4">
                        <div className="flex justify-between items-start mb-4">
                            <span className="text-xs font-bold text-yellow-500 uppercase">Emergency Ideas</span>
                            <button onClick={() => setShowHint(false)}><X size={14} className="text-zinc-500"/></button>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <p className="text-[10px] text-zinc-500 uppercase font-black mb-2">Key Vocabulary</p>
                                <div className="flex flex-wrap gap-2">
                                    {hintData.vocabulary.map((w,i) => (
                                        <button 
                                            key={i} 
                                            onClick={(e) => {
                                                e.currentTarget.classList.add('text-emerald-500', 'bg-emerald-500/10');
                                                ApiClient.saveVocabulary(w, hintData.starter);
                                            }}
                                            className="px-2 py-1 bg-zinc-800 text-zinc-300 text-xs rounded hover:text-white hover:bg-zinc-700 flex items-center gap-1 group transition-all"
                                        >
                                            {w} <Bookmark size={8} className="opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <div>
                                <p className="text-[10px] text-zinc-500 uppercase font-black mb-2">Structure Tip</p>
                                <p className="text-zinc-300 text-xs italic">"{hintData.starter}"</p>
                            </div>
                        </div>
                    </div>
                )}

            </div>
        </div>

        {/* FEEDBACK MIRROR (Slide up on feedback) */}
        {feedback?.feedback_markdown && (
            <div className="absolute bottom-0 left-0 w-full bg-[#18181b] border-t border-zinc-800 p-8 transform transition-transform duration-500 z-30 animate-in slide-in-from-bottom">
                <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12">
                    
                    {/* LEFT: Analysis */}
                    <div className="space-y-4">
                        <h4 className="text-xs font-black text-red-500 uppercase tracking-widest flex items-center gap-2">
                            <Wand2 size={14}/> AI Examiner Analysis
                        </h4>
                        <div className="prose prose-invert prose-sm max-w-none prose-p:text-zinc-400 prose-strong:text-white h-48 overflow-y-auto pr-2 custom-scrollbar">
                            <ReactMarkdown>{feedback.feedback_markdown}</ReactMarkdown>
                        </div>
                    </div>

                    {/* RIGHT: The Band 9 Mirror */}
                    <div className="space-y-4 border-l border-zinc-800 pl-12">
                        <h4 className="text-xs font-black text-emerald-500 uppercase tracking-widest flex items-center gap-2">
                            <Users size={14}/> Band 9 Rewrite (The Mirror)
                        </h4>
                        <div className="p-6 bg-emerald-500/5 border border-emerald-500/20 rounded-2xl relative">
                            <div className="absolute top-4 right-4 text-emerald-500/20"><Users size={48} /></div>
                            <p className="text-emerald-100 text-sm italic leading-relaxed relative z-10">
                                "{feedback.ideal_response || "Excellent answer. Keep up the fluency."}"
                            </p>
                            <button 
                                onClick={() => speak(feedback.ideal_response || "Excellent answer.")}
                                className="mt-4 flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-widest hover:text-white transition-colors"
                            >
                                <Play size={12} className="fill-current" /> Listen to Native Speaker
                            </button>
                        </div>
                        <div className="flex gap-4 mt-8">
                            <button onClick={() => setFeedback(null)} className="flex-1 py-3 bg-zinc-800 text-zinc-400 font-bold text-xs uppercase tracking-widest rounded-xl hover:bg-zinc-700 transition-all">
                                Next Question <ArrowRight size={14} className="inline ml-2"/>
                            </button>
                            <button 
                                onClick={() => {
                                    setFeedback(null);
                                    speak(feedback.next_task_prompt || "Try again.");
                                }} 
                                className="flex-1 py-3 bg-emerald-600 text-white font-bold text-xs uppercase tracking-widest rounded-xl hover:bg-emerald-500 transition-all shadow-lg flex items-center justify-center gap-2"
                            >
                                <Play size={14} /> Retry Immediately
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        )}

    </div>
  );
}

function PartBadge({ part, current, label }: { part: string, current: string, label: string }) {
    const isActive = part === current;
    return (
        <div className={`px-3 py-1 rounded text-[10px] font-black uppercase tracking-widest transition-colors ${isActive ? 'bg-zinc-100 text-black' : 'bg-zinc-900 text-zinc-600'}`}>
            {label}
        </div>
    )
}
