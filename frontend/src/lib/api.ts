import { Intervention, TranslationResponse } from "./types";

const API_BASE_URL = "http://127.0.0.1:8000/api";

export class ApiClient {
  
  static async submitAudio(blob: Blob, taskId: string = "default"): Promise<Intervention> {
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    formData.append("task_id", taskId);

    const res = await fetch(`${API_BASE_URL}/submit-audio`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`API Error: ${res.statusText}`);
    }

    return res.json();
  }

  static async startExam(examType: string = "FULL_MOCK"): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/v1/exams/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ exam_type: examType }),
    });
    if (!res.ok) throw new Error("Failed to start exam");
    return res.json();
  }

  static async submitExamAudio(sessionId: string, blob: Blob): Promise<Intervention> {
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");

    const res = await fetch(`${API_BASE_URL}/v1/exams/${sessionId}/submit-audio`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`Exam API Error: ${res.statusText}`);
    }

    return res.json();
  }

  static async translateText(text: string): Promise<TranslationResponse> {
    const res = await fetch(`${API_BASE_URL}/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!res.ok) {
      throw new Error("Translation failed");
    }

    return res.json();
  }
}
