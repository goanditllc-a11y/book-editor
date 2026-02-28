"""
src/ai_detector.py
Local AI-content detection engine — no external API calls.

Analyses six orthogonal signals and combines them into a single ai_score
in the range [0.0, 1.0] (0 = human-written, 1 = AI-generated).
"""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter

# ---------------------------------------------------------------------------
# AI phrase list
# ---------------------------------------------------------------------------

AI_PHRASES: list[str] = [
    "it is worth noting",
    "it's worth noting",
    "in conclusion",
    "furthermore",
    "moreover",
    "in summary",
    "to summarize",
    "needless to say",
    "it is important to note",
    "as an ai",
    "i cannot",
    "i'm unable to",
    "as a language model",
    "delve",
    "it goes without saying",
    "let's dive",
    "straightforward",
    "commendable",
    "in the realm of",
    "harnessing",
    "not only",
    "a testament to",
    "in terms of",
    "rest assured",
    "i'd be happy to",
    "certainly",
    "i apologize",
    "I apologize",
    "crucial",
    "utilize",
    "leverage",
    "synergy",
    "paradigm",
    "robust",
    "comprehensive",
    "facilitate",
    "innovative",
    "cutting-edge",
    "state-of-the-art",
]

FILLER_WORDS: list[str] = [
    "very",
    "really",
    "quite",
    "rather",
    "essentially",
    "basically",
    "actually",
    "literally",
    "simply",
    "just",
]

# Component weights (must sum to 1.0)
WEIGHTS: dict[str, float] = {
    "phrase_patterns": 0.30,
    "sentence_uniformity": 0.20,
    "vocabulary_diversity": 0.15,
    "burstiness": 0.15,
    "paragraph_uniformity": 0.10,
    "filler_density": 0.10,
}


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

