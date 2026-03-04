"""Curated pool of top French songs by decade.

pick_song_for_date() uses a deterministic MD5-based index so the same date
always returns the same song regardless of PYTHONHASHSEED.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import TypedDict


class SongEntry(TypedDict):
    title: str
    artist: str
    decade: str
    album: str | None


SONGS: list[SongEntry] = [
    # ── 1960s ──────────────────────────────────────────────────────────────
    {"title": "La Bohème", "artist": "Charles Aznavour", "decade": "1960s", "album": "La Bohème"},
    {"title": "Ne me quitte pas", "artist": "Jacques Brel", "decade": "1960s", "album": None},
    {"title": "La Javanaise", "artist": "Serge Gainsbourg", "decade": "1960s", "album": None},
    {"title": "Tous les garçons et les filles", "artist": "Françoise Hardy", "decade": "1960s", "album": None},
    {"title": "Le Pénitencier", "artist": "Johnny Hallyday", "decade": "1960s", "album": None},
    {"title": "Amsterdam", "artist": "Jacques Brel", "decade": "1960s", "album": None},
    {"title": "La Vie en rose", "artist": "Édith Piaf", "decade": "1960s", "album": None},
    {"title": "Que je t'aime", "artist": "Johnny Hallyday", "decade": "1960s", "album": None},
    {"title": "La Chanson des vieux amants", "artist": "Jacques Brel", "decade": "1960s", "album": None},
    {"title": "Hier encore", "artist": "Charles Aznavour", "decade": "1960s", "album": None},
    # ── 1970s ──────────────────────────────────────────────────────────────
    {"title": "Les Champs-Élysées", "artist": "Joe Dassin", "decade": "1970s", "album": None},
    {"title": "L'Été indien", "artist": "Joe Dassin", "decade": "1970s", "album": None},
    {"title": "La Tendresse", "artist": "Bourvil", "decade": "1970s", "album": None},
    {"title": "Alexandrie Alexandra", "artist": "Claude François", "decade": "1970s", "album": None},
    {"title": "Il est libre Max", "artist": "Hervé Cristiani", "decade": "1970s", "album": None},
    {"title": "La Ballade des gens heureux", "artist": "Gérard Lenorman", "decade": "1970s", "album": None},
    {"title": "Le Sud", "artist": "Nino Ferrer", "decade": "1970s", "album": None},
    {"title": "Y'a d'la joie", "artist": "Charles Trenet", "decade": "1970s", "album": None},
    {"title": "Et maintenant", "artist": "Gilbert Bécaud", "decade": "1970s", "album": None},
    {"title": "Alexandrina", "artist": "Michel Sardou", "decade": "1970s", "album": None},
    # ── 1980s ──────────────────────────────────────────────────────────────
    {"title": "L'Aventurier", "artist": "Indochine", "decade": "1980s", "album": "L'Aventurier"},
    {"title": "Je te donne", "artist": "Jean-Jacques Goldman", "decade": "1980s", "album": "Minoritaire"},
    {"title": "Quand la musique est bonne", "artist": "Jean-Jacques Goldman", "decade": "1980s", "album": "Positif"},
    {"title": "Libertine", "artist": "Mylène Farmer", "decade": "1980s", "album": "Cendres de lune"},
    {"title": "Plus grandir", "artist": "Mylène Farmer", "decade": "1980s", "album": "Cendres de lune"},
    {"title": "L'Aziza", "artist": "Daniel Balavoine", "decade": "1980s", "album": "Aimer est plus fort que d'être aimé"},
    {"title": "SOS d'un terrien en détresse", "artist": "Daniel Balavoine", "decade": "1980s", "album": None},
    {"title": "Marcia Baïla", "artist": "Les Rita Mitsouko", "decade": "1980s", "album": "The No Comprendo"},
    {"title": "Cargo de nuit", "artist": "Stephan Eicher", "decade": "1980s", "album": None},
    {"title": "On va s'aimer", "artist": "Gilbert Montagné", "decade": "1980s", "album": None},
    {"title": "Quelque chose de Tennessee", "artist": "Johnny Hallyday", "decade": "1980s", "album": "À mains nues"},
    {"title": "La Groupie du pianiste", "artist": "Michel Berger", "decade": "1980s", "album": None},
    {"title": "Résiste", "artist": "France Gall", "decade": "1980s", "album": "Tout pour la musique"},
    {"title": "Ella elle l'a", "artist": "France Gall", "decade": "1980s", "album": "Babacar"},
    {"title": "Juste quelqu'un de bien", "artist": "Enzo Enzo", "decade": "1980s", "album": None},
    # ── 1990s ──────────────────────────────────────────────────────────────
    {"title": "Désenchantée", "artist": "Mylène Farmer", "decade": "1990s", "album": "L'Autre…"},
    {"title": "Je suis le même", "artist": "Indochine", "decade": "1990s", "album": "Un jour dans notre vie"},
    {"title": "Bouge de là", "artist": "MC Solaar", "decade": "1990s", "album": "Qui sème le vent récolte le tempo"},
    {"title": "Prose Combat", "artist": "MC Solaar", "decade": "1990s", "album": "Prose Combat"},
    {"title": "Je danse le mia", "artist": "IAM", "decade": "1990s", "album": "...Ombre est lumière"},
    {"title": "Nés sous la même étoile", "artist": "Jean-Jacques Goldman", "decade": "1990s", "album": "Rouge"},
    {"title": "Le blues du businessman", "artist": "Starmania", "decade": "1990s", "album": "Starmania"},
    {"title": "Pour que tu m'aimes encore", "artist": "Céline Dion", "decade": "1990s", "album": "D'eux"},
    {"title": "Je sais pas", "artist": "Céline Dion", "decade": "1990s", "album": "D'eux"},
    {"title": "Tomber la chemise", "artist": "Zebda", "decade": "1990s", "album": "Essence ordinaire"},
    {"title": "Que tu reviennes", "artist": "Alizée", "decade": "1990s", "album": None},
    {"title": "L'envie d'aimer", "artist": "Les 2Be3", "decade": "1990s", "album": None},
    {"title": "Mon mec à moi", "artist": "Patricia Kaas", "decade": "1990s", "album": "Mademoiselle chante..."},
    {"title": "Foule sentimentale", "artist": "Alain Souchon", "decade": "1990s", "album": "Foule sentimentale"},
    {"title": "Encore un soir", "artist": "Calogero", "decade": "1990s", "album": None},
    # ── 2000s ──────────────────────────────────────────────────────────────
    {"title": "Et si tu n'existais pas", "artist": "Joe Dassin", "decade": "2000s", "album": None},
    {"title": "Je veux te voir", "artist": "Yelle", "decade": "2000s", "album": "Pop-Up"},
    {"title": "Je suis un homme", "artist": "Zazie", "decade": "2000s", "album": "La zizanie"},
    {"title": "À peu près", "artist": "Sinsemilia", "decade": "2000s", "album": None},
    {"title": "Mon amour", "artist": "Calogero", "decade": "2000s", "album": "En apesanteur"},
    {"title": "C'est beau la bourgeoisie", "artist": "Bénabar", "decade": "2000s", "album": "Bénabar"},
    {"title": "Le Dîner", "artist": "Bénabar", "decade": "2000s", "album": "Les éléphants"},
    {"title": "Dès que le vent soufflera", "artist": "Renaud", "decade": "2000s", "album": "Morgane de toi"},
    {"title": "Mistral gagnant", "artist": "Renaud", "decade": "2000s", "album": "Mistral gagnant"},
    {"title": "Je t'emmène au vent", "artist": "Louise Attaque", "decade": "2000s", "album": "Louise Attaque"},
    {"title": "Ton invitation", "artist": "M", "decade": "2000s", "album": None},
    {"title": "Je suis venu te dire que je m'en vais", "artist": "Serge Gainsbourg", "decade": "2000s", "album": None},
    {"title": "Parce que c'est toi", "artist": "Christophe Maé", "decade": "2000s", "album": "Il est où le bonheur"},
    {"title": "Il est où le bonheur", "artist": "Christophe Maé", "decade": "2000s", "album": "Il est où le bonheur"},
    {"title": "La Boulette", "artist": "Diam's", "decade": "2000s", "album": "Dans ma bulle"},
    # ── 2010s ──────────────────────────────────────────────────────────────
    {"title": "Alors on danse", "artist": "Stromae", "decade": "2010s", "album": "Cheese"},
    {"title": "Papaoutai", "artist": "Stromae", "decade": "2010s", "album": "Racine carrée"},
    {"title": "Formidable", "artist": "Stromae", "decade": "2010s", "album": "Racine carrée"},
    {"title": "Tous les mêmes", "artist": "Stromae", "decade": "2010s", "album": "Racine carrée"},
    {"title": "La Vie est belle", "artist": "Indila", "decade": "2010s", "album": "Mini World"},
    {"title": "Dernière danse", "artist": "Indila", "decade": "2010s", "album": "Mini World"},
    {"title": "Je vole", "artist": "Louane", "decade": "2010s", "album": "Chambre 12"},
    {"title": "On était beau", "artist": "Maître Gims", "decade": "2010s", "album": None},
    {"title": "Zombie", "artist": "PNL", "decade": "2010s", "album": "Que la famille"},
    {"title": "Au DD", "artist": "PNL", "decade": "2010s", "album": "Dans la légende"},
    {"title": "La Loi de Murphy", "artist": "Nekfeu", "decade": "2010s", "album": "Cyborg"},
    {"title": "Fleur bleue", "artist": "Angèle", "decade": "2010s", "album": "Brol"},
    {"title": "Balance ton quoi", "artist": "Angèle", "decade": "2010s", "album": "Brol"},
    {"title": "Finalement", "artist": "Vianney", "decade": "2010s", "album": "Idiot"},
    {"title": "Pas là", "artist": "Vianney", "decade": "2010s", "album": "Idiot"},
]


def pick_song_for_date(target_date: date, decade: str | None = None) -> SongEntry:
    """Deterministically pick a song for a given date.

    If decade is provided, filters to that decade first.
    Uses MD5 for a stable hash across Python sessions.
    """
    pool = [s for s in SONGS if s["decade"] == decade] if decade else SONGS
    if not pool:
        pool = SONGS
    h = int(hashlib.md5(target_date.isoformat().encode()).hexdigest(), 16)
    return pool[h % len(pool)]


def get_pool(decade: str | None = None) -> list[SongEntry]:
    """Return the song pool for a given decade (or all songs if None)."""
    if decade:
        return [s for s in SONGS if s["decade"] == decade]
    return list(SONGS)
