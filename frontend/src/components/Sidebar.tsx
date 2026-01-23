"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, Mic2, Library, BookOpen, Settings, LogOut, Trophy
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { icon: LayoutDashboard, label: "Dashboard", href: "/dashboard" },
    { icon: Mic2, label: "Simulator", href: "/exam" },
    { icon: Library, label: "Topic Bank", href: "/practice" },
    { icon: BookOpen, label: "Vocabulary", href: "/vocabulary" },
    { icon: Trophy, label: "Achievements", href: "/achievements" },
  ];

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-[#0d0d12] border-r border-zinc-800 flex flex-col z-50">
      <div className="p-8">
        <h1 className="text-2xl font-black text-white tracking-tighter flex items-center gap-2">
          IELTS <span className="text-red-600">PRESSURE</span>
        </h1>
      </div>

      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link 
              key={item.href} 
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl font-bold transition-all ${
                isActive 
                  ? "bg-red-600 text-white shadow-[0_0_20px_rgba(220,38,38,0.3)]" 
                  : "text-zinc-500 hover:text-zinc-100 hover:bg-zinc-900"
              }`}
            >
              <item.icon size={20} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-zinc-900">
        <button className="flex items-center gap-3 px-4 py-3 w-full rounded-xl font-bold text-zinc-500 hover:text-white hover:bg-zinc-900 transition-all">
          <Settings size={20} />
          Settings
        </button>
        <button className="flex items-center gap-3 px-4 py-3 w-full rounded-xl font-bold text-red-500 hover:bg-red-500/10 transition-all">
          <LogOut size={20} />
          Logout
        </button>
      </div>

      <div className="p-6 bg-zinc-900/30 m-4 rounded-2xl border border-zinc-800/50">
         <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-red-600 to-amber-500" />
            <div className="flex-1 overflow-hidden">
               <p className="text-sm font-bold text-white truncate">Sebastian</p>
               <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-black">Pro Plan</p>
            </div>
         </div>
      </div>
    </aside>
  );
}
