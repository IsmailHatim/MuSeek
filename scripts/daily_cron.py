#!/usr/bin/env python3
"""Pre-fetch script for MuSeek daily puzzles.

Usage:
    python scripts/daily_cron.py                    # fetch today's puzzle
    python scripts/daily_cron.py --date 2025-07-14  # specific date
    python scripts/daily_cron.py --force            # overwrite if exists

Run from the repository root.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure backend/ is on the path so we can import app modules
REPO_ROOT = Path(__file__).parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("daily_cron")


async def fetch_puzzle_for_date(target_date: date, force: bool = False) -> bool:
    """Fetch and save the puzzle for target_date. Returns True on success."""
    from app import config
    from app.lyrics import fetch_lyrics
    from app.puzzle import build_puzzle, tokenize
    from app.songs import get_pool, pick_song_for_date

    daily_dir = BACKEND_DIR / "daily_puzzles"
    daily_dir.mkdir(exist_ok=True)
    output_path = daily_dir / f"{target_date.isoformat()}.json"

    if output_path.exists() and not force:
        logger.info("Puzzle already exists for %s. Use --force to overwrite.", target_date)
        return True

    decade = config.ACTIVE_DECADE or None
    pool = get_pool(decade)

    # Try songs in order starting from the deterministic pick, falling back to others
    import hashlib
    h = int(hashlib.md5(target_date.isoformat().encode()).hexdigest(), 16)
    start_idx = h % len(pool)
    ordered = pool[start_idx:] + pool[:start_idx]

    for attempt, song in enumerate(ordered):
        logger.info(
            "Attempt %d/%d: %s - %s (%s)",
            attempt + 1, len(ordered), song["artist"], song["title"], song["decade"],
        )
        lyrics = await fetch_lyrics(song["artist"], song["title"])
        if not lyrics:
            logger.warning("No lyrics found. Skipping.")
            continue

        # Validate token count
        tokens = tokenize(lyrics)
        word_count = sum(1 for t in tokens if t.type == "word")
        if word_count < config.MIN_LYRICS_WORDS:
            logger.warning(
                "Lyrics too short (%d words < %d minimum). Skipping.",
                word_count, config.MIN_LYRICS_WORDS,
            )
            continue

        # Build puzzle
        puzzle_state = build_puzzle({
            "puzzle_id": target_date.isoformat(),
            "title": song["title"],
            "artist": song["artist"],
            "decade": song["decade"],
            "lyrics_excerpt": lyrics,
            "album": song.get("album"),
        })

        # Serialize tokens for storage
        serialized_tokens = [
            {"t": t.type, "v": t.value, "n": t.normalized}
            for t in puzzle_state["tokens"]
        ]

        output = {
            "puzzle_id": target_date.isoformat(),
            "title": song["title"],
            "artist": song["artist"],
            "decade": song["decade"],
            "album": song.get("album"),
            "lyrics_excerpt": lyrics,
            "word_index": puzzle_state["word_index"],
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "lyrics_source": "lyrics_ovh_or_genius",
        }

        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            "Saved puzzle for %s: %s - %s (%d words) → %s",
            target_date, song["artist"], song["title"], word_count, output_path,
        )
        return True

    logger.error("All songs failed for %s. No puzzle saved.", target_date)
    return False


def parse_args():
    parser = argparse.ArgumentParser(description="MuSeek daily puzzle pre-fetcher")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Target date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing puzzle file",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of consecutive days to fetch starting from --date (default: 1)",
    )
    return parser.parse_args()


async def main():
    args = parse_args()

    if args.date:
        start = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        start = date.today()

    from datetime import timedelta

    success_count = 0
    for i in range(args.days):
        target = start + timedelta(days=i)
        ok = await fetch_puzzle_for_date(target, force=args.force)
        if ok:
            success_count += 1

    logger.info(
        "Done. %d/%d puzzles successfully fetched.", success_count, args.days
    )
    if success_count < args.days:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
