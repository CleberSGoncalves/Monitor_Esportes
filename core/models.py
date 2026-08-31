from __future__ import annotations

# --- bootstrap de path (pra rodar no VSCode / python gui/main_gui.py) ---
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ------------------------------------------------------------------------

import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import customtkinter as ctk
import cv2
import numpy as np

try:
    from PIL import Image
except Exception:
    Image = None


_YT_ID_RE = re.compile(r"(?:v=|/live/|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", re.IGNORECASE)

_COMPETITION_PATTERNS = [
    ("Campeonato Paulista", ["campeonato paulista", "paulistao", "paulista"]),
    ("Brasileirão", ["brasileirão", "brasileirao", "campeonato brasileiro", "brasileiro serie a", "brasileiro série a", "brasileiro serie b", "brasileiro série b"]),
    ("Copa do Brasil", ["copa do brasil"]),
    ("Libertadores", ["libertadores", "pré-libertadores", "pre-libertadores", "pre libertadores"]),
    ("Sul-Americana", ["sul-americana", "sul americana", "sudamericana"]),
    ("Champions League", ["champions league", "uefa champions", "champions"]),
    ("Copa do Mundo", ["copa do mundo", "world cup", "mundial"]),
    ("Eliminatórias", ["eliminatorias", "eliminatórias", "qualifiers"]),
    ("Amistoso", ["amistoso", "friendly"]),
]


def normalize_watch_url_to_embed(url: str) -> str:
    """
    NÃO usa /embed porque pode dar Erro 153 (embed bloqueado).
    Usa /watch ou /live que roda no OBS Browser Source.
    """
    u = (url or "").strip()
    m = _YT_ID_RE.search(u)
    if not m:
        return u
    vid = m.group(1)
    return f"https://www.youtube.com/live/{vid}?autoplay=1"


def _safe_slug(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")[:80] or "event"


def _now() -> datetime:
    return datetime.now()


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None

    s = str(s).strip()
    if not s:
        return None

    # tenta ISO mais completo primeiro
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        pass

    # Tenta Timestamp numérico
    try:
        if s.replace('.', '', 1).isdigit():
            return datetime.fromtimestamp(float(s))
    except Exception:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
    ):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass

    return None


def _fmt_dt(s: Optional[str]) -> str:
    dt = _parse_dt(s)
    if not dt:
        return "—"
    return dt.strftime("%d/%m %H:%M")


def _human_age(dt: datetime) -> str:
    delta = dt - _now()
    sec = int(delta.total_seconds())

    if sec <= 0:
        return "agora"

    m = sec // 60
    if m < 60:
        return f"em {m} min"

    h = m // 60
    if h < 48:
        return f"em {h}h {m % 60:02d}m"

    d = h // 24
    return f"em {d}d"


def _ensure_dir(p: str) -> str:
    os.makedirs(p, exist_ok=True)
    return p


def _event_root(event_id: str) -> str:
    return _ensure_dir(os.path.join("data", "events", event_id))


def _event_paths(event_id: str) -> Dict[str, str]:
    root = _event_root(event_id)
    return {
        "root": root,
        "frames": _ensure_dir(os.path.join(root, "frames")),
        "audio": _ensure_dir(os.path.join(root, "audio")),
        "reports": _ensure_dir(os.path.join(root, "reports")),
        "logs": _ensure_dir(os.path.join(root, "logs")),
        "debug_templates": _ensure_dir(os.path.join(root, "debug_templates")),
        "debug_snapshots": _ensure_dir(os.path.join(root, "debug_snapshots")),
    }


def _latest_file(folder: str, exts: Tuple[str, ...]) -> Optional[Tuple[str, float]]:
    if not os.path.isdir(folder):
        return None

    best_path: Optional[str] = None
    best_mtime = -1.0

    try:
        for n in os.scandir(folder):
            if not n.name.lower().endswith(exts):
                continue

            p = n.path
            try:
                mt = os.path.getmtime(p)
            except Exception:
                continue

            if mt > best_mtime:
                best_mtime = mt
                best_path = p
    except Exception:
        return None

    if not best_path:
        return None

    return best_path, best_mtime


