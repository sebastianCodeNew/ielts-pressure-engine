"use client";
import { useState } from "react";

export default function TranslatorWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [indoText, setIndoText] = useState("");
  const [engText, setEngText] = useState("");
  const [loading, setLoading] = useState(false);

  const handleTranslate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!indoText.trim()) return;

    setLoading(true);
    try {
      const res = await fetch("http://127.0.0.1:8000/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: indoText }),
      });
      const data = await res.json();
      setEngText(data.translated);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 w-full max-w-xl px-4 z-50">
      {/* The Result Bubble (Only shows if there is a result) */}
      {engText && (
        <div className="mb-2 p-3 bg-red-900/80 border border-red-500 text-white rounded text-center animate-in fade-in slide-in-from-bottom-2">
          <span className="text-xs text-red-300 uppercase tracking-widest block mb-1">English Aid</span>
          <p className="text-lg font-medium">{engText}</p>
        </div>
      )}

      {/* The Input Bar */}
      <div className={`bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl transition-all overflow-hidden ${isOpen ? "h-auto" : "h-12"}`}>
        
        {/* Header / Toggle */}
        <button 
          onClick={() => setIsOpen(!isOpen)}
          className="w-full h-12 flex items-center justify-between px-4 hover:bg-zinc-800 text-xs text-zinc-400 uppercase tracking-widest"
        >
          <span>{isOpen ? "Close Translator" : "Stuck? Type Indonesian here"}</span>
          <span>{isOpen ? "▼" : "▲"}</span>
        </button>

        {/* The Form */}
        {isOpen && (
          <form onSubmit={handleTranslate} className="p-2 flex gap-2">
            <input
              type="text"
              value={indoText}
              onChange={(e) => setIndoText(e.target.value)}
              placeholder="e.g. Saya bingung mau ngomong apa..."
              className="flex-1 bg-zinc-950 text-white p-3 rounded border border-zinc-700 focus:border-red-500 outline-none text-sm"
              autoFocus
            />
            <button 
              type="submit" 
              disabled={loading}
              className="bg-zinc-100 text-zinc-950 px-4 py-2 rounded font-bold hover:bg-white disabled:opacity-50"
            >
              {loading ? "..." : "EN"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}