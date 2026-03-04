/* =========================================================
   MuSeek — client
   State stored in localStorage under key "museek_state"
   ========================================================= */

const STATE_KEY = "museek_state";

let puzzleTokens = [];
let puzzleId     = null;

let state = {
  puzzle_id:       null,
  revealed:        {},   // pos (str) → actual token text
  best_match:      {},   // pos (str) → {word, score}
  last_miss_word:  null,
  history:         [],   // [{word, status, score?}]
  title_solved:    false,
  artist_solved:   false,
  solved_title:    null, // text of the solved title
  solved_artist:   null, // text of the solved artist
  title_guesses:   [],
  artist_guesses:  [],
};

// ── Persistence ───────────────────────────────────────────────────────────

function loadState() {
  try { const r = localStorage.getItem(STATE_KEY); if (r) return JSON.parse(r); }
  catch (_) {}
  return null;
}
function saveState() { localStorage.setItem(STATE_KEY, JSON.stringify(state)); }

// ── Score → CSS class ────────────────────────────────────────────────────

function tokenScoreClass(score) {
  if (score >= 0.82) return "score-hot";
  if (score >= 0.70) return "score-warm";
  if (score >= 0.58) return "score-mild";
  if (score >= 0.45) return "score-cold";
  return "score-frozen";
}

function badgeScoreClass(score) {
  if (score >= 0.70) return "hot";   // green
  if (score >= 0.58) return "warm";  // yellow
  return "cold";                     // red
}

// ── Lyrics rendering ──────────────────────────────────────────────────────

function buildDisplay() {
  const el = document.getElementById("lyrics-display");
  el.innerHTML = "";

  puzzleTokens.forEach((tok, pos) => {
    if (tok.t === "sep") {
      el.appendChild(document.createTextNode(tok.v));
      return;
    }
    const span = document.createElement("span");
    span.dataset.pos = pos;

    const posStr = String(pos);
    if (state.revealed[posStr]) {
      span.className = "token revealed";
      span.textContent = state.revealed[posStr];
    } else if (state.best_match[posStr]) {
      const { word, score } = state.best_match[posStr];
      const isLatest = state.last_miss_word && word === state.last_miss_word;
      span.className = `token labeled ${tokenScoreClass(score)}${isLatest ? " latest" : ""}`;
      span.textContent = word;
    } else {
      span.className = "token masked";
      span.textContent = "█".repeat(tok.len);
    }
    el.appendChild(span);
  });
}

function revealPositions(revealedTexts) {
  Object.entries(revealedTexts).forEach(([posStr, text]) => {
    state.revealed[posStr] = text;
    delete state.best_match[posStr];
    const span = document.querySelector(`[data-pos="${posStr}"]`);
    if (span) {
      span.className = "token revealed";
      span.textContent = text;
    }
  });
}

function updateBestMatch(posScores, displayWord) {
  posScores.forEach(({ pos, score }) => {
    const posStr = String(pos);
    if (state.revealed[posStr]) return;
    const cur = state.best_match[posStr];
    if (!cur || score > cur.score) {
      state.best_match[posStr] = { word: displayWord, score };
    }
  });
}

// ── History sidebar ───────────────────────────────────────────────────────

function makeHistoryItem(num, word, status, score) {
  const li = document.createElement("li");
  li.className = status;

  const numSpan = document.createElement("span");
  numSpan.className = "hist-num";
  numSpan.textContent = num;
  li.appendChild(numSpan);

  const wordSpan = document.createElement("span");
  wordSpan.className = "hist-word";
  wordSpan.textContent = word;
  li.appendChild(wordSpan);

  if (status === "miss" && score != null) {
    const badge = document.createElement("span");
    badge.className = `score-badge ${badgeScoreClass(score)}`;
    badge.textContent = score.toFixed(2);
    li.appendChild(badge);
  }
  return li;
}

function addHistory(word, status, score = null) {
  const num = state.history.length + 1;
  state.history.push({ word, status, score });
  document.getElementById("history").prepend(makeHistoryItem(num, word, status, score));
}

function renderHistory() {
  const ul = document.getElementById("history");
  ul.innerHTML = "";
  [...state.history].reverse().forEach(({ word, status, score }, i) => {
    ul.appendChild(makeHistoryItem(state.history.length - i, word, status, score ?? null));
  });
}

// ── Win conditions ────────────────────────────────────────────────────────

function applyTitleSolved(title) {
  document.getElementById("title-banner-text").textContent = `Titre : « ${title} »`;
  document.getElementById("title-banner").classList.remove("hidden");
  const disp = document.getElementById("title-solved-display");
  disp.textContent = title;
  disp.classList.remove("hidden");
  document.getElementById("title-input").disabled = true;
  document.getElementById("title-submit-btn").disabled = true;
  document.getElementById("title-wrong-msg").classList.add("hidden");
}

function applyArtistSolved(artist) {
  document.getElementById("artist-banner-text").textContent = `Artiste : ${artist}`;
  document.getElementById("artist-banner").classList.remove("hidden");
  const disp = document.getElementById("artist-solved-display");
  disp.textContent = artist;
  disp.classList.remove("hidden");
  document.getElementById("artist-input").disabled = true;
  document.getElementById("artist-submit-btn").disabled = true;
  document.getElementById("artist-wrong-msg").classList.add("hidden");
}

function checkFullWin() {
  if (state.title_solved && state.artist_solved) {
    document.getElementById("full-win-banner").classList.remove("hidden");
  }
}

// ── Feedback messages ─────────────────────────────────────────────────────

