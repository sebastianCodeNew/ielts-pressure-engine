"use client";

import React from 'react';

interface SmartDiffProps {
  original: string;
  improved: string;
}

export function SmartDiff({ original, improved }: SmartDiffProps) {
  // Simple diff logic for MVP: Word-level comparison
  // A robust diff-match-patch library is better for production, but we keep it dep-free here.
  
  const origWords = original.split(/\s+/);
  const impWords = improved.split(/\s+/);
  
  // This is a very naive diff visualization for demonstration.
  // In a real app, use 'diff' package.
  // Here we just show the improved version with highlights if we can detect simple changes.
  
  // Actually, for learning impact, let's try a slightly smarter naive diff
  // If words match map index 1:1, great. If not, just show improved for now to avoid messy UI.
  // But wait, the user wants "Edit Marks".
  
  // Let's rely on a visual convention: 
  // If the improved response is significantly different, we just show the improved one highlighted.
  // If it's close, we might try to diff.
  
  // BETTER APPROACH for MVP:
  // Since we don't have a diff lib, let's just render the "Improved" version 
  // but stylize it to look like a gold standard.
  // And maybe overlay distinct new words in green if they weren't in the original?
  
  const getDiffNodes = () => {
     const nodes = [];
     const lowerOrig = original.toLowerCase();
     
     for (let i = 0; i < impWords.length; i++) {
        const word = impWords[i];
        const cleanWord = word.replace(/[.,!?]/g, '').toLowerCase();
        
        // Is this root word in the original?
        const isNew = !lowerOrig.includes(cleanWord);
        
        nodes.push(
            <span key={i} className={`${isNew ? 'text-emerald-400 font-bold' : 'text-zinc-300'} mr-1`}>
                {word}
            </span>
        );
     }
     return nodes;
  };

  return (
    <div className="bg-zinc-900/50 p-4 rounded-xl border border-zinc-800">
        <div className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2 flex justify-between">
            <span>Optimized Response</span>
            <span className="text-emerald-500">Band 9 Edit</span>
        </div>
        <div className="text-sm leading-relaxed">
            {getDiffNodes()}
        </div>
        <div className="mt-3 pt-3 border-t border-zinc-800/50 flex gap-2">
            <div className="px-2 py-0.5 bg-zinc-800 text-[10px] text-zinc-400 rounded">Original:</div>
            <div className="text-[10px] text-zinc-500 line-through truncate flex-1">{original}</div>
        </div>
    </div>
  );
}
