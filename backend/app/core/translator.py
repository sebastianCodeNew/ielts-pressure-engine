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
    timeout=60,
)

async def translate_to_indonesian_async(text_en: str) -> str:
    """
    Translates English text to natural spoken Indonesian (Async).
    """
    if not text_en:
        return ""
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
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        return response.content.strip().replace('"', '')
    except Exception as e:
        print(f"Translation Error (Async EN->ID): {e}")
        return "Gagal memuat terjemahan."

async def batch_translate_to_indonesian_async(texts: list[str]) -> list[str]:
    """
    Translates multiple English segments to Indonesian in a single LLM call.
    """
    if not texts:
        return []

    # Filter out empty strings but keep indices for reconstruction
    valid_items = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
    if not valid_items:
        return ["" for _ in texts]

    joined = "\n---\n".join([f"ID_{i}: {t}" for i, t in valid_items])
    prompt = f"""
    Task: Translate the following English segments to Indonesian.
    Style: Natural, Professional.
    
    Segments:
    {joined}

    Rules:
    - Maintain the ID prefix (e.g., ID_0: [Terjemahan])
    - Output ONLY the IDs and their translations.
    - One segment per line.
    """

    results = ["" for _ in texts]
    try:
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        lines = response.content.strip().splitlines()
        
        parsed = {}
        for line in lines:
            if ": " in line:
                id_part, content = line.split(": ", 1)
                idx = int(id_part.replace("ID_", ""))
                parsed[idx] = content.strip().replace('"', '')
        
        for i, _ in enumerate(texts):
            results[i] = parsed.get(i, "")
            
    except Exception as e:
        print(f"Batch Translation Error: {e}")
        # Final fallback: individual async calls
        import asyncio
        tasks = [translate_to_indonesian_async(t) for t in texts]
        results = await asyncio.gather(*tasks)

    return results

async def translate_checkpoint_words_async(words: list[str]) -> tuple[list[str], list[str]]:
    """Translates checkpoint words and returns (translations, short_meanings) (Async)."""
    if not words:
        return [], []

    joined = "\n".join([f"- {w}" for w in words])
    prompt = f"""
    Task: For each English word below, provide:
    1) Indonesian translation
    2) Short Indonesian meaning/definition (very simple)

    Words:\n{joined}

    Output rules:
    - Output EXACTLY one line per input word.
    - Format per line: ENGLISH || INDONESIAN_TRANSLATION || INDONESIAN_MEANING
    - No numbering.
    - No extra lines.
    """

    translations: list[str] = []
    meanings: list[str] = []

    try:
        response = await llm.ainvoke([SystemMessage(content=prompt)])
        lines = [ln.strip() for ln in response.content.splitlines() if ln.strip()]

        parsed: dict[str, tuple[str, str]] = {}
        for ln in lines:
            parts = [p.strip() for p in ln.split("||")]
            if len(parts) < 3:
                continue
            en = parts[0].strip('"').strip()
            tr = parts[1].strip('"').strip()
            mn = parts[2].strip('"').strip()
            if en:
                parsed[en.lower()] = (tr or "-", mn or "-")

        for w in words:
            tr, mn = parsed.get(w.lower(), (None, None))
            if not tr:
                tr = await translate_to_indonesian_async(w)
            if not mn:
                mn = "Makna sederhana tidak tersedia."
            translations.append(tr)
            meanings.append(mn)

        return translations, meanings
    except Exception as e:
        print(f"Checkpoint translation error (Async): {e}")
        import asyncio
        tasks = [translate_to_indonesian_async(w) for w in words]
        translations = await asyncio.gather(*tasks)
        meanings = ["Makna sederhana tidak tersedia." for _ in words]
        return translations, meanings