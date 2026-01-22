"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Mic2, Library, Award, BookOpen, Settings } from "lucide-react";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Exam Simulator", href: "/exam", icon: Mic2 },
  { name: "Topic Bank", href: "/practice", icon: Library },
  { name: "Vocabulary", href: "/vocabulary", icon: BookOpen },
  { name: "Achievements", href: "/achievements", icon: Award },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 w-64 bg-[#0a0a0f] border-r border-zinc-800 flex flex-col z-50">
      <div className="p-6">
        <h1 className="text-xl font-bold bg-gradient-to-r from-red-500 to-amber-500 bg-clip-text text-transparent">
          IELTS ELITE
        </h1>
        <p className="text-[10px] text-zinc-500 uppercase tracking-widest mt-1">Platform v2.0</p>
      </div>

      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                isActive
                  ? "bg-red-500/10 text-red-500 border border-red-500/20"
                  : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200"
              }`}
            >
              <Icon size={20} className={isActive ? "text-red-500" : "text-zinc-500 group-hover:text-zinc-300"} />
              <span className="font-medium text-sm">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-zinc-900 mt-auto">
        <Link href="/settings" className="flex items-center gap-3 px-4 py-3 text-zinc-400 hover:text-white transition-colors">
          <Settings size={20} />
          <span className="text-sm font-medium">Settings</span>
        </Link>
        <div className="mt-4 p-4 bg-zinc-900/50 rounded-xl border border-zinc-800">
           <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-600 flex items-center justify-center font-bold text-sm text-white">S</div>
              <div>
                <p className="text-sm font-semibold text-zinc-200">Sebastian</p>
                <p className="text-[10px] text-emerald-500 font-bold uppercase">Pro Learner</p>
              </div>
           </div>
        </div>
      </div>
    </aside>
  );
}
