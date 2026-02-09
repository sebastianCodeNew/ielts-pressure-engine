export type ActionId = 
  | 'MAINTAIN' 
  | 'ESCALATE_PRESSURE' 
  | 'DEESCALATE_PRESSURE' 
  | 'FORCE_RETRY' 
  | 'DRILL_SPECIFIC' 
  | 'FAIL';

export interface SignalMetrics {
  fluency_wpm: number;
  hesitation_ratio: number;
  grammar_error_count: number;
  filler_count: number;
  coherence_score: number;
  is_complete: boolean;
}

export interface Intervention {
  action_id: ActionId;
  next_task_prompt: string;
  topic_core?: string;
  constraints: Record<string, any>;
  
  // Educational Fields
  ideal_response?: string;
  feedback_markdown?: string;
  correction_drill?: string;
  user_transcript?: string;
  reasoning?: string;
  keywords?: string[];
  target_keywords?: string[];
  stress_level?: number;
  
  // Audio Mirror
  user_audio_url?: string;
  
  // Celebration
  keywords_hit?: string[];

  // v4.0 Active Recall Quiz
  quiz_question?: string;
  quiz_options?: string[];
  quiz_correct_index?: number;

  // v4.0 Radar Chart
  radar_metrics?: Record<string, number>;
}

export interface TranslationResponse {
  original: string;
  translated: string;
}
