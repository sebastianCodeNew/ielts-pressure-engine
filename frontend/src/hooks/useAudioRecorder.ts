import { useState, useRef, useEffect, useCallback } from "react";

export function useAudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const stopTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const startRecording = useCallback(async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setStream(mediaStream);
      
      const options = { mimeType: "audio/webm;codecs=opus" };
      const mimeType = MediaRecorder.isTypeSupported(options.mimeType) 
        ? options.mimeType 
        : "audio/webm";

      mediaRecorderRef.current = new MediaRecorder(mediaStream, { mimeType });
      chunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setAudioBlob(blob);
        mediaStream.getTracks().forEach((track) => track.stop());
        setStream(null);
      };

      mediaRecorderRef.current.start(200); 
      setIsRecording(true);
    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  }, []);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || !isRecording) return;

    // Update UI immediately.
    setIsRecording(false);

    // Clear any existing stop timer.
    if (stopTimeoutRef.current) {
      clearTimeout(stopTimeoutRef.current);
      stopTimeoutRef.current = null;
    }

    try {
      // Flush the last buffered chunk before stopping.
      if (recorder.state === "recording") {
        recorder.requestData();
      }
    } catch (err) {
      console.error("MediaRecorder requestData error:", err);
    }

    try {
      if (recorder.state !== "inactive") {
        recorder.stop();
      }
    } catch (err) {
      console.error("MediaRecorder stop error:", err);
    }

    // Fallback: if onstop doesn't fire, release mic and allow retry.
    stopTimeoutRef.current = setTimeout(() => {
      try {
        if (stream) {
          stream.getTracks().forEach((track) => track.stop());
        }
      } catch (err) {
        console.error("Error stopping mic stream:", err);
      }
      stopTimeoutRef.current = null;
    }, 2500);
  }, [isRecording, stream]);

  // CLEANUP: Ensure mic and timers are released on unmount
  useEffect(() => {
    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
      if (stopTimeoutRef.current) {
        clearTimeout(stopTimeoutRef.current);
      }
    };
  }, [stream]);

  return { isRecording, startRecording, stopRecording, audioBlob, setAudioBlob, stream };
}