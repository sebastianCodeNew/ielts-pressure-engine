"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, History as HistoryIcon, MessageSquare, Sparkles, Calendar, ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { ApiClient } from "@/lib/api";

interface HistoryItem {
  id: number;
  part: string;
  question: string;
  your_answer: string;
  improved_answer: string;
  feedback: string;
  score: number;
  date: string;
}

export default function ExamHistory() {
  const router = useRouter();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<HistoryItem | null>(null);

  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await ApiClient.getDetailedHistory();
        setHistory(data);
      } catch (err) {
        console.error("Failed to load history", err);
      } finally {
        setLoading(false);
      }
    }
    loadHistory();
  }, []);

  return (
    <div className="max-w-6xl mx-auto py-12 px-4 space-y-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.back()}
            className="p-3 bg-zinc-900 border border-zinc-800 rounded-2xl text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-3xl font-black text-white uppercase tracking-tighter flex items-center gap-3">
              <HistoryIcon className="text-red-500" /> Exam History
            </h1>
            <p className="text-zinc-500 text-sm font-medium uppercase tracking-widest">Review your past performance & improved responses</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        {/* History List */}
        <div className="lg:col-span-5 space-y-4">
          {loading ? (
             <div className="space-y-4">
                {[1,2,3].map(i => (
                  <div key={i} className="h-24 bg-zinc-900/50 rounded-3xl animate-pulse" />
                ))}
             </div>
          ) : history.length === 0 ? (
            <div className="text-center py-20 bg-zinc-900/30 border border-zinc-800 border-dashed rounded-[40px] space-y-4">
               <MessageSquare size={48} className="mx-auto text-zinc-700" />
               <p className="text-zinc-500 font-bold uppercase tracking-widest text-sm">No exam history found</p>
               <button 
                  onClick={() => router.push('/exam')}
                  className="px-6 py-2 bg-red-600 text-white rounded-full text-xs font-bold uppercase transition-transform active:scale-95"
               >
                 Take your first exam
               </button>
            </div>
          ) : (
            <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-2 custom-scrollbar">
              {history.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setSelectedItem(item)}
                  className={`w-full text-left p-6 rounded-3xl border transition-all group ${
                    selectedItem?.id === item.id 
                    ? "bg-red-600/10 border-red-500/50 shadow-lg shadow-red-500/5" 
                    : "bg-zinc-900/50 border-zinc-800 hover:border-zinc-700"
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <span className="px-2 py-1 bg-zinc-800 text-zinc-400 rounded-lg text-[10px] font-black uppercase tracking-widest group-hover:bg-zinc-700">
                      {item.part}
                    </span>
                    <div className="flex items-center gap-1 text-[10px] font-bold text-zinc-500">
                      <Calendar size={12} /> {item.date}
                    </div>
                  </div>
                  <h3 className="text-zinc-200 font-bold line-clamp-2 mb-4 group-hover:text-white transition-colors">
                    {item.question}
                  </h3>
                  <div className="flex items-center justify-between">
                     <span className="text-[10px] font-black uppercase tracking-tighter text-zinc-500 group-hover:text-zinc-400">View Detailed Analysis</span>
                     <ChevronRight size={16} className={`text-zinc-700 transition-transform ${selectedItem?.id === item.id ? "translate-x-1 text-red-500" : ""}`} />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Detail View */}
        <div className="lg:col-span-7">
          {selectedItem ? (
            <div className="bg-[#12121a] border border-zinc-800 rounded-[40px] p-10 space-y-10 animate-in fade-in slide-in-from-right-8 duration-500 sticky top-12">
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h2 className="text-2xl font-black text-white uppercase tracking-tighter">Evaluation</h2>
                    <div className="flex items-center gap-4">
                        <div className="flex flex-col items-end">
                            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Turn Score</span>
                            <span className="text-xl font-black text-red-500">Band {selectedItem.score}</span>
                        </div>
                    </div>
                  </div>
                  <p className="text-lg text-zinc-300 font-medium leading-relaxed italic border-l-4 border-red-600/30 pl-6 py-2">
                    "{selectedItem.question}"
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-8">
                  <div className="space-y-4">
                    <p className="text-xs font-bold text-zinc-500 uppercase flex items-center gap-2">
                        <MessageSquare size={14} /> Your Original Response
                    </p>
                    <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-3xl text-zinc-400 text-sm leading-relaxed">
                       {selectedItem.your_answer || "No transcript available."}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <p className="text-xs font-bold text-red-500 uppercase flex items-center gap-2">
                        <Sparkles size={14} /> AI Enhanced (Band 8.5)
                    </p>
                    <div className="p-6 bg-red-900/10 border border-red-900/20 rounded-3xl text-red-100/90 text-sm leading-relaxed font-medium">
                       {selectedItem.improved_answer || "No improved response generated."}
                    </div>
                  </div>
                </div>

                <div className="pt-8 border-t border-zinc-800 space-y-4">
                  <p className="text-xs font-bold text-zinc-500 uppercase">Examiner Analysis</p>
                  <div className="prose prose-invert prose-sm max-w-none prose-p:text-zinc-400">
                    <ReactMarkdown>{selectedItem.feedback || "No feedback recorded for this attempt."}</ReactMarkdown>
                  </div>
                </div>
            </div>
          ) : (
            <div className="h-full min-h-[500px] border border-zinc-800 border-dashed rounded-[40px] flex flex-col items-center justify-center text-center p-12 space-y-6">
                <div className="w-20 h-20 bg-zinc-900 rounded-full flex items-center justify-center">
                  <Sparkles size={32} className="text-zinc-700" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-zinc-400 uppercase tracking-tight">Select an attempt</h3>
                  <p className="text-zinc-600 text-sm max-w-xs mx-auto">Click on a past attempt to see how the AI improved your response and view granular feedback.</p>
                </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
