"use client";
import React from "react";
import { useState, useEffect } from "react";
import { 
  TrendingUp, Award, BookOpen, Clock, ChevronRight, 
  Sparkles, Calendar, CheckCircle2, ArrowRight, Zap, LucideIcon
} from "lucide-react";
import { 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, AreaChart, Area
} from "recharts";
import { ApiClient } from "@/lib/api";
import AchievementsList from "@/components/Achievements";

interface ScoreData { name: string; score: number; }
interface SkillData { subject: string; A: number; fullMark: number; }
interface StatsData { average_score: number; total_exams: number; recent_scores: ScoreData[]; skill_breakdown: SkillData[]; }
interface RecentExam { date: string; topic: string; duration: string; score: number; status: string; }
interface StudyPlanItem { day: string; focus: string; tasks: string[]; }
interface StudyPlan { plan: StudyPlanItem[]; }

export default function Dashboard() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [history, setHistory] = useState<RecentExam[]>([]);
  const [studyPlan, setStudyPlan] = useState<StudyPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingPlan, setGeneratingPlan] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, historyData] = await Promise.all([
          ApiClient.getStats(),
          ApiClient.getHistory()
        ]);
        setStats(statsData);
        setHistory(historyData);
      } catch (err) {
        console.error("Dashboard error:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleGeneratePlan = async () => {
    setGeneratingPlan(true);
    try {
        const data = await ApiClient.getStudyPlan();
        setStudyPlan(data);
    } catch (e) {
        console.error(e);
    } finally {
        setGeneratingPlan(false);
    }
  };

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="space-y-10 pb-12 animate-in fade-in duration-1000">
      
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tighter uppercase">Elite <span className="text-red-600">Dashboard</span></h1>
          <p className="text-zinc-500 mt-2 font-medium">Targeting <span className="text-white font-bold">Band 8.5</span> • 12 days until exam</p>
        </div>
        <div className="flex gap-4 w-full md:w-auto">
           <button 
             onClick={handleGeneratePlan}
             className="flex-1 md:flex-none px-6 py-4 bg-zinc-900 border border-zinc-800 hover:border-red-600/50 rounded-2xl text-sm font-bold transition-all flex items-center justify-center gap-2 group"
           >
              {generatingPlan ? <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" /> : <Sparkles size={18} className="text-red-500 group-hover:rotate-12 transition-transform" />}
              AI Study Plan
           </button>
           <button className="flex-1 md:flex-none px-8 py-4 bg-red-600 hover:bg-red-500 text-white rounded-2xl text-sm font-black uppercase tracking-widest transition-all hover:scale-105 shadow-[0_0_30px_rgba(220,38,38,0.3)]">
              Start Exam
           </button>
        </div>
      </div>

      {/* Hero Study Plan Section (Conditional) */}
      {studyPlan && (
        <div className="bg-gradient-to-br from-red-600 to-amber-600 p-[1px] rounded-[40px] animate-in slide-in-from-top duration-700">
            <div className="bg-[#0d0d12] rounded-[39px] p-8 md:p-12 overflow-hidden relative">
                <div className="absolute -right-20 -top-20 opacity-10 rotate-12">
                    <Calendar size={400} />
                </div>
                <div className="relative z-10 flex flex-col lg:flex-row gap-12">
                    <div className="flex-1 space-y-6">
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-red-600/10 border border-red-500/20 text-red-500 rounded-full text-[10px] font-black uppercase tracking-widest">
                            Personalized Path
                        </div>
                        <h2 className="text-3xl font-black text-white uppercase leading-none">Your 7-Day <span className="text-red-600">Blueprint</span></h2>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                            {studyPlan.plan.slice(0, 4).map((day, i) => (
                                <div key={i} className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-3xl group hover:border-red-500/30 transition-all cursor-pointer">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-[10px] font-black text-red-500 uppercase">{day.day}</span>
                                        <div className="w-4 h-4 rounded-full border border-zinc-700" />
                                    </div>
                                    <p className="font-bold text-white text-sm">{day.focus}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="lg:w-80 bg-zinc-900/50 border border-zinc-800 p-8 rounded-[32px] flex flex-col justify-center items-center text-center space-y-4">
                        <div className="w-16 h-16 bg-red-600 rounded-2xl flex items-center justify-center rotate-6 shadow-2xl">
                            <BookOpen size={32} className="text-white" />
                        </div>
                        <h4 className="text-xl font-bold text-white uppercase">Today's Focus</h4>
                        <p className="text-zinc-500 text-sm">{studyPlan.plan[0].tasks[0]}</p>
                        <button className="w-full py-4 bg-white text-black rounded-xl font-black text-xs uppercase tracking-widest hover:bg-zinc-200 transition-all">Continue Mission</button>
                    </div>
                </div>
            </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        
        {/* Main Progression Area */}
        <div className="lg:col-span-3 space-y-8">
            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                <StatBox icon={TrendingUp} label="Band Score" value={stats?.average_score?.toFixed(1) || "0.0"} trend="+0.5" color="text-red-500" />
                <StatBox icon={Award} label="Mocks Done" value={stats?.total_exams || "0"} trend="+2" color="text-amber-500" />
                <StatBox icon={BookOpen} label="Vocab Gems" value="482" trend="+15" color="text-emerald-500" />
            </div>

            {/* Performance Visualizers */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                <ChartCard title="Progression">
                    <ResponsiveContainer width="100%" height={250}>
                        <AreaChart data={stats?.recent_scores || []}>
                            <defs>
                                <linearGradient id="progGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                            <XAxis dataKey="name" stroke="#52525b" hide />
                            <YAxis stroke="#52525b" fontSize={10} domain={[0, 9]} hide />
                            <Tooltip contentStyle={{ backgroundColor: '#18181b', border: 'none', borderRadius: '12px' }} />
                            <Area type="monotone" dataKey="score" stroke="#ef4444" strokeWidth={3} fill="url(#progGradient)" />
                        </AreaChart>
                    </ResponsiveContainer>
                </ChartCard>

                <ChartCard title="Skill DNA">
                    <ResponsiveContainer width="100%" height={250}>
                        <RadarChart data={stats?.skill_breakdown || []}>
                            <PolarGrid stroke="#27272a" />
                            <PolarAngleAxis dataKey="subject" tick={{ fill: '#a1a1aa', fontSize: 10 }} />
                            <Radar name="User" dataKey="A" stroke="#ef4444" fill="#ef4444" fillOpacity={0.5} />
                        </RadarChart>
                    </ResponsiveContainer>
                </ChartCard>
            </div>

            {/* History Table */}
            <div className="bg-[#12121a] border border-zinc-800 rounded-[40px] overflow-hidden">
                <div className="p-8 border-b border-zinc-900 flex justify-between items-center">
                    <h3 className="text-xl font-bold text-white uppercase tracking-tight">Recent Sessions</h3>
                    <button className="text-zinc-500 text-xs font-bold uppercase tracking-widest hover:text-white transition-colors">History Hub</button>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-zinc-900/50 text-zinc-500 text-[10px] uppercase font-black tracking-widest">
                            <tr>
                                <th className="px-8 py-4">Session Date</th>
                                <th className="px-8 py-4">Topic</th>
                                <th className="px-8 py-4">Band</th>
                                <th className="px-8 py-4">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-900">
                            {history.map((row, i) => (
                                <tr key={i} className="hover:bg-zinc-900/30 transition-colors group cursor-pointer">
                                    <td className="px-8 py-5 text-sm text-zinc-400">{row.date}</td>
                                    <td className="px-8 py-5 font-bold text-white">{row.topic}</td>
                                    <td className="px-8 py-5 font-black text-red-500">{row.score.toFixed(1)}</td>
                                    <td className="px-8 py-5">
                                        <span className={`px-2 py-1 rounded-lg text-[10px] font-black uppercase ${row.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-red-500/10 text-red-500'}`}>
                                            {row.status}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {/* Sidebar Gadgets */}
        <div className="space-y-8">
            <AchievementsList />
            
            <div className="bg-gradient-to-br from-zinc-800 to-zinc-900 p-8 rounded-[40px] border border-zinc-800 shadow-xl relative overflow-hidden group">
                <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
                    <Zap size={140} />
                </div>
                <h4 className="text-xl font-bold text-white uppercase mb-2">Weekly Goal</h4>
                <p className="text-zinc-500 text-sm mb-6">Complete 3 full mock exams with Band 7.5+.</p>
                <div className="space-y-4">
                    <div className="flex justify-between text-[10px] font-black uppercase text-zinc-400">
                        <span>Progress</span>
                        <span>67%</span>
                    </div>
                    <div className="h-3 bg-zinc-950 rounded-full p-1 border border-zinc-800/50">
                        <div className="h-full bg-gradient-to-r from-red-600 to-amber-500 rounded-full" style={{ width: '67%' }} />
                    </div>
                </div>
                <button className="w-full mt-8 py-3 bg-zinc-100 text-black rounded-xl font-bold text-xs uppercase tracking-widest flex items-center justify-center gap-2">
                    Activate Boost <ArrowRight size={14} />
                </button>
            </div>
        </div>

      </div>
    </div>
  );
}

interface StatBoxProps { icon: LucideIcon; label: string; value: string; trend: string; color: string; }
function StatBox({ icon: Icon, label, value, trend, color }: StatBoxProps) {
    return (
        <div className="bg-[#12121a] border border-zinc-800 p-8 rounded-[40px] hover:border-zinc-700 transition-all group">
            <div className="flex justify-between items-start mb-6">
                <div className={`p-4 rounded-2xl bg-zinc-900 border border-zinc-800 group-hover:bg-zinc-800 transition-colors ${color}`}>
                    <Icon size={24} />
                </div>
                <span className="text-[10px] font-black text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full uppercase tracking-widest">{trend}</span>
            </div>
            <p className="text-zinc-500 text-xs font-bold uppercase tracking-widest">{label}</p>
            <h3 className="text-4xl font-black text-white mt-1">{value}</h3>
        </div>
    );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <div className="bg-[#12121a] border border-zinc-800 p-8 rounded-[40px] shadow-xl">
            <h4 className="text-sm font-black text-zinc-500 uppercase tracking-widest mb-8">{title}</h4>
            {children}
        </div>
    );
}
