from __future__ import annotations

import re
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    import pytesseract
except Exception:
    pytesseract = None


CLOCK_RE = re.compile(r"(?<!\d)(\d{1,3})\s*[:.]\s*(\d{2})(?!\d)")
COUNTDOWN_HHMMSS_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[:.]\s*(\d{2})\s*[:.]\s*(\d{2})(?!\d)")
TEAM_RE = re.compile(r"\b[A-Z]{2,4}\b")
PHASE_1T_RE = re.compile(r"\b(1T|1\s*T|1TEMPO|PRIMEIRO\s+TEMPO)\b", re.IGNORECASE)
PHASE_2T_RE = re.compile(r"\b(2T|2\s*T|2TEMPO|SEGUNDO\s+TEMPO)\b", re.IGNORECASE)
PHASE_INTERVALO_RE = re.compile(r"\bINTERVALO\b", re.IGNORECASE)
PHASE_PRE_RE = re.compile(r"\b(PR[ÉE]\s*JOGO|AO\s*VIVO\s*EM|DAQUI\s*A\s*POUCO|EM\s*INSTANTES|J[ÁA]\s*J[ÁA])\b", re.IGNORECASE)

DEFAULT_EMPTY_HUD = {
    "score": None,
    "clock": None,
    "phase_text": "",
    "context_text": "",
    "teams": [None, None],
    "countdown": None,
    "countdown_text": "",
    "engine": "empty",
    "low_signal": False,
    "signal_score": 0.0,
    "internal_timeline": [],
}


def _norm_text(s: str) -> str:
    s = (s or "").upper()
    s = s.replace("\n", " ").replace("\r", " ")
    s = s.replace("§", "S").replace("¦", "|")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _norm_numeric_text(s: str) -> str:
    s = _norm_text(s)
    rep = {
        "O": "0",
        "Q": "0",
        "D": "0",
        "I": "1",
        "L": "1",
        "!": "1",
        "|": "1",
        ";": ":",
        ",": ":",
        ".": ":",
        "X": "X",
    }
    for a, b in rep.items():
        s = s.replace(a, b)
    return s


def _clean_text_block(s: str) -> str:
    s = _norm_text(s)
    s = re.sub(r"[^\wÀ-ÿ0-9:!?.,\-/ ]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _safe_tesseract(img: np.ndarray, config: str, timeout: float = 0.5) -> str:
    if pytesseract is None or img is None or img.size == 0:
        return ""
    try:
        return pytesseract.image_to_string(img, config=config, timeout=timeout) or ""
    except Exception:
        return ""


def _crop_rel(crop: np.ndarray, xr: float, yr: float, wr: float, hr: float) -> np.ndarray:
    h, w = crop.shape[:2]
    x = max(0, min(int(round(w * xr)), max(0, w - 1)))
    y = max(0, min(int(round(h * yr)), max(0, h - 1)))
    ww = max(1, min(int(round(w * wr)), w - x))
    hh = max(1, min(int(round(h * hr)), h - y))
    return crop[y:y + hh, x:x + ww]


def _resize(img: np.ndarray, scale: float) -> np.ndarray:
    if scale == 1.0:
        return img
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def _clahe_gray(img: np.ndarray, scale: float = 2.0) -> np.ndarray:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = _resize(g, scale)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(g)


def _prep_dark_on_light(img: np.ndarray, scale: float = 3.0) -> np.ndarray:
    g = _clahe_gray(img, scale)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
    return bw


def _prep_light_on_dark(img: np.ndarray, scale: float = 3.0) -> np.ndarray:
    g = _clahe_gray(img, scale)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
    return bw


def _prep_white_box_black_text(img: np.ndarray, scale: float = 4.0) -> np.ndarray:
    img = _resize(img, scale)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    white = cv2.inRange(hsv, (0, 0, 140), (180, 110, 255))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, dark = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    out = cv2.bitwise_and(dark, dark, mask=white)
    out = cv2.morphologyEx(out, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8), iterations=1)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
    return out


def _prep_green_clock(img: np.ndarray, scale: float = 4.0) -> np.ndarray:
    img = _resize(img, scale)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (18, 20, 40), (100, 255, 255))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, dark = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY_INV)
    out = cv2.bitwise_and(dark, dark, mask=green)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
    return out