def _safe_timestamp(dt: Optional[datetime]) -> float:
    if dt is None:
        return float("inf")

    try:
        ts = dt.timestamp()
        if not (ts == ts) or ts == float("inf") or ts == float("-inf"):
            return float("inf")
        return ts
    except Exception:
        return float("inf")


def _norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s


def _event_matches_category(event_title: str, selected_categories: List[str]) -> bool:
    title = _norm_text(event_title)
    
    # Se não houver filtros ou 'todos' estiver selecionado, aceita tudo (exceto exclusões)
    if not selected_categories or "todos" in [s.lower() for s in selected_categories]:
        matches_cat = True
    else:
        rules = {
            "campeonato paulista": ["paulista", "paulistao", "campeonato paulista"],
            "libertadores": ["libertadores", "pre-libertadores", "pre libertadores"],
            "copa do mundo": ["copa do mundo", "world cup", "mundial"],
            "eliminatorias": ["eliminatorias", "eliminatorias da copa", "qualifiers"],
            "amistoso": ["amistoso", "friendly"],
            "brasileirao": ["brasileirao", "brasileiro", "serie a", "serie b"],
            "copa do brasil": ["copa do brasil"],
            "champions league": ["champions", "uefa champions"],
            "sul-americana": ["sul-americana", "sul americana", "sudamericana"],
        }
        
        matches_cat = False
        forSel = [s.lower() for s in selected_categories]
        for canonical, aliases in _COMPETITION_PATTERNS:
            if canonical.lower() in forSel or any(_norm_text(a) in forSel for a in [canonical] + aliases):
                if any(_norm_text(alias) in title for alias in aliases + [canonical]):
                    matches_cat = True
                    break

    if not matches_cat:
        return False
        
    # NOVAS REGRAS DE FILTRAGEM (Fase 2)
    # 1. Ignorar programas, debates e informativos
    exclude_terms = ["debate", "mesa redonda", "resenha", "pos-jogo", "pre-jogo", "analise", "informacoes", "noticias", "escalacao"]
    if any(term in title for term in exclude_terms):
        return False
        
    return True


def cleanup_old_files(folder: str, keep_last: int = 120, exts: Tuple[str, ...] = (".jpg",)) -> None:
    try:
        if not os.path.isdir(folder):
            return

        files = [
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if f.lower().endswith(exts)
        ]

        files.sort(key=lambda x: os.path.getmtime(x))

        if len(files) <= keep_last:
            return

        for f in files[:-keep_last]:
            try:
                os.remove(f)
            except Exception:
                pass

    except Exception as e:
        print("cleanup error:", e)


