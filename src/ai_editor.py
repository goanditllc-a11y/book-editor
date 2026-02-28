"""
src/ai_editor.py
Automatically rewrite text to reduce AI-generated content traces.

Applies deterministic phrase replacements, contraction expansion,
and light structural variation.  No external API calls are made.
"""

from __future__ import annotations

import re
import random
from typing import NamedTuple

# ---------------------------------------------------------------------------
# Replacement tables
# ---------------------------------------------------------------------------

class _Replacement(NamedTuple):
    pattern: str        # regex pattern (case-insensitive)
    choices: list[str]  # replacement candidates
    is_regex: bool = False


# Ordered list — more specific patterns first
PHRASE_REPLACEMENTS: list[_Replacement] = [
    # Explicit AI self-references → remove the sentence or soften
    _Replacement(r"as an ai[,.]?", [""], is_regex=True),
    _Replacement(r"as a language model[,.]?", [""], is_regex=True),
    _Replacement(r"i(?:'m| am) unable to\b", ["I won't"], is_regex=True),
    _Replacement(r"i cannot\b", ["I won't"], is_regex=True),
    _Replacement(r"i'd be happy to\b", ["I'll"], is_regex=True),
    _Replacement(r"i apologize\b", ["sorry"], is_regex=True),
    _Replacement(r"rest assured[,]?", ["don't worry,"], is_regex=True),
    # Transition phrases
    _Replacement("needless to say,", [""]),
    _Replacement("needless to say", [""]),
    _Replacement("it goes without saying,", [""]),
    _Replacement("it goes without saying", [""]),
    _Replacement("in conclusion,", ["finally,", "to wrap up,"]),
    _Replacement("in conclusion", ["finally", "to wrap up"]),
    _Replacement("in summary,", ["briefly,"]),
    _Replacement("in summary", ["briefly"]),
    _Replacement("to summarize,", ["in short,"]),
    _Replacement("to summarize", ["in short"]),
    _Replacement("furthermore,", ["also,", "and,"]),
    _Replacement("furthermore", ["also", "and"]),
    _Replacement("moreover,", ["besides that,", "also,"]),
    _Replacement("moreover", ["besides that", "also"]),
    _Replacement("it is worth noting that", ["notably"]),
    _Replacement("it's worth noting that", ["notably"]),
    _Replacement("it is worth noting", ["notably"]),
    _Replacement("it's worth noting", ["notably"]),
    _Replacement("it is important to note that", ["importantly"]),
    _Replacement("it is important to note", ["importantly"]),
    # Verbose / formal phrases
    _Replacement("in the realm of", ["in"]),
    _Replacement("in terms of", ["for"]),
    _Replacement("a testament to", ["proof of"]),
    _Replacement("not only.*?but also", ["and also"], is_regex=True),
    _Replacement("let's dive into", ["here's"]),
    _Replacement("let's dive", ["let's look"]),
    _Replacement("delve into", ["dig into"]),
    _Replacement("delve", ["explore"]),
    _Replacement("harnessing", ["using"]),
    _Replacement("harness", ["use"]),
    _Replacement("straightforward", ["simple"]),
    _Replacement("commendable", ["impressive"]),
    _Replacement("certainly,", ["sure,"]),
    _Replacement("certainly", ["sure"]),
    _Replacement("utilize", ["use"]),
    _Replacement("utilise", ["use"]),
    _Replacement("facilitate", ["help"]),
    _Replacement("leverage", ["use"]),
    _Replacement("robust", ["solid"]),
    _Replacement("comprehensive", ["thorough"]),
    _Replacement("innovative", ["new"]),
    _Replacement("cutting-edge", ["modern"]),
    _Replacement("state-of-the-art", ["modern"]),
    _Replacement("crucial", ["key"]),
    _Replacement("synergy", ["cooperation"]),
    _Replacement("paradigm", ["model"]),
]

# Contraction expansion  (it is → it's, etc.)
CONTRACTIONS: list[tuple[str, str]] = [
    (r"\bit is\b", "it's"),
    (r"\bthey are\b", "they're"),
    (r"\bwe are\b", "we're"),
    (r"\byou are\b", "you're"),
    (r"\bhe is\b", "he's"),
    (r"\bshe is\b", "she's"),
    (r"\bthat is\b", "that's"),
    (r"\bthere is\b", "there's"),
    (r"\bwhat is\b", "what's"),
    (r"\bwho is\b", "who's"),
    (r"\bdoes not\b", "doesn't"),
    (r"\bdo not\b", "don't"),
    (r"\bdid not\b", "didn't"),
    (r"\bcannot\b", "can't"),
    (r"\bwill not\b", "won't"),
    (r"\bwould not\b", "wouldn't"),
    (r"\bcould not\b", "couldn't"),
    (r"\bshould not\b", "shouldn't"),
    (r"\bI am\b", "I'm"),
    (r"\bI have\b", "I've"),
    (r"\bI will\b", "I'll"),
    (r"\bI would\b", "I'd"),
]

