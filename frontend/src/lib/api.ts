import { Intervention, TranslationResponse } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export class ApiClient {
  private static async fetchWithRetry(
    url: string,
    options: RequestInit,
    retries: number = 3,
  ): Promise<Response> {
    try {
      const response = await fetch(url, options);
      if (response.status === 429 && retries > 0) {
        // Rate limited - wait and retry
        const wait = response.headers.get("Retry-After")
          ? parseInt(response.headers.get("Retry-After")!) * 1000
          : 2000;
        await new Promise((r) => setTimeout(r, wait));
        return this.fetchWithRetry(url, options, retries - 1);
      }
      if (!response.ok && retries > 0 && response.status >= 500) {
        await new Promise((r) => setTimeout(r, 1000));
        return this.fetchWithRetry(url, options, retries - 1);
      }
      return response;
    } catch (err) {
      if (retries > 0) {
        await new Promise((r) => setTimeout(r, 1000));
        return this.fetchWithRetry(url, options, retries - 1);
      }
      throw err;
    }
  }

  static async submitAudio(
    blob: Blob,
    taskId: string = "default",
  ): Promise<Intervention> {
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");
    formData.append("task_id", taskId);

    const res = await this.fetchWithRetry(`${API_BASE_URL}/submit-audio`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`API Error: ${res.statusText}`);
    return res.json();
  }

  static async startExam(
    userId: string,
    examType: string = "FULL_MOCK",
    topicOverride?: string,
  ): Promise<any> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/exams/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        exam_type: examType,
        topic_override: topicOverride,
      }),
    });
    if (!res.ok) throw new Error("Failed to start exam");
    return res.json();
  }

  static async submitExamAudio(
    sessionId: string,
    blob: Blob,
    isRetry: boolean = false,
    isRefactor: boolean = false
  ): Promise<Intervention> {
    const formData = new FormData();
    formData.append("file", blob, "recording.webm");

    const res = await this.fetchWithRetry(
      `${API_BASE_URL}/v1/exams/${sessionId}/submit-audio?is_retry=${isRetry}&is_refactor=${isRefactor}`,
      {
        method: "POST",
        body: formData,
      },
    );
    if (!res.ok) throw new Error(`Exam API Error: ${res.statusText}`);
    return res.json();
  }

  static async translateText(text: string): Promise<TranslationResponse> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) throw new Error("Translation failed");
    return res.json();
  }

  static async getStats(): Promise<any> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/users/me/stats`, {
      method: "GET",
    });
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  }

  static async getHistory(): Promise<any[]> {
    const res = await this.fetchWithRetry(
      `${API_BASE_URL}/v1/users/me/history`,
      { method: "GET" },
    );
    if (!res.ok) throw new Error("Failed to fetch history");
    return res.json();
  }

  static async getExamSummary(sessionId: string): Promise<any> {
    const res = await this.fetchWithRetry(
      `${API_BASE_URL}/v1/exams/${sessionId}/summary`,
      { method: "GET" },
    );
    if (!res.ok) throw new Error("Failed to fetch exam summary");
    return res.json();
  }

  static async getExamStatus(sessionId: string): Promise<any> {
    const res = await this.fetchWithRetry(
      `${API_BASE_URL}/v1/exams/${sessionId}/status`,
      { method: "GET" },
    );
    if (!res.ok) throw new Error("Failed to fetch exam status");
    return res.json();
  }

  static async getTopics(): Promise<any[]> {
    const res = await this.fetchWithRetry(
      `${API_BASE_URL}/v1/practice/topics`,
      { method: "GET" },
    );
    if (!res.ok) throw new Error("Failed to fetch topics");
    return res.json();
  }

  static async getVocabulary(): Promise<any[]> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/vocabulary/`, {
      method: "GET",
    });
    if (!res.ok) throw new Error("Failed to fetch vocabulary");
    return res.json();
  }

  static async getStudyPlan(): Promise<any> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/study-plan/`, {
      method: "GET",
    });
    if (!res.ok) throw new Error("Failed to fetch study plan");
    return res.json();
  }

  static async getHint(
    sessionId: string,
  ): Promise<{ vocabulary: string[]; starter: string; grammar_tip: string }> {
    const res = await this.fetchWithRetry(
      `${API_BASE_URL}/v1/hints/${sessionId}/hint`,
      { method: "GET" },
    );
    if (!res.ok) throw new Error("Failed to fetch hint");
    return res.json();
  }

  static async updateProfile(data: {
    target_band: string;
    weakness: string;
  }): Promise<any> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/users/me`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update profile");
    return res.json();
  }

  static async saveVocabulary(word: string, context?: string): Promise<any> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/vocabulary/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // We'll mock a definition for now since the UI only passes the word
      body: JSON.stringify({
        word,
        definition: "Saved from Idea Generator",
        context_sentence: context,
      }),
    });
    if (!res.ok) throw new Error("Failed to save vocabulary");
    return res.json();
  }

  static async analyzeShadowing(targetText: string, blob: Blob): Promise<any> {
    const formData = new FormData();
    formData.append("file", blob, "shadow.webm");
    
    // We pass target_text as a query param or part of form data? 
    // In my backend I used it as a param.
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/exams/analyze-shadowing?target_text=${encodeURIComponent(targetText)}`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Shadowing analysis failed");
    return res.json();
  }

  static async getWarmUpVocabulary(userId: string = "default_user"): Promise<any[]> {
    const res = await this.fetchWithRetry(`${API_BASE_URL}/v1/exams/warmup?user_id=${userId}`, {
      method: "GET",
    });
    if (!res.ok) throw new Error("Failed to fetch warmup vocabulary");
    return res.json();
  }
}
