"""
Error Taxonomy for Micro-Skill Tagging
Classifies specific grammar and speaking errors for targeted learning.
"""
from enum import Enum
from typing import List, Optional
import re

class ErrorType(str, Enum):
    # Grammar Errors
    SUBJECT_VERB_AGREEMENT = "Subject-Verb Agreement"
    ARTICLE_USAGE = "Article Usage"
    TENSE_CONSISTENCY = "Tense Consistency"
    PRONOUN_REFERENCE = "Pronoun Reference"
    CONDITIONAL_STRUCTURE = "Conditional Structure"
    PASSIVE_VOICE = "Passive Voice Errors"
    PREPOSITION_USAGE = "Preposition Usage"
    
    # Fluency Errors
    FILLER_WORDS = "Filler Words (um, uh)"
    HESITATION = "Hesitation/Long Pauses"
    REPETITION = "Word Repetition"
    SELF_CORRECTION = "Excessive Self-Correction"
    
    # Coherence Errors
    MISSING_CONNECTORS = "Missing Connectors"
    WEAK_STRUCTURE = "Weak Answer Structure"
    TOPIC_DRIFT = "Topic Drift"
    
    # Lexical Errors
    WORD_CHOICE = "Inappropriate Word Choice"
    COLLOCATION = "Collocation Errors"
    VOCABULARY_RANGE = "Limited Vocabulary Range"

# Pattern matching rules for classification
ERROR_PATTERNS = {
    ErrorType.SUBJECT_VERB_AGREEMENT: [
        r"subject.{0,20}verb.{0,10}agree",
        r"singular.{0,10}plural",
        r"\bhe do\b|\bshe do\b|\bit do\b",
        r"\bthey does\b|\bhe have\b|\bshe have\b"
    ],
    ErrorType.ARTICLE_USAGE: [
        r"article",
        r"missing.{0,10}(a|an|the)",
        r"incorrect.{0,10}(a|an|the)",
        r"definite|indefinite"
    ],
    ErrorType.TENSE_CONSISTENCY: [
        r"tense",
        r"past.{0,10}present",
        r"present.{0,10}past",
        r"verb.{0,10}form"
    ],
    ErrorType.CONDITIONAL_STRUCTURE: [
        r"conditional",
        r"if.{0,10}would",
        r"hypothetical"
    ],
    ErrorType.FILLER_WORDS: [
        r"filler",
        r"\bum\b|\buh\b|\ber\b",
        r"you know|like|basically"
    ],
    ErrorType.HESITATION: [
        r"hesitat",
        r"pause",
        r"silence",
        r"fluency"
    ],
    ErrorType.MISSING_CONNECTORS: [
        r"connector",
        r"linking.{0,10}word",
        r"cohesion",
        r"however|moreover|nevertheless|furthermore"
    ],
    ErrorType.WORD_CHOICE: [
        r"word.{0,10}choice",
        r"vocabulary",
        r"lexical",
        r"inappropriate.{0,10}word"
    ],
    ErrorType.COLLOCATION: [
        r"collocation",
        r"doesn't.{0,10}collocate",
        r"natural.{0,10}pairing"
    ]
}

def classify_errors(feedback_text: str) -> List[ErrorType]:
    """
    Analyzes feedback text and returns classified error types.
    """
    if not feedback_text:
        return []
    
    detected = set()
    text_lower = feedback_text.lower()
    
    for error_type, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                detected.add(error_type)
                break
    
    return list(detected)

def get_error_display_name(error_type: ErrorType) -> str:
    """Returns human-readable name for error type."""
    return error_type.value