def _prep_banner_text(img: np.ndarray, scale: float = 3.0) -> np.ndarray:
    g = _clahe_gray(img, scale)
    g = cv2.GaussianBlur(g, (3, 3), 0)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8), iterations=1)
    return bw


def _text_presence_score(img_bgr: np.ndarray) -> float:
    if img_bgr is None or img_bgr.size == 0:
        return 0.0
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(gray, 70, 170)
    edge_ratio = float(np.count_nonzero(edges)) / float(edges.size)
    std = float(np.std(gray)) / 255.0
    bright_ratio = float(np.count_nonzero(gray > 165)) / float(gray.size)
    return (edge_ratio * 2.0) + (std * 0.7) + (bright_ratio * 0.45)


def _green_dominance(img_bgr: np.ndarray) -> float:
    if img_bgr is None or img_bgr.size == 0:
        return 0.0
    b, g, r = cv2.split(img_bgr)
    mask = (g > (r + 12)) & (g > (b + 8)) & (g > 60)
    return float(np.count_nonzero(mask)) / float(mask.size)


def _majority_or_none(items: List[str], min_count: int = 1) -> Optional[str]:
    vals = [x for x in items if x]
    if not vals:
        return None
    value, qty = Counter(vals).most_common(1)[0]
    if qty >= min_count:
        return value
    return vals[0]


def _parse_clock(txt: str) -> Optional[str]:
    raw = _norm_numeric_text(txt)
    raw = re.sub(r"\b(1T|2T|1\s*T|2\s*T|PRIMEIRO\s+TEMPO|SEGUNDO\s+TEMPO)\b", " ", raw)
    raw = re.sub(r"\s+", "", raw)
    m = CLOCK_RE.search(raw)
    if not m:
        return None
    mm = int(m.group(1))
    ss = int(m.group(2))
    if 0 <= mm <= 180 and 0 <= ss <= 59:
        return f"{mm:02d}:{ss:02d}"
    return None


def _parse_countdown(txt: str) -> Optional[str]:
    raw = _norm_numeric_text(txt)
    raw = re.sub(r"\s+", "", raw)
    m3 = COUNTDOWN_HHMMSS_RE.search(raw)
    if m3:
        hh, mm, ss = int(m3.group(1)), int(m3.group(2)), int(m3.group(3))
        if 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59:
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
    return _parse_clock(raw)


def _is_mmss_clock_text(value: Optional[str]) -> bool:
    if not value:
        return False
    m = re.fullmatch(r"(\d{1,3}):(\d{2})", str(value).strip())
    if not m:
        return False
    mm = int(m.group(1))
    ss = int(m.group(2))
    return 0 <= mm <= 180 and 0 <= ss <= 59


def _is_score_reasonable(score: Optional[str]) -> bool:
    if not score or not re.fullmatch(r"\d+x\d+", score):
        return False
    a, b = [int(x) for x in score.split("x")]
    return a <= 9 and b <= 9 and (a + b) <= 12


def _parse_score(txt: str) -> Optional[str]:
    raw = _norm_numeric_text(txt)
    raw = raw.replace(" ", "")
    if CLOCK_RE.search(raw):
        return None
    m = re.search(r"(?<!\d)(\d)\s*[xX\-:]\s*(\d)(?!\d)", raw)
    if m:
        score = f"{m.group(1)}x{m.group(2)}"
        return score if _is_score_reasonable(score) else None
    digits = re.findall(r"(?<!\d)(\d)(?!\d)", raw)
    if len(digits) >= 2:
        score = f"{digits[0]}x{digits[1]}"
        return score if _is_score_reasonable(score) else None
    return None


def _phase_from_text(txt: str) -> str:
    raw = _clean_text_block(txt)
    if not raw:
        return ""
    if PHASE_INTERVALO_RE.search(raw):
        return "INTERVALO"
    if PHASE_1T_RE.search(raw):
        return "1T"
    if PHASE_2T_RE.search(raw):
        return "2T"
    if PHASE_PRE_RE.search(raw):
        return "PRE_JOGO"
    return ""


def _best_team_token(*texts: str) -> Optional[str]:
    bad = {
        "AO", "TV", "HD", "OO", "O", "CAZE", "CAZ", "VAR", "COM", "PALAVRAS", "RODADA",
        "JOGO", "VASO", "VAS0", "BRASILEIRAO", "BRASILEIRO", "COMPLETO", "X", "XX"
    }
    for txt in texts:
        for token in TEAM_RE.findall(_norm_text(txt)):
            if token not in bad:
                return token
    return None


