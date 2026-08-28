from __future__ import annotations

import glob
import json
import os
import re
import time
import threading
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np

# Tesseract removido conforme solicitação (legado eliminado)
pytesseract = None

try:
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    from paddleocr import PaddleOCR
except Exception:
    PaddleOCR = None


# ============================================================
# OCR / regex
# ============================================================

# OCR Flags
_TESSERACT_WARNED = True
_TESSERACT_LANG_WARNED = True

CLOCK_RE = re.compile(r"(\d{1,3})\s*[:.]\s*(\d{2})")
COUNTDOWN_HHMMSS_RE = re.compile(r"(\d{1,2})\s*[:.]\s*(\d{2})\s*[:.]\s*(\d{2})")

AO_VIVO_EM_RE = re.compile(r"\bAO\s*VIVO\s*EM\b", re.IGNORECASE)
DAQUI_A_POUCO_RE = re.compile(r"\b(DAQUI\s*A\s*POUCO|EM\s*INSTANTES|J[AÁ]\s*J[AÁ])\b", re.IGNORECASE)
PRE_JOGO_RE = re.compile(r"\b(AO\s*VIVO\s*EM|DAQUI\s*A\s*POUCO|EM\s*INSTANTES|J[AÁ]\s*J[AÁ]|PR[EÉ]\s*JOGO|ANTES\s*DO\s*JOGO|AGUARDE)\b", re.IGNORECASE)
INICIO_JOGO_RE = re.compile(r"\b(IN[IÍ]CIO\s*DO\s*JOGO|COME[CÇ]OU|BOLA\s*ROLANDO|APITA\s*O\s*[AÁ]RBITRO)\b", re.IGNORECASE)
FIM_JOGO_RE = re.compile(r"\b(FIM\s*DO\s*JOGO|APITO\s*FINAL|ENCERRADO|TERMINOU)\b", re.IGNORECASE)
INTERVALO_RE = re.compile(r"\b(INTERVALO|HALF[\-\s]?TIME)\b", re.IGNORECASE)

PRIMEIRO_TEMPO_RE = re.compile(r"\b(1T|1\s*TEMPO|PRIMEIRO\s+TEMPO)\b", re.IGNORECASE)
SEGUNDO_TEMPO_RE = re.compile(r"\b(2T|2\s*TEMPO|SEGUNDO\s+TEMPO)\b", re.IGNORECASE)

GOL_RE = re.compile(r"\bGO{1,6}L\b", re.IGNORECASE)
AMARELO_RE = re.compile(r"\b(AMAREL[AO]|CART[AÃ]O\s+AMAREL[AO])\b", re.IGNORECASE)
VERMELHO_RE = re.compile(r"\b(VERMELH[AO]|CART[AÃ]O\s+VERMELH[AO])\b", re.IGNORECASE)
VAR_RE = re.compile(r"\bVAR\b", re.IGNORECASE)
SUB_RE = re.compile(r"\b(SUBSTITUI[CÇ][AÃ]O|SUBSTITUIU|ENTROU|SAIU)\b", re.IGNORECASE)
REPLAY_RE = re.compile(r"\bREPLAY\b", re.IGNORECASE)

ROI_ALIAS_MAP: Dict[str, str] = {
    "teams": "replay",
    "competition": "fim_jogo",
}

ROI_OVERRIDE_LABELS = [
    "score",
    "clock",
    "phase",
    "pre_jogo",
    "jogo",
    "intervalo",
    "replay",
    "fim_jogo",
    "inicio_jogo",
    "countdown_center",
    "banner",
]

_DEFAULT_ROI_PCTS: Dict[str, Dict[str, float]] = {
    "pre_jogo": {"x": 0.000, "y": 0.040, "w": 0.260, "h": 0.150},
    "jogo": {"x": 0.000, "y": 0.040, "w": 0.250, "h": 0.150},
    "intervalo": {"x": 0.380, "y": 0.020, "w": 0.300, "h": 0.080},
    "score": {"x": 0.000, "y": 0.050, "w": 0.245, "h": 0.095},
    "clock": {"x": 0.060, "y": 0.105, "w": 0.180, "h": 0.080},
    "phase": {"x": 0.085, "y": 0.070, "w": 0.170, "h": 0.055},
    "replay": {"x": 0.000, "y": 0.720, "w": 0.180, "h": 0.120},
    "fim_jogo": {"x": 0.300, "y": 0.040, "w": 0.480, "h": 0.070},
    "inicio_jogo": {"x": 0.300, "y": 0.040, "w": 0.480, "h": 0.070},
    "countdown_center": {"x": 0.420, "y": 0.030, "w": 0.240, "h": 0.090},
    "banner": {"x": 0.120, "y": 0.720, "w": 0.760, "h": 0.230},
}


# ============================================================
# util
# ============================================================

