"""Singleton spaCy model shared by similarity.py and puzzle.py."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_nlp = None


def load(model_name: str | None = None) -> None:
    """Load the spaCy model once; subsequent calls are no-ops.

    Tries fr_core_news_md first (has 20k word vectors, needed for similarity
    fallback), then fr_core_news_sm (lemmatization only, no vectors).
    Pass an explicit model_name to override the preference order.
    """
    global _nlp
    if _nlp is not None:
        return
    import spacy  # noqa: PLC0415

    candidates = [model_name] if model_name else ["fr_core_news_md", "fr_core_news_sm"]
    for name in candidates:
        try:
            logger.info("[nlp] Loading %s …", name)
            _nlp = spacy.load(name, disable=["ner", "parser"])
            logger.info("[nlp] Ready (%s).", name)
            return
        except OSError:
            logger.info("[nlp] %s not found, trying next.", name)
    logger.warning("[nlp] No spaCy French model found. Lemmatization and spaCy similarity disabled.")


def get():
    return _nlp
