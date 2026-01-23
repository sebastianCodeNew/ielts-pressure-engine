"use client";
import { Trophy, Star, Zap, Target, Flame, Book } from "lucide-react";
import { LucideIcon } from "lucide-react";

interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  unlocked: boolean;
  progress?: number;
}

export default function AchievementsList() {
  const achievements: Achievement[] = [
    { id: "1", name: "First Steps", description: "Complete your first part 1 practice.", icon: Target, unlocked: true },
    { id: "2", name: "Grammar Master", description: "Score 8.0+ in Grammar in a full mock.", icon: Zap, unlocked: false, progress: 65 },
    { id: "3", name: "Fluent Speaker", description: "Maintain 150+ WPM for 5 minutes.", icon: Flame, unlocked: true },
    { id: "4", name: "Vocabulary King", description: "Master 50 words in the Vocab Lab.", icon: Book, unlocked: false, progress: 40 },
    { id: "5", name: "Pressure Proof", description: "Complete a full exam with high stress.", icon: Trophy, unlocked: false },
  ];

  return (
    <div className="bg-[#12121a] border border-zinc-800 p-8 rounded-[40px] shadow-2xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-black text-white uppercase tracking-tight">Hall of <span className="text-red-600">Fame</span></h2>
          <p className="text-zinc-500 text-sm font-medium">Your milestones and achievements.</p>
        </div>
        <div className="p-3 bg-red-600/10 rounded-2xl border border-red-500/20">
           <Trophy className="text-red-500" size={24} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-4">
        {achievements.map((ach) => (
          <div 
            key={ach.id} 
            className={`p-5 rounded-[24px] border transition-all ${
              ach.unlocked 
                ? "bg-zinc-900 border-zinc-800" 
                : "bg-zinc-900/30 border-zinc-900 opacity-60 grayscale"
            }`}
          >
            <div className="flex items-start gap-4">
               <div className={`p-3 rounded-xl ${ach.unlocked ? 'bg-red-600/10 text-red-500' : 'bg-zinc-800 text-zinc-600'}`}>
                  <ach.icon size={20} />
               </div>
               <div className="flex-1">
                  <h4 className="font-bold text-white text-sm">{ach.name}</h4>
                  <p className="text-xs text-zinc-500 mt-1">{ach.description}</p>
                  
                  {!ach.unlocked && ach.progress !== undefined && (
                    <div className="mt-3">
                       <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden">
                          <div className="h-full bg-red-600" style={{ width: `${ach.progress}%` }} />
                       </div>
                    </div>
                  )}
               </div>
               {ach.unlocked && <Star size={16} className="text-amber-500 fill-amber-500" />}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