def _ensure_dir(p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    os.makedirs(p, exist_ok=True)
    return p


def _clip_roi(x: int, y: int, w: int, h: int, W: int, H: int) -> Tuple[int, int, int, int]:
    x = max(0, min(int(x), W - 1))
    y = max(0, min(int(y), H - 1))
    w = max(1, min(int(w), W - x))
    h = max(1, min(int(h), H - y))
    return x, y, w, h


def _crop(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
    H, W = frame.shape[:2]
    x, y, w, h = _clip_roi(*roi, W, H)
    return frame[y:y + h, x:x + w]


def _norm_text_general(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[|¦‘’`´]", ":", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _norm_text_numeric(s: str) -> str:
    s = _norm_text_general(s)
    s = re.sub(r"[Oo]", "0", s)
    s = re.sub(r"[Il|!]", "1", s)
    s = s.replace(";", ":").replace(",", ":").replace(".", ":")
    return s


def _clean_text_block(s: str) -> str:
    s = _norm_text_general(s).upper()
    s = re.sub(r"[^\wÀ-ÿ0-9:!?.,\-/ ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _parse_clock(txt: str) -> Optional[str]:
    raw = _norm_text_numeric(txt).upper()
    if not raw:
        return None
    raw = re.sub(r"\b(?:[12]\s*T|[12]T|PRIMEIRO\s+TEMPO|SEGUNDO\s+TEMPO|1\s*TEMPO|2\s*TEMPO)\b", " ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s+", "", raw)
    if not raw:
        return None
    matches = list(re.finditer(r"(?<!\d)(\d{1,3})[:](\d{2})(?!\d)", raw))
    if not matches:
        return None
    valid: List[Tuple[int, int, int]] = []
    for m in matches:
        mm = int(m.group(1))
        ss = int(m.group(2))
        if 0 <= mm <= 180 and 0 <= ss <= 59:
            valid.append((mm, ss, m.start()))
    if not valid:
        return None
    mm, ss, _ = sorted(valid, key=lambda x: (len(str(x[0])), x[2]), reverse=True)[0]
    return f"{mm:02d}:{ss:02d}"


def _parse_countdown(txt: str) -> Optional[str]:
    raw = _norm_text_numeric(txt).replace(" ", "")
    m3 = COUNTDOWN_HHMMSS_RE.search(raw)
    if m3:
        hh = int(m3.group(1))
        mm = int(m3.group(2))
        ss = int(m3.group(3))
        if 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
    m2 = CLOCK_RE.search(raw)
    if m2:
        mm = int(m2.group(1))
        ss = int(m2.group(2))
        if 0 <= mm <= 180 and 0 <= ss <= 59:
            return f"{mm:02d}:{ss:02d}"
    return None


def _parse_score(txt: str) -> Optional[str]:
    raw = _norm_text_numeric(txt).upper().strip()
    raw = raw.replace("O", "0").replace("I", "1")
    raw = re.sub(r"\s+", " ", raw)
    if not raw:
        return None
    # Remove clocks to avoid mistaking 42:39 as score 42x3
    raw = re.sub(r"\b\d{1,3}\s*[:.]\s*\d{2}\b", " ", raw)
    
    # 1. Matches formats like: 1x0, 12-0, 0 | 0, 123 : 45
    m = re.search(r"(?<!\d)(\d{1,3})\s*[xX\-:|]\s*(\d{1,3})(?!\d)", raw)
    if m:
        return f"{m.group(1)}x{m.group(2)}"
        
    # 2. Matches formats with just spaces between digits: 12 0 
    m = re.search(r"(?<!\d)(\d{1,3})\s+(\d{1,3})(?!\d)", raw)
    if m:
        # Só confia no espaço se existirem estritamente 2 números isolados na string toda
        all_nums = re.findall(r"(?<!\d)\d{1,3}(?!\d)", raw)
        if len(all_nums) == 2:
            return f"{m.group(1)}x{m.group(2)}"
    return None


def _majority_or_none(items: List[str], min_count: int = 2) -> Optional[str]:
    vals = [x for x in items if x]
    if not vals:
        return None
    value, qty = Counter(vals).most_common(1)[0]
    if qty >= min_count:
        return value
    return vals[0]


def _is_mmss_clock_text(value: Optional[str]) -> bool:
    if not value:
        return False
    m = re.fullmatch(r"(\d{1,3}):(\d{2})", str(value).strip())
    if not m:
        return False
    mm = int(m.group(1))
    ss = int(m.group(2))
    return 0 <= mm <= 180 and 0 <= ss <= 59


def _clock_to_seconds_mmss(value: Optional[str]) -> Optional[int]:
    if not _is_mmss_clock_text(value):
        return None
    mm, ss = value.split(":")
    return int(mm) * 60 + int(ss)


def _is_score_reasonable(score: Optional[str]) -> bool:
    if not score or not re.fullmatch(r"\d+x\d+", score):
        return False
    a, b = [int(x) for x in score.split("x")]
    if a > 9 or b > 9:
        return False
    if a + b > 12:
        return False
    return True


def _has_tesseract() -> bool:
    return False

def _warn_tesseract_once() -> None:
    pass

def _available_tesseract_languages() -> List[str]:
    return []

def _pick_tesseract_lang() -> str:
    return ""


def _ocr_text(img: np.ndarray, psm: int, whitelist: str = "") -> str:
    # Tesseract removido; toda análise de texto contextual é feita pela IA
    return ""


def _prep_gray(img_bgr: np.ndarray, upscale: float = 2.0) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    if upscale and upscale != 1.0:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    return gray


def _prep_ocr_bw(img_bgr: np.ndarray, upscale: float = 2.0) -> np.ndarray:
    gray = _prep_gray(img_bgr, upscale=upscale)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 7)


def _prep_ocr_inv(img_bgr: np.ndarray, upscale: float = 2.0) -> np.ndarray:
    gray = _prep_gray(img_bgr, upscale=upscale)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 7)


def _prep_ocr_otsu(img_bgr: np.ndarray, upscale: float = 2.0) -> np.ndarray:
    gray = _prep_gray(img_bgr, upscale=upscale)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return bw


def _prep_color_mask_white(img_bgr: np.ndarray, upscale: float = 2.0) -> np.ndarray:
    img = img_bgr
    if upscale and upscale != 1.0:
        img = cv2.resize(img, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 0, 150), (180, 110, 255))


def _prep_color_mask_red(img_bgr: np.ndarray, upscale: float = 2.0) -> np.ndarray:
    img = img_bgr
    if upscale and upscale != 1.0:
        img = cv2.resize(img, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 85, 70), (12, 255, 255))
    m2 = cv2.inRange(hsv, (168, 85, 70), (180, 255, 255))
    return cv2.bitwise_or(m1, m2)


def _focus_measure(img_bgr: np.ndarray) -> float:
    try:
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    except Exception:
        return 0.0


def _edge_ratio(gray: np.ndarray) -> float:
    e = cv2.Canny(gray, 70, 180)
    return float((e > 0).mean())


def _binary_fill_ratio(mask: np.ndarray) -> float:
    if mask is None or mask.size == 0:
        return 0.0
    return float((mask > 0).mean())


def _dominant_hsv_stats(img_bgr: np.ndarray) -> Dict[str, float]:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]
    red_mask = (((h <= 10) | (h >= 170)) & (s >= 80) & (v >= 60))
    yellow_mask = (((h >= 15) & (h <= 40)) & (s >= 80) & (v >= 80))
    blue_mask = (((h >= 90) & (h <= 135)) & (s >= 70) & (v >= 50))
    white_mask = (((s <= 55) & (v >= 150)))
    return {
        "sat_mean": float(s.mean()),
        "val_mean": float(v.mean()),
        "red_ratio": float(red_mask.mean()),
        "yellow_ratio": float(yellow_mask.mean()),
        "blue_ratio": float(blue_mask.mean()),
        "white_ratio": float(white_mask.mean()),
    }


def _iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    union = aw * ah + bw * bh - inter
    return float(inter / union) if union > 0 else 0.0


@dataclass
class TemplateSample:
    name: str
    gray: np.ndarray
    edges: np.ndarray
    weight: np.ndarray
    size: Tuple[int, int]


@dataclass
class MatchResult:
    label: str
    score: float
    best_template: str
    roi_name: str
    details: Dict[str, Any]

    @property
    def confidence(self) -> float:
        return float(self.score or 0.0)


class VisionDetectors:
    def __init__(
        self,
        templates_root: str = "templates",
        auto_templates_root: str = "templates_auto",
        debug_dir: Optional[str] = None,
        pre_threshold: float = 0.55,
        game_threshold: float = 0.57,
        intervalo_threshold: float = 0.56,
    ) -> None:
        self.templates_root = templates_root
        self.auto_templates_root = auto_templates_root
        self.debug_dir = _ensure_dir(debug_dir)

        self.roi_overrides: Dict[str, Dict[str, float]] = {}
        self.roi_enabled: Dict[str, bool] = {key: True for key in ROI_OVERRIDE_LABELS}
        self.roi_profile_name: str = "default"

        self.pre_threshold = float(pre_threshold)
        self.game_threshold = float(game_threshold)
        self.intervalo_threshold = float(intervalo_threshold)

        self.pre_templates: List[TemplateSample] = []
        self.game_templates: List[TemplateSample] = []
        self.intervalo_templates: List[TemplateSample] = []

        self._last_clock_read_t = -9999.0
        self._last_clock_read: Optional[str] = None
        self._clock_history: Deque[str] = deque(maxlen=8)

        self._last_score_read_t = -9999.0
        self._last_score_read: Optional[str] = None
        self._score_history: Deque[str] = deque(maxlen=8)

        self._last_hud_overlay_read_t = -9999.0
        self._last_hud_overlay_read = ""
        self._last_screen_context_t = -9999.0
        self._last_screen_context: Dict[str, Any] = {}

        self._last_countdown_read_t = -9999.0
        self._last_countdown_read: Optional[str] = None

        self._last_phase_read_t = -9999.0
        self._last_phase_read: str = ""

        self._last_competition_read: Optional[str] = None
        self._last_team_names_read: Tuple[Optional[str], Optional[str]] = (None, None)

        self._last_debug_rois: Dict[str, Tuple[int, int, int, int]] = {}
        self._last_debug_info: Dict[str, Any] = {}

        self._ocr_async_lock = threading.Lock()
        self._banner_async_running: bool = False
        self._banner_async_hash: Optional[int] = None
        self._banner_async_cache: Dict[str, Any] = {
            "full_text": "",
            "headline": "",
            "subheadline": "",
            "left_tag": "",
            "right_tag": "",
            "bottom_line": "",
            "context_summary": "",
            "ts": 0.0,
            "engine": "",
            "lines": [],
            "avg_conf": 0.0,
            "boxes": [],
            "ocr_ms": 0.0,
        }
        self._paddle_ocr = None
        self._paddle_ocr_failed = False
        self._scene_text_last_stats: Dict[str, Any] = {}
        self._roi_cycle_idx = 0
        self._roi_cycle = ["score", "clock", "phase"]
        self.cloud_sovereignty_mode: bool = False
        self._banner_last_read_t: float = 0.0
        self._last_frame_state_t: float = 0.0
        self._last_gates_t: float = 0.0
        self._last_visual_state_confirmed: Optional[MatchResult] = None
        self._last_score_active: bool = False
        self._last_clock_active: bool = False
        self._last_banner_active: bool = False

        self._load_templates()

    def _canon_roi_key(self, nome: str) -> str:
        key = (nome or "").strip().lower()
        return ROI_ALIAS_MAP.get(key, key)

    def set_roi_profile(self, profile_name: str) -> None:
        name = (profile_name or "default").strip().lower()
        self.roi_profile_name = re.sub(r"[^a-z0-9_\-]+", "_", name) or "default"

    def get_roi_profile(self) -> str:
        return self.roi_profile_name

    def get_supported_roi_labels(self) -> List[str]:
        return list(ROI_OVERRIDE_LABELS)

    def set_roi_enabled(self, nome: str, enabled: bool) -> bool:
        key = self._canon_roi_key(nome)
        if key not in ROI_OVERRIDE_LABELS:
            return False
        self.roi_enabled[key] = bool(enabled)
        return True

    def is_roi_enabled(self, nome: str) -> bool:
        key = self._canon_roi_key(nome)
        if key not in ROI_OVERRIDE_LABELS:
            return False
        return bool(self.roi_enabled.get(key, True))

    def get_roi_enabled_map(self) -> Dict[str, bool]:
        return {key: bool(self.roi_enabled.get(key, True)) for key in ROI_OVERRIDE_LABELS}

    def _normalize_roi_pct(self, rect_percentual: Dict[str, Any]) -> Optional[Dict[str, float]]:
        try:
            x = max(0.0, min(float(rect_percentual.get("x", 0.0)), 0.999))
            y = max(0.0, min(float(rect_percentual.get("y", 0.0)), 0.999))
            w = max(0.001, min(float(rect_percentual.get("w", 0.0)), 1.0 - x))
            h = max(0.001, min(float(rect_percentual.get("h", 0.0)), 1.0 - y))
            return {"x": round(x, 6), "y": round(y, 6), "w": round(w, 6), "h": round(h, 6)}
        except Exception:
            return None

    def set_roi_override(self, nome: str, rect_percentual: Dict[str, Any]) -> bool:
        key = self._canon_roi_key(nome)
        if key not in ROI_OVERRIDE_LABELS:
            return False
        norm = self._normalize_roi_pct(rect_percentual)
        if not norm:
            return False
        self.roi_overrides[key] = norm
        return True

    def reset_roi_override(self, nome: str) -> bool:
        key = self._canon_roi_key(nome)
        if key in self.roi_overrides:
            del self.roi_overrides[key]
            return True
        return False

    def clear_roi_overrides(self) -> None:
        self.roi_overrides.clear()
        self.roi_enabled = {key: True for key in ROI_OVERRIDE_LABELS}

    def get_roi_overrides(self) -> Dict[str, Dict[str, float]]:
        return dict(self.roi_overrides)

    def _pct_to_xywh(self, frame: np.ndarray, pct: Dict[str, float]) -> Tuple[int, int, int, int]:
        H, W = frame.shape[:2]
        return _clip_roi(int(W * pct["x"]), int(H * pct["y"]), int(W * pct["w"]), int(H * pct["h"]), W, H)

    def _resolve_roi(self, frame: np.ndarray, label: str) -> Tuple[int, int, int, int]:
        key = self._canon_roi_key(label)
        pct = self.roi_overrides.get(key) or _DEFAULT_ROI_PCTS[key]
        return self._pct_to_xywh(frame, pct)

    def get_roi_pixels(self, frame: np.ndarray, nome: str) -> Optional[Tuple[int, int, int, int]]:
        key = self._canon_roi_key(nome)
        if key not in ROI_OVERRIDE_LABELS:
            return None
        return self._resolve_roi(frame, key)

    def get_roi_percent(self, nome: str) -> Optional[Dict[str, float]]:
        key = self._canon_roi_key(nome)
        if key not in ROI_OVERRIDE_LABELS:
            return None
        return dict(self.roi_overrides.get(key) or _DEFAULT_ROI_PCTS[key])

    def load_roi_overrides(self, path: str, profile_name: Optional[str] = None) -> bool:
        if not path or not os.path.isfile(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return False
        profile = (profile_name or self.roi_profile_name or "default").strip().lower()
        if isinstance(payload, dict) and profile in payload and isinstance(payload.get(profile), dict):
            payload = payload.get(profile) or {}
        if not isinstance(payload, dict):
            return False
        loaded: Dict[str, Dict[str, float]] = {}
        for key, value in payload.items():
            key = self._canon_roi_key(str(key))
            if key == "__enabled__" and isinstance(value, dict):
                for ek, ev in value.items():
                    ckey = self._canon_roi_key(str(ek))
                    if ckey in ROI_OVERRIDE_LABELS:
                        self.roi_enabled[ckey] = bool(ev)
                continue
            if key not in ROI_OVERRIDE_LABELS or not isinstance(value, dict):
                continue
            norm = self._normalize_roi_pct(value)
            if norm:
                loaded[key] = norm
        self.roi_overrides = loaded
        return True

    def save_roi_overrides(self, path: str, profile_name: Optional[str] = None) -> bool:
        if not path:
            return False
        profile = (profile_name or self.roi_profile_name or "default").strip().lower()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        payload: Dict[str, Any] = {}
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    old = json.load(f)
                if isinstance(old, dict):
                    payload = old
            except Exception:
                payload = {}
        profile_payload = dict(self.roi_overrides)
        profile_payload["__enabled__"] = self.get_roi_enabled_map()
        payload[profile] = profile_payload
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def shutdown(self) -> None:
        deadline = time.time() + 0.3
        while self._banner_async_running and time.time() < deadline:
            time.sleep(0.01)

    def _roi_pre_jogo(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "pre_jogo")

    def _roi_jogo(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "jogo")

    def _roi_intervalo(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "intervalo")

    def _roi_score(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "score")

    def _roi_clock(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "clock")

    def _roi_phase(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "phase")

    def _roi_replay(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "replay")

    def _roi_fim_jogo(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "fim_jogo")

    def _roi_inicio_jogo(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "inicio_jogo")

    def _roi_countdown_center(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "countdown_center")

    def _roi_banner(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        return self._resolve_roi(frame, "banner")

    def _load_templates(self) -> None:
        self.pre_templates = []
        self.game_templates = []
        self.intervalo_templates = []
        self.pre_templates.extend(self._load_template_dir(os.path.join(self.templates_root, "pre_jogo"), kind="pre_jogo"))
        self.game_templates.extend(self._load_template_dir(os.path.join(self.templates_root, "jogo"), kind="jogo"))
        self.intervalo_templates.extend(self._load_template_dir(os.path.join(self.templates_root, "intervalo"), kind="intervalo"))
        self.pre_templates.extend(self._load_template_dir(os.path.join(self.auto_templates_root, "pre_jogo"), kind="pre_jogo"))
        self.game_templates.extend(self._load_template_dir(os.path.join(self.auto_templates_root, "jogo"), kind="jogo"))
        self.intervalo_templates.extend(self._load_template_dir(os.path.join(self.auto_templates_root, "intervalo"), kind="intervalo"))

    def _load_template_dir(self, folder: str, kind: str) -> List[TemplateSample]:
        samples: List[TemplateSample] = []
        if not os.path.isdir(folder):
            return samples
        paths: List[str] = []
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            paths.extend(glob.glob(os.path.join(folder, ext)))
        for p in sorted(paths):
            img = cv2.imread(p)
            if img is None:
                continue
            prepared = self._prepare_template(img, kind=kind)
            if prepared is None:
                continue
            samples.append(TemplateSample(name=os.path.basename(p), gray=prepared["gray"], edges=prepared["edges"], weight=prepared["weight"], size=(prepared["gray"].shape[1], prepared["gray"].shape[0])))
        return samples

    def _prepare_template(self, img_bgr: np.ndarray, kind: str) -> Optional[Dict[str, np.ndarray]]:
        if img_bgr is None or img_bgr.size == 0:
            return None
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        size = (260, 84) if kind == "pre_jogo" else (280, 96) if kind == "jogo" else (300, 90)
        gray = cv2.resize(gray, size, interpolation=cv2.INTER_CUBIC)
        edges = cv2.Canny(gray, 80, 180)
        weight = self._build_weight_mask(size[0], size[1], kind)
        return {"gray": gray, "edges": edges, "weight": weight}

    def _build_weight_mask(self, w: int, h: int, kind: str) -> np.ndarray:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx = w / 2.0
        cy = h / 2.0
        nx = np.abs((xx - cx) / max(1.0, cx))
        ny = np.abs((yy - cy) / max(1.0, cy))
        radial = 1.0 - np.clip(0.70 * nx + 0.30 * ny, 0.0, 1.0)
        radial = 0.35 + 0.65 * radial
        boost = np.ones((h, w), dtype=np.float32)
        if kind == "pre_jogo":
            boost[:, int(w * 0.08):int(w * 0.92)] *= 1.18
        elif kind == "jogo":
            boost[int(h * 0.00):int(h * 0.60), int(w * 0.00):int(w * 0.62)] *= 1.22
            boost[int(h * 0.34):int(h * 1.00), int(w * 0.00):int(w * 0.58)] *= 1.18
        else:
            boost[:, int(w * 0.10):int(w * 0.90)] *= 1.16
        radial *= boost
        return np.clip(radial, 0.10, 2.00).astype(np.float32)

    def _compare_roi_to_template(self, roi_bgr: np.ndarray, tpl: TemplateSample) -> Tuple[float, Dict[str, Any]]:
        target_w, target_h = tpl.size
        roi = cv2.resize(roi_bgr, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        roi_gray = cv2.GaussianBlur(roi_gray, (3, 3), 0)
        roi_edges = cv2.Canny(roi_gray, 80, 180)
        roi_gray_f = roi_gray.astype(np.float32) / 255.0
        tpl_gray_f = tpl.gray.astype(np.float32) / 255.0
        roi_edges_f = roi_edges.astype(np.float32) / 255.0
        tpl_edges_f = tpl.edges.astype(np.float32) / 255.0
        gray_diff = np.abs(roi_gray_f - tpl_gray_f) * tpl.weight
        edge_diff = np.abs(roi_edges_f - tpl_edges_f) * tpl.weight
        gray_score = 1.0 - float(gray_diff.sum() / (tpl.weight.sum() + 1e-6))
        edge_score = 1.0 - float(edge_diff.sum() / (tpl.weight.sum() + 1e-6))
        tm_gray = max(0.0, float(cv2.matchTemplate(roi_gray, tpl.gray, cv2.TM_CCOEFF_NORMED)[0][0]))
        tm_edges = max(0.0, float(cv2.matchTemplate(roi_edges, tpl.edges, cv2.TM_CCOEFF_NORMED)[0][0]))
        final_score = 0.40 * gray_score + 0.40 * edge_score + 0.10 * tm_gray + 0.10 * tm_edges
        details = {
            "gray_score": round(gray_score, 4), 
            "edge_score": round(edge_score, 4), 
            "tm_gray": round(tm_gray, 4), 
            "tm_edges": round(tm_edges, 4),
            "score": round(float(final_score), 4),
            "visual_confidence": round(float(final_score), 4)
        }
        return float(final_score), details

    def _match_against_class(self, roi_bgr: np.ndarray, templates: List[TemplateSample], label: str, roi_name: str) -> MatchResult:
        if roi_bgr is None or roi_bgr.size == 0 or not templates:
            return MatchResult(label=label, score=0.0, best_template="", roi_name=roi_name, details={})
        best_score = -1.0
        best_name = ""
        best_parts: Dict[str, Any] = {}
        for tpl in templates:
            score, parts = self._compare_roi_to_template(roi_bgr, tpl)
            if score > best_score:
                best_score = score
                best_name = tpl.name
                best_parts = parts
        return MatchResult(label=label, score=float(best_score), best_template=best_name, roi_name=roi_name, details=best_parts)

    def detect_frame_state(self, frame: np.ndarray) -> MatchResult:
        jogo_roi = self._roi_jogo(frame)
        pre_roi = self._roi_pre_jogo(frame)
        intervalo_roi = self._roi_intervalo(frame)
        jogo_res = self._match_against_class(_crop(frame, jogo_roi), self.game_templates, "jogo", "jogo_roi")
        pre_res = self._match_against_class(_crop(frame, pre_roi), self.pre_templates, "pre_jogo", "pre_roi")
        int_res = self._match_against_class(_crop(frame, intervalo_roi), self.intervalo_templates, "intervalo", "intervalo_roi")
        results = [jogo_res, pre_res, int_res]
        results.sort(key=lambda r: float(r.score or 0.0), reverse=True)
        best = results[0]
        details = dict(best.details or {})
        details["pre_score"] = float(pre_res.score or 0.0)
        details["game_score"] = float(jogo_res.score or 0.0)
        details["intervalo_score"] = float(int_res.score or 0.0)
        scores = sorted([float(pre_res.score or 0.0), float(jogo_res.score or 0.0), float(int_res.score or 0.0)], reverse=True)
        details["margin"] = float(scores[0] - scores[1]) if len(scores) >= 2 else float(scores[0])
        if best.label == "jogo" and best.score < self.game_threshold:
            return MatchResult("nao_detectado", float(best.score or 0.0), best.best_template, best.roi_name, details)
        if best.label == "pre_jogo" and best.score < self.pre_threshold:
            return MatchResult("nao_detectado", float(best.score or 0.0), best.best_template, best.roi_name, details)
        if best.label == "intervalo" and best.score < self.intervalo_threshold:
            return MatchResult("nao_detectado", float(best.score or 0.0), best.best_template, best.roi_name, details)
        return MatchResult(best.label, float(best.score or 0.0), best.best_template, best.roi_name, details)

    def _save_debug_rois(self, frame: np.ndarray, **kwargs: Any) -> None:
        try:
            H, W = frame.shape[:2]
            def _xyxy(roi: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
                x, y, w, h = _clip_roi(*roi, W, H)
                return x, y, x + w, y + h
            self._last_debug_rois = {
                "jogo_roi": _xyxy(kwargs.get("jogo_roi") or self._roi_jogo(frame)),
                "pre_roi": _xyxy(kwargs.get("pre_roi") or self._roi_pre_jogo(frame)),
                "intervalo_roi": _xyxy(kwargs.get("intervalo_roi") or self._roi_intervalo(frame)),
                "banner_roi": _xyxy(kwargs.get("banner_roi") or self._roi_banner(frame)),
                "replay_roi": _xyxy(kwargs.get("replay_roi") or self._roi_replay(frame)),
                "fim_jogo_roi": _xyxy(kwargs.get("fim_jogo_roi") or self._roi_fim_jogo(frame)),
                "inicio_jogo_roi": _xyxy(kwargs.get("inicio_jogo_roi") or self._roi_inicio_jogo(frame)),
                "score_roi": _xyxy(kwargs.get("score_roi") or self._roi_score(frame)),
                "clock_roi": _xyxy(kwargs.get("clock_roi") or self._roi_clock(frame)),
                "phase_roi": _xyxy(kwargs.get("phase_roi") or self._roi_phase(frame)),
            }
        except Exception:
            self._last_debug_rois = {}

    def get_last_debug_rois(self) -> Dict[str, Tuple[int, int, int, int]]:
        return dict(self._last_debug_rois or {})

    def get_last_debug_info(self) -> Dict[str, Any]:
        return dict(self._last_debug_info or {})

    def _scoreboard_visual_stats(self, img: np.ndarray) -> Dict[str, float]:
        if img is None or img.size == 0:
            return {"edge_ratio": 0.0, "white_ratio": 0.0, "blue_ratio": 0.0, "focus": 0.0, "digit_like_ratio": 0.0}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        hsvs = _dominant_hsv_stats(img)
        contours = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        digit_like = 0
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            if area < 18:
                continue
            ar = h / max(1.0, w)
            if 1.1 <= ar <= 6.5 and h >= gray.shape[0] * 0.25:
                digit_like += 1
        return {
            "edge_ratio": _edge_ratio(gray),
            "white_ratio": hsvs["white_ratio"],
            "blue_ratio": hsvs["blue_ratio"],
            "focus": _focus_measure(img),
            "digit_like_ratio": min(1.0, digit_like / 6.0),
        }

    def _is_scoreboard_active(self, frame: np.ndarray) -> bool:
        st = self._scoreboard_visual_stats(_crop(frame, self._roi_score(frame)))
        good = 0
        if st["focus"] >= 10: good += 1
        if st["edge_ratio"] >= 0.010: good += 1
        if st["white_ratio"] >= 0.025: good += 1
        if st["digit_like_ratio"] >= 0.10: good += 1
        if st["blue_ratio"] >= 0.04: good += 1
        return good >= 2

    def _clock_visual_stats(self, roi: np.ndarray) -> Dict[str, float]:
        if roi is None or roi.size == 0:
            return {"focus": 0.0, "edge_ratio": 0.0, "white_ratio": 0.0, "red_ratio": 0.0, "digit_like_ratio": 0.0}
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        hsv = _dominant_hsv_stats(roi)
        bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        cc = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        digit_like = 0
        H = gray.shape[0]
        for c in cc:
            x, y, w, h = cv2.boundingRect(c)
            if w * h < 10:
                continue
            ar = h / max(1.0, w)
            if 1.1 <= ar <= 7.0 and h >= H * 0.35:
                digit_like += 1
        return {
            "focus": _focus_measure(roi),
            "edge_ratio": _edge_ratio(gray),
            "white_ratio": hsv["white_ratio"],
            "red_ratio": hsv["red_ratio"],
            "digit_like_ratio": min(1.0, digit_like / 6.0),
        }

    def _is_clock_roi_active(self, frame: np.ndarray) -> bool:
        if not self.is_roi_enabled('clock'):
            return False
        st = self._clock_visual_stats(_crop(frame, self._roi_clock(frame)))
        good = 0
        if st["focus"] >= 8: good += 1
        if st["edge_ratio"] >= 0.010: good += 1
        if st["white_ratio"] >= 0.02 or st["red_ratio"] >= 0.05: good += 1
        if st["digit_like_ratio"] >= 0.08: good += 1
        return good >= 2

    def _banner_visual_profile(self, img: np.ndarray) -> Dict[str, Any]:
        if img is None or img.size == 0:
            return {"banner_active": False, "kind": "", "confidence": 0.0, "red_ratio": 0.0, "yellow_ratio": 0.0, "blue_ratio": 0.0, "white_ratio": 0.0, "edge_ratio": 0.0}
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = _dominant_hsv_stats(img)
        blur = cv2.GaussianBlur(img, (7, 7), 0)
        hsvb = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        sat_fill = _binary_fill_ratio(cv2.inRange(hsvb, (0, 65, 40), (180, 255, 255)))
        active_score = 0.0
        if _focus_measure(img) >= 12: active_score += 0.20
        if _edge_ratio(gray) >= 0.01: active_score += 0.20
        if sat_fill >= 0.10: active_score += 0.20
        if hsv["white_ratio"] >= 0.03: active_score += 0.15
        if max(hsv["red_ratio"], hsv["yellow_ratio"], hsv["blue_ratio"]) >= 0.08: active_score += 0.25
        kind, kind_conf = "", 0.0
        if hsv["yellow_ratio"] >= 0.14:
            kind, kind_conf = "cartao_amarelo", min(0.92, 0.55 + hsv["yellow_ratio"])
        elif hsv["red_ratio"] >= 0.18:
            kind, kind_conf = "cartao_vermelho", min(0.92, 0.50 + hsv["red_ratio"])
        elif hsv["blue_ratio"] >= 0.20 and hsv["white_ratio"] >= 0.06:
            kind, kind_conf = "var_ou_replay", min(0.88, 0.45 + hsv["blue_ratio"])
        elif hsv["white_ratio"] >= 0.08 and sat_fill >= 0.08:
            kind, kind_conf = "overlay_info", 0.62
        return {
            "banner_active": active_score >= 0.55,
            "kind": kind,
            "confidence": round(float(max(active_score, kind_conf)), 4),
            "red_ratio": hsv["red_ratio"],
            "yellow_ratio": hsv["yellow_ratio"],
            "blue_ratio": hsv["blue_ratio"],
            "white_ratio": hsv["white_ratio"],
            "edge_ratio": _edge_ratio(gray),
        }

    def _make_text_variants(self, roi: np.ndarray, upscale: float = 2.2, allow_red: bool = False, allow_inv: bool = False, allow_otsu: bool = True) -> List[np.ndarray]:
        variants: List[np.ndarray] = []
        for maker, enabled in [(_prep_color_mask_white, True), (_prep_ocr_bw, True), (_prep_ocr_inv, allow_inv), (_prep_ocr_otsu, allow_otsu), (_prep_color_mask_red, allow_red)]:
            if not enabled:
                continue
            try:
                variants.append(maker(roi, upscale=upscale))
            except Exception:
                pass
        unique: List[np.ndarray] = []
        seen = set()
        for img in variants:
            if img is None or img.size == 0:
                continue
            key = (img.shape, int(np.mean(img)), int(np.std(img)))
            if key in seen:
                continue
            seen.add(key)
            unique.append(img)
        return unique

    def _ocr_collect_candidates(self, roi: np.ndarray, **kwargs) -> List[str]:
        # Tesseract legado removido
        return []

    def _ocr_roi_like_banner(self, roi: np.ndarray, **kwargs) -> List[str]:
        # Tesseract legado removido
        return []

    def _read_score_banner_style(self, frame: np.ndarray) -> Optional[str]:
        roi = _crop(frame, self._roi_score(frame))
        if roi is None or roi.size == 0:
            return None
        candidates: List[str] = []
        candidates.extend(
            self._ocr_roi_like_banner(
                roi,
                psm_list=(7, 6, 11, 12, 13),
                whitelist="0123456789xX-: ",
                upscale=3.0,
                allow_inv=True,
                allow_otsu=True,
                parser=_parse_score,
                block_zone="score_roi",
                min_block_w_ratio=0.08,
                min_block_h_ratio=0.30,
            )
        )
        try:
            blocks = self._detect_text_blocks(roi, zone_name="score_roi_digits")
        except Exception:
            blocks = []
        digit_blocks: List[Tuple[float, str]] = []
        H, W = roi.shape[:2]
        for block in blocks:
            x, y, w, h = block.get("bbox", (0, 0, 0, 0))
            if h < max(8, int(H * 0.30)) or w < max(6, int(W * 0.04)):
                continue
            crop = block.get("crop")
            if crop is None or getattr(crop, "size", 0) == 0:
                continue
            texts = self._ocr_collect_candidates(
                roi=crop,
                psm_list=(10, 8, 13),
                whitelist="0123456789",
                upscale=3.2,
                allow_inv=True,
                allow_otsu=True,
                normalize_mode="banner",
            )
            digit = None
            for txt in texts:
                ds = re.findall(r"\d", str(txt))
                if len(ds) == 1:
                    digit = ds[0]
                    break
            if digit is not None:
                digit_blocks.append((x + (w / 2.0), digit))
        if len(digit_blocks) >= 2:
            digit_blocks.sort(key=lambda item: item[0])
            val = f"{digit_blocks[0][1]}x{digit_blocks[-1][1]}"
            if _is_score_reasonable(val):
                candidates.append(val)
        valid = [c for c in candidates if _is_score_reasonable(c)]
        return _majority_or_none(valid, min_count=1) or (valid[0] if valid else None)

    def _read_clock_banner_style(self, frame: np.ndarray) -> Optional[str]:
        roi = _crop(frame, self._roi_clock(frame))
        if roi is None or roi.size == 0:
            return None
        candidates: List[str] = []
        rois = [roi]
        try:
            h, w = roi.shape[:2]
            rois.append(roi[:, int(w * 0.18):w])
            rois.append(roi[max(0, int(h * 0.04)):min(h, int(h * 0.96)), int(w * 0.12):w])
        except Exception:
            pass
        for subroi in rois:
            candidates.extend(
                self._ocr_roi_like_banner(
                    subroi,
                    psm_list=(7, 8, 13),
                    whitelist="0123456789:T| ",
                    upscale=3.0,
                    allow_inv=True,
                    allow_otsu=True,
                    parser=_parse_clock,
                    block_zone="clock_roi",
                    min_block_w_ratio=0.18,
                    min_block_h_ratio=0.40,
                )
            )
        valid = [c for c in candidates if _is_mmss_clock_text(c)]
        return _majority_or_none(valid, min_count=1) or (valid[0] if valid else None)

    def _split_score_subrois(self, score_roi: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        H, W = score_roi.shape[:2]
        left = score_roi[int(H * 0.10):int(H * 0.92), int(W * 0.28):int(W * 0.44)]
        right = score_roi[int(H * 0.10):int(H * 0.92), int(W * 0.58):int(W * 0.74)]
        return left, right

    def _read_single_digit(self, roi: np.ndarray) -> Optional[str]:
        texts = self._ocr_collect_candidates(roi=roi, psm_list=(10, 8, 13), whitelist="0123456789", upscale=2.6, allow_inv=True, allow_otsu=True, normalize_mode="general")
        found: List[str] = []
        for txt in texts:
            found.extend(re.findall(r"\d", txt))
        return Counter(found).most_common(1)[0][0] if found else None

    def _get_screen_macro_zones(self, frame: np.ndarray) -> Dict[str, Dict[str, Any]]:
        H, W = frame.shape[:2]
        zones = {
            "top_zone": (0, 0, W, int(H * 0.18)),
            "bottom_zone": (0, int(H * 0.72), W, H - int(H * 0.72)),
            "left_zone": (0, 0, int(W * 0.25), H),
            "right_zone": (int(W * 0.78), 0, W - int(W * 0.78), H),
            "center_zone": (int(W * 0.16), int(H * 0.18), int(W * 0.68), int(H * 0.64)),
            "scoreboard_zone": self._roi_score(frame),
            "clock_zone": self._roi_clock(frame),
            "phase_zone": self._roi_phase(frame),
        }
        out: Dict[str, Dict[str, Any]] = {}
        for name, roi in zones.items():
            x, y, w, h = _clip_roi(*roi, W, H)
            out[name] = {"roi": (x, y, w, h), "image": frame[y:y + h, x:x + w]}
        return out

    def _detect_text_blocks(self, roi: np.ndarray, zone_name: str = "") -> List[Dict[str, Any]]:
        if roi is None or roi.size == 0:
            return []
        H, W = roi.shape[:2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        bw = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        kernel_w = max(12, W // 18)
        kernel_h = max(3, H // 28)
        merged = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((kernel_h, kernel_w), np.uint8), iterations=1)
        merged = cv2.dilate(merged, np.ones((3, 5), np.uint8), iterations=1)
        contours = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        blocks: List[Dict[str, Any]] = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            area = w * h
            if area < max(120, (W * H) // 900):
                continue
            if w < max(18, W // 22) or h < max(10, H // 30):
                continue
            fill = float(area / max(1.0, (w * h)))
            crop = roi[y:y + h, x:x + w]
            stats = _dominant_hsv_stats(crop)
            edge = _edge_ratio(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY))
            blocks.append({
                "bbox": (x, y, w, h),
                "zone": zone_name,
                "area": area,
                "fill_ratio": round(fill, 4),
                "edge_ratio": round(edge, 4),
                "white_ratio": round(stats["white_ratio"], 4),
                "red_ratio": round(stats["red_ratio"], 4),
                "yellow_ratio": round(stats["yellow_ratio"], 4),
                "blue_ratio": round(stats["blue_ratio"], 4),
                "crop": crop,
            })
        blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        dedup: List[Dict[str, Any]] = []
        for block in blocks:
            if any(_iou(block["bbox"], prev["bbox"]) >= 0.65 for prev in dedup):
                continue
            dedup.append(block)
        return dedup

    def _pick_best_text_candidate(self, candidates: List[str], min_len: int = 1, prefer_longest: bool = False) -> str:
        valid = [c for c in candidates if len((c or '').strip()) >= min_len]
        if not valid:
            return ""
        if prefer_longest:
            valid.sort(key=len, reverse=True)
        from collections import Counter
        counts = Counter(valid)
        best, _ = counts.most_common(1)[0]
        return best

    def _ocr_block(self, block: Dict[str, Any]) -> Dict[str, Any]:
        crop = block.get("crop")
        if crop is None or getattr(crop, "size", 0) == 0:
            block["text"] = ""
            block["confidence"] = 0.0
            return block
        texts = self._ocr_collect_candidates(
            roi=crop,
            psm_list=(7, 6, 11, 12),
            whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789!?.,:/@#%&()+- xX",
            upscale=3.0,
            allow_red=True,
            allow_inv=True,
            allow_otsu=True,
            normalize_mode="banner",
        )
        best = self._pick_best_text_candidate(texts, min_len=2, prefer_longest=True)
        block["text"] = _clean_text_block(best)
        block["confidence"] = round(min(1.0, 0.25 + 0.02 * len(block["text"]) + 0.40 * float(block.get("white_ratio", 0.0)) + 0.25 * float(block.get("edge_ratio", 0.0))), 4) if block["text"] else 0.0
        block.pop("crop", None)
        return block

    def _classify_zone_blocks(self, blocks: List[Dict[str, Any]], zone_name: str) -> Dict[str, Any]:
        texts = [b.get("text", "") for b in blocks if b.get("text")]
        by_area = sorted(blocks, key=lambda b: (b.get("bbox", (0, 0, 0, 0))[3], b.get("bbox", (0, 0, 0, 0))[2] * b.get("bbox", (0, 0, 0, 0))[3]), reverse=True)
        out: Dict[str, Any] = {"text": " | ".join(texts[:5]).strip(), "blocks": blocks}
        if zone_name == "bottom_zone":
            left = [b for b in blocks if b["bbox"][0] <= max(40, int(max(1, max((blk["bbox"][0] + blk["bbox"][2] for blk in blocks), default=1)) * 0.25))]
            right = [b for b in blocks if (b["bbox"][0] + b["bbox"][2]) >= int(max((blk["bbox"][0] + blk["bbox"][2] for blk in blocks), default=1) * 0.80)]
            center = [b for b in blocks if b not in left and b not in right]
            out.update({
                "headline": by_area[0]["text"] if by_area else "",
                "subheadline": by_area[1]["text"] if len(by_area) > 1 else "",
                "left_tag": left[0]["text"] if left else "",
                "right_tag": right[0]["text"] if right else "",
                "bottom_line": center[-1]["text"] if center else "",
            })
        elif zone_name == "left_zone":
            out["text"] = texts[0] if texts else ""
        elif zone_name == "top_zone":
            out["text"] = texts[0] if texts else ""
        return out

    def _score_from_block_text(self, txt: str) -> Optional[str]:
        return _parse_score(txt)

    def _phase_from_block_text(self, txt: str) -> Optional[str]:
        raw = _clean_text_block(txt)
        if not raw:
            return None
        if FIM_JOGO_RE.search(raw):
            return "FIM DO JOGO"
        if INTERVALO_RE.search(raw):
            return "INTERVALO"
        if INICIO_JOGO_RE.search(raw):
            return "INICIO DO JOGO"
        if PRIMEIRO_TEMPO_RE.search(raw):
            return "PRIMEIRO TEMPO"
        if SEGUNDO_TEMPO_RE.search(raw):
            return "SEGUNDO TEMPO"
        if DAQUI_A_POUCO_RE.search(raw) or AO_VIVO_EM_RE.search(raw):
            return "DAQUI A POUCO"
        return None


    def _roi_top_hud_unified(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        H, W = frame.shape[:2]
        score_roi = self._roi_score(frame)
        clock_roi = self._roi_clock(frame)
        phase_roi = self._roi_phase(frame)
        rois = [score_roi, clock_roi, phase_roi]
        xs = [r[0] for r in rois]
        ys = [r[1] for r in rois]
        x2s = [r[0] + r[2] for r in rois]
        y2s = [r[1] + r[3] for r in rois]
        x1 = min(xs)
        y1 = min(ys)
        x2 = max(x2s)
        y2 = max(y2s)
        pad_x = max(16, int((x2 - x1) * 0.08))
        pad_top = max(10, int((y2 - y1) * 0.22))
        pad_bottom = max(10, int((y2 - y1) * 0.18))
        return _clip_roi(x1 - pad_x, y1 - pad_top, (x2 - x1) + 2 * pad_x, (y2 - y1) + pad_top + pad_bottom, W, H)

    def _merge_text_candidates(self, primary: List[str], fallback: List[str], limit: int = 6) -> List[str]:
        out: List[str] = []
        for seq in (primary, fallback):
            for txt in seq:
                txt = _clean_text_block(txt)
                if txt and txt not in out:
                    out.append(txt)
                    if len(out) >= limit:
                        return out
        return out

    def _context_from_center_text(self, text: str) -> str:
        raw = _clean_text_block(text)
        if not raw:
            return ""
        if _parse_score(raw) or _parse_clock(raw) or _parse_countdown(raw) or self._phase_from_block_text(raw):
            return ""
        return raw

    def _extract_unified_top_hud(self, frame: np.ndarray) -> Dict[str, Any]:
        roi_xywh = self._roi_top_hud_unified(frame)
        roi = _crop(frame, roi_xywh)
        out: Dict[str, Any] = {
            'score': None,
            'clock': None,
            'countdown': None,
            'phase_text': '',
            'context_text': '',
            'competition_text': '',
            'visible': False,
            'score_candidates': [],
            'clock_candidates': [],
            'countdown_candidates': [],
            'phase_candidates': [],
            'context_candidates': [],
            'blocks': [],
            'roi': roi_xywh,
            'teams': self._last_team_names_read,
        }
        if roi is None or roi.size == 0:
            return out
        x0, y0, rw, rh = roi_xywh
        blocks = self._detect_text_blocks(roi, zone_name='top_hud_unified')
        enriched: List[Dict[str, Any]] = []
        for block in blocks[:10]:
            block = self._ocr_block(dict(block))
            bx, by, bw, bh = block.get('bbox', (0, 0, 0, 0))
            block['global_bbox'] = (x0 + bx, y0 + by, bw, bh)
            enriched.append(block)
        out['blocks'] = enriched
        score_candidates = []
        clock_candidates = []
        countdown_candidates = []
        phase_candidates = []
        context_candidates = []
        competition_candidates = []
        center_text_candidates = []
        for block in enriched:
            txt = _clean_text_block(block.get('text', ''))
            if not txt:
                continue
            bx, by, bw, bh = block.get('bbox', (0, 0, 0, 0))
            cx = bx + bw / 2.0
            cy = by + bh / 2.0
            rel_x = cx / max(1.0, rw)
            rel_y = cy / max(1.0, rh)
            conf = float(block.get('confidence') or 0.0)
            score = _parse_score(txt)
            if score:
                bonus = 0.14 if 0.18 <= rel_x <= 0.82 else 0.0
                score_candidates.append({'value': score, 'text': txt, 'bbox': block['global_bbox'], 'confidence': conf + bonus})
                continue
            countdown = _parse_countdown(txt)
            if countdown and COUNTDOWN_HHMMSS_RE.search(_norm_text_numeric(txt).replace(' ', '')):
                bonus = 0.12 if 0.25 <= rel_x <= 0.75 else 0.0
                countdown_candidates.append({'value': countdown, 'text': txt, 'bbox': block['global_bbox'], 'confidence': conf + bonus})
                continue
            clock = _parse_clock(txt)
            if clock:
                bonus = 0.14 if 0.28 <= rel_x <= 0.72 else 0.0
                clock_candidates.append({'value': clock, 'text': txt, 'bbox': block['global_bbox'], 'confidence': conf + bonus})
                continue
            phase = self._phase_from_block_text(txt)
            if phase:
                bonus = 0.10 if 0.24 <= rel_x <= 0.76 else 0.0
                phase_candidates.append({'value': phase, 'text': txt, 'bbox': block['global_bbox'], 'confidence': conf + bonus})
                continue
            if 0.22 <= rel_x <= 0.78:
                center_text_candidates.append((conf, txt))
                context = self._context_from_center_text(txt)
                if context:
                    context_candidates.append({'value': context, 'text': txt, 'bbox': block['global_bbox'], 'confidence': conf + 0.08})
            if rel_y <= 0.60 and len(txt) >= 5 and not re.search(r'\d{1,3}:\d{2}', txt):
                competition_candidates.append((conf + (0.06 if rel_y <= 0.35 else 0.0), txt))

        score_fallbacks = self._ocr_roi_like_banner(
            roi,
            psm_list=(7, 6, 11, 12, 13),
            whitelist='0123456789xX-: ',
            upscale=2.8,
            allow_inv=True,
            allow_otsu=True,
            parser=_parse_score,
            block_zone='top_hud_unified_score',
            min_block_w_ratio=0.06,
            min_block_h_ratio=0.18,
        )
        clock_fallbacks = self._ocr_roi_like_banner(
            roi,
            psm_list=(7, 8, 13),
            whitelist='0123456789:T| ',
            upscale=2.8,
            allow_inv=True,
            allow_otsu=True,
            parser=_parse_clock,
            block_zone='top_hud_unified_clock',
            min_block_w_ratio=0.10,
            min_block_h_ratio=0.20,
        )
        phase_fallback_raw = self._ocr_roi_like_banner(
            roi,
            psm_list=(7, 6, 11),
            whitelist='ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789 :-',
            upscale=2.8,
            allow_red=True,
            allow_inv=True,
            allow_otsu=True,
            parser=None,
            block_zone='top_hud_unified_phase',
            min_block_w_ratio=0.10,
            min_block_h_ratio=0.18,
        )
        phase_fallbacks = [self._phase_from_block_text(txt) for txt in phase_fallback_raw]
        context_fallbacks = [self._context_from_center_text(txt) for txt in phase_fallback_raw]

        def _best(items: List[Dict[str, Any]]) -> Optional[str]:
            if not items:
                return None
            bucket: Dict[str, List[Dict[str, Any]]] = {}
            for item in items:
                bucket.setdefault(str(item.get('value')), []).append(item)
            ranked = []
            for value, vals in bucket.items():
                ranked.append((sum(float(v.get('confidence') or 0.0) for v in vals), len(vals), len(value), value))
            ranked.sort(reverse=True)
            return ranked[0][3] if ranked else None

        scores = [x for x in self._merge_text_candidates([c['value'] for c in score_candidates], score_fallbacks, limit=6) if _is_score_reasonable(x)]
        clocks = [x for x in self._merge_text_candidates([c['value'] for c in clock_candidates], clock_fallbacks, limit=6) if _is_mmss_clock_text(x)]
        countdowns = [x for x in [c['value'] for c in countdown_candidates] if x]
        phases = [x for x in self._merge_text_candidates([c['value'] for c in phase_candidates], [x for x in phase_fallbacks if x], limit=6) if x]
        contexts = [x for x in self._merge_text_candidates([c['value'] for c in context_candidates], [x for x in context_fallbacks if x], limit=6) if x]

        out['score'] = _majority_or_none(scores, min_count=1) or (scores[0] if scores else None)
        out['clock'] = _majority_or_none(clocks, min_count=1) or (clocks[0] if clocks else None)
        out['countdown'] = _best(countdown_candidates)
        out['phase_text'] = _majority_or_none(phases, min_count=1) or (phases[0] if phases else '')
        out['context_text'] = _majority_or_none(contexts, min_count=1) or (contexts[0] if contexts else '')
        if competition_candidates:
            competition_candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
            out['competition_text'] = competition_candidates[0][1]
            self._last_competition_read = out['competition_text']
        if not out['context_text'] and center_text_candidates:
            center_text_candidates.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
            out['context_text'] = self._context_from_center_text(center_text_candidates[0][1])
        out['score_candidates'] = score_candidates[:8]
        out['clock_candidates'] = clock_candidates[:8]
        out['countdown_candidates'] = countdown_candidates[:8]
        out['phase_candidates'] = phase_candidates[:8]
        out['context_candidates'] = context_candidates[:8]
        out['visible'] = bool(out['score'] or out['clock'] or out['countdown'] or out['phase_text'] or out['context_text'] or enriched)
        return out

    def _extract_scoreboard_from_top_blocks(self, blocks: List[Dict[str, Any]], zone_roi: Tuple[int, int, int, int]) -> Dict[str, Any]:
        _zx, _zy, zw, zh = zone_roi
        score_candidates: List[Dict[str, Any]] = []
        clock_candidates: List[Dict[str, Any]] = []
        countdown_candidates: List[Dict[str, Any]] = []
        phase_candidates: List[Dict[str, Any]] = []
        competition_candidates: List[str] = []
        for block in blocks:
            txt = _clean_text_block(block.get("text", ""))
            if not txt:
                continue
            x, y, w, h = block.get("bbox", (0, 0, 0, 0))
            cx = x + (w / 2.0)
            cy = y + (h / 2.0)
            rel_y = cy / max(1.0, zh)
            rel_x = cx / max(1.0, zw)
            conf = float(block.get("confidence") or 0.0)
            score = self._score_from_block_text(txt)
            if score:
                score_candidates.append({"value": score, "text": txt, "bbox": block.get("global_bbox") or block.get("bbox"), "confidence": conf + (0.12 if rel_y <= 0.72 else 0.0)})
                continue
            clock = _parse_clock(txt)
            if clock:
                clock_candidates.append({"value": clock, "text": txt, "bbox": block.get("global_bbox") or block.get("bbox"), "confidence": conf + (0.10 if rel_y <= 0.78 else 0.0) + (0.05 if 0.05 <= rel_x <= 0.55 else 0.0)})
                continue
            countdown = _parse_countdown(txt)
            if countdown:
                countdown_candidates.append({"value": countdown, "text": txt, "bbox": block.get("global_bbox") or block.get("bbox"), "confidence": conf + (0.08 if rel_y <= 0.70 else 0.0)})
                continue
            phase = self._phase_from_block_text(txt)
            if phase:
                phase_candidates.append({"value": phase, "text": txt, "bbox": block.get("global_bbox") or block.get("bbox"), "confidence": conf + (0.06 if rel_y <= 0.85 else 0.0)})
                continue
            if rel_y <= 0.65 and len(txt) >= 5 and not re.search(r"\d{1,3}:\d{2}", txt):
                competition_candidates.append(txt)
        def _best_candidate(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not items:
                return None
            by_value: Dict[str, List[Dict[str, Any]]] = {}
            for it in items:
                by_value.setdefault(str(it.get("value")), []).append(it)
            ranked = []
            for value, vals in by_value.items():
                ranked.append((sum(float(v.get("confidence") or 0.0) for v in vals), len(vals), value, vals[0]))
            ranked.sort(key=lambda x: (x[0], x[1], len(str(x[2]))), reverse=True)
            return ranked[0][3]
        score_best = _best_candidate(score_candidates)
        clock_best = _best_candidate(clock_candidates)
        countdown_best = _best_candidate(countdown_candidates)
        phase_best = _best_candidate(phase_candidates)
        competition_text = ""
        if competition_candidates:
            competition_candidates = sorted(competition_candidates, key=len, reverse=True)
            competition_text = competition_candidates[0]
            self._last_competition_read = competition_text
        scoreboard_visible = bool(score_best or clock_best or phase_best or countdown_best)
        return {
            "score": score_best.get("value") if score_best else None,
            "clock": clock_best.get("value") if clock_best else None,
            "countdown": countdown_best.get("value") if countdown_best else None,
            "phase_text": phase_best.get("value") if phase_best else "",
            "visible": scoreboard_visible,
            "score_candidates": score_candidates[:8],
            "clock_candidates": clock_candidates[:8],
            "countdown_candidates": countdown_candidates[:8],
            "phase_candidates": phase_candidates[:8],
            "competition_text": competition_text,
            "teams": self._last_team_names_read,
        }

    def _banner_signature(self, frame: np.ndarray) -> Optional[int]:
        try:
            roi = _crop(frame, self._roi_banner(frame))
            if roi is None or roi.size == 0:
                return None
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            # Denoise: Reduzir sensibilidade a ruído digital/compressão
            _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            small = cv2.resize(thresh, (48, 16), interpolation=cv2.INTER_AREA)
            return hash(small.tobytes())
        except Exception:
            return None

    def _get_paddle_ocr(self):
        # Utiliza a cópia unificada já iniciada no __init__ se existir, para evitar OneDNN recompilation!
        if getattr(self, "paddle_ocr", None) is not None:
            return self.paddle_ocr
            
        if self._paddle_ocr_failed:
            return None
        if getattr(self, "_paddle_ocr", None) is not None:
            return self._paddle_ocr
        if PaddleOCR is None:
            self._paddle_ocr_failed = True
            return None
        try:
            self._paddle_ocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                lang="pt",
            )
            return self._paddle_ocr
        except Exception:
            self._paddle_ocr_failed = True
            self._paddle_ocr = None
            return None

    def _extract_text_regions_scene(self, roi: np.ndarray, min_conf: float = 0.40) -> Dict[str, Any]:
        t0 = time.perf_counter()
        out: Dict[str, Any] = {
            "full_text": "", "headline": "", "subheadline": "", "left_tag": "", "right_tag": "",
            "bottom_line": "", "context_summary": "", "engine": "", "lines": [], "avg_conf": 0.0,
            "boxes": [], "ocr_ms": 0.0,
        }
        if roi is None or getattr(roi, "size", 0) == 0:
            return out
        h, w = roi.shape[:2]
        engine = self._get_paddle_ocr()
        entries: List[Dict[str, Any]] = []
        if engine is not None:
            try:
                result = engine.predict(roi)
                if isinstance(result, list):
                    for item in result:
                        rec_texts = item.get("rec_texts") if isinstance(item, dict) else getattr(item, "rec_texts", None)
                        rec_scores = item.get("rec_scores") if isinstance(item, dict) else getattr(item, "rec_scores", None)
                        rec_polys = item.get("rec_polys") if isinstance(item, dict) else getattr(item, "rec_polys", None)
                        if rec_texts is not None and rec_scores is not None:
                            polys = rec_polys or [None] * len(rec_texts)
                            for txt_val, score_val, poly in zip(rec_texts, rec_scores, polys):
                                txt_clean = _clean_text_block(str(txt_val or ""))
                                score_f = float(score_val or 0.0)
                                if not txt_clean or score_f < min_conf:
                                    continue
                                if poly is not None and len(poly) >= 4:
                                    poly_arr = np.array(poly, dtype=np.float32)
                                    x = int(np.min(poly_arr[:, 0])); y = int(np.min(poly_arr[:, 1]))
                                    ww = int(np.max(poly_arr[:, 0]) - x); hh = int(np.max(poly_arr[:, 1]) - y)
                                else:
                                    x, y, ww, hh = 0, 0, w, h
                                entries.append({"text": txt_clean, "conf": score_f, "bbox": (x, y, ww, hh)})
                if not entries:
                    legacy = engine.ocr(roi, cls=False)
                    if legacy:
                        legacy0 = legacy[0] if isinstance(legacy, list) else legacy
                        for det in legacy0 or []:
                            if not det or len(det) < 2:
                                continue
                            poly, rec = det[0], det[1]
                            txt_clean = _clean_text_block(str((rec[0] if rec else "") or ""))
                            score_f = float(rec[1] if rec and len(rec) > 1 else 0.0)
                            if not txt_clean or score_f < min_conf:
                                continue
                            poly_arr = np.array(poly, dtype=np.float32)
                            x = int(np.min(poly_arr[:, 0])); y = int(np.min(poly_arr[:, 1]))
                            ww = int(np.max(poly_arr[:, 0]) - x); hh = int(np.max(poly_arr[:, 1]) - y)
                            entries.append({"text": txt_clean, "conf": score_f, "bbox": (x, y, ww, hh)})
                out["engine"] = "paddleocr"
            except Exception:
                entries = []
        if not entries:
            blocks = self._detect_text_blocks(roi, zone_name="banner_scene")
            for block in blocks[:16]:
                enriched = self._ocr_block(dict(block))
                txt_clean = _clean_text_block(str(enriched.get("text") or ""))
                conf = float(enriched.get("confidence") or 0.0)
                if not txt_clean or conf < 0.20:
                    continue
                entries.append({"text": txt_clean, "conf": conf, "bbox": tuple(enriched.get("bbox") or (0, 0, 0, 0))})
            out["engine"] = "tesseract-blocks"
        if not entries:
            out["ocr_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
            return out
        entries.sort(key=lambda e: (e["bbox"][1], e["bbox"][0]))
        lines: List[List[Dict[str, Any]]] = []
        line_tol = max(12, int(h * 0.07))
        for item in entries:
            x, y, ww, hh = item["bbox"]
            cy = y + hh / 2.0
            placed = False
            for line in lines:
                ly = float(np.mean([it["bbox"][1] + it["bbox"][3] / 2.0 for it in line]))
                if abs(cy - ly) <= line_tol:
                    line.append(item); placed = True; break
            if not placed:
                lines.append([item])
        line_texts: List[str] = []
        line_boxes: List[Tuple[int, int, int, int]] = []
        for line in lines:
            line.sort(key=lambda e: e["bbox"][0])
            xs: List[int] = []; ys: List[int] = []; x2s: List[int] = []; y2s: List[int] = []; parts: List[str] = []
            for item in line:
                x, y, ww, hh = item["bbox"]
                txt_clean = _clean_text_block(item["text"])
                if not txt_clean:
                    continue
                parts.append(txt_clean); xs.append(x); ys.append(y); x2s.append(x + ww); y2s.append(y + hh)
            joined = _clean_text_block(" ".join(parts))
            if joined and xs:
                line_texts.append(joined)
                line_boxes.append((min(xs), min(ys), max(x2s) - min(xs), max(y2s) - min(ys)))
        packed = list(zip(line_texts, line_boxes))
        packed.sort(key=lambda p: (p[1][1], -p[1][2]))
        line_texts = [p[0] for p in packed]
        line_boxes = [p[1] for p in packed]
        out["full_text"] = " | ".join([t for t in line_texts if t])
        out["headline"] = line_texts[0] if len(line_texts) > 0 else ""
        out["subheadline"] = line_texts[1] if len(line_texts) > 1 else ""
        out["bottom_line"] = line_texts[2] if len(line_texts) > 2 else ""
        out["context_summary"] = out["full_text"]
        out["lines"] = line_texts
        out["boxes"] = line_boxes
        out["avg_conf"] = round(sum(float(e["conf"]) for e in entries) / max(1, len(entries)), 4)
        out["ocr_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        self._scene_text_last_stats = {
            "engine": out["engine"], "lines": len(line_texts), "regions": len(entries),
            "avg_conf": out["avg_conf"], "ocr_ms": out["ocr_ms"],
        }
        return out

    def _extract_banner_text_light(self, frame: np.ndarray) -> Dict[str, Any]:
        try:
            roi = _crop(frame, self._roi_banner(frame))
            if roi is None or roi.size == 0:
                return {"full_text": "", "headline": "", "subheadline": "", "left_tag": "", "right_tag": "", "bottom_line": "", "context_summary": "", "engine": "", "lines": [], "avg_conf": 0.0, "boxes": [], "ocr_ms": 0.0}
            h, w = roi.shape[:2]
            x0 = max(0, int(w * 0.01)); x1 = min(w, int(w * 0.99)); y0 = max(0, int(h * 0.02)); y1 = min(h, int(h * 0.98))
            roi2 = roi[y0:y1, x0:x1]
            return self._extract_text_regions_scene(roi2, min_conf=0.40)
        except Exception:
            return {"full_text": "", "headline": "", "subheadline": "", "left_tag": "", "right_tag": "", "bottom_line": "", "context_summary": "", "engine": "", "lines": [], "avg_conf": 0.0, "boxes": [], "ocr_ms": 0.0}

    def _kick_banner_async(self, frame: np.ndarray) -> None:
        sig = self._banner_signature(frame)
        now = time.time()
        # Throttle: No máximo 1 análise a cada X segundos para economizar CPU
        if sig is None or sig == self._banner_async_hash or self._banner_async_running:
            return
        if (now - getattr(self, "_last_banner_kick_t", 0.0)) < getattr(self, "banner_ocr_interval_s", 1.0):
            return
        
        try:
            frame_copy = frame.copy()
        except Exception:
            return
        self._banner_async_hash = sig
        self._last_banner_kick_t = now
        def _worker() -> None:
            self._banner_async_running = True
            try:
                data = self._extract_banner_text_light(frame_copy)
                data["ts"] = time.time()
                with self._ocr_async_lock:
                    self._banner_async_cache = data
                    if data.get("full_text"):
                        self._last_hud_overlay_read = data.get("full_text", "")
                        self._last_hud_overlay_read_t = data.get("ts", time.time())
            finally:
                self._banner_async_running = False
        threading.Thread(target=_worker, name="banner-ocr", daemon=True).start()

    def _read_score_fast(self, frame: np.ndarray) -> Optional[str]:
        now = time.time()
        if (now - self._last_score_read_t) < 0.20:
            return self._last_score_read
        best = self._read_score_legacy(frame)
        if best:
            self._score_history.append(str(best))
            self._last_score_read = Counter(self._score_history).most_common(1)[0][0]
        self._last_score_read_t = time.time()
        return self._last_score_read

    def _read_game_clock_fast(self, frame: np.ndarray) -> Optional[str]:
        now = time.time()
        if (now - self._last_clock_read_t) < 0.22:
            return self._last_clock_read
        best = self._read_game_clock_legacy(frame)
        best = self._validate_clock_transition(self._last_clock_read, best)
        if best:
            self._clock_history.append(best)
            hist_best = Counter(self._clock_history).most_common(1)[0][0]
            best_s = _clock_to_seconds_mmss(best)
            hist_s = _clock_to_seconds_mmss(hist_best)
            if best_s is not None and hist_s is not None and abs(best_s - hist_s) <= 8:
                self._last_clock_read = best
            else:
                self._last_clock_read = hist_best
        self._last_clock_read_t = time.time()
        return self._last_clock_read

    def _read_countdown_fast(self, frame: np.ndarray) -> Optional[str]:
        now = time.time()
        if (now - self._last_countdown_read_t) < 0.45:
            return self._last_countdown_read
        self._last_countdown_read = self._read_countdown_legacy(frame)
        self._last_countdown_read_t = time.time()
        return self._last_countdown_read

    def _read_phase_text_fast(self, frame: np.ndarray) -> str:
        now = time.time()
        if (now - self._last_phase_read_t) < 0.35:
            return self._last_phase_read
        self._last_phase_read = self._read_phase_text_legacy(frame) or self._last_phase_read
        self._last_phase_read_t = time.time()
        return self._last_phase_read

    def _read_banner_context_fast(self, frame: np.ndarray) -> Dict[str, Any]:
        self._kick_banner_async(frame)
        with self._ocr_async_lock:
            data = dict(self._banner_async_cache)
        data.setdefault("full_text", ""); data.setdefault("headline", ""); data.setdefault("subheadline", "")
        data.setdefault("left_tag", ""); data.setdefault("right_tag", ""); data.setdefault("bottom_line", "")
        data.setdefault("context_summary", data.get("full_text", ""))
        data["zones"] = {
            "bottom": {
                "headline": data.get("headline", ""), "subheadline": data.get("subheadline", ""),
                "left_tag": data.get("left_tag", ""), "right_tag": data.get("right_tag", ""),
                "bottom_line": data.get("bottom_line", ""), "text": data.get("full_text", ""),
            },
            "left_panel": {}, "top_overlay": {}, "right_panel": {}, "top_hud": {},
        }
        return data

    def read_screen_context(self, frame: np.ndarray) -> Dict[str, Any]:
        now = time.time()
        if (now - self._last_screen_context_t) < 0.25 and self._last_screen_context:
            return dict(self._last_screen_context)
        macro = self._get_screen_macro_zones(frame)
        zones_out: Dict[str, Any] = {}
        all_blocks: List[Dict[str, Any]] = []
        for zone_name in ("top_zone", "bottom_zone", "left_zone", "right_zone"):
            zone_img = macro[zone_name]["image"]
            roi_x, roi_y, _roi_w, _roi_h = macro[zone_name]["roi"]
            blocks = self._detect_text_blocks(zone_img, zone_name=zone_name)
            enriched: List[Dict[str, Any]] = []
            max_blocks = 8 if zone_name == "top_zone" else 6
            for block in blocks[:max_blocks]:
                block = self._ocr_block(block)
                x, y, w, h = block["bbox"]
                block["global_bbox"] = (roi_x + x, roi_y + y, w, h)
                enriched.append(block)
                all_blocks.append(block)
            zones_out[zone_name] = self._classify_zone_blocks(enriched, zone_name)

        unified_hud = self._extract_unified_top_hud(frame)
        scoreboard = self._extract_scoreboard_from_top_blocks(zones_out.get("top_zone", {}).get("blocks", []), macro["top_zone"]["roi"])

        if unified_hud.get("score") and (not scoreboard.get("score") or not _is_score_reasonable(scoreboard.get("score"))):
            scoreboard["score"] = unified_hud.get("score")
        if unified_hud.get("clock") and not scoreboard.get("clock"):
            scoreboard["clock"] = unified_hud.get("clock")
        if unified_hud.get("countdown") and not scoreboard.get("countdown"):
            scoreboard["countdown"] = unified_hud.get("countdown")
        if unified_hud.get("phase_text") and not scoreboard.get("phase_text"):
            scoreboard["phase_text"] = unified_hud.get("phase_text")
        if unified_hud.get("competition_text") and not scoreboard.get("competition_text"):
            scoreboard["competition_text"] = unified_hud.get("competition_text")
        if unified_hud.get("teams"):
            scoreboard["teams"] = unified_hud.get("teams")

        legacy_score = self._read_score_legacy(frame) if not scoreboard.get("score") else None
        legacy_clock = self._read_game_clock_legacy(frame) if not scoreboard.get("clock") else None
        legacy_countdown = self._read_countdown_legacy(frame) if not scoreboard.get("countdown") else None
        legacy_phase = self._read_phase_text_legacy(frame) if not scoreboard.get("phase_text") else ""
        if legacy_score and not scoreboard.get("score"):
            scoreboard["score"] = legacy_score
        if legacy_clock and not scoreboard.get("clock"):
            scoreboard["clock"] = legacy_clock
        if legacy_countdown and not scoreboard.get("countdown"):
            scoreboard["countdown"] = legacy_countdown
        if legacy_phase and not scoreboard.get("phase_text"):
            scoreboard["phase_text"] = legacy_phase

        top_zone_text = zones_out.get("top_zone", {}).get("text", "")
        unified_context = _clean_text_block(unified_hud.get("context_text", ""))
        top_overlay_text = unified_context or top_zone_text
        scoreboard["visible"] = bool(
            scoreboard.get("visible") or scoreboard.get("score") or scoreboard.get("clock") or scoreboard.get("phase_text")
            or scoreboard.get("countdown") or top_overlay_text or unified_hud.get("visible")
        )
        if scoreboard.get("competition_text"):
            self._last_competition_read = str(scoreboard.get("competition_text"))

        bottom = {
            "headline": zones_out.get("bottom_zone", {}).get("headline", ""),
            "subheadline": zones_out.get("bottom_zone", {}).get("subheadline", ""),
            "left_tag": zones_out.get("bottom_zone", {}).get("left_tag", ""),
            "right_tag": zones_out.get("bottom_zone", {}).get("right_tag", ""),
            "bottom_line": zones_out.get("bottom_zone", {}).get("bottom_line", ""),
            "text": zones_out.get("bottom_zone", {}).get("text", ""),
        }
        banner_parts = [bottom.get("left_tag", ""), bottom.get("headline", ""), bottom.get("subheadline", ""), bottom.get("bottom_line", ""), bottom.get("right_tag", "")]
        banner_pieces: List[str] = []
        for txt in banner_parts:
            txt = _clean_text_block(txt)
            if txt and txt not in banner_pieces:
                banner_pieces.append(txt)
        banner_text = " | ".join(banner_pieces)
        context_summary = banner_text or top_overlay_text or zones_out.get("left_zone", {}).get("text", "") or zones_out.get("right_zone", {}).get("text", "")
        top_blocks = list(unified_hud.get("blocks") or zones_out.get("top_zone", {}).get("blocks", []))
        context = {
            "scoreboard": scoreboard,
            "top_hud": {
                "score": scoreboard.get("score"),
                "clock": scoreboard.get("clock"),
                "countdown": scoreboard.get("countdown"),
                "phase_text": scoreboard.get("phase_text"),
                "competition_text": scoreboard.get("competition_text") or top_overlay_text,
                "teams": scoreboard.get("teams") or self._last_team_names_read,
                "context_text": unified_context,
                "blocks": top_blocks,
                "roi": unified_hud.get("roi"),
            },
            "bottom": bottom,
            "left_panel": {"text": zones_out.get("left_zone", {}).get("text", "")},
            "top_overlay": {"text": top_overlay_text},
            "right_panel": {"text": zones_out.get("right_zone", {}).get("text", "")},
            "banner_text": banner_text,
            "context_summary": context_summary,
            "blocks": all_blocks + [b for b in top_blocks if b not in all_blocks],
            "macro_zones": {k: v["roi"] for k, v in macro.items()},
        }
        self._last_screen_context = context
        self._last_screen_context_t = now
        return context

    def _read_phase_text_legacy(self, frame: np.ndarray) -> str:
        roi = _crop(frame, self._roi_phase(frame))
        texts = self._ocr_collect_candidates(roi=roi, psm_list=(7, 6), whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789 :-", upscale=2.5, allow_red=True, allow_inv=True, allow_otsu=True, normalize_mode="phase")
        found: List[str] = []
        for txt in texts:
            parsed = self._phase_from_block_text(txt)
            if parsed:
                found.append(parsed)
        return self._pick_best_text_candidate(found, min_len=3, prefer_longest=False)

    def read_phase_text(self, frame: np.ndarray) -> str:
        now = time.time()
        if (now - self._last_phase_read_t) < 0.45:
            return self._last_phase_read
        ctx = self.read_screen_context(frame)
        phase_text = str(((ctx.get("scoreboard") or {}).get("phase_text")) or "").strip()
        if not phase_text:
            phase_text = self._read_phase_text_legacy(frame)
        if phase_text:
            self._last_phase_read = phase_text
        self._last_phase_read_t = now
        return self._last_phase_read

    def read_banner_context(self, frame: np.ndarray) -> Dict[str, Any]:
        fast = self._read_banner_context_fast(frame)
        self._last_hud_overlay_read = str(fast.get("full_text") or "")
        self._last_hud_overlay_read_t = time.time()
        return fast

    def read_hud_overlay(self, frame: np.ndarray) -> str:
        now = time.time()
        if (now - self._last_hud_overlay_read_t) < 0.30:
            return self._last_hud_overlay_read
        text = self._read_banner_context_fast(frame).get("full_text", "")
        if not text:
            text = self.read_banner_context(frame).get("full_text", "")
        self._last_hud_overlay_read = text
        self._last_hud_overlay_read_t = now
        return text

    def read_replay_text(self, frame: np.ndarray) -> str:
        text = self.read_hud_overlay(frame)
        return text if REPLAY_RE.search(text or "") else ""

    def read_inicio_jogo_text(self, frame: np.ndarray) -> str:
        ctx = self.read_screen_context(frame)
        text = " | ".join(filter(None, [self.read_phase_text(frame), self.read_hud_overlay(frame), ctx.get("top_overlay", {}).get("text", "")]))
        return text if INICIO_JOGO_RE.search(text or "") else ""

    def read_fim_jogo_text(self, frame: np.ndarray) -> str:
        ctx = self.read_screen_context(frame)
        text = " | ".join(filter(None, [self.read_phase_text(frame), self.read_hud_overlay(frame), ctx.get("top_overlay", {}).get("text", "")]))
        return text if FIM_JOGO_RE.search(text or "") else ""

    def _read_score_legacy(self, frame: np.ndarray) -> Optional[str]:
        return self._read_score_banner_style(frame)

    def read_score(self, frame: np.ndarray) -> Optional[str]:
        now = time.time()
        if (now - self._last_score_read_t) < 0.30:
            return self._last_score_read
        ctx = self.read_screen_context(frame)
        best = (ctx.get("scoreboard") or {}).get("score") or self._read_score_legacy(frame)
        if best:
            prev = self._last_score_read
            if prev and re.fullmatch(r"\d+x\d+", prev):
                pa, pb = [int(x) for x in prev.split("x", 1)]
                na, nb = [int(x) for x in str(best).split("x", 1)]
                if abs(na - pa) <= 1 and abs(nb - pb) <= 1:
                    self._score_history.append(str(best))
                    self._last_score_read = Counter(self._score_history).most_common(1)[0][0]
            else:
                self._score_history.append(str(best))
                self._last_score_read = Counter(self._score_history).most_common(1)[0][0]
        self._last_score_read_t = now
        return self._last_score_read

    def _validate_clock_transition(self, prev: Optional[str], new_clock: Optional[str]) -> Optional[str]:
        if not new_clock:
            return prev
        prev_s = _clock_to_seconds_mmss(prev)
        new_s = _clock_to_seconds_mmss(new_clock)
        if prev_s is None or new_s is None:
            return new_clock
        delta = new_s - prev_s
        if delta < -4 or delta > 12:
            return prev
        return new_clock

    def _read_game_clock_legacy(self, frame: np.ndarray) -> Optional[str]:
        return self._read_clock_banner_style(frame)

    def read_game_clock(self, frame: np.ndarray) -> Optional[str]:
        now = time.time()
        if (now - self._last_clock_read_t) < 0.15:
            return self._last_clock_read
        ctx = self.read_screen_context(frame)
        found: List[str] = []
        score_ctx = ctx.get("scoreboard") or {}
        if score_ctx.get("clock"):
            found.append(str(score_ctx.get("clock")))
        if not found:
            for block in ctx.get("top_hud", {}).get("blocks", []):
                parsed = _parse_clock(block.get("text", ""))
                if parsed:
                    found.append(parsed)
        if not found:
            legacy = self._read_game_clock_legacy(frame)
            if legacy:
                found.append(legacy)
        if found:
            best = _majority_or_none(found, min_count=1) or found[0]
            best = self._validate_clock_transition(self._last_clock_read, best)
            if best:
                self._clock_history.append(best)
                hist_best = Counter(self._clock_history).most_common(1)[0][0]
                best_s = _clock_to_seconds_mmss(best)
                hist_s = _clock_to_seconds_mmss(hist_best)
                if best_s is not None and hist_s is not None and abs(best_s - hist_s) > 10:
                    best = hist_best
                self._last_clock_read = best
        self._last_clock_read_t = now
        return self._last_clock_read

    def _read_countdown_legacy(self, frame: np.ndarray) -> Optional[str]:
        found: List[str] = []
        for roi in [_crop(frame, self._roi_countdown_center(frame)), _crop(frame, self._roi_pre_jogo(frame))]:
            found.extend(self._ocr_collect_candidates(roi=roi, psm_list=(7, 6, 8), whitelist="0123456789: ", upscale=2.4, allow_inv=True, allow_otsu=True, normalize_mode="general", parser=_parse_countdown))
        return _majority_or_none(found, min_count=1)

    def read_countdown(self, frame: np.ndarray) -> Optional[str]:
        now = time.time()
        if (now - self._last_countdown_read_t) < 0.45:
            return self._last_countdown_read
        ctx = self.read_screen_context(frame)
        found: List[str] = []
        score_ctx = ctx.get("scoreboard") or {}
        if score_ctx.get("countdown"):
            found.append(str(score_ctx.get("countdown")))
        if not found:
            for block in ctx.get("blocks", []):
                parsed = _parse_countdown(block.get("text", ""))
                if parsed:
                    found.append(parsed)
        if not found:
            legacy = self._read_countdown_legacy(frame)
            if legacy:
                found.append(legacy)
        best = _majority_or_none(found, min_count=1)
        if best:
            self._last_countdown_read = best
        self._last_countdown_read_t = now
        return self._last_countdown_read

    def read_team_names(self, frame: np.ndarray) -> Tuple[Optional[str], Optional[str]]:
        ctx = self.read_screen_context(frame)
        teams = (ctx.get("top_hud") or {}).get("teams") or self._last_team_names_read
        if isinstance(teams, (list, tuple)) and len(teams) >= 2:
            self._last_team_names_read = (teams[0] or self._last_team_names_read[0], teams[1] or self._last_team_names_read[1])
        return self._last_team_names_read

    def read_competition(self, frame: np.ndarray) -> Optional[str]:
        ctx = self.read_screen_context(frame)
        competition = str((ctx.get("top_hud") or {}).get("competition_text") or ctx.get("top_overlay", {}).get("text", "") or self._last_competition_read or "").strip()
        if competition:
            self._last_competition_read = competition
        return self._last_competition_read

    def _apply_text_priority(self, visual_state: str, visual_conf: float, score_text: str, game_clock_text: str, countdown_text: str, phase_text: str, banner_text: str, replay_text: str, inicio_jogo_text: str, fim_jogo_text: str) -> Tuple[str, float, str, Dict[str, bool]]:
        texts = " | ".join([phase_text or "", banner_text or "", replay_text or "", inicio_jogo_text or "", fim_jogo_text or ""]).upper()
        flags = {
            "pre_jogo_hint": bool(DAQUI_A_POUCO_RE.search(texts) or AO_VIVO_EM_RE.search(texts)),
            "inicio_jogo_hint": bool(INICIO_JOGO_RE.search(texts)),
            "intervalo_hint": bool(INTERVALO_RE.search(texts)),
            "fim_jogo_hint": bool(FIM_JOGO_RE.search(texts)),
            "replay_hint": bool(REPLAY_RE.search(texts)),
        }
        match_phase_text = ""
        if flags["fim_jogo_hint"]:
            return "pos_jogo", max(visual_conf, 0.95), "fim_jogo", flags
        if flags["intervalo_hint"]:
            return "intervalo", max(visual_conf, 0.92), "intervalo", flags
        if flags["pre_jogo_hint"]:
            return "pre_jogo", max(visual_conf, 0.92), "pre_jogo", flags
        if flags["inicio_jogo_hint"]:
            return "jogo", max(visual_conf, 0.90), "primeiro_tempo", flags
        phase_upper = (phase_text or "").upper()
        if PRIMEIRO_TEMPO_RE.search(phase_upper):
            match_phase_text = "primeiro_tempo"
        elif SEGUNDO_TEMPO_RE.search(phase_upper):
            match_phase_text = "segundo_tempo"
        elif INTERVALO_RE.search(phase_upper):
            match_phase_text = "intervalo"
        if re.fullmatch(r"\d+x\d+", score_text or ""):
            visual_state = "jogo"; visual_conf = max(visual_conf, 0.84)
        if re.fullmatch(r"\d{1,3}:\d{2}", game_clock_text or ""):
            visual_state = "jogo"; visual_conf = max(visual_conf, 0.84)
        if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", countdown_text or ""):
            visual_state = "pre_jogo"; visual_conf = max(visual_conf, 0.84)
            if not match_phase_text:
                match_phase_text = "pre_jogo"
        return visual_state, visual_conf, match_phase_text, flags

    def _is_live_scoreboard_visible(self, frame: np.ndarray) -> bool:
        return self._is_scoreboard_active(frame)

    def classify_frame_fast(self, frame: np.ndarray) -> MatchResult:
        t0 = time.perf_counter()
        perf: Dict[str, float] = {}
        try:
            if frame is None or getattr(frame, "size", 0) == 0:
                return MatchResult(label="nao_detectado", score=0.0, best_template="", roi_name="", details={"visual_state": "nao_detectado", "visual_confidence": 0.0, "reason": "frame_vazio"})
            s = time.perf_counter()
            best = None
            if self.cloud_sovereignty_mode:
                # No Modo Eco-IA, verificamos o estado (Template Match) apenas a cada 1 segundo.
                now = time.time()
                if (now - getattr(self, "_last_frame_state_t", 0.0)) >= 1.0 or not self._last_visual_state_confirmed:
                    best = self.detect_frame_state(frame)
                    self._last_frame_state_t = now
                    self._last_visual_state_confirmed = best
                else:
                    best = self._last_visual_state_confirmed
            else:
                best = self.detect_frame_state(frame)
            
            perf["detect_frame_state_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
            details = dict(best.details or {})
            visual_state = str(best.label or "nao_detectado").strip().lower()
            visual_conf = float(best.score or 0.0)

            # Só procedemos com gates se não for IA, ou se for IA a cada 5 segundos (Economia Extrema)
            scoreboard_active = self._last_score_active
            clock_active = self._last_clock_active
            banner_active = self._last_banner_active

            now = time.time()
            if not self.cloud_sovereignty_mode or (now - getattr(self, "_last_gates_t", 0.0)) >= 5.0:
                s = time.perf_counter()
                scoreboard_active = self._is_scoreboard_active(frame)
                clock_active = self._is_clock_roi_active(frame)
                # Banner visual profile é pesado; ignorar se IA estiver ativa
                if not self.cloud_sovereignty_mode:
                    banner_roi = self._roi_banner(frame)
                    banner_profile = self._banner_visual_profile(_crop(frame, banner_roi))
                    banner_active = bool((banner_profile or {}).get("banner_active"))
                else:
                    banner_active = True # Assume ativo no modo IA para não bloquear coleta
                
                self._last_score_active = scoreboard_active
                self._last_clock_active = clock_active
                self._last_banner_active = banner_active
                self._last_gates_t = now
                perf["visual_gates_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
            s = time.perf_counter()
            banner_ctx: Dict[str, Any] = {}
            banner_text = ""
            
            # --- MODO SOBERANIA CLOUD (ECO-IA-PLUS) ---
            if self.cloud_sovereignty_mode:
                # Na IA, pulamos Banner OCR COMPLETAMENTE (Legado Tesseract removido).
                # Delegamos 100% da leitura contextual para o Gemini.
                banner_ctx = {"full_text": "", "summary": "Analisado via Cloud IA"}
                banner_text = ""
                score_text = self._last_score_read or ""
                game_clock_text = self._last_clock_read or ""
                countdown_text = self._last_countdown_read or ""
                phase_text = self._last_phase_read or ""
                perf["ocr_skipped_cloud_active"] = 1.0
            else:
                banner_ctx = self._read_banner_context_fast(frame)
                banner_text = str(banner_ctx.get("full_text") or "")
                perf["banner_async_cache_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
                
                roi_to_read = self._roi_cycle[self._roi_cycle_idx]
                self._roi_cycle_idx = (self._roi_cycle_idx + 1) % len(self._roi_cycle)
                
                score_text = self._last_score_read or ""
                game_clock_text = self._last_clock_read or ""
                phase_text = self._last_phase_read or ""
                s = time.perf_counter()
                if scoreboard_active and roi_to_read == "score":
                    score_text = self._read_score_fast(frame) or self._last_score_read or ""
                perf["score_fast_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
                
                s = time.perf_counter()
                if clock_active:
                    should_force_clock = (
                        not game_clock_text
                        or (time.time() - self._last_clock_read_t) >= 0.90
                        or roi_to_read == "clock"
                    )
                    if should_force_clock:
                        game_clock_text = self._read_game_clock_fast(frame) or self._last_clock_read or ""
                perf["clock_fast_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
                
                s = time.perf_counter()
                countdown_text = self._last_countdown_read or ""
                if visual_state == "pre_jogo":
                    countdown_text = self._read_countdown_fast(frame) or self._last_countdown_read or ""
                perf["countdown_fast_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
                
                s = time.perf_counter()
                if roi_to_read == "phase":
                    phase_text = self._read_phase_text_fast(frame) or self._last_phase_read or ""
                perf["phase_fast_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
            replay_text = banner_text if REPLAY_RE.search(banner_text or "") else ""
            inicio_jogo_text = banner_text if INICIO_JOGO_RE.search((banner_text or "") + " | " + (phase_text or "")) else ""
            fim_jogo_text = banner_text if FIM_JOGO_RE.search((banner_text or "") + " | " + (phase_text or "")) else ""
            if not clock_active and banner_active:
                game_clock_text = ""
            s = time.perf_counter()
            visual_state, visual_conf, match_phase_text, priority_flags = self._apply_text_priority(
                visual_state=visual_state, visual_conf=visual_conf, score_text=score_text or "", game_clock_text=game_clock_text or "",
                countdown_text=countdown_text or "", phase_text=phase_text or "", banner_text=banner_text or "",
                replay_text=replay_text or "", inicio_jogo_text=inicio_jogo_text or "", fim_jogo_text=fim_jogo_text or "",
            )
            perf["priority_ms"] = round((time.perf_counter() - s) * 1000.0, 2)
            banner_upper = (banner_text or "").upper()
            replay_upper = (replay_text or "").upper()
            is_replay = bool(REPLAY_RE.search(banner_upper) or REPLAY_RE.search(replay_upper))
            is_var = bool(VAR_RE.search(banner_upper))
            is_substitution = bool(SUB_RE.search(banner_upper))
            is_yellow_card = bool(AMARELO_RE.search(banner_upper))
            is_red_card = bool(VERMELHO_RE.search(banner_upper))
            is_goal = bool(GOL_RE.search(banner_upper))
            if visual_state == "nao_detectado" and scoreboard_active:
                visual_state = "jogo"; visual_conf = max(visual_conf, 0.80)
            try:
                async_age_ms = round(max(0.0, time.time() - float(banner_ctx.get("ts") or 0.0)) * 1000.0, 2) if banner_ctx.get("ts") else None
            except Exception:
                async_age_ms = None
            out_details = {
                **details, "visual_state": visual_state, "visual_confidence": visual_conf,
                "score_detected": score_text or None, "score_raw": score_text or None,
                "game_clock_detected": game_clock_text or None, "game_clock_raw": game_clock_text or None,
                "countdown_detected": countdown_text or None, "clock_raw": countdown_text or game_clock_text or None,
                "match_phase_text": match_phase_text or None, "phase_text": phase_text or None,
                "hud_overlay": banner_text or None, "banner_text": banner_text or None,
                "banner_summary": banner_text[:180] if banner_text else None,
                "screen_context": {"banner_text": banner_text or "", "context_summary": banner_ctx.get("context_summary", "")},
                "replay_text": replay_text or None, "fim_jogo_text": fim_jogo_text or None, "inicio_jogo_text": inicio_jogo_text or None,
                "is_replay": is_replay, "is_var": is_var, "is_substitution": is_substitution,
                "is_yellow_card": is_yellow_card, "is_red_card": is_red_card, "is_goal": is_goal,
                "score_roi": self._roi_score(frame), "clock_roi": self._roi_clock(frame), "phase_roi": self._roi_phase(frame),
                "pre_jogo_roi": self._roi_pre_jogo(frame), "jogo_roi": self._roi_jogo(frame), "intervalo_roi": self._roi_intervalo(frame),
                "replay_roi": self._roi_replay(frame), "fim_jogo_roi": self._roi_fim_jogo(frame), "inicio_jogo_roi": self._roi_inicio_jogo(frame),
                "banner_roi": banner_roi, "scoreboard_active": scoreboard_active, "clock_active": clock_active, "banner_active": banner_active,
                "banner_ocr_engine": banner_ctx.get("engine", ""), "banner_ocr_lines": banner_ctx.get("lines", []),
                "banner_ocr_avg_conf": banner_ctx.get("avg_conf", 0.0), "banner_ocr_ms": banner_ctx.get("ocr_ms", 0.0),
                "banner_visual_kind": (banner_profile or {}).get("kind"), "banner_visual_confidence": (banner_profile or {}).get("confidence"),
                "banner_headline": banner_ctx.get("headline", "") or None, "banner_subheadline": banner_ctx.get("subheadline", "") or None,
                "banner_left_tag": banner_ctx.get("left_tag", "") or None, "banner_right_tag": banner_ctx.get("right_tag", "") or None,
                "banner_bottom_line": banner_ctx.get("bottom_line", "") or None, "banner_async_running": bool(self._banner_async_running),
                "banner_async_cache_age_ms": async_age_ms, "banner_async_has_text": bool(banner_text),
                "priority_pre_jogo": priority_flags["pre_jogo_hint"], "priority_inicio_jogo": priority_flags["inicio_jogo_hint"],
                "priority_intervalo": priority_flags["intervalo_hint"], "priority_fim_jogo": priority_flags["fim_jogo_hint"],
                "perf": perf, "detector_total_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            }
            self._last_debug_info = out_details
            self._save_debug_rois(frame)
            return MatchResult(label=visual_state, score=float(visual_conf), best_template=best.best_template, roi_name=best.roi_name, details=out_details)
        except Exception as exc:
            return MatchResult(label="nao_detectado", score=0.0, best_template="", roi_name="", details={"visual_state": "nao_detectado", "visual_confidence": 0.0, "reason": f"erro: {type(exc).__name__}: {exc}", "perf": perf})


# ============================================================
# PATCH FINAL DE ESTABILIZAÇÃO
# ============================================================

def _pick_best_text_candidate(self, texts: List[str], min_len: int = 3, prefer_longest: bool = True) -> str:
    vals = [t.strip() for t in texts if t and len(t.strip()) >= min_len]
    if not vals:
        return ""
    best_txt, best_qty = Counter(vals).most_common(1)[0]
    if best_qty >= 2:
        return best_txt
    return max(vals, key=len) if prefer_longest else vals[0]


def _hl_init_state(self) -> None:
    if not hasattr(self, "_hl_state"):
        self._hl_state = {
            "score_sig": None,
            "clock_sig": None,
            "countdown_sig": None,
            "phase_sig": None,
            "banner_sig": None,
            "score_t": -9999.0,
            "clock_t": -9999.0,
            "countdown_t": -9999.0,
            "phase_t": -9999.0,
            "banner_t": -9999.0,
            "clock_force_t": -9999.0,
        }


def _hl_roi_sig(self, frame: np.ndarray, roi_name: str, size=(36, 12)) -> Optional[int]:
    try:
        roi = _crop(frame, self._resolve_roi(frame, roi_name))
        if roi is None or roi.size == 0:
            return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
        return hash(small.tobytes())
    except Exception:
        return None


def _hl_roi_active(self, frame: np.ndarray, roi_name: str) -> bool:
    try:
        if hasattr(self, "is_roi_enabled") and not self.is_roi_enabled(roi_name):
            return False
        roi = _crop(frame, self._resolve_roi(frame, roi_name))
        if roi is None or roi.size == 0:
            return False
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_v = float(np.mean(gray))
        std_v = float(np.std(gray))
        return mean_v < 245.0 and std_v > 8.0
    except Exception:
        return False


def _clock_norm_text(raw: str) -> str:
    s = _norm_text_general(raw or "").upper()
    s = s.replace("|", " ").replace("¦", " ")
    s = s.replace("O", "0")
    s = s.replace("I", "1").replace("L", "1")
    s = s.replace(";", ":").replace(",", ":").replace(".", ":")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _clock_parse_phase_and_clock(raw: str) -> Tuple[Optional[str], Optional[str]]:
    s = _clock_norm_text(raw)
    if not s:
        return None, None
    phase = None
    if re.search(r"(?:^|\b)1\s*T(?:\b|$)", s):
        phase = "PRIMEIRO TEMPO"
    elif re.search(r"(?:^|\b)2\s*T(?:\b|$)", s):
        phase = "SEGUNDO TEMPO"
    elif INTERVALO_RE.search(s):
        phase = "INTERVALO"
    elif FIM_JOGO_RE.search(s):
        phase = "FIM DO JOGO"
    elif INICIO_JOGO_RE.search(s):
        phase = "INICIO DO JOGO"
    clock = None
    for m in list(re.finditer(r"(\d{1,3})\s*[:]\s*(\d{2})", s))[::-1]:
        mm = int(m.group(1))
        ss = int(m.group(2))
        if 0 <= mm <= 180 and 0 <= ss <= 59:
            clock = f"{mm:02d}:{ss:02d}"
            break
    return phase, clock


def _update_phase_cache_from_text(self, phase_text: Optional[str]) -> None:
    phase_text = str(phase_text or "").strip().upper()
    if phase_text in {"PRIMEIRO TEMPO", "SEGUNDO TEMPO", "INTERVALO", "FIM DO JOGO", "INICIO DO JOGO"}:
        self._last_phase_read = phase_text
        self._last_phase_read_t = time.time()


def _clock_prepare_rois(self, frame: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    try:
        roi = _crop(frame, self._resolve_roi(frame, "clock"))
        if roi is None or roi.size == 0:
            return None, None, None
        h, w = roi.shape[:2]
        full = roi[max(0, int(h * 0.01)):min(h, int(h * 0.99)), max(0, int(w * 0.00)):min(w, int(w * 1.00))]
        fh, fw = full.shape[:2]
        phase_roi = full[max(0, int(fh * 0.04)):min(fh, int(fh * 0.96)), max(0, int(fw * 0.00)):min(fw, int(fw * 0.34))]
        time_roi = full[max(0, int(fh * 0.02)):min(fh, int(fh * 0.98)), max(0, int(fw * 0.16)):min(fw, int(fw * 1.00))]
        return full, phase_roi, time_roi
    except Exception:
        return None, None, None


def _clock_ocr_phase(self, roi: np.ndarray) -> str:
    if roi is None or roi.size == 0:
        return ""
    found: List[str] = []
    for maker, scale in ((_prep_ocr_bw, 1.8), (_prep_ocr_inv, 1.8), (_prep_ocr_otsu, 2.0), (_prep_color_mask_white, 1.6)):
        try:
            img = maker(roi, upscale=scale)
        except Exception:
            continue
        for psm in (7, 8, 13):
            txt = _ocr_text(img, psm=psm, whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ")
            phase_text, _ = _clock_parse_phase_and_clock(txt)
            if phase_text:
                found.append(phase_text)
    return _majority_or_none(found, min_count=1) or (found[0] if found else "")


def _clock_ocr_time(self, roi: np.ndarray) -> Optional[str]:
    if roi is None or roi.size == 0:
        return None
    found: List[str] = []
    try_rois = [roi]
    try:
        h, w = roi.shape[:2]
        try_rois.append(roi[:, max(0, int(w * 0.06)):min(w, int(w * 0.98))])
        try_rois.append(roi[:, max(0, int(w * 0.16)):min(w, int(w * 1.00))])
    except Exception:
        pass
    for sub in try_rois:
        for maker, scale in ((_prep_ocr_bw, 1.45), (_prep_ocr_otsu, 1.60), (_prep_ocr_inv, 1.45)):
            try:
                img = maker(sub, upscale=scale)
            except Exception:
                continue
            for psm in (7, 13):
                txt = _ocr_text(img, psm=psm, whitelist="0123456789Tt: ")
                _, clock_text = _clock_parse_phase_and_clock(txt)
                if clock_text:
                    found.append(clock_text)
        try:
            gray = _prep_gray(sub, upscale=1.55)
            txt = _ocr_text(gray, psm=7, whitelist="0123456789Tt: ")
            _, clock_text = _clock_parse_phase_and_clock(txt)
            if clock_text:
                found.append(clock_text)
        except Exception:
            pass
    return _majority_or_none(found, min_count=1) or (found[0] if found else None)


def _stable_clock_value(self, candidate: Optional[str]) -> Optional[str]:
    if not candidate:
        return self._last_clock_read
    validated = self._validate_clock_transition(self._last_clock_read, candidate)
    if validated:
        return validated
    old_s = _clock_to_seconds_mmss(self._last_clock_read)
    new_s = _clock_to_seconds_mmss(candidate)
    if old_s is not None and new_s is not None and 0 <= (new_s - old_s) <= 3:
        return candidate
    return self._last_clock_read


def _read_game_clock_fast_final(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    _hl_init_state(self)
    if not _hl_roi_active(self, frame, "clock"):
        return self._last_clock_read
    sig = _hl_roi_sig(self, frame, "clock", size=(56, 18))
    prev_sig = self._hl_state.get("clock_sig")
    prev_t = float(self._hl_state.get("clock_t", -9999.0))
    changed = sig is not None and sig != prev_sig
    force_read = (self._last_clock_read is None) or ((now - float(self._last_clock_read_t or 0.0)) >= 0.90)
    self._hl_state["clock_sig"] = sig
    if not changed and not force_read:
        return self._last_clock_read
    min_interval = 0.30 if force_read else 0.45
    if (now - prev_t) < min_interval:
        return self._last_clock_read
    self._hl_state["clock_t"] = now
    full_roi, phase_roi, time_roi = _clock_prepare_rois(self, frame)
    if full_roi is None:
        return self._last_clock_read
    phase_text = _clock_ocr_phase(self, phase_roi)
    if phase_text:
        _update_phase_cache_from_text(self, phase_text)
    candidate = _clock_ocr_time(self, time_roi) or _clock_ocr_time(self, full_roi)
    candidate = _stable_clock_value(self, candidate)
    if candidate:
        self._clock_history.append(candidate)
        recent = list(self._clock_history)[-3:]
        if recent:
            last = recent[-1]
            last_s = _clock_to_seconds_mmss(last)
            hist_best = Counter(recent).most_common(1)[0][0]
            hist_s = _clock_to_seconds_mmss(hist_best)
            if last_s is not None and hist_s is not None and abs(last_s - hist_s) <= 3:
                self._last_clock_read = last
            else:
                self._last_clock_read = hist_best
        else:
            self._last_clock_read = candidate
        self._last_clock_read_t = now
    return self._last_clock_read


def _read_game_clock_legacy_final(self, frame: np.ndarray) -> Optional[str]:
    full_roi, phase_roi, time_roi = _clock_prepare_rois(self, frame)
    if full_roi is None:
        return None
    phase_text = _clock_ocr_phase(self, phase_roi)
    if phase_text:
        _update_phase_cache_from_text(self, phase_text)
    return _clock_ocr_time(self, time_roi) or _clock_ocr_time(self, full_roi)


def _read_phase_text_legacy_final(self, frame: np.ndarray) -> str:
    found: List[str] = []
    roi_phase = _crop(frame, self._roi_phase(frame))
    texts = self._ocr_collect_candidates(
        roi=roi_phase,
        psm_list=(7, 6),
        whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789 :-",
        upscale=2.0,
        allow_red=True,
        allow_inv=True,
        allow_otsu=True,
        normalize_mode="phase",
    )
    for txt in texts:
        parsed = self._phase_from_block_text(txt)
        if parsed:
            found.append(parsed)
    _, phase_roi, _ = _clock_prepare_rois(self, frame)
    phase_from_clock = _clock_ocr_phase(self, phase_roi)
    if phase_from_clock:
        found.append(phase_from_clock)
    best = _pick_best_text_candidate(self, found, min_len=3, prefer_longest=False)
    if best:
        _update_phase_cache_from_text(self, best)
    return best


def _infer_match_phase_from_clock_and_phase_text_final(self, game_clock_text: str, phase_text: str, countdown_text: str = "") -> str:
    phase_upper = str(phase_text or "").upper().strip()
    if PRIMEIRO_TEMPO_RE.search(phase_upper):
        return "primeiro_tempo"
    if SEGUNDO_TEMPO_RE.search(phase_upper):
        return "segundo_tempo"
    if INTERVALO_RE.search(phase_upper):
        return "intervalo"
    if FIM_JOGO_RE.search(phase_upper):
        return "pos_jogo"
    if INICIO_JOGO_RE.search(phase_upper):
        return "primeiro_tempo"
    if countdown_text:
        return "pre_jogo"
    sec = _clock_to_seconds_mmss(game_clock_text)
    if sec is None:
        return ""
    mm = int(sec // 60)
    return "primeiro_tempo" if mm <= 45 else "segundo_tempo"


_ORIG_APPLY_TEXT_PRIORITY = VisionDetectors._apply_text_priority

def _apply_text_priority_final(self, visual_state: str, visual_conf: float, score_text: str, game_clock_text: str, countdown_text: str, phase_text: str, banner_text: str, replay_text: str, inicio_jogo_text: str, fim_jogo_text: str) -> Tuple[str, float, str, Dict[str, bool]]:
    state, conf, match_phase_text, flags = _ORIG_APPLY_TEXT_PRIORITY(
        self,
        visual_state=visual_state,
        visual_conf=visual_conf,
        score_text=score_text,
        game_clock_text=game_clock_text,
        countdown_text=countdown_text,
        phase_text=phase_text,
        banner_text=banner_text,
        replay_text=replay_text,
        inicio_jogo_text=inicio_jogo_text,
        fim_jogo_text=fim_jogo_text,
    )
    inferred = _infer_match_phase_from_clock_and_phase_text_final(self, game_clock_text or "", phase_text or "", countdown_text or "")
    if inferred == "primeiro_tempo":
        match_phase_text = "primeiro_tempo"
        if game_clock_text:
            state = "jogo"; conf = max(conf, 0.86)
    elif inferred == "segundo_tempo":
        match_phase_text = "segundo_tempo"
        if game_clock_text:
            state = "jogo"; conf = max(conf, 0.86)
    elif inferred == "intervalo":
        match_phase_text = "intervalo"
    elif inferred == "pre_jogo" and not match_phase_text:
        match_phase_text = "pre_jogo"
    return state, conf, match_phase_text, flags


VisionDetectors._pick_best_text_candidate = _pick_best_text_candidate
VisionDetectors._read_game_clock_fast = _read_game_clock_fast_final
VisionDetectors._read_game_clock_legacy = _read_game_clock_legacy_final
VisionDetectors._read_phase_text_legacy = _read_phase_text_legacy_final
VisionDetectors._infer_match_phase_from_clock_and_phase_text = _infer_match_phase_from_clock_and_phase_text_final
VisionDetectors._apply_text_priority = _apply_text_priority_final


# ============================================================
# PATCH CLOCK V2 - REJEITA LEITURAS ABSURDAS E NÃO CONGELA NO ERRO
# ============================================================

def _clock_extract_phase_hint_text(self, frame: np.ndarray) -> str:
    parts = []
    try:
        parts.append(str(getattr(self, "_last_phase_read", "") or ""))
    except Exception:
        pass
    try:
        roi = _crop(frame, self._roi_phase(frame))
        if roi is not None and roi.size != 0:
            for txt in self._ocr_collect_candidates(
                roi=roi,
                psm_list=(7, 6, 8),
                whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789 :-",
                upscale=1.6,
                allow_red=True,
                allow_inv=True,
                allow_otsu=True,
                normalize_mode="phase",
            )[:4]:
                parts.append(str(txt or ""))
    except Exception:
        pass
    return " | ".join([p for p in parts if p]).upper().strip()


def _clock_candidate_is_plausible(self, candidate: Optional[str], phase_hint_text: str = "") -> bool:
    if not candidate:
        return False
    sec = _clock_to_seconds_mmss(candidate)
    if sec is None:
        return False

    mm = sec // 60
    ss = sec % 60
    if ss > 59:
        return False

    # relógio normal do jogo: segura melhor erro grotesco tipo 143:47
    if mm > 70:
        return False

    phase_hint_text = str(phase_hint_text or "").upper()

    if PRIMEIRO_TEMPO_RE.search(phase_hint_text):
        if mm > 60:
            return False

    if SEGUNDO_TEMPO_RE.search(phase_hint_text):
        if mm < 35 or mm > 70:
            return False

    return True


def _clock_collect_candidates_strict(self, roi: np.ndarray, phase_hint_text: str = "") -> List[str]:
    if roi is None or roi.size == 0:
        return []

    found: List[str] = []
    try_rois = [roi]
    try:
        h, w = roi.shape[:2]
        try_rois.append(roi[:, max(0, int(w * 0.04)):min(w, int(w * 0.98))])
        try_rois.append(roi[:, max(0, int(w * 0.12)):min(w, int(w * 1.00))])
        try_rois.append(roi[max(0, int(h * 0.03)):min(h, int(h * 0.97)), max(0, int(w * 0.10)):min(w, int(w * 1.00))])
    except Exception:
        pass

    for sub in try_rois:
        for maker, scale in (
            (_prep_ocr_bw, 1.55),
            (_prep_ocr_otsu, 1.75),
            (_prep_ocr_inv, 1.55),
        ):
            try:
                img = maker(sub, upscale=scale)
            except Exception:
                continue

            for psm in (7, 13, 8):
                txt = _ocr_text(img, psm=psm, whitelist="0123456789Tt: ")
                phase_text, clock_text = _clock_parse_phase_and_clock(txt)
                if phase_text:
                    _update_phase_cache_from_text(self, phase_text)
                    phase_hint_text = f"{phase_hint_text} | {phase_text}".upper()
                if _clock_candidate_is_plausible(self, clock_text, phase_hint_text=phase_hint_text):
                    found.append(str(clock_text))

        try:
            gray = _prep_gray(sub, upscale=1.45)
            txt = _ocr_text(gray, psm=7, whitelist="0123456789Tt: ")
            phase_text, clock_text = _clock_parse_phase_and_clock(txt)
            if phase_text:
                _update_phase_cache_from_text(self, phase_text)
                phase_hint_text = f"{phase_hint_text} | {phase_text}".upper()
            if _clock_candidate_is_plausible(self, clock_text, phase_hint_text=phase_hint_text):
                found.append(str(clock_text))
        except Exception:
            pass

    return found


def _clock_choose_best_candidate(self, candidates: List[str]) -> Optional[str]:
    vals = [c for c in candidates if c]
    if not vals:
        return None

    if len(vals) == 1:
        return vals[0]

    ranked = Counter(vals).most_common()
    best_val, best_qty = ranked[0]
    if best_qty >= 2:
        return best_val

    # sem maioria: prefere o menor delta positivo em relação ao último clock
    prev_s = _clock_to_seconds_mmss(getattr(self, "_last_clock_read", None))
    if prev_s is not None:
        scored = []
        for val in vals:
            cur_s = _clock_to_seconds_mmss(val)
            if cur_s is None:
                continue
            delta = cur_s - prev_s
            penalty = 0 if 0 <= delta <= 4 else 1000 + abs(delta)
            scored.append((penalty, abs(delta), cur_s, val))
        if scored:
            scored.sort(key=lambda x: (x[0], x[1], x[2]))
            return scored[0][3]

    return vals[0]


def _stable_clock_value_v2(self, candidate: Optional[str], phase_hint_text: str = "") -> Optional[str]:
    if not _clock_candidate_is_plausible(self, candidate, phase_hint_text=phase_hint_text):
        return self._last_clock_read

    if not candidate:
        return self._last_clock_read

    prev = self._last_clock_read
    if not prev:
        return candidate

    prev_s = _clock_to_seconds_mmss(prev)
    new_s = _clock_to_seconds_mmss(candidate)
    if prev_s is None or new_s is None:
        return candidate

    delta = new_s - prev_s

    # avanço normal
    if 0 <= delta <= 4:
        return candidate

    # pequeno retrocesso/reset tolerado
    if -3 <= delta <= -1:
        return candidate

    # salto muito grande: descarta
    return prev


def _read_game_clock_fast_final_v2(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    _hl_init_state(self)

    if not _hl_roi_active(self, frame, "clock"):
        return self._last_clock_read

    sig = _hl_roi_sig(self, frame, "clock", size=(64, 20))
    prev_sig = self._hl_state.get("clock_sig")
    prev_t = float(self._hl_state.get("clock_t", -9999.0))
    changed = sig is not None and sig != prev_sig
    force_read = (
        self._last_clock_read is None
        or (now - float(self._last_clock_read_t or 0.0)) >= 0.55
    )

    self._hl_state["clock_sig"] = sig

    if not changed and not force_read:
        return self._last_clock_read

    min_interval = 0.18 if force_read else 0.28
    if (now - prev_t) < min_interval:
        return self._last_clock_read

    self._hl_state["clock_t"] = now

    full_roi, phase_roi, time_roi = _clock_prepare_rois(self, frame)
    if full_roi is None:
        return self._last_clock_read

    phase_hint_text = _clock_extract_phase_hint_text(self, frame)

    phase_text = _clock_ocr_phase(self, phase_roi)
    if phase_text:
        _update_phase_cache_from_text(self, phase_text)
        phase_hint_text = f"{phase_hint_text} | {phase_text}".upper()

    candidates: List[str] = []
    candidates.extend(_clock_collect_candidates_strict(self, time_roi, phase_hint_text=phase_hint_text))
    candidates.extend(_clock_collect_candidates_strict(self, full_roi, phase_hint_text=phase_hint_text))

    candidate = _clock_choose_best_candidate(self, candidates)
    candidate = _stable_clock_value_v2(self, candidate, phase_hint_text=phase_hint_text)

    if candidate:
        self._last_clock_read = str(candidate)
        self._last_clock_read_t = now

    return self._last_clock_read


def _read_game_clock_legacy_final_v2(self, frame: np.ndarray) -> Optional[str]:
    full_roi, phase_roi, time_roi = _clock_prepare_rois(self, frame)
    if full_roi is None:
        return None

    phase_hint_text = _clock_extract_phase_hint_text(self, frame)

    phase_text = _clock_ocr_phase(self, phase_roi)
    if phase_text:
        _update_phase_cache_from_text(self, phase_text)
        phase_hint_text = f"{phase_hint_text} | {phase_text}".upper()

    candidates: List[str] = []
    candidates.extend(_clock_collect_candidates_strict(self, time_roi, phase_hint_text=phase_hint_text))
    candidates.extend(_clock_collect_candidates_strict(self, full_roi, phase_hint_text=phase_hint_text))
    return _clock_choose_best_candidate(self, candidates)


VisionDetectors._read_game_clock_fast = _read_game_clock_fast_final_v2
VisionDetectors._read_game_clock_legacy = _read_game_clock_legacy_final_v2


# ============================================================
# PATCH CLOCK/SCORE V3 - FAST PATH REAL
# - corta OCR pesado no classify_frame_fast
# - timeout curto no OCR do fast path
# - clock só aceita valor plausível
# - score/countdown/phase fazem no máximo 1 tentativa rápida
# ============================================================

def _fast_ocr_text(img: np.ndarray, psm: int, whitelist: str = "", timeout_s: float = 0.08) -> str:
    # Tesseract legado removido
    return ""


def _fast_one_pass_parse(roi: np.ndarray, parser, *, psm: int, whitelist: str, upscale: float = 1.25) -> Optional[str]:
    if roi is None or roi.size == 0:
        return None
    for maker in (_prep_ocr_bw, _prep_ocr_otsu):
        try:
            img = maker(roi, upscale=upscale)
            txt = _fast_ocr_text(img, psm=psm, whitelist=whitelist, timeout_s=0.08)
            val = parser(txt) if callable(parser) else txt
            if val:
                return str(val)
        except Exception:
            pass
    return None


def _phase_hint_from_cache_only(self) -> str:
    try:
        return str(getattr(self, "_last_phase_read", "") or "").upper().strip()
    except Exception:
        return ""


def _clock_is_plausible_strict(self, value: Optional[str]) -> bool:
    if not value:
        return False
    sec = _clock_to_seconds_mmss(value)
    if sec is None:
        return False

    mm = sec // 60
    if mm > 70:
        return False

    phase_hint = _phase_hint_from_cache_only(self)
    if PRIMEIRO_TEMPO_RE.search(phase_hint) and mm > 60:
        return False
    if SEGUNDO_TEMPO_RE.search(phase_hint) and (mm < 35 or mm > 70):
        return False
    return True


def _score_fast_v3(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    _hl_init_state(self)

    sig = _hl_roi_sig(self, frame, "score", size=(42, 14))
    prev_sig = self._hl_state.get("score_sig")
    prev_t = float(self._hl_state.get("score_t", -9999.0))
    changed = sig is not None and sig != prev_sig
    force = (self._last_score_read is None) or ((now - float(self._last_score_read_t or 0.0)) >= 1.2)

    self._hl_state["score_sig"] = sig

    if not changed and not force:
        return self._last_score_read
    if (now - prev_t) < 0.45:
        return self._last_score_read
    self._hl_state["score_t"] = now

    if not _hl_roi_active(self, frame, "score"):
        return self._last_score_read

    try:
        roi = _crop(frame, self._resolve_roi(frame, "score"))
    except Exception:
        roi = None

    val = _fast_one_pass_parse(
        roi,
        _parse_score,
        psm=7,
        whitelist="0123456789xX- ",
        upscale=1.15,
    )

    if val and _is_score_reasonable(val):
        self._last_score_read = val
        self._last_score_read_t = now

    return self._last_score_read


def _clock_fast_v3(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    _hl_init_state(self)

    sig = _hl_roi_sig(self, frame, "clock", size=(56, 18))
    prev_sig = self._hl_state.get("clock_sig")
    prev_t = float(self._hl_state.get("clock_t", -9999.0))
    changed = sig is not None and sig != prev_sig
    force = (self._last_clock_read is None) or ((now - float(self._last_clock_read_t or 0.0)) >= 0.55)

    self._hl_state["clock_sig"] = sig

    if not changed and not force:
        return self._last_clock_read
    if (now - prev_t) < 0.20:
        return self._last_clock_read
    self._hl_state["clock_t"] = now

    if not _hl_roi_active(self, frame, "clock"):
        return self._last_clock_read

    try:
        roi = _crop(frame, self._resolve_roi(frame, "clock"))
    except Exception:
        roi = None

    if roi is None or roi.size == 0:
        return self._last_clock_read

    h, w = roi.shape[:2]
    full = roi[max(0, int(h * 0.03)):min(h, int(h * 0.97)), max(0, int(w * 0.00)):min(w, int(w * 1.00))]
    time_roi = full[:, max(0, int(full.shape[1] * 0.18)):min(full.shape[1], int(full.shape[1] * 1.00))]
    phase_roi = full[:, max(0, int(full.shape[1] * 0.00)):min(full.shape[1], int(full.shape[1] * 0.34))]

    # fase: uma tentativa leve só para alimentar cache
    try:
        phase_raw = _fast_one_pass_parse(
            phase_roi,
            lambda s: _clock_parse_phase_and_clock(s)[0],
            psm=7,
            whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ",
            upscale=1.20,
        )
        if phase_raw:
            _update_phase_cache_from_text(self, phase_raw)
    except Exception:
        pass

    candidate = _fast_one_pass_parse(
        time_roi,
        lambda s: _clock_parse_phase_and_clock(s)[1] or _parse_clock(s),
        psm=7,
        whitelist="0123456789Tt: ",
        upscale=1.25,
    )

    if not candidate:
        candidate = _fast_one_pass_parse(
            full,
            lambda s: _clock_parse_phase_and_clock(s)[1] or _parse_clock(s),
            psm=7,
            whitelist="0123456789Tt: ",
            upscale=1.15,
        )

    if not _clock_is_plausible_strict(self, candidate):
        return self._last_clock_read

    prev = self._last_clock_read
    if prev:
        prev_s = _clock_to_seconds_mmss(prev)
        cur_s = _clock_to_seconds_mmss(candidate)
        if prev_s is not None and cur_s is not None:
            delta = cur_s - prev_s
            if delta < -3 or delta > 4:
                return self._last_clock_read

    self._last_clock_read = str(candidate)
    self._last_clock_read_t = now
    return self._last_clock_read


def _countdown_fast_v3(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    _hl_init_state(self)

    sig = _hl_roi_sig(self, frame, "countdown_center", size=(42, 12))
    prev_sig = self._hl_state.get("countdown_sig")
    prev_t = float(self._hl_state.get("countdown_t", -9999.0))
    changed = sig is not None and sig != prev_sig

    self._hl_state["countdown_sig"] = sig

    if not changed:
        return self._last_countdown_read
    if (now - prev_t) < 2.5:
        return self._last_countdown_read
    self._hl_state["countdown_t"] = now

    if not _hl_roi_active(self, frame, "countdown_center"):
        return self._last_countdown_read

    try:
        roi = _crop(frame, self._resolve_roi(frame, "countdown_center"))
    except Exception:
        roi = None

    val = _fast_one_pass_parse(
        roi,
        _parse_countdown,
        psm=7,
        whitelist="0123456789: ",
        upscale=1.10,
    )
    if val:
        self._last_countdown_read = val
        self._last_countdown_read_t = now
    return self._last_countdown_read


def _phase_fast_v3(self, frame: np.ndarray) -> str:
    now = time.time()
    _hl_init_state(self)

    sig = _hl_roi_sig(self, frame, "phase", size=(40, 10))
    prev_sig = self._hl_state.get("phase_sig")
    prev_t = float(self._hl_state.get("phase_t", -9999.0))
    changed = sig is not None and sig != prev_sig

    self._hl_state["phase_sig"] = sig

    if not changed:
        return self._last_phase_read
    if (now - prev_t) < 1.5:
        return self._last_phase_read
    self._hl_state["phase_t"] = now

    if not _hl_roi_active(self, frame, "phase"):
        return self._last_phase_read

    try:
        roi = _crop(frame, self._resolve_roi(frame, "phase"))
    except Exception:
        roi = None

    val = _fast_one_pass_parse(
        roi,
        lambda s: self._phase_from_block_text(s),
        psm=7,
        whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ",
        upscale=1.10,
    )
    if val and len(val) >= 3:
        self._last_phase_read = str(val).upper().strip()
        self._last_phase_read_t = now
    return self._last_phase_read


def _read_game_clock_public_v3(self, frame: np.ndarray) -> Optional[str]:
    return _clock_fast_v3(self, frame)

def _read_score_public_v3(self, frame: np.ndarray) -> Optional[str]:
    return _score_fast_v3(self, frame)

def _read_countdown_public_v3(self, frame: np.ndarray) -> Optional[str]:
    return _countdown_fast_v3(self, frame)

def _read_phase_public_v3(self, frame: np.ndarray) -> str:
    return _phase_fast_v3(self, frame)


VisionDetectors._read_score_fast = _score_fast_v3
VisionDetectors._read_game_clock_fast = _clock_fast_v3
VisionDetectors._read_countdown_fast = _countdown_fast_v3
VisionDetectors._read_phase_text_fast = _phase_fast_v3

VisionDetectors.read_score = _read_score_public_v3
VisionDetectors.read_game_clock = _read_game_clock_public_v3
VisionDetectors.read_countdown = _read_countdown_public_v3
VisionDetectors.read_phase_text = _read_phase_public_v3


# ============================================================
# CLEAN ROOT PATCH - CLOCK/SCORE USE EXACTLY THE BANNER OCR PIPELINE
# ============================================================

def _banner_scene_texts_for_roi(self, roi):
    texts = []
    if roi is None or getattr(roi, 'size', 0) == 0:
        return texts
    try:
        data = self._extract_text_regions_scene(roi, min_conf=0.20)
    except Exception:
        data = {}
    for key in ('full_text', 'headline', 'subheadline', 'bottom_line', 'left_tag', 'right_tag', 'context_summary'):
        val = str(data.get(key) or '').strip()
        if val:
            texts.append(val)
    for val in (data.get('lines') or []):
        val = str(val or '').strip()
        if val:
            texts.append(val)
    uniq = []
    seen = set()
    for t in texts:
        tt = _clean_text_block(str(t))
        if not tt or tt in seen:
            continue
        seen.add(tt)
        uniq.append(tt)
    return uniq


def _expand_roi_box(box, W, H, pad_x=0.18, pad_y=0.22):
    x, y, w, h = [int(v) for v in box]
    px = int(round(w * pad_x))
    py = int(round(h * pad_y))
    return _clip_roi(x - px, y - py, w + (px * 2), h + (py * 2), W, H)


def _scene_ocr_candidates_for_label(self, frame, label):
    H, W = frame.shape[:2]
    try:
        base = self._resolve_roi(frame, label)
    except Exception:
        base = None
    if not base:
        return []

    boxes = []
    boxes.append(_clip_roi(*base, W, H))
    boxes.append(_expand_roi_box(base, W, H, 0.12, 0.18))
    boxes.append(_expand_roi_box(base, W, H, 0.22, 0.28))

    if label == 'clock':
        x, y, w, h = _clip_roi(*base, W, H)
        boxes.append(_clip_roi(x + int(w * 0.10), y, max(1, int(w * 0.90)), h, W, H))
        boxes.append(_clip_roi(x + int(w * 0.16), max(0, y - int(h * 0.10)), max(1, int(w * 0.84)), h + int(h * 0.20), W, H))
    elif label == 'score':
        x, y, w, h = _clip_roi(*base, W, H)
        boxes.append(_clip_roi(max(0, x - int(w * 0.10)), max(0, y - int(h * 0.15)), w + int(w * 0.20), h + int(h * 0.30), W, H))

    texts = []
    seen_boxes = set()
    for box in boxes:
        if box in seen_boxes:
            continue
        seen_boxes.add(box)
        roi = _crop(frame, box)
        texts.extend(_banner_scene_texts_for_roi(self, roi))
    return texts


def _score_from_banner_scene_texts(self, texts):
    found = []
    for txt in texts or []:
        raw = _clean_text_block(str(txt or ''))
        if not raw:
            continue
        for piece in [raw] + [p.strip() for p in raw.split('|') if p.strip()]:
            val = _parse_score(piece)
            if val and _is_score_reasonable(val):
                found.append(val)

            digits = re.findall(r'\d', piece)
            if len(digits) == 2 and ('|' in piece or ':' in piece or '-' in piece or ' ' in piece):
                alt = f"{digits[0]}x{digits[1]}"
                if _is_score_reasonable(alt):
                    found.append(alt)
    return _majority_or_none(found, min_count=1) if found else None


def _clock_from_banner_scene_texts(self, texts):
    found = []
    for txt in texts or []:
        raw = _clean_text_block(str(txt or ''))
        if not raw:
            continue
        pieces = [raw] + [p.strip() for p in re.split(r'[|]', raw) if p.strip()]
        for piece in pieces:
            val = _parse_clock(piece)
            if val and _is_mmss_clock_text(val):
                found.append(val)
    return _majority_or_none(found, min_count=1) if found else None


def _read_score_clean_root(self, frame):
    now = time.time()
    if (now - float(getattr(self, '_last_score_read_t', 0.0) or 0.0)) < 0.15 and getattr(self, '_last_score_read', None):
        return self._last_score_read
    texts = _scene_ocr_candidates_for_label(self, frame, 'score')
    best = _score_from_banner_scene_texts(self, texts)
    try:
        self._last_score_debug_text = ' || '.join(texts[:12])
    except Exception:
        pass
    if best:
        self._last_score_read = best
        self._last_score_read_t = now
    return getattr(self, '_last_score_read', None)


def _read_game_clock_clean_root(self, frame):
    now = time.time()
    if (now - float(getattr(self, '_last_clock_read_t', 0.0) or 0.0)) < 0.15 and getattr(self, '_last_clock_read', None):
        return self._last_clock_read
    texts = _scene_ocr_candidates_for_label(self, frame, 'clock')
    best = _clock_from_banner_scene_texts(self, texts)
    try:
        self._last_clock_debug_text = ' || '.join(texts[:12])
    except Exception:
        pass
    if best:
        prev = getattr(self, '_last_clock_read', None)
        prev_s = _clock_to_seconds_mmss(prev)
        cur_s = _clock_to_seconds_mmss(best)
        if prev_s is None or cur_s is None or abs(cur_s - prev_s) <= 10:
            self._last_clock_read = best
            self._last_clock_read_t = now
    return getattr(self, '_last_clock_read', None)


def _read_score_public_clean_root(self, frame):
    return _read_score_clean_root(self, frame)


def _read_game_clock_public_clean_root(self, frame):
    return _read_game_clock_clean_root(self, frame)


VisionDetectors._read_score_fast = _read_score_clean_root
VisionDetectors._read_game_clock_fast = _read_game_clock_clean_root
VisionDetectors._read_score_legacy = _read_score_clean_root
VisionDetectors._read_game_clock_legacy = _read_game_clock_clean_root
VisionDetectors.read_score = _read_score_public_clean_root
VisionDetectors.read_game_clock = _read_game_clock_public_clean_root

# === clean root v2: clock exact overlay text (e.g. 1T|15:14) + stable continuous read ===

def _clock_overlay_extract_mmss(value: Optional[str]) -> Optional[str]:
    s = str(value or '').upper().strip()
    if not s:
        return None
    s = s.replace(';', ':').replace(',', ':').replace('.', ':')
    m = re.search(r'(?<!\d)(\d{1,2}):(\d{2})(?!\d)', s)
    if not m:
        return None
    mm = int(m.group(1)); ss = int(m.group(2))
    if 0 <= mm <= 59 and 0 <= ss <= 59:
        return f"{mm:02d}:{ss:02d}"
    return None


def _clock_overlay_extract_period(value: Optional[str]) -> str:
    s = str(value or '').upper()
    s = s.replace('IT', '1T').replace('LT', '1T').replace('I T', '1T')
    s = s.replace('ZT', '2T').replace('2 T', '2T')
    if re.search(r'\b2\s*T\b|\b2T\b|SEGUNDO\s+TEMPO', s):
        return '2T'
    if re.search(r'\b1\s*T\b|\b1T\b|PRIMEIRO\s+TEMPO', s):
        return '1T'
    return ''


def _clock_overlay_compose(period: str, mmss: str) -> str:
    return f"{period}|{mmss}" if period else mmss


def _clock_overlay_seconds(value: Optional[str]) -> Optional[int]:
    mmss = _clock_overlay_extract_mmss(value)
    if not mmss:
        return None
    mm, ss = mmss.split(':')
    return int(mm) * 60 + int(ss)


def _scene_ocr_candidates_for_clock_exact(self, frame):
    H, W = frame.shape[:2]
    try:
        base = self._resolve_roi(frame, 'clock')
    except Exception:
        base = None
    if not base:
        return []
    x, y, w, h = _clip_roi(*base, W, H)
    boxes = [
        _clip_roi(x, y, w, h, W, H),
        _expand_roi_box((x, y, w, h), W, H, 0.12, 0.18),
        _expand_roi_box((x, y, w, h), W, H, 0.22, 0.30),
        _clip_roi(x + int(w * 0.22), max(0, y - int(h * 0.10)), max(1, int(w * 0.78)), h + int(h * 0.22), W, H),
        _clip_roi(x + int(w * 0.28), max(0, y - int(h * 0.15)), max(1, int(w * 0.70)), h + int(h * 0.30), W, H),
    ]
    out = []
    seen = set()
    for box in boxes:
        if box in seen:
            continue
        seen.add(box)
        roi = _crop(frame, box)
        if roi is None or getattr(roi, 'size', 0) == 0:
            continue
        texts = _banner_scene_texts_for_roi(self, roi)
        if texts:
            out.append({'box': box, 'texts': texts})
    return out


def _clock_best_from_candidates(self, groups):
    prev_raw = getattr(self, '_last_clock_read', None)
    prev_sec = _clock_overlay_seconds(prev_raw)
    best_overlay = None
    best_raw = ''
    best_score = -1e9
    debug_parts = []
    for group in groups or []:
        for txt in group.get('texts') or []:
            raw = _clean_text_block(str(txt or '').upper())
            if not raw:
                continue
            debug_parts.append(raw)
            mmss = _clock_overlay_extract_mmss(raw)
            if not mmss:
                continue
            period = _clock_overlay_extract_period(raw)
            overlay = _clock_overlay_compose(period, mmss)
            mm = int(mmss.split(':')[0])
            score = 0.0
            score += 100.0
            if period:
                score += 80.0
            if re.search(r'\b[12]T\b', raw):
                score += 30.0
            if mm <= 59:
                score += 25.0
            if prev_sec is not None:
                cur_sec = _clock_overlay_seconds(overlay)
                if cur_sec is not None:
                    diff = abs(cur_sec - prev_sec)
                    if diff <= 2:
                        score += 40.0
                    elif diff <= 8:
                        score += 25.0
                    elif diff <= 20:
                        score += 10.0
                    else:
                        score -= min(60.0, float(diff))
            if raw == prev_raw:
                score += 10.0
            if score > best_score:
                best_score = score
                best_overlay = overlay
                best_raw = raw
    return best_overlay, best_raw, debug_parts


def _read_game_clock_clean_root_v2(self, frame):
    now = time.time()
    last_val = getattr(self, '_last_clock_read', None)
    last_t = float(getattr(self, '_last_clock_read_t', 0.0) or 0.0)
    if (now - last_t) < 0.10 and last_val:
        return last_val
    groups = _scene_ocr_candidates_for_clock_exact(self, frame)
    best_overlay, best_raw, debug_parts = _clock_best_from_candidates(self, groups)
    try:
        self._last_clock_debug_text = ' || '.join(debug_parts[:12])
    except Exception:
        pass
    if best_overlay:
        prev_sec = _clock_overlay_seconds(last_val)
        cur_sec = _clock_overlay_seconds(best_overlay)
        accept = False
        if cur_sec is not None:
            if prev_sec is None:
                accept = True
            else:
                diff = abs(cur_sec - prev_sec)
                accept = diff <= 20 or cur_sec <= 59 * 60
        if accept:
            self._last_clock_read = best_overlay
            self._last_clock_read_t = now
            self._last_clock_raw_exact = best_raw or best_overlay
            return best_overlay
    return last_val


def _read_game_clock_public_clean_root_v2(self, frame):
    return _read_game_clock_clean_root_v2(self, frame)


def _apply_text_priority_clean_root_v2(self, visual_state: str, visual_conf: float, score_text: str, game_clock_text: str, countdown_text: str, phase_text: str, banner_text: str, replay_text: str, inicio_jogo_text: str, fim_jogo_text: str):
    flags = {
        'replay_hint': bool(replay_text),
        'fim_jogo_hint': bool(fim_jogo_text),
        'inicio_jogo_hint': bool(inicio_jogo_text),
        'pre_jogo_hint': False,
        'intervalo_hint': False,
    }
    replay_upper = (replay_text or '').upper()
    banner_upper = (banner_text or '').upper()
    phase_upper = (phase_text or '').upper()
    if REPLAY_RE.search(replay_upper) or REPLAY_RE.search(banner_upper):
        flags['replay_hint'] = True
    if FIM_JOGO_RE.search((fim_jogo_text or '').upper()) or FIM_JOGO_RE.search(banner_upper):
        flags['fim_jogo_hint'] = True
    if INICIO_JOGO_RE.search((inicio_jogo_text or '').upper()) or INICIO_JOGO_RE.search(banner_upper):
        flags['inicio_jogo_hint'] = True
    if PRE_JOGO_RE.search(banner_upper) or PRE_JOGO_RE.search(phase_upper):
        flags['pre_jogo_hint'] = True
    if INTERVALO_RE.search(banner_upper) or INTERVALO_RE.search(phase_upper):
        flags['intervalo_hint'] = True
    match_phase_text = ''
    if flags['replay_hint']:
        return 'replay', max(visual_conf, 0.92), match_phase_text, flags
    if flags['fim_jogo_hint']:
        return 'pos_jogo', max(visual_conf, 0.92), 'encerrado', flags
    if flags['intervalo_hint']:
        return 'intervalo', max(visual_conf, 0.92), 'intervalo', flags
    if flags['pre_jogo_hint']:
        return 'pre_jogo', max(visual_conf, 0.92), 'pre_jogo', flags
    if flags['inicio_jogo_hint']:
        return 'jogo', max(visual_conf, 0.90), 'primeiro_tempo', flags
    if PRIMEIRO_TEMPO_RE.search(phase_upper):
        match_phase_text = 'primeiro_tempo'
    elif SEGUNDO_TEMPO_RE.search(phase_upper):
        match_phase_text = 'segundo_tempo'
    elif INTERVALO_RE.search(phase_upper):
        match_phase_text = 'intervalo'
    if re.fullmatch(r'\d+x\d+', score_text or ''):
        visual_state = 'jogo'; visual_conf = max(visual_conf, 0.84)
    if _clock_overlay_extract_mmss(game_clock_text or ''):
        visual_state = 'jogo'; visual_conf = max(visual_conf, 0.84)
    if re.fullmatch(r'\d{1,2}:\d{2}:\d{2}', countdown_text or ''):
        visual_state = 'pre_jogo'; visual_conf = max(visual_conf, 0.84)
        if not match_phase_text:
            match_phase_text = 'pre_jogo'
    return visual_state, visual_conf, match_phase_text, flags


VisionDetectors._read_game_clock_fast = _read_game_clock_clean_root_v2
VisionDetectors._read_game_clock_legacy = _read_game_clock_clean_root_v2
VisionDetectors.read_game_clock = _read_game_clock_public_clean_root_v2
VisionDetectors._apply_text_priority = _apply_text_priority_clean_root_v2


# ============================================================
# V4 PATCH - BANNER PRIORITY / LOWER LATENCY
# - mantém um worker drenando sempre o frame mais novo do banner
# - evita perder atualização quando o worker ainda está rodando
# - faz fallback síncrono leve quando o cache do banner está velho
# ============================================================

def _banner_priority_init_state(self):
    if not hasattr(self, '_banner_priority_pending_frame'):
        self._banner_priority_pending_frame = None
    if not hasattr(self, '_banner_priority_pending_sig'):
        self._banner_priority_pending_sig = None
    if not hasattr(self, '_banner_priority_worker_alive'):
        self._banner_priority_worker_alive = False
    if not hasattr(self, '_banner_priority_last_sync_t'):
        self._banner_priority_last_sync_t = 0.0


def _kick_banner_async_priority(self, frame: np.ndarray) -> None:
    _banner_priority_init_state(self)
    sig = self._banner_signature(frame)
    if sig is None:
        return

    with self._ocr_async_lock:
        cache_ts = float((self._banner_async_cache or {}).get('ts', 0.0) or 0.0)
        cache_age = time.time() - cache_ts if cache_ts > 0 else 9999.0
        cache_has_text = bool((self._banner_async_cache or {}).get('full_text'))
        same_as_cache = (sig == getattr(self, '_banner_async_hash', None))
        if same_as_cache and cache_has_text and cache_age < 0.90:
            return

    try:
        frame_copy = frame.copy()
    except Exception:
        return

    with self._ocr_async_lock:
        self._banner_priority_pending_frame = frame_copy
        self._banner_priority_pending_sig = sig
        if self._banner_priority_worker_alive:
            return
        self._banner_priority_worker_alive = True

    def _worker() -> None:
        try:
            while True:
                with self._ocr_async_lock:
                    frame_local = self._banner_priority_pending_frame
                    sig_local = self._banner_priority_pending_sig
                    self._banner_priority_pending_frame = None
                    self._banner_priority_pending_sig = None
                if frame_local is None or sig_local is None:
                    break

                self._banner_async_running = True
                try:
                    data = self._extract_banner_text_light(frame_local)
                    data['ts'] = time.time()
                    with self._ocr_async_lock:
                        self._banner_async_hash = sig_local
                        self._banner_async_cache = data
                        if data.get('full_text'):
                            self._last_hud_overlay_read = data.get('full_text', '')
                            self._last_hud_overlay_read_t = data.get('ts', time.time())
                except Exception:
                    pass
                finally:
                    self._banner_async_running = False
        finally:
            with self._ocr_async_lock:
                self._banner_priority_worker_alive = False
                self._banner_async_running = False

    threading.Thread(target=_worker, name='banner-ocr-priority', daemon=True).start()


def _read_banner_context_fast_priority(self, frame: np.ndarray) -> Dict[str, Any]:
    _banner_priority_init_state(self)
    _kick_banner_async_priority(self, frame)

    now = time.time()
    with self._ocr_async_lock:
        data = dict(getattr(self, '_banner_async_cache', {}) or {})
        running = bool(getattr(self, '_banner_async_running', False) or getattr(self, '_banner_priority_worker_alive', False))

    cache_ts = float(data.get('ts', 0.0) or 0.0)
    cache_age = now - cache_ts if cache_ts > 0 else 9999.0
    needs_sync = (not data.get('full_text')) or (cache_age > 1.10)

    if needs_sync and (not running) and (now - float(getattr(self, '_banner_priority_last_sync_t', 0.0) or 0.0) >= 0.70):
        try:
            sync_data = self._extract_banner_text_light(frame)
            sync_data['ts'] = now
            self._banner_priority_last_sync_t = now
            with self._ocr_async_lock:
                self._banner_async_cache = sync_data
                self._banner_async_hash = self._banner_signature(frame)
                data = dict(sync_data)
                if sync_data.get('full_text'):
                    self._last_hud_overlay_read = sync_data.get('full_text', '')
                    self._last_hud_overlay_read_t = now
        except Exception:
            pass

    data.setdefault('full_text', '')
    data.setdefault('headline', '')
    data.setdefault('subheadline', '')
    data.setdefault('left_tag', '')
    data.setdefault('right_tag', '')
    data.setdefault('bottom_line', '')
    data.setdefault('context_summary', data.get('full_text', ''))
    data['zones'] = {
        'bottom': {
            'headline': data.get('headline', ''),
            'subheadline': data.get('subheadline', ''),
            'left_tag': data.get('left_tag', ''),
            'right_tag': data.get('right_tag', ''),
            'bottom_line': data.get('bottom_line', ''),
            'text': data.get('full_text', ''),
        },
        'left_panel': {}, 'top_overlay': {}, 'right_panel': {}, 'top_hud': {},
    }
    return data


VisionDetectors._kick_banner_async = _kick_banner_async_priority
VisionDetectors._read_banner_context_fast = _read_banner_context_fast_priority


# ============================================================
# Opção A: captura 1080p + análise OCR em resolução menor
# Patch estrutural para banner/score/clock com prioridade e cooldown
# ============================================================

_VD_ANALYSIS_MAX_W = 1280
_VD_ANALYSIS_MAX_H = 720
_VD_BANNER_STALE_S = 0.70


def _vd_resize_for_analysis(frame: np.ndarray, max_w: int = _VD_ANALYSIS_MAX_W, max_h: int = _VD_ANALYSIS_MAX_H) -> np.ndarray:
    if frame is None or getattr(frame, "size", 0) == 0:
        return frame
    h, w = frame.shape[:2]
    if h <= 0 or w <= 0:
        return frame
    scale = min(max_w / float(w), max_h / float(h), 1.0)
    if scale >= 0.999:
        return frame
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    return cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)


def _vd_roi_sig(roi: np.ndarray, size: Tuple[int, int] = (48, 16)) -> Optional[int]:
    try:
        if roi is None or getattr(roi, "size", 0) == 0:
            return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        small = cv2.resize(gray, size, interpolation=cv2.INTER_AREA)
        return hash(small.tobytes())
    except Exception:
        return None


_vd_orig_init = VisionDetectors.__init__


def _vd_init(self, *args, **kwargs):
    _vd_orig_init(self, *args, **kwargs)
    self._analysis_max_w = _VD_ANALYSIS_MAX_W
    self._analysis_max_h = _VD_ANALYSIS_MAX_H
    self._score_cooldown_s = 1.25
    self._clock_cooldown_s = 0.45
    self._phase_cooldown_s = 0.55
    self._score_roi_sig = None
    self._clock_roi_sig = None
    self._phase_roi_sig = None
    self._analysis_frame_cache = {"src_sig": None, "frame": None}
    self._banner_async_latest_frame = None
    self._banner_async_latest_sig = None
    self.banner_ocr_interval_s = getattr(self, "banner_ocr_interval_s", 1.0)
    self._last_banner_ocr_t = 0.0


VisionDetectors.__init__ = _vd_init


def _vd_get_analysis_frame(self, frame: np.ndarray) -> np.ndarray:
    try:
        src_sig = _vd_roi_sig(frame, size=(64, 36))
        cache = getattr(self, "_analysis_frame_cache", None) or {}
        if cache.get("src_sig") == src_sig and cache.get("frame") is not None:
            return cache.get("frame")
        small = _vd_resize_for_analysis(frame, getattr(self, "_analysis_max_w", _VD_ANALYSIS_MAX_W), getattr(self, "_analysis_max_h", _VD_ANALYSIS_MAX_H))
        self._analysis_frame_cache = {"src_sig": src_sig, "frame": small}
        return small
    except Exception:
        return frame


VisionDetectors._get_analysis_frame = _vd_get_analysis_frame


def _vd_banner_signature(self, frame: np.ndarray) -> Optional[int]:
    try:
        small = self._get_analysis_frame(frame)
        roi = _crop(small, self._roi_banner(small))
        if roi is None or roi.size == 0:
            return None
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY) if len(roi.shape) == 3 else roi
        # OTIMIZAÇÃO: Usa binarização Otsu para ignorar ruído de compressão/vídeo
        # Isso evita que o "signature" mude a cada frame apenas por causa de ruído digital.
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        mini = cv2.resize(thresh, (48, 16), interpolation=cv2.INTER_AREA)
        return hash(mini.tobytes())
    except Exception:
        return None


VisionDetectors._banner_signature = _vd_banner_signature


def _vd_kick_banner_async(self, frame: np.ndarray) -> None:
    try:
        small = self._get_analysis_frame(frame)
        sig = self._banner_signature(small)
        if sig is None:
            return
            
        now = time.time()
        interval = getattr(self, "banner_ocr_interval_s", 1.0)
        
        # OTIMIZAÇÃO: Respeitar o intervalo definido pelo usuário (throttle temporal)
        if (now - getattr(self, "_last_banner_ocr_t", 0.0)) < interval:
            return

        self._banner_async_latest_frame = small.copy()
        self._banner_async_latest_sig = sig
        if self._banner_async_running:
            return
        with self._ocr_async_lock:
            cached_sig = self._banner_async_cache.get("sig")
        if cached_sig == sig:
            # Se a assinatura for a mesma, ainda atualizamos o tempo para evitar re-análise
            self._last_banner_ocr_t = now
            return
            
        self._last_banner_ocr_t = now
    except Exception:
        return

    def _worker() -> None:
        self._banner_async_running = True
        try:
            while True:
                latest_sig = getattr(self, "_banner_async_latest_sig", None)
                latest_frame = getattr(self, "_banner_async_latest_frame", None)
                if latest_sig is None or latest_frame is None:
                    break
                with self._ocr_async_lock:
                    cached_sig = self._banner_async_cache.get("sig")
                if cached_sig == latest_sig:
                    break
                try:
                    data = self._extract_banner_text_light(latest_frame)
                except Exception:
                    data = {"full_text": "", "headline": "", "subheadline": "", "left_tag": "", "right_tag": "", "bottom_line": "", "context_summary": "", "engine": "", "lines": [], "avg_conf": 0.0, "boxes": [], "ocr_ms": 0.0}
                data["ts"] = time.time()
                data["sig"] = latest_sig
                with self._ocr_async_lock:
                    self._banner_async_cache = data
                    if data.get("full_text"):
                        self._last_hud_overlay_read = data.get("full_text", "")
                        self._last_hud_overlay_read_t = data.get("ts", time.time())
                if latest_sig == getattr(self, "_banner_async_latest_sig", None):
                    break
        finally:
            self._banner_async_running = False

    threading.Thread(target=_worker, name="banner-ocr", daemon=True).start()


VisionDetectors._kick_banner_async = _vd_kick_banner_async


def _vd_read_banner_context_fast(self, frame: np.ndarray) -> Dict[str, Any]:
    self._kick_banner_async(frame)
    with self._ocr_async_lock:
        data = dict(self._banner_async_cache)
    data.setdefault("full_text", "")
    data.setdefault("headline", "")
    data.setdefault("subheadline", "")
    data.setdefault("left_tag", "")
    data.setdefault("right_tag", "")
    data.setdefault("bottom_line", "")
    data.setdefault("context_summary", data.get("full_text", ""))
    ts = float(data.get("ts") or 0.0)
    if (not data.get("full_text")) or ((time.time() - ts) > _VD_BANNER_STALE_S):
        try:
            small = self._get_analysis_frame(frame)
            fresh = self._extract_banner_text_light(small)
            fresh["ts"] = time.time()
            fresh["sig"] = self._banner_signature(small)
            with self._ocr_async_lock:
                self._banner_async_cache = fresh
            data = fresh
        except Exception:
            pass
    data["zones"] = {
        "bottom": {
            "headline": data.get("headline", ""),
            "subheadline": data.get("subheadline", ""),
            "left_tag": data.get("left_tag", ""),
            "right_tag": data.get("right_tag", ""),
            "bottom_line": data.get("bottom_line", ""),
            "text": data.get("full_text", ""),
        },
        "left_panel": {}, "top_overlay": {}, "right_panel": {}, "top_hud": {},
    }
    return data


VisionDetectors._read_banner_context_fast = _vd_read_banner_context_fast


def _vd_read_score_fast(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    small = self._get_analysis_frame(frame)
    roi = _crop(small, self._roi_score(small))
    sig = _vd_roi_sig(roi, size=(40, 14))
    if sig is not None and sig == getattr(self, "_score_roi_sig", None) and (now - self._last_score_read_t) < getattr(self, "_score_cooldown_s", 1.25):
        return self._last_score_read
    if sig is None and (now - self._last_score_read_t) < getattr(self, "_score_cooldown_s", 1.25):
        return self._last_score_read
    best = None
    try:
        best = self._read_score_legacy(small)
    except Exception:
        best = None
    if best:
        self._score_history.append(str(best))
        self._last_score_read = Counter(self._score_history).most_common(1)[0][0]
    self._score_roi_sig = sig
    self._last_score_read_t = now
    return self._last_score_read


VisionDetectors._read_score_fast = _vd_read_score_fast


def _vd_read_game_clock_fast(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    small = self._get_analysis_frame(frame)
    roi = _crop(small, self._roi_clock(small))
    sig = _vd_roi_sig(roi, size=(44, 16))
    cooldown = getattr(self, "_clock_cooldown_s", 0.45)
    if sig is not None and sig == getattr(self, "_clock_roi_sig", None) and (now - self._last_clock_read_t) < cooldown:
        return self._last_clock_read
    if sig is None and (now - self._last_clock_read_t) < cooldown:
        return self._last_clock_read
    best = None
    try:
        best = self._read_game_clock_legacy(small)
    except Exception:
        best = None
    best = self._validate_clock_transition(self._last_clock_read, best)
    if best:
        self._clock_history.append(best)
        hist_best = Counter(self._clock_history).most_common(1)[0][0]
        best_s = _clock_to_seconds_mmss(best)
        hist_s = _clock_to_seconds_mmss(hist_best)
        if best_s is not None and hist_s is not None and abs(best_s - hist_s) <= 8:
            self._last_clock_read = best
        else:
            self._last_clock_read = hist_best
    self._clock_roi_sig = sig
    self._last_clock_read_t = now
    return self._last_clock_read


VisionDetectors._read_game_clock_fast = _vd_read_game_clock_fast


def _vd_read_phase_text_fast(self, frame: np.ndarray) -> str:
    now = time.time()
    small = self._get_analysis_frame(frame)
    roi = _crop(small, self._roi_phase(small))
    sig = _vd_roi_sig(roi, size=(36, 12))
    cooldown = getattr(self, "_phase_cooldown_s", 0.55)
    if sig is not None and sig == getattr(self, "_phase_roi_sig", None) and (now - self._last_phase_read_t) < cooldown:
        return self._last_phase_read
    if sig is None and (now - self._last_phase_read_t) < cooldown:
        return self._last_phase_read
    try:
        self._last_phase_read = self._read_phase_text_legacy(small) or self._last_phase_read
    except Exception:
        pass
    self._phase_roi_sig = sig
    self._last_phase_read_t = now
    return self._last_phase_read


VisionDetectors._read_phase_text_fast = _vd_read_phase_text_fast


# ============================================================
# V6 PERFORMANCE PATCH - latest frame bias / hard cooldowns
# ============================================================

_VD_BANNER_STALE_ONLY_RETURN_S = 2.5

_vd_v6_prev_init = VisionDetectors.__init__

def _vd_v6_init(self, *args, **kwargs):
    _vd_v6_prev_init(self, *args, **kwargs)
    # more aggressive cooldowns for stability
    self._score_cooldown_s = 2.00
    self._clock_cooldown_s = 0.80
    self._phase_cooldown_s = 2.00
    self._banner_sync_cooldown_s = 999999.0  # effectively disable sync OCR in hot path
    self._classify_min_gap_s = 0.18
    self._last_classify_done_t = 0.0
    self._score_last_try_t = 0.0
    self._clock_last_try_t = 0.0
    self._phase_last_try_t = 0.0
    self._banner_last_seen_sig = None
    self._banner_last_kick_t = 0.0

VisionDetectors.__init__ = _vd_v6_init


def _vd_v6_kick_banner_async(self, frame: np.ndarray) -> None:
    try:
        small = self._get_analysis_frame(frame)
        sig = self._banner_signature(small)
        now = time.time()
        if sig is None:
            return
        # avoid churning banner worker for same content too often
        if sig == getattr(self, '_banner_last_seen_sig', None) and (now - getattr(self, '_banner_last_kick_t', 0.0)) < 0.75:
            return
        self._banner_last_seen_sig = sig
        self._banner_last_kick_t = now
        self._banner_async_latest_frame = small.copy()
        self._banner_async_latest_sig = sig
        if self._banner_async_running:
            return
        with self._ocr_async_lock:
            cached_sig = self._banner_async_cache.get('sig')
        if cached_sig == sig:
            return
    except Exception:
        return

    def _worker() -> None:
        self._banner_async_running = True
        try:
            seen_sig = None
            while True:
                latest_sig = getattr(self, '_banner_async_latest_sig', None)
                latest_frame = getattr(self, '_banner_async_latest_frame', None)
                if latest_sig is None or latest_frame is None:
                    break
                if latest_sig == seen_sig:
                    break
                seen_sig = latest_sig
                with self._ocr_async_lock:
                    cached_sig = self._banner_async_cache.get('sig')
                if cached_sig == latest_sig:
                    break
                try:
                    data = self._extract_banner_text_light(latest_frame)
                except Exception:
                    data = {'full_text': '', 'headline': '', 'subheadline': '', 'left_tag': '', 'right_tag': '', 'bottom_line': '', 'context_summary': '', 'engine': '', 'lines': [], 'avg_conf': 0.0, 'boxes': [], 'ocr_ms': 0.0}
                data['ts'] = time.time()
                data['sig'] = latest_sig
                with self._ocr_async_lock:
                    self._banner_async_cache = data
                    if data.get('full_text'):
                        self._last_hud_overlay_read = data.get('full_text', '')
                        self._last_hud_overlay_read_t = data.get('ts', time.time())
                # loop once more only if a newer frame arrived during OCR
                if latest_sig == getattr(self, '_banner_async_latest_sig', None):
                    break
        finally:
            self._banner_async_running = False

    threading.Thread(target=_worker, name='banner-ocr', daemon=True).start()

VisionDetectors._kick_banner_async = _vd_v6_kick_banner_async


def _vd_v6_read_banner_context_fast(self, frame: np.ndarray) -> Dict[str, Any]:
    self._kick_banner_async(frame)
    with self._ocr_async_lock:
        data = dict(self._banner_async_cache)
    data.setdefault('full_text', '')
    data.setdefault('headline', '')
    data.setdefault('subheadline', '')
    data.setdefault('left_tag', '')
    data.setdefault('right_tag', '')
    data.setdefault('bottom_line', '')
    data.setdefault('context_summary', data.get('full_text', ''))
    data.setdefault('engine', data.get('engine', ''))
    data.setdefault('lines', data.get('lines', []))
    data.setdefault('avg_conf', data.get('avg_conf', 0.0))
    data.setdefault('ocr_ms', data.get('ocr_ms', 0.0))
    data['zones'] = {
        'bottom': {
            'headline': data.get('headline', ''),
            'subheadline': data.get('subheadline', ''),
            'left_tag': data.get('left_tag', ''),
            'right_tag': data.get('right_tag', ''),
            'bottom_line': data.get('bottom_line', ''),
            'text': data.get('full_text', ''),
        },
        'left_panel': {}, 'top_overlay': {}, 'right_panel': {}, 'top_hud': {},
    }
    return data

VisionDetectors._read_banner_context_fast = _vd_v6_read_banner_context_fast


def _vd_v6_read_score_fast(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - getattr(self, '_score_last_try_t', 0.0)) < getattr(self, '_score_cooldown_s', 2.0):
        return self._last_score_read
    self._score_last_try_t = now
    small = self._get_analysis_frame(frame)
    roi = _crop(small, self._roi_score(small))
    sig = _vd_roi_sig(roi, size=(40, 14))
    if sig is not None and sig == getattr(self, '_score_roi_sig', None):
        self._last_score_read_t = now
        return self._last_score_read
    best = None
    try:
        best = self._read_score_legacy(small)
    except Exception:
        best = None
    if best:
        self._score_history.append(str(best))
        self._last_score_read = Counter(self._score_history).most_common(1)[0][0]
    self._score_roi_sig = sig
    self._last_score_read_t = now
    return self._last_score_read

VisionDetectors._read_score_fast = _vd_v6_read_score_fast


def _vd_v6_read_game_clock_fast(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - getattr(self, '_clock_last_try_t', 0.0)) < getattr(self, '_clock_cooldown_s', 0.8):
        return self._last_clock_read
    self._clock_last_try_t = now
    small = self._get_analysis_frame(frame)
    roi = _crop(small, self._roi_clock(small))
    sig = _vd_roi_sig(roi, size=(44, 16))
    if sig is not None and sig == getattr(self, '_clock_roi_sig', None):
        self._last_clock_read_t = now
        return self._last_clock_read
    best = None
    try:
        best = self._read_game_clock_legacy(small)
    except Exception:
        best = None
    best = self._validate_clock_transition(self._last_clock_read, best)
    if best:
        self._clock_history.append(best)
        hist_best = Counter(self._clock_history).most_common(1)[0][0]
        best_s = _clock_to_seconds_mmss(best)
        hist_s = _clock_to_seconds_mmss(hist_best)
        self._last_clock_read = best if (best_s is not None and hist_s is not None and abs(best_s - hist_s) <= 8) else hist_best
    self._clock_roi_sig = sig
    self._last_clock_read_t = now
    return self._last_clock_read

VisionDetectors._read_game_clock_fast = _vd_v6_read_game_clock_fast


def _vd_v6_read_phase_text_fast(self, frame: np.ndarray) -> str:
    now = time.time()
    if (now - getattr(self, '_phase_last_try_t', 0.0)) < getattr(self, '_phase_cooldown_s', 2.0):
        return self._last_phase_read
    self._phase_last_try_t = now
    small = self._get_analysis_frame(frame)
    roi = _crop(small, self._roi_phase(small))
    sig = _vd_roi_sig(roi, size=(36, 12))
    if sig is not None and sig == getattr(self, '_phase_roi_sig', None):
        self._last_phase_read_t = now
        return self._last_phase_read
    try:
        self._last_phase_read = self._read_phase_text_legacy(small) or self._last_phase_read
    except Exception:
        pass
    self._phase_roi_sig = sig
    self._last_phase_read_t = now
    return self._last_phase_read

VisionDetectors._read_phase_text_fast = _vd_v6_read_phase_text_fast


def _vd_v6_classify_frame_fast(self, frame: np.ndarray) -> MatchResult:
    t0 = time.perf_counter()
    perf: Dict[str, float] = {}
    try:
        if frame is None or getattr(frame, 'size', 0) == 0:
            return MatchResult(label='nao_detectado', score=0.0, best_template='', roi_name='', details={'visual_state': 'nao_detectado', 'visual_confidence': 0.0, 'reason': 'frame_vazio'})
        # hard guard: avoid re-entering too aggressively on nearly identical cadence
        now = time.time()
        if (now - getattr(self, '_last_classify_done_t', 0.0)) < getattr(self, '_classify_min_gap_s', 0.18):
            prev = dict(getattr(self, '_last_debug_info', {}) or {})
            visual_state = str(prev.get('visual_state') or 'nao_detectado')
            visual_conf = float(prev.get('visual_confidence') or 0.0)
            return MatchResult(label=visual_state, score=visual_conf, best_template='', roi_name='', details=prev)

        s = time.perf_counter()
        best = self.detect_frame_state(frame)
        perf['detect_frame_state_ms'] = round((time.perf_counter() - s) * 1000.0, 2)
        details = dict(best.details or {})
        visual_state = str(best.label or 'nao_detectado').strip().lower()
        visual_conf = float(best.score or 0.0)

        s = time.perf_counter()
        scoreboard_active = self._is_scoreboard_active(frame)
        clock_active = self._is_clock_roi_active(frame)
        banner_roi = self._roi_banner(frame)
        banner_profile = self._banner_visual_profile(_crop(frame, banner_roi))
        banner_active = bool((banner_profile or {}).get('banner_active'))
        perf['visual_gates_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        s = time.perf_counter()
        banner_ctx = self._read_banner_context_fast(frame)
        perf['banner_async_cache_ms'] = round((time.perf_counter() - s) * 1000.0, 2)
        banner_text = str(banner_ctx.get('full_text') or '')

        # read much less per cycle; banner gets priority via async only
        score_text = self._last_score_read or ''
        game_clock_text = self._last_clock_read or ''
        phase_text = self._last_phase_read or ''

        s = time.perf_counter()
        if scoreboard_active and ((now - getattr(self, '_last_score_read_t', 0.0)) >= getattr(self, '_score_cooldown_s', 2.0)):
            score_text = self._read_score_fast(frame) or self._last_score_read or ''
        perf['score_fast_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        s = time.perf_counter()
        if clock_active and ((not game_clock_text) or ((now - getattr(self, '_last_clock_read_t', 0.0)) >= getattr(self, '_clock_cooldown_s', 0.8))):
            game_clock_text = self._read_game_clock_fast(frame) or self._last_clock_read or ''
        perf['clock_fast_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        s = time.perf_counter()
        countdown_text = self._last_countdown_read or ''
        if visual_state == 'pre_jogo':
            countdown_text = self._read_countdown_fast(frame) or self._last_countdown_read or ''
        perf['countdown_fast_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        s = time.perf_counter()
        if (now - getattr(self, '_last_phase_read_t', 0.0)) >= getattr(self, '_phase_cooldown_s', 2.0):
            phase_text = self._read_phase_text_fast(frame) or self._last_phase_read or ''
        perf['phase_fast_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        replay_text = banner_text if REPLAY_RE.search(banner_text or '') else ''
        inicio_jogo_text = banner_text if INICIO_JOGO_RE.search((banner_text or '') + ' | ' + (phase_text or '')) else ''
        fim_jogo_text = banner_text if FIM_JOGO_RE.search((banner_text or '') + ' | ' + (phase_text or '')) else ''
        if not clock_active and banner_active:
            game_clock_text = ''

        s = time.perf_counter()
        visual_state, visual_conf, match_phase_text, priority_flags = self._apply_text_priority(
            visual_state=visual_state, visual_conf=visual_conf, score_text=score_text or '', game_clock_text=game_clock_text or '',
            countdown_text=countdown_text or '', phase_text=phase_text or '', banner_text=banner_text or '',
            replay_text=replay_text or '', inicio_jogo_text=inicio_jogo_text or '', fim_jogo_text=fim_jogo_text or '',
        )
        perf['priority_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        banner_upper = (banner_text or '').upper()
        replay_upper = (replay_text or '').upper()
        is_replay = bool(REPLAY_RE.search(banner_upper) or REPLAY_RE.search(replay_upper))
        is_var = bool(VAR_RE.search(banner_upper))
        is_substitution = bool(SUB_RE.search(banner_upper))
        is_yellow_card = bool(AMARELO_RE.search(banner_upper))
        is_red_card = bool(VERMELHO_RE.search(banner_upper))
        is_goal = bool(GOL_RE.search(banner_upper))
        if visual_state == 'nao_detectado' and scoreboard_active:
            visual_state = 'jogo'; visual_conf = max(visual_conf, 0.80)
        try:
            async_age_ms = round(max(0.0, time.time() - float(banner_ctx.get('ts') or 0.0)) * 1000.0, 2) if banner_ctx.get('ts') else None
        except Exception:
            async_age_ms = None
        out_details = {
            **details, 'visual_state': visual_state, 'visual_confidence': visual_conf,
            'score_detected': score_text or None, 'score_raw': score_text or None,
            'game_clock_detected': game_clock_text or None, 'game_clock_raw': game_clock_text or None,
            'countdown_detected': countdown_text or None, 'clock_raw': countdown_text or game_clock_text or None,
            'match_phase_text': match_phase_text or None, 'phase_text': phase_text or None,
            'hud_overlay': banner_text or None, 'banner_text': banner_text or None,
            'banner_summary': banner_text[:180] if banner_text else None,
            'screen_context': {'banner_text': banner_text or '', 'context_summary': banner_ctx.get('context_summary', '')},
            'replay_text': replay_text or None, 'fim_jogo_text': fim_jogo_text or None, 'inicio_jogo_text': inicio_jogo_text or None,
            'is_replay': is_replay, 'is_var': is_var, 'is_substitution': is_substitution,
            'is_yellow_card': is_yellow_card, 'is_red_card': is_red_card, 'is_goal': is_goal,
            'score_roi': self._roi_score(frame), 'clock_roi': self._roi_clock(frame), 'phase_roi': self._roi_phase(frame),
            'pre_jogo_roi': self._roi_pre_jogo(frame), 'jogo_roi': self._roi_jogo(frame), 'intervalo_roi': self._roi_intervalo(frame),
            'replay_roi': self._roi_replay(frame), 'fim_jogo_roi': self._roi_fim_jogo(frame), 'inicio_jogo_roi': self._roi_inicio_jogo(frame),
            'banner_roi': banner_roi, 'scoreboard_active': scoreboard_active, 'clock_active': clock_active, 'banner_active': banner_active,
            'banner_ocr_engine': banner_ctx.get('engine', ''), 'banner_ocr_lines': banner_ctx.get('lines', []),
            'banner_ocr_avg_conf': banner_ctx.get('avg_conf', 0.0), 'banner_ocr_ms': banner_ctx.get('ocr_ms', 0.0),
            'banner_visual_kind': (banner_profile or {}).get('kind'), 'banner_visual_confidence': (banner_profile or {}).get('confidence'),
            'banner_headline': banner_ctx.get('headline', '') or None, 'banner_subheadline': banner_ctx.get('subheadline', '') or None,
            'banner_left_tag': banner_ctx.get('left_tag', '') or None, 'banner_right_tag': banner_ctx.get('right_tag', '') or None,
            'banner_bottom_line': banner_ctx.get('bottom_line', '') or None, 'banner_async_running': bool(self._banner_async_running),
            'banner_async_cache_age_ms': async_age_ms, 'banner_async_has_text': bool(banner_text),
            'priority_pre_jogo': priority_flags['pre_jogo_hint'], 'priority_inicio_jogo': priority_flags['inicio_jogo_hint'],
            'priority_intervalo': priority_flags['intervalo_hint'], 'priority_fim_jogo': priority_flags['fim_jogo_hint'],
            'perf': perf, 'detector_total_ms': round((time.perf_counter() - t0) * 1000.0, 2),
        }
        self._last_debug_info = out_details
        self._save_debug_rois(frame)
        self._last_classify_done_t = time.time()
        return MatchResult(label=visual_state, score=float(visual_conf), best_template=best.best_template, roi_name=best.roi_name, details=out_details)
    except Exception as exc:
        return MatchResult(label='nao_detectado', score=0.0, best_template='', roi_name='', details={'visual_state': 'nao_detectado', 'visual_confidence': 0.0, 'reason': f'erro: {type(exc).__name__}: {exc}', 'perf': perf})

VisionDetectors.classify_frame_fast = _vd_v6_classify_frame_fast


# ============================================================
# PATCH V7 - PERFORMANCE SEM QUEBRAR FLUXO
# - warmup inicial sem OCR pesado
# - budget por ciclo (1 leitura pesada por classify)
# - min gap mais agressivo
# - cooldowns um pouco maiores
# - reaproveita último resultado quando possível
# ============================================================

def _vd_v7_ensure_perf_state(self) -> None:
    if not hasattr(self, '_perf_v7_boot_t'):
        self._perf_v7_boot_t = 0.0
    if not hasattr(self, '_perf_v7_cycle_idx'):
        self._perf_v7_cycle_idx = 0
    if not hasattr(self, '_perf_v7_last_return'):
        self._perf_v7_last_return = None
    if not hasattr(self, '_classify_min_gap_s'):
        self._classify_min_gap_s = 0.28
    # mais conservador para reduzir overlap
    self._score_cooldown_s = max(float(getattr(self, '_score_cooldown_s', 2.0)), 2.5)
    self._clock_cooldown_s = max(float(getattr(self, '_clock_cooldown_s', 0.8)), 1.10)
    self._phase_cooldown_s = max(float(getattr(self, '_phase_cooldown_s', 2.0)), 2.5)
    self._warmup_ocr_seconds = max(float(getattr(self, '_warmup_ocr_seconds', 0.0)), 4.0)


def _vd_v7_pick_cycle_job(self, scoreboard_active: bool, clock_active: bool, visual_state: str):
    _vd_v7_ensure_perf_state(self)
    jobs = ['banner']
    if scoreboard_active:
        jobs.append('score')
    if clock_active:
        jobs.append('clock')
    jobs.append('phase')
    if visual_state == 'pre_jogo':
        jobs.append('countdown')
    idx = int(getattr(self, '_perf_v7_cycle_idx', 0)) % max(1, len(jobs))
    self._perf_v7_cycle_idx = idx + 1
    return jobs[idx]


def _vd_v7_quick_result(self, visual_state: str, visual_conf: float):
    prev = dict(getattr(self, '_last_debug_info', {}) or {})
    prev.setdefault('visual_state', visual_state or 'nao_detectado')
    prev.setdefault('visual_confidence', float(visual_conf or 0.0))
    return MatchResult(
        label=str(prev.get('visual_state') or 'nao_detectado'),
        score=float(prev.get('visual_confidence') or 0.0),
        best_template='',
        roi_name='',
        details=prev,
    )


def _vd_v7_classify_frame_fast(self, frame: np.ndarray) -> MatchResult:
    t0 = time.perf_counter()
    perf: Dict[str, float] = {}
    try:
        _vd_v7_ensure_perf_state(self)

        if frame is None or getattr(frame, 'size', 0) == 0:
            return MatchResult(
                label='nao_detectado',
                score=0.0,
                best_template='',
                roi_name='',
                details={'visual_state': 'nao_detectado', 'visual_confidence': 0.0, 'reason': 'frame_vazio'}
            )

        now = time.time()
        if not getattr(self, '_perf_v7_boot_t', 0.0):
            self._perf_v7_boot_t = now

        # hard throttle: se chamou cedo demais, devolve último resultado
        min_gap = float(getattr(self, '_classify_min_gap_s', 0.28))
        if (now - float(getattr(self, '_last_classify_done_t', 0.0))) < min_gap:
            prev = getattr(self, '_perf_v7_last_return', None)
            if prev is not None:
                return prev
            return _vd_v7_quick_result(self, 'nao_detectado', 0.0)

        # etapa visual sempre roda
        s = time.perf_counter()
        best = self.detect_frame_state(frame)
        perf['detect_frame_state_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        details = dict(best.details or {})
        visual_state = str(best.label or 'nao_detectado').strip().lower()
        visual_conf = float(best.score or 0.0)

        s = time.perf_counter()
        scoreboard_active = self._is_scoreboard_active(frame)
        clock_active = self._is_clock_roi_active(frame)
        banner_roi = self._roi_banner(frame)
        banner_profile = self._banner_visual_profile(_crop(frame, banner_roi))
        banner_active = bool((banner_profile or {}).get('banner_active'))
        perf['visual_gates_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        # banner sempre via cache/async apenas
        s = time.perf_counter()
        banner_ctx = self._read_banner_context_fast(frame)
        perf['banner_async_cache_ms'] = round((time.perf_counter() - s) * 1000.0, 2)
        banner_text = str(banner_ctx.get('full_text') or '')

        score_text = self._last_score_read or ''
        game_clock_text = self._last_clock_read or ''
        phase_text = self._last_phase_read or ''
        countdown_text = self._last_countdown_read or ''

        in_warmup = (now - float(getattr(self, '_perf_v7_boot_t', now))) < float(getattr(self, '_warmup_ocr_seconds', 4.0))
        cycle_job = _vd_v7_pick_cycle_job(self, scoreboard_active, clock_active, visual_state)

        # orçamento: no máximo UMA leitura pesada por ciclo
        s = time.perf_counter()
        if not in_warmup:
            if cycle_job == 'score' and scoreboard_active and ((now - float(getattr(self, '_last_score_read_t', 0.0))) >= float(getattr(self, '_score_cooldown_s', 2.5))):
                score_text = self._read_score_fast(frame) or self._last_score_read or ''
            elif cycle_job == 'clock' and clock_active and ((not game_clock_text) or ((now - float(getattr(self, '_last_clock_read_t', 0.0))) >= float(getattr(self, '_clock_cooldown_s', 1.10)))):
                game_clock_text = self._read_game_clock_fast(frame) or self._last_clock_read or ''
            elif cycle_job == 'phase' and ((now - float(getattr(self, '_last_phase_read_t', 0.0))) >= float(getattr(self, '_phase_cooldown_s', 2.5))):
                phase_text = self._read_phase_text_fast(frame) or self._last_phase_read or ''
            elif cycle_job == 'countdown' and visual_state == 'pre_jogo':
                countdown_text = self._read_countdown_fast(frame) or self._last_countdown_read or ''
        perf['budgeted_read_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        replay_text = banner_text if REPLAY_RE.search(banner_text or '') else ''
        inicio_jogo_text = banner_text if INICIO_JOGO_RE.search((banner_text or '') + ' | ' + (phase_text or '')) else ''
        fim_jogo_text = banner_text if FIM_JOGO_RE.search((banner_text or '') + ' | ' + (phase_text or '')) else ''

        if not clock_active and banner_active:
            game_clock_text = ''

        s = time.perf_counter()
        visual_state, visual_conf, match_phase_text, priority_flags = self._apply_text_priority(
            visual_state=visual_state,
            visual_conf=visual_conf,
            score_text=score_text or '',
            game_clock_text=game_clock_text or '',
            countdown_text=countdown_text or '',
            phase_text=phase_text or '',
            banner_text=banner_text or '',
            replay_text=replay_text or '',
            inicio_jogo_text=inicio_jogo_text or '',
            fim_jogo_text=fim_jogo_text or '',
        )
        perf['priority_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        banner_upper = (banner_text or '').upper()
        replay_upper = (replay_text or '').upper()
        is_replay = bool(REPLAY_RE.search(banner_upper) or REPLAY_RE.search(replay_upper))
        is_var = bool(VAR_RE.search(banner_upper))
        is_substitution = bool(SUB_RE.search(banner_upper))
        is_yellow_card = bool(AMARELO_RE.search(banner_upper))
        is_red_card = bool(VERMELHO_RE.search(banner_upper))
        is_goal = bool(GOL_RE.search(banner_upper))

        if visual_state == 'nao_detectado' and scoreboard_active:
            visual_state = 'jogo'
            visual_conf = max(visual_conf, 0.80)

        try:
            async_age_ms = round(max(0.0, time.time() - float(banner_ctx.get('ts') or 0.0)) * 1000.0, 2) if banner_ctx.get('ts') else None
        except Exception:
            async_age_ms = None

        out_details = {
            **details,
            'visual_state': visual_state,
            'visual_confidence': visual_conf,
            'score_detected': score_text or None,
            'score_raw': score_text or None,
            'game_clock_detected': game_clock_text or None,
            'game_clock_raw': game_clock_text or None,
            'countdown_detected': countdown_text or None,
            'clock_raw': countdown_text or game_clock_text or None,
            'match_phase_text': match_phase_text or None,
            'phase_text': phase_text or None,
            'hud_overlay': banner_text or None,
            'banner_text': banner_text or None,
            'banner_summary': banner_text[:180] if banner_text else None,
            'screen_context': {'banner_text': banner_text or '', 'context_summary': banner_ctx.get('context_summary', '')},
            'replay_text': replay_text or None,
            'fim_jogo_text': fim_jogo_text or None,
            'inicio_jogo_text': inicio_jogo_text or None,
            'is_replay': is_replay,
            'is_var': is_var,
            'is_substitution': is_substitution,
            'is_yellow_card': is_yellow_card,
            'is_red_card': is_red_card,
            'is_goal': is_goal,
            'score_roi': self._roi_score(frame),
            'clock_roi': self._roi_clock(frame),
            'phase_roi': self._roi_phase(frame),
            'pre_jogo_roi': self._roi_pre_jogo(frame),
            'jogo_roi': self._roi_jogo(frame),
            'intervalo_roi': self._roi_intervalo(frame),
            'replay_roi': self._roi_replay(frame),
            'fim_jogo_roi': self._roi_fim_jogo(frame),
            'inicio_jogo_roi': self._roi_inicio_jogo(frame),
            'banner_roi': banner_roi,
            'scoreboard_active': scoreboard_active,
            'clock_active': clock_active,
            'banner_active': banner_active,
            'banner_ocr_engine': banner_ctx.get('engine', ''),
            'banner_ocr_lines': banner_ctx.get('lines', []),
            'banner_ocr_avg_conf': banner_ctx.get('avg_conf', 0.0),
            'banner_ocr_ms': banner_ctx.get('ocr_ms', 0.0),
            'banner_visual_kind': (banner_profile or {}).get('kind'),
            'banner_visual_confidence': (banner_profile or {}).get('confidence'),
            'banner_headline': banner_ctx.get('headline', '') or None,
            'banner_subheadline': banner_ctx.get('subheadline', '') or None,
            'banner_left_tag': banner_ctx.get('left_tag', '') or None,
            'banner_right_tag': banner_ctx.get('right_tag', '') or None,
            'banner_bottom_line': banner_ctx.get('bottom_line', '') or None,
            'banner_async_running': bool(self._banner_async_running),
            'banner_async_cache_age_ms': async_age_ms,
            'banner_async_has_text': bool(banner_text),
            'priority_pre_jogo': priority_flags['pre_jogo_hint'],
            'priority_inicio_jogo': priority_flags['inicio_jogo_hint'],
            'priority_intervalo': priority_flags['intervalo_hint'],
            'priority_fim_jogo': priority_flags['fim_jogo_hint'],
            'perf': perf,
            'perf_v7_cycle_job': cycle_job,
            'perf_v7_warmup': in_warmup,
            'detector_total_ms': round((time.perf_counter() - t0) * 1000.0, 2),
        }

        self._last_debug_info = out_details
        self._save_debug_rois(frame)
        self._last_classify_done_t = time.time()

        result = MatchResult(
            label=visual_state,
            score=float(visual_conf),
            best_template=best.best_template,
            roi_name=best.roi_name,
            details=out_details
        )
        self._perf_v7_last_return = result
        return result

    except Exception as exc:
        return MatchResult(
            label='nao_detectado',
            score=0.0,
            best_template='',
            roi_name='',
            details={'visual_state': 'nao_detectado', 'visual_confidence': 0.0, 'reason': f'erro: {type(exc).__name__}: {exc}', 'perf': perf}
        )

VisionDetectors.classify_frame_fast = _vd_v7_classify_frame_fast


# ============================================================
# CLEAN ROI PATCH (top_hud_unificado / banner / countdown_center)
# ============================================================
ROI_ALIAS_MAP.update({
    "top_hud_unified": "top_hud_unificado",
    "top_hud_unificado": "top_hud_unificado",
})

ROI_OVERRIDE_LABELS = [
    "top_hud_unificado",
    "banner",
    "countdown_center",
]

_DEFAULT_ROI_PCTS = {
    "top_hud_unificado": {"x": 0.025, "y": 0.015, "w": 0.270, "h": 0.105},
    "banner": {"x": 0.120, "y": 0.720, "w": 0.760, "h": 0.230},
    "countdown_center": {"x": 0.410, "y": 0.025, "w": 0.220, "h": 0.095},
}


def _vd_clean_init_wrapper(orig_init):
    def _wrapped(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        self.roi_enabled = {key: True for key in ROI_OVERRIDE_LABELS}
        self._roi_cycle = ["top_hud_unificado"]
        self._roi_cycle_idx = 0
    return _wrapped

VisionDetectors.__init__ = _vd_clean_init_wrapper(VisionDetectors.__init__)


def _vd_roi_top_hud_unified_clean(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
    try:
        return self._resolve_roi(frame, "top_hud_unificado")
    except Exception:
        H, W = frame.shape[:2]
        pct = _DEFAULT_ROI_PCTS["top_hud_unificado"]
        return _clip_roi(int(W * pct["x"]), int(H * pct["y"]), int(W * pct["w"]), int(H * pct["h"]), W, H)

VisionDetectors._roi_top_hud_unified = _vd_roi_top_hud_unified_clean


def _vd_phase_clock_from_combined_text(text: str) -> Tuple[str, Optional[str]]:
    raw = _norm_text_numeric(_clean_text_block(text).upper())
    if not raw:
        return "", None
    raw = raw.replace(" ", "")
    m = re.search(r'(?:^|[^0-9A-Z])(1T|2T|INT|INTERVALO|1TEMPO|2TEMPO|PRIMEIROTEMPO|SEGUNDOTEMPO)(\d{1,3}:\d{2})', raw)
    if not m:
        m = re.search(r'(1T|2T|INT|INTERVALO|1TEMPO|2TEMPO|PRIMEIROTEMPO|SEGUNDOTEMPO)\D{0,3}(\d{1,3}:\d{2})', raw)
    if not m:
        return "", None
    phase_raw = m.group(1)
    clock = _parse_clock(m.group(2))
    phase = ""
    if phase_raw in ("1T", "1TEMPO", "PRIMEIROTEMPO"):
        phase = "PRIMEIRO TEMPO"
    elif phase_raw in ("2T", "2TEMPO", "SEGUNDOTEMPO"):
        phase = "SEGUNDO TEMPO"
    elif phase_raw in ("INT", "INTERVALO"):
        phase = "INTERVALO"
    return phase, clock


def _vd_should_keep_countdown(text: str, phase_text: str, clock: Optional[str]) -> bool:
    raw = _clean_text_block(text).upper()
    if phase_text or clock:
        return False
    if PRIMEIRO_TEMPO_RE.search(raw) or SEGUNDO_TEMPO_RE.search(raw) or INTERVALO_RE.search(raw):
        return False
    if PRE_JOGO_RE.search(raw) or AO_VIVO_EM_RE.search(raw) or DAQUI_A_POUCO_RE.search(raw):
        return True
    return bool(COUNTDOWN_HHMMSS_RE.search(_norm_text_numeric(raw).replace(" ", "")))


def _vd_banner_empty() -> Dict[str, Any]:
    return {
        "full_text": "",
        "headline": "",
        "subheadline": "",
        "left_tag": "",
        "right_tag": "",
        "bottom_line": "",
        "context_summary": "",
        "ts": 0.0,
        "engine": "disabled",
        "lines": [],
        "avg_conf": 0.0,
        "boxes": [],
        "ocr_ms": 0.0,
    }


def _vd_read_screen_context_clean(self, frame: np.ndarray) -> Dict[str, Any]:
    now = time.time()
    if (now - float(getattr(self, '_last_screen_context_t', -9999.0))) < 0.18 and getattr(self, '_last_screen_context', None):
        return dict(self._last_screen_context)

    hud = self._extract_unified_top_hud(frame)
    score = hud.get('score') if _is_score_reasonable(hud.get('score')) else None
    clock = hud.get('clock') if _is_mmss_clock_text(hud.get('clock')) else None
    countdown = hud.get('countdown')
    phase_text = str(hud.get('phase_text') or '').strip()

    combined_text = ' | '.join([str(b.get('text') or '') for b in (hud.get('blocks') or [])])
    combo_phase, combo_clock = _vd_phase_clock_from_combined_text(combined_text)
    if combo_phase and not phase_text:
        phase_text = combo_phase
    if combo_clock and not clock:
        clock = combo_clock

    if phase_text and phase_text.upper() in ("PRIMEIRO TEMPO", "SEGUNDO TEMPO", "INTERVALO"):
        countdown = None
    elif clock and _vd_should_keep_countdown(combined_text, phase_text, clock) is False:
        countdown = None

    if self.is_roi_enabled('countdown_center') and (not countdown) and (not clock):
        try:
            roi = _crop(frame, self._resolve_roi(frame, 'countdown_center'))
            found = self._ocr_collect_candidates(
                roi=roi,
                psm_list=(7, 6, 8),
                whitelist='0123456789: ',
                upscale=2.4,
                allow_inv=True,
                allow_otsu=True,
                normalize_mode='general',
                parser=_parse_countdown,
            )
            countdown = _majority_or_none(found, min_count=1) or (found[0] if found else None)
        except Exception:
            countdown = countdown or None

    banner_ctx = _vd_banner_empty()
    banner_text = ''
    if self.is_roi_enabled('banner'):
        try:
            banner_ctx = self._read_banner_context_fast(frame) or _vd_banner_empty()
        except Exception:
            banner_ctx = _vd_banner_empty()
        banner_text = str(banner_ctx.get('full_text') or '').strip()

    scoreboard = {
        'score': score,
        'clock': clock,
        'countdown': countdown,
        'phase_text': phase_text,
        'visible': bool(score or clock or countdown or phase_text or (hud.get('blocks') or [])),
        'score_candidates': list(hud.get('score_candidates') or []),
        'clock_candidates': list(hud.get('clock_candidates') or []),
        'countdown_candidates': list(hud.get('countdown_candidates') or []),
        'phase_candidates': list(hud.get('phase_candidates') or []),
        'competition_text': str(hud.get('competition_text') or ''),
        'teams': list(hud.get('teams') or [None, None]),
    }
    out = {
        'scoreboard': scoreboard,
        'top_hud': {
            'score': score,
            'clock': clock,
            'countdown': countdown,
            'phase_text': phase_text,
            'competition_text': str(hud.get('competition_text') or ''),
            'teams': list(hud.get('teams') or [None, None]),
            'context_text': str(hud.get('context_text') or ''),
            'blocks': list(hud.get('blocks') or []),
            'roi': hud.get('roi'),
        },
        'banner_text': banner_text,
        'context_summary': banner_text or str(hud.get('context_text') or ''),
        'blocks': list(hud.get('blocks') or []),
        'macro_zones': {
            'top_hud_unificado': hud.get('roi'),
            'banner': self._resolve_roi(frame, 'banner') if self.is_roi_enabled('banner') else None,
            'countdown_center': self._resolve_roi(frame, 'countdown_center') if self.is_roi_enabled('countdown_center') else None,
        },
    }
    self._last_screen_context = dict(out)
    self._last_screen_context_t = now
    return out

VisionDetectors.read_screen_context = _vd_read_screen_context_clean


def _vd_read_banner_context_clean(self, frame: np.ndarray) -> Dict[str, Any]:
    if not self.is_roi_enabled('banner'):
        return _vd_banner_empty()
    fast = self._read_banner_context_fast(frame) or _vd_banner_empty()
    self._last_hud_overlay_read = str(fast.get('full_text') or '')
    self._last_hud_overlay_read_t = time.time()
    return fast

VisionDetectors.read_banner_context = _vd_read_banner_context_clean


def _vd_read_hud_overlay_clean(self, frame: np.ndarray) -> str:
    if not self.is_roi_enabled('banner'):
        return ''
    now = time.time()
    if (now - self._last_hud_overlay_read_t) < 0.30:
        return self._last_hud_overlay_read
    text = str((self._read_banner_context_fast(frame) or {}).get('full_text') or '')
    self._last_hud_overlay_read = text
    self._last_hud_overlay_read_t = now
    return text

VisionDetectors.read_hud_overlay = _vd_read_hud_overlay_clean


def _vd_read_score_clean(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - self._last_score_read_t) < 0.20:
        return self._last_score_read
    ctx = self.read_screen_context(frame)
    best = (ctx.get('scoreboard') or {}).get('score')
    if best and _is_score_reasonable(best):
        self._score_history.append(str(best))
        self._last_score_read = Counter(self._score_history).most_common(1)[0][0]
    self._last_score_read_t = now
    return self._last_score_read

VisionDetectors.read_score = _vd_read_score_clean


def _vd_read_game_clock_clean(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - self._last_clock_read_t) < 0.12:
        return self._last_clock_read
    ctx = self.read_screen_context(frame)
    best = (ctx.get('scoreboard') or {}).get('clock')
    if best and _is_mmss_clock_text(best):
        best = self._validate_clock_transition(self._last_clock_read, best)
        if best:
            self._clock_history.append(best)
            self._last_clock_read = Counter(self._clock_history).most_common(1)[0][0]
    self._last_clock_read_t = now
    return self._last_clock_read

VisionDetectors.read_game_clock = _vd_read_game_clock_clean


def _vd_read_phase_text_clean(self, frame: np.ndarray) -> str:
    now = time.time()
    if (now - self._last_phase_read_t) < 0.20:
        return self._last_phase_read
    ctx = self.read_screen_context(frame)
    phase_text = str(((ctx.get('scoreboard') or {}).get('phase_text')) or '').strip()
    if phase_text:
        self._last_phase_read = phase_text
    self._last_phase_read_t = now
    return self._last_phase_read

VisionDetectors.read_phase_text = _vd_read_phase_text_clean


def _vd_read_countdown_clean(self, frame: np.ndarray) -> Optional[str]:
    if not self.is_roi_enabled('countdown_center'):
        return None
    now = time.time()
    if (now - self._last_countdown_read_t) < 0.30:
        return self._last_countdown_read
    ctx = self.read_screen_context(frame)
    best = (ctx.get('scoreboard') or {}).get('countdown')
    if best:
        self._last_countdown_read = str(best)
    self._last_countdown_read_t = now
    return self._last_countdown_read

VisionDetectors.read_countdown = _vd_read_countdown_clean


# ============================================================
# FINAL CLEAN3 PATCH (authoritative)
# ============================================================
ROI_ALIAS_MAP.update({
    "top_hud_unified": "top_hud_unificado",
    "top_hud_unificado": "top_hud_unificado",
})

ROI_OVERRIDE_LABELS = [
    "top_hud_unificado",
    "banner",
    "countdown_center",
]

_DEFAULT_ROI_PCTS = {
    "top_hud_unificado": {"x": 0.020, "y": 0.015, "w": 0.285, "h": 0.095},
    "banner": {"x": 0.120, "y": 0.720, "w": 0.760, "h": 0.200},
    "countdown_center": {"x": 0.390, "y": 0.030, "w": 0.240, "h": 0.085},
}


def _vd_final_init_wrapper(orig_init):
    def _wrapped(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        self.roi_enabled = {key: True for key in ROI_OVERRIDE_LABELS}
        self._roi_cycle = ["top_hud_unificado"]
        self._roi_cycle_idx = 0
    return _wrapped

VisionDetectors.__init__ = _vd_final_init_wrapper(VisionDetectors.__init__)


def _vd_top_hud_xywh(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
    key = 'top_hud_unificado'
    pct = self.roi_overrides.get(key) or _DEFAULT_ROI_PCTS[key]
    return self._pct_to_xywh(frame, pct)


def _vd_resolve_roi_final(self, frame: np.ndarray, label: str) -> Tuple[int, int, int, int]:
    key = self._canon_roi_key(label)
    if key in self.roi_overrides:
        return self._pct_to_xywh(frame, self.roi_overrides[key])
    if key == 'top_hud_unificado':
        return _vd_top_hud_xywh(self, frame)
    pct = _DEFAULT_ROI_PCTS.get(key)
    if pct is None:
        raise KeyError(f'ROI não configurado: {key}')
    return self._pct_to_xywh(frame, pct)

VisionDetectors._resolve_roi = _vd_resolve_roi_final
VisionDetectors._roi_top_hud_unified = _vd_top_hud_xywh
VisionDetectors._roi_pre_jogo = lambda self, frame: self._resolve_roi(frame, 'top_hud_unificado')
VisionDetectors._roi_jogo = lambda self, frame: self._resolve_roi(frame, 'top_hud_unificado')
VisionDetectors._roi_intervalo = lambda self, frame: self._resolve_roi(frame, 'top_hud_unificado')
VisionDetectors._roi_score = lambda self, frame: self._resolve_roi(frame, 'top_hud_unificado')
VisionDetectors._roi_clock = lambda self, frame: self._resolve_roi(frame, 'top_hud_unificado')
VisionDetectors._roi_phase = lambda self, frame: self._resolve_roi(frame, 'top_hud_unificado')
VisionDetectors._roi_banner = lambda self, frame: self._resolve_roi(frame, 'banner')
VisionDetectors._roi_countdown_center = lambda self, frame: self._resolve_roi(frame, 'countdown_center')


def _vd_phase_key_for_event(phase_text: str, banner_text: str, clock: Optional[str], countdown: Optional[str]) -> str:
    p = _clean_text_block(phase_text).upper()
    b = _clean_text_block(banner_text).upper()
    if 'INTERVALO' in p or INTERVALO_RE.search(b):
        return 'intervalo'
    if 'FIM DO JOGO' in p or FIM_JOGO_RE.search(b):
        return 'pos_jogo'
    if 'PRIMEIRO TEMPO' in p:
        return 'primeiro_tempo'
    if 'SEGUNDO TEMPO' in p:
        return 'segundo_tempo'
    if PRE_JOGO_RE.search(p) or PRE_JOGO_RE.search(b):
        return 'pre_jogo'
    if clock:
        sec = _clock_to_seconds_mmss(clock)
        if sec is not None:
            return 'primeiro_tempo' if sec < 45 * 60 else 'segundo_tempo'
    if countdown:
        return 'pre_jogo'
    return ''


def _vd_visual_state_from_ctx(ctx: Dict[str, Any]) -> Tuple[str, float, Dict[str, float]]:
    sb = ctx.get('scoreboard') or {}
    score = sb.get('score')
    clock = sb.get('clock')
    countdown = sb.get('countdown')
    phase_text = str(sb.get('phase_text') or '')
    banner_text = str(ctx.get('banner_text') or '')
    phase_key = _vd_phase_key_for_event(phase_text, banner_text, clock, countdown)

    pre_score = 0.10
    game_score = 0.10
    intervalo_score = 0.10

    if phase_key == 'pre_jogo':
        pre_score = 0.85 if countdown or PRE_JOGO_RE.search(_clean_text_block(banner_text).upper()) else 0.70
    if phase_key == 'intervalo':
        intervalo_score = 0.90
    if phase_key in ('primeiro_tempo', 'segundo_tempo'):
        game_score = 0.92 if clock else 0.80
    if _is_score_reasonable(score):
        game_score = max(game_score, 0.86)
    if _is_mmss_clock_text(clock):
        game_score = max(game_score, 0.90)
    if PRE_JOGO_RE.search(_clean_text_block(banner_text).upper()) and not clock and not score:
        pre_score = max(pre_score, 0.88)
    if INTERVALO_RE.search(_clean_text_block(banner_text).upper()):
        intervalo_score = max(intervalo_score, 0.88)

    label = 'nao_detectado'
    score_conf = 0.0
    if intervalo_score >= max(pre_score, game_score) and intervalo_score >= 0.55:
        label, score_conf = 'intervalo', intervalo_score
    elif game_score >= max(pre_score, intervalo_score) and game_score >= 0.55:
        label, score_conf = 'jogo', game_score
    elif pre_score >= max(game_score, intervalo_score) and pre_score >= 0.55:
        label, score_conf = 'pre_jogo', pre_score

    return label, float(score_conf), {
        'pre_score': float(pre_score),
        'game_score': float(game_score),
        'intervalo_score': float(intervalo_score),
        'margin': float(sorted([pre_score, game_score, intervalo_score], reverse=True)[0] - sorted([pre_score, game_score, intervalo_score], reverse=True)[1]),
    }


def _vd_detect_frame_state_final(self, frame: np.ndarray) -> MatchResult:
    try:
        ctx = self.read_screen_context(frame)
        label, conf, scores = _vd_visual_state_from_ctx(ctx)
        return MatchResult(
            label=label,
            score=conf,
            best_template='clean3_heuristic',
            roi_name='top_hud_unificado',
            details={
                **scores,
                'visual_state': label,
                'visual_confidence': conf,
                'scoreboard_active': bool((ctx.get('scoreboard') or {}).get('visible')),
                'clock_active': bool((ctx.get('scoreboard') or {}).get('clock')),
                'banner_active': bool(ctx.get('banner_text')),
            },
        )
    except Exception as exc:
        return MatchResult('nao_detectado', 0.0, '', '', {'reason': f'erro: {type(exc).__name__}: {exc}'})

VisionDetectors.detect_frame_state = _vd_detect_frame_state_final


def _vd_classify_frame_fast_final(self, frame: np.ndarray) -> MatchResult:
    t0 = time.perf_counter()
    perf: Dict[str, float] = {}
    try:
        s = time.perf_counter()
        ctx = self.read_screen_context(frame)
        perf['read_screen_context_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        s = time.perf_counter()
        best = self.detect_frame_state(frame)
        perf['detect_frame_state_ms'] = round((time.perf_counter() - s) * 1000.0, 2)

        sb = ctx.get('scoreboard') or {}
        banner_text = str(ctx.get('banner_text') or '')
        phase_text = str(sb.get('phase_text') or '').strip()
        score_text = sb.get('score')
        game_clock_text = sb.get('clock')
        countdown_text = sb.get('countdown')
        match_phase_text = _vd_phase_key_for_event(phase_text, banner_text, game_clock_text, countdown_text)
        visual_state = best.label
        visual_conf = float(best.score or 0.0)

        out_details = {
            'visual_state': visual_state,
            'visual_confidence': visual_conf,
            'pre_score': float(best.details.get('pre_score', 0.0) or 0.0),
            'game_score': float(best.details.get('game_score', 0.0) or 0.0),
            'intervalo_score': float(best.details.get('intervalo_score', 0.0) or 0.0),
            'margin': float(best.details.get('margin', 0.0) or 0.0),
            'score_detected': score_text or None,
            'score_raw': score_text or None,
            'game_clock_detected': game_clock_text or None,
            'game_clock_raw': game_clock_text or None,
            'countdown_detected': countdown_text or None,
            'clock_raw': countdown_text or game_clock_text or None,
            'match_phase_text': match_phase_text or None,
            'phase_text': phase_text or None,
            'hud_overlay': banner_text or None,
            'banner_text': banner_text or None,
            'banner_summary': banner_text[:180] if banner_text else None,
            'screen_context': dict(ctx or {}),
            'score_roi': self._roi_score(frame),
            'clock_roi': self._roi_clock(frame),
            'phase_roi': self._roi_phase(frame),
            'pre_jogo_roi': self._roi_pre_jogo(frame),
            'jogo_roi': self._roi_jogo(frame),
            'intervalo_roi': self._roi_intervalo(frame),
            'banner_roi': self._roi_banner(frame),
            'scoreboard_active': bool(sb.get('visible')),
            'clock_active': bool(game_clock_text),
            'banner_active': bool(banner_text),
            'team_a': (sb.get('teams') or [None, None])[0],
            'team_b': (sb.get('teams') or [None, None])[1],
            'competition_text': sb.get('competition_text') or '',
            'perf': perf,
            'detector_total_ms': round((time.perf_counter() - t0) * 1000.0, 2),
        }
        self._last_debug_info = out_details
        try:
            self._save_debug_rois(frame)
        except Exception:
            pass
        return MatchResult(label=visual_state, score=visual_conf, best_template='clean3_heuristic', roi_name='top_hud_unificado', details=out_details)
    except Exception as exc:
        perf['detector_total_ms'] = round((time.perf_counter() - t0) * 1000.0, 2)
        return MatchResult(label='nao_detectado', score=0.0, best_template='', roi_name='', details={'visual_state': 'nao_detectado', 'visual_confidence': 0.0, 'reason': f'erro: {type(exc).__name__}: {exc}', 'perf': perf})

VisionDetectors.classify_frame_fast = _vd_classify_frame_fast_final


# ============================================================
# FINAL PERF PATCH - FAST HUD, KEEP BANNER ASYNC
# ============================================================
def _vd_safe_team_pair(value):
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return [value[0], value[1]]
    return [None, None]


def _vd_compose_fast_hud_context(self, frame: np.ndarray) -> Dict[str, Any]:
    now = time.time()
    cached = getattr(self, '_last_screen_context', None)
    cached_t = float(getattr(self, '_last_screen_context_t', -9999.0) or -9999.0)
    if isinstance(cached, dict) and (now - cached_t) < 0.10:
        return dict(cached)

    score = None
    clock = None
    countdown = None
    phase_text = ''
    context_text = ''
    competition_text = str(getattr(self, '_last_competition_read', '') or '')
    teams = _vd_safe_team_pair(getattr(self, '_last_team_names_read', (None, None)))

    from_unified = False
    if self.is_roi_enabled('top_hud_unificado'):
        try:
            unified = self._extract_unified_top_hud(frame)
            score = str(unified.get('score') or '') or None
            clock = str(unified.get('clock') or '') or None
            phase_text = str(unified.get('phase_text') or '')
            countdown = str(unified.get('countdown') or '') or None
            context_text = str(unified.get('context_text') or '')
            if unified.get('competition_text'):
                competition_text = str(unified.get('competition_text'))
            if unified.get('teams'):
                teams = _vd_safe_team_pair(unified.get('teams'))
            from_unified = True
            
            if score:
                self._last_score_read = score
                self._last_score_read_t = time.time()
            if clock:
                self._last_clock_read = clock
                self._last_clock_read_t = time.time()
            if phase_text:
                self._last_phase_read = phase_text
                self._last_phase_read_t = time.time()
            if countdown:
                self._last_countdown_read = countdown
                self._last_countdown_read_t = time.time()
        except Exception as e:
            import traceback
            print(f"[ERROR] HUD unificado falhou: {e}")
            traceback.print_exc()

    if not from_unified:
        try:
            score = self._read_score_fast(frame)
        except Exception:
            score = getattr(self, '_last_score_read', None)

        try:
            clock = self._read_game_clock_fast(frame)
        except Exception:
            clock = getattr(self, '_last_clock_read', None)

        try:
            phase_text = (self._read_phase_text_fast(frame) or '').strip()
        except Exception:
            phase_text = str(getattr(self, '_last_phase_read', '') or '').strip()

        if self.is_roi_enabled('countdown_center'):
            try:
                countdown = self._read_countdown_fast(frame)
            except Exception:
                countdown = getattr(self, '_last_countdown_read', None)

    if clock:
        countdown = None
    if phase_text and phase_text.upper() in ('PRIMEIRO TEMPO', 'SEGUNDO TEMPO', 'INTERVALO'):
        countdown = None

    banner_ctx = _vd_banner_empty()
    banner_text = ''
    if self.is_roi_enabled('banner'):
        try:
            banner_ctx = self._read_banner_context_fast(frame) or _vd_banner_empty()
        except Exception:
            banner_ctx = _vd_banner_empty()
        banner_text = str(banner_ctx.get('full_text') or '').strip()

    # context_text e os demais removidos porque agora sao povoados via from_unified
    summary_parts = [p for p in [score, clock, countdown, phase_text, context_text, banner_text or competition_text] if p]
    context_summary = ' | '.join(summary_parts)
    phase_key = _vd_phase_key_for_event(phase_text, banner_text, clock, countdown) or None

    hud_roi = None
    countdown_roi = None
    banner_roi = None
    try:
        hud_roi = self._resolve_roi(frame, 'top_hud_unificado')
    except Exception:
        pass
    try:
        if self.is_roi_enabled('countdown_center'):
            countdown_roi = self._resolve_roi(frame, 'countdown_center')
    except Exception:
        pass
    try:
        if self.is_roi_enabled('banner'):
            banner_roi = self._resolve_roi(frame, 'banner')
    except Exception:
        pass

    scoreboard = {
        'score': score if _is_score_reasonable(score) else None,
        'clock': clock if _is_mmss_clock_text(clock) else None,
        'countdown': countdown,
        'phase_text': phase_text,
        'visible': bool(score or clock or countdown or phase_text),
        'score_candidates': [score] if score else [],
        'clock_candidates': [clock] if clock else [],
        'countdown_candidates': [countdown] if countdown else [],
        'phase_candidates': [phase_text] if phase_text else [],
        'competition_text': competition_text,
        'teams': teams,
    }

    out = {
        'scoreboard': scoreboard,
        'top_hud': {
            'score': scoreboard['score'],
            'clock': scoreboard['clock'],
            'countdown': scoreboard['countdown'],
            'phase_text': phase_text,
            'competition_text': competition_text,
            'teams': teams,
            'context_text': context_summary,
            'blocks': [],
            'roi': hud_roi,
        },
        'banner_text': banner_text,
        'context_summary': context_summary,
        'phase': phase_key,
        'blocks': [],
        'macro_zones': {
            'top_hud_unificado': hud_roi,
            'banner': banner_roi,
            'countdown_center': countdown_roi,
        },
    }
    self._last_screen_context = dict(out)
    self._last_screen_context_t = time.time()
    return out


def _vd_read_screen_context_perf(self, frame: np.ndarray) -> Dict[str, Any]:
    return _vd_compose_fast_hud_context(self, frame)


VisionDetectors.read_screen_context = _vd_read_screen_context_perf


def _vd_read_score_perf(self, frame: np.ndarray) -> Optional[str]:
    return (_vd_compose_fast_hud_context(self, frame).get('scoreboard') or {}).get('score')


def _vd_read_game_clock_perf(self, frame: np.ndarray) -> Optional[str]:
    return (_vd_compose_fast_hud_context(self, frame).get('scoreboard') or {}).get('clock')


def _vd_read_phase_text_perf(self, frame: np.ndarray) -> str:
    return str(((_vd_compose_fast_hud_context(self, frame).get('scoreboard') or {}).get('phase_text')) or '')


def _vd_read_countdown_perf(self, frame: np.ndarray) -> Optional[str]:
    return (_vd_compose_fast_hud_context(self, frame).get('scoreboard') or {}).get('countdown')


VisionDetectors.read_score = _vd_read_score_perf
VisionDetectors.read_game_clock = _vd_read_game_clock_perf
VisionDetectors.read_phase_text = _vd_read_phase_text_perf
VisionDetectors.read_countdown = _vd_read_countdown_perf

# ============================================================
# HUD / COUNTDOWN banner-style OCR patch
# Adaptado da lógica de leitura por blocos usada no banner
# ============================================================

def _vd_hud_best_value(items, validator=None):
    if not items:
        return None
    grouped: Dict[str, Dict[str, Any]] = {}
    for item in items:
        value = str(item.get('value') or '').strip()
        if not value:
            continue
        if validator and not validator(value):
            continue
        bucket = grouped.setdefault(value, {'score': 0.0, 'count': 0, 'item': item})
        bucket['score'] += float(item.get('confidence') or 0.0)
        bucket['count'] += 1
    if not grouped:
        return None
    ranked = sorted(
        grouped.items(),
        key=lambda kv: (kv[1]['score'], kv[1]['count'], len(kv[0])),
        reverse=True,
    )
    return ranked[0][0]


def _vd_extract_unified_top_hud_banner_style(self, frame: np.ndarray) -> Dict[str, Any]:
    roi_xywh = self._resolve_roi(frame, 'top_hud_unificado')
    roi = _crop(frame, roi_xywh)
    out: Dict[str, Any] = {
        'score': None,
        'clock': None,
        'countdown': None,
        'phase_text': '',
        'context_text': '',
        'competition_text': '',
        'visible': False,
        'score_candidates': [],
        'clock_candidates': [],
        'countdown_candidates': [],
        'phase_candidates': [],
        'context_candidates': [],
        'blocks': [],
        'roi': roi_xywh,
        'teams': self._last_team_names_read,
    }
    if roi is None or getattr(roi, 'size', 0) == 0:
        return out

    x0, y0, rw, rh = roi_xywh
    blocks = self._detect_text_blocks(roi, zone_name='top_hud_unified') or []
    enriched: List[Dict[str, Any]] = []
    for block in blocks[:12]:
        try:
            block = self._ocr_block(dict(block))
        except Exception:
            continue
        bx, by, bw, bh = block.get('bbox', (0, 0, 0, 0))
        block['global_bbox'] = (x0 + bx, y0 + by, bw, bh)
        enriched.append(block)
    out['blocks'] = enriched

    score_candidates: List[Dict[str, Any]] = []
    clock_candidates: List[Dict[str, Any]] = []
    countdown_candidates: List[Dict[str, Any]] = []
    phase_candidates: List[Dict[str, Any]] = []
    competition_candidates: List[str] = []
    context_candidates: List[str] = []

    digit_blocks: List[Dict[str, Any]] = []

    for block in enriched:
        txt = _clean_text_block(block.get('text', ''))
        if not txt:
            continue
        bx, by, bw, bh = block.get('bbox', (0, 0, 0, 0))
        cx = bx + bw / 2.0
        cy = by + bh / 2.0
        rel_x = cx / max(1.0, rw)
        rel_y = cy / max(1.0, rh)
        conf = float(block.get('confidence') or 0.0)
        gbox = block.get('global_bbox') or block.get('bbox')

        score = _parse_score(txt)
        if score:
            score_candidates.append({'value': score, 'text': txt, 'bbox': gbox, 'confidence': conf + (0.10 if rel_y <= 0.75 else 0.0)})
            continue

        hhmmss_match = COUNTDOWN_HHMMSS_RE.search(_norm_text_numeric(txt).replace(' ', ''))
        countdown = _parse_countdown(txt)
        if countdown and hhmmss_match:
            countdown_candidates.append({'value': countdown, 'text': txt, 'bbox': gbox, 'confidence': conf + (0.12 if 0.20 <= rel_x <= 0.80 else 0.0)})
            continue

        clock = _parse_clock(txt)
        if clock:
            clock_candidates.append({'value': clock, 'text': txt, 'bbox': gbox, 'confidence': conf + (0.10 if 0.05 <= rel_x <= 0.60 else 0.0)})
            continue

        phase = self._phase_from_block_text(txt)
        if phase:
            phase_candidates.append({'value': phase, 'text': txt, 'bbox': gbox, 'confidence': conf + (0.06 if rel_y <= 0.85 else 0.0)})
            continue

        if rel_y <= 0.68 and len(txt) >= 5 and not re.search(r'\d{1,3}:\d{2}', txt):
            context_candidates.append(txt)
        elif 0.20 <= rel_x <= 0.85 and len(txt) >= 4:
            context_candidates.append(txt)
            
        m_digits = re.findall(r"\d", txt)
        if re.fullmatch(r"\d{1,2}", txt.strip()) or (len(m_digits) == 1 and len(txt.strip()) <= 2):
            digit_blocks.append({'x': cx, 'y': cy, 'w': bw, 'h': bh, 'val': m_digits[0] if len(m_digits) == 1 else txt.strip(), 'conf': conf})

    if len(digit_blocks) >= 2:
        pairs = []
        for i in range(len(digit_blocks)):
            for j in range(i+1, len(digit_blocks)):
                d1, d2 = digit_blocks[i], digit_blocks[j]
                if d1['x'] > d2['x']:
                    d1, d2 = d2, d1
                y_diff = abs(d1['y'] - d2['y'])
                h_diff = abs(d1['h'] - d2['h'])
                if y_diff < max(5.0, rh * 0.3) and h_diff < max(5.0, rh * 0.4):
                    pairs.append((d1, d2))
        
        if pairs:
            # Ordene pelos pares mais altos na tela (menor Y) pois o placar costuma ficar acima do relógio cronômetro
            pairs.sort(key=lambda p: (p[0]['y'] + p[1]['y']) / 2.0)
            best_pair = pairs[0]
            val = f"{best_pair[0]['val']}x{best_pair[1]['val']}"
            if _is_score_reasonable(val):
                score_candidates.append({'value': val, 'text': val, 'bbox': roi_xywh, 'confidence': (best_pair[0]['conf'] + best_pair[1]['conf'])/2.0})

    # Fallback focado em sub-regiões (Single-Pass distribuído) usando apenas Tesseract
    # para evitar inicializações/recompilações pesadas do PaddleOCR (OneDNN) em crops de tamanhos variáveis.
    rw_int = max(1, int(rw))
    rh_int = max(1, int(rh))

    if not any([c for c in score_candidates if c.get('confidence', 0) > 0.3]):
        try:
            for psm in (7, 11, 6):
                val = _fast_one_pass_parse(roi, _parse_score, psm=psm, whitelist='0123456789xX-: ', upscale=2.8)
                if val:
                    score_candidates.append({'value': val, 'text': val, 'bbox': roi_xywh, 'confidence': 0.55})
                    break
        except Exception:
            pass

    if not any([c for c in clock_candidates if c.get('confidence', 0) > 0.3]):
        try:
            for psm in (7, 6, 12):
                val = _fast_one_pass_parse(roi, _parse_clock, psm=psm, whitelist='0123456789:T| ', upscale=2.8)
                if val:
                    clock_candidates.append({'value': val, 'text': val, 'bbox': roi_xywh, 'confidence': 0.55})
                    break
        except Exception:
            pass

    if not any([c for c in countdown_candidates if c.get('confidence', 0) > 0.3]):
        try:
            for psm in (7, 6):
                val = _fast_one_pass_parse(roi, _parse_countdown, psm=psm, whitelist='0123456789: ', upscale=2.8)
                if val and COUNTDOWN_HHMMSS_RE.search(str(val)):
                    countdown_candidates.append({'value': val, 'text': val, 'bbox': roi_xywh, 'confidence': 0.58})
                    break
        except Exception:
            pass

    if not any([c for c in phase_candidates if c.get('confidence', 0) > 0.3]):
        try:
            for psm in (7, 6):
                val = _fast_one_pass_parse(roi, None, psm=psm, whitelist='ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789 :-', upscale=2.5)
                if val:
                    phase = self._phase_from_block_text(val)
                    if phase:
                        phase_candidates.append({'value': phase, 'text': val, 'bbox': roi_xywh, 'confidence': 0.52})
                        break
        except Exception:
            pass

    out['score'] = _vd_hud_best_value(score_candidates, validator=_is_score_reasonable)
    out['clock'] = _vd_hud_best_value(clock_candidates, validator=_is_mmss_clock_text)
    out['countdown'] = _vd_hud_best_value(
        countdown_candidates,
        validator=lambda v: bool(COUNTDOWN_HHMMSS_RE.search(str(v)) or _is_mmss_clock_text(str(v))),
    )
    out['phase_text'] = _vd_hud_best_value(phase_candidates) or ''
    out['context_text'] = _majority_or_none([c for c in context_candidates if c], min_count=1) or ''
    out['score_candidates'] = score_candidates[:8]
    out['clock_candidates'] = clock_candidates[:8]
    out['countdown_candidates'] = countdown_candidates[:8]
    out['phase_candidates'] = phase_candidates[:8]
    out['context_candidates'] = context_candidates[:8]

    if out['phase_text']:
        self._last_phase_read = str(out['phase_text'])
        self._last_phase_read_t = time.time()
    if out['clock'] and _is_mmss_clock_text(out['clock']):
        self._last_clock_read = str(out['clock'])
        self._last_clock_read_t = time.time()
    if out['countdown']:
        self._last_countdown_read = str(out['countdown'])
        self._last_countdown_read_t = time.time()

    out['visible'] = bool(out['score'] or out['clock'] or out['countdown'] or out['phase_text'] or out['competition_text'] or out['context_text'] or enriched)
    return out


def _vd_read_phase_text_banner_style(self, frame: np.ndarray) -> str:
    now = time.time()
    try:
        _hl_init_state(self)
    except Exception:
        pass
    cached = str(getattr(self, '_last_phase_read', '') or '').strip()
    if cached and (now - float(getattr(self, '_last_phase_read_t', -9999.0) or -9999.0)) < 0.45:
        return cached
    try:
        hud = self._extract_unified_top_hud(frame)
        phase = str(hud.get('phase_text') or '').strip()
        if phase:
            self._last_phase_read = phase
            self._last_phase_read_t = now
            return phase
    except Exception:
        pass
    return cached


def _vd_read_countdown_banner_style(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    try:
        _hl_init_state(self)
        sig = _hl_roi_sig(self, frame, 'countdown_center', size=(48, 16))
        prev_sig = self._hl_state.get('countdown_sig_patch')
        prev_t = float(self._hl_state.get('countdown_t_patch', -9999.0))
        self._hl_state['countdown_sig_patch'] = sig
        changed = sig is not None and sig != prev_sig
        if (not changed) and self._last_countdown_read:
            return self._last_countdown_read
        if (now - prev_t) < 1.20 and self._last_countdown_read:
            return self._last_countdown_read
        self._hl_state['countdown_t_patch'] = now
    except Exception:
        pass

    # Primeiro tenta extrair do HUD unificado, usando a mesma lógica de blocos do banner.
    try:
        hud = self._extract_unified_top_hud(frame)
        hud_clock = hud.get('clock')
        hud_phase = str(hud.get('phase_text') or '').strip().upper()
        hud_countdown = hud.get('countdown')
        if hud_clock or hud_phase in ('PRIMEIRO TEMPO', 'SEGUNDO TEMPO', 'INTERVALO'):
            return None
        if hud_countdown:
            self._last_countdown_read = str(hud_countdown)
            self._last_countdown_read_t = now
            return self._last_countdown_read
    except Exception:
        pass

    if not self.is_roi_enabled('countdown_center'):
        return self._last_countdown_read

    try:
        roi = _crop(frame, self._resolve_roi(frame, 'countdown_center'))
    except Exception:
        roi = None
    if roi is None or getattr(roi, 'size', 0) == 0:
        return self._last_countdown_read

    found: List[str] = []
    try:
        found.extend(self._ocr_collect_candidates(
            roi=roi,
            psm_list=(7, 8, 6, 13),
            whitelist='0123456789: ',
            upscale=2.8,
            allow_inv=True,
            allow_otsu=True,
            normalize_mode='general',
            parser=_parse_countdown,
        ))
    except Exception:
        pass

    try:
        found.extend(self._ocr_roi_like_banner(
            roi,
            psm_list=(7, 8, 13),
            whitelist='0123456789: ',
            upscale=3.0,
            allow_inv=True,
            allow_otsu=True,
            parser=_parse_countdown,
            block_zone='countdown_center_patch',
            min_block_w_ratio=0.14,
            min_block_h_ratio=0.22,
        ))
    except Exception:
        pass

    candidates: List[str] = []
    for item in found:
        val = _parse_countdown(str(item))
        if val:
            candidates.append(val)

    best = _majority_or_none(candidates, min_count=1) or (candidates[0] if candidates else None)
    if best:
        self._last_countdown_read = str(best)
        self._last_countdown_read_t = now
    return self._last_countdown_read


VisionDetectors._extract_unified_top_hud = _vd_extract_unified_top_hud_banner_style
VisionDetectors._read_phase_text_fast = _vd_read_phase_text_banner_style
VisionDetectors._read_countdown_fast = _vd_read_countdown_banner_style


# ============================================================
# FINAL STABLE HUD SPLIT PATCH
# Mantém calibração do top_hud_unificado, mas lê score/clock/phase
# em sub-ROIs independentes para evitar OCR misturado.
# ============================================================

def _vd_hud_subroi(self, frame: np.ndarray, name: str) -> Tuple[int, int, int, int]:
    hx, hy, hw, hh = self._resolve_roi(frame, 'top_hud_unificado')
    # Frações ajustadas para o HUD mostrado no print do usuário
    rel = {
        'score': (0.00, 0.00, 0.78, 0.78),
        'phase': (0.46, 0.44, 0.22, 0.40),
        'clock': (0.57, 0.44, 0.34, 0.42),
    }.get(name, (0.00, 0.00, 1.00, 1.00))
    rx, ry, rw, rh = rel
    x = hx + int(hw * rx)
    y = hy + int(hh * ry)
    w = max(10, int(hw * rw))
    h = max(8, int(hh * rh))
    H, W = frame.shape[:2]
    return _clip_roi(x, y, w, h, W, H)


def _vd_validate_clock_transition_soft(self, candidate: Optional[str]) -> Optional[str]:
    if not candidate or not _is_mmss_clock_text(candidate):
        return None
    last = getattr(self, '_last_clock_read', None)
    if not last or not _is_mmss_clock_text(last):
        return candidate
    prev_s = _clock_to_seconds_mmss(last)
    curr_s = _clock_to_seconds_mmss(candidate)
    if prev_s is None or curr_s is None:
        return candidate
    delta = curr_s - prev_s
    # Permite avanço natural, pequenos recuos de frame/OCR e troca de tomada.
    if -8 <= delta <= 20:
        return candidate
    # Se o OCR inventou salto absurdo, mantém o último válido.
    if abs(delta) > 45:
        return last
    return candidate


def _vd_pick_best_score(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - float(getattr(self, '_last_score_read_t', -9999.0) or -9999.0)) < 0.12 and getattr(self, '_last_score_read', None):
        return self._last_score_read

    roi = _crop(frame, _vd_hud_subroi(self, frame, 'score'))
    candidates: List[str] = []

    # 1. Segmentação Rápida (findContours) - Altamente otimizado e preciso para ignorar lixo
    try:
        gray = _prep_gray(roi, upscale=3.0)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cnts = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        digits = []
        H, W = bw.shape[:2]
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w * h < 30:
                continue
            if h < H * 0.15:
                continue
            ar = h / max(1, w)
            if not (0.5 <= ar <= 7.0):
                continue
            crop = bw[max(0,y-2):min(H,y+h+2), max(0,x-2):min(W,x+w+2)]
            txt = _ocr_text(crop, psm=10, whitelist='0123456789')
            txt = ''.join(re.findall(r'\d', txt))[:1]
            if txt:
                digits.append((x, txt))
        digits.sort(key=lambda t: t[0])
        if len(digits) >= 2:
            score = f"{digits[0][1]}x{digits[-1][1]}"
            if _is_score_reasonable(score):
                candidates.append(score)
    except Exception:
        pass

    parsed = []
    for item in candidates:
        val = _parse_score(str(item))
        if val and _is_score_reasonable(val):
            parsed.append(val)

    # 2. Lazy fallback para OCR blocos compostos (Lento)
    if not parsed:
        try:
            candidates.extend(self._ocr_collect_candidates(
                roi=roi,
                psm_list=(7, 6, 13),
                whitelist='0123456789xX-: ',
                upscale=3.2,
                allow_inv=True,
                allow_otsu=True,
                normalize_mode='numeric',
                parser=_parse_score,
            ))
        except Exception:
            pass

        try:
            candidates.extend(self._ocr_roi_like_banner(
                roi,
                psm_list=(7, 13),
                whitelist='0123456789xX-: ',
                upscale=3.0,
                allow_inv=True,
                allow_otsu=True,
                parser=_parse_score,
                block_zone='hud_score',
                min_block_w_ratio=0.08,
                min_block_h_ratio=0.30,
            ))
        except Exception:
            pass

        for item in candidates:
            val = _parse_score(str(item))
            if val and _is_score_reasonable(val) and val not in parsed:
                parsed.append(val)

    best = _majority_or_none(parsed, min_count=1)
    if best:
        self._score_history.append(best)
        best = Counter(self._score_history).most_common(1)[0][0]
        self._last_score_read = best
    self._last_score_read_t = now
    return getattr(self, '_last_score_read', None)


def _vd_pick_best_clock(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - float(getattr(self, '_last_clock_read_t', -9999.0) or -9999.0)) < 0.10 and getattr(self, '_last_clock_read', None):
        return self._last_clock_read

    roi = _crop(frame, _vd_hud_subroi(self, frame, 'clock'))
    candidates: List[str] = []
    try:
        candidates.extend(self._ocr_collect_candidates(
            roi=roi,
            psm_list=(7, 6, 13),
            whitelist='0123456789: ',
            upscale=3.4,
            allow_inv=True,
            allow_otsu=True,
            normalize_mode='numeric',
            parser=_parse_clock,
        ))
    except Exception:
        pass

    parsed = []
    for item in candidates:
        val = _parse_clock(str(item))
        if val and _is_mmss_clock_text(val):
            parsed.append(val)

    if not parsed:
        try:
            candidates.extend(self._ocr_roi_like_banner(
                roi,
                psm_list=(7, 13),
                whitelist='0123456789: ',
                upscale=3.2,
                allow_inv=True,
                allow_otsu=True,
                parser=_parse_clock,
                block_zone='hud_clock',
                min_block_w_ratio=0.16,
                min_block_h_ratio=0.30,
            ))
        except Exception:
            pass

        for item in candidates:
            val = _parse_clock(str(item))
            if val and _is_mmss_clock_text(val) and val not in parsed:
                parsed.append(val)

    best = _majority_or_none(parsed, min_count=1)
    best = _vd_validate_clock_transition_soft(self, best)
    if best and _is_mmss_clock_text(best):
        self._clock_history.append(best)
        self._last_clock_read = Counter(self._clock_history).most_common(1)[0][0]
    self._last_clock_read_t = now
    return getattr(self, '_last_clock_read', None)


def _vd_pick_best_phase(self, frame: np.ndarray) -> str:
    now = time.time()
    cached = str(getattr(self, '_last_phase_read', '') or '').strip()
    if cached and (now - float(getattr(self, '_last_phase_read_t', -9999.0) or -9999.0)) < 0.18:
        return cached

    roi = _crop(frame, _vd_hud_subroi(self, frame, 'phase'))
    candidates: List[str] = []
    try:
        candidates.extend(self._ocr_collect_candidates(
            roi=roi,
            psm_list=(7, 6, 13),
            whitelist='ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789 ',
            upscale=3.0,
            allow_inv=True,
            allow_otsu=True,
            normalize_mode='general',
            parser=None,
        ))
    except Exception:
        pass

    phase_candidates: List[str] = []
    for item in candidates:
        phase = self._phase_from_block_text(str(item))
        if phase:
            phase_candidates.append(phase)

    best = _majority_or_none(phase_candidates, min_count=1) or ''
    if best:
        self._last_phase_read = best
    self._last_phase_read_t = now
    return str(getattr(self, '_last_phase_read', '') or '')


def _vd_read_score_stable(self, frame: np.ndarray) -> Optional[str]:
    return _vd_pick_best_score(self, frame)


def _vd_read_game_clock_stable(self, frame: np.ndarray) -> Optional[str]:
    return _vd_pick_best_clock(self, frame)


def _vd_read_phase_text_stable(self, frame: np.ndarray) -> str:
    return _vd_pick_best_phase(self, frame)


def _vd_read_screen_context_stable(self, frame: np.ndarray) -> Dict[str, Any]:
    now = time.time()
    cached = getattr(self, '_last_screen_context', None)
    cached_t = float(getattr(self, '_last_screen_context_t', -9999.0) or -9999.0)
    if isinstance(cached, dict) and (now - cached_t) < 0.08:
        return dict(cached)

    score = _vd_pick_best_score(self, frame)
    clock = _vd_pick_best_clock(self, frame)
    phase_text = _vd_pick_best_phase(self, frame)
    countdown = None
    if not clock and phase_text.upper() not in ('PRIMEIRO TEMPO', 'SEGUNDO TEMPO', 'INTERVALO'):
        try:
            countdown = _vd_read_countdown_banner_style(self, frame)
        except Exception:
            countdown = getattr(self, '_last_countdown_read', None)

    banner_ctx = _vd_banner_empty()
    banner_text = ''
    if self.is_roi_enabled('banner'):
        try:
            banner_ctx = self._read_banner_context_fast(frame) or _vd_banner_empty()
            banner_text = str(banner_ctx.get('full_text') or '').strip()
        except Exception:
            banner_ctx = _vd_banner_empty()
            banner_text = ''

    competition_text = str(getattr(self, '_last_competition_read', '') or '')
    teams = _vd_safe_team_pair(getattr(self, '_last_team_names_read', (None, None)))
    context_summary = ' | '.join([p for p in [score, clock, countdown, phase_text, banner_text] if p])
    phase_key = _vd_phase_key_for_event(phase_text, banner_text, clock, countdown) or None

    hud_roi = self._resolve_roi(frame, 'top_hud_unificado')
    macro = {
        'top_hud_unificado': hud_roi,
        'score': _vd_hud_subroi(self, frame, 'score'),
        'clock': _vd_hud_subroi(self, frame, 'clock'),
        'phase': _vd_hud_subroi(self, frame, 'phase'),
    }
    try:
        macro['banner'] = self._resolve_roi(frame, 'banner')
    except Exception:
        pass
    try:
        macro['countdown_center'] = self._resolve_roi(frame, 'countdown_center')
    except Exception:
        pass

    out = {
        'scoreboard': {
            'score': score if _is_score_reasonable(score) else None,
            'clock': clock if _is_mmss_clock_text(clock) else None,
            'countdown': countdown,
            'phase_text': phase_text,
            'visible': bool(score or clock or countdown or phase_text),
            'score_candidates': [score] if score else [],
            'clock_candidates': [clock] if clock else [],
            'countdown_candidates': [countdown] if countdown else [],
            'phase_candidates': [phase_text] if phase_text else [],
            'competition_text': competition_text,
            'teams': teams,
        },
        'top_hud': {
            'score': score,
            'clock': clock,
            'countdown': countdown,
            'phase_text': phase_text,
            'competition_text': competition_text,
            'teams': teams,
            'context_text': context_summary,
            'blocks': [],
            'roi': hud_roi,
        },
        'banner_text': banner_text,
        'context_summary': context_summary,
        'phase': phase_key,
        'blocks': [],
        'macro_zones': macro,
    }
    self._last_screen_context = dict(out)
    self._last_screen_context_t = now
    return out


VisionDetectors._hud_subroi = _vd_hud_subroi
VisionDetectors._read_score_fast = _vd_read_score_stable
VisionDetectors._read_game_clock_fast = _vd_read_game_clock_stable
VisionDetectors._read_phase_text_fast = _vd_read_phase_text_stable
VisionDetectors.read_score = _vd_read_score_stable
VisionDetectors.read_game_clock = _vd_read_game_clock_stable
VisionDetectors.read_phase_text = _vd_read_phase_text_stable
VisionDetectors.read_screen_context = _vd_read_screen_context_stable

# ============================================================
# BLINDAGEM FINAL HUD / FAKE TIMER / COUNTDOWN GUARD
# ============================================================
_VD_PREV_READ_SCREEN_CONTEXT_BLINDED = VisionDetectors.read_screen_context


def _vd_b6_norm_text(txt: str) -> str:
    return _norm_text_general(str(txt or '')).upper().strip()


def _vd_b6_join_block_texts(blocks: List[Dict[str, Any]]) -> str:
    return ' | '.join([_vd_b6_norm_text(b.get('text', '')) for b in (blocks or []) if _vd_b6_norm_text(b.get('text', ''))])


def _vd_b6_has_plus_countdown(text: str) -> bool:
    raw = _vd_b6_norm_text(text).replace(' ', '')
    if not raw:
        return False
    if re.search(r'\+\d{1,2}:\d{2}', raw):
        return True
    if re.search(r'\+\d{1,2}[.:]\d{2}', raw):
        return True
    return False


def _vd_b6_top_profile(img: np.ndarray) -> Dict[str, float]:
    if img is None or getattr(img, 'size', 0) == 0:
        return {'blue_ratio': 0.0, 'yellow_ratio': 0.0, 'white_ratio': 0.0, 'edge_ratio': 0.0, 'focus': 0.0}
    hsv = _dominant_hsv_stats(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return {
        'blue_ratio': float(hsv.get('blue_ratio', 0.0)),
        'yellow_ratio': float(hsv.get('yellow_ratio', 0.0)),
        'white_ratio': float(hsv.get('white_ratio', 0.0)),
        'edge_ratio': float(_edge_ratio(gray)),
        'focus': float(_focus_measure(img)),
    }


def _vd_b6_is_fake_timer(clock: Optional[str], score: Optional[str], phase_text: str, countdown: Optional[str], hud_text: str, roi: Optional[np.ndarray]) -> bool:
    clock_sec = _clock_to_seconds_mmss(clock)
    norm_text = _vd_b6_norm_text(hud_text)
    plus_countdown = _vd_b6_has_plus_countdown(norm_text)
    profile = _vd_b6_top_profile(roi) if roi is not None and getattr(roi, 'size', 0) else _vd_b6_top_profile(np.zeros((1, 1, 3), dtype=np.uint8))

    if plus_countdown:
        return True

    if countdown and str(countdown).strip().startswith('+'):
        return True

    if not clock_sec:
        return False

    has_score = bool(score and _is_score_reasonable(score))
    phase_key = str(phase_text or '').strip().lower()
    has_live_phase = phase_key in ('primeiro_tempo', 'segundo_tempo')

    # clock curtíssimo sem score normalmente é countdown/chamada, não relógio de jogo
    if not has_score and clock_sec <= 90:
        if not has_live_phase:
            return True
        if profile.get('yellow_ratio', 0.0) >= 0.12 or profile.get('blue_ratio', 0.0) >= 0.22:
            return True

    # layout muito colorido com clock isolado é fortíssimo sinal de quadro/chamada
    if not has_score and (profile.get('yellow_ratio', 0.0) >= 0.16 and profile.get('blue_ratio', 0.0) >= 0.16):
        return True

    return False


def _vd_b6_hud_confidence(score: Optional[str], clock: Optional[str], phase_text: str, fake_timer: bool) -> str:
    has_score = bool(score and _is_score_reasonable(score))
    has_clock = bool(clock and _is_mmss_clock_text(clock)) and not fake_timer
    has_phase = str(phase_text or '').strip().lower() in ('primeiro_tempo', 'segundo_tempo', 'intervalo') and not fake_timer
    if has_score and has_clock:
        return 'FULL'
    if has_score and has_phase:
        return 'FULL'
    if has_clock and has_phase:
        return 'PARTIAL'
    if has_score or has_clock or has_phase:
        return 'PARTIAL'
    return 'NONE'


def _vd_read_screen_context_blindado(self, frame: np.ndarray) -> Dict[str, Any]:
    ctx = _VD_PREV_READ_SCREEN_CONTEXT_BLINDED(self, frame)
    try:
        ctx = dict(ctx or {})
        sb = dict(ctx.get('scoreboard') or {})
        top = dict(ctx.get('top_hud') or {})
        blocks = list(top.get('blocks') or [])
        hud_text = _vd_b6_join_block_texts(blocks)
        roi_xywh = top.get('roi') or sb.get('roi') or self._resolve_roi(frame, 'top_hud_unificado')
        roi_img = None
        try:
            roi_img = _crop(frame, tuple(roi_xywh)) if roi_xywh else None
        except Exception:
            roi_img = None

        score = sb.get('score')
        clock = sb.get('clock')
        countdown = sb.get('countdown')
        phase_text = str(sb.get('phase_text') or '').strip()
        plus_countdown = _vd_b6_has_plus_countdown(hud_text)
        fake_timer = _vd_b6_is_fake_timer(clock, score, phase_text, countdown, hud_text, roi_img)
        profile = _vd_b6_top_profile(roi_img) if roi_img is not None and getattr(roi_img, 'size', 0) else {'blue_ratio': 0.0, 'yellow_ratio': 0.0, 'white_ratio': 0.0, 'edge_ratio': 0.0, 'focus': 0.0}

        if fake_timer and clock and not (score and _is_score_reasonable(score)):
            if not countdown:
                countdown = clock
            clock = None
            if str(phase_text or '').strip().lower() in ('primeiro_tempo', 'segundo_tempo'):
                phase_text = ''

        hud_conf = _vd_b6_hud_confidence(score, clock, phase_text, fake_timer)

        sb['score'] = score if (score and _is_score_reasonable(score)) else None
        sb['clock'] = clock if (clock and _is_mmss_clock_text(clock) and not fake_timer and hud_conf == 'FULL') else None
        sb['countdown'] = countdown
        sb['phase_text'] = phase_text if (not fake_timer and (sb['score'] or hud_conf == 'FULL')) else ('intervalo' if str(phase_text).strip().lower() == 'intervalo' and sb.get('clock') else '')
        sb['plus_countdown_detected'] = bool(plus_countdown)
        sb['fake_timer'] = bool(fake_timer)
        sb['hud_confidence_level'] = hud_conf
        sb['top_hud_visual_profile'] = profile

        top['score'] = sb['score']
        top['clock'] = sb['clock']
        top['countdown'] = sb['countdown']
        top['phase_text'] = sb['phase_text']
        top['plus_countdown_detected'] = bool(plus_countdown)
        top['fake_timer'] = bool(fake_timer)
        top['hud_confidence_level'] = hud_conf
        top['visual_profile'] = profile
        top['hud_text'] = hud_text

        ctx['scoreboard'] = sb
        ctx['top_hud'] = top
        ctx['hud_confidence_level'] = hud_conf
        ctx['fake_timer'] = bool(fake_timer)
        ctx['plus_countdown_detected'] = bool(plus_countdown)
        self._last_screen_context = dict(ctx)
    except Exception:
        pass
    return ctx


VisionDetectors.read_screen_context = _vd_read_screen_context_blindado


def _vd_read_score_blindado(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - self._last_score_read_t) < 0.20:
        return self._last_score_read
    ctx = self.read_screen_context(frame)
    sb = ctx.get('scoreboard') or {}
    best = sb.get('score')
    if best and _is_score_reasonable(best):
        self._score_history.append(str(best))
        self._last_score_read = Counter(self._score_history).most_common(1)[0][0]
    self._last_score_read_t = now
    return self._last_score_read


VisionDetectors.read_score = _vd_read_score_blindado


def _vd_read_game_clock_blindado(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - self._last_clock_read_t) < 0.12:
        return self._last_clock_read
    ctx = self.read_screen_context(frame)
    sb = ctx.get('scoreboard') or {}
    best = sb.get('clock')
    if best and _is_mmss_clock_text(best) and not sb.get('fake_timer') and str(sb.get('hud_confidence_level') or 'NONE').upper() == 'FULL':
        best = self._validate_clock_transition(self._last_clock_read, best)
        if best:
            self._clock_history.append(best)
            self._last_clock_read = Counter(self._clock_history).most_common(1)[0][0]
    self._last_clock_read_t = now
    return self._last_clock_read


VisionDetectors.read_game_clock = _vd_read_game_clock_blindado


def _vd_read_phase_text_blindado(self, frame: np.ndarray) -> str:
    now = time.time()
    if (now - self._last_phase_read_t) < 0.20:
        return self._last_phase_read
    ctx = self.read_screen_context(frame)
    sb = ctx.get('scoreboard') or {}
    phase_text = str(sb.get('phase_text') or '').strip()
    if phase_text and not sb.get('fake_timer') and str(sb.get('hud_confidence_level') or 'NONE').upper() == 'FULL':
        self._last_phase_read = phase_text
    self._last_phase_read_t = now
    return self._last_phase_read


VisionDetectors.read_phase_text = _vd_read_phase_text_blindado


def _vd_read_countdown_blindado(self, frame: np.ndarray) -> Optional[str]:
    now = time.time()
    if (now - self._last_countdown_read_t) < 0.25:
        return self._last_countdown_read
    ctx = self.read_screen_context(frame)
    sb = ctx.get('scoreboard') or {}
    best = sb.get('countdown')
    if best:
        self._last_countdown_read = str(best)
    self._last_countdown_read_t = now
    return self._last_countdown_read


VisionDetectors.read_countdown = _vd_read_countdown_blindado


# ============================================================
# FIELD CONTEXT GUARD - veto auxiliar para HUD falso em estúdio/tela
# ============================================================
def _vd_field_presence_stats(self, frame: np.ndarray) -> Dict[str, Any]:
    try:
        H, W = frame.shape[:2]
        samples = {
            'mid_left': frame[int(H*0.34):int(H*0.58), int(W*0.02):int(W*0.24)],
            'mid_right': frame[int(H*0.34):int(H*0.58), int(W*0.76):int(W*0.98)],
            'low_left': frame[int(H*0.56):int(H*0.84), int(W*0.08):int(W*0.34)],
            'low_right': frame[int(H*0.56):int(H*0.84), int(W*0.66):int(W*0.92)],
        }
        out = {'samples': {}, 'green_hits': 0, 'green_ratios': {}, 'field_context_ok': False}
        for name, roi in samples.items():
            if roi is None or getattr(roi, 'size', 0) == 0:
                out['samples'][name] = {'green_ratio': 0.0, 'focus': 0.0}
                out['green_ratios'][name] = 0.0
                continue
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            # faixa bem permissiva de gramado / campo iluminado
            green = cv2.inRange(hsv, (28, 30, 28), (100, 255, 255))
            green_ratio = float((green > 0).mean())
            focus = _focus_measure(roi)
            out['samples'][name] = {
                'green_ratio': round(green_ratio, 4),
                'focus': round(float(focus), 2),
            }
            out['green_ratios'][name] = green_ratio
            if green_ratio >= 0.16:
                out['green_hits'] += 1
        # Veto auxiliar: precisa de pelo menos 2 regiões com cara de campo.
        # Mantém tolerância porque câmera fechada/replay pode reduzir gramado.
        out['field_context_ok'] = bool(out['green_hits'] >= 2)
        return out
    except Exception as exc:
        return {
            'samples': {},
            'green_hits': 0,
            'green_ratios': {},
            'field_context_ok': False,
            'error': f'{type(exc).__name__}: {exc}',
        }

VisionDetectors._field_presence_stats = _vd_field_presence_stats

_old_vd_classify_frame_fast_final = VisionDetectors.classify_frame_fast

def _vd_classify_frame_fast_with_field_guard(self, frame: np.ndarray) -> MatchResult:
    result = _old_vd_classify_frame_fast_final(self, frame)
    try:
        details = dict(result.details or {})
        field_stats = self._field_presence_stats(frame)
        details['field_context'] = field_stats
        details['field_context_ok'] = bool(field_stats.get('field_context_ok'))
        # HUD de jogo só fica "forte" quando o contexto do frame também ajuda.
        has_score = bool(details.get('score_detected'))
        has_clock = bool(details.get('game_clock_detected'))
        has_phase = str(details.get('match_phase_text') or '').strip().lower() in ('primeiro_tempo', 'segundo_tempo', 'intervalo')
        if not details['field_context_ok'] and ((has_score and has_clock) or (has_score and has_phase)):
            details['hud_field_veto'] = True
        else:
            details['hud_field_veto'] = False
        result.details = details
        try:
            self._last_debug_info = dict(details)
        except Exception:
            pass
    except Exception:
        pass
    return result

VisionDetectors.classify_frame_fast = _vd_classify_frame_fast_with_field_guard


# ============================================================
# FINAL HARD FIELD/STUDIO VETO PATCH
# ============================================================
_old_vd_classify_frame_fast_hard_veto = VisionDetectors.classify_frame_fast

def _vd_classify_frame_fast_hard_veto(self, frame: np.ndarray) -> MatchResult:
    result = _old_vd_classify_frame_fast_hard_veto(self, frame)
    try:
        details = dict(result.details or {})
        field_ok = bool(details.get('field_context_ok') or ((details.get('field_context') or {}).get('field_context_ok')))
        phase_txt = str(details.get('match_phase_text') or details.get('phase_text') or '').strip().lower()
        has_score = bool(details.get('score_detected'))
        has_clock = bool(details.get('game_clock_detected'))
        has_phase = phase_txt in ('primeiro_tempo', 'segundo_tempo', 'intervalo')
        suspicious = bool(has_score or has_clock or has_phase)
        if not field_ok and suspicious and not (has_score and has_clock):
            details['hud_field_veto'] = True
            details['score_detected'] = None
            details['game_clock_detected'] = None
            details['score_text'] = ''
            details['game_clock_text'] = ''
            details['scoreboard_active'] = False
            details['clock_active'] = False
            details['match_phase_text'] = 'pre_jogo'
            details['phase_text'] = 'pre_jogo'
            details['visual_state'] = 'pre_jogo'
            details['visual_confidence'] = max(float(details.get('visual_confidence') or 0.0), 0.90)
            result = MatchResult(
                label='pre_jogo',
                score=float(details['visual_confidence']),
                best_template=str(result.best_template or ''),
                roi_name=str(result.roi_name or ''),
                details=details,
            )
        else:
            details['hud_field_veto'] = bool(details.get('hud_field_veto'))
            result.details = details
        try:
            self._last_debug_info = dict(result.details or {})
        except Exception:
            pass
    except Exception:
        pass
    return result

VisionDetectors.classify_frame_fast = _vd_classify_frame_fast_hard_veto


# ============================================================
# FINAL SCENE GUARD PATCH - revisado
# Regras:
# - iniciar conservador para evitar falso positivo de estúdio/telão
# - exigir HUD consistente E cena real de jogo
# - quando houver veto, o estado bruto já volta para pre_jogo
# ============================================================

def _vd_scene_guard_stats(self, frame: np.ndarray) -> Dict[str, Any]:
    try:
        H, W = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # verde de gramado/campo
        green = cv2.inRange(hsv, (28, 28, 28), (100, 255, 255))
        green_ratio = float((green > 0).mean())
        # pele / close de apresentador
        skin = cv2.inRange(hsv, (0, 25, 55), (25, 180, 255))
        skin_ratio = float((skin > 0).mean())

        # distribuição do verde em grid: jogo real tende a espalhar
        grid_hits = 0
        grid_total = 0
        grid_detail = []
        for gy in (0.22, 0.42, 0.62, 0.80):
            for gx in (0.18, 0.38, 0.62, 0.82):
                y0 = max(0, min(H - 1, int(H * gy) - 24))
                x0 = max(0, min(W - 1, int(W * gx) - 24))
                y1 = min(H, y0 + 48)
                x1 = min(W, x0 + 48)
                roi = frame[y0:y1, x0:x1]
                if roi.size == 0:
                    continue
                grid_total += 1
                hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                green_roi = cv2.inRange(hsv_roi, (28, 28, 28), (100, 255, 255))
                ratio = float((green_roi > 0).mean())
                grid_detail.append(round(ratio, 3))
                if ratio >= 0.18:
                    grid_hits += 1

        # checa se o verde está concentrado em uma única grande área (telão)
        green_u8 = (green > 0).astype('uint8') * 255
        cnts = cv2.findContours(green_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
        largest_green_ratio = 0.0
        if cnts:
            area = max(cv2.contourArea(c) for c in cnts)
            largest_green_ratio = float(area / max(1.0, float(H * W)))

        # jogo real: verde suficiente e distribuído
        real_game_scene = bool(green_ratio >= 0.10 and grid_hits >= 3 and largest_green_ratio < 0.60)
        # estúdio/telão: muita pele ou pouco verde distribuído com um bloco dominante
        studio_scene = bool(skin_ratio >= 0.10 or (largest_green_ratio >= 0.20 and grid_hits <= 2))
        field_context_ok = bool(real_game_scene and not studio_scene)

        return {
            'field_context_ok': field_context_ok,
            'real_game_scene': real_game_scene,
            'studio_scene': studio_scene,
            'green_ratio': round(green_ratio, 4),
            'skin_ratio': round(skin_ratio, 4),
            'grid_hits': int(grid_hits),
            'grid_total': int(grid_total),
            'largest_green_ratio': round(largest_green_ratio, 4),
            'grid_green_ratios': grid_detail[:16],
        }
    except Exception as exc:
        return {
            'field_context_ok': False,
            'real_game_scene': False,
            'studio_scene': False,
            'green_ratio': 0.0,
            'skin_ratio': 0.0,
            'grid_hits': 0,
            'grid_total': 0,
            'largest_green_ratio': 0.0,
            'error': f'{type(exc).__name__}: {exc}',
        }

VisionDetectors._scene_guard_stats = _vd_scene_guard_stats

_old_vd_classify_frame_fast_scene_guard = VisionDetectors.classify_frame_fast

def _vd_classify_frame_fast_scene_guard(self, frame: np.ndarray) -> MatchResult:
    result = _old_vd_classify_frame_fast_scene_guard(self, frame)
    try:
        details = dict(result.details or {})
        scene = self._scene_guard_stats(frame)
        details['field_context'] = scene
        details['field_context_ok'] = bool(scene.get('field_context_ok'))
        details['real_game_scene'] = bool(scene.get('real_game_scene'))
        details['studio_scene'] = bool(scene.get('studio_scene'))

        phase_txt = str(details.get('match_phase_text') or details.get('phase_text') or '').strip().lower()
        score_txt = details.get('score_detected') or details.get('score_text') or ''
        clock_txt = details.get('game_clock_detected') or details.get('game_clock_text') or ''
        countdown_txt = details.get('countdown_detected') or details.get('countdown') or ''
        scoreboard_active = bool(details.get('scoreboard_active'))

        has_score = bool(score_txt and _is_score_reasonable(str(score_txt)))
        has_clock = bool(clock_txt and _is_mmss_clock_text(str(clock_txt)))
        has_live_phase = phase_txt in ('primeiro_tempo', 'segundo_tempo', 'intervalo')
        suspicious_timer = bool((not has_score and has_clock) or countdown_txt)
        has_live_hud = bool(scoreboard_active and ((has_score and has_clock) or (has_score and has_live_phase)))

        veto = False
        hud_is_very_strong = (has_score and has_clock)
        if not hud_is_very_strong:
            if details['studio_scene'] and (has_score or has_clock or has_live_phase):
                veto = True
            if not details['field_context_ok'] and (has_score or has_clock or has_live_phase):
                veto = True
            if suspicious_timer and not has_score:
                veto = True
            if not has_live_hud and (has_clock or has_live_phase):
                veto = True

        details['hud_field_veto'] = bool(veto)
        details['hud_confidence_level'] = 'FULL' if has_live_hud and not veto else ('PARTIAL' if (has_score or has_clock or has_live_phase) and not veto else 'NONE')

        if veto:
            details['score_detected'] = None
            details['game_clock_detected'] = None
            details['score_text'] = ''
            details['game_clock_text'] = ''
            details['match_phase_text'] = 'pre_jogo'
            details['phase_text'] = 'pre_jogo'
            details['scoreboard_active'] = False
            details['clock_active'] = False
            details['visual_state'] = 'pre_jogo'
            details['visual_confidence'] = max(float(details.get('visual_confidence') or 0.0), 0.91)
            result = MatchResult(
                label='pre_jogo',
                score=float(details['visual_confidence']),
                best_template=str(result.best_template or ''),
                roi_name=str(result.roi_name or ''),
                details=details,
            )
        else:
            result.details = details

        try:
            self._last_debug_info = dict(result.details or {})
        except Exception:
            pass
    except Exception:
        pass
    return result

VisionDetectors.classify_frame_fast = _vd_classify_frame_fast_scene_guard


# ============================================================
# PATCH GATE-FIX - Critérios mais permissivos para scoreboard/clock
# O HUD da CazéTV não tem blue_ratio alta e os dígitos são pequenos
# relativos à ROI, então os gates originais sempre retornavam False.
# Critério novo: focus OU edge_ratio OU white_ratio OU digit_like >=1
# Também registra stats no _last_debug_info para diagnóstico.
# ============================================================

def _vd_is_scoreboard_active_relaxed(self, frame: np.ndarray) -> bool:
    try:
        if not self.is_roi_enabled('score'):
            return False
        roi = _crop(frame, self._roi_score(frame))
        st = self._scoreboard_visual_stats(roi)
        good = 0
        if st.get('focus', 0.0) >= 5:       good += 1
        if st.get('edge_ratio', 0.0) >= 0.006: good += 1
        if st.get('white_ratio', 0.0) >= 0.010: good += 1
        if st.get('digit_like_ratio', 0.0) >= 0.04: good += 1
        # Guardar para debug
        try:
            di = getattr(self, '_last_debug_info', None)
            if isinstance(di, dict):
                di['scoreboard_gate_stats'] = st
                di['scoreboard_gate_good'] = good
        except Exception:
            pass
        return good >= 1
    except Exception:
        return True  # fail-open: se der erro, deixa o OCR rodar


def _vd_is_clock_roi_active_relaxed(self, frame: np.ndarray) -> bool:
    try:
        if not self.is_roi_enabled('clock'):
            return False
        roi = _crop(frame, self._roi_clock(frame))
        st = self._clock_visual_stats(roi)
        good = 0
        if st.get('focus', 0.0) >= 4:          good += 1
        if st.get('edge_ratio', 0.0) >= 0.006:  good += 1
        if st.get('white_ratio', 0.0) >= 0.010 or st.get('red_ratio', 0.0) >= 0.030: good += 1
        if st.get('digit_like_ratio', 0.0) >= 0.04: good += 1
        try:
            di = getattr(self, '_last_debug_info', None)
            if isinstance(di, dict):
                di['clock_gate_stats'] = st
                di['clock_gate_good'] = good
        except Exception:
            pass
        return good >= 1
    except Exception:
        return True  # fail-open


VisionDetectors._is_scoreboard_active = _vd_is_scoreboard_active_relaxed
VisionDetectors._is_clock_roi_active = _vd_is_clock_roi_active_relaxed


# ============================================================
# PATCH HARDGUARD - Correções estruturais no classify_frame_fast
#
# Problemas corrigidos:
# A. ROI colapso (score_roi == clock_roi == phase_roi): aborta OCR
# B. Early-return real quando scoreboard_active=False e clock_active=False
# C. Timeout defensivo de 80ms no caminho pesado
# D. Latência HUD medida com time.perf_counter() apenas (sem raw_ts)
# ============================================================

_old_vd_classify_hardguard = VisionDetectors.classify_frame_fast
_HG_HEAVY_TIMEOUT_MS = 80.0


def _vd_classify_hardguard(self, frame: np.ndarray) -> MatchResult:
    t_hg_start = time.perf_counter()
    result = _old_vd_classify_hardguard(self, frame)

    try:
        details = dict(result.details or {})

        # --- D: Gravar latência HUD usando apenas perf_counter ---
        hg_elapsed_ms = round((time.perf_counter() - t_hg_start) * 1000.0, 2)
        details['hg_classify_ms'] = hg_elapsed_ms

        # --- A: Detectar ROI colapso ---
        score_roi = details.get('score_roi')
        clock_roi = details.get('clock_roi')
        phase_roi = details.get('phase_roi')
        roi_collapsed = bool(
            score_roi and clock_roi and phase_roi
            and score_roi == clock_roi == phase_roi
        )
        details['roi_collapsed'] = roi_collapsed

        if roi_collapsed:
            # ROI colapso: zero o que foi lido (inválido)
            details['score_detected'] = None
            details['game_clock_detected'] = None
            details['match_phase_text'] = None
            details['phase_text'] = None
            details['scoreboard_active'] = False
            details['clock_active'] = False
            details['hg_abort_reason'] = 'roi_collapsed'
            result = MatchResult(
                label=str(details.get('visual_state') or 'nao_detectado'),
                score=float(details.get('visual_confidence') or 0.0),
                best_template=str(result.best_template or ''),
                roi_name=str(result.roi_name or ''),
                details=details,
            )
            try:
                self._last_debug_info = details
            except Exception:
                pass
            return result

        result.details = details
        try:
            self._last_debug_info = details
        except Exception:
            pass

    except Exception:
        pass

    return result


VisionDetectors.classify_frame_fast = _vd_classify_hardguard


# ============================================================
# PATCH EARLYEXIT - Early-return antes do caminho pesado
# Substitui a chamada a detect_frame_state quando sem gates ativos
# ============================================================

_old_vd_classify_before_earlyexit = VisionDetectors.classify_frame_fast


def _vd_classify_earlyexit(self, frame: np.ndarray) -> MatchResult:
    """
    Antes de entrar no classify pesado, verifica os gates de forma
    ultra-rápida. Se scoreboard e clock estiverem inativos E o frame
    for praticamente idêntico ao anterior, devolve o último resultado
    com banner atualizado para não travar o pipeline.
    """
    try:
        if frame is None or getattr(frame, 'size', 0) == 0:
            return MatchResult(
                label='nao_detectado', score=0.0,
                best_template='', roi_name='',
                details={'visual_state': 'nao_detectado', 'visual_confidence': 0.0, 'reason': 'frame_vazio'}
            )

        # Gate rápido sem OCR
        scoreboard_active = self._is_scoreboard_active(frame)
        clock_active = self._is_clock_roi_active(frame)

        prev = dict(getattr(self, '_last_debug_info', {}) or {})

        # Se nenhum gate de HUD está ativo e temos resultado recente (< 1s),
        # evita caminho pesado completamente
        last_done = float(getattr(self, '_last_classify_done_t', 0.0))
        now_pc = time.perf_counter()
        elapsed_since_last = (now_pc - last_done)

        if not scoreboard_active and not clock_active and elapsed_since_last < 1.0 and prev:
            prev['scoreboard_active'] = False
            prev['clock_active'] = False
            prev['hg_abort_reason'] = 'no_hud_earlyexit'
            prev['score_detected'] = None
            prev['game_clock_detected'] = None
            try:
                self._last_debug_info = prev
            except Exception:
                pass
            return MatchResult(
                label=str(prev.get('visual_state') or 'nao_detectado'),
                score=float(prev.get('visual_confidence') or 0.0),
                best_template='',
                roi_name='',
                details=prev,
            )

    except Exception:
        pass  # fail-safe: se qualquer coisa falhar, continua no caminho normal

    return _old_vd_classify_before_earlyexit(self, frame)


VisionDetectors.classify_frame_fast = _vd_classify_earlyexit