def _clean_event_title(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return "—"

    # Remover colchetes [Tags]
    s = re.sub(r"\[[^\]]+\]", " ", s)
    
    # Remover tags comuns de transmissão e rodada
    ignore_patterns = [
        r"\(.*?\)", 
        r"\b(?:AO VIVO|LIVE|COM IMAGENS|NARRAÇÃO|REAÇÃO|REACT|FULL MATCH|REPLAY|MELHORES MOMENTOS)\b",
        r"\b(?:JOGO COMPLETO|PARTIDA COMPLETA)\b",
        r"\b(?:\d+ª?\s*RODADA|ROUND\s*\d+)\b",
        r"\b(?:SÉRIE [A-Z]|SERIE [A-Z])\b",
        r"\b(?:COPA\s+.*?|CAMPEONATO\s+.*?)\b",
    ]
    
    for pat in ignore_patterns:
        s = re.sub(pat, " ", s, flags=re.IGNORECASE)
        
    s = re.sub(r"\s+", " ", s).strip(" -|:")
    return s or raw.strip() or "—"


def _find_competition(raw: str, selected_category: str = "") -> str:
    raw_norm = _norm_text(raw)

    for canonical, aliases in _COMPETITION_PATTERNS:
        if any(_norm_text(alias) in raw_norm for alias in aliases):
            return canonical

    selected = (selected_category or "").strip()
    if selected and _norm_text(selected) != "todos":
        return selected

    split_parts = [p.strip() for p in re.split(r"\s+\|\s+|\s+-\s+", raw) if p.strip()]
    if len(split_parts) >= 2:
        tail = split_parts[-1]
        if len(tail) <= 60 and not re.search(r"\b(?:x|×)\b", tail, flags=re.IGNORECASE):
            return tail

    return "—"


def _normalize_team_name(name: str) -> str:
    s = (name or "").strip(" -|:")
    s = re.sub(r"\b(?:ao vivo|live|com imagens|narração|react|reação)\b", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" -|:")
    return s or "—"


def _extract_match_from_title(raw: str) -> Tuple[str, str]:
    s = _clean_event_title(raw)

    patterns = [
        r"(.+?)\s+([xX×]|vs\.?)\s+(.+?)(?:\s+\||\s+-\s+|$)",
        r"(.+?)\s+-\s+(.+?)(?:\s+\||\s+|$)", # Formato Time A - Time B
    ]

    for pat in patterns:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if m:
            if "x" in pat or "vs" in pat:
                a = _normalize_team_name(m.group(1))
                b = _normalize_team_name(m.group(3))
            else:
                a = _normalize_team_name(m.group(1))
                b = _normalize_team_name(m.group(2))
            # Garantir que não pegamos fragmentos irrelevantes
            if a != "—" and b != "—" and len(a) > 2 and len(b) > 2:
                return a, b

    return "—", "—"


def _extract_event_meta(title: str, selected_category: str = "") -> Dict[str, str]:
    raw = (title or "").strip()
    clean = _clean_event_title(raw)

    team_a, team_b = _extract_match_from_title(clean)
    competition = _find_competition(clean, selected_category)

    if team_a != "—" and team_b != "—":
        match_display = f"{team_a} x {team_b}"
    else:
        match_display = clean

    return {
        "competition": competition or "—",
        "team_a": team_a,
        "team_b": team_b,
        "match_display": match_display,
    }


def _clean_hud_text(s: Optional[str]) -> str:
    t = (s or "").strip()
    t = re.sub(r"\s+", " ", t)
    t = t.strip(" -|")
    return t or "—"


def _fmt_conf(v: Any) -> str:
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "—"


def _fit_image(frame_bgr: np.ndarray, max_w: int, max_h: int) -> np.ndarray:
    max_w = max(1, int(max_w))
    max_h = max(1, int(max_h))

    if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
        return np.zeros((max_h, max_w, 3), dtype=np.uint8)

    h, w = frame_bgr.shape[:2]
    if h <= 0 or w <= 0:
        return np.zeros((max_h, max_w, 3), dtype=np.uint8)

    scale = min(max_w / float(w), max_h / float(h))
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return cv2.resize(frame_bgr, (nw, nh), interpolation=cv2.INTER_AREA)


def _bgr_to_pil(frame_bgr: np.ndarray) -> Optional[Any]:
    if Image is None or frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
        return None
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def _bgr_to_ctk(frame_bgr: np.ndarray, size: Optional[Tuple[int, int]] = None) -> Optional[Any]:
    if Image is None or frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
        return None

    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)

    if size is None:
        size = (pil_img.width, pil_img.height)

    return ctk.CTkImage(
        light_image=pil_img,
        dark_image=pil_img,
        size=size,
    )


