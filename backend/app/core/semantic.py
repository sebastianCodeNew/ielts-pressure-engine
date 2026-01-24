import os
import httpx
import numpy as np
from typing import List

# Load API Key from environment
DEEPINFRA_KEY = os.getenv("DEEPINFRA_API_KEY")
BASE_URL = "https://api.deepinfra.com/v1/openai"

def get_embedding(text: str) -> List[float]:
    """
    Sends text to DeepInfra and returns a vector (list of floats).
    """
    # Safety: If text is empty/None, return a zero-vector
    if not text or not isinstance(text, str):
        return [0.0] * 768  # Gemma-300m uses 768 dimensions
        
    if not DEEPINFRA_KEY:
        print("WARNING: DEEPINFRA_API_KEY is missing. Returning zero vector.")
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
        # We use a context manager to ensure connection closes
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{BASE_URL}/embeddings", json=payload, headers=headers)
            
            if response.status_code != 200:
                print(f"Embedding API Error: {response.text}")
                return [0.0] * 768

            data = response.json()
            # Extract the vector from the OpenAI-compatible response format
            return data["data"][0]["embedding"]
            
    except Exception as e:
        print(f"Embedding Network Error: {e}")
        return [0.0] * 768

def calculate_coherence(target_prompt: str, user_response: str) -> float:
    """
    Math: Calculates the Cosine Similarity between two text vectors.
    """
    # 1. Get Vectors
    vec_a = get_embedding(target_prompt)
    vec_b = get_embedding(user_response)
    
    # 2. Convert to Numpy Arrays for fast math
    a = np.array(vec_a)
    b = np.array(vec_b)
    
    # 3. Calculate Dot Product and Norms (Magnitude)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    # 4. Avoid Division by Zero
    if norm_a == 0 or norm_b == 0:
        return 0.0
        
    # 5. Result
    return float(dot_product / (norm_a * norm_b))