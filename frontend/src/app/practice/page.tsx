"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ApiClient } from "@/lib/api";
import { 
  Library, Search, Play, Star, ChevronRight, Lock 
} from "lucide-react";

export default function TopicBankPage() {
  const router = useRouter();
  const [topics, setTopics] = useState<any[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadTopics() {
      try {
        const data = await ApiClient.getTopics();
        setTopics(data);
      } catch (err) {
        console.error("Failed to load topics:", err);
      } finally {
        setLoading(false);
      }
    }
    loadTopics();
  }, []);

  const filteredTopics = topics.filter(t => filter === "ALL" || t.part === filter);

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen bg-[#0d0d12]">
      <div className="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0d0d12] text-zinc-100 p-8 pt-12">
      <div className="max-w-6xl mx-auto space-y-10">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-1">
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Library className="text-red-600" /> Topic Bank
            </h1>
            <p className="text-zinc-500">Master every section with targeted IELTS practice drills.</p>
          </div>
          
          <div className="flex bg-zinc-900 border border-zinc-800 p-1 rounded-xl">
             <FilterBtn active={filter === "ALL"} onClick={() => setFilter("ALL")} label="All" />
             <FilterBtn active={filter === "PART_1"} onClick={() => setFilter("PART_1")} label="Part 1" />
             <FilterBtn active={filter === "PART_2"} onClick={() => setFilter("PART_2")} label="Part 2" />
             <FilterBtn active={filter === "PART_3"} onClick={() => setFilter("PART_3")} label="Part 3" />
          </div>
        </div>

        {/* Search & Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
           <div className="md:col-span-2 relative">
             <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600" size={18} />
             <input 
               type="text" 
               placeholder="Search for topics like 'Environment' or 'Technology'..." 
               className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 pl-12 pr-4 focus:outline-none focus:border-red-600 transition-colors"
             />
           </div>
           <div className="bg-gradient-to-br from-red-600/20 to-transparent border border-red-600/20 p-4 rounded-2xl flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase font-black text-red-500 tracking-widest">Your Mastery</p>
                <p className="text-2xl font-bold">12 / 84</p>
              </div>
              <div className="w-12 h-12 rounded-full border-2 border-red-500/30 flex items-center justify-center text-red-500 font-bold">
                 14%
              </div>
           </div>
        </div>

        {/* Topics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
           {filteredTopics.map((topic, i) => (
             <TopicCard 
               key={i} 
               topic={topic} 
               onClick={() => router.push(`/exam?topic=${topic.id}`)}
             />
           ))}
           
           {/* Coming Soon placeholders */}
           {[1,2,3].map(i => (
             <div key={i} className="group p-6 bg-zinc-900/40 border border-zinc-800/50 rounded-2xl flex flex-col justify-between opacity-50 grayscale">
                <div className="space-y-4">
                  <div className="flex justify-between items-start">
                    <span className="w-10 h-10 rounded-xl bg-zinc-800 flex items-center justify-center">
                      <Lock size={18} className="text-zinc-600" />
                    </span>
                  </div>
                  <div className="space-y-2">
                    <h3 className="font-bold text-zinc-500">Premium Topic {i}</h3>
                    <div className="h-4 w-3/4 bg-zinc-800 rounded animate-pulse" />
                  </div>
                </div>
             </div>
           ))}
        </div>

      </div>
    </div>
  );
}

function FilterBtn({ active, onClick, label }: any) {
  return (
    <button 
      onClick={onClick}
      className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
        active 
          ? "bg-red-600 text-white shadow-lg" 
          : "text-zinc-500 hover:text-white"
      }`}
    >
      {label}
    </button>
  );
}

function TopicCard({ topic, onClick }: any) {
  return (
    <div className="group p-6 bg-zinc-900/50 border border-zinc-800 rounded-2xl hover:border-zinc-500/50 transition-all hover:scale-[1.02] cursor-pointer flex flex-col justify-between h-full shadow-lg">
      <div className="space-y-4">
        <div className="flex justify-between items-start">
          <div className="flex gap-2">
            <span className={`px-2 py-0.5 rounded-md text-[9px] font-black uppercase tracking-widest border ${
              topic.level === 'Easy' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' :
              topic.level === 'Medium' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20' :
              'bg-red-500/10 text-red-500 border-red-500/20'
            }`}>
              {topic.level}
            </span>
            <span className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded-md text-[9px] font-black uppercase tracking-widest text-zinc-400">
              {topic.part.replace("_", " ")}
            </span>
          </div>
          <div className="flex gap-0.5">
            {[1,2,3].map(i => (
              <Star key={i} size={8} className={i <= (topic.level === 'Easy' ? 1 : topic.level === 'Medium' ? 2 : 3) ? "text-yellow-500 fill-yellow-500" : "text-zinc-700"} />
            ))}
          </div>
        </div>
        
        <div className="space-y-2">
          <h3 className="text-lg font-bold text-zinc-100 group-hover:text-red-500 transition-colors uppercase tracking-tight">{topic.name}</h3>
          <p className="text-xs text-zinc-500 leading-relaxed line-clamp-2">{topic.desc}</p>
        </div>
      </div>

      <div className="mt-8 flex items-center justify-between pt-6 border-t border-zinc-800/50">
        <div className="flex items-center gap-1.5 text-[10px] font-bold text-zinc-600 uppercase">
           <Play size={12} fill="currentColor" /> Practice now
        </div>
        <ChevronRight size={16} className="text-zinc-700 group-hover:text-white transition-all transform group-hover:translate-x-1" />
      </div>
    </div>
  );
}
