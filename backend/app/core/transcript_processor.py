import re

# whisper hallucination blacklist (v13.0)
HALLUCINATION_BLACKLIST = {
    "thanks for watching", "thank you for watching", "please subscribe", 
    "watching!", "thank you.", "thanks for watching.", "...", "subtitles by",
    "amara.org", "you", "th", "thank you very much"
}

def clean_hallucinations(text: str) -> str:
    """
    Strips common Whisper phantoms that occur during silence/noise.
    """
    clean_text = text.lower().strip().replace(".", "").replace("!", "")
    if clean_text in HALLUCINATION_BLACKLIST:
        return ""
    
    # Also catch cases where the hallucination is at the end of a very short string
    for phantom in HALLUCINATION_BLACKLIST:
        if len(text) < 50 and phantom in text.lower():
            # If the response is short and contains a known phantom, it's likely noise
            return ""
            
    return text

def apply_heuristic_punctuation(text: str) -> str:
    """
    Adds periods to transcripts that lack punctuation. 
    Prevents linguistic analyzers from reporting "1 sentence" for long speech.
    """
    if not text:
        return ""
        
    text = text.strip()
    
    # 1. Check if already punctuated
    if any(p in text for p in [".", "?", "!"]):
        return text
        
    # 2. Heuristic: Split into "sentences" every ~12 words 
    # if it's long and unpunctuated.
    words = text.split()
    if len(words) < 15:
        # Too short to reliably segment, just add one at the end
        return text + "." if not text.endswith(".") else text
        
    processed_words = []
    for i, word in enumerate(words):
        processed_words.append(word)
        # Every 12-18 words, look for a logical break (v12.0 heuristic)
        if (i + 1) % 15 == 0 and i < len(words) - 3:
            processed_words[-1] = word + "."
            
    text = " ".join(processed_words)
    if not text.endswith("."):
        text += "."
        
    # 3. Capitalize sentences
    sentences = text.split(". ")
    text = ". ".join(s[0].upper() + s[1:] if s else s for s in sentences)
    
    # 4. Standardize space
    text = " ".join(text.split())
    
    return text

def deduplicate_repetitions(text: str) -> str:
    """
    Collapses consecutive repeated words caused by Whisper loops.
    E.g., "I like like like like dogs" -> "I like dogs"
    """
    if not text:
        return ""
    
    words = text.split()
    if len(words) < 3:
        return text
    
    cleaned = [words[0]]
    repeat_count = 1
    
    for i in range(1, len(words)):
        if words[i].lower() == words[i - 1].lower():
            repeat_count += 1
            # Allow up to 2 consecutive identical words (natural emphasis)
            # but collapse 3+ (Whisper stutter)
            if repeat_count <= 2:
                cleaned.append(words[i])
        else:
            repeat_count = 1
            cleaned.append(words[i])
    
    return " ".join(cleaned)

def post_process_transcript(text: str) -> str:
    """
    Full pipeline to clean and fix transcripts.
    """
    if not text:
        return ""
    
    # 1. Hallucination Guard
    text = clean_hallucinations(text)
    if not text:
        return ""

    # 2. Repetition Loop Filter (v14.0)
    text = deduplicate_repetitions(text)

    # 3. Heuristic Punctuation
    text = apply_heuristic_punctuation(text)
    
    return text

