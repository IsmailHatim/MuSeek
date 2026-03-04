"""Tokenization, normalization, and puzzle building for MuSeek song lyrics."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import simplemma


@dataclass
class Token:
    type: Literal["word", "sep"]
    value: str
    normalized: str | None = None  # only set for word tokens


# Word regex: Unicode letters and hyphens; apostrophes are NOT included so
# contractions like l'amour split into two tokens: ["l", "amour"].
_WORD_RE = re.compile(r"[^\W\d_](?:[^\W\d_]|\-[^\W\d_])*", re.UNICODE)

# French elision prefix (l', d', j', …)
_ELISION_RE = re.compile(r"^(?:l|d|j|m|t|s|n|c|qu)'(.+)$", re.IGNORECASE | re.UNICODE)

# French contractions with wrong lemmas
_CONTRACTIONS: dict[str, str] = {
    "des": "de",
    "du": "de",
    "au": "a",
    "aux": "a",
}

# Elision prefixes produced by splitting on apostrophe (e.g. "d'" → "d", "l'" → "l").
# Maps the bare prefix back to its full form so that guessing "de" reveals "d'" tokens,
# guessing "je" reveals "j'" tokens, etc.
_ELISION_EXPAND: dict[str, str] = {
    "d":  "de",
    "l":  "le",
    "j":  "je",
    "m":  "me",
    "n":  "ne",
    "c":  "ce",
    "s":  "se",
    "t":  "te",
    "qu": "que",
}

# Structural lyrics markers to strip
_MARKER_RE = re.compile(
    r"\[.*?\]"          # [Couplet 1], [Refrain], [Chorus], etc.
    r"|\((?:x\d+|[A-Z][A-Z\s]*)\)",  # (x2), (OH OH), (YEAH)
    re.IGNORECASE,
)


def normalize(word: str) -> str:
    """Lowercase and strip combining accents for matching."""
    nfkd = unicodedata.normalize("NFKD", word.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def clean_lyrics(text: str) -> str:
    """Strip structural markers, normalize apostrophes, collapse blank lines."""
    # Normalize curly apostrophes to straight
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    # Strip structural markers
    text = _MARKER_RE.sub("", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip stray HTML entities
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    return text.strip()


def extract_excerpt(text: str, max_lines: int = 20) -> str:
    """Take the first max_lines non-empty lines."""
    lines = text.split("\n")
    taken, count = [], 0
    for line in lines:
        stripped = line.strip()
        taken.append(line)
        if stripped:
            count += 1
        if count >= max_lines:
            break
    return "\n".join(taken).strip()


def lemmatize_word(word_lower: str) -> str:
    """Return the French lemma of a lowercased word."""
    from . import nlp_cache  # lazy import to avoid circular dep

    m = _ELISION_RE.match(word_lower)
    if m:
        word_lower = m.group(1)

    if word_lower in _CONTRACTIONS:
        return _CONTRACTIONS[word_lower]

    nlp = nlp_cache.get()
    if nlp is not None:
        tok = nlp(word_lower)[0]
        lemma = tok.lemma_
        if lemma and lemma not in ("-PRON-", ""):
            return lemma
    return simplemma.lemmatize(word_lower, lang="fr")


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    for m in _WORD_RE.finditer(text):
        start, end = m.start(), m.end()
        if start > pos:
            tokens.append(Token(type="sep", value=text[pos:start]))
        word = m.group()
        tokens.append(Token(type="word", value=word, normalized=normalize(word)))
        pos = end
    if pos < len(text):
        tokens.append(Token(type="sep", value=text[pos:]))
    return tokens


def build_index(tokens: list[Token]) -> dict[str, list[int]]:
    """Map normalized word → list of token indices (exact match)."""
    index: dict[str, list[int]] = {}
    for i, tok in enumerate(tokens):
        if tok.type == "word" and tok.normalized:
            index.setdefault(tok.normalized, []).append(i)
    return index


def build_lemma_index(tokens: list[Token]) -> dict[str, list[int]]:
    """Map normalize(lemma(word)) → list of token indices.

    Elision prefixes ("d", "l", "j", …) are first expanded to their full forms
    ("de", "le", "je", …) so that guessing "de" reveals "d'" tokens, etc.
    """
    index: dict[str, list[int]] = {}
    for i, tok in enumerate(tokens):
        if tok.type == "word" and tok.value:
            word_lower = tok.value.lower()
            # Expand bare elision prefix before lemmatizing
            word_lower = _ELISION_EXPAND.get(word_lower, word_lower)
            lemma = lemmatize_word(word_lower)
            lemma_key = normalize(lemma)
            index.setdefault(lemma_key, []).append(i)
    return index


_PUZZLE_PATH = Path(__file__).parent.parent / "puzzle.json"


def build_puzzle(data: dict) -> dict:
    """Build runtime puzzle structures from a song data dict.

    Returns a dict with all the runtime state needed by main.py.
    """
    import json

    text = data["lyrics_excerpt"]
    tokens = tokenize(text)
    word_index = build_index(tokens)
    lemma_index = build_lemma_index(tokens)

    title = data["title"]
    title_normalized = normalize(title)

    artist = data["artist"]
    artist_normalized = normalize(artist)
    # For partial matching: each word of the artist name
    artist_word_norms = [normalize(t.value) for t in tokenize(artist) if t.type == "word"]

    return {
        "tokens": tokens,
        "word_index": word_index,
        "lemma_index": lemma_index,
        "title": title,
        "title_normalized": title_normalized,
        "artist": artist,
        "artist_normalized": artist_normalized,
        "artist_word_norms": artist_word_norms,
        "decade": data.get("decade", ""),
        "puzzle_id": data.get("puzzle_id", "unknown"),
    }


def load_puzzle() -> dict:
    """Load from local puzzle.json (last-resort fallback)."""
    import json
    data = json.loads(_PUZZLE_PATH.read_text(encoding="utf-8"))
    return build_puzzle(data)
