"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useTTS } from "@/hooks/useTTS";
import { Mic2, Square, Wand2, Play, Users, BarChart3, HelpCircle, X, ArrowRight, Bookmark, Volume2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import AudioWaveform from "@/components/AudioWaveform";
import { ApiClient } from "@/lib/api";

interface FeedbackData {
  next_task_prompt?: string;
  feedback_markdown?: string;
  correction_drill?: string;
  ideal_response?: string;
  user_transcript?: string;
  action_id?: string;
  stress_level?: number;
  target_keywords?: string[];
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
  
  // Part 2 Protocol State
  const [part2Phase, setPart2Phase] = useState<"IDLE" | "PREP" | "SPEAKING">("IDLE");
  const [timer, setTimer] = useState(0); // General purpose timer for Prep (60s) and Speak (120s)

  // Shadowing State
  const [shadowingMode, setShadowingMode] = useState(false);
  const getSentences = (text: string) => text.split(/[.!?]+/).filter(s => s.trim().length > 0).map(s => s.trim() + ".");

  // Hint State
  const [showHint, setShowHint] = useState(false);
  const [hintData, setHintData] = useState<{ vocabulary: string[]; starter: string; grammar_tip: string } | null>(null);
  const [isMasteryMode, setIsMasteryMode] = useState(false);

  // Lexical Expansion State
  const [activeMission, setActiveMission] = useState<string[]>([]);
  const [usedKeywords, setUsedKeywords] = useState<string[]>([]);
  const [silenceTimer, setSilenceTimer] = useState(0);

  // Advanced Learning: Shadowing Mastery
  const [shadowingIndex, setShadowingIndex] = useState<number | null>(null);
  const [shadowResults, setShadowResults] = useState<Record<number, any>>({});
  const [shadowProcessing, setShadowProcessing] = useState(false);

  // AI Notepad State
  const [notes, setNotes] = useState("");

  const hasNudgedRef = useRef(false);

  // Auto-Vocal Nudge Logic
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isRecording) {
      interval = setInterval(() => {
        setSilenceTimer(s => {
          const next = s + 1;
          // AUTO-VOCAL NUDGE: At 10 seconds of silence, offer a supportive prompt
          // Ref check ensures we only nudge ONCE per recording turn
          if (next === 10 && !isSpeaking && !hasNudgedRef.current) {
             hasNudgedRef.current = true;
             const nudges = [
               "And how did that make you feel?",
               "Tell me more about that.",
               "What happened next?",
               "Can you give me an example?"
             ];
             const randomNudge = nudges[Math.floor(Math.random() * nudges.length)];
             speak(randomNudge);
          }
          return next;
        });
      }, 1000);
    } else {
      setSilenceTimer(0);
      hasNudgedRef.current = false; // Reset for next turn
    }
    return () => clearInterval(interval);
  }, [isRecording, isSpeaking, speak]);

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
      setPart2Phase("IDLE"); // Reset protocol state
      setShadowingMode(false); // Reset shadowing
      
      // Use Dynamic Prompt from Backend
      const initialPrompt = session.current_prompt || "Welcome to the IELTS Speaking Mock Exam. Let's begin with Part 1. Can you tell me about your hometown?";
      
      if (session.initial_keywords) {
        setActiveMission(session.initial_keywords);
      }
      
      setFeedback({ next_task_prompt: initialPrompt });
      speak(initialPrompt);
      setNotes(""); // Clear notes for new exam
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
      if (shadowingIndex !== null) {
        // Handle Shadowing Submission
        const sentences = getSentences(feedback?.ideal_response || "");
        const targetText = sentences[shadowingIndex];
        
        const submitShadow = async () => {
          setShadowProcessing(true);
          try {
            const result = await ApiClient.analyzeShadowing(targetText, audioBlob);
            setShadowResults(prev => ({ ...prev, [shadowingIndex]: result }));
          } catch (e) {
            console.error(e);
          } finally {
            setShadowProcessing(false);
            setShadowingIndex(null);
            setAudioBlob(null);
          }
        };
        submitShadow();
      } else {
        // Handle standard Exam Submission
        const submit = async () => {
          setProcessing(true);
          try {
            const data = await ApiClient.submitExamAudio(sessionId, audioBlob);
            
            // Keyword Hit Detection (Against mission that was active during recording)
            const checkText = data.user_transcript || data.feedback_markdown || "";
            if (activeMission.length > 0 && checkText) {
               const lowerTranscript = checkText.toLowerCase();
               const hits = activeMission.filter(word => {
                  const regex = new RegExp(`\\b${word.toLowerCase()}\\b`, 'i');
                  return regex.test(lowerTranscript);
               });
               setUsedKeywords(hits);
            }

            setFeedback(data);
            
            // If we were in Mastery Mode and passed, exit it
            if (isMasteryMode && data.target_keywords) {
               setIsMasteryMode(false);
            }

            // Update Active Mission for the NEXT turn
            if (data.target_keywords) {
              setActiveMission(data.target_keywords);
            }

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
    }
  }, [audioBlob, sessionId, speak, setAudioBlob, shadowingIndex, activeMission, feedback]);

  // PART 2 PROTOCOL LOGIC
  useEffect(() => {
    // 1. Detect Entry into Part 2
    if (examPart === "PART_2" && part2Phase === "IDLE") {
        setPart2Phase("PREP");
        setTimer(60); // 1 Minute Prep
    }

    // 2. Timer Countdown
    let interval: NodeJS.Timeout;
    if (part2Phase === "PREP" && timer > 0) {
        interval = setInterval(() => setTimer(t => t - 1), 1000);
    } else if (part2Phase === "PREP" && timer === 0) {
        // Auto-Transition to Speaking
        setPart2Phase("SPEAKING");
        setTimer(120); // 2 Minutes Speaking
        startRecording();
    } else if (part2Phase === "SPEAKING" && timer > 0) {
        interval = setInterval(() => setTimer(t => t - 1), 1000);
    } else if (part2Phase === "SPEAKING" && timer === 0) {
        // Time's up! Force stop.
        stopRecording();
        // The existing useEffect will handle the audioBlob submission
    }

    return () => clearInterval(interval);
  }, [examPart, part2Phase, timer, startRecording, stopRecording]);



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
            <div className="flex items-center gap-6">
                <div className="flex items-center gap-4">
                    <span className="text-xs font-black text-red-600 uppercase tracking-widest px-2 py-1 bg-red-600/10 rounded">Live Session</span>
                    <span className="text-zinc-500 text-sm font-medium">Target: Band {targetBand}</span>
                </div>
                
                {/* PRESSURE GAUGE */}
                <div className="flex items-center gap-3 bg-zinc-900/50 px-4 py-1.5 rounded-full border border-zinc-800">
                    <div className="flex flex-col items-center">
                         <span className="text-[8px] font-black text-zinc-500 uppercase leading-none">Pressure</span>
                         <span className={`text-[10px] font-bold leading-none mt-1 ${(feedback?.stress_level || 0) > 0.7 ? 'text-red-500 animate-pulse' : 'text-emerald-500'}`}>
                            {Math.round((feedback?.stress_level || 0) * 100)}%
                         </span>
                    </div>
                    <div className="w-24 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                        <div 
                            className={`h-full transition-all duration-1000 ${(feedback?.stress_level || 0) > 0.7 ? 'bg-red-600' : (feedback?.stress_level || 0) > 0.4 ? 'bg-yellow-500' : 'bg-emerald-500'}`}
                            style={{ width: `${(feedback?.stress_level || 0) * 100}%` }}
                        />
                    </div>
                </div>
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
                
                {/* LEXICAL MISSION HUD */}
                {activeMission.length > 0 && (
                    <div className="flex flex-col items-center gap-3 mb-4 animate-in fade-in slide-in-from-top-4 duration-700">
                        <div className={`text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full border mb-1 flex items-center gap-2 ${isMasteryMode ? 'bg-amber-500/20 border-amber-500 text-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.2)]' : 'bg-zinc-900/50 border-zinc-800/50 text-zinc-500'}`}>
                            {isMasteryMode && <Wand2 size={10} className="animate-pulse" />}
                            {isMasteryMode ? 'Mastery Mode: Use These Now' : 'Current Mission: Active Lexis'}
                        </div>
                        <div className="flex gap-3">
                            {activeMission.map((word, i) => (
                                <div 
                                    key={i}
                                    className={`px-4 py-1.5 rounded-full border text-[10px] font-black uppercase tracking-widest transition-all duration-500 shadow-lg ${
                                        usedKeywords.some(u => u.toLowerCase() === word.toLowerCase()) 
                                        ? 'bg-amber-500 border-amber-400 text-black shadow-amber-500/40 scale-110' 
                                        : 'bg-zinc-900/80 border-zinc-700 text-zinc-400'
                                    }`}
                                >
                                    {word}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* CORRECTION CHALLENGE (The Mastery Drill) */}
                {feedback?.correction_drill && !isRecording && (
                    <div className="max-w-md w-full bg-amber-500/10 border border-amber-500/30 p-4 rounded-2xl animate-in zoom-in-95 duration-500 flex items-start gap-4">
                        <div className="p-2 bg-amber-500 rounded-lg text-black">
                            <Wand2 size={20} />
                        </div>
                        <div className="flex-1">
                            <h4 className="text-amber-500 text-[10px] font-black uppercase tracking-widest mb-1">Correction Challenge</h4>
                            <p className="text-zinc-300 text-xs font-medium leading-relaxed italic">
                                "{feedback.correction_drill}"
                            </p>
                        </div>
                    </div>
                )}

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
                <div className="h-24 w-full max-w-md flex flex-col items-center justify-center relative">
                    <AudioWaveform isRecording={isRecording} audioStream={stream} pulsing={isRecording && silenceTimer > 4} />
                    
                    {/* FLUENCY NUDGE */}
                    {isRecording && silenceTimer > 4 && (
                        <div className="absolute -top-12 text-amber-500 text-[10px] font-black uppercase tracking-widest animate-pulse">
                            Maintain your flow! Give an example...
                        </div>
                    )}
                </div>

                {/* CONTROLS & PACING RING */}
                <div className="flex items-center gap-8 relative">
                    {isRecording && (
                        <div 
                            className={`absolute inset-0 -m-4 border-4 rounded-full transition-all duration-700 ${
                                silenceTimer > 4 ? 'border-amber-500/50 scale-110 shadow-[0_0_30px_rgba(245,158,11,0.3)]' : 'border-red-600/30 scale-100'
                            }`}
                            style={{ 
                                animation: silenceTimer > 4 ? 'none' : 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite' 
                            }}
                        />
                    )}
                    
                    {!isRecording ? (
                        <button 
                            disabled={isSpeaking || processing}
                            onClick={startRecording}
                            className="relative z-10 w-24 h-24 bg-red-600 hover:bg-red-500 text-white rounded-full flex items-center justify-center shadow-[0_0_30px_rgba(220,38,38,0.4)] transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {processing ? <div className="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin"/> : <Mic2 size={32} />}
                        </button>
                    ) : (
                        <button 
                            onClick={stopRecording}
                            className="relative z-10 w-24 h-24 bg-zinc-100 hover:bg-white text-black rounded-full flex items-center justify-center shadow-2xl transition-all hover:scale-105 active:scale-95"
                        >
                            <Square size={32} fill="currentColor" />
                        </button>
                    )}
                </div>

                {/* CONDITIONAL UI: PART 2 vs STANDARD */}
                {examPart === "PART_2" && part2Phase !== "IDLE" ? (
                    <div className="w-full max-w-2xl bg-white text-black p-8 rounded-xl shadow-2xl relative overflow-hidden">
                        {/* Status Bar */}
                        <div className={`absolute top-0 left-0 w-full h-2 ${part2Phase === 'PREP' ? 'bg-blue-500' : 'bg-red-500'} transition-colors`} />
                        
                        <div className="flex justify-between items-start mb-6">
                            <div>
                                <h3 className="text-sm font-black uppercase tracking-widest text-zinc-500 mb-1">
                                    {part2Phase === "PREP" ? "Preparation Time" : "Long Turn"}
                                </h3>
                                <div className="text-5xl font-black tabular-nums tracking-tighter">
                                    {Math.floor(timer / 60)}:{(timer % 60).toString().padStart(2, '0')}
                                </div>
                            </div>
                            {part2Phase === "PREP" && (
                                <button 
                                    onClick={() => setTimer(0)} // Skip prep
                                    className="px-4 py-2 bg-black text-white text-xs font-bold uppercase rounded hover:bg-zinc-800"
                                >
                                    Start Speaking Now
                                </button>
                            )}
                        </div>

                        {/* Topic Card */}
                        <div className="bg-zinc-100 p-6 rounded-lg border-l-4 border-black mb-6">
                            <p className="font-serif text-xl italic leading-relaxed text-zinc-800">
                                {feedback?.next_task_prompt || "Describe a place you like to visit..."}
                            </p>
                            <ul className="mt-4 space-y-2 text-sm text-zinc-600 list-disc pl-5">
                                <li>You should say:</li>
                                <li>Where it is</li>
                                <li>When you went there</li>
                                <li>And explain why you liked it</li>
                            </ul>
                        </div>

                        {/* Story Scaffolding Arc */}
                        {part2Phase === "SPEAKING" && (
                            <div className="mt-8 pt-8 border-t border-zinc-200">
                                <p className="text-[10px] font-black uppercase text-zinc-400 mb-6 tracking-widest text-center">Mastery Scaffold: Story Arc</p>
                                <div className="flex justify-between relative px-4">
                                    <div className="absolute top-1/2 left-0 w-full h-0.5 bg-zinc-200 -translate-y-1/2 -z-10" />
                                    {[
                                        { label: "Intro", time: 120 },
                                        { label: "Core Story", time: 90 },
                                        { label: "Description", time: 60 },
                                        { label: "Feelings", time: 30 }
                                    ].map((m, i) => (
                                        <div key={i} className={`flex flex-col items-center gap-2 bg-zinc-100 px-2 rounded-lg transition-all duration-700 ${silenceTimer > 4 && timer <= m.time ? 'animate-pulse' : ''}`}>
                                            <div className={`w-4 h-4 rounded-full border-2 transition-all duration-500 ${timer <= m.time ? 'bg-emerald-500 border-emerald-500 scale-125 shadow-[0_0_10px_rgba(16,185,129,0.4)]' : 'bg-white border-zinc-300'}`} />
                                            <span className={`text-[9px] font-bold uppercase transition-colors ${timer <= m.time ? 'text-emerald-600' : 'text-zinc-400'}`}>{m.label}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* AI Notepad */}
                        <div className="mt-6 flex flex-col gap-2">
                            <div className="flex justify-between items-center bg-zinc-100 p-3 rounded-lg border border-zinc-200">
                                <span className="text-[10px] font-black uppercase text-zinc-400">AI Notepad (1-Minute Prep)</span>
                                {part2Phase === "SPEAKING" && (
                                    <span className="text-[10px] bg-red-100 text-red-600 px-2 py-0.5 rounded font-bold animate-pulse">Notes Locked</span>
                                )}
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <textarea
                                    value={notes}
                                    onChange={(e) => part2Phase === "PREP" && setNotes(e.target.value)}
                                    placeholder="Type your notes here..."
                                    className={`w-full h-40 p-4 text-sm font-medium border-0 focus:ring-2 focus:ring-blue-500 transition-all rounded-lg resize-none ${part2Phase === "SPEAKING" ? 'bg-zinc-50/50 text-zinc-400 cursor-not-allowed opacity-60' : 'bg-zinc-50 text-zinc-800 shadow-inner'}`}
                                />
                                <div className={`bg-blue-50/50 rounded-lg p-4 flex flex-col gap-3 transition-all duration-700 ${silenceTimer > 4 ? 'ring-2 ring-blue-400 ring-offset-2 animate-pulse shadow-lg bg-blue-100' : ''}`}>
                                    <span className={`text-[10px] font-black uppercase ${silenceTimer > 4 ? 'text-blue-600' : 'text-blue-400'}`}>Coach: Think of...</span>
                                    <ul className="space-y-2">
                                        {[
                                            "5 Senses (Smell, Sound, etc.)",
                                            "A specific conflict or challenge",
                                            "How did it change you?",
                                            "Emotional peak (Excitement/Loss)"
                                        ].map((item, id) => (
                                            <li key={id} className={`flex items-center gap-2 text-[11px] font-bold transition-colors ${silenceTimer > 4 ? 'text-blue-800' : 'text-blue-700/70'}`}>
                                                <div className={`w-1 h-1 rounded-full transition-all ${silenceTimer > 4 ? 'bg-blue-600 scale-150' : 'bg-blue-400'}`} />
                                                {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        </div>

                        {/* Visual Pressure Hook */}
                        {part2Phase === "SPEAKING" && (
                            <div className="mt-8 w-full h-1 bg-zinc-200 rounded-full overflow-hidden">
                                <div 
                                    className={`h-full transition-all duration-1000 ${timer < 20 ? 'bg-red-500' : timer < 60 ? 'bg-yellow-500' : 'bg-emerald-500'}`}
                                    style={{ width: `${(timer / 120) * 100}%` }}
                                />
                            </div>
                        )}
                        
                        {part2Phase === "PREP" && (
                            <div className="text-xs text-zinc-400 font-medium mt-4">
                                Use this time to take notes. Do not speak yet.
                            </div>
                        )}
                    </div>
                ) : (
                    /* STANDARD UI PANIC BUTTON / HINT */
                    <button 
                        onClick={handleGetHint}
                        className="absolute bottom-12 right-12 flex items-center gap-2 px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-full text-zinc-500 hover:text-white hover:border-zinc-700 transition-all text-xs font-bold uppercase tracking-widest"
                    >
                        <HelpCircle size={16} /> Idea Generator
                    </button>
                )}

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
                                    {(hintData.vocabulary as string[]).map((w: string, i: number) => (
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
                        <div className="flex justify-between items-center">
                            <h4 className="text-xs font-black text-emerald-500 uppercase tracking-widest flex items-center gap-2">
                                <Users size={14}/> Band 9 Rewrite (The Mirror)
                            </h4>
                            <button 
                                onClick={() => setShadowingMode(!shadowingMode)}
                                className={`px-3 py-1 rounded-full text-[10px] font-bold border transition-all ${shadowingMode ? 'bg-emerald-600 border-emerald-500 text-white' : 'bg-transparent border-zinc-700 text-zinc-500 hover:text-white hover:border-zinc-500'}`}
                            >
                                {shadowingMode ? "Exit Shadowing" : "Shadowing Lab"}
                            </button>
                        </div>

                        {!shadowingMode ? (
                            <div className="p-6 bg-red-600/5 border border-red-600/20 rounded-2xl relative group overflow-hidden">
                                <div className="absolute top-4 right-4 text-red-600/20"><Volume2 size={48} /></div>
                                <div className="absolute inset-0 bg-red-600/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                                <h4 className="text-[10px] font-black uppercase text-red-500 tracking-widest mb-3">Your Potential (Band 9 Refined)</h4>
                                <p className="text-white text-sm italic leading-relaxed relative z-10 font-medium">
                                    "{feedback.ideal_response || "Excellent answer. Focus on expanding your Part 3 responses."}"
                                </p>
                                <button 
                                    disabled={isSpeaking || processing}
                                    onClick={() => speak(feedback.ideal_response || "")}
                                    className="mt-6 flex items-center justify-center gap-3 w-full py-4 bg-red-600 hover:bg-red-500 text-white rounded-xl font-black uppercase tracking-widest transition-all shadow-xl hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:grayscale disabled:cursor-not-allowed"
                                >
                                    <Volume2 size={20} className={isSpeaking ? "" : "animate-pulse"} /> {isSpeaking ? "Coaching..." : "Play My Potential"}
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-3 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
                                {getSentences(feedback.ideal_response || "").map((s, i) => (
                                    <div key={i} className={`p-4 bg-zinc-900 border rounded-xl flex justify-between items-center group transition-all ${shadowingIndex === i ? 'border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.2)] bg-red-500/5' : 'border-zinc-800 hover:border-emerald-500/50'}`}>
                                        <div className="max-w-[80%] space-y-2">
                                            <p className="text-xs text-zinc-300 leading-relaxed">{s}</p>
                                            {shadowResults[i] && (
                                                <div className="flex items-center gap-3">
                                                    <span className={`text-[10px] font-black uppercase ${shadowResults[i].is_passed ? 'text-emerald-500' : 'text-amber-500'}`}>
                                                        Mastery: {Math.round(shadowResults[i].mastery_score * 100)}%
                                                    </span>
                                                    <div className="h-1 w-24 bg-zinc-800 rounded-full overflow-hidden">
                                                        <div 
                                                            className={`h-full transition-all duration-1000 ${shadowResults[i].is_passed ? 'bg-emerald-500' : 'bg-amber-500'}`}
                                                            style={{ width: `${shadowResults[i].mastery_score * 100}%` }}
                                                        />
                                                    </div>
                                                </div>
                                            )}
                                            {shadowResults[i] && shadowResults[i].mastery_score > 0 && (
                                                <div className="flex gap-1 mt-1">
                                                    {[...Array(20)].map((_, idx) => (
                                                        <div 
                                                            key={idx}
                                                            className={`h-2 w-1 rounded-full transition-all duration-700 ${
                                                                shadowResults[i].mastery_score > (idx / 20) 
                                                                ? (shadowResults[i].is_passed ? 'bg-emerald-500' : 'bg-amber-500') 
                                                                : 'bg-zinc-800'
                                                            }`}
                                                            style={{ transitionDelay: `${idx * 50}ms` }}
                                                        />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <div className="flex gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                                            <button 
                                                onClick={() => speak(s)}
                                                className="p-2 bg-emerald-600/20 text-emerald-500 rounded-lg hover:bg-emerald-600/40"
                                            >
                                                <Play size={12} fill="currentColor"/>
                                            </button>
                                            <button 
                                                disabled={shadowProcessing}
                                                onClick={() => {
                                                    if (shadowingIndex === i) {
                                                        stopRecording();
                                                    } else {
                                                        setShadowingIndex(i);
                                                        startRecording();
                                                    }
                                                }}
                                                className={`p-2 rounded-lg transition-all ${shadowingIndex === i ? 'bg-red-600 text-white animate-pulse' : 'bg-zinc-800 text-zinc-400 hover:text-white'}`}
                                            >
                                                {shadowProcessing && shadowingIndex === i ? (
                                                    <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"/>
                                                ) : (
                                                    <Mic2 size={12}/>
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="flex gap-4 mt-8">
                            <button onClick={() => { setFeedback(null); setShadowingMode(false); }} className="flex-1 py-3 bg-zinc-800 text-zinc-400 font-bold text-xs uppercase tracking-widest rounded-xl hover:bg-zinc-700 transition-all">
                                Next Question <ArrowRight size={14} className="inline ml-2"/>
                            </button>
                            <button 
                                onClick={() => {
                                    setFeedback(null);
                                    setShadowingMode(false);
                                    setIsMasteryMode(true); // Enter Mastery Mode
                                    speak(feedback.next_task_prompt || "Try again.");
                                }} 
                                className="flex-1 py-3 bg-emerald-600 text-white font-bold text-xs uppercase tracking-widest rounded-xl hover:bg-emerald-500 transition-all shadow-lg flex items-center justify-center gap-2"
                            >
                                <Wand2 size={14} /> Mastery Retake
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