let _unknownTimer = null;
function showUnknownMsg(word) {
  const el = document.getElementById("unknown-msg");
  el.textContent = `« ${word} » — je ne connais pas ce mot.`;
  el.classList.remove("hidden");
  if (_unknownTimer) clearTimeout(_unknownTimer);
  _unknownTimer = setTimeout(() => el.classList.add("hidden"), 3000);
}

function showWrongMsg(elId, word) {
  const el = document.getElementById(elId);
  el.textContent = `« ${word} » — ce n'est pas la bonne réponse.`;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3000);
}

// ── API ───────────────────────────────────────────────────────────────────

async function fetchPuzzle() {
  const r = await fetch("/api/puzzle");
  if (!r.ok) throw new Error("Failed to fetch puzzle");
  return r.json();
}

async function postGuess(guess) {
  const r = await fetch("/api/guess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ guess }),
  });
  return r.json();
}

async function postTitleGuess(guess) {
  const r = await fetch("/api/guess_title", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title_guess: guess }),
  });
  return r.json();
}

async function postArtistGuess(guess) {
  const r = await fetch("/api/guess_artist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ artist_guess: guess }),
  });
  return r.json();
}

// ── Word guess handler ────────────────────────────────────────────────────

document.getElementById("guess-form").addEventListener("submit", async (e) => {
  e.preventDefault();

  const input = document.getElementById("guess-input");
  const word = input.value.trim();
  input.value = "";
  if (!word) return;

  const data = await postGuess(word);

  if (data.status === "unknown") {
    showUnknownMsg(word);
    return;
  }
  if (data.status === "invalid") {
    return;
  }
  if (data.status === "already_found") {
    return;
  }

  if (data.status === "hit") {
    revealPositions(data.revealed_texts || {});
    if (data.word_scores && data.word_scores.length) {
      updateBestMatch(data.word_scores, word);
      buildDisplay();
    }
    addHistory(word, "hit");
  } else if (data.status === "miss") {
    state.last_miss_word = word;
    updateBestMatch(data.word_scores || [], word);
    buildDisplay();
    addHistory(word, "miss", data.similarity ?? null);
  } else {
    addHistory(word, data.status);
  }

  saveState();
});

// ── Title guess handler ───────────────────────────────────────────────────

document.getElementById("title-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (state.title_solved) return;

  const input = document.getElementById("title-input");
  const guess = input.value.trim();
  input.value = "";
  if (!guess) return;

  state.title_guesses.push(guess);
  const data = await postTitleGuess(guess);

  if (data.solved) {
    state.title_solved = true;
    state.solved_title = data.title;
    applyTitleSolved(data.title);
    checkFullWin();
    saveState();
  } else {
    showWrongMsg("title-wrong-msg", guess);
  }
});

// ── Artist guess handler ──────────────────────────────────────────────────

document.getElementById("artist-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (state.artist_solved) return;

  const input = document.getElementById("artist-input");
  const guess = input.value.trim();
  input.value = "";
  if (!guess) return;

  state.artist_guesses.push(guess);
  const data = await postArtistGuess(guess);

  if (data.solved) {
    state.artist_solved = true;
    state.solved_artist = data.artist;
    applyArtistSolved(data.artist);
    checkFullWin();
    saveState();
  } else {
    showWrongMsg("artist-wrong-msg", guess);
  }
});

// ── Reset ─────────────────────────────────────────────────────────────────

document.getElementById("reset-btn").addEventListener("click", () => {
  if (confirm("Recommencer depuis zéro ?")) {
    localStorage.removeItem(STATE_KEY);
    location.reload();
  }
});

// ── Init ──────────────────────────────────────────────────────────────────

async function init() {
  const puzzle = await fetchPuzzle();
  puzzleId     = puzzle.puzzle_id;
  puzzleTokens = puzzle.token_stream;

  // Update header
  const decade = puzzle.decade;
  if (decade) {
    document.getElementById("decade-badge").textContent = decade;
  }
  const dateEl = document.getElementById("puzzle-date");
  if (puzzleId && /^\d{4}-\d{2}-\d{2}$/.test(puzzleId)) {
    const [y, m, d] = puzzleId.split("-");
    dateEl.textContent = `${d}/${m}/${y}`;
  }

  if (!puzzle.admin_mode) {
    document.getElementById("reset-btn").classList.add("hidden");
  }

  // Restore or init state
  const saved = loadState();
  if (saved && saved.puzzle_id === puzzleId) {
    state = {
      puzzle_id:      puzzleId,
      revealed:       saved.revealed       || {},
      best_match:     saved.best_match     || {},
      last_miss_word: saved.last_miss_word ?? null,
      history:        saved.history        || [],
      title_solved:   saved.title_solved   || false,
      artist_solved:  saved.artist_solved  || false,
      solved_title:   saved.solved_title   ?? null,
      solved_artist:  saved.solved_artist  ?? null,
      title_guesses:  saved.title_guesses  || [],
      artist_guesses: saved.artist_guesses || [],
    };
  } else {
    state = {
      puzzle_id: puzzleId,
      revealed: {}, best_match: {}, last_miss_word: null,
      history: [], title_solved: false, artist_solved: false,
      solved_title: null, solved_artist: null,
      title_guesses: [], artist_guesses: [],
    };
    saveState();
  }

  buildDisplay();
  renderHistory();

  // Restore win states
  if (state.title_solved && state.solved_title) {
    applyTitleSolved(state.solved_title);
  }
  if (state.artist_solved && state.solved_artist) {
    applyArtistSolved(state.solved_artist);
  }
  checkFullWin();
}

init().catch(err => console.error("Init failed:", err));
