"""
src/rater.py
Multi-dimensional book rating engine.

Produces star ratings (1–5) for readability, originality and quality,
plus a weighted overall rating and a human-readable summary.
"""

from __future__ import annotations

import re
import statistics


# ---------------------------------------------------------------------------
# Readability helpers
# ---------------------------------------------------------------------------

def _flesch_reading_ease(text: str) -> float:
    """
    Flesch Reading Ease formula (0–100; higher = easier).
    We compute it manually so the module works without textstat as a fallback.
    """
    try:
        import textstat
        return float(textstat.flesch_reading_ease(text))
    except Exception:  # noqa: BLE001
        pass

    # Manual calculation
    words = re.findall(r"\b[a-zA-Z']+\b", text)
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]

    if not sentences or not words:
        return 50.0

    syllables = sum(_syllable_count(w) for w in words)
    avg_sentence_len = len(words) / len(sentences)
    avg_syllables_per_word = syllables / len(words) if words else 1

    score = 206.835 - 1.015 * avg_sentence_len - 84.6 * avg_syllables_per_word
    return max(0.0, min(100.0, score))


def _fk_grade(text: str) -> float:
    """Flesch-Kincaid Grade Level."""
    try:
        import textstat
        return float(textstat.flesch_kincaid_grade(text))
    except Exception:  # noqa: BLE001
        pass

    words = re.findall(r"\b[a-zA-Z']+\b", text)
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    if not sentences or not words:
        return 8.0
    syllables = sum(_syllable_count(w) for w in words)
    return 0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59


def _syllable_count(word: str) -> int:
    """Rough syllable counter."""
    word = word.lower().strip(".,;:!?")
    if not word:
        return 1
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _gunning_fog(text: str) -> float:
    """Gunning Fog Index."""
    try:
        import textstat
        return float(textstat.gunning_fog(text))
    except Exception:  # noqa: BLE001
        pass

    words = re.findall(r"\b[a-zA-Z']+\b", text)
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    if not sentences or not words:
        return 10.0
    complex_words = [w for w in words if _syllable_count(w) >= 3]
    return 0.4 * (len(words) / len(sentences) + 100 * len(complex_words) / len(words))


# ---------------------------------------------------------------------------
# Individual dimension scorers  (all return float in [1, 5])
# ---------------------------------------------------------------------------

def _readability_stars(text: str) -> tuple[float, dict]:
    """Rate readability using three metrics → 1–5 stars."""
    fre = _flesch_reading_ease(text)
    fkg = _fk_grade(text)
    fog = _gunning_fog(text)

    # FRE: 90–100 = very easy, 0–30 = very hard
    # Map to 1-5: 0→1, 100→5
    fre_stars = 1.0 + (fre / 100.0) * 4.0

    # FK Grade: grade 6 = ideal (5 stars), grade 16+ = hard (1 star)
    # Stars decrease as grade increases
    fkg_stars = max(1.0, min(5.0, 5.0 - (fkg - 6) * 0.4))

    # Fog: 8 = ideal, 18+ = very hard
    fog_stars = max(1.0, min(5.0, 5.0 - (fog - 8) * 0.3))

    combined = (fre_stars * 0.5 + fkg_stars * 0.3 + fog_stars * 0.2)
    combined = max(1.0, min(5.0, combined))

    return round(combined, 2), {
        "flesch_reading_ease": round(fre, 1),
        "fk_grade_level": round(fkg, 1),
        "gunning_fog": round(fog, 1),
    }


def _originality_stars(ai_score: float) -> float:
    """Convert ai_score (0=human, 1=AI) to 1–5 originality stars."""
    originality = 1.0 - ai_score
    # Map 0→1 star, 1→5 stars
    stars = 1.0 + originality * 4.0
    return round(max(1.0, min(5.0, stars)), 2)


