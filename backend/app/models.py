from typing import Literal

from pydantic import BaseModel


class GuessRequest(BaseModel):
    guess: str


class GuessResponse(BaseModel):
    status: Literal["hit", "miss", "invalid", "unknown", "already_found"]
    positions: list[int]
    revealed_texts: dict[str, str] | None = None   # pos (str) → actual token text
    similarity: float | None = None                # best score for miss (history badge)
    word_scores: list[dict] | None = None          # [{pos, score}] for labeled tokens


class TitleGuessRequest(BaseModel):
    title_guess: str


class TitleGuessResponse(BaseModel):
    solved: bool
    title: str | None = None


class ArtistGuessRequest(BaseModel):
    artist_guess: str


class ArtistGuessResponse(BaseModel):
    solved: bool
    artist: str | None = None