def _ocr(img: np.ndarray, *, psm: int, whitelist: Optional[str], numeric: bool, timeout: float = 0.5) -> str:
    cfg = f"--oem 3 --psm {psm}"
    if whitelist:
        cfg += f" -c tessedit_char_whitelist={whitelist}"
    txt = _safe_tesseract(img, cfg, timeout=timeout)
    return _norm_numeric_text(txt) if numeric else _norm_text(txt)


def _hud_signal_metrics(crop: np.ndarray) -> Tuple[bool, float]:
    presence = _text_presence_score(crop)
    green = _green_dominance(crop)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    bright = float(np.count_nonzero(gray > 168)) / float(gray.size)
    signal = presence + (bright * 0.40) - (green * 0.14)
    return signal < 0.11, signal


def _ocr_variants(
    images: List[np.ndarray],
    *,
    psm_list: Tuple[int, ...],
    whitelist: Optional[str],
    numeric: bool,
    parser=None,
    timeout: float = 0.5,
) -> List[str]:
    found: List[str] = []
    for img in images:
        if img is None or getattr(img, "size", 0) == 0:
            continue
        for psm in psm_list:
            txt = _ocr(img, psm=psm, whitelist=whitelist, numeric=numeric, timeout=timeout)
            if not txt:
                continue
            if parser is not None:
                parsed = parser(txt)
                if parsed:
                    found.append(parsed)
            else:
                cleaned = _clean_text_block(txt)
                if cleaned:
                    found.append(cleaned)
    return [x for x in found if x]


def _read_team_roi(team_roi: np.ndarray) -> Tuple[Optional[str], List[str]]:
    texts = _ocr_variants(
        [
            _prep_white_box_black_text(team_roi, 4.6),
            _prep_dark_on_light(team_roi, 4.2),
            _resize(team_roi, 4.0),
        ],
        psm_list=(8, 7, 13),
        whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        numeric=False,
        parser=None,
        timeout=0.7,
    )
    token = _best_team_token(*texts)
    return token, texts


def _read_score_roi(score_roi: np.ndarray) -> Tuple[Optional[str], List[str]]:
    texts: List[str] = []
    whole = _ocr_variants(
        [
            _prep_white_box_black_text(score_roi, 5.0),
            _prep_dark_on_light(score_roi, 4.5),
            _resize(score_roi, 4.0),
        ],
        psm_list=(7, 13, 6),
        whitelist="0123456789xX:- ",
        numeric=True,
        parser=_parse_score,
        timeout=0.8,
    )
    texts.extend(whole)

    left_digit_roi = _crop_rel(score_roi, 0.02, 0.02, 0.34, 0.92)
    right_digit_roi = _crop_rel(score_roi, 0.64, 0.02, 0.34, 0.92)
    digits = []
    for digit_roi in (left_digit_roi, right_digit_roi):
        digit_texts = _ocr_variants(
            [
                _prep_white_box_black_text(digit_roi, 5.5),
                _prep_dark_on_light(digit_roi, 5.0),
                _resize(digit_roi, 4.2),
            ],
            psm_list=(10, 8),
            whitelist="0123456789",
            numeric=True,
            parser=None,
            timeout=0.7,
        )
        digit = None
        for txt in digit_texts:
            m = re.search(r"\d", txt)
            if m:
                digit = m.group(0)
                break
        digits.append(digit)
    if digits[0] is not None and digits[1] is not None:
        score = f"{digits[0]}x{digits[1]}"
        if _is_score_reasonable(score):
            texts.append(score)
    best = _majority_or_none([t for t in texts if _is_score_reasonable(t)], min_count=1)
    return best, texts


