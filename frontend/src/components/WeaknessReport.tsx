"use client";

import { useEffect, useState } from "react";
import { ApiClient } from "@/lib/api";
import { AlertTriangle, TrendingUp, Target, X } from "lucide-react";

interface WeaknessReportData {
  skill_averages: Record<string, number>;
  lowest_area: string;
  trend_data: { session: number; score: number }[];
  recurring_errors: { error: string; count: number }[];
  total_attempts: number;
}

interface WeaknessReportProps {
  isOpen: boolean;
  onClose: () => void;
  userId?: string;
}

export function WeaknessReport({ isOpen, onClose, userId = "default_user" }: WeaknessReportProps) {
  const [data, setData] = useState<WeaknessReportData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      setLoading(true);
      fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/users/me/weakness-report?user_id=${userId}`)
        .then(res => res.json())
        .then(setData)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [isOpen, userId]);

  if (!isOpen) return null;

  const skills = data?.skill_averages || {};
  const maxScore = 9;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-700 rounded-3xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-8 relative">
        <button onClick={onClose} className="absolute top-6 right-6 text-zinc-500 hover:text-white transition-colors">
          <X size={24} />
        </button>

        <h2 className="text-2xl font-black text-white mb-2">Your Weakness Report</h2>
        <p className="text-zinc-500 text-sm mb-8">Analysis across {data?.total_attempts || 0} attempts</p>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-8">
            {/* Skill Radar (Simple Bar Chart) */}
            <div className="bg-zinc-800/50 rounded-2xl p-6">
              <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                <Target size={14} /> Skill Breakdown
              </h3>
              <div className="space-y-3">
                {Object.entries(skills).map(([skill, score]) => (
                  <div key={skill} className="flex items-center gap-4">
                    <span className={`w-28 text-sm font-medium ${skill === data?.lowest_area ? 'text-amber-500' : 'text-zinc-400'}`}>
                      {skill}
                    </span>
                    <div className="flex-1 h-3 bg-zinc-700 rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${skill === data?.lowest_area ? 'bg-amber-500' : 'bg-emerald-500'}`}
                        style={{ width: `${(score / maxScore) * 100}%` }}
                      />
                    </div>
                    <span className="text-white font-bold w-10 text-right">{score.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Lowest Area Callout */}
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-6 flex items-start gap-4">
              <AlertTriangle className="text-amber-500 flex-shrink-0 mt-1" size={24} />
              <div>
                <h4 className="text-amber-500 font-black uppercase text-xs tracking-widest mb-1">Focus Area</h4>
                <p className="text-white font-medium">
                  Your <span className="text-amber-400">{data?.lowest_area}</span> needs the most attention. 
                  The AI examiner will prioritize questions targeting this skill.
                </p>
              </div>
            </div>

            {/* Recurring Errors */}
            {data?.recurring_errors && data.recurring_errors.length > 0 && (
              <div className="bg-zinc-800/50 rounded-2xl p-6">
                <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest mb-4">
                  Top Recurring Errors
                </h3>
                <div className="flex flex-wrap gap-3">
                  {data.recurring_errors.map((err, i) => (
                    <div key={i} className="px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-full text-red-400 text-sm font-medium">
                      {err.error} <span className="text-red-600">({err.count}x)</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Trend Data */}
            {data?.trend_data && data.trend_data.length > 0 && (
              <div className="bg-zinc-800/50 rounded-2xl p-6">
                <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                  <TrendingUp size={14} /> Score Trend (Last {data.trend_data.length} Sessions)
                </h3>
                <div className="flex items-end gap-2 h-32">
                  {data.trend_data.map((d, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div 
                        className="w-full bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t-md transition-all duration-300"
                        style={{ height: `${(d.score / 9) * 100}%` }}
                      />
                      <span className="text-[10px] text-zinc-500">{d.session}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
