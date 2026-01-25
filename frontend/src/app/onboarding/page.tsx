"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { 
  ArrowRight, Mic2, Star, Target, CheckCircle2,
  Sparkles, ShieldCheck, Trophy
} from "lucide-react";

import { ApiClient } from "@/lib/api";

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    targetBand: "7.5",
    weakness: "Fluency",
    examDate: "Next Month"
  });
  const router = useRouter();

  const [saving, setSaving] = useState(false);
  
  const nextStep = async () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      setSaving(true);
      try {
        await ApiClient.updateProfile({
            target_band: formData.targetBand,
            weakness: formData.weakness
        });
        router.push("/dashboard");
      } catch (e) {
        console.error("Onboarding Save Failed", e);
        // Fallback for demo navigation if API is down
        router.push("/dashboard");
      } finally {
        setSaving(false);
      }
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[80vh] p-4">
      <div className="max-w-xl w-full bg-[#12121a] border border-zinc-800 rounded-[40px] shadow-2xl p-8 md:p-12 animate-in zoom-in duration-500">
        
        {/* Progress Dots */}
        <div className="flex justify-center gap-2 mb-12">
           {[1,2,3].map(i => (
             <div key={i} className={`h-1.5 rounded-full transition-all duration-500 ${step === i ? 'w-8 bg-red-600' : 'w-2 bg-zinc-800'}`} />
           ))}
        </div>

        {step === 1 && (
          <div className="space-y-8 text-center animate-in fade-in slide-in-from-bottom duration-500">
            <div className="w-20 h-20 bg-red-600 rounded-3xl mx-auto flex items-center justify-center shadow-2xl rotate-6">
                <Mic2 size={40} className="text-white" />
            </div>
            <div className="space-y-4">
                <h1 className="text-4xl font-black text-white uppercase tracking-tighter">Welcome to <span className="text-red-600">Pressure</span></h1>
                <p className="text-zinc-500 font-medium">The world's first AI examiner that adapts to your stress levels. Ready to hit your target band?</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
                <Feature icon={ShieldCheck} label="AI Precision" sub="Llama-3.3 Powered" />
                <Feature icon={Sparkles} label="Adaptive Stress" sub="Real-time Difficulty" />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-8 animate-in fade-in slide-in-from-right duration-500">
             <div className="text-center">
                <h2 className="text-3xl font-black text-white uppercase">Your <span className="text-red-600">Goal</span></h2>
                <p className="text-zinc-500 mt-2 font-medium">Let's customize your preparation path.</p>
             </div>
             
             <div className="space-y-6">
                <div className="space-y-2">
                    <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest pl-1">Target Band Score</label>
                    <select 
                      value={formData.targetBand}
                      onChange={(e) => setFormData({...formData, targetBand: e.target.value})}
                      className="w-full p-4 bg-zinc-900 border border-zinc-800 rounded-2xl text-white font-bold focus:border-red-600 outline-none transition-all"
                    >
                        {["6.0", "6.5", "7.0", "7.5", "8.0", "8.5", "9.0"].map(v => (
                            <option key={v} value={v}>Band {v}</option>
                        ))}
                    </select>
                </div>
                
                <div className="space-y-2">
                    <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest pl-1">Primary Weakness</label>
                    <div className="grid grid-cols-2 gap-3">
                        {["Fluency", "Grammar", "Vocab", "Anxiety"].map(w => (
                            <button 
                              key={w}
                              onClick={() => setFormData({...formData, weakness: w})}
                              className={`p-4 rounded-2xl border font-bold transition-all text-sm ${formData.weakness === w ? 'bg-red-600 border-red-600 text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-500 hover:border-zinc-700'}`}
                            >
                                {w}
                            </button>
                        ))}
                    </div>
                </div>
             </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-8 text-center animate-in fade-in slide-in-from-right duration-500">
             <div className="w-20 h-20 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-full mx-auto flex items-center justify-center">
                <CheckCircle2 size={40} />
             </div>
             <div className="space-y-2">
                <h2 className="text-3xl font-black text-white uppercase">Ready for <span className="text-emerald-500">Launch</span></h2>
                <p className="text-zinc-500 font-medium">We've generated your initial study roadmap.</p>
             </div>
             <div className="bg-zinc-900/50 p-6 rounded-3xl border border-zinc-800 text-left space-y-4">
                <div className="flex gap-4 items-center">
                    <div className="p-2 bg-red-600/10 rounded-xl text-red-500"><Target size={20} /></div>
                    <p className="text-sm font-bold text-white">Daily Mock Simulation Plan</p>
                </div>
                <div className="flex gap-4 items-center">
                    <div className="p-2 bg-amber-500/10 rounded-xl text-amber-500"><Trophy size={20} /></div>
                    <p className="text-sm font-bold text-white">Achievement Tracking Online</p>
                </div>
             </div>
          </div>
        )}

        <button 
          onClick={nextStep}
          className="w-full mt-12 py-5 bg-red-600 hover:bg-red-500 text-white rounded-[24px] font-black uppercase tracking-widest flex items-center justify-center gap-3 transition-all hover:scale-[1.02] active:scale-95 shadow-[0_0_40px_rgba(220,38,38,0.2)]"
        >
          {step === 3 ? "Enter Dashboard" : "Continue"} <ArrowRight size={20} />
        </button>

      </div>
    </div>
  );
}

function Feature({ icon: Icon, label, sub }: any) {
    return (
        <div className="flex items-center gap-4 p-4 bg-zinc-900/50 rounded-2xl border border-zinc-800/50">
            <div className="text-red-500 bg-red-500/10 p-2 rounded-lg">
                <Icon size={18} />
            </div>
            <div>
                <p className="text-xs font-black text-white uppercase">{label}</p>
                <p className="text-[10px] text-zinc-500">{sub}</p>
            </div>
        </div>
    );
}
