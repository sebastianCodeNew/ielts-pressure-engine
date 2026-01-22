"use client";
import { useState, useEffect } from "react";
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, AreaChart, Area
} from "recharts";
import { TrendingUp, Award, BookOpen, Clock, ChevronRight } from "lucide-react";

const mockScoreHistory = [
  { name: "Attempt 1", score: 5.5 },
  { name: "Attempt 2", score: 6.0 },
  { name: "Attempt 3", score: 6.5 },
  { name: "Attempt 4", score: 6.5 },
  { name: "Attempt 5", score: 7.0 },
  { name: "Attempt 6", score: 7.5 },
];

const mockSkillData = [
  { subject: 'Fluency', A: 7.5, fullMark: 9 },
  { subject: 'Coherence', A: 7.0, fullMark: 9 },
  { subject: 'Lexical', A: 8.0, fullMark: 9 },
  { subject: 'Grammar', A: 6.5, fullMark: 9 },
  { subject: 'Pronunciation', A: 7.5, fullMark: 9 },
];

export default function Dashboard() {
  return (
    <div className="p-8 space-y-8 animate-in fade-in duration-700">
      
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-zinc-100">Welcome back, Sebastian</h1>
          <p className="text-zinc-500 mt-1">You're on track to hit Band 8.0 by next month.</p>
        </div>
        <div className="flex gap-3">
           <button className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-xl text-sm font-medium transition-colors">Generate Study Plan</button>
           <button className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-xl text-sm font-bold transition-all hover:scale-105">New Mock Exam</button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard icon={TrendingUp} label="Current Band" value="7.5" color="text-red-500" trend="+0.5" />
        <StatCard icon={Award} label="Exams Taken" value="12" color="text-amber-500" trend="+2" />
        <StatCard icon={BookOpen} label="Vocab Mastery" value="482" color="text-emerald-500" trend="+45" />
        <StatCard icon={Clock} label="Practice Time" value="18.5h" color="text-blue-500" trend="+3.2h" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Main Progression Chart */}
        <div className="lg:col-span-2 bg-[#12121a] border border-zinc-800/50 p-6 rounded-2xl shadow-xl">
          <h3 className="text-lg font-semibold text-zinc-200 mb-6 flex items-center gap-2">
            <TrendingUp size={18} className="text-red-500" />
            Band Score Progression
          </h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockScoreHistory}>
                <defs>
                  <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="name" stroke="#52525b" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#52525b" fontSize={12} tickLine={false} axisLine={false} domain={[0, 9]} />
                <Tooltip 
                   contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '12px' }}
                   itemStyle={{ color: '#f4f4f5' }}
                />
                <Area type="monotone" dataKey="score" stroke="#ef4444" strokeWidth={3} fillOpacity={1} fill="url(#colorScore)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Skill Breakdown Chart */}
        <div className="bg-[#12121a] border border-zinc-800/50 p-6 rounded-2xl shadow-xl">
          <h3 className="text-lg font-semibold text-zinc-200 mb-4 text-center">Skill Breakdown</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={mockSkillData}>
                <PolarGrid stroke="#27272a" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#a1a1aa', fontSize: 10 }} />
                <Radar
                  name="Sebastian"
                  dataKey="A"
                  stroke="#ef4444"
                  fill="#ef4444"
                  fillOpacity={0.6}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Recent Attempts Table */}
      <div className="bg-[#12121a] border border-zinc-800/50 rounded-2xl overflow-hidden">
         <div className="p-6 border-b border-zinc-800 flex justify-between items-center">
            <h3 className="font-semibold text-zinc-200">Recent Exam Simulations</h3>
            <button className="text-zinc-500 hover:text-white text-xs font-medium flex items-center gap-1 transition-colors">
                View All <ChevronRight size={14} />
            </button>
         </div>
         <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
                <thead className="bg-zinc-900/50 text-zinc-500 font-medium uppercase tracking-wider text-[10px]">
                    <tr>
                        <th className="px-6 py-4">Date</th>
                        <th className="px-6 py-4">Topic</th>
                        <th className="px-6 py-4">Duration</th>
                        <th className="px-6 py-4">Score</th>
                        <th className="px-6 py-4">Status</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                    <RecentRow date="Oct 20, 2025" topic="Education in AI" duration="14m" score="7.5" status="Completed" />
                    <RecentRow date="Oct 18, 2025" topic="Environmental Policy" duration="11m" score="6.5" status="Completed" />
                    <RecentRow date="Oct 15, 2025" topic="Work-Life Balance" duration="15m" score="7.0" status="Completed" />
                </tbody>
            </table>
         </div>
      </div>

    </div>
  );
}

function StatCard({ icon: Icon, label, value, color, trend }: any) {
  return (
    <div className="bg-[#12121a] border border-zinc-800/50 p-6 rounded-2xl hover:border-zinc-700/50 transition-all group shadow-lg">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-xl bg-zinc-900 border border-zinc-800 group-hover:bg-zinc-800 transition-colors ${color}`}>
            <Icon size={24} />
        </div>
        <span className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">
            {trend}
        </span>
      </div>
      <p className="text-zinc-500 text-sm font-medium">{label}</p>
      <p className="text-3xl font-bold text-zinc-100 mt-1">{value}</p>
    </div>
  );
}

function RecentRow({ date, topic, duration, score, status }: any) {
    return (
        <tr className="hover:bg-zinc-900/50 transition-colors cursor-pointer group">
            <td className="px-6 py-4 text-zinc-400 group-hover:text-zinc-200">{date}</td>
            <td className="px-6 py-4 font-semibold text-zinc-200">{topic}</td>
            <td className="px-6 py-4 text-zinc-500">{duration}</td>
            <td className="px-6 py-4 font-bold text-red-500">{score}</td>
            <td className="px-6 py-4">
                <span className="px-2 py-1 rounded-full text-[10px] font-bold uppercase bg-zinc-800 text-zinc-400 border border-zinc-700">
                    {status}
                </span>
            </td>
        </tr>
    );
}
