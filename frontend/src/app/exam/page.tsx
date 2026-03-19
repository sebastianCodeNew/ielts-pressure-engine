"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAudioRecorder } from "@/hooks/useAudioRecorder";
import { useTTS } from "@/hooks/useTTS";
import { Mic2, Square, Wand2, ArrowRight, Timer, AlertCircle, Lightbulb, CheckCircle2, Play, RotateCcw, Pencil, Volume2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import AudioWaveform from "@/components/AudioWaveform";
import { ApiClient } from "@/lib/api";
import { Intervention } from "@/lib/types";
import { SmartDiff } from "@/components/SmartDiff";

// --- TYPES ---
interface FeedbackData extends Intervention {
  stress_level?: number;
}

// --- VOCABULARY HEATMAP ---
// Highlights words: gold = Band 8+ vocabulary, default = basic words
const BAND8_WORDS = new Set([
  "furthermore","moreover","nevertheless","consequently","significantly",
  "predominantly","substantially","comprehensive","meticulous","exemplify",
  "innovative","profound","paramount","encompass","articulate",
  "exquisite","ubiquitous","facilitate","augment","eloquent",
  "intricate","nuanced","pivotal","compelling","unprecedented",
  "rejuvenating","picturesque","cosmopolitan","quintessential","indispensable",
  "elaborate","versatile","contemporary","aesthetic","phenomenal",
  "intriguing","captivating","remarkable","exceptional","gratifying",
  "detrimental","inadvertent","inevitable","commendable","formidable",
]);

function HighlightedTranscript({ text, keywordsHit }: { text: string; keywordsHit?: string[] }) {
  // Sort phrases by length descending to ensure longest phrases are matched first
  const hitPhrases = useMemo(() => 
    (keywordsHit || [])
      .map(k => k.toLowerCase())
      .sort((a, b) => b.length - a.length), 
    [keywordsHit]
  );
  
  if (!text) return null;

  // Strategy: Replace phrases with markers to keep them intact, then split and map
  let highlighted = [{ text, type: "default" }];

  // 1. Mark Keyword Hits (Phrases)
  hitPhrases.forEach(phrase => {
    if (!phrase.trim()) return;
    const newParts: { text: string; type: string }[] = [];
    highlighted.forEach(part => {
      if (part.type !== "default") {
        newParts.push(part);
        return;
      }
      const regex = new RegExp(`(\\b${phrase.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')}\\b)`, "gi");
      const subParts = part.text.split(regex);
      subParts.forEach(sub => {
        if (sub.toLowerCase() === phrase) {
          newParts.push({ text: sub, type: "kw-hit" });
        } else if (sub) {
          newParts.push({ text: sub, type: "default" });
        }
      });
    });
    highlighted = newParts;
  });

  // 2. Mark Band 8 words for remaining "default" parts
  const finalParts: { text: string; type: string }[] = [];
  highlighted.forEach(part => {
    if (part.type !== "default") {
      finalParts.push(part);
      return;
    }
    const words = part.text.split(/(\s+)/);
    words.forEach(word => {
      const clean = word.replace(/[^a-zA-Z]/g, "").toLowerCase();
      if (clean && BAND8_WORDS.has(clean)) {
        finalParts.push({ text: word, type: "band8" });
      } else {
        finalParts.push({ text: word, type: "default" });
      }
    });
  });

  return (
    <span>
      {finalParts.map((part, i) => {
        if (part.type === "kw-hit") {
          return <span key={i} className="text-green-400 font-bold bg-green-900/30 px-1 rounded">{part.text}</span>;
        }
        if (part.type === "band8") {
          return <span key={i} className="text-yellow-400 font-bold bg-yellow-900/20 px-1 rounded">{part.text}</span>;
        }
        return <span key={i} className="text-zinc-400">{part.text}</span>;
      })}
    </span>
  );
}

// --- MAIN COMPONENT ---
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
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [examPart, setExamPart] = useState<"INTRO" | "PART_1" | "PART_2" | "PART_3" | "FINISHED">("INTRO");
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [processing, setProcessing] = useState(false);
  const [stopping, setStopping] = useState(false);
  const processingRef = useRef(false);
  const startingRef = useRef(false);
  const processedBlobRef = useRef<Blob | null>(null);

  // Educational Review Flow
  const [isReviewing, setIsReviewing] = useState(false);
  const [pendingNextPrompt, setPendingNextPrompt] = useState<string | null>(null);
  const [isRetaking, setIsRetaking] = useState(false);

  // Audio Mirror
  const [isPlayingMirror, setIsPlayingMirror] = useState(false);
  const audioMirrorRef = useRef<HTMLAudioElement | null>(null);

  // Checkpoint Words HUD State
  const [wordBank, setWordBank] = useState<{ word: string; translation?: string; meaning?: string }[]>([]);

  // Prep Phase State (Part 2)
  const [isPrepPhase, setIsPrepPhase] = useState(false);
  const [prepTimer, setPrepTimer] = useState(0);
  const [prepNotes, setPrepNotes] = useState("");

  // User Notification State
  const [errorStatus, setErrorStatus] = useState<string | null>(null);

  // Hint State
  const [showHint, setShowHint] = useState(false);
  const [hintData, setHintData] = useState<{ vocabulary: string[]; starter: string; grammar_tip: string } | null>(null);

  // U5: Response Timer for Part 1/3
  const [responseTimer, setResponseTimer] = useState(0);
  const responseTimerRef = useRef<NodeJS.Timeout | null>(null);

  // --- LIFECYCLE ---
  useEffect(() => {
    const savedSessionId = localStorage.getItem("ielts_exam_session_id");
    if (savedSessionId) {
      setSessionId(savedSessionId);
      ApiClient.getExamStatus(savedSessionId).then(async (data) => {
        setExamPart(data.current_part as any);
        if (data.status === "COMPLETED") {
          setExamPart("FINISHED");
        } else {
          if (data.checkpoint_words && data.checkpoint_words.length > 0) {
            const words: string[] = data.checkpoint_words;
            const tr: string[] = data.checkpoint_words_translated || [];
            const mn: string[] = data.checkpoint_words_meanings || [];
            setWordBank(words.map((w: string, i: number) => ({
              word: w,
              translation: tr[i],
              meaning: mn[i]
            })));
          } else {
            setWordBank([]);
          }

          // Hardening Path: If we have an existing session, check if the last attempt needs review
          const history = await ApiClient.getDetailedHistory("default_user");
          const lastAttempt = history[0];
          
          if (lastAttempt && lastAttempt.session_id === savedSessionId && !data.current_prompt?.startsWith("Welcome")) {
            setFeedback({
              next_task_prompt: data.current_prompt,
              next_task_prompt_translated: data.current_prompt_translated,
              feedback_markdown: lastAttempt.feedback,
              feedback_translated: lastAttempt.feedback_translated,
              user_transcript: lastAttempt.your_answer,
              user_transcript_translated: lastAttempt.your_answer_translated,
              ideal_response: lastAttempt.improved_answer,
              ideal_response_translated: lastAttempt.improved_answer_translated,
              user_audio_url: lastAttempt.audio_url,
              keywords_hit: lastAttempt.keywords_hit
            });
            setIsReviewing(true);
            setPendingNextPrompt(data.current_prompt || null);

            // Robust Part 2 transition recovery: If session moved to P2 but last attempt was P1
            if (data.current_part === "PART_2" && lastAttempt.part === "PART_1") {
              localStorage.setItem("pending_part2_prep", "true");
            }
          } else {
            setFeedback({ 
              next_task_prompt: data.current_prompt,
              next_task_prompt_translated: data.current_prompt_translated
            } as FeedbackData);
          }
        }
      }).catch(() => {
        localStorage.removeItem("ielts_exam_session_id");
        startExam();
      });
    } else {
      startExam();
    }
  }, []);

  // Handle Prep Timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPrepPhase && prepTimer > 0) {
      interval = setInterval(() => setPrepTimer((prev) => prev - 1), 1000);
    } else if (isPrepPhase && prepTimer === 0) {
      setIsPrepPhase(false);
      speak("Your preparation time is over. Please start speaking now.");
    }
    return () => clearInterval(interval);
  }, [isPrepPhase, prepTimer, speak]);

  // U5: Response Timer (counts up during recording)
  useEffect(() => {
    if (isRecording) {
      setResponseTimer(0);
      responseTimerRef.current = setInterval(() => setResponseTimer((s) => s + 1), 1000);
    } else {
      if (responseTimerRef.current) {
        clearInterval(responseTimerRef.current);
        responseTimerRef.current = null;
      }
    }
    return () => {
      if (responseTimerRef.current) clearInterval(responseTimerRef.current);
    };
  }, [isRecording]);

  // --- HANDLERS ---
  const handleStopRecording = () => {
    setErrorStatus(null);
    setStopping(true);
    stopRecording();
  };

  // Watchdog: if user pressed Stop but we never get an audioBlob, don't get stuck.
  useEffect(() => {
    if (!stopping) return;
    if (audioBlob) {
      setStopping(false);
      return;
    }

    const t = setTimeout(() => {
      setStopping(false);
      setErrorStatus("Recording didn’t finalize. Please try recording again.");
      setAudioBlob(null);
    }, 3500);
    return () => clearTimeout(t);
  }, [stopping, audioBlob, setAudioBlob]);

  const handleGetHint = async () => {
    if (!sessionId) return;
    try {
      const data = await ApiClient.getHint(sessionId);
      setHintData(data);
      setShowHint(true);
    } catch (e) { 
      console.error(e); 
      setErrorStatus("Failed to fetch hint. Please try again shortly.");
    }
  };

  const startExam = async () => {
    if (startingRef.current) return;
    startingRef.current = true;
    try {
      const session = await ApiClient.startExam(process.env.NEXT_PUBLIC_DEFAULT_USER_ID || "default_user", "FULL_MOCK");
      localStorage.setItem("ielts_exam_session_id", session.id);
      setExamPart("PART_1");
      const initialPrompt = session.current_prompt || "Welcome. Let's begin with Part 1. Can you tell me about your hometown?";
      setFeedback({ next_task_prompt: initialPrompt });
      if (session.checkpoint_words && session.checkpoint_words.length > 0) {
        const words: string[] = session.checkpoint_words;
        const tr: string[] = session.checkpoint_words_translated || [];
        const mn: string[] = session.checkpoint_words_meanings || [];
        setWordBank(words.map((w: string, i: number) => ({
          word: w,
          translation: tr[i],
          meaning: mn[i]
        })));
      } else if (session.initial_keywords && session.initial_keywords.length > 0) {
        const words: string[] = session.initial_keywords;
        const tr: string[] = session.initial_keywords_translated || [];
        const mn: string[] = session.initial_keywords_meanings || [];
        setWordBank(words.map((w: string, i: number) => ({
          word: w,
          translation: tr[i],
          meaning: mn[i]
        })));
      } else {
        setWordBank([]);
      }
      speak(initialPrompt);
    } catch (e) {
      console.error(e);
      setErrorStatus("Failed to start session. Check your connection.");
    } finally {
      startingRef.current = false;
    }
  };

  const handlePlayMirror = () => {
    if (!feedback?.user_audio_url) return;
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
    const audioUrl = `${apiBase.replace("/api", "")}${feedback.user_audio_url}`;
    
    if (audioMirrorRef.current) {
      audioMirrorRef.current.pause();
    }
    const audio = new Audio(audioUrl);
    audioMirrorRef.current = audio;
    setIsPlayingMirror(true);
    audio.play();
    audio.onended = () => setIsPlayingMirror(false);
    audio.onerror = () => setIsPlayingMirror(false);
  };

  const handleSpeakIdeal = () => {
    if (feedback?.ideal_response) {
      speak(feedback.ideal_response);
    }
  };

  const handleRetake = () => {
    setIsRetaking(true);
    setIsReviewing(false);
  };

  const handleContinue = () => {
    setIsReviewing(false);
    setIsRetaking(false);
    setPrepNotes("");
    
    const isTransitioningToPart2 = examPart === "PART_2" && localStorage.getItem("pending_part2_prep") === "true";
    
    if (isTransitioningToPart2) {
      localStorage.removeItem("pending_part2_prep");
      setIsPrepPhase(true);
      setPrepTimer(60);
      setFeedback((prev) => ({
        ...(prev || {}),
        next_task_prompt: pendingNextPrompt || prev?.next_task_prompt,
        next_task_prompt_translated: prev?.next_task_prompt_translated,
      } as FeedbackData));
      speak("You now have one minute to prepare your talk. You can make some notes if you wish. I'll tell you when to start.");
    } else if (pendingNextPrompt) {
      setFeedback((prev) => ({
        ...(prev || {}),
        next_task_prompt: pendingNextPrompt,
        next_task_prompt_translated: prev?.next_task_prompt_translated,
      } as FeedbackData));
      speak(pendingNextPrompt);
      setPendingNextPrompt(null);
    }
  };

  // --- SUBMISSION EFFECT ---
  useEffect(() => {
    if (audioBlob && sessionId && !processingRef.current && processedBlobRef.current !== audioBlob) {
      const submit = async () => {
        processedBlobRef.current = audioBlob;
        processingRef.current = true;
        setProcessing(true);
        setErrorStatus(null);
        try {
          if (audioBlob.size < 1500) {
            throw new Error("Audio too short or empty. Please record for at least 2-3 seconds and try again.");
          }

          const data = await ApiClient.submitExamAudio(sessionId, audioBlob, isRetaking);
          setFeedback(data);
          setIsRetaking(false);

          // Prefer checkpoint words if provided
          if (data.checkpoint_words && data.checkpoint_words.length > 0) {
            const words = data.checkpoint_words;
            const tr = data.checkpoint_words_translated || [];
            const mn = data.checkpoint_words_meanings || [];
            setWordBank(words.map((w, i) => ({ word: w, translation: tr[i], meaning: mn[i] })));
          } else if (data.realtime_word_bank && data.realtime_word_bank.length > 0) {
            const paired = data.realtime_word_bank.map((word, i) => ({
              word,
              translation: data.realtime_word_bank_translated?.[i]
            }));
            setWordBank(paired);
          } else if (data.target_keywords && data.target_keywords.length > 0) {
            setWordBank(data.target_keywords.map(w => ({ word: w })));
          }

          const session = await ApiClient.getExamStatus(sessionId);
          
          if (session.status === "COMPLETED") {
            setExamPart("FINISHED");
            localStorage.removeItem("ielts_exam_session_id");
            router.push(`/exam/result/${sessionId}`);
          } else {
            const prevPart = examPart;
            const nextPart = session.current_part as "PART_1" | "PART_2" | "PART_3";
            setExamPart(nextPart);

            setIsReviewing(true);
            setPendingNextPrompt(data.next_task_prompt || null);

            if (nextPart === "PART_2" && prevPart !== "PART_2") {
              localStorage.setItem("pending_part2_prep", "true");
            }
          }
        } catch (e: any) {
          console.error(e);
          setErrorStatus(e.message || "Failed to submit response. Please try again.");
        } finally {
          setProcessing(false);
          setStopping(false);
          processingRef.current = false;
          setAudioBlob(null);
        }
      };
      submit();
    }
  }, [audioBlob, sessionId, speak, setAudioBlob, router, examPart, isRetaking]);

  // --- INTRO SCREEN ---
  if (examPart === "INTRO") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 animate-in fade-in zoom-in duration-500">
        <div className="w-24 h-24 bg-red-600 rounded-3xl flex items-center justify-center rotate-3 shadow-2xl">
          <Mic2 size={48} className="text-white" />
        </div>
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-black tracking-tight text-white uppercase">Ready for Pressure?</h1>
          <p className="text-zinc-500 max-w-md mx-auto">
            This 15-minute mock exam simulates real IELTS conditions with adaptive AI stress levels.
          </p>
        </div>
        <button
          onClick={startExam}
          className="px-8 py-4 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold flex items-center gap-2 group transition-all"
        >
          Begin Simulation <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    );
  }

  // --- MAIN EXAM UI ---
  return (
    <div className="max-w-4xl mx-auto space-y-8 py-8">
      {/* Status Bar */}
      <div className="flex justify-between items-center bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl">
        <div className="flex gap-4">
          <PartIndicator active={examPart === "PART_1"} label="Part 1" />
          <PartIndicator active={examPart === "PART_2"} label="Part 2" />
          <PartIndicator active={examPart === "PART_3"} label="Part 3" />
        </div>
        <div className="flex items-center gap-2">
          {errorStatus && (
            <div className="flex items-center gap-2 text-red-500 text-xs font-bold uppercase animate-pulse">
              <AlertCircle size={14} /> {errorStatus}
            </div>
          )}
          <button onClick={handleGetHint} className="text-xs font-bold uppercase tracking-widest text-zinc-500 hover:text-white transition-colors">
            Stuck? Get Help
          </button>
          <div className="w-px h-4 bg-zinc-800 mx-2"/>
          <button onClick={() => router.push('/exam/history')} className="text-xs font-bold uppercase tracking-widest text-zinc-500 hover:text-white transition-colors">
            History
          </button>
        </div>
      </div>

      {/* ========== REVIEW MODE ========== */}
      {isReviewing && feedback && (
        <div className="bg-[#12121a] border border-zinc-800 p-8 rounded-[40px] shadow-2xl space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-500">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-black text-white uppercase tracking-tighter">Turn Evaluation</h2>
            <div className="px-3 py-1 bg-red-600/20 text-red-500 rounded-full text-[10px] font-bold uppercase tracking-widest">
              Review Required
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-zinc-500 uppercase flex items-center gap-2">
                <Mic2 size={14}/> Your Response
              </p>
              {feedback.user_audio_url && (
                <button 
                  onClick={handlePlayMirror}
                  disabled={isPlayingMirror}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all ${
                    isPlayingMirror 
                    ? "bg-blue-600/20 text-blue-400 animate-pulse" 
                    : "bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700"
                  }`}
                >
                  <Play size={12}/> {isPlayingMirror ? "Playing..." : "Hear Yourself"}
                </button>
              )}
            </div>
            <div className="p-5 bg-zinc-900/50 border border-zinc-800 rounded-2xl text-sm leading-relaxed">
              {feedback.user_transcript ? (
                <>
                  <HighlightedTranscript 
                    text={feedback.user_transcript} 
                    keywordsHit={feedback.keywords_hit} 
                  />
                  {feedback.user_transcript_translated && (
                    <p className="mt-2 text-xs text-zinc-500 italic">
                      {feedback.user_transcript_translated}
                    </p>
                  )}
                </>
              ) : (
                <span className="text-zinc-500 italic">Transcript not available</span>
              )}
            </div>
            <div className="flex items-center gap-6 text-[10px] font-bold uppercase tracking-widest">
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded bg-yellow-900/40 border border-yellow-700/30"/>
                <span className="text-yellow-500">Band 8+ Word</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded bg-green-900/40 border border-green-700/30"/>
                <span className="text-green-500">Keyword Hit</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded bg-zinc-800 border border-zinc-700"/>
                <span className="text-zinc-500">Basic</span>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-red-500 uppercase flex items-center gap-2">
                <Wand2 size={14}/> AI Enhanced (Band 8.5)
              </p>
              <button 
                onClick={handleSpeakIdeal}
                disabled={isSpeaking}
                className="flex items-center gap-2 px-3 py-1.5 bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all disabled:opacity-50"
              >
                <Volume2 size={12}/> Listen
              </button>
            </div>
            <div className="space-y-4">
              {/* U1: SmartDiff — Visual diff of user response vs ideal */}
              {feedback.user_transcript && feedback.ideal_response ? (
                <SmartDiff 
                  original={feedback.user_transcript} 
                  improved={feedback.ideal_response} 
                />
              ) : (
                <div className="bg-zinc-800/50 p-4 rounded-lg text-zinc-300 border border-zinc-700/50">
                  {feedback.ideal_response || "Analysis in progress..."}
                </div>
              )}
              {feedback.ideal_response_translated && (
                <div className="text-sm text-zinc-500 italic px-4">
                  {feedback.ideal_response_translated}
                </div>
              )}
            </div>
          </div>

          <div className="border-t border-zinc-800 pt-6 space-y-4">
            <p className="text-xs font-bold text-zinc-500 uppercase">Grammar & Vocabulary Corrections</p>
            <div className="prose prose-invert max-w-none text-zinc-300">
              <ReactMarkdown>{feedback.feedback_markdown || "No specific corrections needed for this turn."}</ReactMarkdown>
              {feedback.feedback_translated && (
                <div className="mt-4 pt-4 border-t border-zinc-800 text-sm text-zinc-500 italic">
                    {feedback.feedback_translated}
                </div>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
            <button 
              onClick={handleRetake}
              className="py-4 bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-600/30 rounded-2xl font-black uppercase tracking-widest flex flex-col items-center justify-center gap-2 transition-all active:scale-95"
            >
              <div className="flex items-center gap-2">
                <RotateCcw size={18}/> Say It Better
              </div>
              {feedback.correction_drill && (
                <span className="text-[10px] text-amber-500/70 font-medium normal-case tracking-normal max-w-xs text-center">
                  Focus: &quot;{feedback.correction_drill.slice(0, 60)}{feedback.correction_drill.length > 60 ? '...' : ''}&quot;
                </span>
              )}
            </button>
            <button 
              onClick={handleContinue}
              className="py-4 bg-white text-zinc-950 rounded-2xl font-black uppercase tracking-widest flex items-center justify-center gap-3 hover:bg-zinc-200 transition-all active:scale-95"
            >
              Got It, Next Question <CheckCircle2 size={18}/>
            </button>
          </div>
        </div>
      )}

      {/* ========== EXAMINER MODE ========== */}
      {!isReviewing && (
        <>
          <div className="bg-[#12121a] border border-zinc-800/50 p-10 rounded-[40px] shadow-2xl relative overflow-visible group">
            <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
              <Wand2 size={120} />
            </div>
            <div className="space-y-6 relative z-10">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest transition-colors ${
                    (feedback?.stress_level ?? 0.5) > 0.6 
                    ? "bg-green-600/20 text-green-500 border border-green-500/30" 
                    : (feedback?.stress_level ?? 0.5) < 0.4
                    ? "bg-red-600/20 text-red-500 border border-red-500/30"
                    : "bg-zinc-800 text-zinc-400"
                  }`}>
                    {(feedback?.stress_level ?? 0.5) > 0.6 ? "Supportive Mentor" : (feedback?.stress_level ?? 0.5) < 0.4 ? "Strict Challenger" : "Standard Examiner"}
                  </span>
                  <div className="flex gap-1">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className={`w-1 h-1 rounded-full ${
                        (feedback?.stress_level || 0) * 3 >= i ? "bg-red-500" : "bg-zinc-800"
                      }`} />
                    ))}
                  </div>
                </div>
                {isPrepPhase && (
                  <div className="flex items-center gap-2 text-amber-500 font-bold font-mono bg-amber-500/10 px-3 py-1 rounded-lg border border-amber-500/20">
                    <Timer size={16} className="animate-pulse" /> 00:{prepTimer.toString().padStart(2, '0')}
                  </div>
                )}
              </div>
              <div className="text-2xl font-medium text-zinc-100 leading-relaxed min-h-[80px]">
                {isPrepPhase
                  ? "Please look at the task card below. You have 1 minute to prepare."
                  : (feedback?.next_task_prompt || "Please describe the room you are in right now.").split('\n\nYou should say:')[0]}
              </div>

              {isPrepPhase && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-6 bg-zinc-950 border border-zinc-800 rounded-3xl animate-in zoom-in duration-300 shadow-xl overflow-hidden relative">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-red-600/5 -rotate-12 translate-x-8 -translate-y-8 rounded-full blur-2xl"/>
                    <p className="text-[10px] text-zinc-500 font-black uppercase tracking-[0.2em] mb-4 border-b border-zinc-900 pb-2">Candidate Task Card</p>
                    <div className="space-y-4">
                      <p className="text-xl text-white font-bold tracking-tight">
                        {feedback?.next_task_prompt?.split('\n\nYou should say:')[0]}
                      </p>
                      {feedback?.next_task_prompt?.includes('You should say:') && (
                        <div className="pt-2">
                          <p className="text-[10px] text-zinc-600 font-bold uppercase mb-3">You should say:</p>
                          <ul className="space-y-2">
                            {feedback.next_task_prompt.split('\nYou should say:\n')[1]?.split('\n').map((bullet, i) => (
                              <li key={i} className="flex items-start gap-3 group">
                                <span className="w-1.5 h-1.5 rounded-full bg-red-500/40 mt-1.5 group-hover:bg-red-500 transition-colors"/>
                                <span className="text-sm text-zinc-400 group-hover:text-zinc-200 transition-colors">{bullet.replace('- ', '')}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="p-4 bg-zinc-900 border border-amber-900/30 rounded-2xl animate-in zoom-in duration-500">
                    <p className="text-sm text-amber-500 font-bold uppercase tracking-widest mb-2 flex items-center gap-2">
                      <Pencil size={14}/> Your Notes
                    </p>
                    <textarea
                      value={prepNotes}
                      onChange={(e) => setPrepNotes(e.target.value)}
                      placeholder="Jot down key points, vocabulary, ideas..."
                      className="w-full h-24 bg-transparent text-zinc-300 text-sm resize-none outline-none placeholder:text-zinc-600"
                    />
                  </div>
                </div>
              )}

              {isSpeaking && (
                <div className="flex gap-1 items-end h-4">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="w-1 bg-red-500 animate-bounce"
                      style={{ animationDelay: `${i * 0.1}s`, height: `${Math.random() * 100}%` }}
                    />
                  ))}
                </div>
              )}

              {/* U6: Show correction drill when retaking */}
              {isRetaking && feedback?.correction_drill && !isRecording && (
                <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-2xl animate-in fade-in slide-in-from-top-4 duration-500">
                  <div className="flex items-center gap-2 mb-2">
                    <Wand2 size={14} className="text-amber-500" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-amber-500">Focus On This</span>
                  </div>
                  <p className="text-sm text-zinc-300 italic font-medium leading-relaxed">
                    &quot;{feedback.correction_drill}&quot;
                  </p>
                  {feedback.reasoning && (
                    <p className="mt-2 text-[9px] text-amber-500/70 font-bold uppercase">
                      💡 {feedback.reasoning}
                    </p>
                  )}
                </div>
              )}

              {/* U5: Response timer during recording */}
              {isRecording && (
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-zinc-400 font-mono text-sm">
                    <Timer size={14} className={responseTimer > 45 ? "text-amber-500 animate-pulse" : "text-zinc-500"} />
                    <span className={responseTimer > 45 ? "text-amber-500" : ""}>
                      {Math.floor(responseTimer / 60)}:{(responseTimer % 60).toString().padStart(2, '0')}
                    </span>
                  </div>
                  {examPart === "PART_1" && responseTimer > 45 && (
                    <span className="text-[10px] text-amber-500 font-bold uppercase animate-pulse">
                      Wrap up your answer
                    </span>
                  )}
                  {examPart === "PART_3" && responseTimer > 60 && (
                    <span className="text-[10px] text-amber-500 font-bold uppercase animate-pulse">
                      Consider concluding
                    </span>
                  )}
                </div>
              )}
            </div>

            {showHint && hintData && (
              <HintCard hint={hintData} onClose={() => setShowHint(false)} />
            )}
          </div>

          {!isPrepPhase && wordBank.length > 0 && (
            <div className="bg-zinc-900/40 border border-zinc-800 p-6 rounded-3xl animate-in fade-in slide-in-from-top-4 duration-700">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb size={16} className="text-yellow-500" />
                <span className="text-xs font-black uppercase tracking-widest text-zinc-500">Checkpoint Words (Required)</span>
              </div>
              <div className="flex flex-wrap gap-3">
                {wordBank.map((item, idx) => (
                  <div
                    key={idx}
                    className={`px-4 py-2 border rounded-xl transition-all hover:scale-105 cursor-default group flex flex-col items-center ${
                      (feedback?.checkpoint_words_hit || feedback?.keywords_hit || []).some(
                        (u) => u.toLowerCase() === item.word.toLowerCase(),
                      )
                        ? "bg-emerald-900/30 border-emerald-700/60"
                        : "bg-zinc-800 hover:bg-zinc-700 border-zinc-700"
                    }`}
                  >
                    <span className="text-sm font-bold text-zinc-300 group-hover:text-white uppercase tracking-tight">{item.word}</span>
                    {item.translation && (
                      <span className="text-[10px] text-zinc-500 font-medium italic border-t border-zinc-700/50 mt-1 pt-1 w-full text-center">
                        {item.translation}
                      </span>
                    )}
                    {item.meaning && (
                      <span className="text-[10px] text-zinc-500 font-medium mt-1 w-full text-center">
                        {item.meaning}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="max-w-md mx-auto w-full">
            <AudioWaveform isRecording={isRecording} audioStream={stream} />
          </div>

          <div className="flex flex-col items-center gap-6">
            {isPrepPhase ? (
              <div className="flex flex-col items-center gap-4">
                <div className="w-24 h-24 bg-zinc-800 rounded-full flex items-center justify-center opacity-50">
                  <Timer size={48} className="text-zinc-500" />
                </div>
                <p className="text-amber-500 font-bold uppercase tracking-widest text-sm animate-pulse">Preparation in Progress</p>
              </div>
            ) : !isRecording ? (
              <button
                disabled={isSpeaking || processing}
                onClick={startRecording}
                className="group relative w-24 h-24 bg-red-600 disabled:bg-zinc-800 rounded-full flex items-center justify-center transition-all hover:scale-105 active:scale-95 shadow-[0_0_30px_rgba(220,38,38,0.4)] disabled:shadow-none"
              >
                {!isSpeaking && !processing && (
                  <div className="absolute inset-0 rounded-full bg-red-600 animate-ping opacity-20 pointer-events-none"/>
                )}
                {processing ? (
                  <div className="w-8 h-8 border-4 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Mic2 size={32} className="text-white" />
                )}
              </button>
            ) : (
              <button
                disabled={processing || stopping}
                onClick={handleStopRecording}
                className="group w-24 h-24 bg-zinc-100 rounded-full flex items-center justify-center transition-all hover:scale-105 active:scale-95"
              >
                <Square size={32} className="text-zinc-950" />
              </button>
            )}

            <p className="text-zinc-500 text-xs font-bold uppercase tracking-widest text-center">
              {isPrepPhase
                ? "Use this time to plan your answer"
                : isRecording
                  ? "Listening... Speak clearly"
                  : stopping
                    ? "Finalizing recording..."
                  : isSpeaking
                    ? "Examiner is speaking..."
                    : isRetaking
                      ? "Now record your improved version"
                      : "Tap to respond"}
            </p>
          </div>
        </>
      )}
    </div>
  );
}

function PartIndicator({ active, label }: { active: boolean; label: string }) {
  return (
    <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all ${
      active ? "bg-red-600/10 border-red-500/50 text-red-500" : "bg-transparent border-transparent text-zinc-600"
    }`}>
      <div className={`w-1.5 h-1.5 rounded-full ${active ? "bg-red-500" : "bg-zinc-800"}`} />
      <span className="text-xs font-black uppercase tracking-widest">{label}</span>
    </div>
  );
}

function HintCard({ hint, onClose }: { hint: { vocabulary: string[]; starter: string; grammar_tip: string }; onClose: () => void }) {
  return (
    <div className="absolute inset-x-0 -bottom-4 translate-y-full bg-zinc-900 border border-zinc-800 p-6 rounded-3xl z-20 shadow-2xl animate-in slide-in-from-top-4">
      <div className="flex justify-between items-start mb-4">
        <h4 className="text-sm font-bold text-yellow-500 uppercase tracking-widest flex items-center gap-2">
          <Wand2 size={16} /> Examiner's Tip
        </h4>
        <button onClick={onClose} className="text-zinc-500 hover:text-white"><Square size={16} /></button>
      </div>
      <div className="space-y-4">
        <div>
          <p className="text-xs text-zinc-500 mb-1">Useful Vocabulary:</p>
          <div className="flex flex-wrap gap-2">
            {hint.vocabulary.map((w, i) => (
              <span key={i} className="px-2 py-1 bg-zinc-800 text-zinc-300 rounded text-sm">{w}</span>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs text-zinc-500 mb-1">Sentence Starter:</p>
          <p className="text-zinc-200 italic">"{hint.starter}"</p>
        </div>
        <div className="pt-2 border-t border-zinc-800">
          <p className="text-xs text-zinc-400">💡 {hint.grammar_tip}</p>
        </div>
      </div>
    </div>
  );
}
