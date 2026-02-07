"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ApiClient } from "@/lib/api";
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer 
} from "recharts";
import { Award, ArrowLeft, RefreshCw, BarChart3, MessageSquare, Zap } from "lucide-react";
import ReactMarkdown from "react-markdown";

export default function ExamResultPage() {
  const { sessionId } = useParams();
  const router = useRouter();
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [drillLoading, setDrillLoading] = useState(false);

  useEffect(() => {
    async function fetchResult() {
      try {
        const data = await ApiClient.getExamSummary(sessionId as string);
        setResult(data);
      } catch (err) {
        console.error("Failed to fetch result:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchResult();
  }, [sessionId]);

  const handleMasteryDrill = async () => {
    if (!result?.topic_prompt) return;
    setDrillLoading(true);
    try {
      // Start a "DRILL" mode exam with the topic override
      const nextSession = await ApiClient.startExam(
        "default_user",
        "PART_3_ONLY",
        result.topic_prompt,
      );
      router.push(`/exam/ongoing/${nextSession.id}`);
    } catch (err) {
      console.error("Mastery drill failed:", err);
      setDrillLoading(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen bg-[#0d0d12]">
      <div className="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  if (!result) return (
    <div className="flex flex-col items-center justify-center min-h-screen text-white gap-4">
      <h1 className="text-2xl font-bold">Session not found</h1>
      <button onClick={() => router.push("/dashboard")} className="text-red-500 hover:underline">Return to Dashboard</button>
    </div>
  );

  const radarData = [
    { subject: 'Fluency', A: result.breakdown.fluency, B: 9, fullMark: 9 },
    { subject: 'Coherence', A: result.breakdown.coherence, B: 9, fullMark: 9 },
    { subject: 'Lexical', A: result.breakdown.lexical_resource, B: 9, fullMark: 9 },
    { subject: 'Grammar', A: result.breakdown.grammatical_range, B: 9, fullMark: 9 },
    { subject: 'Pronunciation', A: result.breakdown.pronunciation, B: 9, fullMark: 9 },
  ];

  return (
    <div className="min-h-screen bg-[#0d0d12] text-zinc-100 p-8 pt-12">
      <div className="max-w-5xl mx-auto space-y-12">
        
        {/* Navigation */}
        <button 
          onClick={() => router.push("/dashboard")}
          className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors"
        >
          <ArrowLeft size={18} /> Back to Dashboard
        </button>

        {/* Hero Section */}
        <div className="flex flex-col md:flex-row items-center gap-12 bg-zinc-900/50 border border-zinc-800 p-10 rounded-3xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-600/10 rounded-full blur-[100px] -mr-32 -mt-32" />
          
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="w-32 h-32 rounded-full bg-red-600 flex items-center justify-center text-5xl font-black shadow-[0_0_50px_rgba(220,38,38,0.4)]">
              {result.overall_score.toFixed(1)}
            </div>
            <div className="space-y-1">
              <h1 className="text-2xl font-bold">Overall Band Score</h1>
              <p className="text-zinc-500 font-medium">Completed on {new Date().toLocaleDateString()}</p>
            </div>
          </div>

          <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-6 w-full">
             <ScoreBadge label="Fluency" score={result.breakdown.fluency} />
             <ScoreBadge label="Coherence" score={result.breakdown.coherence} />
             <ScoreBadge label="Lexical" score={result.breakdown.lexical_resource} />
             <ScoreBadge label="Grammar" score={result.breakdown.grammatical_range} />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
          
          {/* Chart Section */}
          <div className="bg-zinc-900/30 border border-zinc-800 p-8 rounded-3xl h-[400px]">
            <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
              <BarChart3 size={20} className="text-red-500" /> Skill Analysis
            </h3>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid stroke="#27272a" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                <Radar
                   name="Target 9.0"
                   dataKey="B"
                   stroke="#27272a"
                   fill="#27272a"
                   fillOpacity={0.1}
                />
                <Radar
                   name="You"
                   dataKey="A"
                   stroke="#ef4444"
                   fill="#ef4444"
                   fillOpacity={0.5}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Feedback section */}
          <div className="bg-zinc-900/30 border border-zinc-800 p-8 rounded-3xl space-y-6">
            <h3 className="text-lg font-bold flex items-center gap-2">
              <MessageSquare size={20} className="text-blue-500" /> AI Examiner's Review
            </h3>
            <div className="prose prose-invert prose-sm max-w-none text-zinc-400 leading-relaxed">
              <ReactMarkdown>{result.feedback || "Your performance showed good grammatical range, though some hesitation in Part 3 affected the fluency score. Focus on using more complex discourse markers to bridge ideas."}</ReactMarkdown>
            </div>
            
            <div className="pt-6 border-t border-zinc-800 flex gap-4">
              <button 
                onClick={() => router.push("/exam")}
                className="flex-1 py-4 bg-zinc-800 hover:bg-zinc-700 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all"
              >
                <RefreshCw size={18} /> Retry Exam
              </button>
              <button 
                disabled={drillLoading}
                onClick={handleMasteryDrill}
                className="flex-1 py-4 bg-red-600 hover:bg-red-500 rounded-2xl font-bold transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {drillLoading ? (
                   <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <Zap size={18} fill="currentColor" />
                )}
                Topic Mastery Drill
              </button>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}

function ScoreBadge({ label, score }: { label: string, score: number }) {
  return (
    <div className="p-4 bg-zinc-800/40 rounded-2xl border border-zinc-800">
      <p className="text-[10px] uppercase font-black text-zinc-500 tracking-widest mb-1">{label}</p>
      <p className="text-xl font-bold text-zinc-100">{score.toFixed(1)}</p>
    </div>
  );
}
