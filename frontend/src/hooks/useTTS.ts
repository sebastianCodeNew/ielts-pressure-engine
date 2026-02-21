import { useState, useEffect, useCallback, useRef } from 'react';

export const useTTS = () => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [supportsTTS, setSupportsTTS] = useState(false);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    
    setSupportsTTS(true);

    // B12 Fix: Voices are loaded asynchronously in most browsers.
    // We must listen for `voiceschanged` to get the full list.
    const loadVoices = () => {
      voicesRef.current = window.speechSynthesis.getVoices();
    };

    loadVoices(); // Try immediately (works in Firefox)
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);

    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
    };
  }, []);

  const speak = useCallback((text: string) => {
    if (!supportsTTS || !text) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    
    // Select a voice (use cached voices from ref)
    const voices = voicesRef.current;
    const preferredVoice = voices.find(v => v.name.includes("Google US English")) || 
                           voices.find(v => v.lang.startsWith("en-US")) || 
                           voices.find(v => v.lang.startsWith("en")) ||
                           voices[0];
    
    if (preferredVoice) utterance.voice = preferredVoice;
    
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  }, [supportsTTS]);

  const stop = useCallback(() => {
     if (typeof window !== 'undefined') {
        window.speechSynthesis.cancel();
        setIsSpeaking(false);
     }
  }, []);

  return { speak, stop, isSpeaking, supportsTTS };
};