def _read_bottom_roi(bottom_roi: np.ndarray) -> Tuple[Optional[str], str, List[str]]:
    clock_zone = _crop_rel(bottom_roi, 0.00, 0.00, 0.60, 1.00)
    phase_zone = _crop_rel(bottom_roi, 0.00, 0.00, 0.28, 1.00)

    clock_texts = _ocr_variants(
        [
            _prep_green_clock(clock_zone, 5.2),
            _prep_dark_on_light(clock_zone, 4.8),
            _resize(clock_zone, 4.2),
        ],
        psm_list=(7, 8, 13),
        whitelist="0123456789:T| ",
        numeric=False,
        parser=_parse_clock,
        timeout=0.8,
    )
    clock = _majority_or_none([c for c in clock_texts if _is_mmss_clock_text(c)], min_count=1)

    phase_raws = _ocr_variants(
        [
            _prep_green_clock(phase_zone, 5.0),
            _prep_dark_on_light(phase_zone, 4.6),
            _resize(phase_zone, 4.0),
        ],
        psm_list=(7, 8),
        whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ",
        numeric=False,
        parser=None,
        timeout=0.7,
    )
    phases = [_phase_from_text(t) for t in phase_raws if _phase_from_text(t)]
    phase = _majority_or_none(phases, min_count=1) or ""
    return clock, phase, clock_texts + phase_raws


def _read_full_support(full_roi: np.ndarray) -> List[str]:
    return _ocr_variants(
        [
            _prep_white_box_black_text(full_roi, 3.8),
            _prep_dark_on_light(full_roi, 3.6),
            _resize(full_roi, 3.2),
        ],
        psm_list=(6, 11),
        whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:- ",
        numeric=False,
        parser=None,
        timeout=0.8,
    )


