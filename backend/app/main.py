import json
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, similarity
from .models import (
    ArtistGuessRequest,
    ArtistGuessResponse,
    GuessRequest,
    GuessResponse,
    TitleGuessRequest,
    TitleGuessResponse,
)
from .puzzle import Token, build_puzzle, lemmatize_word, load_puzzle, normalize

logger = logging.getLogger(__name__)

_BASE = Path(__file__).parent.parent
_CACHE_PATH = _BASE / "puzzle_cache.json"
_FALLBACK_PATH = _BASE / "puzzle.json"
_DAILY_DIR = _BASE / "daily_puzzles"

# ---------------------------------------------------------------------------
# Runtime puzzle state (loaded once at startup)
# ---------------------------------------------------------------------------
_state: dict = {}  # populated in lifespan

# ---------------------------------------------------------------------------
# Rate limiting (in-memory, per IP)
# ---------------------------------------------------------------------------
_rate_counts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str) -> bool:
    """Return True if the IP is within the rate limit."""
    now = time.time()
    window = _rate_counts[ip]
    # Keep only timestamps within the last hour
    _rate_counts[ip] = [t for t in window if now - t < 3600]
    if len(_rate_counts[ip]) >= config.RATE_LIMIT_PER_HOUR:
        return False
    _rate_counts[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Puzzle loading
# ---------------------------------------------------------------------------

async def _load_puzzle_data() -> tuple[dict, str]:
    """Return (raw_data_dict, source_label).

    Priority:
      1. daily_puzzles/YYYY-MM-DD.json
      2. Live fetch from lyrics API
      3. puzzle_cache.json
      4. puzzle.json (hardcoded fallback)
    """
    from .lyrics import fetch_lyrics  # lazy import
    from .songs import pick_song_for_date  # lazy import

    today = date.today()
    daily_path = _DAILY_DIR / f"{today.isoformat()}.json"

    # 1. Today's pre-fetched daily puzzle
    if daily_path.exists():
        try:
            data = json.loads(daily_path.read_text(encoding="utf-8"))
            logger.info("[puzzle] Loaded daily puzzle: %s - %s", data.get("artist"), data.get("title"))
            return data, f"daily-{today.isoformat()}"
        except Exception as exc:
            logger.warning("[puzzle] Daily puzzle read failed (%s). Falling back.", exc)

    # 2. Live fetch
    try:
        decade = config.ACTIVE_DECADE or None
        song = pick_song_for_date(today, decade=decade)
        logger.info("[puzzle] Fetching lyrics for: %s - %s", song["artist"], song["title"])
        lyrics = await fetch_lyrics(song["artist"], song["title"])
        if lyrics:
            data = {
                "puzzle_id": today.isoformat(),
                "title": song["title"],
                "artist": song["artist"],
                "decade": song["decade"],
                "lyrics_excerpt": lyrics,
                "album": song.get("album"),
                "lyrics_source": "live",
            }
            _CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("[puzzle] Live fetch success: %s - %s", song["artist"], song["title"])
            return data, f"live-{today.isoformat()}"
    except Exception as exc:
        logger.warning("[puzzle] Live fetch failed (%s). Trying cache.", exc)

    # 3. puzzle_cache.json
    if _CACHE_PATH.exists():
        try:
            data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
            logger.info("[puzzle] Loaded from cache: %s - %s", data.get("artist"), data.get("title"))
            return data, "cache"
        except Exception as exc:
            logger.warning("[puzzle] Cache read failed (%s). Using hardcoded fallback.", exc)

    # 4. Hardcoded fallback
    data = json.loads(_FALLBACK_PATH.read_text(encoding="utf-8"))
    logger.info("[puzzle] Using hardcoded fallback: %s - %s", data.get("artist"), data.get("title"))
    return data, "fallback"


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _state

    similarity.load_model()

    from . import nlp_cache
    try:
        nlp_cache.load()
    except Exception as exc:
        logger.warning("[nlp] spaCy load failed (%s). Lemmatization disabled.", exc)

    raw_data, _ = await _load_puzzle_data()
    _state = build_puzzle(raw_data)

    vocab = list(_state["word_index"].keys())
    _state["vocab_embeddings"] = similarity.precompute(vocab)

    # For elision tokens ("d", "l", "j", …) the Word2Vec model rarely has a
    # standalone single-letter entry.  Borrow the embedding from the full form
    # ("de", "le", "je", …) so similarity labels still appear on those positions.
    from .puzzle import _ELISION_EXPAND, normalize as _norm
    for bare, full in _ELISION_EXPAND.items():
        bare_key = _norm(bare)   # "d", "l", …  (ASCII, same after normalize)
        if bare_key in _state["word_index"] and bare_key not in _state["vocab_embeddings"]:
            v = similarity.embed(_norm(full))
            if v is not None:
                _state["vocab_embeddings"][bare_key] = v
                logger.debug("[similarity] Borrowed embedding '%s' for elision token '%s'.", full, bare)

    if _state["vocab_embeddings"]:
        logger.info("[similarity] Precomputed embeddings for %d vocab words.", len(_state["vocab_embeddings"]))

    yield


app = FastAPI(lifespan=lifespan)

_STATIC_DIR = _BASE / "static"


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/puzzle")
def get_puzzle():
    tokens: list[Token] = _state["tokens"]
    stream = []
    total_words = 0
    for tok in tokens:
        if tok.type == "word":
            stream.append({"t": "word", "len": len(tok.value)})
            total_words += 1
        else:
            stream.append({"t": "sep", "v": tok.value})

    unique_words = len(_state["word_index"])
    return {
        "puzzle_id": _state["puzzle_id"],
        "language": "fr",
        "decade": _state["decade"],
        "token_stream": stream,
        "meta": {"total_words": total_words, "unique_words": unique_words},
        "admin_mode": config.ADMIN_MODE,
    }


@app.post("/api/guess", response_model=GuessResponse)
def post_guess(body: GuessRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    guess = body.guess.strip()
    if len(guess) < config.MIN_GUESS_LENGTH:
        return GuessResponse(status="invalid", positions=[])

    norm = normalize(guess)
    lemma = normalize(lemmatize_word(guess.lower()))

    word_index: dict[str, list[int]] = _state["word_index"]
    lemma_index: dict[str, list[int]] = _state["lemma_index"]
    tokens: list[Token] = _state["tokens"]
    vocab_embeddings = _state.get("vocab_embeddings", {})

    # Similarity scores against all lyric positions (used for miss labels and hit labels)
    pos_scores, best_score = similarity.score_positions(norm, vocab_embeddings, word_index)

    # Hit: lemma match covers conjugations, plurals, etc.
    # Also fall back to exact word_index match for words not in spaCy lemmatizer.
    positions = lemma_index.get(lemma, []) or word_index.get(norm, [])
    if positions:
        revealed_set = {str(p) for p in positions}
        revealed_texts = {str(pos): tokens[pos].value for pos in positions}
        # Keep similarity labels only for still-unrevealed positions
        hit_scores = [
            p for p in pos_scores
            if p["score"] >= config.MIN_LABEL_SCORE and str(p["pos"]) not in revealed_set
        ]
        return GuessResponse(
            status="hit",
            positions=positions,
            revealed_texts=revealed_texts,
            word_scores=hit_scores if hit_scores else None,
        )

    # Miss — reject words unknown to the vocabulary (pass original casing so
    # accented forms like "été" are found correctly in the Word2Vec model).
    if not similarity.is_in_vocab(guess):
        return GuessResponse(status="unknown", positions=[])

    filtered_scores = [p for p in pos_scores if p["score"] >= config.MIN_LABEL_SCORE]
    return GuessResponse(
        status="miss",
        positions=[],
        similarity=best_score,
        word_scores=filtered_scores if filtered_scores else None,
    )


@app.post("/api/guess_title", response_model=TitleGuessResponse)
def post_guess_title(body: TitleGuessRequest):
    norm = normalize(body.title_guess.strip())
    solved = norm == _state["title_normalized"]
    return TitleGuessResponse(solved=solved, title=_state["title"] if solved else None)


@app.post("/api/guess_artist", response_model=ArtistGuessResponse)
def post_guess_artist(body: ArtistGuessRequest):
    norm = normalize(body.artist_guess.strip())
    # Match full name OR any single word of the artist name
    solved = (
        norm == _state["artist_normalized"]
        or norm in _state["artist_word_norms"]
    )
    return ArtistGuessResponse(solved=solved, artist=_state["artist"] if solved else None)


# Static files mounted last so API routes take priority
app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
