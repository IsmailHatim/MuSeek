# MuSeek

A daily French music guessing game. A hidden song's lyrics are displayed as masked blocks — guess words to reveal them, then identify the title and artist.

Inspired by word-reveal guessing games like Pedantle.

---

## How it works

Each day, a new song is drawn from a curated pool of iconic French songs spanning the 60s through the 2010s. The lyrics excerpt is shown entirely masked. You have three ways to interact:

- **Guess a word** — if it appears in the lyrics, all occurrences are revealed instantly. If it misses, a similarity score tells you how close you are, and near-matches appear as colored labels directly on the masked tokens (red → yellow → green).
- **Guess the title** — a separate input to submit your song title answer.
- **Guess the artist** — partial matches work (e.g. "Goldman" matches "Jean-Jacques Goldman").

One puzzle per day, same for everyone. Your progress is saved locally and restored on refresh.

---

## Features

- Masked lyrics with `█` blocks matching the exact character length of each word
- Semantic similarity scoring — near-miss words are scored and color-coded on the lyrics
- Latest guess shown in heat colors (red → green); previous guesses fade to grayscale
- Conjugation-aware matching — guessing `"parlait"` reveals all forms of `"parler"` in the lyrics
- Dual win conditions: song title + artist name (partial artist match supported)
- Decade badge shown at load (harmless context, no spoilers)
- Full client-side state in `localStorage` — no account needed, refreshes resume progress

---

## Tech stack

- **Backend**: Python, FastAPI, Uvicorn
- **Similarity**: French Word2Vec model ([Fauconnier frWiki](https://fauconnier.github.io/)) via Gensim; spaCy fallback
- **Lemmatization**: spaCy `fr_core_news_sm` + simplemma
- **Lyrics**: Lyrics.ovh (primary) + Genius HTML scraping (fallback)
- **Frontend**: Vanilla JS, no framework

---

## Setup

```bash
# Install dependencies
cd backend
pip install -r requirements.txt
python -m spacy download fr_core_news_sm

# (Optional) Link the Word2Vec model for semantic scoring
ln -s /path/to/frWiki_no_lem_no_postag_no_phrase_1000_skip_cut200.bin backend/

# Run
uvicorn app.main:app --reload
# → http://localhost:8000
```

The server starts with a hardcoded fallback puzzle ("La Bohème" — Charles Aznavour) if no lyrics can be fetched. Set `GENIUS_API_KEY` in your environment for better lyrics coverage.

---

## Pre-fetching daily puzzles

```bash
# Fetch today's puzzle
python scripts/daily_cron.py

# Fetch a specific date
python scripts/daily_cron.py --date 2025-07-14

# Pre-fetch the next 7 days
python scripts/daily_cron.py --days 7

# Overwrite an existing puzzle
python scripts/daily_cron.py --force
```

Pre-fetched puzzles are saved to `backend/daily_puzzles/YYYY-MM-DD.json`. The server loads today's file at startup — no live API calls during gameplay.

---

## Configuration

All settings are environment variables:

| Variable | Default | Description |
|---|---|---|
| `ACTIVE_DECADE` | *(all)* | Filter song pool to a specific decade (`"1980s"`, `"1990s"`, …) |
| `GENIUS_API_KEY` | — | Genius API key for lyrics fallback |
| `WORD2VEC_MODEL_PATH` | `frWiki_no_lem_...bin` | Path to the Word2Vec `.bin` model |
| `MIN_LABEL_SCORE` | `0.30` | Minimum similarity to show a label on a token |
| `MAX_LYRICS_LINES` | `20` | Max lines extracted from fetched lyrics |
| `MIN_LYRICS_WORDS` | `60` | Skip a song if its lyrics have fewer words than this |
| `ADMIN_MODE` | `true` | Shows the reset button; disable in production |
| `RATE_LIMIT_PER_HOUR` | `300` | Max word guesses per IP per hour |

---

## Song pool

~80 curated songs across six decades: 1960s, 1970s, 1980s, 1990s, 2000s, 2010s. Artists include Aznavour, Brel, Goldman, Mylène Farmer, Indochine, MC Solaar, IAM, Stromae, Angèle, PNL, and more.

Songs are defined in `backend/app/songs.py` — easy to extend.

---

## Project structure

```
backend/
  app/
    main.py          FastAPI app + API routes
    puzzle.py        Tokenizer, normalizer, puzzle builder
    lyrics.py        Lyrics.ovh + Genius fetch chain
    songs.py         Curated song pool + date picker
    similarity.py    Word2Vec scoring
    nlp_cache.py     spaCy singleton
    config.py        Environment config
  static/
    index.html
    app.js
    style.css
  puzzle.json        Hardcoded fallback song
  daily_puzzles/     Pre-fetched YYYY-MM-DD.json files
scripts/
  daily_cron.py      Daily puzzle pre-fetch script
```
