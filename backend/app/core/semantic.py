import httpx
import numpy as np
from typing import List
from app.core.config import settings

# Load API Key from centralized config
DEEPINFRA_KEY = settings.DEEPINFRA_API_KEY
BASE_URL = settings.DEEPINFRA_BASE_URL

async def get_embedding_async(text: str) -> List[float]:
    """
    Sends text to DeepInfra and returns a vector (list of floats) (Async).
    """
    if not text or not isinstance(text, str):
        return [0.0] * 768
        
    from app.core.logger import logger
    if not DEEPINFRA_KEY:
        logger.warning("DEEPINFRA_API_KEY is missing. Returning zero vector.")
        return [0.0] * 768

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPINFRA_KEY}"
    }
    
    payload = {
        "input": text,
        "model": "google/embeddinggemma-300m",
        "encoding_format": "float"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(f"{BASE_URL}/embeddings", json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Embedding API Error: {response.text}")
                return [0.0] * 768

            data = response.json()
            return data["data"][0]["embedding"]
            
    except Exception as e:
        logger.error(f"Embedding Network Error (Async): {e}", exc_info=True)
        return [0.0] * 768

async def calculate_coherence_async(target_prompt: str, user_response: str) -> float:
    """
    Calculates the Cosine Similarity between two text vectors (Async).
    """
    import asyncio
    
    # Run both embeddings in parallel
    vec_a, vec_b = await asyncio.gather(
        get_embedding_async(target_prompt),
        get_embedding_async(user_response)
    )
    
    a = np.array(vec_a)
    b = np.array(vec_b)
    
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    return float(dot_product / (norm_a * norm_b))