import { Intervention } from "@/lib/types";

interface HistorySidebarProps {
  history: { prompt: string; action: string; time: string }[];
  isOpen: boolean;
  toggle: () => void;
}

export default function HistorySidebar({ history, isOpen, toggle }: HistorySidebarProps) {
  return (
    <>
      {/* Toggle Button (Visible when closed) */}
      {!isOpen && (
        <button 
            onClick={toggle}
            className="fixed left-4 top-4 z-50 p-2 bg-zinc-800/80 rounded-full hover:bg-zinc-700 text-zinc-400 border border-zinc-700 transition-all hover:scale-110"
        >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3h18"/><path d="M3 12h18"/><path d="M3 21h18"/></svg>
        </button>
      )}

      {/* Sidebar Panel */}
      <div className={`fixed inset-y-0 left-0 w-80 bg-[#0a0a0e] border-r border-zinc-800 transform transition-transform duration-300 ease-in-out z-40 ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-6 h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-xl font-bold text-zinc-200 tracking-wider">SESSION LOG</h2>
                <button onClick={toggle} className="text-zinc-500 hover:text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 18 12"/></svg>
                </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-4">
                {history.length === 0 ? (
                    <p className="text-zinc-600 text-sm italic">No attempts yet. Start speaking!</p>
                ) : (
                    history.map((item, i) => (
                        <div key={i} className="p-3 bg-zinc-900/50 rounded-lg border border-zinc-800 hover:border-zinc-700 transition-colors">
                             <div className="flex justify-between items-start mb-1">
                                <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${item.action.includes('FAIL') ? 'bg-red-900/30 text-red-400' : 'bg-green-900/30 text-green-400'}`}>
                                    {item.action}
                                </span>
                                <span className="text-zinc-600 text-xs font-mono">{item.time}</span>
                             </div>
                             <p className="text-zinc-300 text-sm line-clamp-2">{item.prompt}</p>
                        </div>
                    ))
                )}
            </div>
            
            <div className="pt-6 mt-auto border-t border-zinc-800">
                <p className="text-center text-zinc-600 text-xs">IELTS Pressure Engine v1.1</p>
            </div>
        </div>
      </div>
    </>
  );
}