def _quality_stars(text: str) -> float:
    """
    Simple quality score based on:
    - Sentence variety (std dev of lengths)
    - Average sentence length (15-20 words = sweet spot)
    - Paragraph structure
    """
    words = re.findall(r"\b[a-zA-Z']+\b", text)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    if not sentences:
        return 2.5

    sent_lengths = [len(re.findall(r"\b[a-zA-Z']+\b", s)) for s in sentences if s]
    sent_lengths = [l for l in sent_lengths if l > 0]

    if not sent_lengths:
        return 2.5

    avg_len = statistics.mean(sent_lengths)
    # Ideal average sentence length: 15-20 words
    len_score = max(0.0, 1.0 - abs(avg_len - 17.5) / 15.0)

    # Variety: higher std dev = more varied = better
    if len(sent_lengths) > 2:
        try:
            std = statistics.stdev(sent_lengths)
            variety_score = min(1.0, std / 12.0)
        except statistics.StatisticsError:
            variety_score = 0.5
    else:
        variety_score = 0.5

    # Paragraph structure: more paragraphs is generally better (up to 1 per ~100 words)
    word_count = len(words)
    ideal_para_count = max(1, word_count // 100)
    actual_para_count = len(paragraphs)
    para_score = min(1.0, actual_para_count / ideal_para_count) if ideal_para_count else 0.5

    quality = (len_score * 0.35 + variety_score * 0.40 + para_score * 0.25)
    stars = 1.0 + quality * 4.0
    return round(max(1.0, min(5.0, stars)), 2)


# ---------------------------------------------------------------------------
# Summary generator
# ---------------------------------------------------------------------------

def _generate_summary(
    readability: float,
    originality: float,
    quality: float,
    overall: float,
    ai_percentage: int,
) -> str:
    parts: list[str] = []

    if readability >= 4.0:
        parts.append("Excellent readability")
    elif readability >= 3.0:
        parts.append("Good readability")
    elif readability >= 2.0:
        parts.append("Moderate readability")
    else:
        parts.append("Difficult to read")

    if ai_percentage >= 70:
        parts.append(f"very high AI content detected ({ai_percentage}%)")
    elif ai_percentage >= 40:
        parts.append(f"moderate AI content detected ({ai_percentage}%)")
    elif ai_percentage >= 20:
        parts.append(f"some AI content detected ({ai_percentage}%)")
    else:
        parts.append(f"low AI content ({ai_percentage}%)")

    if quality >= 4.0:
        parts.append("strong writing quality")
    elif quality >= 3.0:
        parts.append("decent writing quality")
    else:
        parts.append("writing quality could be improved")

    summary = ", ".join(parts[:2]) + ". " + parts[2].capitalize() + "."

    if ai_percentage >= 40:
        summary += " Consider using the Auto-Edit feature to improve originality."

    return summary


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rate(text: str, ai_score: float) -> dict:
    """
    Compute a full rating for the given *text* and pre-computed *ai_score*.

    Returns
    -------
    dict with keys:
        readability_stars, originality_stars, quality_stars,
        overall_rating, readability_metrics, summary
    """
    if not text or not text.strip():
        return {
            "readability_stars": 1.0,
            "originality_stars": 1.0,
            "quality_stars": 1.0,
            "overall_rating": 1.0,
            "readability_metrics": {},
            "summary": "No text to analyse.",
        }

    readability_stars, metrics = _readability_stars(text)
    originality_stars = _originality_stars(ai_score)
    quality_stars = _quality_stars(text)

    overall = round(
        readability_stars * 0.30
        + originality_stars * 0.40
        + quality_stars * 0.30,
        2,
    )
    overall = max(1.0, min(5.0, overall))

    ai_pct = round(ai_score * 100)
    summary = _generate_summary(
        readability_stars, originality_stars, quality_stars, overall, ai_pct
    )

    return {
        "readability_stars": readability_stars,
        "originality_stars": originality_stars,
        "quality_stars": quality_stars,
        "overall_rating": overall,
        "readability_metrics": metrics,
        "summary": summary,
    }
