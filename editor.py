"""
AI Content Editor / Rewriter Module

Rewrites text that has been flagged as likely AI-generated so that it
sounds more natural and human.  All processing is local — no external API.

Techniques:
  - Replace common AI stock phrases with natural alternatives
  - Vary sentence structure by splitting/merging sentences
  - Introduce contractions
  - Vary transition words
  - Randomise paragraph lengths slightly
"""

import re
import random

# ---------------------------------------------------------------------------
# Phrase replacement map  (AI phrase → human alternatives)
# ---------------------------------------------------------------------------
PHRASE_REPLACEMENTS = {
    r"\bin conclusion\b": ["to wrap things up", "all in all", "when it's all said and done", "putting it all together"],
    r"\bto summarize\b": ["in short", "to put it briefly", "the gist is", "bottom line"],
    r"\bit is important to note(?: that)?\b": ["keep in mind that", "worth remembering:", "don't overlook the fact that", "note that"],
    r"\bit is worth noting(?: that)?\b": ["worth mentioning", "notably", "interestingly", "it turns out that"],
    r"\bit is essential to\b": ["you need to", "you've got to", "it really matters to", "one must"],
    r"\bit is crucial to\b": ["it really matters to", "you need to", "don't skip", "make sure to"],
    r"\bfurthermore\b": ["on top of that", "also", "what's more", "and", "besides that"],
    r"\bmoreover\b": ["also", "and", "beyond that", "plus", "not only that"],
    r"\badditionally\b": ["also", "and", "on top of that", "as well"],
    r"\bin summary\b": ["in short", "to put it simply", "all told", "the upshot is"],
    r"\boverall\b": ["all in all", "on the whole", "taken together", "by and large"],
    r"\bultimately\b": ["in the end", "at the end of the day", "when all's said and done", "finally"],
    r"\bfostering\b": ["building", "nurturing", "growing", "encouraging"],
    r"\bseamlessly\b": ["smoothly", "effortlessly", "without a hitch", "easily"],
    r"\brobust\b": ["solid", "strong", "reliable", "sturdy"],
    r"\bdelve into\b": ["dig into", "explore", "look at", "examine"],
    r"\bembark on a journey\b": ["start out", "set off", "begin", "take a look"],
    r"\bin the realm of\b": ["in the world of", "when it comes to", "in"],
    r"\bnavigating the complexities\b": ["dealing with the tricky parts of", "working through", "making sense of"],
    r"\bnavigating the landscape\b": ["understanding the lay of the land in", "working through"],
    r"\btailored to\b": ["designed for", "built for", "made to suit", "customised for"],
    r"\bin today's world\b": ["these days", "nowadays", "today"],
    r"\bin today's society\b": ["these days", "in modern life", "today"],
    r"\bin today's digital age\b": ["these days", "in the digital world", "nowadays"],
    r"\bthe importance of\b": ["why", "how much", "the value of"],
    r"\bplays a crucial role\b": ["matters a great deal", "is key", "makes a real difference"],
    r"\bplays a vital role\b": ["is vital", "makes all the difference", "is essential"],
    r"\bplays an important role\b": ["is important", "matters", "plays a big part"],
    r"\bplays a key role\b": ["is key", "matters a lot", "has a big impact"],
    r"\bplays a significant role\b": ["is significant", "has a significant impact", "matters quite a bit"],
    r"\bin this essay\b": ["here", "in this piece", "throughout this"],
    r"\bin this article\b": ["here", "in this piece", "as we'll see"],
    r"\bin this paper\b": ["here", "in this piece", "throughout"],
    r"\bit's worth (mentioning|noting|pointing out)\b": ["worth saying", "I should mention", "as a side note"],
}

PHRASE_PATTERNS = {
    re.compile(k, re.IGNORECASE): v
    for k, v in PHRASE_REPLACEMENTS.items()
}

