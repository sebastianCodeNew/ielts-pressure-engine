from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_llm(temperature: float = 0.1, timeout: int = 60) -> ChatOpenAI:
    """
    Factory function to create a standardized ChatOpenAI client 
    configured for the DeepInfra backend.
    """
    return ChatOpenAI(
        base_url=settings.DEEPINFRA_BASE_URL,
        api_key=settings.DEEPINFRA_API_KEY,
        model=settings.EVALUATOR_MODEL,
        temperature=temperature,
        timeout=timeout,
    )
