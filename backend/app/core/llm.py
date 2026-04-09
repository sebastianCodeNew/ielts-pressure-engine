from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_llm(
    model_name: str = None, temperature: float = 0.1, timeout: int = 60
) -> ChatOpenAI:
    """
    Factory function to create a standardized ChatOpenAI client
    configured for the DeepInfra backend.
    """
    selected_model = model_name or settings.EVALUATOR_MODEL
    return ChatOpenAI(
        base_url=settings.DEEPINFRA_BASE_URL,
        api_key=settings.DEEPINFRA_API_KEY,
        model=selected_model,
        temperature=temperature,
        timeout=timeout,
    )
