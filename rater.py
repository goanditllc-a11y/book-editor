"""
Book Rating Engine

Rates uploaded literary works on multiple dimensions (each 0-100):
  - Readability  : Flesch Reading Ease (via textstat, with fallback)
  - Originality  : vocabulary diversity + cliché density
  - Quality      : grammar-proxy + structural analysis
  - Overall      : weighted average
"""

import re
import math
from collections import Counter

# Try to import textstat for readability; fall back to manual calculation
try:
    import textstat
    HAS_TEXTSTAT = True
except ImportError:
    HAS_TEXTSTAT = False


# Common clichés to detect
CLICHE_PATTERNS = [
    r"\bat the end of the day\b",
    r"\bthink outside the box\b",
    r"\blow-hanging fruit\b",
    r"\bmove the needle\b",
    r"\bgame changer\b",
    r"\bsynergy\b",
    r"\bnew normal\b",
    r"\bunprecedented\b",
    r"\bleverage\b",
    r"\bcircle back\b",
    r"\bdeep dive\b",
    r"\bpivot\b",
    r"\bvalue-add\b",
    r"\bbest practices\b",
    r"\bholistic approach\b",
    r"\bsea change\b",
    r"\bparadigm shift\b",
    r"\bwhen all is said and done\b",
    r"\btime will tell\b",
    r"\bwhen life gives you lemons\b",
]
CLICHE_COMPILED = [re.compile(p, re.IGNORECASE) for p in CLICHE_PATTERNS]


def _count_syllables(word):
    """Count syllables in a word (simple heuristic)."""
    word = word.lower().strip(".,;:!?\"'")
    if len(word) <= 3:
        return 1
    word = re.sub(r'(?:[^aeiou])es$', '', word)
    word = re.sub(r'(?:[^aeiou])ed$', '', word)
    word = re.sub(r'e$', '', word)
    syllables = len(re.findall(r'[aeiou]+', word))
    return max(1, syllables)


def _flesch_reading_ease(text):
    """Calculate Flesch Reading Ease score (0-100)."""
    if HAS_TEXTSTAT:
        try:
            score = textstat.flesch_reading_ease(text)
            # Clamp to 0-100
            return round(max(0.0, min(100.0, score)), 2)
        except Exception:
            pass

    # Manual fallback
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r"\b[a-zA-Z']+\b", text)

    if not sentences or not words:
        return 50.0

    avg_sentence_length = len(words) / len(sentences)
    avg_syllables = sum(_count_syllables(w) for w in words) / len(words)

    score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables
    return round(max(0.0, min(100.0, score)), 2)


def _vocabulary_diversity(text):
    """
    Type-token ratio normalised to 0-100.
    Higher = more diverse = more original.
    """
    words = re.findall(r"[a-z']+", text.lower())
    if len(words) < 20:
        return 50.0
    ttr = len(set(words)) / len(words)
    # Map TTR [0, 1] → [0, 100]; a TTR of 0.5 is considered average
    score = ttr * 100
    return round(min(100.0, score), 2)


def _cliche_density(text):
    """
    Return penalty score based on cliché density.
    0 = no clichés; 100 = extremely cliché.
    """
    words = re.findall(r"\b\w+\b", text)
    word_count = max(len(words), 1)
    hits = sum(1 for p in CLICHE_COMPILED if p.search(text))
    density = (hits / word_count) * 1000
    return round(min(100.0, density * 10), 2)


def _originality_score(text):
    """Combine vocabulary diversity and cliché penalty."""
    diversity = _vocabulary_diversity(text)
    cliche_penalty = _cliche_density(text)
    score = diversity - cliche_penalty * 0.5
    return round(max(0.0, min(100.0, score)), 2)


def _average_sentence_length(text):
    """Average words per sentence."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r"\b\w+\b", text)
    if not sentences:
        return 0
    return len(words) / len(sentences)


def _quality_score(text):
    """
    Proxy for quality:
      - Penalise very long average sentence length (>40 words)
      - Reward moderate sentence length (15-25 words)
      - Check for paragraph structure
    """
    avg_len = _average_sentence_length(text)

    # Ideal sentence length ~15-25 words
    if 15 <= avg_len <= 25:
        length_score = 100.0
    elif avg_len < 15:
        length_score = 60.0 + avg_len * 2.67
    else:
        penalty = (avg_len - 25) * 2
        length_score = max(0.0, 100.0 - penalty)

    # Paragraph structure: reward multiple paragraphs
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    para_score = min(100.0, len(paragraphs) * 10) if paragraphs else 50.0

    score = length_score * 0.7 + para_score * 0.3
    return round(max(0.0, min(100.0, score)), 2)


def rate_book(full_text):
    """
    Rate the given text.
    Returns a dict with readability, originality, quality, and overall scores.
    """
    if not full_text or not full_text.strip():
        return {
            'readability': 0.0,
            'originality': 0.0,
            'quality': 0.0,
            'overall': 0.0,
        }

    readability = _flesch_reading_ease(full_text)
    originality = _originality_score(full_text)
    quality = _quality_score(full_text)

    # Weighted overall
    overall = (
        readability * 0.35
        + originality * 0.35
        + quality * 0.30
    )
    overall = round(max(0.0, min(100.0, overall)), 2)

    return {
        'readability': readability,
        'originality': originality,
        'quality': quality,
        'overall': overall,
    }
