import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

# Reuse the same cheap/fast model
llm = ChatOpenAI(
    base_url="https://api.deepinfra.com/v1/openai",
    api_key=os.getenv("DEEPINFRA_API_KEY"),
    model="meta-llama/Llama-3.2-3B-Instruct",
    temperature=0.0, # We want exact translation, not creativity
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