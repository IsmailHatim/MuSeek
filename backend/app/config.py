"""Centralised runtime configuration loaded from environment variables."""

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

ACTIVE_DECADE: str = os.getenv("ACTIVE_DECADE", "")  # empty = all decades
MAX_LYRICS_LINES: int = int(os.getenv("MAX_LYRICS_LINES", "20"))
MIN_LYRICS_WORDS: int = int(os.getenv("MIN_LYRICS_WORDS", "60"))
MIN_GUESS_LENGTH: int = int(os.getenv("MIN_GUESS_LENGTH", "2"))
MIN_LABEL_SCORE: float = float(os.getenv("MIN_LABEL_SCORE", "0.30"))

WORD2VEC_MODEL_PATH: str = os.getenv(
    "WORD2VEC_MODEL_PATH",
    "frWiki_no_lem_no_postag_no_phrase_1000_skip_cut200.bin",
)

GENIUS_API_KEY: str = os.getenv("GENIUS_API_KEY", "")
LYRICS_OVH_TIMEOUT: int = int(os.getenv("LYRICS_OVH_TIMEOUT", "5"))
ADMIN_MODE: bool = os.getenv("ADMIN_MODE", "true").lower() in ("1", "true", "yes")
RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "300"))
