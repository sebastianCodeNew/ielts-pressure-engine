import re
import asyncio
from langchain_core.messages import SystemMessage

from app.core.config import settings
from app.core.llm import get_llm
from app.core.logger import logger

# Reuse the same cheap/fast model but centralized
llm = get_llm(model_name=settings.TRANSLATOR_MODEL, temperature=0.0, timeout=60)

# Global semaphore to limit concurrent translation requests to prevent rate limiting/timeouts
# (v16.0 - Resiliency Hardening)
translation_semaphore = asyncio.Semaphore(5)

from app.core.cache import get_cached_translation, save_translation_to_cache


async def translate_to_indonesian_async(text: str) -> str:
    """
    Translates English text to Indonesian using the designated LLM (Async).
    Now with Graceful Passthrough if the API is unreachable.
    """
    if not text or not text.strip():
        return ""

    from app.core.cache import get_cached_translation, save_translation_to_cache

    cached = get_cached_translation(text)
    if cached:
        return cached

    # RESILIENT WRAPPER: If AI fails, return original text instead of crashing everything
    async with translation_semaphore:
        try:
            prompt = f"Translate the following IELTS-related text to natural, conversational Indonesian. Output ONLY the translation: {text}"
            response = await llm.ainvoke([SystemMessage(content=prompt)])
            translated = response.content.strip().replace('"', "")

            # Update cache
            save_translation_to_cache(text, translated)
            return translated
        except Exception as e:
            logger.error(
                f"Translation failure for '{text[:20]}...': {e}. Returning original."
            )
            return text


async def batch_translate_to_indonesian_async(texts: list[str]) -> list[str]:
    """
    Translates multiple English segments to Indonesian using chunking for stability.
    (v16.0 - Resiliency Hardening)
    """
    if not texts:
        return []

    # Filter out empty strings but keep indices for reconstruction
    # v24.1: ENHANCED CACHING - Avoid translating what we already know
    results = ["" for _ in texts]
    pending_items = []
    
    for i, t in enumerate(texts):
        if not t or not t.strip():
            continue
            
        cached = get_cached_translation(t)
        if cached:
            results[i] = cached
        else:
            pending_items.append((i, t))

    if not pending_items:
        return results

    # Chunk items to prevent prompt overflow/hallucination on large batches
    CHUNK_SIZE = 10
    chunks = [
        pending_items[i : i + CHUNK_SIZE] for i in range(0, len(pending_items), CHUNK_SIZE)
    ]

    for chunk in chunks:
        joined = "\n---\n".join([f"ID_{i}: {t}" for i, t in chunk])
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

        try:
            async with translation_semaphore:
                response = await llm.ainvoke([SystemMessage(content=prompt)])
                lines = response.content.strip().splitlines()
                for line in lines:
                    match = re.search(r"ID_(\d+)[:\-]\s*(.*)", line)
                    if match:
                        idx = int(match.group(1))
                        content = match.group(2).strip().replace('"', "")
                        results[idx] = content
                        
                        # v24.1: Persist success to cache
                        original_text = texts[idx]
                        save_translation_to_cache(original_text, content)
        except Exception as e:
            logger.error(f"Batch Chunk Translation Error: {e}", exc_info=True)
            # Fallback to single calls for THIS chunk
            for i, t in chunk:
                if not results[i]:
                    results[i] = await translate_to_indonesian_async(t)

    return results


async def translate_checkpoint_words_async(
    words: list[str],
) -> tuple[list[str], list[str]]:
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
            # Resilient split against || or | separators
            parts = re.split(r"\|\||\|", ln)
            if len(parts) < 3:
                continue
            en = parts[0].strip(' "-')
            tr = parts[1].strip(' "-')
            mn = parts[2].strip(' "-')
            if en:
                translated_val = tr or "-"
                meaning_val = mn or "-"
                parsed[en.lower()] = (translated_val, meaning_val)
                # v24.1: Save word translation to cache for future single-lookup hits
                save_translation_to_cache(en, translated_val)

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
        logger.error(f"Checkpoint translation error (Async): {e}", exc_info=True)
        tasks = [translate_to_indonesian_async(w) for w in words]
        translations = await asyncio.gather(*tasks)
        meanings = ["Makna sederhana tidak tersedia." for _ in words]
        return translations, meanings
