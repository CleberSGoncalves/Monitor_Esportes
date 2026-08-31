from __future__ import annotations

import re
import unicodedata
from typing import Dict, Optional, Tuple

try:
    import yt_dlp
except Exception:
    yt_dlp = None


_COMP_PATTERNS = [
    ("Campeonato Paulista", [r"\bpaulista\b", r"\bpaulistao\b", r"\bpaulistão\b"]),
    ("Brasileirão", [r"\bbrasileirao\b", r"\bbrasileirão\b", r"\bcampeonato brasileiro\b"]),
    ("Copa do Brasil", [r"\bcopa do brasil\b"]),
    ("Libertadores", [r"\blibertadores\b"]),
    ("Sul-Americana", [r"\bsul[- ]americana\b", r"\bsudamericana\b"]),
    ("Champions League", [r"\bchampions\b", r"\buefa champions\b"]),
    ("Copa do Mundo", [r"\bcopa do mundo\b", r"\bworld cup\b"]),
    ("Eliminatórias", [r"\beliminatorias\b", r"\beliminatórias\b"]),
    ("Amistoso", [r"\bamistoso\b", r"\bfriendly\b"]),
]

_NOISE_PATTERNS = [
    r"\bao vivo\b",
    r"\blive\b",
    r"\bcom imagens\b",
    r"\bnarrac[aã]o\b",
    r"\brea[cç][aã]o\b",
    r"\breact\b",
    r"\bjogo completo\b",
    r"\bmelhores momentos\b",
    r"\bfinal\b",
    r"\bsemifinal\b",
    r"\bquartas\b",
    r"\bvolta\b",
    r"\bida\b",
    r"\bhoje\b",
    r"\bagora\b",
]


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def fetch_youtube_title(url: str) -> Optional[str]:
    if yt_dlp is None or not url:
        return None

    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if isinstance(info, dict):
                title = (info.get("title") or "").strip()
                return title or None
    except Exception:
        pass

    return None


def _clean_title(title: str) -> str:
    s = (title or "").strip()
    s = re.sub(r"https?://\S+", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\[[^\]]+\]", " ", s)
    s = re.sub(r"\([^)]*\)", " ", s)

    for pat in _NOISE_PATTERNS:
        s = re.sub(pat, " ", s, flags=re.IGNORECASE)

    s = re.sub(r"\s+", " ", s).strip(" -|:")
    return s or "—"


def _extract_competition(title: str) -> str:
    t = _norm(title)
    for label, patterns in _COMP_PATTERNS:
        if any(re.search(p, t, flags=re.IGNORECASE) for p in patterns):
            return label
    return "—"


def _clean_team_chunk(s: str) -> str:
    s = _clean_title(s)
    s = re.sub(r"\b(?:campeonato|copa|libertadores|sul-americana|sudamericana|champions|brasileirao|brasileirão|paulista|paulistao|paulistão)\b.*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" -|:")
    return s.title() if s else "—"


def _extract_match(title: str) -> Tuple[str, str]:
    s = _clean_title(title)

    patterns = [
        r"([A-Za-zÀ-ÿ0-9 .\-]+?)\s+[xX×]\s+([A-Za-zÀ-ÿ0-9 .\-]+?)(?:\s+\||\s+-\s+|$)",
        r"([A-Za-zÀ-ÿ0-9 .\-]+?)\s+vs\.?\s+([A-Za-zÀ-ÿ0-9 .\-]+?)(?:\s+\||\s+-\s+|$)",
    ]

    for pat in patterns:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if not m:
            continue

        a = _clean_team_chunk(m.group(1))
        b = _clean_team_chunk(m.group(2))

        if a != "—" and b != "—" and a.lower() != b.lower():
            return a, b

    return "—", "—"


def get_youtube_metadata(url: str) -> Dict[str, str]:
    raw_title = fetch_youtube_title(url) or "—"
    clean_title = _clean_title(raw_title)

    team_a, team_b = _extract_match(clean_title)
    competition = _extract_competition(raw_title)

    match_display = f"{team_a} x {team_b}" if team_a != "—" and team_b != "—" else "—"

    return {
        "title": clean_title,
        "team_a": team_a,
        "team_b": team_b,
        "match_display": match_display,
        "competition": competition,
    }