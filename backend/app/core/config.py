import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys & URLs
    DEEPINFRA_API_KEY: Optional[str] = os.getenv("DEEPINFRA_API_KEY")
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    
    # Models
    EVALUATOR_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"
    TRANSLATOR_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ielts_pressure.db")
    
    # Storage
    AUDIO_STORAGE_DIR: str = "audio_storage"
    
    # Defaults
    DEFAULT_USER_ID: str = "default_user"
    INITIAL_PROMPT: str = "Tell me about your hometown."
    
    # Educational Content
    PART_1_TOPICS: list[str] = [
        "Tell me about your hometown.",
        "Tell me about your job or studies.",
        "Do you prefer living in a house or an apartment?",
        "How do you usually spend your weekends?",
        "Tell me about your family.",
        "Do you like traveling?",
        "What kind of music do you like?"
    ]
    
    @property
    def PART_2_CUES(self) -> list[dict]:
        import json
        p2_path = os.path.join(os.path.dirname(__file__), "p2_cues.json")
        try:
            with open(p2_path, "r") as f:
                return json.load(f)["topics"]
        except Exception:
            return []
    MAX_AUDIO_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: list[str] = [".webm", ".mp3", ".wav", ".m4a", ".ogg"]
    RATE_LIMIT_COUNT: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    AUDIO_CLEANUP_HOURS: int = 24
    WHISPER_MODEL_SIZE: str = "medium.en"  # "small.en" or "base.en" for lower RAM
    
    # Adaptive Logic Thresholds
    STRESS_INCREASE_THRESHOLD: float = 0.7
    STRESS_DECREASE_THRESHOLD: float = 0.4
    
    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
