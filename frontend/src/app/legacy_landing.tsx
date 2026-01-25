"use client";
import Link from "next/link";
import { ArrowRight, Mic2, LayoutDashboard, Library } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 text-center bg-[#0d0d12]">
      
      {/* Background Glow */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-red-600/5 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-3xl space-y-8">
        <div className="space-y-2">
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white">
                Master the <span className="text-red-600">IELTS</span> <br />
                with AI Precision.
            </h1>
            <p className="text-zinc-500 text-lg md:text-xl max-w-xl mx-auto">
                Real-time analysis, structured mock exams, and personalized feedback designed to push you to Band 8.0+.
            </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-12">
            <FeatureLink 
                href="/exam" 
                icon={Mic2} 
                title="Simulator" 
                desc="Structure mocks" 
                color="bg-red-600" 
            />
            <FeatureLink 
                href="/dashboard" 
                icon={LayoutDashboard} 
                title="Dashboard" 
                desc="Tracks analytics" 
            />
            <FeatureLink 
                href="/practice" 
                icon={Library} 
                title="Topic Bank" 
                desc="Drill skills" 
            />
        </div>

        <div className="pt-12">
            <Link href="/exam" className="inline-flex items-center gap-2 px-8 py-4 bg-zinc-100 hover:bg-white text-black font-bold rounded-2xl transition-all hover:scale-105">
                Get Started for Free <ArrowRight size={20} />
            </Link>
        </div>
      </div>
    </div>
  );
}

function FeatureLink({ href, icon: Icon, title, desc, color }: any) {
    return (
        <Link href={href} className="group p-6 bg-zinc-900/50 border border-zinc-800 rounded-2xl text-left hover:border-zinc-700 transition-all">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${color || 'bg-zinc-800'} text-white`}>
                <Icon size={20} />
            </div>
            <h3 className="font-bold text-zinc-100 mb-1">{title}</h3>
            <p className="text-xs text-zinc-500">{desc}</p>
        </Link>
    );
}