# Expansion of contractions  AI→human
CONTRACTION_EXPANSIONS = [
    (re.compile(r'\bdo not\b'), "don't"),
    (re.compile(r'\bcannot\b'), "can't"),
    (re.compile(r'\bwill not\b'), "won't"),
    (re.compile(r'\bshould not\b'), "shouldn't"),
    (re.compile(r'\bwould not\b'), "wouldn't"),
    (re.compile(r'\bcould not\b'), "couldn't"),
    (re.compile(r'\bdoes not\b'), "doesn't"),
    (re.compile(r'\bdid not\b'), "didn't"),
    (re.compile(r'\bis not\b'), "isn't"),
    (re.compile(r'\bare not\b'), "aren't"),
    (re.compile(r'\bwas not\b'), "wasn't"),
    (re.compile(r'\bwere not\b'), "weren't"),
    (re.compile(r'\bI am\b'), "I'm"),
    (re.compile(r'\bI will\b'), "I'll"),
    (re.compile(r'\bI have\b'), "I've"),
    (re.compile(r'\bthey are\b'), "they're"),
    (re.compile(r'\bwe are\b'), "we're"),
    (re.compile(r'\byou are\b'), "you're"),
    (re.compile(r'\bhe is\b'), "he's"),
    (re.compile(r'\bshe is\b'), "she's"),
    (re.compile(r'\bit is\b'), "it's"),
    (re.compile(r'\bthat is\b'), "that's"),
    (re.compile(r'\bthere is\b'), "there's"),
    (re.compile(r'\bwhat is\b'), "what's"),
]


def _replace_phrases(text):
    """Replace known AI phrases with natural alternatives."""
    for pattern, alternatives in PHRASE_PATTERNS.items():
        def _replacer(m, alts=alternatives):
            choice = random.choice(alts)
            # Preserve capitalisation
            matched = m.group(0)
            if matched and choice and matched[0].isupper():
                return choice[0].upper() + choice[1:]
            return choice
        text = pattern.sub(_replacer, text)
    return text


def _introduce_contractions(text):
    """Replace formal expansions with contractions (50% probability each)."""
    for pattern, contraction in CONTRACTION_EXPANSIONS:
        def _replacer(m, c=contraction):
            if random.random() < 0.5:
                return c
            return m.group(0)
        text = pattern.sub(_replacer, text)
    return text


def _vary_sentence_structure(text):
    """
    Occasionally break long sentences or merge short consecutive ones.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) < 2:
        return text

    result = []
    i = 0
    while i < len(sentences):
        s = sentences[i]
        word_count = len(s.split())

        # Merge two consecutive very short sentences (~30% chance)
        if (word_count <= 8 and i + 1 < len(sentences)
                and random.random() < 0.3):
            next_s = sentences[i + 1]
            # Join with a comma + "and" or "so"
            connector = random.choice(["and", "so", "but"])
            s = s.rstrip('.!?') + f", {connector} " + next_s[0].lower() + next_s[1:]
            i += 2
        # Split a very long sentence at a comma (~25% chance)
        elif word_count > 30 and ',' in s and random.random() < 0.25:
            parts = s.split(',', 1)
            if len(parts[0].split()) >= 5 and len(parts[1].split()) >= 5:
                result.append(parts[0].strip() + '.')
                s = parts[1].strip()
                s = s[0].upper() + s[1:] if s else s
            i += 1
        else:
            i += 1
        result.append(s)

    return ' '.join(result)


def _vary_transition_words(text):
    """Swap identical consecutive transition words for variety."""
    # Simple case: replace a second consecutive 'However' with alternatives
    replacements = {
        'However': ['That said', 'Still', 'Even so', 'Yet'],
        'Therefore': ['So', 'As a result', 'Thus', 'Consequently'],
        'Additionally': ['Also', 'On top of that', 'Plus'],
        'Furthermore': ['What\'s more', 'Beyond that', 'And'],
    }
    for word, alternatives in replacements.items():
        # Replace every occurrence after the first with a random alternative
        count = [0]

        def _replacer(m, w=word, alts=alternatives, c=count):
            c[0] += 1
            if c[0] > 1:
                return random.choice(alts)
            return m.group(0)

        text = re.sub(r'\b' + word + r'\b', _replacer, text)
    return text


def rewrite_chunk(text):
    """
    Rewrite a single text chunk to reduce AI-like characteristics.
    Returns the rewritten text.
    """
    if not text or not text.strip():
        return text

    # Apply transformations in sequence
    text = _replace_phrases(text)
    text = _introduce_contractions(text)
    text = _vary_sentence_structure(text)
    text = _vary_transition_words(text)

    return text


def edit_document(chunks, ai_results):
    """
    Edit chunks that were flagged as AI-generated.
    chunks: list of str
    ai_results: list of dicts from ai_detector.analyse_document
    Returns list of edited strings (unchanged chunks are returned as-is).
    """
    edited = []
    chunk_results = ai_results.get('chunk_results', [])
    for i, chunk in enumerate(chunks):
        if i < len(chunk_results) and chunk_results[i].get('is_ai_flagged'):
            edited.append(rewrite_chunk(chunk))
        else:
            edited.append(chunk)
    return edited
