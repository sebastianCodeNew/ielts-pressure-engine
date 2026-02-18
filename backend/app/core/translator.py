import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from app.core.config import settings

# Reuse the same cheap/fast model
llm = ChatOpenAI(
    base_url=settings.DEEPINFRA_BASE_URL,
    api_key=settings.DEEPINFRA_API_KEY,
    model=settings.TRANSLATOR_MODEL,
    temperature=0.0, # We want exact translation, not creativity
    timeout=20,
)

def translate_to_english(text_id: str) -> str:
    """
    Translates Indonesian text to natural spoken English.
    """
    prompt = f"""
    Task: Translate this Indonesian text to English.
    Style: Casual, Spoken, Natural.
    Input: "{text_id}"
    
    Rules:
    - Output ONLY the English translation.
    - No explanations.
    - No "Here is the translation".
    """
    
    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        # Clean up any potential quotes or whitespace
        return response.content.strip().replace('"', '')
    except Exception as e:
        print(f"Translation Error: {e}")
        return "Error loading translation."

def translate_to_indonesian(text_en: str) -> str:
    """
    Translates English text to natural spoken Indonesian.
    """
    prompt = f"""
    Task: Translate this English text to Indonesian.
    Style: Educational, Supportive, Natural.
    Input: "{text_en}"
    
    Rules:
    - Output ONLY the Indonesian translation.
    - No explanations.
    - No "Here is the translation".
    """
    
    try:
        response = llm.invoke([SystemMessage(content=prompt)])
        return response.content.strip().replace('"', '')
    except Exception as e:
        print(f"Translation Error (EN->ID): {e}")
        return "Gagal memuat terjemahan."