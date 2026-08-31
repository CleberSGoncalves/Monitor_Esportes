from __future__ import annotations

import re
import time
import threading
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional

import cv2
import numpy as np

from modules.vision_detectors import VisionDetectors


_REPLAY_RE = re.compile(r"\bREPLAY\b", re.IGNORECASE)
_VAR_RE = re.compile(r"\bVAR\b", re.IGNORECASE)
_SUB_RE = re.compile(r"\b(SUBSTITUI[CÇ][AÃ]O|SUBSTITUIU|ENTROU|SAIU)\b", re.IGNORECASE)
_YELLOW_RE = re.compile(r"\b(AMAREL[AO]|CART[AÃ]O\s+AMAREL[AO])\b", re.IGNORECASE)
_RED_RE = re.compile(r"\b(VERMELH[AO]|CART[AÃ]O\s+VERMELH[AO])\b", re.IGNORECASE)
_GOL_RE = re.compile(r"\bGO{1,6}L\b", re.IGNORECASE)
_CLOCK_RE = re.compile(r"(\d{1,3})\s*[:.]\s*(\d{2})")
_COUNTDOWN_HHMMSS_RE = re.compile(r"(\d{1,2})\s*[:.]\s*(\d{2})\s*[:.]\s*(\d{2})")


def _mean_absdiff(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None or getattr(a, "size", 0) == 0 or getattr(b, "size", 0) == 0:
        return 999.0
    if a.shape != b.shape:
        try:
            b = cv2.resize(b, (a.shape[1], a.shape[0]), interpolation=cv2.INTER_AREA)
        except Exception:
            return 999.0
    return float(cv2.absdiff(a, b).mean())
def _is_mmss_clock(value: Optional[str]) -> bool:
    if not value:
        return False
    m = re.fullmatch(r"(\d{1,3}):(\d{2})", str(value).strip())
    if not m:
        return False
    mm = int(m.group(1))
    ss = int(m.group(2))
    return 0 <= mm <= 180 and 0 <= ss <= 59


def _clock_to_seconds(clock: Optional[str]) -> Optional[int]:
    if not clock:
        return None

    txt = (clock or "").replace(" ", "")

    m3 = _COUNTDOWN_HHMMSS_RE.search(txt)
    if m3:
        hh = int(m3.group(1))
        mm = int(m3.group(2))
        ss = int(m3.group(3))
        if 0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59:
            return hh * 3600 + mm * 60 + ss

    m = _CLOCK_RE.search(txt)
    if not m:
        return None

    mm = int(m.group(1))
    ss = int(m.group(2))
    if 0 <= mm <= 180 and 0 <= ss <= 59:
        return mm * 60 + ss

    return None


def _is_reasonable_score(score: Optional[str]) -> bool:
    if not score:
        return False
    m = re.fullmatch(r"(\d+)x(\d+)", score.strip())
    if not m:
        return False
    a = int(m.group(1))
    b = int(m.group(2))
    if a > 9 or b > 9:
        return False
    if a + b > 12:
        return False
    return True


@dataclass
class DetectorConfig:
    black_mean_threshold: float = 12.0
    black_min_seconds: float = 3.0
    enable_fallback_reads = False

    freeze_diff_threshold: float = 1.2
    freeze_min_seconds: float = 3.0

    frame_state_window: int = 9
    no_overlay_hold_seconds: float = 8.0

    intervalo_clock_min_minutes: int = 38
    intervalo_clock_max_minutes: int = 60
    pos_jogo_clock_min_minutes: int = 85

    heartbeat_every_s: float = 30.0
    dedupe_window_s: float = 6.0
    replay_hold_seconds: float = 6.0
    visual_score_min_log: float = 0.45

    score_window: int = 5
    score_confirm_count: int = 2

    banner_window: int = 5
    banner_confirm_count: int = 2

    goal_cooldown_s: float = 20.0
    banner_event_cooldown_s: float = 12.0

    pre_visual_min_conf: float = 0.55
    game_visual_min_conf: float = 0.57
    intervalo_visual_min_conf: float = 0.56

    auto_template_enabled: bool = True
    auto_template_min_stable_count: int = 6
    auto_template_pre_conf: float = 0.80
    auto_template_game_conf: float = 0.83
    auto_template_intervalo_conf: float = 0.82

    clock_window: int = 7
    clock_confirm_count: int = 1
    max_clock_backwards_s: int = 20
    max_clock_jump_forward_s: int = 600

    pre_countdown_priority: bool = True
    keep_live_state_without_overlay_s: float = 20.0
    live_state_min_template_margin: float = 0.015

    recent_transcripts_window: int = 8

    seek_jump_seconds: int = 120
    seek_hold_seconds: float = 3.0

    require_scoreboard_for_live_score: bool = False
    require_clock_active_for_clock: bool = False
    require_banner_active_for_banner: bool = False


    fallback_score_every_s: float = 1.2
    fallback_clock_every_s: float = 0.8
    fallback_countdown_every_s: float = 1.5
    fallback_banner_every_s: float = 1.2

    enable_perf_log: bool = True

    cloud_enabled: bool = True
    cloud_interval_minutes: int = 2
    cloud_sample_every_s: float = 15.0
    cloud_batch_size: int = 4
    banner_ocr_interval_s: float = 1.0


@dataclass
class _State:
    black_on: bool = False
    black_since: Optional[float] = None

    freeze_on: bool = False
    freeze_since: Optional[float] = None
    last_gray: Optional[np.ndarray] = None

    last_score_read_t: float = -9999.0
    last_countdown_read_t: float = -9999.0
    last_banner_read_t: float = -9999.0
    last_clock_read_t: float = -9999.0

    phase: str = "pre_jogo"
    context: str = "desconhecido"

    current_team_a: str = "—"
    current_team_b: str = "—"
    current_match_display: str = "—"
    current_competition: str = "—"

    last_clock_text: Optional[str] = None
    last_score_text: Optional[str] = None
    last_banner_text: str = ""
    last_clock_seen_t: Optional[float] = None

    frame_states: Deque[str] = None  # type: ignore[assignment]
    last_visual_state: str = "nao_detectado"
    last_visual_info: Dict[str, Any] = None  # type: ignore[assignment]
    no_overlay_since: Optional[float] = None

    last_game_clock_seconds: Optional[int] = None
    last_game_score: Optional[str] = None
    last_live_visual_t: float = -9999.0

    first_half_started: bool = False
    interval_confirmed: bool = False
    second_half_started: bool = False

    replay_on: bool = False
    replay_until: float = 0.0

    last_heartbeat_t: float = 0.0

    last_push_type: str = ""
    last_push_label: str = ""
    last_push_t: float = -9999.0

    recent_scores: Deque[str] = None  # type: ignore[assignment]
    recent_banner_labels: Deque[str] = None  # type: ignore[assignment]
    recent_clocks: Deque[str] = None  # type: ignore[assignment]
    recent_transcripts: Deque[str] = None  # type: ignore[assignment]
    recent_hud_contexts: Deque[str] = None  # type: ignore[assignment]

    confirmed_score: Optional[str] = None
    confirmed_banner_label: Optional[str] = None
    confirmed_clock: Optional[str] = None
    confirmed_hud_context: str = ""

    last_goal_t: float = -9999.0
    last_banner_event_t: float = -9999.0

    seek_mode_until: float = 0.0
    last_seek_t: float = -9999.0

    last_perf: Dict[str, float] = None  # type: ignore[assignment]
    last_meta_read_t: float = -9999.0
    last_screen_context: Dict[str, Any] = None  # type: ignore[assignment]

    cloud_buffer: List[np.ndarray] = None  # type: ignore[assignment]
    last_cloud_sample_t: float = 0.0
    last_cloud_analysis_t: float = 0.0
    last_cloud_result: Dict[str, Any] = None  # type: ignore[assignment]
    last_cloud_correction_t: float = -9999.0
    cloud_analysis_in_progress: bool = False
    last_cloud_error: str = ""
    cloud_logs: List[str] = None # type: ignore[assignment]
    last_cloud_duration_s: float = 0.0
    _ia_status_msg: str = "Aguardando gatilho..."
    _last_cloud_raw_response: str = "Nenhuma análise realizada ainda."
    _cloud_countdown: int = 0
    _cloud_busy: bool = False


class EventDetector:
    def __init__(self, config: Optional[DetectorConfig] = None, log_hook: Optional[Any] = None) -> None:
        self.cfg = config or DetectorConfig()
        self._log_hook = log_hook
        self._event_id: Optional[str] = None
        self._timeline: List[Dict[str, Any]] = []
        self._t0_wall: Optional[float] = None

        self.vision = VisionDetectors(
            templates_root="templates",
            auto_templates_root="templates_auto",
            debug_dir="data/debug_templates",
            pre_threshold=self.cfg.pre_visual_min_conf,
            game_threshold=self.cfg.game_visual_min_conf,
            intervalo_threshold=self.cfg.intervalo_visual_min_conf,
        )
        self.vision.banner_ocr_interval_s = float(self.cfg.banner_ocr_interval_s or 1.0)
        
        print(
            "[EventDetector.__init__] "
            f"enable_fallback_reads={self.cfg.enable_fallback_reads} | "
            f"fallback_score_every_s={self.cfg.fallback_score_every_s} | "
            f"fallback_clock_every_s={self.cfg.fallback_clock_every_s} | "
            f"fallback_countdown_every_s={self.cfg.fallback_countdown_every_s} | "
            f"fallback_banner_every_s={self.cfg.fallback_banner_every_s}"
        )

        self._state = self._new_state()
        self._ingest_lock = threading.Lock()
        self._ingest_skip_overlap = 0
        self._last_ingest_sig = ""
        self._last_ingest_start_wall = 0.0
        self._pending_ingest: Optional[Dict[str, Any]] = None
        self._pending_ingest_lock = threading.Lock()
        self._cloud_expert = None
        self._cloud_init_attempted = False

        # Warmup em background (somente após _state estar pronto para evitar AttributeErrors)
        threading.Thread(target=self._vision_warmup, daemon=True, name="vision_warmup").start()

    def _vision_warmup(self) -> None:
        try:
            self._log("[WARMUP] Iniciando pré-carregamento de recursos de visão...")
            import numpy as np
            dummy = np.zeros((360, 640, 3), dtype=np.uint8)
            # Força o carregamento dos templates e primeira execução do matchTemplate (cache do CV2/SIMD)
            _ = self.vision.detect_frame_state(dummy)
            self._log("[WARMUP] Recursos de visão prontos na memória.")
        except Exception as e:
            self._log(f"[WARMUP] Alerta: Falha no warmup (não crítico): {e}")

    def set_logger(self, log_hook: Optional[Any]) -> None:
        self._log_hook = log_hook

    def _log(self, msg: str) -> None:
        try:
            if callable(self._log_hook):
                self._log_hook(str(msg))
        except Exception:
            pass

    def _new_state(self) -> _State:
        st = _State()
        st.frame_states = deque(maxlen=max(3, int(self.cfg.frame_state_window)))
        st.last_visual_info = {}
        st.recent_scores = deque(maxlen=max(3, int(self.cfg.score_window)))
        st.recent_banner_labels = deque(maxlen=max(3, int(self.cfg.banner_window)))
        st.recent_clocks = deque(maxlen=max(3, int(self.cfg.clock_window)))
        st.recent_transcripts = deque(maxlen=max(3, int(self.cfg.recent_transcripts_window)))
        st.recent_hud_contexts = deque(maxlen=8)
        st.last_perf = {}
        st.last_screen_context = {}
        st.cloud_buffer = []
        st.last_cloud_result = {}
        st.last_cloud_correction_t = -9999.0
        return st

    def start_session(self, event_id: str) -> None:
        self._event_id = event_id
        self._timeline = []
        self._t0_wall = time.time()
        self._state = self._new_state()
        self._ingest_lock = threading.Lock()


    def stop_session(self) -> None:
        t = self.elapsed_seconds()

        if self._state.black_on:
            self._push("interruption", "BLACK_SCREEN_END", t, confidence=0.85, details={})
        if self._state.freeze_on:
            self._push("interruption", "FREEZE_END", t, confidence=0.85, details={})

        try:
            self.vision.shutdown()
        except Exception:
            pass

        self._event_id = None
        self._t0_wall = None

    def add_timeline_entry(self, t_seconds: float, typ: str, label: str, details: Dict[str, Any], confidence: float = 0.85, clock: Optional[str] = None, match_display: Optional[str] = None) -> None:
        """Adiciona um evento manualmente à timeline (útil para IA Expert)."""
        self._push(typ, label, t_seconds, confidence=confidence, details=details, clock=clock, match_display=match_display)

    def elapsed_seconds(self) -> float:
        if not self._t0_wall:
            return 0.0
        return max(0.0, time.time() - self._t0_wall)

    def get_timeline(self) -> List[Dict[str, Any]]:
        return list(self._timeline)

    def get_last_perf(self) -> Dict[str, float]:
        return dict(self._state.last_perf or {})

    def ingest_transcript(self, text: str, t_seconds: float, source: str = "speech") -> None:
        clean = (text or "").strip()
        if clean:
            self._state.recent_transcripts.append(clean)

        self._push(
            "context",
            f"TRANSCRIPT:{source}",
            float(t_seconds),
            confidence=0.55,
            details={
                "text": clean[:240],
                "speech_summary": self._summarize_recent_speech(),
            },
        )

    def ingest_audio_metrics(self, t_seconds: float, rms: float, peak: float, silence_ratio: float) -> None:
        self._push(
            "context",
            "AUDIO_METRICS",
            float(t_seconds),
            confidence=0.60,
            details={
                "rms": float(rms),
                "peak": float(peak),
                "silence_ratio": float(silence_ratio),
            },
        )

    def _clean_ocr_text(self, txt: str) -> str:
        if not txt:
            return ""
        txt = txt.replace("\n", " ").replace("|", " ").replace("  ", " ")
        txt = re.sub(r"[^A-Za-zÀ-ÿ0-9\s:.\-]", "", txt).strip()
        if len(txt) < 3:
            return ""
        if len(txt) > 160:
            txt = txt[:160]
        return txt

    def _clean_meta_text(self, txt: Optional[str]) -> str:
        s = (txt or "").strip()
        s = re.sub(r"\s+", " ", s)
        s = s.strip(" -|")
        if len(s) < 2:
            return "—"
        return s

    def _clock_to_minute(self, clock_text: Optional[str]) -> Optional[int]:
        sec = _clock_to_seconds(clock_text)
        if sec is None:
            return None
        return int(sec // 60)


    def _normalize_match_text(self, value: Optional[str]) -> str:
        s = str(value or "").strip()
        s = re.sub(r"\s+", " ", s)
        return s.upper()

    def _has_team_competition_context(self, visual_info: Optional[Dict[str, Any]] = None) -> bool:
        st = self._state
        info = visual_info or {}
        known = [
            st.current_team_a,
            st.current_team_b,
            st.current_competition,
            info.get("team_a"),
            info.get("team_b"),
            info.get("competition"),
            info.get("competition_text"),
            info.get("match"),
            info.get("match_display"),
        ]
        for item in known:
            txt = self._normalize_match_text(item)
            if txt and txt != "—" and len(txt) >= 3:
                return True
        return False

    def _score_pre_game_evidence(
        self,
        visual_info: Optional[Dict[str, Any]],
        countdown_clock: Optional[str],
        game_clock: Optional[str],
        score: Optional[str],
    ) -> Dict[str, Any]:
        info = visual_info or {}
        st = self._state

        banner_text = self._normalize_match_text(
            info.get("banner_text") or info.get("hud_overlay") or info.get("banner_summary")
        )
        phase_text = self._normalize_match_text(info.get("phase_text") or info.get("match_phase_text"))
        ctx_summary = self._normalize_match_text(
            (info.get("screen_context") or {}).get("context_summary") or info.get("context_summary")
        )
        combo = " | ".join([x for x in [banner_text, phase_text, ctx_summary] if x])

        strong_patterns = [
            r"AO\s+VIVO\s+EM",
            r"EM\s+INSTANTES",
            r"DAQUI\s+A\s+POUCO",
            r"POUCO\s+PRA\s+INICIAR",
            r"POUCO\s+PARA\s+INICIAR",
            r"VAI\s+COME[CÇ]AR",
            r"VAI\s+COMECAR",
            r"J[ÁA]\s*J[ÁA]",
            r"PR[EÉ]\s*JOGO",
            r"ANTES\s+DO\s+JOGO",
            r"AQUECIMENTO",
            r"ESQUENTA",
            r"AGUARDE",
        ]
        hard_negative_patterns = [
            r"1T", r"2T", r"PRIMEIRO\s+TEMPO", r"SEGUNDO\s+TEMPO",
            r"INTERVALO", r"FIM\s+DO\s+JOGO", r"APITO\s+FINAL", r"ENCERRAD[OA]"
        ]

        score_value = 0
        reasons = []

        if countdown_clock:
            score_value += 4
            reasons.append('countdown')
        if combo and any(re.search(p, combo, re.IGNORECASE) for p in strong_patterns):
            score_value += 4
            reasons.append('banner_pre_jogo')
        if combo and 'PRE_JOGO' in combo:
            score_value += 3
            reasons.append('phase_pre_jogo')
        if self._has_team_competition_context(info):
            score_value += 1
            reasons.append('match_context')
        if not score:
            score_value += 1
            reasons.append('sem_score')
        if not game_clock:
            score_value += 1
            reasons.append('sem_clock_jogo')
        if str(info.get('visual_state') or '').strip().lower() == 'pre_jogo':
            score_value += 1
            reasons.append('template_pre_jogo')
        if bool(info.get('banner_active')):
            score_value += 1
            reasons.append('banner_active')

        if game_clock and _is_mmss_clock(game_clock):
            score_value -= 5
            reasons.append('clock_jogo_valido')
        if score and _is_reasonable_score(score):
            score_value -= 3
            reasons.append('placar_valido')
        if combo and any(re.search(p, combo, re.IGNORECASE) for p in hard_negative_patterns):
            score_value -= 6
            reasons.append('texto_contra_pre_jogo')
        if st.first_half_started:
            score_value -= 3
            reasons.append('jogo_ja_iniciado')
        if st.second_half_started:
            score_value -= 2
            reasons.append('segundo_tempo_ja_visto')

        return {
            'score': score_value,
            'is_pre_game': score_value >= 5,
            'reasons': reasons,
            'banner_text': banner_text[:180],
            'phase_text': phase_text[:120],
        }

    def _event_meta_details(self, clock_ref: Optional[str]) -> Dict[str, Any]:
        st = self._state
        minute = self._clock_to_minute(clock_ref)
        return {
            "clock": clock_ref,
            "minute": minute,
            "match": st.current_match_display,
            "competition": st.current_competition,
            "team_a": st.current_team_a,
            "team_b": st.current_team_b,
        }

    def _update_match_metadata_from_frame(self, frame_bgr: np.ndarray, t: Optional[float] = None) -> None:
        st = self._state
        now_t = float(t if t is not None else self.elapsed_seconds())

        if (now_t - float(getattr(st, 'last_meta_read_t', -9999.0) or -9999.0)) < 5.0:
            self._log(f"[DETECTOR][STEP] update_match_metadata:skip_throttled | dt={now_t - float(getattr(st, 'last_meta_read_t', -9999.0) or -9999.0):.2f}")
            return

        st.last_meta_read_t = now_t
        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            self._log("[DETECTOR][WARN] update_match_metadata frame vazio")
            return

        # Emergency safe mode for local pipeline:
        # do not call heavy OCR/context readers here; keep ingest responsive.
        self._log("[DETECTOR][STEP] update_match_metadata:safe_mode_skip_heavy_reads")
        return

    def _summarize_recent_speech(self) -> str:
        texts = " ".join(self._state.recent_transcripts).lower()
        if not texts.strip():
            return "Comentário geral da transmissão"

        rules = [
            (["escalacao", "escalação", "titular", "banco"], "Comentando escalação e jogadores"),
            (["arbitragem", "juiz", "var"], "Comentando arbitragem"),
            (["posse", "pressao", "pressão", "ataque", "defesa", "tatico", "tática"], "Comentando tática e volume do jogo"),
            (["melhores momentos", "replay", "repeticao", "repetição"], "Comentando replay ou lance anterior"),
            (["intervalo", "segundo tempo", "primeiro tempo"], "Comentando o momento da partida"),
            (["lesao", "lesão", "machuc", "substitui"], "Comentando substituição ou problema físico"),
            (["gol", "chance", "finalizacao", "finalização", "cruzamento", "escanteio"], "Comentando lance de perigo"),
        ]

        for keys, label in rules:
            if any(k in texts for k in keys):
                return label

        tail = " ".join(self._state.recent_transcripts)[-140:].strip()
        if tail:
            return tail[:140]

        return "Comentário geral da transmissão"

    def _stable_majority(self, items: Deque[str], min_count: int) -> Optional[str]:
        if not items:
            return None
        cnt = Counter([x for x in items if x])
        if not cnt:
            return None
        label, qty = cnt.most_common(1)[0]
        if qty >= min_count:
            return label
        return None

    def _dominant_visual_state(self) -> str:
        st = self._state
        if not st.frame_states:
            return "nao_detectado"

        cnt = Counter(st.frame_states)
        label, qty = cnt.most_common(1)[0]
        ratio = qty / len(st.frame_states)

        if ratio >= 0.55:
            return label

        return st.last_visual_state or label

    def _stable_state_count(self, label: str) -> int:
        st = self._state
        if not st.frame_states:
            return 0
        return sum(1 for x in st.frame_states if x == label)

    def _min_conf_for_label(self, label: str) -> float:
        if label == "pre_jogo":
            return float(self.cfg.auto_template_pre_conf)
        if label == "jogo":
            return float(self.cfg.auto_template_game_conf)
        if label == "intervalo":
            return float(self.cfg.auto_template_intervalo_conf)
        return 999.0

    def _classify_banner_label(self, banner: str, visual_info: Optional[Dict[str, Any]] = None) -> str:
        info = visual_info or {}
        kind = str(info.get("banner_visual_kind") or "").strip().lower()
        b = (banner or "").upper()

        if kind == "cartao_amarelo":
            return "CARTAO_AMARELO"
        if kind == "cartao_vermelho":
            return "CARTAO_VERMELHO"
        if kind == "var_ou_replay":
            if _REPLAY_RE.search(b):
                return "REPLAY"
            if _VAR_RE.search(b):
                return "VAR"
            return "VAR"

        if not b:
            return ""

        if _VAR_RE.search(b):
            return "VAR"
        if _SUB_RE.search(b):
            return "SUBSTITUICAO"
        if _YELLOW_RE.search(b):
            return "CARTAO_AMARELO"
        if _RED_RE.search(b):
            return "CARTAO_VERMELHO"
        if _GOL_RE.search(b):
            return "GOL"
        if _REPLAY_RE.search(b):
            return "REPLAY"
        return ""

    def _event_clock_for_log(self) -> Optional[str]:
        return self._state.last_clock_text or self._state.confirmed_clock

    def _enter_seek_mode(self, t: float, old_clock: Optional[str], new_clock: Optional[str]) -> None:
        st = self._state

        st.recent_scores.clear()
        st.recent_clocks.clear()
        st.recent_banner_labels.clear()

        st.confirmed_score = None
        st.confirmed_clock = None
        st.confirmed_banner_label = None

        st.last_goal_t = t
        st.last_banner_event_t = t
        st.seek_mode_until = t + float(self.cfg.seek_hold_seconds)
        st.last_seek_t = t

        self._push(
            "status",
            "SEEK_DETECTED",
            t,
            confidence=0.90,
            details={
                "old_clock": old_clock,
                "new_clock": new_clock,
                "hold_seconds": float(self.cfg.seek_hold_seconds),
            },
        )

    def _maybe_detect_seek(self, accepted_clock: Optional[str], t: float) -> None:
        st = self._state

        if not accepted_clock or not _is_mmss_clock(accepted_clock):
            return

        new_sec = _clock_to_seconds(accepted_clock)
        old_sec = st.last_game_clock_seconds

        if new_sec is None or old_sec is None:
            return

        if abs(new_sec - old_sec) >= int(self.cfg.seek_jump_seconds):
            self._enter_seek_mode(t, st.last_clock_text, accepted_clock)

    def _resolve_state(
        self,
        raw_visual_state: str,
        visual_info: Dict[str, Any],
        countdown_clock: Optional[str],
        game_clock: Optional[str],
        score: Optional[str],
        t: float,
    ) -> str:
        st = self._state
        raw_visual_state = raw_visual_state or "nao_detectado"

        margin = float((visual_info or {}).get("margin", 0.0) or 0.0)
        pre_score = float((visual_info or {}).get("pre_score", 0.0) or 0.0)
        game_score = float((visual_info or {}).get("game_score", 0.0) or 0.0)

        scoreboard_active = bool((visual_info or {}).get("scoreboard_active"))
        clock_active = bool((visual_info or {}).get("clock_active"))
        banner_active = bool((visual_info or {}).get("banner_active"))
        match_phase_text = str((visual_info or {}).get("match_phase_text") or "").strip().lower()
        pre_game_signal = self._score_pre_game_evidence(
            visual_info=visual_info,
            countdown_clock=countdown_clock,
            game_clock=game_clock,
            score=score,
        )

        if game_clock and clock_active:
            csec = _clock_to_seconds(game_clock)
            if csec is not None:
                prev_csec = st.last_game_clock_seconds
                if prev_csec is None:
                    st.last_live_visual_t = t
                    return "jogo"
                if abs(csec - prev_csec) >= int(self.cfg.seek_jump_seconds):
                    st.last_live_visual_t = t
                    return "jogo"
                if csec >= (prev_csec - 5):
                    st.last_live_visual_t = t
                    return "jogo"

        if score and _is_reasonable_score(score) and (scoreboard_active or not self.cfg.require_scoreboard_for_live_score):
            st.last_live_visual_t = t
            return "jogo"

        if match_phase_text == "intervalo":
            return "intervalo"
        if match_phase_text == "pre_jogo":
            return "pre_jogo"
        if match_phase_text in ("primeiro_tempo", "segundo_tempo"):
            return "jogo"
        if pre_game_signal.get("is_pre_game") and not st.first_half_started:
            if not game_clock and not score:
                return "pre_jogo"
            if raw_visual_state in ("pre_jogo", "nao_detectado"):
                return "pre_jogo"

        if st.first_half_started:
            if raw_visual_state == "pre_jogo":
                if countdown_clock and not game_clock and not score and not scoreboard_active:
                    return "pre_jogo" if (t - st.last_live_visual_t) > 25.0 else "jogo"
                return "jogo"

            if raw_visual_state == "nao_detectado":
                if (t - float(st.last_live_visual_t)) <= float(self.cfg.keep_live_state_without_overlay_s):
                    return "jogo"

        if not st.first_half_started and self.cfg.pre_countdown_priority and countdown_clock:
            if raw_visual_state == "pre_jogo":
                return "pre_jogo"
            if raw_visual_state == "nao_detectado":
                return "pre_jogo"
            if raw_visual_state == "jogo":
                if game_score >= pre_score and margin >= float(self.cfg.live_state_min_template_margin):
                    return "jogo"
                if not scoreboard_active and not clock_active:
                    return "pre_jogo"
                return "pre_jogo"
            if raw_visual_state == "intervalo":
                return "pre_jogo"

        if raw_visual_state == "jogo":
            return "jogo"
        if raw_visual_state == "intervalo":
            return "intervalo"
        if raw_visual_state == "pre_jogo":
            return "pre_jogo"

        if raw_visual_state == "nao_detectado":
            if st.first_half_started and ((game_clock is not None) or (score is not None) or scoreboard_active):
                return "jogo"
            if not st.first_half_started and countdown_clock and not scoreboard_active:
                return "pre_jogo"
            if pre_game_signal.get("is_pre_game") and not st.first_half_started:
                return "pre_jogo"
            if banner_active and match_phase_text == "intervalo":
                return "intervalo"

        return raw_visual_state

    def _apply_live_lock(
        self,
        dominant_state: str,
        countdown_clock: Optional[str],
        game_clock: Optional[str],
        score: Optional[str],
        t: float,
    ) -> str:
        st = self._state

        if st.first_half_started:
            if dominant_state == "pre_jogo" and not countdown_clock:
                return "jogo"

            if (game_clock or score) is not None:
                return "jogo"

            if (t - float(st.last_live_visual_t)) <= float(self.cfg.keep_live_state_without_overlay_s):
                if dominant_state in ("nao_detectado", "pre_jogo"):
                    return "jogo"
        else:
            if dominant_state == "jogo" and countdown_clock and not game_clock and not score:
                return "pre_jogo"

        return dominant_state

    def _accept_and_stabilize_clock(self, raw_clock: Optional[str], visual_state: str, t: float) -> Optional[str]:
        st = self._state

        if not raw_clock:
            return st.confirmed_clock or st.last_clock_text

        if visual_state in ("jogo", "intervalo") and not _is_mmss_clock(raw_clock):
            return st.confirmed_clock or st.last_clock_text

        raw_sec = _clock_to_seconds(raw_clock)
        if raw_sec is None:
            return st.confirmed_clock or st.last_clock_text

        prev_sec = _clock_to_seconds(st.confirmed_clock or st.last_clock_text)

        if prev_sec is not None:
            delta = raw_sec - prev_sec

            if abs(delta) >= int(self.cfg.seek_jump_seconds):
                st.confirmed_clock = raw_clock
                return raw_clock

            if visual_state in ("jogo", "intervalo"):
                if delta < -int(self.cfg.max_clock_backwards_s):
                    return st.confirmed_clock or st.last_clock_text
                if delta > int(self.cfg.max_clock_jump_forward_s):
                    return st.confirmed_clock or st.last_clock_text

        st.recent_clocks.append(raw_clock)

        stable_clock = self._stable_majority(st.recent_clocks, self.cfg.clock_confirm_count)
        if stable_clock:
            # PRIORIDADE CLOUD: Trava de 120s pós-correção inteligente
            if self.cfg.cloud_enabled and (t - st.last_cloud_correction_t < 120.0):
                if stable_clock != st.confirmed_clock:
                    return stable_clock # Retornamos o estável mas não atualizamos o 'confirmed' global

            st.confirmed_clock = stable_clock
            return stable_clock

        if visual_state == "pre_jogo":
            st.confirmed_clock = raw_clock
            return raw_clock

        return st.confirmed_clock or st.last_clock_text or raw_clock

    def _update_phase_by_clock(self, clock_sec: int, t: float) -> None:
        st = self._state
        prev = st.last_game_clock_seconds

        if t <= st.seek_mode_until:
            if 0 <= clock_sec < 46 * 60:
                st.phase = "jogo"
                st.first_half_started = True
                st.second_half_started = False
            else:
                st.phase = "jogo"
                st.first_half_started = True
                st.second_half_started = True
                st.interval_confirmed = True
            st.last_game_clock_seconds = clock_sec
            return

        if not st.first_half_started:
            if 0 <= clock_sec < 45 * 60:
                st.first_half_started = True
                st.phase = "primeiro_tempo"
                self._push(
                    "phase",
                    "PRIMEIRO_TEMPO_START",
                    t,
                    confidence=0.95,
                    details={"clock_seconds": clock_sec, "source": "clock"},
                )
                st.last_game_clock_seconds = clock_sec
                return

        if st.first_half_started and not st.second_half_started:
            if prev is not None:
                if prev >= 35 * 60 and clock_sec <= 10 * 60:
                    st.interval_confirmed = True
                    st.second_half_started = True
                    st.phase = "segundo_tempo"
                    self._push(
                        "phase",
                        "SEGUNDO_TEMPO_START",
                        t,
                        confidence=0.95,
                        details={"clock_seconds": clock_sec, "source": "clock_reset"},
                    )
                    st.last_game_clock_seconds = clock_sec
                    return

            if clock_sec >= 46 * 60 and not st.second_half_started:
                st.interval_confirmed = True
                st.second_half_started = True
                st.phase = "segundo_tempo"
                self._push(
                    "phase",
                    "SEGUNDO_TEMPO_START",
                    t,
                    confidence=0.90,
                    details={"clock_seconds": clock_sec, "source": "clock_continuous"},
                )
                st.last_game_clock_seconds = clock_sec
                return

        if st.second_half_started and clock_sec >= 85 * 60:
            if st.phase != "pos_jogo":
                st.phase = "pos_jogo"
                self._push(
                    "phase",
                    "POS_JOGO_START",
                    t,
                    confidence=0.85,
                    details={"clock_seconds": clock_sec, "source": "clock"},
                )

        st.last_game_clock_seconds = clock_sec

    def _maybe_push_visual_debug(self, dominant_state: str, visual_info: Dict[str, Any], t: float) -> None:
        score = float((visual_info or {}).get("visual_confidence", (visual_info or {}).get("score", 0.0)) or 0.0)
        if score < self.cfg.visual_score_min_log:
            return

        self._push(
            "ocr",
            f"VISUAL_{dominant_state.upper()}",
            t,
            confidence=score,
            details=visual_info or {},
        )

    def _maybe_auto_collect_template(
        self,
        frame_bgr: np.ndarray,
        dominant_state: str,
        visual_info: Dict[str, Any],
        clock: Optional[str],
        score: Optional[str],
        banner: str,
        t: float,
    ) -> None:
        if not self.cfg.auto_template_enabled:
            return

        st = self._state

        if dominant_state not in ("pre_jogo", "jogo", "intervalo"):
            return

        stable_count = self._stable_state_count(dominant_state)
        if stable_count < int(self.cfg.auto_template_min_stable_count):
            return

        conf = float((visual_info or {}).get("visual_confidence", (visual_info or {}).get("score", 0.0)) or 0.0)
        if conf < self._min_conf_for_label(dominant_state):
            return

        if st.black_on or st.freeze_on:
            return

        if st.replay_on and t <= st.replay_until:
            return

        if banner and _VAR_RE.search(banner):
            return

        if dominant_state == "pre_jogo" and not clock:
            return

        if dominant_state == "jogo" and not (clock or score):
            return

        saved_path = self.vision.maybe_auto_collect_template(
            frame_bgr=frame_bgr,
            label=dominant_state,
            confidence=conf,
            t_seconds=t,
            phase=st.phase,
            context=st.context,
            extra={
                "clock": clock,
                "score": score,
                "banner_hint": (banner or "")[:80],
                "stable_count": stable_count,
            },
        )

        if saved_path:
            self._push(
                "status",
                "AUTO_TEMPLATE_SAVED",
                t,
                confidence=min(0.99, conf),
                details={
                    "label": dominant_state,
                    "path": saved_path,
                    "clock": clock,
                    "score": score,
                    "stable_count": stable_count,
                },
            )

    def _update_phase_from_visual(self, dominant_state: str, t: float) -> None:
        st = self._state

        if st.first_half_started and st.last_game_clock_seconds is not None:
            if dominant_state == "intervalo" and not st.second_half_started:
                last_seen = st.last_clock_seen_t
                clock_missing_long_enough = (
                    last_seen is not None and
                    (t - float(last_seen)) >= float(self.cfg.no_overlay_hold_seconds)
                )

                if clock_missing_long_enough and not st.interval_confirmed:
                    st.interval_confirmed = True
                    st.phase = "intervalo"
                    self._push(
                        "phase",
                        "INTERVALO_START",
                        t,
                        confidence=0.80,
                        details={"source": "visual_support", "clock": st.last_clock_text},
                    )
            return

        info = st.last_visual_info or {}
        match_phase_text = (info.get("match_phase_text") or "").strip().lower()
        pre_game_signal = self._score_pre_game_evidence(
            visual_info=info,
            countdown_clock=st.last_clock_text if not _is_mmss_clock(st.last_clock_text) else None,
            game_clock=st.last_clock_text if _is_mmss_clock(st.last_clock_text) else None,
            score=st.last_score_text,
        )

        if match_phase_text == "pre_jogo" or (pre_game_signal.get("is_pre_game") and not st.first_half_started):
            st.no_overlay_since = None
            if not st.first_half_started:
                if st.phase != "pre_jogo":
                    self._push(
                        "phase",
                        "PRE_JOGO_START",
                        t,
                        confidence=0.88 if match_phase_text == "pre_jogo" else 0.84,
                        details={
                            "clock": st.last_clock_text,
                            "source": "visual_match_phase" if match_phase_text == "pre_jogo" else "pre_game_score",
                            "pre_game_reasons": pre_game_signal.get("reasons", []),
                            "pre_game_score": pre_game_signal.get("score"),
                        },
                    )
                st.phase = "pre_jogo"
            return

        if match_phase_text == "intervalo":
            st.no_overlay_since = None
            if st.first_half_started and not st.second_half_started:
                if not st.interval_confirmed:
                    st.interval_confirmed = True
                    st.phase = "intervalo"
                    self._push(
                        "phase",
                        "INTERVALO_START",
                        t,
                        confidence=0.90,
                        details={"clock": st.last_clock_text, "source": "visual_match_phase"},
                    )
                else:
                    st.phase = "intervalo"
            return

        if match_phase_text == "primeiro_tempo":
            st.no_overlay_since = None
            if not st.first_half_started:
                st.first_half_started = True
                st.phase = "jogo"
                self._push(
                    "phase",
                    "PRIMEIRO_TEMPO_START",
                    t,
                    confidence=0.93,
                    details={"clock": st.last_clock_text, "source": "visual_match_phase"},
                )
            else:
                st.phase = "jogo"
            return

        if match_phase_text == "segundo_tempo":
            st.no_overlay_since = None

            if not st.first_half_started:
                st.first_half_started = True

            if not st.interval_confirmed:
                st.interval_confirmed = True

            if not st.second_half_started:
                st.second_half_started = True
                st.phase = "jogo"
                self._push(
                    "phase",
                    "SEGUNDO_TEMPO_START",
                    t,
                    confidence=0.93,
                    details={"clock": st.last_clock_text, "source": "visual_match_phase"},
                )
            else:
                st.phase = "jogo"
            return

        if dominant_state == "jogo":
            st.no_overlay_since = None

            if not st.first_half_started:
                st.phase = "jogo"
                st.first_half_started = True
                self._push(
                    "phase",
                    "PRIMEIRO_TEMPO_START",
                    t,
                    confidence=0.92,
                    details={"clock": st.last_clock_text, "source": "visual"},
                )
                return

            if st.interval_confirmed and not st.second_half_started:
                st.phase = "jogo"
                st.second_half_started = True
                self._push(
                    "phase",
                    "SEGUNDO_TEMPO_START",
                    t,
                    confidence=0.92,
                    details={"clock": st.last_clock_text, "source": "visual"},
                )
                return

            st.phase = "jogo"
            return

        if dominant_state == "intervalo":
            st.no_overlay_since = None
            if st.first_half_started and not st.second_half_started and not st.interval_confirmed:
                st.interval_confirmed = True
                st.phase = "intervalo"
                self._push(
                    "phase",
                    "INTERVALO_START",
                    t,
                    confidence=0.82,
                    details={"clock": st.last_clock_text, "source": "visual_intervalo"},
                )
            return

        if dominant_state == "pre_jogo" or (pre_game_signal.get("is_pre_game") and not st.first_half_started):
            st.no_overlay_since = None
            if not st.first_half_started and st.phase != "pre_jogo":
                st.phase = "pre_jogo"
                self._push(
                    "phase",
                    "PRE_JOGO_START",
                    t,
                    confidence=0.90 if dominant_state == "pre_jogo" else 0.84,
                    details={
                        "clock": st.last_clock_text,
                        "source": "visual" if dominant_state == "pre_jogo" else "pre_game_score",
                        "pre_game_reasons": pre_game_signal.get("reasons", []),
                        "pre_game_score": pre_game_signal.get("score"),
                    },
                )
            return

        if st.no_overlay_since is None:
            st.no_overlay_since = t

        if (t - st.no_overlay_since) < self.cfg.no_overlay_hold_seconds:
            return

        if st.phase == "jogo":
            last_sec = st.last_game_clock_seconds
            if last_sec is None:
                return

            last_min = int(last_sec // 60)

            if st.second_half_started and last_min >= self.cfg.pos_jogo_clock_min_minutes:
                st.phase = "pos_jogo"
                self._push(
                    "phase",
                    "POS_JOGO_START",
                    st.no_overlay_since,
                    confidence=0.82,
                    details={
                        "source": "historico",
                        "last_clock_seconds": last_sec,
                        "clock": st.last_clock_text,
                    },
                )
                return

            if (
                st.first_half_started and
                not st.second_half_started and
                self.cfg.intervalo_clock_min_minutes <= last_min <= self.cfg.intervalo_clock_max_minutes
            ):
                if not st.interval_confirmed:
                    st.interval_confirmed = True
                    st.phase = "intervalo"
                    self._push(
                        "phase",
                        "INTERVALO_START",
                        st.no_overlay_since,
                        confidence=0.82,
                        details={
                            "source": "historico",
                            "last_clock_seconds": last_sec,
                            "clock": st.last_clock_text,
                        },
                    )

    def _detect_match_events_stable(self, score: Optional[str], banner: str, t: float, visual_info: Dict[str, Any]) -> None:
        st = self._state
        info = visual_info or {}

        if t <= st.seek_mode_until:
            if score and _is_reasonable_score(score):
                st.confirmed_score = score
                st.last_score_text = score
            return

        scoreboard_active = bool(info.get("scoreboard_active"))
        banner_active = bool(info.get("banner_active"))
        banner_visual_kind = str(info.get("banner_visual_kind") or "").strip().lower()
        banner_visual_confidence = float(info.get("banner_visual_confidence") or 0.0)

        if score and _is_reasonable_score(score):
            if (not self.cfg.require_scoreboard_for_live_score) or scoreboard_active:
                st.recent_scores.append(score)

        stable_score = self._stable_majority(st.recent_scores, self.cfg.score_confirm_count)
        if stable_score and stable_score != st.confirmed_score:
            # PRIORIDADE CLOUD: Se houve correção da nuvem nos últimos 120s, local não sobrescreve
            # a menos que o valor sugerido localmente seja exatamente o que a nuvem já confirmou
            if self.cfg.cloud_enabled and (t - st.last_cloud_correction_t < 120.0):
                if stable_score != st.confirmed_score:
                    # Omitir log para não poluir, apenas ignoramos a mudança local "incerta"
                    return

            old_confirmed = st.confirmed_score
            st.confirmed_score = stable_score

            if old_confirmed and (t - st.last_goal_t) >= self.cfg.goal_cooldown_s:
                m_old = re.match(r"^(\d+)x(\d+)$", old_confirmed or "")
                m_new = re.match(r"^(\d+)x(\d+)$", stable_score or "")

                plausible = False
                if m_old and m_new:
                    oa, ob = int(m_old.group(1)), int(m_old.group(2))
                    na, nb = int(m_new.group(1)), int(m_new.group(2))
                    if 0 <= na - oa <= 1 and 0 <= nb - ob <= 1 and ((na - oa) + (nb - ob) == 1):
                        plausible = True

                if plausible:
                    clock_ref = self._event_clock_for_log()
                    meta = self._event_meta_details(clock_ref)

                    self._push(
                        "match_event",
                        "GOL",
                        t,
                        confidence=0.92,
                        details={
                            "score_from": old_confirmed,
                            "score_to": stable_score,
                            "clock": meta["clock"],
                            "minute": meta["minute"],
                            "match": meta["match"],
                            "competition": meta["competition"],
                            "team_a": meta["team_a"],
                            "team_b": meta["team_b"],
                            "source": "score_change",
                        },
                    )
                    st.last_goal_t = t

        banner_label = ""
        if info.get("is_var"):
            banner_label = "VAR"
        elif info.get("is_substitution"):
            banner_label = "SUBSTITUICAO"
        elif info.get("is_yellow_card"):
            banner_label = "CARTAO_AMARELO"
        elif info.get("is_red_card"):
            banner_label = "CARTAO_VERMELHO"
        elif info.get("is_goal"):
            banner_label = "GOL"
        elif info.get("is_replay"):
            banner_label = "REPLAY"

        if not banner_label:
            banner_label = self._classify_banner_label(banner, info)

        accept_banner = False
        if banner_label:
            if self.cfg.require_banner_active_for_banner:
                accept_banner = banner_active
            else:
                accept_banner = banner_active or banner_visual_kind in (
                    "cartao_amarelo",
                    "cartao_vermelho",
                    "var_ou_replay",
                    "overlay_info",
                ) or bool(banner)

        if banner_visual_kind in ("cartao_amarelo", "cartao_vermelho") and banner_visual_confidence >= 0.60:
            accept_banner = True

        if banner_label and accept_banner:
            st.recent_banner_labels.append(banner_label)
        else:
            st.recent_banner_labels.append("")

        stable_banner = self._stable_majority(st.recent_banner_labels, self.cfg.banner_confirm_count)
        if stable_banner:
            is_new = (stable_banner != st.confirmed_banner_label)
            # Sensibilidade v8.9: Se o label é o mesmo, mas o texto OCR mudou, consideramos 'novo'
            if not is_new:
                last_txt = str(st.last_banner_text or "").upper().strip()
                new_txt = str(banner or "").upper().strip()
                if len(new_txt) > 5 and last_txt != new_txt:
                    is_new = True

            if is_new and (t - st.last_banner_event_t) >= 8.0:
                st.confirmed_banner_label = stable_banner
                st.last_banner_text = banner
                clock_ref = self._event_clock_for_log()
                meta = self._event_meta_details(clock_ref)

                self._push(
                    "match_event",
                    stable_banner,
                    t,
                    confidence=0.84 if stable_banner != "REPLAY" else 0.72,
                    details={
                        "banner": (banner or "")[:160],
                        "clock": meta["clock"],
                        "minute": meta["minute"],
                        "match": meta["match"],
                        "competition": meta["competition"],
                        "team_a": meta["team_a"],
                        "team_b": meta["team_b"],
                        "summary": info.get("banner_summary", "") or info.get("context_summary", ""),
                        "screen_context": info.get("screen_context"),
                        "source": "banner_flags_rich" if is_new and stable_banner == st.confirmed_banner_label else "banner_flags",
                        "banner_active": banner_active,
                        "banner_visual_kind": banner_visual_kind,
                    },
                )
                st.last_banner_event_t = t

        hud_ctx = str(info.get("screen_context", {}).get("top_hud", {}).get("context_text") or "").strip()
        if hud_ctx and len(hud_ctx) >= 4:
            st.recent_hud_contexts.append(hud_ctx)
        else:
            st.recent_hud_contexts.append("")

        stable_hud_ctx = self._stable_majority(st.recent_hud_contexts, 3)
        if stable_hud_ctx and stable_hud_ctx != st.confirmed_hud_context:
            if (t - getattr(st, 'last_hud_event_t', 0.0)) >= 15.0:
                st.confirmed_hud_context = stable_hud_ctx
                st.last_hud_event_t = t
                clock_ref = self._event_clock_for_log()
                meta = self._event_meta_details(clock_ref)
                self._push(
                    "match_event",
                    "HUD_MENSAGEM",
                    t,
                    confidence=0.90,
                    details={
                        "mensagem": stable_hud_ctx,
                        "clock": meta["clock"],
                        "minute": meta["minute"],
                        "match": meta["match"],
                        "competition": meta["competition"],
                        "source": "hud_context",
                    }
                )
        elif not stable_hud_ctx and st.confirmed_hud_context:
            st.confirmed_hud_context = ""

    def _update_replay_context(self, banner: str, t: float, visual_info: Optional[Dict[str, Any]] = None) -> None:
        st = self._state
        info = visual_info or {}

        if info.get("is_replay"):
            st.replay_on = True
            st.replay_until = t + self.cfg.replay_hold_seconds
            return

        if str(info.get("banner_visual_kind") or "").strip().lower() == "var_ou_replay":
            if banner and _REPLAY_RE.search(banner):
                st.replay_on = True
                st.replay_until = t + self.cfg.replay_hold_seconds
                return

        if banner and _REPLAY_RE.search(banner):
            st.replay_on = True
            st.replay_until = t + self.cfg.replay_hold_seconds

    def _update_context(
        self,
        dominant_state: str,
        clock: Optional[str],
        score: Optional[str],
        banner: str,
        t: float,
    ) -> None:
        st = self._state

        if st.black_on or st.freeze_on:
            if st.context != "interrupcao_tecnica":
                st.context = "interrupcao_tecnica"
                self._push(
                    "context",
                    "INTERRUPCAO_TECNICA",
                    t,
                    confidence=0.90,
                    details={"black": st.black_on, "freeze": st.freeze_on, "context_summary": str((st.last_visual_info or {}).get("context_summary") or "")[:180]},
                )
            return

        if st.replay_on and t <= st.replay_until:
            if st.context != "replay":
                st.context = "replay"
                self._push("context", "REPLAY", t, confidence=0.80, details={"context_summary": str((st.last_visual_info or {}).get("context_summary") or (st.last_visual_info or {}).get("banner_summary") or "")[:180], "screen_context": (st.last_visual_info or {}).get("screen_context")})
            return
        else:
            st.replay_on = False

        if banner and _VAR_RE.search(banner):
            if st.context != "var":
                st.context = "var"
                self._push("context", "VAR", t, confidence=0.75, details={"context_summary": str((st.last_visual_info or {}).get("context_summary") or (st.last_visual_info or {}).get("banner_summary") or "")[:180], "screen_context": (st.last_visual_info or {}).get("screen_context")})
            return

        if dominant_state == "pre_jogo" and not st.first_half_started:
            if st.context != "pre_jogo_countdown":
                st.context = "pre_jogo_countdown"
                self._push(
                    "context",
                    "PRE_JOGO_COUNTDOWN",
                    t,
                    confidence=0.90,
                    details={"clock": clock, "visual": st.last_visual_info, "context_summary": str((st.last_visual_info or {}).get("context_summary") or "")[:180], "screen_context": (st.last_visual_info or {}).get("screen_context"), "pre_game_signal": self._score_pre_game_evidence(st.last_visual_info, clock if not _is_mmss_clock(clock) else None, clock if _is_mmss_clock(clock) else None, score)},
                )
            return

        if dominant_state == "jogo" or st.phase == "jogo":
            if st.context != "jogo_ao_vivo":
                self._push(
                    "context",
                    "JOGO_AO_VIVO",
                    t,
                    confidence=0.88,
                    details={"clock": clock, "score": score, "visual": st.last_visual_info, "context_summary": str((st.last_visual_info or {}).get("context_summary") or "")[:180], "screen_context": (st.last_visual_info or {}).get("screen_context")},
                )
                st.context = "jogo_ao_vivo"
            return

        if dominant_state == "intervalo" or st.phase == "intervalo":
            if st.context != "intervalo":
                st.context = "intervalo"
                self._push(
                    "context",
                    "INTERVALO",
                    t,
                    confidence=0.80,
                    details={"visual": st.last_visual_info, "clock": st.last_clock_text, "context_summary": str((st.last_visual_info or {}).get("context_summary") or "")[:180], "screen_context": (st.last_visual_info or {}).get("screen_context")},
                )
            return

        if st.phase == "pos_jogo":
            if st.context != "pos_jogo":
                st.context = "pos_jogo"
                self._push(
                    "context",
                    "POS_JOGO",
                    t,
                    confidence=0.75,
                    details={"clock": st.last_clock_text, "context_summary": str((st.last_visual_info or {}).get("context_summary") or "")[:180], "screen_context": (st.last_visual_info or {}).get("screen_context")},
                )
            return

        banner_summary = self._clean_ocr_text(
            (st.last_visual_info or {}).get("context_summary", "") or
            (st.last_visual_info or {}).get("banner_summary", "")
        )
        speech_summary = self._clean_ocr_text(self._summarize_recent_speech())

        if banner_summary and len(banner_summary) > 6:
            context_summary = banner_summary
        elif speech_summary and len(speech_summary) > 6:
            context_summary = speech_summary
        else:
            context_summary = "Comentário da transmissão"

        if st.context != "comentario":
            st.context = "comentario"
            self._push(
                "context",
                "COMENTARIO_ANALISE",
                t,
                confidence=0.60,
                details={
                    "speech_summary": speech_summary,
                    "banner_summary": banner_summary,
                    "screen_context": (st.last_visual_info or {}).get("screen_context"),
                    "context_summary": context_summary,
                },
            )

    def _maybe_heartbeat(
        self,
        clock: Optional[str],
        score: Optional[str],
        banner: str,
        dominant_state: str,
        t: float,
    ) -> None:
        st = self._state

        if self.cfg.heartbeat_every_s <= 0:
            return
        if (t - st.last_heartbeat_t) < self.cfg.heartbeat_every_s:
            return

        st.last_heartbeat_t = t
        self._push(
            "status",
            "STATUS_HEARTBEAT",
            t,
            confidence=0.55,
            details={
                "phase": st.phase,
                "context": st.context,
                "clock": clock or st.last_clock_text or st.confirmed_clock,
                "score": score or st.last_score_text,
                "visual_state": dominant_state,
                "visual_info": st.last_visual_info,
                "banner_hint": (banner or "")[:80],
                "first_half_started": st.first_half_started,
                "interval_confirmed": st.interval_confirmed,
                "second_half_started": st.second_half_started,
                "match": st.current_match_display,
                "competition": st.current_competition,
                "team_a": st.current_team_a,
                "team_b": st.current_team_b,
                "minute": self._clock_to_minute(clock or st.last_clock_text or st.confirmed_clock),
                "seek_mode": bool(t <= st.seek_mode_until),
                "context_summary": str((st.last_visual_info or {}).get("context_summary") or (st.last_visual_info or {}).get("banner_summary") or "")[:180],
                "screen_context": (st.last_visual_info or {}).get("screen_context"),
            },
        )

    def _detect_black_freeze(self, frame_bgr: np.ndarray, t: float) -> None:
        st = self._state
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        mean = float(gray.mean())

        if mean <= self.cfg.black_mean_threshold:
            if st.black_since is None:
                st.black_since = t
            if (not st.black_on) and (t - st.black_since >= self.cfg.black_min_seconds):
                st.black_on = True
                self._push(
                    "interruption",
                    "BLACK_SCREEN_START",
                    st.black_since,
                    confidence=0.90,
                    details={"mean": mean},
                )
        else:
            if st.black_on:
                self._push("interruption", "BLACK_SCREEN_END", t, confidence=0.90, details={"mean": mean})
            st.black_on = False
            st.black_since = None

        last = st.last_gray
        if last is not None and last.shape != gray.shape:
            self._log(f"[DETECTOR][WARN] freeze reset por mudança de shape | old={getattr(last, 'shape', None)} | new={getattr(gray, 'shape', None)}")
            st.last_gray = gray
            st.freeze_since = None
            st.freeze_on = False
            return
        st.last_gray = gray
        if last is None:
            return

        diff_mean = _mean_absdiff(gray, last)
        if diff_mean <= self.cfg.freeze_diff_threshold:
            if st.freeze_since is None:
                st.freeze_since = t
            if (not st.freeze_on) and (t - st.freeze_since >= self.cfg.freeze_min_seconds):
                st.freeze_on = True
                self._push(
                    "interruption",
                    "FREEZE_START",
                    st.freeze_since,
                    confidence=0.85,
                    details={"diff_mean": diff_mean},
                )
        else:
            if st.freeze_on:
                self._push("interruption", "FREEZE_END", t, confidence=0.85, details={"diff_mean": diff_mean})
            st.freeze_on = False
    def _cloud_log(self, msg: str) -> None:
        st = self._state
        if st.cloud_logs is None: 
            st.cloud_logs = []
            # Log de boas vindas imediato
            from datetime import datetime
            ts = datetime.now().strftime("%H:%M:%S")
            st.cloud_logs.append(f"[{ts}] Sincronização Cloud Oracle Iniciada.")
        
        # Import centralizado na primeira condicional se necessário, 
        # mas aqui usamos o local apenas uma vez.
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{ts}] {msg}"
        st.cloud_logs.append(full_msg)
        if len(st.cloud_logs) > 100: st.cloud_logs.pop(0)
        self._log(f"[CLOUD] {msg}")

    def _ensure_cloud_expert(self) -> bool:
        if self._cloud_expert: return True
        if self._cloud_init_attempted: return False
        self._cloud_init_attempted = True
        try:
            from modules.cloud_expert import CloudExpert
            import sys
            from pathlib import Path
            if getattr(sys, "frozen", False):
                proj_root = Path(sys.executable).parent
            else:
                proj_root = Path(__file__).resolve().parents[1]
            cfg_path = os.path.join(proj_root, "config", "google_ai.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r") as f:
                    data = json.load(f)
                    key = data.get("gemini_api_key") or data.get("api_key")
                    if key:
                        model_id = data.get("model", "gemini-2.0-flash")
                        self._cloud_expert = CloudExpert(key, model_id=model_id)
                        self._cloud_log(f"Especialista Gemini ({model_id}) inicializado.")
                        return True
        except Exception as e:
            err_msg = f"Load Fail: {e}"
            self._log(f"[CLOUD] {err_msg}")
            self._state.last_cloud_error = err_msg
        return False

    def _maybe_collect_cloud_sample(self, frame_bgr: np.ndarray, t: float) -> None:
        if not self.cfg.cloud_enabled: return
        st = self._state
        
        # Otimização: No primeiro lote da sessão, coletamos frames mais rápido (cada 1s)
        # para que o usuário receba um diagnóstico da IA logo de cara.
        # Depois do primeiro lote ok, o intervalo de amostragem entre frames 
        # deve ser (cloud_interval_minutes * 60 / batch_size) para cobrir o período desejado.
        
        total_period_s = max(10, self.cfg.cloud_interval_minutes * 60)
        sample_gap = total_period_s / max(1, self.cfg.cloud_batch_size)
        
        current_interval = sample_gap
        if st.last_cloud_analysis_t == 0.0:
            current_interval = 1.0 # Coleta ultra-acelerada inicial (1 frame por segundo no 1º lote)

        if (t - st.last_cloud_sample_t) >= current_interval:
            st.last_cloud_sample_t = t
            # Guardamos uma versão leve para o lote
            small = cv2.resize(frame_bgr, (640, 360), interpolation=cv2.INTER_AREA)
            st.cloud_buffer.append(small)
            st._ia_status_msg = f"Coletando Frames ({len(st.cloud_buffer)}/{self.cfg.cloud_batch_size})"
            self._cloud_log(f"Lote Cloud: Frame {len(st.cloud_buffer)}/{self.cfg.cloud_batch_size} coletado.")
            if len(st.cloud_buffer) >= self.cfg.cloud_batch_size:
                self._trigger_cloud_analysis(t)
            
            # Limpeza de segurança (Evita o 5/4 e estouro se expert travar)
            if len(st.cloud_buffer) > (self.cfg.cloud_batch_size + 2):
                st.cloud_buffer = []

    def _trigger_cloud_analysis(self, t: float) -> None:
        st = self._state
        batch = list(st.cloud_buffer)
        st.cloud_buffer = [] # Limpa IMEDIATAMENTE antes de tentar, para evitar overflow
        st.last_cloud_analysis_t = t
        st.last_cloud_error = ""

        if not self._ensure_cloud_expert(): 
            # O st.last_cloud_error já foi preenchido por _ensure_cloud_expert
            return
        
        st.cloud_analysis_in_progress = True
        st._cloud_busy = True
        st._ia_status_msg = "Preparando Envio..."

        def bg_worker():
            t_start = time.perf_counter()
            try:
                st._ia_status_msg = "Enviando para o Gemini..."
                self._cloud_log(f"Analisando sequência de {len(batch)} frames no Gemini...")
                res = self._cloud_expert.analyze_batch(batch, f"Contexto local: fase={st.phase}, seeker={getattr(st, 'seek_mode_until', 0) > t}")
                st._ia_status_msg = "Processando Resposta..."
                st.last_cloud_result = res
                st.last_cloud_duration_s = round(time.perf_counter() - t_start, 2)
                st.last_cloud_error = ""
                self._apply_cloud_correction(res, t)
            except Exception as e:
                st.last_cloud_error = str(e)
                self._cloud_log(f"Erro na análise em nuvem: {e}")
            finally:
                st.cloud_analysis_in_progress = False
                st._cloud_busy = False
                if not st.last_cloud_error:
                    st._ia_status_msg = "Concluído com sucesso"
                else:
                    st._ia_status_msg = "Falha na análise"

        threading.Thread(target=bg_worker, daemon=True, name="cloud_analysis_bg").start()

    def _apply_cloud_correction(self, res: dict, t: float) -> None:
        st = self._state
        phase_map = {
            "pre_game": "pre_jogo",
            "first_half": "primeiro_tempo",
            "half_time": "intervalo",
            "second_half": "segundo_tempo",
            "post_game": "pos_jogo"
        }
        cloud_phase = phase_map.get(res.get("current_phase"))
        
        # 1. Correção de Fase (Word of God)
        if cloud_phase and cloud_phase != st.phase:
            self._cloud_log(f"!!! CORREÇÃO DE FASE !!! Local={st.phase} -> Cloud={cloud_phase}")
            self._cloud_log(f"Sumário Gemini: {res.get('summary')}")
            st.phase = cloud_phase
            
            # Sincronizar trilhos de tempo
            if cloud_phase in ("primeiro_tempo", "segundo_tempo"):
                st.first_half_started = True
            if cloud_phase == "segundo_tempo":
                st.second_half_started = True
                st.interval_confirmed = True

            self._push("phase", "CLOUD_ORACLE_CORRECTION", t, confidence=0.99, details=res)

        # 2. Extração de Banners e Contexto (para Relatório e GUI)
        cloud_banners = res.get("banners", {})
        summary_text = res.get("summary")
        st._last_cloud_raw_response = str(summary_text or "Insight recebido sem sumário textual.")
        
        # Mapeamos para o formato que a GUI e o ReportGenerator esperam
        if cloud_banners.get("active") or summary_text:
            headline = cloud_banners.get("headline") or summary_text
            subheadline = cloud_banners.get("subheadline")
            
            # Atualiza estado para a GUI
            st.last_banner_text = str(headline)
            st.last_banner_read_t = t
            
            if st.last_visual_info is None:
                st.last_visual_info = {}
            
            # Injetamos no visual_info para que o Dashboard da GUI reflita a IA
            st.last_visual_info["banner_headline"] = headline
            st.last_visual_info["banner_subheadline"] = subheadline
            st.last_visual_info["banner_text"] = headline
            
            # Emulamos o screen_context para o ReportGenerator
            if "screen_context" not in st.last_visual_info:
                st.last_visual_info["screen_context"] = {}
            
            st.last_visual_info["screen_context"]["bottom"] = {
                "headline": headline,
                "subheadline": subheadline,
                "active": True
            }
            st.last_visual_info["screen_context"]["context_summary"] = summary_text

            # 3. Registrar no Timeline (para o PDF do ReportGenerator)
            ctx_details = {
                "context_summary": summary_text,
                "banner_summary": headline,
                "score": res.get("current_score") or st.last_score_text,
                "clock": res.get("current_clock") or st.last_clock_text,
                "cloud_verified": True
            }
            self._push("context", "CLOUD_ORACLE_UPDATE", t, confidence=0.98, details=ctx_details)

        # 4. Atualização de Score/Clock (Opcional se local estiver vago)
        # Sincronizamos também as variáveis 'confirmed' para garantir que o 'Word of God' da IA prevaleça.
        cloud_score = res.get("current_score")
        if cloud_score and cloud_score != "null":
            if not st.confirmed_score or (cloud_score != st.confirmed_score and cloud_score != "0x0"):
                self._log(f"[CLOUD] Placar Cloud corrigido: {cloud_score} (Local: {st.confirmed_score})")
                st.confirmed_score = cloud_score
                st.last_cloud_correction_t = t 
                if st.recent_scores is not None:
                    st.recent_scores.append(cloud_score)

        cloud_clock = res.get("current_clock")
        if cloud_clock and cloud_clock != "null":
             if not st.confirmed_clock or (cloud_clock != st.confirmed_clock):
                st.confirmed_clock = cloud_clock
                if st.recent_clocks is not None:
                    st.recent_clocks.append(cloud_clock)
                self._cloud_log(f"Relógio Cloud sugere: {cloud_clock} (Local: {st.confirmed_clock})")
                st.last_cloud_correction_t = t 

        # 5. Calibração (Opcional - Log apenas)
        if res.get("hud_calibration", {}).get("visible"):
            self._cloud_log(f"Calibração HUD sugerida: {res['hud_calibration'].get('bbox_score_normalized')}")

        # 6. Processamento de Eventos de Banner (Retroativo)
        cloud_events = res.get("events_detected", [])
        if isinstance(cloud_events, list) and cloud_events:
            for evt in cloud_events:
                evt_upper = str(evt).upper()
                if evt_upper != "NONE":
                    self._cloud_log(f"Evento de banner confirmado no lote: {evt_upper}")
                    # Push de evento especial para garantir presença no relatório
                    self._push(
                        "banner",
                        f"CLOUD_DETECTED_{evt_upper}",
                        t,
                        confidence=0.98,
                        details={"origin": "Gemini Batch Analysis", "summary": res.get("summary")}
                    )


    def ingest_frame(
        self,
        frame_main: np.ndarray,
        t_seconds: float,
        frame_fast: Optional[np.ndarray] = None,
    ) -> None:
        pending_frame_main = frame_main
        pending_frame_fast = frame_fast
        pending_t_seconds = t_seconds

        while True:
            if not self._ingest_lock.acquire(blocking=False):
                with self._pending_ingest_lock:
                    self._pending_ingest = {
                        "frame_main": pending_frame_main,
                        "frame_fast": pending_frame_fast,
                        "t_seconds": float(pending_t_seconds),
                    }
                self._ingest_skip_overlap += 1
                if self._ingest_skip_overlap <= 5 or (self._ingest_skip_overlap % 10) == 0:
                    now = time.time()
                    self._log(
                        f"[DETECTOR][WARN] ingest skip overlap | t={float(pending_t_seconds):.2f} | "
                        f"last_start={now - self._last_ingest_start_wall:.3f}s | "
                        f"thread={threading.current_thread().name} | skipped={self._ingest_skip_overlap}"
                    )
                return

            ingest_t0 = time.perf_counter()
            try:
                t = float(pending_t_seconds)
                st = self._state
                perf: Dict[str, float] = {}

                # Pré-inicialização para evitar UnboundLocalError
                visual_res = None
                visual_info = {}
                visual_state = "nao_detectado"
                score = None
                game_clock = None
                countdown_clock = None
                banner = ""
                stable_clock = None
                score_for_state = None
                dominant_state = "nao_detectado"

                # Sincroniza flag de soberania para o detector visual (Eco-IA Mode)
                self.vision.cloud_sovereignty_mode = bool(self.cfg.cloud_enabled)

                if pending_frame_main is None or getattr(pending_frame_main, "size", 0) == 0:
                    self._log("[DETECTOR][WARN] ingest_frame frame_main vazio")
                    return

                # OTIMIZAÇÃO: Pula resize se o frame já estiver em 640x360 (ou muito próximo)
                fast_frame = pending_frame_fast if pending_frame_fast is not None and getattr(pending_frame_fast, "size", 0) > 0 else pending_frame_main
                try:
                    fh, fw = fast_frame.shape[:2]
                    if fw != 640 or fh != 360:
                        fast_frame = cv2.resize(fast_frame, (640, 360), interpolation=cv2.INTER_AREA)
                except Exception:
                    pass

                s = time.perf_counter()
                visual_res = self.vision.classify_frame_fast(fast_frame)
                perf["vision_ms"] = round((time.perf_counter() - s) * 1000.0, 2)

                visual_info = dict(getattr(visual_res, "details", {}) or {})
                visual_state = str(
                    getattr(visual_res, "label", None)
                    or visual_info.get("visual_state")
                    or "nao_detectado"
                ).strip().lower()

                frame_sig = f"{getattr(pending_frame_main, 'shape', None)}|{int(pending_frame_main[0,0,0]) if getattr(pending_frame_main,'size',0) else -1}|{int(pending_frame_main[-1,-1,0]) if getattr(pending_frame_main,'size',0) else -1}"
                duplicate_sig = frame_sig == self._last_ingest_sig
                self._last_ingest_sig = frame_sig
                self._last_ingest_start_wall = time.time()
                self._maybe_collect_cloud_sample(pending_frame_main, t)

                # Atualiza countdown para a API/Dashboard
                total_interval = self.cfg.cloud_interval_minutes * 60
                elapsed = t - st.last_cloud_analysis_t if st.last_cloud_analysis_t > 0 else 0
                st._cloud_countdown = max(0, int(total_interval - elapsed))

                countdown_clock: Optional[str] = (visual_info or {}).get("countdown_detected")
                game_clock: Optional[str] = (visual_info or {}).get("game_clock_detected")
                score: Optional[str] = (visual_info or {}).get("score_detected")
                banner: str = (
                    (visual_info or {}).get("hud_overlay", "")
                    or (visual_info or {}).get("banner_text", "")
                    or ((visual_info or {}).get("screen_context", {}) or {}).get("banner_text", "")
                    or ""
                )

                scoreboard_active = bool((visual_info or {}).get("scoreboard_active"))
                clock_active = bool((visual_info or {}).get("clock_active"))
                banner_active = bool((visual_info or {}).get("banner_active"))
                match_phase_text = str((visual_info or {}).get("match_phase_text") or "").strip().lower()

                # OTIMIZAÇÃO: Throttle nos logs de diagnóstico para não inundar o terminal/UI e travar a thread principal
                now_wall = time.time()
                should_log_diag = (now_wall - getattr(self, "_last_diag_log_t", 0.0)) >= 2.0 or self._ingest_skip_overlap > 0
                if should_log_diag:
                    self._last_diag_log_t = now_wall
                    self._log(
                        f"[DETECTOR][STEP] ingest start | t={t_seconds:.2f} | thread={threading.current_thread().name} | "
                        f"main_shape={getattr(pending_frame_main, 'shape', None)} | fast_shape={getattr(fast_frame, 'shape', None)} | "
                        f"duplicate_sig={duplicate_sig} | overlap_skips={self._ingest_skip_overlap}"
                    )
                    self._log(f"[DETECTOR][DIAG] visual summary | state={visual_state} | conf={float(visual_res.score or 0.0):.2f} | "
                              f"scoreboard={visual_info.get('scoreboard_active')} | clock={visual_info.get('clock_active')} | "
                              f"banner={visual_info.get('banner_active')}")
                    
                    perf_map = visual_info.get('perf') or {}
                    self._log("[DETECTOR][DIAG] classify perf | "
                              f"detect={perf_map.get('detect_frame_state_ms')}ms | gates={perf_map.get('visual_gates_ms')}ms | "
                              f"banner={perf_map.get('banner_async_cache_ms')}ms | total={visual_info.get('detector_total_ms')}ms")
                    
                    self._log(f"[DETECTOR][DIAG] post-fallback | score={score} | game_clock={game_clock} | countdown={countdown_clock} | banner_len={len((banner or '').strip())} | phase={match_phase_text}")
                    self._log("[DETECTOR][DIAG] roi gates | "
                              f"scoreboard={scoreboard_active} | clock={clock_active} | banner={banner_active} | "
                              f"score_roi={visual_info.get('score_roi')} | clock_roi={visual_info.get('clock_roi')}")
                match_phase_text = str((visual_info or {}).get("match_phase_text") or "").strip().lower()

                s = time.perf_counter()
                if self.cfg.enable_fallback_reads:
                    pass  # Fallbacks removed; relying on unified VisionDetectors cache

                if not game_clock and st.last_clock_text and (t - float(st.last_clock_seen_t or t)) <= 2.5:
                    game_clock = st.last_clock_text
                if not score and st.last_score_text:
                    score = st.last_score_text
                if not banner and st.last_banner_text:
                    banner = st.last_banner_text

                perf["fallback_ms"] = round((time.perf_counter() - s) * 1000.0, 2)

                s = time.perf_counter()
                score_for_state = score
                if self.cfg.require_clock_active_for_clock and not clock_active:
                    if visual_state in ("jogo", "intervalo") and not game_clock:
                        game_clock = None
                if self.cfg.require_scoreboard_for_live_score and not scoreboard_active:
                    if visual_state in ("jogo", "intervalo") and not score_for_state:
                        score_for_state = None

                stable_clock = self._accept_and_stabilize_clock(game_clock, visual_state, t)
                if stable_clock:
                    st.last_clock_text = stable_clock
                    st.last_clock_seen_t = t
                    self._maybe_detect_seek(stable_clock, t)
                    csec = _clock_to_seconds(stable_clock)
                    if csec is not None:
                        self._update_phase_by_clock(csec, t)

                if score_for_state and _is_reasonable_score(score_for_state):
                    st.last_score_text = score_for_state

                banner = self._clean_ocr_text(banner) or st.last_banner_text or ""
                if banner:
                    st.last_banner_text = banner

                perf["resolve_ms"] = round((time.perf_counter() - s) * 1000.0, 2)

                s = time.perf_counter()
                dominant_state = self._dominant_visual_state()
                dominant_state = self._apply_live_lock(
                    dominant_state=dominant_state,
                    countdown_clock=countdown_clock,
                    game_clock=stable_clock,
                    score=score_for_state,
                    t=t,
                )
                perf["dominant_ms"] = round((time.perf_counter() - s) * 1000.0, 2)

                s = time.perf_counter()
                self._maybe_push_visual_debug(dominant_state, visual_info or {}, t)
                self._update_replay_context(banner, t, visual_info or {})
                self._update_phase_from_visual(dominant_state, t)
                self._detect_match_events_stable(score_for_state, banner, t, visual_info or {})
                perf["events_ms"] = round((time.perf_counter() - s) * 1000.0, 2)

                s = time.perf_counter()
                self._update_context(dominant_state, stable_clock, score_for_state, banner, t)
                self._maybe_auto_collect_template(
                    pending_frame_main, dominant_state, visual_info or {}, stable_clock, score_for_state, banner, t
                )
                perf["context_ms"] = round((time.perf_counter() - s) * 1000.0, 2)

                s = time.perf_counter()
                self._maybe_heartbeat(stable_clock, score_for_state, banner, dominant_state, t)
                perf["heartbeat_ms"] = round((time.perf_counter() - s) * 1000.0, 2)

                perf["total_ingest_ms"] = round((time.perf_counter() - ingest_t0) * 1000.0, 2)
                st.last_perf = dict(perf)
                if isinstance(st.last_visual_info, dict):
                    st.last_visual_info["ingest_perf"] = dict(perf)
            finally:
                self._ingest_lock.release()

            next_pending = None
            with self._pending_ingest_lock:
                if self._pending_ingest is not None:
                    next_pending = self._pending_ingest
                    self._pending_ingest = None

            if not next_pending:
                return

            pending_frame_main = next_pending["frame_main"]
            pending_frame_fast = next_pending["frame_fast"]
            pending_t_seconds = next_pending["t_seconds"]

    def _push(
        self,
        typ: str,
        label: str,
        t_seconds: float,
        confidence: float = 0.7,
        details: Optional[Dict[str, Any]] = None,
        clock: Optional[str] = None,
        match_display: Optional[str] = None,
    ) -> None:
        st = self._state
        t = float(t_seconds)
        new_details = details or {}

        # Deduplicação inteligente: ignora apenas se TUDO for igual (tipo, label e conteúdo principal)
        # Se for um banner ou mensagem, comparamos o texto
        is_duplicate = (typ == st.last_push_type and label == st.last_push_label)
        
        if is_duplicate:
            old_content = str(getattr(st, "last_push_details", {}).get("banner") or getattr(st, "last_push_details", {}).get("mensagem") or "")
            new_content = str(new_details.get("banner") or new_details.get("mensagem") or "")
            
            # Se o conteúdo textual mudou, NÃO é duplicata (ex: nomes de jogadores diferentes na mesma label)
            if old_content != new_content:
                is_duplicate = False
            # Senão, respeitamos a janela de tempo
            elif (t - st.last_push_t) < self.cfg.dedupe_window_s:
                return

        st.last_push_type = typ
        st.last_push_label = label
        st.last_push_t = t
        st.last_push_details = new_details

        self._timeline.append(
            {
                "type": typ,
                "label": label,
                "t_seconds": round(t, 3),
                "clock": clock,
                "match_display": match_display,
                "confidence": round(float(confidence), 3),
                "phase": st.phase,
                "details": new_details,
            }
        )


# ============================================================
# FINAL CLEAN3 EVENT PATCH
# ============================================================
_orig_event_init = EventDetector.__init__

def _event_init_clean3(self, config: Optional[DetectorConfig] = None, log_hook: Optional[Any] = None) -> None:
    _orig_event_init(self, config=config, log_hook=log_hook)
    try:
        supported = set(self.vision.get_supported_roi_labels())
        for key in list(getattr(self.vision, 'roi_enabled', {}).keys()):
            self.vision.roi_enabled[key] = key in supported
    except Exception:
        pass

EventDetector.__init__ = _event_init_clean3


# ============================================================
# HUD QUORUM PATCH - evita promover jogo com clock isolado
# ============================================================

_prev_event_init_hud = EventDetector.__init__

def _event_init_hud_quorum(self, config: Optional[DetectorConfig] = None, log_hook: Optional[Any] = None) -> None:
    _prev_event_init_hud(self, config=config, log_hook=log_hook)
    st = self._state
    setattr(st, '_live_quorum_hits', 0)
    setattr(st, '_phase_quorum_hits', 0)
    setattr(st, '_last_quorum_key', '')
    setattr(st, '_last_phase_candidate', '')

EventDetector.__init__ = _event_init_hud_quorum


def _ensure_hud_quorum_state(self) -> None:
    st = self._state
    if not hasattr(st, '_live_quorum_hits'):
        setattr(st, '_live_quorum_hits', 0)
    if not hasattr(st, '_phase_quorum_hits'):
        setattr(st, '_phase_quorum_hits', 0)
    if not hasattr(st, '_last_quorum_key'):
        setattr(st, '_last_quorum_key', '')
    if not hasattr(st, '_last_phase_candidate'):
        setattr(st, '_last_phase_candidate', '')


def _live_hud_evidence(self, dominant_state: str = '') -> Dict[str, Any]:
    self._ensure_hud_quorum_state()
    st = self._state
    info = dict(st.last_visual_info or {})

    score = info.get('score_detected') or st.last_score_text
    clock = info.get('game_clock_detected') or st.last_clock_text
    countdown = info.get('countdown_detected')
    phase_text = str(info.get('match_phase_text') or info.get('phase_text') or '').strip().lower()
    scoreboard_active = bool(info.get('scoreboard_active'))

    has_score = bool(score and _is_reasonable_score(score))
    has_clock = bool(clock and _is_mmss_clock(clock))
    has_live_phase = phase_text in ('primeiro_tempo', 'segundo_tempo')
    has_interval = phase_text == 'intervalo'
    has_pre = phase_text == 'pre_jogo'

    pre_game_signal = self._score_pre_game_evidence(
        visual_info=info,
        countdown_clock=countdown if countdown and not _is_mmss_clock(countdown) else None,
        game_clock=clock if has_clock else None,
        score=score if has_score else None,
    )
    strong_pre = bool(has_pre or pre_game_signal.get('is_pre_game') or countdown or dominant_state == 'pre_jogo')

    points = 0
    if scoreboard_active:
        points += 1
    if has_score:
        points += 2
    if has_clock:
        points += 1
    if has_live_phase:
        points += 1
    if has_interval:
        points += 1

    live_confirmed = scoreboard_active and ((has_score and has_clock) or (has_score and has_live_phase))
    live_probable = scoreboard_active and (has_clock and has_live_phase)
    interval_confirmed = scoreboard_active and (has_interval and (has_score or has_clock))

    quorum_key = f"sb={int(scoreboard_active)}|s={int(has_score)}|c={int(has_clock)}|p={phase_text}"
    if quorum_key == getattr(st, '_last_quorum_key', ''):
        st._live_quorum_hits += 1
    else:
        st._live_quorum_hits = 1
        st._last_quorum_key = quorum_key

    phase_candidate = phase_text if phase_text in ('primeiro_tempo', 'segundo_tempo', 'intervalo', 'pre_jogo') else ''
    if phase_candidate and phase_candidate == getattr(st, '_last_phase_candidate', ''):
        st._phase_quorum_hits += 1
    else:
        st._phase_quorum_hits = 1 if phase_candidate else 0
        st._last_phase_candidate = phase_candidate

    return {
        'score': score,
        'clock': clock,
        'countdown': countdown,
        'phase_text': phase_text,
        'scoreboard_active': scoreboard_active,
        'has_score': has_score,
        'has_clock': has_clock,
        'has_live_phase': has_live_phase,
        'has_interval': has_interval,
        'has_pre': has_pre,
        'points': points,
        'live_confirmed': live_confirmed,
        'live_probable': live_probable,
        'interval_confirmed': interval_confirmed,
        'strong_pre': strong_pre,
        'pre_game_signal': pre_game_signal,
        'live_hits': int(getattr(st, '_live_quorum_hits', 0) or 0),
        'phase_hits': int(getattr(st, '_phase_quorum_hits', 0) or 0),
    }


EventDetector._ensure_hud_quorum_state = _ensure_hud_quorum_state
EventDetector._live_hud_evidence = _live_hud_evidence


def _update_phase_by_clock_guarded(self, clock_sec: int, t: float) -> None:
    st = self._state
    ev = self._live_hud_evidence(dominant_state=str(st.last_visual_state or ''))

    # Clock isolado não pode iniciar o jogo.
    if not st.first_half_started:
        allow_start = bool(
            ev.get('live_confirmed') or
            (ev.get('live_probable') and int(ev.get('live_hits', 0)) >= 2) or
            (ev.get('has_clock') and ev.get('has_score'))
        )
        if not allow_start:
            self._log(
                f"[DETECTOR][HUD_GUARD] bloqueado _update_phase_by_clock | "
                f"clock={ev.get('clock')} | score={ev.get('score')} | phase={ev.get('phase_text')} | "
                f"scoreboard_active={ev.get('scoreboard_active')} | live_hits={ev.get('live_hits')}"
            )
            return

    prev = st.last_game_clock_seconds

    if t <= st.seek_mode_until:
        if 0 <= clock_sec < 46 * 60:
            st.phase = 'jogo'
            st.first_half_started = True
            st.second_half_started = False
        else:
            st.phase = 'jogo'
            st.first_half_started = True
            st.second_half_started = True
            st.interval_confirmed = True
        st.last_game_clock_seconds = clock_sec
        return

    if not st.first_half_started:
        if 0 <= clock_sec < 45 * 60:
            st.first_half_started = True
            st.phase = 'primeiro_tempo'
            self._push(
                'phase',
                'PRIMEIRO_TEMPO_START',
                t,
                confidence=0.95,
                details={'clock_seconds': clock_sec, 'source': 'clock_guarded', 'hud_evidence': ev},
            )
            st.last_game_clock_seconds = clock_sec
            return

    if st.first_half_started and not st.second_half_started:
        if prev is not None:
            if prev >= 35 * 60 and clock_sec <= 10 * 60:
                st.interval_confirmed = True
                st.second_half_started = True
                st.phase = 'segundo_tempo'
                self._push(
                    'phase',
                    'SEGUNDO_TEMPO_START',
                    t,
                    confidence=0.95,
                    details={'clock_seconds': clock_sec, 'source': 'clock_reset_guarded', 'hud_evidence': ev},
                )
                st.last_game_clock_seconds = clock_sec
                return

        if clock_sec >= 46 * 60 and not st.second_half_started:
            st.interval_confirmed = True
            st.second_half_started = True
            st.phase = 'segundo_tempo'
            self._push(
                'phase',
                'SEGUNDO_TEMPO_START',
                t,
                confidence=0.90,
                details={'clock_seconds': clock_sec, 'source': 'clock_continuous_guarded', 'hud_evidence': ev},
            )
            st.last_game_clock_seconds = clock_sec
            return

    if st.second_half_started and clock_sec >= 85 * 60:
        if st.phase != 'pos_jogo':
            st.phase = 'pos_jogo'
            self._push(
                'phase',
                'POS_JOGO_START',
                t,
                confidence=0.85,
                details={'clock_seconds': clock_sec, 'source': 'clock_guarded', 'hud_evidence': ev},
            )

    st.last_game_clock_seconds = clock_sec


EventDetector._update_phase_by_clock = _update_phase_by_clock_guarded


def _update_phase_from_visual_guarded(self, dominant_state: str, t: float) -> None:
    st = self._state
    ev = self._live_hud_evidence(dominant_state=dominant_state)
    info = st.last_visual_info or {}
    match_phase_text = str((info.get('match_phase_text') or '')).strip().lower()
    pre_game_signal = ev.get('pre_game_signal') or {}

    # Pré-jogo vence clock isolado / fase isolada enquanto o jogo ainda não começou.
    if not st.first_half_started and ev.get('strong_pre') and not ev.get('live_confirmed'):
        st.no_overlay_since = None
        if st.phase != 'pre_jogo':
            self._push(
                'phase',
                'PRE_JOGO_START',
                t,
                confidence=0.89,
                details={
                    'source': 'hud_guard_pre',
                    'clock': ev.get('clock'),
                    'score': ev.get('score'),
                    'phase_text': ev.get('phase_text'),
                    'pre_game_reasons': pre_game_signal.get('reasons', []),
                    'pre_game_score': pre_game_signal.get('score'),
                },
            )
        st.phase = 'pre_jogo'
        return

    if match_phase_text == 'intervalo' and (ev.get('interval_confirmed') or int(ev.get('phase_hits', 0)) >= 2):
        st.no_overlay_since = None
        if st.first_half_started and not st.second_half_started:
            if not st.interval_confirmed:
                st.interval_confirmed = True
                st.phase = 'intervalo'
                self._push(
                    'phase',
                    'INTERVALO_START',
                    t,
                    confidence=0.90,
                    details={'clock': ev.get('clock'), 'source': 'visual_match_phase_guarded', 'hud_evidence': ev},
                )
            else:
                st.phase = 'intervalo'
        return

    if match_phase_text == 'primeiro_tempo':
        st.no_overlay_since = None
        if ev.get('live_confirmed') or (ev.get('live_probable') and int(ev.get('phase_hits', 0)) >= 2):
            if not st.first_half_started:
                st.first_half_started = True
                st.phase = 'jogo'
                self._push(
                    'phase',
                    'PRIMEIRO_TEMPO_START',
                    t,
                    confidence=0.93,
                    details={'clock': ev.get('clock'), 'source': 'visual_match_phase_guarded', 'hud_evidence': ev},
                )
            else:
                st.phase = 'jogo'
        else:
            self._log(
                f"[DETECTOR][HUD_GUARD] ignorando primeiro_tempo sem quorum | "
                f"clock={ev.get('clock')} | score={ev.get('score')} | live_hits={ev.get('live_hits')} | phase_hits={ev.get('phase_hits')}"
            )
        return

    if match_phase_text == 'segundo_tempo':
        st.no_overlay_since = None
        if ev.get('live_confirmed') or (ev.get('live_probable') and int(ev.get('phase_hits', 0)) >= 2):
            if not st.first_half_started:
                st.first_half_started = True
            if not st.interval_confirmed:
                st.interval_confirmed = True
            if not st.second_half_started:
                st.second_half_started = True
                st.phase = 'jogo'
                self._push(
                    'phase',
                    'SEGUNDO_TEMPO_START',
                    t,
                    confidence=0.93,
                    details={'clock': ev.get('clock'), 'source': 'visual_match_phase_guarded', 'hud_evidence': ev},
                )
            else:
                st.phase = 'jogo'
        else:
            self._log(
                f"[DETECTOR][HUD_GUARD] ignorando segundo_tempo sem quorum | "
                f"clock={ev.get('clock')} | score={ev.get('score')} | live_hits={ev.get('live_hits')} | phase_hits={ev.get('phase_hits')}"
            )
        return

    if dominant_state == 'jogo':
        st.no_overlay_since = None
        if ev.get('live_confirmed') or (ev.get('live_probable') and int(ev.get('live_hits', 0)) >= 2):
            if not st.first_half_started:
                st.phase = 'jogo'
                st.first_half_started = True
                self._push(
                    'phase',
                    'PRIMEIRO_TEMPO_START',
                    t,
                    confidence=0.92,
                    details={'clock': ev.get('clock'), 'source': 'visual_guarded', 'hud_evidence': ev},
                )
                return
            if st.interval_confirmed and not st.second_half_started:
                st.phase = 'jogo'
                st.second_half_started = True
                self._push(
                    'phase',
                    'SEGUNDO_TEMPO_START',
                    t,
                    confidence=0.92,
                    details={'clock': ev.get('clock'), 'source': 'visual_guarded', 'hud_evidence': ev},
                )
                return
            st.phase = 'jogo'
        else:
            self._log(
                f"[DETECTOR][HUD_GUARD] dominant_state=jogo sem quorum | "
                f"clock={ev.get('clock')} | score={ev.get('score')} | phase={ev.get('phase_text')}"
            )
        return

    if dominant_state == 'intervalo':
        st.no_overlay_since = None
        if st.first_half_started and not st.second_half_started and not st.interval_confirmed and (ev.get('interval_confirmed') or int(ev.get('phase_hits', 0)) >= 2):
            st.interval_confirmed = True
            st.phase = 'intervalo'
            self._push(
                'phase',
                'INTERVALO_START',
                t,
                confidence=0.82,
                details={'clock': ev.get('clock'), 'source': 'visual_intervalo_guarded', 'hud_evidence': ev},
            )
        return

    if dominant_state == 'pre_jogo' or (pre_game_signal.get('is_pre_game') and not st.first_half_started):
        st.no_overlay_since = None
        if not st.first_half_started and st.phase != 'pre_jogo':
            st.phase = 'pre_jogo'
            self._push(
                'phase',
                'PRE_JOGO_START',
                t,
                confidence=0.90 if dominant_state == 'pre_jogo' else 0.84,
                details={
                    'clock': ev.get('clock'),
                    'source': 'visual_pre_guarded' if dominant_state == 'pre_jogo' else 'pre_game_score_guarded',
                    'pre_game_reasons': pre_game_signal.get('reasons', []),
                    'pre_game_score': pre_game_signal.get('score'),
                },
            )
        return

    if st.no_overlay_since is None:
        st.no_overlay_since = t

    if (t - st.no_overlay_since) < self.cfg.no_overlay_hold_seconds:
        return

    if st.phase == 'jogo':
        last_sec = st.last_game_clock_seconds
        if last_sec is None:
            return

        last_min = int(last_sec // 60)

        if st.second_half_started and last_min >= self.cfg.pos_jogo_clock_min_minutes:
            st.phase = 'pos_jogo'
            self._push(
                'phase',
                'POS_JOGO_START',
                st.no_overlay_since,
                confidence=0.82,
                details={
                    'source': 'historico',
                    'last_clock_seconds': last_sec,
                    'clock': st.last_clock_text,
                },
            )
            return


EventDetector._update_phase_from_visual = _update_phase_from_visual_guarded

# ============================================================
# BLINDAGEM FINAL HUD / TIMER REGRESSIVO / PARTIAL HUD GUARD
# ============================================================

def _live_hud_evidence_blindado(self, dominant_state: str = '') -> Dict[str, Any]:
    self._ensure_hud_quorum_state()
    st = self._state
    info = dict(st.last_visual_info or {})

    score = info.get('score_detected') or st.last_score_text
    clock = info.get('game_clock_detected') or st.last_clock_text
    countdown = info.get('countdown_detected')
    phase_text = str(info.get('match_phase_text') or info.get('phase_text') or '').strip().lower()
    scoreboard_active = bool(info.get('scoreboard_active'))

    has_score = bool(score and _is_reasonable_score(score))
    has_clock_raw = bool(clock and _is_mmss_clock(clock))
    clock_sec = _clock_to_seconds(clock) if has_clock_raw else None
    has_live_phase_raw = phase_text in ('primeiro_tempo', 'segundo_tempo')
    has_interval = phase_text == 'intervalo'
    has_pre = phase_text == 'pre_jogo'

    suspicious_partial = False
    if has_clock_raw and not has_score:
        if countdown:
            suspicious_partial = True
        elif clock_sec is not None and clock_sec <= 90:
            suspicious_partial = True
        elif dominant_state == 'pre_jogo' and not has_live_phase_raw:
            suspicious_partial = True

    has_clock = has_clock_raw and not suspicious_partial
    has_live_phase = has_live_phase_raw and not suspicious_partial

    pre_game_signal = self._score_pre_game_evidence(
        visual_info=info,
        countdown_clock=countdown if countdown and not _is_mmss_clock(countdown) else None,
        game_clock=clock if has_clock else None,
        score=score if has_score else None,
    )
    strong_pre = bool(has_pre or pre_game_signal.get('is_pre_game') or countdown or dominant_state == 'pre_jogo' or suspicious_partial)

    points = 0
    if scoreboard_active:
        points += 1
    if has_score:
        points += 2
    if has_clock:
        points += 1
    if has_live_phase:
        points += 1
    if has_interval:
        points += 1

    live_confirmed = scoreboard_active and ((has_score and has_clock) or (has_score and has_live_phase))
    live_probable = scoreboard_active and (has_clock and has_live_phase and not suspicious_partial)
    interval_confirmed = scoreboard_active and (has_interval and (has_score or has_clock))

    quorum_key = f"sb={int(scoreboard_active)}|s={int(has_score)}|c={int(has_clock)}|p={phase_text}|sp={int(suspicious_partial)}"
    if quorum_key == getattr(st, '_last_quorum_key', ''):
        st._live_quorum_hits += 1
    else:
        st._live_quorum_hits = 1
        st._last_quorum_key = quorum_key

    phase_candidate = phase_text if phase_text in ('primeiro_tempo', 'segundo_tempo', 'intervalo', 'pre_jogo') and not suspicious_partial else ''
    if phase_candidate and phase_candidate == getattr(st, '_last_phase_candidate', ''):
        st._phase_quorum_hits += 1
    else:
        st._phase_quorum_hits = 1 if phase_candidate else 0
        st._last_phase_candidate = phase_candidate

    return {
        'score': score,
        'clock': clock if has_clock else None,
        'countdown': countdown,
        'phase_text': phase_text if not suspicious_partial else '',
        'scoreboard_active': scoreboard_active,
        'has_score': has_score,
        'has_clock': has_clock,
        'has_live_phase': has_live_phase,
        'has_interval': has_interval,
        'has_pre': has_pre,
        'points': points,
        'live_confirmed': live_confirmed,
        'live_probable': live_probable,
        'interval_confirmed': interval_confirmed,
        'strong_pre': strong_pre,
        'pre_game_signal': pre_game_signal,
        'live_hits': int(getattr(st, '_live_quorum_hits', 0) or 0),
        'phase_hits': int(getattr(st, '_phase_quorum_hits', 0) or 0),
        'suspicious_partial': suspicious_partial,
        'clock_seconds': clock_sec,
    }


EventDetector._live_hud_evidence = _live_hud_evidence_blindado


# ============================================================
# FIELD CONTEXT GUARD - exige contexto visual mínimo de campo para promover jogo
# ============================================================
def _live_hud_evidence_field_guard(self, dominant_state: str = '') -> Dict[str, Any]:
    self._ensure_hud_quorum_state()
    st = self._state
    info = dict(st.last_visual_info or {})

    score = info.get('score_detected') or st.last_score_text
    clock = info.get('game_clock_detected') or st.last_clock_text
    countdown = info.get('countdown_detected')
    phase_text = str(info.get('match_phase_text') or info.get('phase_text') or '').strip().lower()
    scoreboard_active = bool(info.get('scoreboard_active'))
    field_context_ok = bool(info.get('field_context_ok') or ((info.get('field_context') or {}).get('field_context_ok')))

    has_score = bool(score and _is_reasonable_score(score))
    has_clock_raw = bool(clock and _is_mmss_clock(clock))
    clock_sec = _clock_to_seconds(clock) if has_clock_raw else None
    has_live_phase_raw = phase_text in ('primeiro_tempo', 'segundo_tempo')
    has_interval = phase_text == 'intervalo'
    has_pre = phase_text == 'pre_jogo'

    suspicious_partial = False
    if has_clock_raw and not has_score:
        if countdown:
            suspicious_partial = True
        elif clock_sec is not None and clock_sec <= 90:
            suspicious_partial = True
        elif dominant_state == 'pre_jogo' and not has_live_phase_raw:
            suspicious_partial = True

    # novo veto auxiliar: HUD de jogo em frame sem contexto de campo vira suspeito
    if not field_context_ok and (has_score or has_clock_raw or has_live_phase_raw):
        suspicious_partial = True

    has_clock = has_clock_raw and not suspicious_partial
    has_live_phase = has_live_phase_raw and not suspicious_partial

    pre_game_signal = self._score_pre_game_evidence(
        visual_info=info,
        countdown_clock=countdown if countdown and not _is_mmss_clock(countdown) else None,
        game_clock=clock if has_clock else None,
        score=score if has_score else None,
    )
    strong_pre = bool(has_pre or pre_game_signal.get('is_pre_game') or countdown or dominant_state == 'pre_jogo' or suspicious_partial)

    points = 0
    if scoreboard_active:
        points += 1
    if has_score:
        points += 2
    if has_clock:
        points += 1
    if has_live_phase:
        points += 1
    if has_interval:
        points += 1
    if field_context_ok:
        points += 1

    hud_is_very_strong = scoreboard_active and has_score and has_clock
    live_confirmed = (field_context_ok and scoreboard_active and ((has_score and has_clock) or (has_score and has_live_phase))) or hud_is_very_strong
    live_probable = (field_context_ok and scoreboard_active and (has_clock and has_live_phase and not suspicious_partial))
    interval_confirmed = (field_context_ok and scoreboard_active and (has_interval and (has_score or has_clock))) or (scoreboard_active and has_interval and has_score)

    quorum_key = f"sb={int(scoreboard_active)}|field={int(field_context_ok)}|s={int(has_score)}|c={int(has_clock)}|p={phase_text}|sp={int(suspicious_partial)}"
    if quorum_key == getattr(st, '_last_quorum_key', ''):
        st._live_quorum_hits += 1
    else:
        st._live_quorum_hits = 1
        st._last_quorum_key = quorum_key

    phase_candidate = phase_text if phase_text in ('primeiro_tempo', 'segundo_tempo', 'intervalo', 'pre_jogo') and not suspicious_partial else ''
    if phase_candidate and phase_candidate == getattr(st, '_last_phase_candidate', ''):
        st._phase_quorum_hits += 1
    else:
        st._phase_quorum_hits = 1 if phase_candidate else 0
        st._last_phase_candidate = phase_candidate

    return {
        'score': score,
        'clock': clock if has_clock else None,
        'countdown': countdown,
        'phase_text': phase_text if not suspicious_partial else '',
        'scoreboard_active': scoreboard_active,
        'field_context_ok': field_context_ok,
        'has_score': has_score,
        'has_clock': has_clock,
        'has_live_phase': has_live_phase,
        'has_interval': has_interval,
        'has_pre': has_pre,
        'points': points,
        'live_confirmed': live_confirmed,
        'live_probable': live_probable,
        'interval_confirmed': interval_confirmed,
        'strong_pre': strong_pre,
        'pre_game_signal': pre_game_signal,
        'live_hits': int(getattr(st, '_live_quorum_hits', 0) or 0),
        'phase_hits': int(getattr(st, '_phase_quorum_hits', 0) or 0),
        'suspicious_partial': suspicious_partial,
        'clock_seconds': clock_sec,
    }

EventDetector._live_hud_evidence = _live_hud_evidence_field_guard


# ============================================================
# FINAL START SESSION + HARD VETO PATCH
# ============================================================
_old_event_start_session_final = EventDetector.start_session

def _event_start_session_with_pre_jogo(self, event_id: str) -> None:
    _old_event_start_session_final(self, event_id)
    try:
        self._state.phase = 'pre_jogo'
        self._state.context = 'pre_jogo'
        self._push('phase', 'PRE_JOGO_START', 0.0, confidence=0.99, details={
            'phase': 'pre_jogo',
            'source': 'session_start',
            'summary': 'Sessão iniciada em pré-jogo',
        })
        self._push('context', 'PRE_JOGO_COUNTDOWN', 0.0, confidence=0.80, details={
            'context_summary': 'Monitoramento iniciado. Estado inicial assumido como pré-jogo até confirmação forte de jogo.',
            'phase': 'pre_jogo',
            'source': 'session_start',
        })
    except Exception:
        pass

EventDetector.start_session = _event_start_session_with_pre_jogo

_old_live_hud_evidence_final = EventDetector._live_hud_evidence

def _live_hud_evidence_final_guard(self, dominant_state: str = '') -> Dict[str, Any]:
    ev = dict(_old_live_hud_evidence_final(self, dominant_state=dominant_state) or {})
    try:
        info = dict((self._state.last_visual_info or {}))
        hud_field_veto = bool(info.get('hud_field_veto'))
        field_context_ok = bool(info.get('field_context_ok') or ((info.get('field_context') or {}).get('field_context_ok')))
        
        has_score = bool(ev.get('has_score'))
        has_clock = bool(ev.get('has_clock'))
        hud_is_very_strong = bool(has_score and has_clock)
        
        if not hud_is_very_strong and (hud_field_veto or not field_context_ok):
            ev['field_context_ok'] = False
            ev['suspicious_partial'] = True
            ev['live_confirmed'] = False
            ev['live_probable'] = False
            ev['interval_confirmed'] = False
            ev['has_clock'] = False
            ev['has_live_phase'] = False
            ev['clock'] = None
            ev['phase_text'] = 'pre_jogo'
            ev['strong_pre'] = True
        return ev
    except Exception:
        return ev

EventDetector._live_hud_evidence = _live_hud_evidence_final_guard


# ============================================================
# FINAL SCENE GUARD PATCH - revisado
# - sessão nasce em pre_jogo
# - veto de estúdio/telão ou ausência de cena real de jogo derruba promoção
# ============================================================
_old_event_start_session_scene_guard = EventDetector.start_session

def _event_start_session_scene_guard(self, event_id: str) -> None:
    _old_event_start_session_scene_guard(self, event_id)
    try:
        self._state.phase = 'pre_jogo'
        self._state.context = 'pre_jogo'
    except Exception:
        pass

EventDetector.start_session = _event_start_session_scene_guard

_old_live_hud_evidence_scene_guard = EventDetector._live_hud_evidence

def _live_hud_evidence_scene_guard(self, dominant_state: str = '') -> Dict[str, Any]:
    ev = dict(_old_live_hud_evidence_scene_guard(self, dominant_state=dominant_state) or {})
    try:
        info = dict(self._state.last_visual_info or {})
        scene = dict(info.get('field_context') or {})
        field_context_ok = bool(info.get('field_context_ok') or scene.get('field_context_ok'))
        studio_scene = bool(info.get('studio_scene') or scene.get('studio_scene'))
        real_game_scene = bool(info.get('real_game_scene') or scene.get('real_game_scene'))
        hud_field_veto = bool(info.get('hud_field_veto'))

        has_score = bool(ev.get('has_score'))
        has_clock = bool(ev.get('has_clock'))
        hud_is_very_strong = bool(has_score and has_clock)

        if not hud_is_very_strong and (hud_field_veto or studio_scene or (not field_context_ok) or (not real_game_scene)):
            ev['field_context_ok'] = False
            ev['studio_scene'] = studio_scene
            ev['real_game_scene'] = real_game_scene
            ev['suspicious_partial'] = True
            ev['live_confirmed'] = False
            ev['live_probable'] = False
            ev['interval_confirmed'] = False
            ev['has_clock'] = False
            ev['has_live_phase'] = False
            ev['clock'] = None
            ev['phase_text'] = 'pre_jogo'
            ev['strong_pre'] = True
        return ev
    except Exception:
        return ev

EventDetector._live_hud_evidence = _live_hud_evidence_scene_guard