def _sentences(text: str) -> list[str]:
    """Simple sentence splitter (handles .!?)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in parts if s.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"\b[a-zA-Z']+\b", text.lower())


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


# ---------------------------------------------------------------------------
# Individual scoring functions
# ---------------------------------------------------------------------------

def _score_phrase_patterns(text: str, total_words: int) -> tuple[float, list[str]]:
    """Count AI phrases per 1000 words → 0-1 score."""
    lower = text.lower()
    found: list[str] = []
    count = 0
    for phrase in AI_PHRASES:
        occurrences = lower.count(phrase.lower())
        if occurrences:
            found.append(phrase)
            count += occurrences

    if total_words == 0:
        return 0.0, found

    per_1000 = (count / total_words) * 1000
    # Saturates at ~10 occurrences per 1000 words → score = 1.0
    score = min(per_1000 / 10.0, 1.0)
    return score, found


def _score_sentence_uniformity(text: str) -> float:
    """Low std-dev of sentence lengths → more AI-like → higher score."""
    sents = _sentences(text)
    if len(sents) < 5:
        return 0.5  # Not enough data

    lengths = [len(_words(s)) for s in sents if _words(s)]
    if len(lengths) < 5:
        return 0.5

    try:
        std = statistics.stdev(lengths)
        mean = statistics.mean(lengths)
    except statistics.StatisticsError:
        return 0.5

    if mean == 0:
        return 0.5

    # Coefficient of variation; lower CV → more uniform → more AI
    cv = std / mean
    # Natural prose CV typically 0.4–0.8; AI is often <0.35
    score = max(0.0, min(1.0, 1.0 - (cv / 0.6)))
    return score


def _score_vocabulary_diversity(words: list[str]) -> float:
    """Low TTR → repetitive → AI-like (for long texts)."""
    if len(words) < 50:
        return 0.3

    # Use moving-window TTR (200-word window) for long texts
    window = 200
    ttrs: list[float] = []
    for i in range(0, len(words) - window, window // 2):
        chunk = words[i : i + window]
        ttrs.append(len(set(chunk)) / len(chunk))

    if not ttrs:
        ttr = len(set(words)) / len(words)
    else:
        ttr = statistics.mean(ttrs)

    # Natural prose TTR ~0.55–0.75; AI can be slightly lower for long texts
    # Lower TTR → more AI
    score = max(0.0, min(1.0, (0.65 - ttr) / 0.20 + 0.3))
    return score


def _score_burstiness(words: list[str]) -> float:
    """
    Natural text has bursty word usage (a word appears several times in one
    section, then disappears).  AI text tends to spread words more evenly.
    Lower coefficient of variation of content-word frequencies → more AI.
    """
    if len(words) < 100:
        return 0.3

    # Filter out very common stop words
    stops = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "is", "was", "are", "were", "be", "been",
        "has", "have", "had", "it", "its", "this", "that", "as", "by",
        "from", "not", "no", "so", "if", "do", "did", "he", "she",
        "they", "we", "you", "i", "my", "his", "her", "our", "your",
    }
    content = [w for w in words if w not in stops and len(w) > 3]
    if len(content) < 50:
        return 0.3

    freq = Counter(content)
    counts = list(freq.values())
    if len(counts) < 5:
        return 0.3

    try:
        mean = statistics.mean(counts)
        std = statistics.stdev(counts)
    except statistics.StatisticsError:
        return 0.3

    if mean == 0:
        return 0.3

    cv = std / mean
    # High cv → bursty → human; low cv → uniform → AI
    score = max(0.0, min(1.0, 1.0 - (cv / 2.0)))
    return score


def _score_paragraph_uniformity(text: str) -> float:
    """AI tends to produce paragraphs of similar length."""
    paras = _paragraphs(text)
    if len(paras) < 4:
        return 0.3

    lengths = [len(_words(p)) for p in paras if _words(p)]
    if len(lengths) < 4:
        return 0.3

    try:
        std = statistics.stdev(lengths)
        mean = statistics.mean(lengths)
    except statistics.StatisticsError:
        return 0.3

    if mean == 0:
        return 0.3

    cv = std / mean
    score = max(0.0, min(1.0, 1.0 - (cv / 0.8)))
    return score


def _score_filler_density(words: list[str], total_words: int) -> float:
    """High filler-word density is a weak AI signal."""
    if total_words == 0:
        return 0.0
    count = sum(1 for w in words if w in FILLER_WORDS)
    density = count / total_words
    # Saturates at 5% filler density
    return min(density / 0.05, 1.0)


# ---------------------------------------------------------------------------
# AI-likely sentence extraction
# ---------------------------------------------------------------------------

def _flagged_sentences(text: str, max_sentences: int = 10) -> list[str]:
    """Return sentences that contain at least one AI phrase."""
    lower = text.lower()
    sents = _sentences(text)
    result: list[str] = []
    for s in sents:
        sl = s.lower()
        if any(ph in sl for ph in AI_PHRASES):
            result.append(s.strip())
        if len(result) >= max_sentences:
            break
    return result


# ---------------------------------------------------------------------------
# Chunked processing
# ---------------------------------------------------------------------------

CHUNK_WORDS = 5000


def _analyse_chunk(chunk: str) -> dict:
    words = _words(chunk)
    total = len(words)

    phrase_score, found_phrases = _score_phrase_patterns(chunk, total)
    sent_score = _score_sentence_uniformity(chunk)
    vocab_score = _score_vocabulary_diversity(words)
    burst_score = _score_burstiness(words)
    para_score = _score_paragraph_uniformity(chunk)
    filler_score = _score_filler_density(words, total)

    components = {
        "phrase_patterns": round(phrase_score, 4),
        "sentence_uniformity": round(sent_score, 4),
        "vocabulary_diversity": round(vocab_score, 4),
        "burstiness": round(burst_score, 4),
        "paragraph_uniformity": round(para_score, 4),
        "filler_density": round(filler_score, 4),
    }

    ai_score = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)

    return {
        "ai_score": ai_score,
        "components": components,
        "found_phrases": found_phrases,
    }


def _split_into_chunks(text: str, chunk_words: int = CHUNK_WORDS) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    for i in range(0, len(words), chunk_words):
        chunks.append(" ".join(words[i : i + chunk_words]))
    return chunks or [text]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect(text: str) -> dict:
    """
    Analyse *text* for AI-generated content.

    Returns a dict with keys:
        ai_score, ai_percentage, confidence, components,
        flagged_phrases, ai_sentences
    """
    if not text or not text.strip():
        return {
            "ai_score": 0.0,
            "ai_percentage": 0,
            "confidence": "low",
            "components": {k: 0.0 for k in WEIGHTS},
            "flagged_phrases": [],
            "ai_sentences": [],
        }

    chunks = _split_into_chunks(text)
    chunk_results = [_analyse_chunk(c) for c in chunks]

    # Average scores across chunks
    avg_ai = statistics.mean(r["ai_score"] for r in chunk_results)
    avg_components: dict[str, float] = {}
    for key in WEIGHTS:
        avg_components[key] = round(
            statistics.mean(r["components"][key] for r in chunk_results), 4
        )

    # Collect unique flagged phrases
    all_phrases: set[str] = set()
    for r in chunk_results:
        all_phrases.update(r["found_phrases"])

    ai_score = round(avg_ai, 4)
    ai_percentage = round(ai_score * 100)

    # Confidence based on text length
    total_words = len(text.split())
    if total_words < 200:
        confidence = "low"
    elif total_words < 1000:
        confidence = "medium"
    else:
        confidence = "high"

    return {
        "ai_score": ai_score,
        "ai_percentage": ai_percentage,
        "confidence": confidence,
        "components": avg_components,
        "flagged_phrases": sorted(all_phrases),
        "ai_sentences": _flagged_sentences(text),
    }
