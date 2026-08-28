from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np

try:
    import pytesseract
except Exception:
    pytesseract = None


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
FRAME_DIR = PROJECT_ROOT / "data" / "frames"

TESSERACT_CANDIDATES = [
    os.environ.get("TESSERACT_CMD", ""),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

EVENT_WORDS = [
    "PASSES",
    "CERTOS",
    "POSSE",
    "BOLA",
    "ESCANTEIO",
    "FALTAS",
    "FINALIZACOES",
    "FINALIZAÇÕES",
    "AMARELO",
    "VERMELHO",
    "SUBSTITUICAO",
    "SUBSTITUIÇÃO",
    "REPLAY",
    "VAR",
    "GOL",
]

TEAM_HINTS = [
    "PAL", "NOV", "COR", "FLA", "SAO", "SPF", "SAN", "BOT", "VAS", "CAM",
    "GRE", "INT", "CRU", "BAH", "CAP", "CUI", "FOR", "CEA", "GOI", "BRA"
]


@dataclass
class AnalysisResult:
    file: str
    state: str
    period: Optional[str]
    score_a: Optional[int]
    score_b: Optional[int]
    clock: Optional[str]
    has_overlay: bool
    raw_top_text: str
    raw_wide_text: str
    notes: List[str]


# ============================================================
# TESSERACT
# ============================================================

def configure_tesseract() -> None:
    if pytesseract is None:
        raise RuntimeError("pytesseract não está instalado.")

    for cand in TESSERACT_CANDIDATES:
        if cand and os.path.isfile(cand):
            pytesseract.pytesseract.tesseract_cmd = cand
            return


# ============================================================
# HELPERS
# ============================================================

def norm_text(s: str) -> str:
    s = (s or "").upper()
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def safe_imread(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise RuntimeError(f"Falha ao abrir imagem: {path}")
    return img


def crop_rel(img: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> np.ndarray:
    h, w = img.shape[:2]
    xa = max(0, min(w, int(w * x1)))
    xb = max(0, min(w, int(w * x2)))
    ya = max(0, min(h, int(h * y1)))
    yb = max(0, min(h, int(h * y2)))
    if xb <= xa or yb <= ya:
        return img.copy()
    return img[ya:yb, xa:xb].copy()


def upscale(gray: np.ndarray, scale: float = 4.0) -> np.ndarray:
    return cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)


def prep_variants(img: np.ndarray) -> Dict[str, np.ndarray]:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = upscale(gray, 4.0)

    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    _, th_otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    th_inv = cv2.bitwise_not(th_otsu)

    adap = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 8
    )
    adap_inv = cv2.bitwise_not(adap)

    return {
        "gray": gray,
        "th_otsu": th_otsu,
        "th_inv": th_inv,
        "adap": adap,
        "adap_inv": adap_inv,
    }


def ocr_text(img: np.ndarray, psm: int = 6, whitelist: Optional[str] = None) -> str:
    if pytesseract is None:
        return ""

    cfg = f"--oem 3 --psm {psm}"
    if whitelist:
        cfg += f' -c tessedit_char_whitelist="{whitelist}"'

    try:
        out = pytesseract.image_to_string(img, lang="eng", config=cfg)
    except Exception:
        try:
            out = pytesseract.image_to_string(img, config=cfg)
        except Exception:
            return ""

    return norm_text(out)


def collect_ocr_candidates(img: np.ndarray) -> List[str]:
    variants = prep_variants(img)

    texts = []
    for key, v in variants.items():
        texts.append(ocr_text(v, psm=6))
        texts.append(ocr_text(v, psm=7))
        texts.append(ocr_text(v, psm=11))

    uniq = []
    seen = set()
    for t in texts:
        t = norm_text(t)
        if t and t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


# ============================================================
# EXTRAÇÃO
# ============================================================

_CLOCK_RE = re.compile(r"\b(\d{1,3})[:.](\d{2})\b")
_SCORE_X_RE = re.compile(r"\b(\d{1,2})\s*[-Xx]\s*(\d{1,2})\b")
_SCORE_SP_RE = re.compile(r"\b([A-Z]{2,5})\s+(\d{1,2})\s+(\d{1,2})\s+([A-Z]{2,5})\b")
_PLUS_RE = re.compile(r"\+\s*(\d{1,2})\b")


def extract_clock_from_texts(texts: List[str]) -> Optional[str]:
    best = None
    for t in texts:
        m = _CLOCK_RE.search(t)
        if m:
            minute = int(m.group(1))
            second = int(m.group(2))
            if 0 <= minute <= 150 and 0 <= second <= 59:
                cand = f"{minute:02d}:{second:02d}"
                if best is None:
                    best = cand
                else:
                    prev_min = int(best.split(":")[0])
                    if minute > prev_min:
                        best = cand
    return best


def has_event_overlay(texts: List[str]) -> bool:
    joined = " | ".join(texts)
    joined = norm_text(joined)
    return any(w in joined for w in EVENT_WORDS)


def looks_like_score_context(text: str) -> bool:
    t = norm_text(text)
    team_count = sum(1 for hint in TEAM_HINTS if hint in t)
    if team_count >= 1:
        return True
    if " X " in t or "-" in t:
        return True
    return False


def extract_score_from_texts(texts: List[str], clock: Optional[str]) -> Tuple[Optional[int], Optional[int], List[str]]:
    notes: List[str] = []

    # 1) padrão tipo: NOV 1 0 COR
    for t in texts:
        m = _SCORE_SP_RE.search(t)
        if m:
            a = int(m.group(2))
            b = int(m.group(3))
            if 0 <= a <= 20 and 0 <= b <= 20:
                notes.append(f"score por contexto de times: {a}x{b}")
                return a, b, notes

    # 2) padrão tipo 1-0 / 1x0
    for t in texts:
        m = _SCORE_X_RE.search(t)
        if m:
            a = int(m.group(1))
            b = int(m.group(2))
            if 0 <= a <= 20 and 0 <= b <= 20:
                notes.append(f"score por padrão x/-: {a}x{b}")
                return a, b, notes

    # 3) fallback: pegar números, mas protegendo contra clock
    clock_nums = set()
    if clock:
        parts = clock.split(":")
        if len(parts) == 2:
            try:
                clock_nums = {int(parts[0]), int(parts[1])}
            except Exception:
                clock_nums = set()

    for t in texts:
        nums = [int(x) for x in re.findall(r"\b\d{1,2}\b", t)]
        if len(nums) < 2:
            continue

        filtered = []
        for n in nums:
            if n in clock_nums:
                continue
            if 0 <= n <= 20:
                filtered.append(n)

        if len(filtered) >= 2 and looks_like_score_context(t):
            notes.append(f"score por fallback contextual: {filtered[0]}x{filtered[1]}")
            return filtered[0], filtered[1], notes

    notes.append("score não encontrado com segurança")
    return None, None, notes


def infer_period(clock: Optional[str], has_overlay: bool) -> Optional[str]:
    if not clock:
        return None

    try:
        minute = int(clock.split(":")[0])
    except Exception:
        return None

    # contador inicial de pré-jogo
    if minute == 0 and not has_overlay:
        return "pre_jogo"

    if minute < 46:
        return "primeiro_tempo"

    return "segundo_tempo"


def infer_state(
    score_a: Optional[int],
    score_b: Optional[int],
    clock: Optional[str],
    period: Optional[str],
    overlay: bool,
) -> str:
    if period == "pre_jogo":
        return "pre_jogo"

    if overlay and score_a is None and score_b is None:
        return "overlay_evento"

    if overlay:
        return "overlay_evento"

    if clock is not None:
        return "em_jogo"

    if score_a is not None and score_b is not None:
        return "em_jogo"

    return "desconhecido"


# ============================================================
# ANALISADOR
# ============================================================

def analyze_frame(path: Path) -> AnalysisResult:
    frame = safe_imread(path)
    notes: List[str] = []

    # recortes principais
    roi_top_left = crop_rel(frame, 0.00, 0.00, 0.55, 0.23)
    roi_top_wide = crop_rel(frame, 0.00, 0.00, 1.00, 0.32)
    roi_top_center = crop_rel(frame, 0.20, 0.00, 0.80, 0.26)

    texts_top_left = collect_ocr_candidates(roi_top_left)
    texts_top_wide = collect_ocr_candidates(roi_top_wide)
    texts_top_center = collect_ocr_candidates(roi_top_center)

    all_top = []
    seen = set()
    for t in texts_top_left + texts_top_center + texts_top_wide:
        if t and t not in seen:
            seen.add(t)
            all_top.append(t)

    clock = extract_clock_from_texts(all_top)
    if clock:
        notes.append(f"clock detectado: {clock}")
    else:
        notes.append("clock não detectado")

    overlay = has_event_overlay(all_top)
    notes.append(f"overlay={overlay}")

    score_a, score_b, score_notes = extract_score_from_texts(all_top, clock)
    notes.extend(score_notes)

    period = infer_period(clock, overlay)
    state = infer_state(score_a, score_b, clock, period, overlay)

    return AnalysisResult(
        file=path.name,
        state=state,
        period=period,
        score_a=score_a,
        score_b=score_b,
        clock=clock,
        has_overlay=overlay,
        raw_top_text=" | ".join(all_top[:8]),
        raw_wide_text=" | ".join(texts_top_wide[:8]),
        notes=notes,
    )


# ============================================================
# EXPECTATIVAS OPCIONAIS
# ============================================================

EXPECTED = {
    "pre_jogo.JPG": {
        "state": "pre_jogo",
        "score": (0, 0),
    },
    "Jogo.png": {
        "state": "em_jogo",
        "score": (1, 0),
        "clock": "92:44",
        "period": "segundo_tempo",
    },
    "eventos.png": {
        "state": "overlay_evento",
        "score": (0, 0),
    },
}


def compare_expected(res: AnalysisResult) -> List[str]:
    issues = []
    exp = EXPECTED.get(res.file)
    if not exp:
        return issues

    if "state" in exp and res.state != exp["state"]:
        issues.append(f"state esperado={exp['state']} atual={res.state}")

    if "score" in exp:
        if (res.score_a, res.score_b) != exp["score"]:
            issues.append(
                f"score esperado={exp['score'][0]}x{exp['score'][1]} atual={res.score_a}x{res.score_b}"
            )

    if "clock" in exp and res.clock != exp["clock"]:
        issues.append(f"clock esperado={exp['clock']} atual={res.clock}")

    if "period" in exp and res.period != exp["period"]:
        issues.append(f"period esperado={exp['period']} atual={res.period}")

    return issues


# ============================================================
# MAIN
# ============================================================

def print_result(res: AnalysisResult) -> None:
    print("=" * 90)
    print(f"Arquivo     : {res.file}")
    print(f"Estado      : {res.state}")
    print(f"Período     : {res.period}")
    print(f"Score       : {res.score_a} x {res.score_b}")
    print(f"Clock       : {res.clock}")
    print(f"Overlay     : {res.has_overlay}")
    print(f"OCR topo    : {res.raw_top_text[:500]}")
    print("Notas       :")
    for n in res.notes:
        print(f"  - {n}")

    issues = compare_expected(res)
    if issues:
        print("Validação   : FALHOU")
        for i in issues:
            print(f"  - {i}")
    else:
        print("Validação   : OK")


def main() -> None:
    configure_tesseract()

    print("\nTESTE DIRETO DE LEITURA DE SCOREBOARD\n")

    if not FRAME_DIR.exists():
        print(f"Pasta não encontrada: {FRAME_DIR}")
        return

    files = sorted(
        [
            p for p in FRAME_DIR.iterdir()
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        ]
    )

    if not files:
        print("Nenhuma imagem encontrada em data/frames.")
        return

    failed = 0

    for path in files:
        try:
            res = analyze_frame(path)
            print_result(res)

            issues = compare_expected(res)
            if issues:
                failed += 1

        except Exception as e:
            failed += 1
            print("=" * 90)
            print(
                f"Arquivo     : {path.name}")
            print(f"Erro        : {e}")

    print("\n" + "=" * 90)
    print(f"Total arquivos: {len(files)}")
    print(f"Falhas       : {failed}")
    print(f"Sucesso      : {len(files) - failed}")

    if failed == 0:
        print("RESULTADO FINAL: OK")
    else:
        print("RESULTADO FINAL: EXISTEM DIVERGÊNCIAS")


if __name__ == "__main__":
    main()