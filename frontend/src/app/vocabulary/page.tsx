"use client";
import React from "react";
import { useState, useEffect } from "react";
import { 
  Search, Plus, Book, CheckCircle2, AlertCircle, 
  ChevronRight, Volume2, Trophy, LucideIcon
} from "lucide-react";
import { ApiClient } from "@/lib/api";

interface VocabularyItem {
  id: number;
  word: string;
  definition: string;
  context_sentence?: string;
  mastery_level: number;
}

export default function VocabularyPage() {
  const [vocab, setVocab] = useState<VocabularyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [, setShowAddModal] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await ApiClient.getVocabulary();
        setVocab(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filteredVocab = vocab.filter(item => 
    item.word.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8 pb-12 animate-in fade-in duration-700">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight uppercase">Vocabulary <span className="text-red-600">Lab</span></h1>
          <p className="text-zinc-500 mt-2 font-medium">Master academic keywords and improve your Lexical Resource score.</p>
        </div>
        
        <div className="flex gap-4 w-full md:w-auto">
           <div className="relative group flex-1 md:w-64">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 group-focus-within:text-red-500 transition-colors" size={18} />
              <input 
                type="text" 
                placeholder="Search words..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-12 pr-4 py-3 bg-zinc-900 border border-zinc-800 rounded-2xl text-white focus:outline-none focus:border-red-500/50 transition-all font-medium"
              />
           </div>
           <button 
             onClick={() => setShowAddModal(true)}
             className="px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold flex items-center gap-2 transition-all hover:scale-105 shadow-[0_0_20px_rgba(220,38,38,0.3)]"
           >
              <Plus size={20} /> Add Word
           </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         <StatsCard 
           icon={Book} 
           label="Total Words" 
           value={vocab.length.toString()} 
           sub="Learned so far" 
           color="text-blue-500"
         />
         <StatsCard 
           icon={Trophy} 
           label="Mastered" 
           value={vocab.filter(i => i.mastery_level >= 4).length.toString()} 
           sub="Ready for exam" 
           color="text-red-500"
         />
         <StatsCard 
           icon={CheckCircle2} 
           label="Today's Goal" 
           value="12/20" 
           sub="8 more to go" 
           color="text-emerald-500"
         />
      </div>

      {/* Main Grid */}
      {loading ? (
        <div className="flex justify-center p-20">
            <div className="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          {filteredVocab.map((item) => (
            <VocabCard key={item.id} item={item} />
          ))}
          {filteredVocab.length === 0 && (
            <div className="col-span-full py-20 bg-zinc-900/30 border border-zinc-800 border-dashed rounded-[32px] text-center">
                <AlertCircle size={48} className="text-zinc-700 mx-auto mb-4" />
                <p className="text-zinc-500 font-medium">No words found. Add your first word to start mastering!</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function VocabCard({ item }: { item: VocabularyItem }) {
  const masteryPercentage = (item.mastery_level / 5) * 100;
  
  return (
    <div className="group bg-[#12121a] border border-zinc-800 hover:border-red-500/30 p-6 rounded-[32px] transition-all duration-300 hover:shadow-[0_0_30px_rgba(220,38,38,0.1)] relative overflow-hidden">
      <div className="absolute top-0 right-0 p-4">
        <div className={`w-3 h-3 rounded-full ${item.mastery_level >= 4 ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' : 'bg-amber-500'}`} />
      </div>
      
      <div className="space-y-4">
        <div className="flex justify-between items-start">
           <h3 className="text-2xl font-black text-white group-hover:text-red-500 transition-colors uppercase">{item.word}</h3>
           <button className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-white transition-colors">
              <Volume2 size={18} />
           </button>
        </div>
        
        <p className="text-zinc-400 font-medium leading-relaxed">{item.definition}</p>
        
        {item.context_sentence && (
          <div className="p-4 bg-zinc-900/50 rounded-2xl italic text-sm text-zinc-500 border border-zinc-800/50">
            "{item.context_sentence}"
          </div>
        )}
        
        <div className="pt-4 border-t border-zinc-900">
           <div className="flex justify-between items-end mb-2">
              <span className="text-[10px] font-black uppercase tracking-widest text-zinc-600">Mastery Level</span>
              <span className="text-[10px] font-black text-white">{masteryPercentage}%</span>
           </div>
           <div className="h-2 w-full bg-zinc-900 rounded-full overflow-hidden p-[1px]">
              <div 
                className={`h-full rounded-full bg-gradient-to-r from-red-600 to-amber-500 transition-all duration-1000`} 
                style={{ width: `${masteryPercentage}%` }}
              />
           </div>
        </div>
        
        <button className="w-full py-3 mt-2 flex items-center justify-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500 hover:text-white group-hover:bg-red-600 group-hover:text-white rounded-xl transition-all">
           Review Card <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

interface StatsCardProps { icon: LucideIcon; label: string; value: string; sub: string; color: string; }
function StatsCard({ icon: Icon, label, value, sub, color }: StatsCardProps) {
    return (
        <div className="bg-[#12121a] border border-zinc-800 p-6 rounded-[32px] flex items-center gap-6">
            <div className={`p-4 rounded-2xl bg-zinc-900 ${color} border border-zinc-800`}>
                <Icon size={28} />
            </div>
            <div>
                <p className="text-zinc-500 text-xs font-bold uppercase tracking-widest">{label}</p>
                <h4 className="text-3xl font-black text-white my-1">{value}</h4>
                <p className="text-zinc-600 text-xs font-medium">{sub}</p>
            </div>
        </div>
    );
}