def _safe_crop(frame: np.ndarray, rect: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
    if frame is None or getattr(frame, "size", 0) == 0 or rect is None:
        return np.zeros((80, 160, 3), dtype=np.uint8)

    x1, y1, x2, y2 = rect
    h, w = frame.shape[:2]

    x1 = max(0, min(w - 1, int(x1)))
    x2 = max(1, min(w, int(x2)))
    y1 = max(0, min(h - 1, int(y1)))
    y2 = max(1, min(h, int(y2)))

    if x2 <= x1 or y2 <= y1:
        return np.zeros((80, 160, 3), dtype=np.uint8)

    return frame[y1:y2, x1:x2].copy()


def _xywh_to_xyxy(rect: Any) -> Optional[Tuple[int, int, int, int]]:
    if rect is None:
        return None

    if isinstance(rect, (tuple, list)) and len(rect) == 4:
        x, y, w, h = rect
        if all(isinstance(v, (int, float)) for v in rect):
            x = int(x)
            y = int(y)
            w = int(w)
            h = int(h)
            return (x, y, x + w, y + h)

    return None


def _normalize_rect(rect: Any, frame_shape: Tuple[int, ...]) -> Optional[Tuple[int, int, int, int]]:
    if rect is None:
        return None

    h, w = frame_shape[:2]

    if isinstance(rect, dict):
        vals = (
            rect.get("x1", rect.get("left")),
            rect.get("y1", rect.get("top")),
            rect.get("x2", rect.get("right")),
            rect.get("y2", rect.get("bottom")),
        )
        if all(v is not None for v in vals):
            x1, y1, x2, y2 = vals
            return int(x1), int(y1), int(x2), int(y2)

    if isinstance(rect, (tuple, list)) and len(rect) == 4:
        x1, y1, x2, y2 = rect
        if all(isinstance(v, (int, float)) for v in rect):
            if 0 <= x1 <= 1 and 0 <= x2 <= 1 and 0 <= y1 <= 1 and 0 <= y2 <= 1:
                return (
                    int(x1 * w),
                    int(y1 * h),
                    int(x2 * w),
                    int(y2 * h),
                )
            return int(x1), int(y1), int(x2), int(y2)

    return None


def _draw_rect(
    frame: np.ndarray,
    rect: Optional[Tuple[int, int, int, int]],
    label: str,
    color: Tuple[int, int, int],
) -> None:
    if frame is None or getattr(frame, "size", 0) == 0 or rect is None:
        return

    x1, y1, x2, y2 = rect
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(
        frame,
        label,
        (x1, max(18, y1 - 6)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )


@dataclass
class DebugSnapshot:
    frame_path: str = ""
    frame_bgr: Optional[np.ndarray] = None
    annotated_bgr: Optional[np.ndarray] = None
    rois: Dict[str, np.ndarray] = field(default_factory=dict)
    visual_info: Dict[str, Any] = field(default_factory=dict)
    last_status_details: Dict[str, Any] = field(default_factory=dict)
    last_update_ts: float = 0.0
    detector_latency_ms: float = 0.0
    fps_loop: float = 0.0
    seek_active: bool = False
    raw_clock: str = "—"
    accepted_clock: str = "—"
    raw_score: str = "—"
    accepted_score: str = "—"
    countdown: str = "—"
    visual_state: str = "—"
    match_phase_text: str = "—"
    visual_confidence: float = 0.0
    banner_summary: str = "—"
    teams_text: str = "—"
    competition_text: str = "—"
    replay_text: str = "—"
    fim_jogo_text: str = "—"
    inicio_jogo_text: str = "—"


@dataclass
class MonitorRuntime:
    running: bool = False
    preparing: bool = False
    event_id: Optional[str] = None
    event_title: str = ""
    event_url: str = ""
    started_at: float = 0.0
    game_has_started: bool = False
    last_partial_report_t: float = 0.0
    partial_report_every_s: int = 600

    frames_seen: int = 0
    audio_seen: int = 0
    timeline_seen: int = 0

    last_clock: Optional[str] = None
    last_score: Optional[str] = None
    last_phase: str = "—"
    last_context: str = "—"
    last_context_summary: str = "—"
    last_event: str = "—"

    current_match_display: str = "—"
    current_competition: str = "—"
    current_team_a: str = "—"
    current_team_b: str = "—"

    detector_fps: float = 0.0
    detector_latency_ms: float = 0.0
    last_seek_state: str = "—"
    last_visual_confidence: float = 0.0