def read_hud_fast(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> Dict[str, object]:
    x, y, w, h = roi
    crop = frame[y:y + h, x:x + w]
    out = dict(DEFAULT_EMPTY_HUD)
    if crop.size == 0:
        return out

    timeline: List[Dict[str, object]] = []
    t_all = time.perf_counter()

    t0 = time.perf_counter()
    low_signal, signal_score = _hud_signal_metrics(crop)
    timeline.append({"stage": "signal_gate", "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 1)})
    out["signal_score"] = round(signal_score, 4)
    out["low_signal"] = bool(low_signal)
    if low_signal:
        out["engine"] = "low_signal_skip"
        out["internal_timeline"] = timeline + [{"stage": "total", "elapsed_ms": round((time.perf_counter() - t_all) * 1000.0, 1)}]
        return out

    left_team_roi = _crop_rel(crop, 0.01, 0.02, 0.19, 0.54)
    score_roi = _crop_rel(crop, 0.18, 0.02, 0.27, 0.54)
    right_team_roi = _crop_rel(crop, 0.44, 0.02, 0.21, 0.54)
    bottom_roi = _crop_rel(crop, 0.16, 0.48, 0.38, 0.30)
    full_roi = _crop_rel(crop, 0.00, 0.00, 0.72, 0.82)

    t1 = time.perf_counter()
    left_team, left_team_texts = _read_team_roi(left_team_roi)
    right_team, right_team_texts = _read_team_roi(right_team_roi)
    timeline.append({"stage": "teams_accuracy_first", "elapsed_ms": round((time.perf_counter() - t1) * 1000.0, 1)})

    t2 = time.perf_counter()
    score, score_texts = _read_score_roi(score_roi)
    timeline.append({"stage": "score_accuracy_first", "elapsed_ms": round((time.perf_counter() - t2) * 1000.0, 1)})

    t3 = time.perf_counter()
    clock, phase_text, bottom_texts = _read_bottom_roi(bottom_roi)
    timeline.append({"stage": "bottom_accuracy_first", "elapsed_ms": round((time.perf_counter() - t3) * 1000.0, 1)})

    t4 = time.perf_counter()
    full_texts = _read_full_support(full_roi)
    timeline.append({"stage": "full_support", "elapsed_ms": round((time.perf_counter() - t4) * 1000.0, 1)})

    if not left_team:
        left_team = _best_team_token(*full_texts)
    if not right_team:
        reversed_support = list(reversed(full_texts))
        right_team = _best_team_token(*reversed_support)
    if left_team == right_team:
        right_team = None

    if not score:
        for txt in full_texts:
            score = _parse_score(txt)
            if score:
                break
    if not clock:
        for txt in full_texts:
            clock = _parse_clock(txt)
            if clock:
                break
    if not phase_text:
        for txt in bottom_texts + full_texts:
            phase_text = _phase_from_text(txt)
            if phase_text:
                break

    context_parts = [left_team or "", score or "", right_team or "", clock or "", phase_text or ""]
    context_text = _norm_text(" ".join(part for part in context_parts if part))

    out.update({
        "score": score,
        "clock": clock,
        "phase_text": phase_text,
        "context_text": context_text,
        "teams": [left_team, right_team],
        "countdown": None,
        "countdown_text": "",
        "engine": "hud_fast_v10_accuracy_first",
        "internal_timeline": timeline + [{"stage": "total", "elapsed_ms": round((time.perf_counter() - t_all) * 1000.0, 1)}],
        "ocr_debug": {
            "left_team_texts": left_team_texts,
            "right_team_texts": right_team_texts,
            "score_texts": score_texts,
            "bottom_texts": bottom_texts,
            "full_texts": full_texts,
        },
    })
    return out


def _detect_text_blocks(roi: np.ndarray) -> List[np.ndarray]:
    if roi is None or roi.size == 0:
        return []
    h, w = roi.shape[:2]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    _, bw = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    merged = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, np.ones((max(3, h // 18), max(15, w // 12)), np.uint8), iterations=1)
    contours = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]
    crops: List[Tuple[int, np.ndarray]] = []
    for c in contours:
        x, y, ww, hh = cv2.boundingRect(c)
        area = ww * hh
        if area < max(400, (w * h) // 200):
            continue
        if ww < max(25, w // 18) or hh < max(12, h // 10):
            continue
        crops.append((area, roi[y:y + hh, x:x + ww]))
    crops.sort(key=lambda item: item[0], reverse=True)
    return [c for _, c in crops[:4]]


def read_banner_fast(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> Dict[str, object]:
    x, y, w, h = roi
    crop = frame[y:y + h, x:x + w]
    if crop.size == 0:
        return {"banner_text": "", "context_summary": "", "engine": "empty", "lines": [], "ocr_ms": 0.0, "text_presence": 0.0, "green_ratio": 0.0}

    t0 = time.perf_counter()
    presence = _text_presence_score(crop)
    green_ratio = _green_dominance(crop)
    if presence < 0.14:
        return {
            "banner_text": "",
            "context_summary": "",
            "engine": "skipped_low_signal",
            "lines": [],
            "ocr_ms": round((time.perf_counter() - t0) * 1000.0, 1),
            "text_presence": round(presence, 4),
            "green_ratio": round(green_ratio, 4),
        }

    band = _crop_rel(crop, 0.03, 0.08, 0.94, 0.76)
    images = [
        _prep_banner_text(band, 3.8),
        _prep_light_on_dark(band, 3.6),
        _resize(band, 3.2),
    ]
    blocks = _detect_text_blocks(band)
    for block in blocks:
        images.append(_prep_banner_text(block, 4.0))

    texts = _ocr_variants(
        images,
        psm_list=(6, 11),
        whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZÁÀÃÂÉÊÍÓÔÕÚÇ0123456789!?.,:/@#%&()+- R$ ",
        numeric=False,
        parser=None,
        timeout=0.7,
    )

    lines: List[str] = []
    seen = set()
    for txt in texts:
        cleaned = _clean_text_block(txt)
        if len(re.sub(r"[^A-Z0-9]", "", cleaned)) < 6:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        lines.append(cleaned)
    full = " | ".join(lines[:4]).strip()
    return {
        "banner_text": full,
        "context_summary": full,
        "engine": "ocr_banner_accuracy_first",
        "lines": lines[:4],
        "ocr_ms": round((time.perf_counter() - t0) * 1000.0, 1),
        "text_presence": round(presence, 4),
        "green_ratio": round(green_ratio, 4),
    }


def read_countdown_fast(frame: np.ndarray, roi: Tuple[int, int, int, int]) -> Optional[str]:
    x, y, w, h = roi
    crop = frame[y:y + h, x:x + w]
    if crop.size == 0:
        return None
    if _text_presence_score(crop) < 0.08:
        return None

    texts = _ocr_variants(
        [
            _prep_dark_on_light(crop, 4.6),
            _prep_light_on_dark(crop, 4.4),
            _resize(crop, 4.0),
        ],
        psm_list=(7, 8, 13),
        whitelist="0123456789:",
        numeric=True,
        parser=_parse_countdown,
        timeout=0.7,
    )
    best = _majority_or_none(texts, min_count=1)
    if not best:
        return None
    if len(best) == 5:
        try:
            mm, ss = best.split(":")
            if int(mm) <= 15 and int(ss) <= 59:
                return best
        except Exception:
            return None
        return None
    return best