# How many consecutive "The …" sentences must appear before we try to vary them
THE_RUN_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _apply_phrase_replacements(text: str) -> tuple[str, list[str]]:
    """Apply all PHRASE_REPLACEMENTS and return (new_text, changes)."""
    changes: list[str] = []

    for rep in PHRASE_REPLACEMENTS:
        choice = random.choice(rep.choices)  # noqa: S311
        flags = re.IGNORECASE

        if rep.is_regex:
            compiled = re.compile(rep.pattern, flags | re.DOTALL)
            def _sub(m: re.Match, repl: str = choice, rep_pat: str = rep.pattern) -> str:  # noqa: ANN001
                changes.append(f"'{m.group(0).strip()}' → '{repl}'")
                return repl
            new_text = compiled.sub(_sub, text)
        else:
            pattern_lower = rep.pattern.lower()
            compiled = re.compile(re.escape(rep.pattern), flags)
            def _sub(m: re.Match, repl: str = choice, orig: str = rep.pattern) -> str:  # noqa: ANN001
                changes.append(f"'{orig}' → '{repl}'")
                return repl
            new_text = compiled.sub(_sub, text)

        text = new_text

    return text, changes


def _apply_contractions(text: str, rate: float = 0.6) -> tuple[str, int]:
    """
    Replace formal phrases with contractions at the given *rate* (0–1).
    Returns (new_text, replacement_count).
    """
    count = 0
    for pattern, contraction in CONTRACTIONS:
        compiled = re.compile(pattern)

        def _sub(m: re.Match, c: str = contraction) -> str:  # noqa: ANN001
            nonlocal count
            if random.random() < rate:  # noqa: S311
                count += 1
                # Preserve leading capitalisation
                if m.group(0)[0].isupper():
                    return c[0].upper() + c[1:]
                return c
            return m.group(0)

        text = compiled.sub(_sub, text)
    return text, count


def _vary_the_sentences(text: str) -> tuple[str, int]:
    """
    If ≥ THE_RUN_THRESHOLD consecutive sentences start with "The ",
    move the subject to the start of some of them using passive inversion.
    This is a lightweight heuristic.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text)
    changes = 0
    run_start = None

    for i, s in enumerate(sentences):
        if re.match(r"^The\s+", s, re.IGNORECASE):
            if run_start is None:
                run_start = i
        else:
            if run_start is not None and (i - run_start) >= THE_RUN_THRESHOLD:
                # Flip a few in the middle of the run
                for j in range(run_start + 1, i - 1, 2):
                    m = re.match(r"^The\s+(\w+)\s+(\w+)\s+(.*)", sentences[j])
                    if m:
                        subj = m.group(1)
                        verb = m.group(2)
                        rest = m.group(3)
                        sentences[j] = f"{subj.capitalize()} {verb} the {rest}"
                        changes += 1
            run_start = None

    return " ".join(sentences), changes


def _clean_up(text: str) -> str:
    """Remove double spaces and fix spacing after punctuation."""
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\s+([,.:;!?])", r"\1", text)
    text = re.sub(r"([,.:;!?])(\w)", r"\1 \2", text)
    # Remove orphaned commas left by blank replacements
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s+,", ",", text)
    # Fix sentences that start with lowercase after a blank replacement
    text = re.sub(
        r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text
    )
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def edit(text: str, ai_score: float = 0.5) -> dict:
    """
    Edit *text* to reduce AI content traces.

    Parameters
    ----------
    text:
        The original text.
    ai_score:
        The detected AI score (0–1).  Used to decide how aggressively to
        apply contractions.

    Returns
    -------
    dict with keys:
        edited_text, changes_made, changes_list, new_ai_score
    """
    if not text or not text.strip():
        return {
            "edited_text": text,
            "changes_made": 0,
            "changes_list": [],
            "new_ai_score": 0.0,
        }

    all_changes: list[str] = []

    # 1. Phrase replacements
    text, phrase_changes = _apply_phrase_replacements(text)
    all_changes.extend(phrase_changes)

    # 2. Contractions — more aggressive for high AI scores
    contraction_rate = min(0.9, 0.4 + ai_score * 0.6)
    text, n_contractions = _apply_contractions(text, rate=contraction_rate)
    if n_contractions:
        all_changes.append(f"Applied {n_contractions} natural contractions")

    # 3. Sentence variation for "The …" runs
    text, n_varied = _vary_the_sentences(text)
    if n_varied:
        all_changes.append(f"Varied {n_varied} sentence openings")

    # 4. Final cleanup
    text = _clean_up(text)

    # Estimate new AI score (heuristic: each edit reduces score slightly)
    reduction = min(0.35, len(phrase_changes) * 0.01 + n_contractions * 0.002)
    new_ai_score = max(0.0, round(ai_score - reduction, 4))

    return {
        "edited_text": text,
        "changes_made": len(all_changes),
        "changes_list": all_changes[:50],  # cap for display
        "new_ai_score": new_ai_score,
    }
