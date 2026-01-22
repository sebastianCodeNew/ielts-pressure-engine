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
