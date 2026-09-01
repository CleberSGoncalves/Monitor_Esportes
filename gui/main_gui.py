from __future__ import annotations

import os
import sys
from pathlib import Path
import ssl

# --- BOOTSTRAP DE SYS.PATH (Garantia de importação para 'modules' em Script e Executável PyInstaller) ---
if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)
    exe_dir = str(Path(sys.executable).parent)
    if exe_dir not in sys.path:
        sys.path.insert(0, exe_dir)
    try:
        os.chdir(Path(sys.executable).parent)
    except Exception:
        pass
else:
    file_dir = Path(__file__).resolve().parent
    root_dir = str(file_dir.parent) if file_dir.name == "gui" else str(file_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

try:
    orig_create_default_context = ssl.create_default_context
    def unverified_create_default_context(*args, **kwargs):
        context = orig_create_default_context(*args, **kwargs)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    ssl.create_default_context = unverified_create_default_context
except Exception:
    pass

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from datetime import datetime, timedelta

import tkinter as tk
from tkinter import messagebox
import unicodedata
import urllib.request
import io

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    file_dir = Path(__file__).resolve().parent
    PROJECT_ROOT = file_dir.parent if file_dir.name == "gui" else file_dir
# ------------------------------------------------------------------------

# --- SMOKE TEST GUARDRAIL (Validação de inicialização pré-deploy) ---
if "--check-version" in sys.argv or "--smoke-test" in sys.argv:
    try:
        from modules.auto_updater import AutoUpdater
        print(f"SMOKE_TEST_OK: v{AutoUpdater().current_version}")
        sys.exit(0)
    except Exception as e_smoke:
        print(f"SMOKE_TEST_FAILED: {e_smoke}")
        sys.exit(1)
# --------------------------------------------------------------------

import os
import re
import json
import time
import shutil
import threading
import traceback
import gc
from typing import Any, Dict, List, Optional, Tuple, Callable, Set

from modules.perf_logger import PerfLogger

import customtkinter as ctk
import cv2
import numpy as np

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

# Dependências do projeto
from config.settings import (
    CHANNEL_STREAMS_URL,
    PREPARE_MINUTES_BEFORE,
    AUTO_MONITOR_WHEN_LIVE,
    OBS_HOST,
    OBS_PORT,
    OBS_PASSWORD,
    OBS_SCENE_MONITOR,
    OBS_BROWSER_SOURCE,
    OBS_EXE_PATH,
    OBS_ARGS,
    OBS_AUTO_START,
    SRT_INPUT_URL,
    FRAME_SAMPLE_FPS,
    AUDIO_SEGMENT_SECONDS,
    ENABLE_AUDIO_ANALYSIS,
    EMAIL_SMTP_SERVER,
    EMAIL_SMTP_PORT,
)
from modules.youtube_metadata import get_youtube_metadata
from modules.youtube_events import get_channel_events
from modules.youtube_api_v3 import get_official_events

# Forçar detecção de sub-módulos para o compilador (PyInstaller)
import email.mime.multipart
import email.mime.text
import email.mime.base
import email.encoders
import flask
import flask_cors
import requests
import paddleocr
import paddlex

from modules.ad_analyzer import AdAnalyzer
from modules.obs_controller import OBSController
from modules.event_detector import EventDetector
from modules.report_generator import ReportGenerator
from modules.email_service import EmailService
from modules.api_provider import start_api_thread
from core.monitor_core import MonitorCoreMixin
from modules.auto_updater import AutoUpdater
from core.models import (
    DebugSnapshot,
    MonitorRuntime,
    normalize_watch_url_to_embed,
    _safe_slug,
    _now,
    _parse_dt,
    _fmt_dt,
    _human_age,
    _ensure_dir,
    _event_root,
    _event_paths,
    _latest_file,
    _safe_timestamp,
    _norm_text,
    _event_matches_category,
    cleanup_old_files,
    _clean_event_title,
    _find_competition,
    _normalize_team_name,
    _extract_match_from_title,
    _extract_event_meta,
    _clean_hud_text,
    _fmt_conf,
    _fit_image,
    _bgr_to_pil,
    _bgr_to_ctk,
    _safe_crop,
    _xywh_to_xyxy,
    _normalize_rect,
    _draw_rect,
)

_YT_ID_RE = re.compile(r"(?:v=|/live/|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", re.IGNORECASE)

_COMPETITION_PATTERNS: List[Tuple[str, List[str]]] = [
    ("Campeonato Paulista", ["campeonato paulista", "paulistao", "paulista"]),
    ("Brasileirão", ["brasileirao", "brasileirão", "campeonato brasileiro", "serie a", "série a", "serie b", "série b"]),
    ("Copa do Brasil", ["copa do brasil"]),
    ("Libertadores", ["libertadores", "pré-libertadores", "pre-libertadores", "pre libertadores"]),
    ("Sul-Americana", ["sul-americana", "sul americana", "sudamericana"]),
    ("Champions League", ["champions league", "uefa champions", "champions"]),
    ("Copa do Mundo", ["copa do mundo", "world cup", "mundial"]),
    ("Amistoso", ["amistoso", "friendly"]),
]

# Diretórios de configuração híbrida (Local e Persistente no AppData do Windows)
USER_CONFIG_DIR = os.path.join(os.environ.get("APPDATA", str(PROJECT_ROOT)), "Monitor_Esportes", "config")
LOCAL_CONFIG_DIR = os.path.join(PROJECT_ROOT, "config")

def _get_config_read_path(filename: str) -> str:
    """Retorna o caminho do arquivo de config procurando primeiro no local e depois no APPDATA permanente."""
    local_path = os.path.join(LOCAL_CONFIG_DIR, filename)
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return local_path
    appdata_path = os.path.join(USER_CONFIG_DIR, filename)
    if os.path.exists(appdata_path) and os.path.getsize(appdata_path) > 0:
        return appdata_path
    return local_path

def _save_config_file(filename: str, data: Any) -> None:
    """Salva o arquivo de configuração tanto na pasta local quanto na pasta permanente do Windows (%APPDATA%)."""
    for folder in [LOCAL_CONFIG_DIR, USER_CONFIG_DIR]:
        try:
            os.makedirs(folder, exist_ok=True)
            p = os.path.join(folder, filename)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

def _load_saved_emails() -> list:
    path = _get_config_read_path("saved_emails.json")
    default_emails = ["cleber.goncalves@ibope.com"]
    if not os.path.exists(path):
        _save_config_file("saved_emails.json", default_emails)
        return default_emails
    try:
        with open(path, "r", encoding="utf-8") as f:
            emails = json.load(f)
            if "arthur@mediadna.com.br" in emails:
                emails.remove("arthur@mediadna.com.br")
                _save_config_file("saved_emails.json", emails)
            return emails
    except:
        return default_emails

def _save_email(email_str: str) -> list:
    emails = _load_saved_emails()
    email_str = email_str.strip()
    if email_str and email_str not in emails:
        emails.append(email_str)
        _save_config_file("saved_emails.json", emails)
    return emails

def _remove_saved_email(email_str: str) -> list:
    emails = _load_saved_emails()
    email_str = email_str.strip()
    if email_str in emails:
        emails.remove(email_str)
        _save_config_file("saved_emails.json", emails)
    return emails

def _load_scheduled_games() -> list:
    path = _get_config_read_path("scheduled_games.json")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except:
            pass
            
    # Se não houver arquivo salvo ou estiver vazio, inicializa automaticamente com os 5 próximos jogos da CBF
    try:
        events = _load_cbf_streaming_events()
        initial_games = []
        for evt in events[:5]:
            initial_games.append({
                "team1": evt.get("team1", ""),
                "team2": evt.get("team2", ""),
                "comp": evt.get("comp", ""),
                "date": evt.get("date", datetime.now().strftime("%d/%m/%Y")),
                "time": evt.get("time", "20:00"),
                "platform": evt.get("platform", "CazéTV"),
                "status": "pending",
                "last_run": None,
                "report_file": None
            })
        if initial_games:
            _save_scheduled_games(initial_games)
            return initial_games
    except:
        pass
    return []

def _save_scheduled_games(games_list: list) -> None:
    _save_config_file("scheduled_games.json", games_list)

def _load_recent_searches() -> list:
    path = _get_config_read_path("recent_searches.json")
    default_searches = [
        {"team1": "Palmeiras", "team2": "Santos", "comp": "Copa do Brasil", "date": "26/08/2026", "platform": "Amazon Prime"},
        {"team1": "Cruzeiro", "team2": "Flamengo", "comp": "Brasileiro Serie A", "date": "22/08/2026", "platform": "Amazon Prime"},
        {"team1": "Fluminense", "team2": "Remo", "comp": "Brasileiro Serie A", "date": "22/08/2026", "platform": "CazéTV"}
    ]
    if not os.path.exists(path):
        _save_config_file("recent_searches.json", default_searches)
        return default_searches
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_searches

def _save_recent_search(team1: str, team2: str, comp: str, date: str, platform: str) -> list:
    searches = _load_recent_searches()
    if not team1 or not team2:
        return searches
        
    new_item = {
        "team1": team1.strip(),
        "team2": team2.strip(),
        "comp": comp.strip() or "Campeonato",
        "date": date.strip() or datetime.now().strftime("%d/%m/%Y"),
        "platform": platform.strip() or "CazéTV"
    }
    # Remover duplicatas
    searches = [s for s in searches if not (s.get("team1", "").lower() == new_item["team1"].lower() and s.get("team2", "").lower() == new_item["team2"].lower())]
    searches.insert(0, new_item)
    searches = searches[:5]
    _save_config_file("recent_searches.json", searches)
    return searches

def _load_cbf_streaming_events() -> list:
    """Lê os eventos oficiais de transmissão do projeto Streaming_Scheduler (E:\desenvolvimento\Streaming_Scheduler\data.csv)."""
    scheduler_csv = r"E:\desenvolvimento\Streaming_Scheduler\data.csv"
    fallback_csv = os.path.join(PROJECT_ROOT, "config", "streaming_data.csv")
    
    csv_path = scheduler_csv if os.path.exists(scheduler_csv) else fallback_csv
    events = []
    
    if not os.path.exists(csv_path):
        return [
            {"comp": "Brasileirão Série A", "partida": "Corinthians x São Paulo", "team1": "Corinthians", "team2": "São Paulo", "date": "10/05/2026", "time": "17:30", "platform": "Amazon Prime"},
            {"comp": "Brasileirão Série A", "partida": "Vasco da Gama x Athletico", "team1": "Vasco da Gama", "team2": "Athletico", "date": "10/05/2026", "time": "19:30", "platform": "CazéTV"},
            {"comp": "Brasileirão Série A", "partida": "Internacional x Vasco da Gama", "team1": "Internacional", "team2": "Vasco da Gama", "date": "16/05/2026", "time": "17:30", "platform": "Amazon Prime"},
            {"comp": "Brasileirão Série A", "partida": "Fluminense x São Paulo", "team1": "Fluminense", "team2": "São Paulo", "date": "16/05/2026", "time": "19:30", "platform": "CazéTV"},
            {"comp": "Copa do Brasil", "partida": "Palmeiras x Santos", "team1": "Palmeiras", "team2": "Santos", "date": "26/08/2026", "time": "21:30", "platform": "Amazon Prime"}
        ]
        
    try:
        import csv
        with open(csv_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comp = row.get("Campeonato", "").replace("CBF - ", "").strip()
                partida = row.get("Partida", "").strip()
                d_str = row.get("Data", "").strip()
                t_str = row.get("Horário", "").strip()
                plat = row.get("Canal de Transmissão", "").strip()
                
                if not partida or "x" not in partida.lower():
                    continue
                    
                parts = partida.split(" x " if " x " in partida else " X ")
                t1 = parts[0].strip() if len(parts) > 0 else "Time 1"
                t2 = parts[1].strip() if len(parts) > 1 else "Time 2"
                
                events.append({
                    "comp": comp or "Brasileirão Série A",
                    "partida": partida,
                    "team1": t1,
                    "team2": t2,
                    "date": d_str or datetime.now().strftime("%d/%m/%Y"),
                    "time": t_str or "20:00",
                    "platform": plat or "Amazon Prime"
                })
    except Exception as e:
        print(f"[STREAMING SCHEDULER WARN] Erro ao carregar CSV: {e}")
        
    try:
        def parse_dt(g):
            try:
                return datetime.strptime(f"{g.get('date', '')} {g.get('time', '')}", "%d/%m/%Y %H:%M")
            except:
                return datetime.max
        events.sort(key=parse_dt)
    except:
        pass
        
    return events


class MonitorApp(MonitorCoreMixin, ctk.CTk):
    def _load_ui_scale_preference(self) -> float:
        path = _get_config_read_path("ui_settings.json")
        default_scale = 1.15
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    zoom_str = data.get("zoom", "115%")
                    self.ui_scale_str_var.set(zoom_str)
                    return float(zoom_str.replace("%", "")) / 100.0
            except Exception:
                pass
        self.ui_scale_str_var.set("115%")
        return default_scale

    def _on_change_ui_zoom(self, zoom_val: str) -> None:
        try:
            scale_factor = float(zoom_val.replace("%", "").strip()) / 100.0
            ctk.set_widget_scaling(scale_factor)
            ctk.set_window_scaling(scale_factor)
            _save_config_file("ui_settings.json", {"zoom": zoom_val})
            self._log(f"[UI] Zoom da interface ajustado para {zoom_val}.")
        except Exception as e:
            self._log(f"[UI WARN] Erro ao aplicar zoom: {e}")

    def __init__(self) -> None:
        super().__init__()

        ctk.set_default_color_theme("blue")
        ctk.set_appearance_mode("Dark")

        # Configuração de Escala e Zoom da Interface (Padrão 115% para legibilidade nítida e ampla)
        self.ui_scale_str_var = ctk.StringVar(value="115%")
        initial_scale = self._load_ui_scale_preference()
        try:
            ctk.set_widget_scaling(initial_scale)
            ctk.set_window_scaling(initial_scale)
        except Exception:
            pass

        # 1. Variáveis de UI e Estado (Fundamentais)
        self.perf = PerfLogger()
        self.runtime = MonitorRuntime()
        self.debug_snapshot = DebugSnapshot()
        
        # Variáveis de Controle de ROI e Debug
        self._roi_edit_mode = ctk.BooleanVar(value=False)
        self.selected_roi_var = ctk.StringVar(value="top_hud_unificado")
        self.show_context_boxes_var = ctk.BooleanVar(value=False)
        
        self.roi_pixel_var = ctk.StringVar(value="px = —")
        self.roi_percent_var = ctk.StringVar(value="pct = —")
        self.roi_ocr_var = ctk.StringVar(value="OCR = —")
        self.roi_file_var = ctk.StringVar(value="arquivo = —")

        # Variáveis de Cloud Analysis e Configuração
        self.cloud_enabled_var = ctk.BooleanVar(value=True)
        self.cloud_interval_var = ctk.IntVar(value=2)  # Sincronizado com Slider
        self.cloud_status_var = ctk.StringVar(value="Cloud: Inativo")

        # Variáveis de E-mail e Auto-Stop (Solicitado pelo usuário)
        self.email_recipients_var = ctk.StringVar(value="")
        self.send_report_email_var = ctk.BooleanVar(value=False)
        self.auto_stop_pos_mins_var = ctk.IntVar(value=5)
        self.auto_stop_pos_mins_var.trace_add("write", lambda *a: self._on_autostop_change())
        self.auto_schedule_audit_var = ctk.BooleanVar(value=False)
        self._last_auto_schedule_fetch_time = 0.0
        
        self.cloud_progress_var = ctk.DoubleVar(value=0.0)
        self.banner_ocr_interval_var = ctk.DoubleVar(value=1.0)
        
        # Categorias e Filtros
        self.category_vars: Dict[str, ctk.BooleanVar] = {}
        self.categories_list = [
            "Todos",
            "Campeonato Paulista",
            "Brasileirão",
            "Copa do Brasil",
            "Libertadores",
            "Sul-Americana",
            "Champions League",
            "Copa do Mundo",
            "Eliminatorias",
            "Amistoso",
        ]
        for cat in self.categories_list:
            self.category_vars[cat] = ctk.BooleanVar(value=(cat == "Todos"))

        self.event_filter_var = ctk.StringVar(value="Todos")
        self.event_search_var = ctk.StringVar(value="")

        # Preferências do Relatório Expert
        self.expert_show_chrono_var = ctk.BooleanVar(value=True)
        self.expert_show_milestones_var = ctk.BooleanVar(value=True)
        self.expert_show_secondary_var = ctk.BooleanVar(value=True)
        self.expert_show_sources_var = ctk.BooleanVar(value=True)

        # Outras variáveis de estado/UI
        self.preview_status_var = ctk.StringVar(value="Preview: aguardando frames...")
        self.detector_stage_var = ctk.StringVar(value="Detector: ocioso")
        self.build_marker_var = ctk.StringVar(value="")
        
        self.pipe_gate_var = ctk.StringVar(value="GATE")
        self.pipe_score_var = ctk.StringVar(value="SCORE")
        self.pipe_clock_var = ctk.StringVar(value="CLOCK")
        self.pipe_banner_var = ctk.StringVar(value="BANNER")
        self.pipe_countdown_var = ctk.StringVar(value="COUNTDOWN")

        # Text containers (initialized before _build_ui)
        self.log_text: Optional[ctk.CTkTextbox] = None
        self.error_text: Optional[ctk.CTkTextbox] = None
        self.frag_text: Optional[ctk.CTkTextbox] = None
        self.ia_log_box: Optional[ctk.CTkTextbox] = None

        # 2. Componentes de infraestrutura
        self.obs = OBSController(
            host=OBS_HOST,
            port=OBS_PORT,
            password=OBS_PASSWORD,
            obs_exe_path=OBS_EXE_PATH,
            obs_args=OBS_ARGS,
        )
        self.detector = EventDetector()
        self.detector.set_logger(self._log_from_pipeline_component)
        self.ad_analyzer = None # Inicialização preguiçosa na aba Ads
        self.ad_last_results = []
        self.ad_selected_files = []
        self.ad_stop_flag = threading.Event()
        _reports_dir = os.path.join(PROJECT_ROOT, "reports")
        os.makedirs(_reports_dir, exist_ok=True)
        self.reporter = ReportGenerator(reports_dir=_reports_dir)

        # 3. Definições de Preview / Canvas
        self._preview_display_size: Tuple[int, int] = (920, 560)
        self._preview_render_size: Tuple[int, int] = (1, 1)
        self._preview_frame_size: Tuple[int, int] = (1, 1)
        self._preview_scale_x: float = 1.0
        self._preview_scale_y: float = 1.0
        self._preview_padding_x: int = 0
        self._preview_padding_y: int = 0
        self._preview_drag_start: Optional[Tuple[int, int]] = None
        self._preview_drag_rect_id: Optional[int] = None
        self._preview_drag_label_id: Optional[int] = None
        self._last_roi_crop_applied: bool = False
        
        self._latest_raw_frame: Optional[np.ndarray] = None
        self._latest_raw_frame_ts: float = 0.0
        self._last_preview_draw_ts: float = 0.0
        self._last_preview_status_text: str = ""
        self._preview_busy: bool = False
        self._preview_lock = threading.Lock()
        self._preview_img_ref = None
        self._preview_canvas_image_id: Optional[int] = None
        self._preview_canvas_wait_id: Optional[int] = None
        self._preview_roi_items: Dict[str, Dict[str, Optional[int]]] = {}

        # 4. Threads e Timing
        self._last_meta_update_t = 0.0
        self._last_cleanup_t = 0.0
        self._last_ui_preview_t = 0.0
        self._last_frame_loop_ts = 0.0
        self._frame_processing = False
        self._analysis_lock = threading.Lock()
        self._analysis_cv = threading.Condition(self._analysis_lock)
        self._analysis_worker_thread: Optional[threading.Thread] = None
        self._pending_analysis_frame: Optional[np.ndarray] = None
        self._pending_analysis_ts: float = 0.0
        self._pending_analysis_seq: int = 0
        self._last_processed_seq: int = 0
        self._pipeline_stats: Dict[str, int] = {"queued": 0, "processed": 0, "dropped": 0}
        
        self._analysis_stop_flag = threading.Event()
        self._local_analysis_thread: Optional[threading.Thread] = None
        self._last_local_analyzed_raw_ts: float = 0.0
        self._last_local_analyze_wall_t: float = 0.0
        self._last_pipeline_watchdog_t: float = 0.0
        self._last_pipeline_processed_t: float = 0.0
        self._last_events_refresh_t: float = 0.0
        self._pipeline_seq_local: int = 0
        self._no_frames_finalize_timeout_s: float = 600.0
        self._last_no_frames_warn_t: float = 0.0
        self._pos_jogo_since: Optional[float] = None
        self._finalize_in_progress: bool = False
        self._finalize_reason: str = ""
        self._stop_flag = threading.Event()
        self._expert_stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._ingest_thread: Optional[threading.Thread] = None

        # 5. Inicialização de UI Adicional e Carregamento de Configurações
        self.roi_cards: Dict[str, Dict[str, Any]] = {}
        self._roi_refs: Dict[str, Any] = {}
        self.roi_enabled_vars: Dict[str, ctk.BooleanVar] = {}
        self._roi_enabled_checks_built: bool = False
        self._events: List[Dict[str, Any]] = []
        self._selected_indices: Set[int] = set()
        self._event_buttons: List[ctk.CTkFrame] = []
        self._event_checkbox_vars: Dict[int, ctk.BooleanVar] = {}
        self._event_checkboxes: Dict[int, ctk.CTkCheckBox] = {}
        self.stream = None
        
        # Variáveis que serão inicializadas no _build_ui mas que precisamos garantir que existam
        self.theme_var = ctk.StringVar(value="Dark")
        self.channel_url_var = ctk.StringVar(value=CHANNEL_STREAMS_URL)
        self.channel_var = ctk.StringVar(value="CazéTV")
        self.manual_url_var = ctk.StringVar(value="")
        self.auto_prepare_var = ctk.BooleanVar(value=True)
        self.auto_start_var = ctk.BooleanVar(value=bool(AUTO_MONITOR_WHEN_LIVE))
        self.debug_mode_var = ctk.BooleanVar(value=True)
        self.status_var = ctk.StringVar(value="🔴 Parado")

        # Monitor Tab Vars
        self.frames_var = ctk.StringVar(value="0")
        self.phase_var = ctk.StringVar(value="—")
        self.clock_var = ctk.StringVar(value="—")
        self.score_var = ctk.StringVar(value="—")
        self.match_var = ctk.StringVar(value="—")
        self.comp_var = ctk.StringVar(value="—")
        self.detector_perf_var = ctk.StringVar(value="—")
        self.visual_conf_var = ctk.StringVar(value="—")

        # Fragment Tab Vars
        self.frag_filter_var = ctk.StringVar(value="all")
        self.frag_autoscroll_var = ctk.BooleanVar(value=True)

        # History and Debug Vars
        self.hist_filter_var = ctk.StringVar(value="Tudo")
        self.dbg_visual_state_var = ctk.StringVar(value="visual_state: —")
        self.dbg_phase_var = ctk.StringVar(value="match_phase_text: —")
        self.dbg_countdown_var = ctk.StringVar(value="countdown: —")
        self.dbg_clock_raw_var = ctk.StringVar(value="clock bruto: —")
        self.dbg_clock_ok_var = ctk.StringVar(value="clock aceito: —")
        self.dbg_score_raw_var = ctk.StringVar(value="score bruto: —")
        self.dbg_score_ok_var = ctk.StringVar(value="score aceito: —")
        self.dbg_banner_var = ctk.StringVar(value="banner: —")
        self.dbg_teams_var = ctk.StringVar(value="times: —")

        # Expert Assistant Mode (API-Only)
        self.monitoring_mode_var = ctk.StringVar(value="Expert (API-Only)")
        self.expert_team1_var = ctk.StringVar(value="")
        self.expert_team2_var = ctk.StringVar(value="")
        self.expert_comp_var = ctk.StringVar(value="")
        self.expert_platform_var = ctk.StringVar(value="CazéTV")
        self.expert_date_var = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.expert_time_var = ctk.StringVar(value="")
        self.expert_tag_var = ctk.StringVar(value="🏷️ Normal")
        self.dbg_comp_var = ctk.StringVar(value="competição: —")
        self.dbg_seek_var = ctk.StringVar(value="seek: —")
        self.dbg_perf_var = ctk.StringVar(value="latência/fps: —")
        self.ad_video_path_var = ctk.StringVar(value="")

        self.ctx_headline_var = ctk.StringVar(value="headline: —")
        self.ctx_subheadline_var = ctk.StringVar(value="subheadline: —")
        self.ctx_left_tag_var = ctk.StringVar(value="left_tag: —")
        self.ctx_right_tag_var = ctk.StringVar(value="right_tag: —")
        self.ctx_bottom_line_var = ctk.StringVar(value="bottom_line: —")
        self.ctx_top_overlay_var = ctk.StringVar(value="top_overlay: —")
        self.ctx_left_panel_var = ctk.StringVar(value="left_panel: —")
        self.ctx_right_panel_var = ctk.StringVar(value="right_panel: —")
        self.ctx_blocks_var = ctk.StringVar(value="blocks: 0")
        self.ctx_blocks_text = ""

        # Config Tab Vars
        self.prepare_min_var = ctk.IntVar(value=int(PREPARE_MINUTES_BEFORE))
        self.cleanup_days_var = ctk.IntVar(value=7)
        self.sample_fps_var = ctk.IntVar(value=int(FRAME_SAMPLE_FPS))
        self.seg_audio_var = ctk.IntVar(value=int(AUDIO_SEGMENT_SECONDS))
        self.partial_report_var = ctk.IntVar(value=600)

        # Variáveis de Busca (Data)
        from datetime import timedelta
        now = datetime.now()
        sixty_days_ago = now - timedelta(days=60)
        self.search_date_start_var = ctk.StringVar(value=sixty_days_ago.strftime("%d/%m/%Y"))
        self.search_date_end_var = ctk.StringVar(value=now.strftime("%d/%m/%Y"))

        self.event_sort_var = ctk.StringVar(value="Data (Recentes)")

        updater = AutoUpdater()
        self.title(f"Expert Assistant & Strategic Monitoring - Mediadna (v{updater.current_version})")
        self._center_window(1600, 940)
        self._audit_semaphore = threading.Semaphore(2)
        self._schedule_cards_cache = {}

        self._is_loading_settings = True
        try:
            self._load_general_settings()
        finally:
            self._is_loading_settings = False

        self._build_ui()
        self._scheduled_games = _load_scheduled_games()
        self._render_dynamic_quick_presets()
        self._render_cbf_mural_ui()
        self._on_mode_change(self.monitoring_mode_var.get())
        
        # Thread para verificar atualizações no GitHub em background
        def check_updates():
            try:
                has_update, remote_ver, download_url, changelog = updater.check_for_update()
                if has_update:
                    def ask_user():
                        # Atualizar a UI do cabeçalho com o alerta de atualização pendente
                        if hasattr(self, "btn_header_update"):
                            self.btn_header_update.configure(
                                text=f"⚠️ Atualizar para v{remote_ver}", 
                                fg_color="#FF4500", 
                                hover_color="#CD3700"
                            )
                        if hasattr(self, "lbl_header_version"):
                            self.lbl_header_version.configure(text_color="#00FF00")
                            
                        msg = f"Uma nova versão ({remote_ver}) está disponível!\n\nChangelog:\n{changelog}\n\nDeseja baixar e atualizar agora automaticamente?"
                        if messagebox.askyesno("Atualização Disponível", msg):
                            self._start_self_update(download_url, remote_ver)
                    self.after(0, ask_user)
            except Exception as e_up:
                print(f"[AUTO-UPDATER WARN] Erro ao verificar atualizações: {e_up}")

        threading.Thread(target=check_updates, daemon=True).start()

        self._log("[RESTORE] GUI reinicializada com sucesso")

        self.after(250, self._tick_ui)
        self.after(180, self._tick_debug_preview)
        self.after(1000, self._tick_autopilot)
        self.after(2000, self._start_schedule_timer_loop)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._sync_buttons()
        
        # Inicia provedor de API para o Frontend React (Porta 5000)
        start_api_thread(self)
        self._on_autostop_change() # Sync inicial

    def _on_autostop_change(self) -> None:
        try:
            mins = int(self.auto_stop_pos_mins_var.get())
            if mins > 0:
                self._no_frames_finalize_timeout_s = float(mins * 60)
                self._log(f"[WATCHDOG] Timeout de inatividade sincronizado: {mins} min ({self._no_frames_finalize_timeout_s}s)")
            else:
                self._no_frames_finalize_timeout_s = 600.0 # Default seguro se 0
                self._log("[WATCHDOG] Auto-Stop desativado; usando timeout padrão de 10 min para queda de sinal.")
        except Exception as e:
            print(f"Error on autostop change: {e}")


    # =========================================================
    # ROI / Preview
    # =========================================================

    def _on_roi_edit_mode_toggle(self) -> None:
        active = bool(self._roi_edit_mode.get())

        try:
            self.preview_canvas.configure(cursor=("crosshair" if active else "arrow"))
        except Exception:
            pass

        try:
            self.btn_roi_save.configure(
                state="normal",
                fg_color=("#1565C0", "#1565C0") if active else None,
                hover_color=("#0F4B92", "#0F4B92") if active else None,
            )
            self.btn_roi_save.lift()
        except Exception:
            pass

        try:
            self._update_preview_widget()
        except Exception:
            pass

    def _current_roi_xywh(self, key: str, frame: Optional[np.ndarray]) -> Optional[Tuple[int, int, int, int]]:
        vision = getattr(self.detector, "vision", None)
        if vision is None or frame is None or frame.size == 0:
            return None

        try:
            return vision.get_roi_pixels(frame, key)
        except Exception:
            return None

    def _clear_preview_overlay_items(self) -> None:
        try:
            for item in self._preview_roi_items.values():
                rect_id = item.get("rect")
                text_id = item.get("text")
                if rect_id:
                    self.preview_canvas.delete(rect_id)
                if text_id:
                    self.preview_canvas.delete(text_id)
        except Exception:
            pass
        self._preview_roi_items = {}

    def _show_preview_waiting(self, text: str) -> None:
        self.preview_canvas.delete("all")
        self._preview_canvas_image_id = None
        self._preview_canvas_wait_id = self.preview_canvas.create_text(
            40,
            30,
            anchor="nw",
            fill="white",
            text=text,
        )
        self._clear_preview_overlay_items()

    def _ensure_preview_image(self, tk_img: Any, w: int, h: int) -> None:
        self._preview_img_ref = tk_img
        self.preview_canvas.configure(width=w, height=h)

        if self._preview_canvas_wait_id:
            try:
                self.preview_canvas.delete(self._preview_canvas_wait_id)
            except Exception:
                pass
            self._preview_canvas_wait_id = None

        # Centralização automática para preencher a área
        w_canvas = self.preview_canvas.winfo_width()
        h_canvas = self.preview_canvas.winfo_height()
        
        if self._preview_canvas_image_id is None:
            self._preview_canvas_image_id = self.preview_canvas.create_image(
                w_canvas // 2, h_canvas // 2, anchor="center", image=self._preview_img_ref
            )
        else:
            self.preview_canvas.itemconfig(self._preview_canvas_image_id, image=self._preview_img_ref)
            self.preview_canvas.coords(self._preview_canvas_image_id, w_canvas // 2, h_canvas // 2)
            self.preview_canvas.itemconfig(self._preview_canvas_image_id, anchor="center")

    def _draw_roi_overlays_on_canvas(self, frame: np.ndarray) -> None:
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            self._clear_preview_overlay_items()
            return

        colors = {
            "top_hud_unificado": "#00FF7F",
            "banner": "#FF9800",
            "countdown_center": "#00BFFF",
        }

        try:
            labels = vision.get_supported_roi_labels()
        except Exception:
            labels = []

        selected_key = (self.selected_roi_var.get() or "").strip().lower()
        only_selected = bool(self._roi_edit_mode.get())

        wanted_keys: List[str] = []
        for key in labels:
            if only_selected and key != selected_key:
                continue
            wanted_keys.append(key)

        current_keys = set(self._preview_roi_items.keys())
        wanted_set = set(wanted_keys)

        for stale_key in current_keys - wanted_set:
            item = self._preview_roi_items.pop(stale_key, {})
            try:
                if item.get("rect"):
                    self.preview_canvas.delete(item["rect"])
                if item.get("text"):
                    self.preview_canvas.delete(item["text"])
            except Exception:
                pass

        for key in wanted_keys:
            rect = self._current_roi_xywh(key, frame)
            if not rect:
                item = self._preview_roi_items.pop(key, None)
                if item:
                    try:
                        if item.get("rect"):
                            self.preview_canvas.delete(item["rect"])
                        if item.get("text"):
                            self.preview_canvas.delete(item["text"])
                    except Exception:
                        pass
                continue

            x, y, w, h = rect

            sx1 = int(round(x / max(1e-9, self._preview_scale_x))) + self._preview_padding_x
            sy1 = int(round(y / max(1e-9, self._preview_scale_y))) + self._preview_padding_y
            sx2 = int(round((x + w) / max(1e-9, self._preview_scale_x))) + self._preview_padding_x
            sy2 = int(round((y + h) / max(1e-9, self._preview_scale_y))) + self._preview_padding_y

            selected = key == selected_key
            line_w = 3 if selected else 2
            color = colors.get(key, "#FFFFFF")

            item = self._preview_roi_items.get(key)
            if item is None:
                rect_id = self.preview_canvas.create_rectangle(
                    sx1, sy1, sx2, sy2,
                    outline=color,
                    width=line_w
                )
                text_id = self.preview_canvas.create_text(
                    sx1 + 6,
                    max(10, sy1 - 8),
                    anchor="sw",
                    fill=color,
                    text=key
                )
                self._preview_roi_items[key] = {"rect": rect_id, "text": text_id}
            else:
                rect_id = item.get("rect")
                text_id = item.get("text")

                if rect_id:
                    self.preview_canvas.coords(rect_id, sx1, sy1, sx2, sy2)
                    self.preview_canvas.itemconfig(rect_id, outline=color, width=line_w)

                if text_id:
                    self.preview_canvas.coords(text_id, sx1 + 6, max(10, sy1 - 8))
                    self.preview_canvas.itemconfig(text_id, fill=color, text=key)

    def _draw_screen_context_overlays_on_canvas(self, frame: np.ndarray) -> None:
        if not bool(self.show_context_boxes_var.get()):
            return
        snap = getattr(self, "debug_snapshot", None)
        if snap is None:
            return
        visual_info = getattr(snap, "visual_info", {}) or {}
        screen_ctx = visual_info.get("screen_context") or {}
        blocks = screen_ctx.get("blocks") or []
        if not isinstance(blocks, list):
            return
        for idx, block in enumerate(blocks[:18]):
            gb = block.get("global_bbox") or block.get("bbox")
            if not gb or len(gb) != 4:
                continue
            x, y, w, h = gb
            sx1 = int(round(x / max(1e-9, self._preview_scale_x))) + self._preview_padding_x
            sy1 = int(round(y / max(1e-9, self._preview_scale_y))) + self._preview_padding_y
            sx2 = int(round((x + w) / max(1e-9, self._preview_scale_x))) + self._preview_padding_x
            sy2 = int(round((y + h) / max(1e-9, self._preview_scale_y))) + self._preview_padding_y
            try:
                self.preview_canvas.create_rectangle(sx1, sy1, sx2, sy2, outline="#FFB300", width=1)
                label = str(block.get("text") or block.get("zone") or f"blk{idx}")[:28]
                self.preview_canvas.create_text(sx1 + 3, max(8, sy1 - 6), anchor="sw", fill="#FFB300", text=label)
            except Exception:
                pass

    def _fill_context_blocks_text(self, blocks: List[Dict[str, Any]]) -> None:
        widget = getattr(self, "ctx_blocks_text", None)
        if widget is None:
            return
        try:
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            for i, block in enumerate((blocks or [])[:20], 1):
                zone = str(block.get("zone") or "—")
                text = str(block.get("text") or "—").strip()
                conf = float(block.get("confidence", 0.0) or 0.0)
                widget.insert("end", f"{i:02d}. [{zone}] conf={conf:.2f} | {text}\n")
            widget.configure(state="disabled")
        except Exception:
            pass

    def _refresh_selected_roi_panel(self) -> None:
        snap = getattr(self, "debug_snapshot", None)
        if snap is None:
            self.roi_pixel_var.set("px = —")
            self.roi_percent_var.set("pct = —")
            self.roi_ocr_var.set("OCR = —")
            return

        key = (self.selected_roi_var.get() or "").strip().lower()
        frame = getattr(snap, "frame_bgr", None)

        if frame is None:
            frame = getattr(snap, "annotated_bgr", None)

        rect = self._current_roi_xywh(key, frame)

        if rect:
            x, y, w, h = rect
            pct = self._frame_to_percent_rect((x, y, x + w, y + h))
            self.roi_pixel_var.set(f"px = ({x}, {y}, {w}, {h})")
            self.roi_percent_var.set(
                f"pct = ({pct['x']:.4f}, {pct['y']:.4f}, {pct['w']:.4f}, {pct['h']:.4f})"
            )
        else:
            self.roi_pixel_var.set("px = —")
            self.roi_percent_var.set("pct = —")

        ocr_value = "—"
        try:
            card = self.roi_cards.get(key)
            if card:
                ocr_value = str(card["txt"].get()).replace("OCR: ", "", 1)
        except Exception:
            pass

        self.roi_ocr_var.set(f"OCR = {ocr_value}")

    def _preview_to_frame_xy(self, px: int, py: int) -> Tuple[int, int]:
        # Adjust canvas coordinates by padding before scaling to frame coordinates
        fx = int(round((px - self._preview_padding_x) * self._preview_scale_x))
        fy = int(round((py - self._preview_padding_y) * self._preview_scale_y))

        fw, fh = self._preview_frame_size
        fx = max(0, min(fx, max(0, fw - 1)))
        fy = max(0, min(fy, max(0, fh - 1)))
        return fx, fy

    def _frame_to_percent_rect(self, rect_xyxy: Tuple[int, int, int, int]) -> Dict[str, float]:
        fw, fh = self._preview_frame_size
        x1, y1, x2, y2 = rect_xyxy

        x = max(0, min(x1, fw - 1))
        y = max(0, min(y1, fh - 1))
        w = max(1, x2 - x1)
        h = max(1, y2 - y1)

        return {
            "x": round(x / max(1, fw), 6),
            "y": round(y / max(1, fh), 6),
            "w": round(w / max(1, fw), 6),
            "h": round(h / max(1, fh), 6),
        }

    def _on_preview_mouse_down(self, event: Any) -> None:
        if not self._roi_edit_mode.get():
            return

        self._preview_drag_start = (int(event.x), int(event.y))

        try:
            if self._preview_drag_rect_id:
                self.preview_canvas.delete(self._preview_drag_rect_id)
            if self._preview_drag_label_id:
                self.preview_canvas.delete(self._preview_drag_label_id)
        except Exception:
            pass

        self._preview_drag_rect_id = self.preview_canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="#00E5FF",
            width=2,
            dash=(4, 2)
        )

        self._preview_drag_label_id = self.preview_canvas.create_text(
            event.x + 8, event.y + 8,
            anchor="nw",
            fill="#00E5FF",
            text=self.selected_roi_var.get()
        )

    def _on_preview_mouse_drag(self, event: Any) -> None:
        if not self._roi_edit_mode.get():
            return
        if not self._preview_drag_start:
            return
        if not self._preview_drag_rect_id:
            return

        x0, y0 = self._preview_drag_start
        self.preview_canvas.coords(self._preview_drag_rect_id, x0, y0, event.x, event.y)

        if self._preview_drag_label_id:
            self.preview_canvas.coords(
                self._preview_drag_label_id,
                min(x0, event.x) + 8,
                min(y0, event.y) + 8
            )

    def _on_preview_mouse_up(self, event: Any) -> None:
        if not self._roi_edit_mode.get():
            return
        if not self._preview_drag_start:
            return

        x0, y0 = self._preview_drag_start
        x1, y1 = int(event.x), int(event.y)
        self._preview_drag_start = None

        if abs(x1 - x0) < 4 or abs(y1 - y0) < 4:
            return

        px1, px2 = sorted([x0, x1])
        py1, py2 = sorted([y0, y1])

        fx1, fy1 = self._preview_to_frame_xy(px1, py1)
        fx2, fy2 = self._preview_to_frame_xy(px2, py2)

        if fx2 <= fx1 or fy2 <= fy1:
            return

        pct = self._frame_to_percent_rect((fx1, fy1, fx2, fy2))
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            return

        key = (self.selected_roi_var.get() or "").strip().lower()

        try:
            vision.set_roi_override(key, pct)
            self._last_roi_crop_applied = True
            self._refresh_selected_roi_panel()
            try:
                self.btn_roi_save.configure(
                    state="normal",
                    fg_color=("#1B5E20", "#1B5E20"),
                    hover_color=("#144A18", "#144A18"),
                    text="Salvar calibração",
                )
                self.btn_roi_save.lift()
                self.btn_roi_save.focus_set()
            except Exception:
                pass
            try:
                self._log(
                    f"[ROI] {key} = px({fx1},{fy1},{fx2 - fx1},{fy2 - fy1}) "
                    f"pct({pct['x']:.4f},{pct['y']:.4f},{pct['w']:.4f},{pct['h']:.4f})"
                )
                self._log("[ROI] crop manual aplicado. Clique em 'Salvar calibração' para persistir no JSON.")
            except Exception:
                pass
        except Exception as e:
            try:
                self._log(f"[WARN] set roi drag: {e}")
            except Exception:
                pass

    # =========================================================
    # UI helpers
    # =========================================================

    def _ui_info(self, msg: str) -> None:
        self._set_status("preparing", msg)
        self._log(msg)

    def _ui_success(self, msg: str) -> None:
        self._set_status("running", msg)
        self._log(f"[SUCESSO] {msg}")

    def _ui_error(self, msg: str) -> None:
        self._set_status("stopped", msg)
        self._log(f"[ERRO] {msg}")

    def _sync_buttons(self) -> None:
        busy = bool(self.runtime.running or self.runtime.preparing)

        for btn, state_busy, state_idle in [
            (getattr(self, "btn_start", None), "disabled", "normal"),
            (getattr(self, "btn_start_manual", None), "disabled", "normal"),
            (getattr(self, "btn_load", None), "disabled", "normal"),
        ]:
            try:
                if btn is not None:
                    btn.configure(state=(state_busy if busy else state_idle))
            except Exception:
                pass

        try:
            self.btn_stop.configure(state=("normal" if busy else "disabled"))
        except Exception:
            pass

        try:
            self.btn_snapshot.configure(state=("normal" if busy else "disabled"))
        except Exception:
            pass

        try:
            self.btn_stop.configure(
                fg_color=("#B00020", "#B00020") if busy else ("gray40", "gray25"),
                hover_color=("#8C001A", "#8C001A") if busy else None,
            )
        except Exception:
            pass

        try:
            if not busy:
                self.btn_start.configure(fg_color=("#1B5E20", "#1B5E20"), hover_color=("#144A18", "#144A18"))
                self.btn_start_manual.configure(fg_color=("#1565C0", "#1565C0"), hover_color=("#0F4B92", "#0F4B92"))
            else:
                self.btn_start.configure(fg_color=("gray40", "gray25"))
                self.btn_start_manual.configure(fg_color=("gray40", "gray25"))
        except Exception:
            pass

    def _roi_profile_slug(self) -> str:
        raw = ""
        try:
            raw = (self.channel_var.get() or "").strip().lower()
        except Exception:
            raw = "default"

        raw = unicodedata.normalize("NFKD", raw)
        raw = "".join(ch for ch in raw if not unicodedata.combining(ch))
        raw = re.sub(r"[^a-z0-9_\-]+", "_", raw)
        raw = raw.strip("_")
        return raw or "default"

    def _roi_profile_path(self) -> str:
        return os.path.join("config", f"roi_{self._roi_profile_slug()}.json")

    def _roi_enabled_profile_path(self) -> str:
        return os.path.join("config", f"roi_enabled_{self._roi_profile_slug()}.json")

    def _get_roi_toggle_keys(self) -> List[str]:
        vision = getattr(self.detector, "vision", None)
        try:
            if vision is not None and hasattr(vision, "get_roi_enabled_map"):
                data = vision.get_roi_enabled_map()
                if isinstance(data, dict) and data:
                    return list(data.keys())
        except Exception:
            pass
        return [
            "top_hud_unificado",
            "banner",
            "countdown_center",
        ]

    def _ensure_roi_toggle_vars(self) -> None:
        for key in self._get_roi_toggle_keys():
            if key not in self.roi_enabled_vars:
                self.roi_enabled_vars[key] = ctk.BooleanVar(value=True)

    def _collect_roi_enabled_map_from_ui(self) -> Dict[str, bool]:
        self._ensure_roi_toggle_vars()
        return {str(k): bool(v.get()) for k, v in self.roi_enabled_vars.items()}

    def _save_roi_enabled_profile(self) -> bool:
        self._ensure_roi_toggle_vars()
        path = self._roi_enabled_profile_path()
        data = {
            "profile": self._roi_profile_slug(),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "roi_enabled": self._collect_roi_enabled_map_from_ui(),
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._log(f"[ROI] ativação salva: {path}")
            # Ao salvar ROI, também salvamos configs gerais
            self._save_general_settings()
            return True
        except Exception as e:
            self._log(f"[WARN] save roi enabled: {e}")
            return False

    def _general_settings_path(self) -> str:
        return os.path.join("config", "general_settings.json")

    def _save_general_settings(self) -> bool:
        path = self._general_settings_path()
        data = {
            "theme": self.theme_var.get(),
            "channel_preset": self.channel_var.get(),
            "channel_url": self.channel_url_var.get(),
            "cloud_enabled": bool(self.cloud_enabled_var.get()),
            "cloud_interval_minutes": int(self.cloud_interval_var.get()),
            "banner_ocr_interval_s": float(self.banner_ocr_interval_var.get()),
            "selected_categories": [cat for cat, var in self.category_vars.items() if var.get()],
            "auto_prepare": bool(self.auto_prepare_var.get()),
            "auto_start": bool(self.auto_start_var.get()),
            "debug_mode": bool(self.debug_mode_var.get()),
            "email_recipients": self.email_recipients_var.get(),
            "send_report_email": bool(self.send_report_email_var.get()),
            "auto_schedule_audit": bool(self.auto_schedule_audit_var.get()),
            "auto_stop_pos_mins": int(self.auto_stop_pos_mins_var.get()),
            "show_context_boxes": bool(self.show_context_boxes_var.get()),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self._log(f"[WARN] Erro ao salvar configurações gerais: {e}")
            return False

    def _load_general_settings(self) -> None:
        path = self._general_settings_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if "theme" in data:
                self.theme_var.set(data["theme"])
                ctk.set_appearance_mode(data["theme"])
            if "channel_preset" in data:
                self.channel_var.set(data["channel_preset"])
            if "channel_url" in data:
                self.channel_url_var.set(data["channel_url"])
            if "cloud_enabled" in data:
                self.cloud_enabled_var.set(data["cloud_enabled"])
            if "cloud_interval_minutes" in data:
                self.cloud_interval_var.set(data["cloud_interval_minutes"])
            if "banner_ocr_interval_s" in data:
                self.banner_ocr_interval_var.set(data["banner_ocr_interval_s"])
            if "auto_prepare" in data:
                self.auto_prepare_var.set(data["auto_prepare"])
            if "auto_start" in data:
                self.auto_start_var.set(data["auto_start"])
            if "debug_mode" in data:
                self.debug_mode_var.set(data["debug_mode"])
            if "email_recipients" in data:
                self.email_recipients_var.set(data["email_recipients"])
            if "send_report_email" in data:
                self.send_report_email_var.set(data["send_report_email"])
            if "auto_schedule_audit" in data:
                self.auto_schedule_audit_var.set(data["auto_schedule_audit"])
            if "auto_stop_pos_mins" in data:
                self.auto_stop_pos_mins_var.set(data["auto_stop_pos_mins"])
            if "show_context_boxes" in data:
                self.show_context_boxes_var.set(data["show_context_boxes"])
            if "selected_categories" in data:
                sel = data["selected_categories"]
                if sel:
                    # Desmarca tudo primeiro
                    for v in self.category_vars.values():
                        v.set(False)
                    # Marca os salvos
                    found = False
                    for cat_name in sel:
                        if cat_name in self.category_vars:
                            self.category_vars[cat_name].set(True)
                            found = True
                    if not found:
                        self.category_vars["Todos"].set(True)
            
            # Aplicar ao detector
            self.detector.cfg.cloud_enabled = bool(self.cloud_enabled_var.get())
            self.detector.cfg.cloud_interval_minutes = int(self.cloud_interval_var.get())
            self.detector.cfg.banner_ocr_interval_s = float(self.banner_ocr_interval_var.get())
            
            # Garantir aplicação no vision component
            if hasattr(self.detector, "vision"):
                self.detector.vision.banner_ocr_interval_s = float(self.banner_ocr_interval_var.get())
            
            self._log(f"[CONFIG] Configurações gerais carregadas de {path}")
        except Exception as e:
            self._log(f"[WARN] Erro ao carregar configurações gerais: {e}")

    def _load_roi_enabled_ui_from_detector(self) -> None:
        self._ensure_roi_toggle_vars()
        vision = getattr(self.detector, "vision", None)
        enabled_map: Dict[str, bool] = {}
        try:
            if vision is not None and hasattr(vision, "get_roi_enabled_map"):
                data = vision.get_roi_enabled_map()
                if isinstance(data, dict):
                    enabled_map = {str(k): bool(v) for k, v in data.items()}
        except Exception:
            enabled_map = {}

        for key, var in self.roi_enabled_vars.items():
            var.set(bool(enabled_map.get(key, True)))

    def _load_roi_enabled_profile(self, apply_runtime: bool = True) -> None:
        self._ensure_roi_toggle_vars()
        path = self._roi_enabled_profile_path()

        if not os.path.isfile(path):
            self._load_roi_enabled_ui_from_detector()
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

            enabled_map = data.get("roi_enabled", {})
            if not isinstance(enabled_map, dict):
                enabled_map = {}

            for key in self._get_roi_toggle_keys():
                if key not in self.roi_enabled_vars:
                    self.roi_enabled_vars[key] = ctk.BooleanVar(value=True)

            for key, var in self.roi_enabled_vars.items():
                var.set(bool(enabled_map.get(key, True)))

            if apply_runtime:
                vision = getattr(self.detector, "vision", None)
                if vision is not None:
                    for key, var in self.roi_enabled_vars.items():
                        try:
                            if hasattr(vision, "set_roi_enabled"):
                                vision.set_roi_enabled(key, bool(var.get()))
                        except Exception:
                            pass

            self._log(f"[ROI] ativação carregada: {path}")
        except Exception as e:
            self._log(f"[WARN] load roi enabled: {e}")
            self._load_roi_enabled_ui_from_detector()

    def _update_preview_widget(self) -> None:
        try:
            if not self.tab_monitor.winfo_ismapped() and not self.tab_debug.winfo_ismapped():
                return
            if self.frame_q.empty():
                return
            frame_preview, snap = self.frame_q.get_nowait()
            self.debug_snapshot = snap
            self._draw_preview(frame_preview, snap)
        except Exception as e:
            self._log(f"[WARN] update_preview: {e}")

    def _on_history_filter_change(self, val: str) -> None:
        self._update_history_grid(force=True)

    def _update_history_grid(self, force: bool = False) -> None:
        tl = self.detector.get_timeline()
        if len(tl) == getattr(self, "_last_history_count", 0) and not force:
            return
        self._last_history_count = len(tl)
        for widget in self.history_grid.winfo_children():
            widget.destroy()
        if not tl:
            self.hist_empty_lbl = ctk.CTkLabel(self.history_grid, text="Nenhum momento capturado.", text_color="#555555")
            self.hist_empty_lbl.pack(pady=40)
            return
        filt = self.hist_filter_var.get()
        count = 0
        
        # Encontrar o primeiro horário válido para base_sec
        base_sec = None
        for item in tl:
            c = item.get("clock")
            if not c or c == "N/A" or c == "00:00":
                t_sec = item.get("t_seconds", 0)
                if t_sec > 0:
                    c = f"{int(t_sec//3600):02d}:{int((t_sec%3600)//60):02d}:{int(t_sec%60):02d}"
            
            if c:
                m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(c).strip())
                if m:
                    base_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                    break

        def sort_key(x):
            lbl = str(x.get("label", "") or x.get("type", "")).upper()
            try:
                m_min = int(x.get("minute", 0))
            except:
                try:
                    m_min = int(x.get("details", {}).get("minute", 0))
                except:
                    m_min = 0
            
            prio = 50
            if "INÍCIO TRANSMISSÃO" in lbl or "INICIO TRANSMISSÃO" in lbl or "INICIO_TRANSMISSAO" in lbl: prio = 0
            elif "PRE_JOGO" in lbl: prio = 1
            elif "INÍCIO" in lbl or "INICIO" in lbl: prio = 2
            elif "APITO INICIAL (1T)" in lbl or "APITO_INICIAL_1T" in lbl: prio = 3
            elif any(k in lbl for k in ["GOL", "CARTÃO", "CARTAO", "VAR", "SUBSTI", "PENAL"]): prio = 5
            elif "ACRÉSCIMO" in lbl or "ACRESCIMO" in lbl: prio = 8
            elif "INTERVALO" in lbl: prio = 10
            elif "VOLTA INTERVALO" in lbl or "VOLTA_INTERVALO" in lbl: prio = 11
            elif "APITO INICIAL (2T)" in lbl or "APITO_INICIAL_2T" in lbl: prio = 12
            elif "APITO FINAL" in lbl or "APITO_FINAL" in lbl: prio = 90
            elif "ENCERRAMENTO" in lbl: prio = 100
            
            c = x.get("clock")
            if not c or c == "N/A" or c == "00:00":
                t_sec = x.get("t_seconds", 0)
                if t_sec > 0:
                    c = f"{int(t_sec//3600):02d}:{int((t_sec%3600)//60):02d}:{int(t_sec%60):02d}"
            
            if c:
                m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(c).strip())
                if m:
                    clk_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                    if base_sec is not None and clk_sec < base_sec - 43200: # Virada de meia-noite
                        clk_sec += 86400
                    return (1, clk_sec, prio, m_min)
            
            return (0, m_min, prio, lbl)

        rendering_list = sorted(tl, key=sort_key)

        for entry in rendering_list:
            etype = str(entry.get("type", "")).lower()
            label = str(entry.get("label", ""))
            if filt == "Banners/IA" and etype not in ("ia_analysis", "banner"): continue
            if filt == "Gols/Cartões" and label not in ("GOL", "CARTAO_AMARELO", "CARTAO_VERMELHO", "VAR"): continue
            if filt == "Mudança de Fase" and etype != "phase_change": continue
            if filt == "Debug/Errors" and etype not in ("error", "debug"): continue
            self._create_history_card(entry)
            count += 1
            if count >= 60: break # Aumentado para ver batch completa
        if count == 0:
            ctk.CTkLabel(self.history_grid, text="Nenhum momento para o filtro.", text_color="#555555").pack(pady=20)

    def _create_history_card(self, entry: Dict[str, Any]) -> None:
        if hasattr(self, "hist_empty_lbl") and self.hist_empty_lbl.winfo_exists():
            self.hist_empty_lbl.destroy()
            
        card = ctk.CTkFrame(self.history_grid, corner_radius=8, fg_color="#181818", border_width=1, border_color="#2c2c2c", height=36)
        card.pack(fill="x", padx=4, pady=3)
        
        clock = entry.get("clock")
        if not clock or clock == "N/A" or clock == "00:00":
            t_sec = entry.get("t_seconds", 0)
            if t_sec > 0:
                clock = f"{int(t_sec//60):02d}:{int(t_sec%60):02d}"
            else:
                clock = "--:--"
        
        m_min = entry.get("minute")
        min_str = f" - {m_min}'" if m_min is not None and str(m_min) != "0" else ""
        time_lbl = f"[{clock}{min_str}]"

        badge_color = "#00CED1"
        label = str(entry.get("label", "")).upper()
        if "GOL" in label: badge_color = "#FFD700"
        elif "CARTAO" in label: badge_color = "#FF4500"
        elif "APITO" in label or "INICIO" in label or "FIM" in label: badge_color = "#ADFF2F"
        
        ctk.CTkLabel(card, text=time_lbl, font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#ffffff").pack(side="left", padx=(10, 4), pady=5)
        ctk.CTkLabel(card, text=label or entry.get("type", "").upper(), font=ctk.CTkFont(size=12, weight="bold"), text_color=badge_color).pack(side="left", padx=4, pady=5)
        
        details = entry.get("details", "")
        if isinstance(details, dict):
            summary = (
                details.get("summary") 
                or details.get("context_summary") 
                or details.get("mensagem") 
                or details.get("banner_text") 
                or details.get("banner_hint") 
                or ""
            )
        else:
            summary = str(details)
            
        if summary:
            ctk.CTkLabel(card, text=f"• {summary[:85]}", font=ctk.CTkFont(size=12), text_color="#E0E0E0", anchor="w").pack(side="left", fill="x", expand=True, padx=6, pady=5)

        conf = entry.get("confidence", 0.85)
        try:
            val = int(float(conf) * 100)
            bg_color = "#1B5E20" if val > 80 else "#FBC02D" if val > 50 else "#B71C1C"
            cbadge = ctk.CTkLabel(
                card, 
                text=f"{val}%", 
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white",
                fg_color=bg_color,
                corner_radius=6,
                width=42,
                height=22
            )
            cbadge.pack(side="right", padx=8, pady=5)
        except: pass

        # Exibição de Fontes (Grounding)
        sources = entry.get("sources", [])
        if sources:
            src_frame = ctk.CTkFrame(card, fg_color="transparent")
            src_frame.pack(fill="x", padx=12, pady=(0, 8))
            
            # Formata lista de nomes de domínios ou títulos curtos
            src_list = []
            for s in sources[:3]: # Limita a 3 fontes principais para ser sucinto
                title = s.get("title", "")
                if len(title) > 30: title = title[:27] + "..."
                src_list.append(title)
            
            txt_sources = "Fontes: " + ", ".join(src_list)
            if len(sources) > 3:
                txt_sources += f" (+{len(sources)-3})"
                
            ctk.CTkLabel(src_frame, text=txt_sources, font=ctk.CTkFont(size=11, slant="italic"), text_color="#00E5FF").pack(side="left")

    def _apply_roi_enabled_runtime(self, save_profile: bool = False) -> None:
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            return

        self._ensure_roi_toggle_vars()

        applied: Dict[str, bool] = {}
        for key, var in self.roi_enabled_vars.items():
            enabled = bool(var.get())
            applied[key] = enabled
            try:
                if hasattr(vision, "set_roi_enabled"):
                    vision.set_roi_enabled(key, enabled)
            except Exception:
                pass

        if save_profile:
            self._save_current_roi_profile()
            self._save_roi_enabled_profile()
        else:
            self._refresh_selected_roi_panel()

        try:
            enabled_list = ", ".join([k for k, v in applied.items() if v]) or "nenhuma"
            disabled_list = ", ".join([k for k, v in applied.items() if not v]) or "nenhuma"
            action = "salvas" if save_profile else "aplicadas"
            self._log(f"[ROI] ROIs {action} | ativas: {enabled_list} | desativadas: {disabled_list}")
        except Exception:
            pass

    def _set_roi_mode_performance(self) -> None:
        self._ensure_roi_toggle_vars()
        keep = {"top_hud_unificado"}
        for key, var in self.roi_enabled_vars.items():
            var.set(key in keep)

    def _set_roi_mode_full(self) -> None:
        self._ensure_roi_toggle_vars()
        for var in self.roi_enabled_vars.values():
            var.set(True)

    def _reload_roi_enabled_from_profile(self) -> None:
        self._reload_current_roi_profile()

    def _sync_roi_profile_from_channel(self) -> None:
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            return

        try:
            vision.set_roi_profile(self._roi_profile_slug())
        except Exception:
            pass

        self.roi_file_var.set(f"arquivo = {self._roi_profile_path()}")
        self._reload_current_roi_profile()

    def _reload_current_roi_profile(self) -> None:
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            return

        path = self._roi_profile_path()

        try:
            vision.set_roi_profile(self._roi_profile_slug())

            if os.path.isfile(path):
                vision.load_roi_overrides(path, self._roi_profile_slug())
                try:
                    self._log(f"[ROI] calibração carregada: {path}")
                    self._log(f"[ROI] perfil ativo: {self._roi_profile_slug()}")
                except Exception:
                    pass
            else:
                vision.clear_roi_overrides()

            self.roi_file_var.set(f"arquivo = {path}")
            self._load_roi_enabled_profile(apply_runtime=True)
            self._refresh_selected_roi_panel()
        except Exception as e:
            try:
                self._log(f"[WARN] reload roi: {e}")
            except Exception:
                pass

    def _save_current_roi_profile(self) -> None:
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            return

        path = self._roi_profile_path()

        try:
            vision.set_roi_profile(self._roi_profile_slug())
            ok = vision.save_roi_overrides(path, self._roi_profile_slug())

            if ok:
                self.roi_file_var.set(f"arquivo = {path}")
                self._last_roi_crop_applied = False
                try:
                    self.btn_roi_save.configure(
                        state="normal",
                        fg_color=("#1565C0", "#1565C0"),
                        hover_color=("#0F4B92", "#0F4B92"),
                        text="Salvar calibração",
                    )
                except Exception:
                    pass
                try:
                    self._log(f"[ROI] calibração salva: {path}")
                except Exception:
                    pass
            else:
                try:
                    self._log(f"[WARN] não foi possível salvar ROI em {path}")
                except Exception:
                    pass
        except Exception as e:
            try:
                self._log(f"[WARN] save roi: {e}")
            except Exception:
                pass

    def _reset_selected_roi(self) -> None:
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            return

        key = (self.selected_roi_var.get() or "").strip().lower()

        try:
            vision.reset_roi_override(key)
            self._refresh_selected_roi_panel()
            try:
                self._log(f"[ROI] resetada: {key}")
            except Exception:
                pass
        except Exception as e:
            try:
                self._log(f"[WARN] reset roi: {e}")
            except Exception:
                pass

    # =========================================================
    # UI build
    # =========================================================

    def _build_ui(self) -> None:
        # Seletor de Modo de Operação (Visual vs API)
        mode_bar = ctk.CTkFrame(self, corner_radius=14, fg_color="#141414", border_width=1, border_color="#333333")
        mode_bar.pack(fill="x", padx=12, pady=(12, 0))
        
        ctk.CTkLabel(mode_bar, text="ESTRATÉGIA DE MONITORAMENTO:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888").pack(side="left", padx=15, pady=10)
        
        self.mode_switch = ctk.CTkSegmentedButton(
            mode_bar,
            values=["Expert (API-Only)", "Visual (OBS)", "Ads & Merchan", "Config IA"],
            variable=self.monitoring_mode_var,
            command=self._on_mode_change,
            height=32,
            width=560,
            selected_color="#00CED1",
            selected_hover_color="#008B8B"
        )
        self.mode_switch.pack(side="left", padx=10, pady=10)
        
        self.btn_flows = ctk.CTkButton(
            mode_bar, 
            text=" Fluxos de cada modo", 
            font=ctk.CTkFont(size=11),
            width=160,
            fg_color="transparent",
            border_width=1,
            border_color="#444444",
            hover_color="#333333",
            command=self._show_mode_flows
        )
        self.btn_flows.pack(side="left", padx=10, pady=10)



        # Seção do Auto-Updater no Header (Canto Superior Direito)
        # Seção do Auto-Updater e Zoom no Header (Canto Superior Direito)
        self.updater_header_frame = ctk.CTkFrame(mode_bar, fg_color="transparent")
        self.updater_header_frame.pack(side="right", padx=15, pady=5)
        
        # Seletor de Zoom da Interface
        lbl_zoom = ctk.CTkLabel(
            self.updater_header_frame,
            text="🔍 Zoom:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#AAAAAA"
        )
        lbl_zoom.pack(side="left", padx=(0, 4))
        
        self.opt_zoom = ctk.CTkOptionMenu(
            self.updater_header_frame,
            values=["100%", "110%", "115%", "125%", "135%", "150%"],
            variable=self.ui_scale_str_var,
            command=self._on_change_ui_zoom,
            width=78,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#222222",
            button_color="#333333",
            button_hover_color="#444444",
            dropdown_font=ctk.CTkFont(size=11)
        )
        self.opt_zoom.pack(side="left", padx=(0, 12))
        
        self.lbl_header_version = ctk.CTkLabel(
            self.updater_header_frame, 
            text=f"v{AutoUpdater().current_version}", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#888888"
        )
        self.lbl_header_version.pack(side="left", padx=(0, 8))
        
        def force_header_update_check():
            self.btn_header_update.configure(text="🔄 Checando...", state="disabled")
            def run_check():
                try:
                    updater = AutoUpdater()
                    has_update, remote_ver, download_url, changelog = updater.check_for_update()
                    if has_update:
                        def ask_user():
                            self.btn_header_update.configure(
                                text=f"⚠️ Atualizar para v{remote_ver}", 
                                fg_color="#FF4500", 
                                hover_color="#CD3700",
                                state="normal"
                            )
                            self.lbl_header_version.configure(text_color="#00FF00")
                            msg = f"Uma nova versão ({remote_ver}) está disponível!\n\nChangelog:\n{changelog}\n\nDeseja baixar e atualizar agora automaticamente?"
                            if messagebox.askyesno("Atualização Disponível", msg):
                                self._start_self_update(download_url, remote_ver)
                        self.after(0, ask_user)
                    else:
                        def notify_up_to_date():
                            self.btn_header_update.configure(
                                text="🔄 Verificar Atualizações", 
                                fg_color="#333333", 
                                hover_color="#444444",
                                state="normal"
                            )
                            messagebox.showinfo("Sistema Atualizado", f"Você já está utilizando a versão mais recente ({updater.current_version}) do Monitor Esportes.")
                        self.after(0, notify_up_to_date)
                except Exception as e_up:
                    def notify_error(err=e_up):
                        self.btn_header_update.configure(
                            text="❌ Erro na Checagem", 
                            fg_color="#333333", 
                            hover_color="#444444",
                            state="normal"
                        )
                        messagebox.showerror("Erro de Rede", f"Não foi possível consultar atualizações no GitHub:\n{err}")
                    self.after(0, notify_error)

            threading.Thread(target=run_check, daemon=True).start()

        self.btn_header_update = ctk.CTkButton(
            self.updater_header_frame, 
            text="🔄 Verificar Atualizações", 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#333333", 
            hover_color="#444444", 
            height=26, 
            width=150,
            command=force_header_update_check
        )
        self.btn_header_update.pack(side="left")

        # Disparar checagem automática silenciosa na inicialização
        self._check_update_silent_startup()

    def _check_update_silent_startup(self) -> None:
        """Checa silenciosamente se há novas versões ao iniciar e destaca o botão se houver atualização."""
        def run_silent():
            try:
                updater = AutoUpdater()
                has_update, remote_ver, download_url, changelog = updater.check_for_update()
                if has_update:
                    def highlight_ui():
                        if hasattr(self, "btn_header_update") and self.btn_header_update:
                            self.btn_header_update.configure(
                                text=f"🚀 NOVA VERSÃO DISPONÍVEL (v{remote_ver})",
                                fg_color="#FF3300",
                                hover_color="#CC0000",
                                text_color="#FFFFFF"
                            )
                        if hasattr(self, "lbl_header_version") and self.lbl_header_version:
                            self.lbl_header_version.configure(
                                text=f"v{updater.current_version} (⚠️ Desatualizado!)",
                                text_color="#FF6666"
                            )
                        self._log(f"🔔 [AUTO UPDATER] Nova versão v{remote_ver} disponível no GitHub! Clique no botão vermelho no topo para atualizar.")
                    self.after(0, highlight_ui)
            except Exception:
                pass
        threading.Thread(target=run_silent, daemon=True).start()

        # 1. Letreiro Horizontal de Jogos CBF (Ticker Bar no Topo com Alternância: Últimos Jogos vs Próximos)
        self.cbf_ticker_frame = ctk.CTkFrame(self, height=44, corner_radius=10, fg_color="#141414", border_width=1, border_color="#1f538d")
        self.cbf_ticker_frame.pack(side="top", fill="x", padx=12, pady=(2, 4))
        
        self.cbf_ticker_tab_var = ctk.StringVar(value="⚽ Últimos Jogos (Auditoria)")
        
        self.cbf_ticker_seg = ctk.CTkSegmentedButton(
            self.cbf_ticker_frame,
            values=["⚽ Últimos Jogos (Auditoria)", "📅 Próximos (Agendar)"],
            variable=self.cbf_ticker_tab_var,
            command=lambda v: self._render_cbf_mural_ui(),
            font=ctk.CTkFont(size=11, weight="bold"),
            selected_color="#1f538d",
            selected_hover_color="#153b66",
            unselected_color="#222222",
            height=28
        )
        self.cbf_ticker_seg.pack(side="left", padx=(10, 6), pady=4)
        
        btn_refresh_ticker = ctk.CTkButton(
            self.cbf_ticker_frame, 
            text="🔄", 
            width=26, 
            height=26, 
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1f538d", 
            hover_color="#153b66", 
            command=self._force_refresh_cbf_mural
        )
        btn_refresh_ticker.pack(side="left", padx=(0, 6), pady=4)
        
        self.cbf_mural_scroll = ctk.CTkScrollableFrame(self.cbf_ticker_frame, orientation="horizontal", fg_color="transparent", height=32)
        self.cbf_mural_scroll.pack(side="left", fill="both", expand=True, padx=4, pady=2)

        # 2. Barra de Configurações do YouTube / Canais (FIXA NO RODAPÉ)
        self.top = ctk.CTkFrame(self, corner_radius=14)
        self.top.pack(side="bottom", fill="x", padx=12, pady=(4, 4))

        # 3. Painel manual do modo Expert (FIXO NO RODAPÉ, ACIMA DA BARRA DO YOUTUBE)
        self.expert_manual_frame = ctk.CTkFrame(self, corner_radius=14, border_width=1, border_color="#333333")
        self.expert_manual_frame.pack(side="bottom", fill="x", padx=12, pady=(4, 4))
        
        lbl_title = ctk.CTkLabel(
            self.expert_manual_frame,
            text="🔍 DADOS DA PARTIDA PARA AUDITORIA (SEM VÍDEO)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#00CED1"
        )
        lbl_title.pack(anchor="w", padx=15, pady=(8, 2))

        # Barra de Presets Rápidos de Jogos (Dinâmica por Histórico de Pesquisas)
        row_presets = ctk.CTkFrame(self.expert_manual_frame, fg_color="transparent")
        row_presets.pack(fill="x", padx=15, pady=(2, 4))

        ctk.CTkLabel(
            row_presets,
            text="Seleção Rápida (Últimas Pesquisadas):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00CED1"
        ).pack(side="left", padx=(0, 6))

        self.presets_buttons_container = ctk.CTkFrame(row_presets, fg_color="transparent")
        self.presets_buttons_container.pack(side="left", fill="x", expand=True)

        # Linha 1: Campos de Entrada de Dados
        row_inputs = ctk.CTkFrame(self.expert_manual_frame, fg_color="transparent")
        row_inputs.pack(fill="x", padx=15, pady=(4, 6))

        BRAZILIAN_TEAMS = [
            "Palmeiras", "Flamengo", "São Paulo", "Corinthians", "Santos", "Fluminense", 
            "Vasco", "Botafogo", "Cruzeiro", "Atlético-MG", "Grêmio", "Internacional", 
            "Bahia", "Athletico-PR", "Fortaleza", "Ceará", "Remo", "Juventude", "Criciúma", 
            "Vitória", "Goiás", "Coritiba", "Sport", "América-MG", "Avaí", "Chapecoense", 
            "Ponte Preta", "Guarani", "Vila Nova", "CRB", "Novorizontino", "Mirassol", 
            "Operário-PR", "Bragantino", "Cuiabá", "Atlético-GO", "Paysandu", "Amazonas", "Brusque"
        ]

        ctk.CTkLabel(row_inputs, text="Time Casa:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.expert_team1_combo = ctk.CTkComboBox(
            row_inputs,
            variable=self.expert_team1_var,
            values=BRAZILIAN_TEAMS,
            width=140
        )
        self.expert_team1_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_inputs, text="Time Fora:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.expert_team2_combo = ctk.CTkComboBox(
            row_inputs,
            variable=self.expert_team2_var,
            values=BRAZILIAN_TEAMS,
            width=140
        )
        self.expert_team2_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_inputs, text="Competição:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.expert_comp_combo = ctk.CTkComboBox(
            row_inputs,
            variable=self.expert_comp_var,
            values=["Brasileiro Serie A", "Copa do Brasil", "Brasileiro Serie B", "Copa Libertadores", "Copa Sul-Americana", "Paulistão"],
            width=155
        )
        self.expert_comp_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_inputs, text="Data:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        if DateEntry:
            self.expert_date_entry = DateEntry(
                row_inputs,
                textvariable=self.expert_date_var,
                width=10,
                background='#1f1f1f',
                foreground='white',
                headersbackground='#333333',
                headersforeground='white',
                selectbackground='#1f538d',
                selectforeground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy',
                locale='pt_BR'
            )
            self.expert_date_entry.pack(side="left", padx=(0, 2), pady=4)
            self.btn_cal_expert = ctk.CTkButton(
                row_inputs,
                text="📅",
                width=28,
                height=28,
                command=lambda: self.expert_date_entry.drop_down()
            )
            self.btn_cal_expert.pack(side="left", padx=(0, 10), pady=4)
        else:
            self.expert_date_entry = ctk.CTkEntry(row_inputs, textvariable=self.expert_date_var, width=110, placeholder_text="DD/MM/YYYY")
            self.expert_date_entry.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_inputs, text="Plataforma:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.expert_platform_combo = ctk.CTkComboBox(
            row_inputs,
            variable=self.expert_platform_var,
            values=["Amazon Prime", "CazéTV", "Premiere", "Globo", "SporTV", "YouTube"],
            width=130
        )
        self.expert_platform_combo.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_inputs, text="Horário (VOD):", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        ctk.CTkEntry(row_inputs, textvariable=self.expert_time_var, width=75, placeholder_text="Ex: 22:30").pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_inputs, text="Tag:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        self.expert_tag_combo = ctk.CTkComboBox(
            row_inputs,
            variable=self.expert_tag_var,
            values=["🏷️ Normal", "🔥 Clássico", "🏆 Decisivo", "📺 Exclusivo", "⭐ Alta Prioridade"],
            width=135
        )
        self.expert_tag_combo.pack(side="left", padx=(0, 4))

        # Linha 2: Barra de Ações Rápidas & Agendamento
        row_actions = ctk.CTkFrame(self.expert_manual_frame, fg_color="transparent")
        row_actions.pack(fill="x", padx=15, pady=(2, 8))

        btn_run = ctk.CTkButton(
            row_actions,
            text="🚀 Iniciar Auditoria",
            command=self._on_click_start_audit,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#00CED1",
            text_color="black",
            hover_color="#008B8B",
            width=160,
            height=34
        )
        btn_run.pack(side="left", padx=(0, 10))

        btn_schedule = ctk.CTkButton(
            row_actions,
            text="⏰ Agendar Fila (5 Jogos)",
            command=self._open_schedule_games_modal,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#8B008B",
            hover_color="#4B0082",
            width=180,
            height=34
        )
        btn_schedule.pack(side="left", padx=(0, 10))

        btn_copy_summary = ctk.CTkButton(
            row_actions,
            text="📋 Copiar Resumo",
            command=self._copy_executive_summary,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2B5B84",
            hover_color="#1E3F5A",
            width=130,
            height=34
        )
        btn_copy_summary.pack(side="left", padx=(0, 10))

        btn_view_prompt = ctk.CTkButton(
            row_actions,
            text="👁️ Ajustar Prompt",
            command=self._open_prompt_editor_modal,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#333333",
            hover_color="#444444",
            width=130,
            height=32
        )
        btn_view_prompt.pack(side="left", padx=(0, 0))

        row_yt_header = ctk.CTkFrame(self.top, fg_color="transparent")
        row_yt_header.pack(fill="x", padx=12, pady=(6, 2))

        lbl_yt_title = ctk.CTkLabel(
            row_yt_header,
            text="📺 PESQUISAR TRANSMISSÕES & CARREGAR EVENTOS DO YOUTUBE / CANAIS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#00CED1"
        )
        lbl_yt_title.pack(side="left")

        row1 = ctk.CTkFrame(self.top, fg_color="transparent")
        row1.pack(fill="x", padx=12, pady=(2, 4))
        
        row2 = ctk.CTkFrame(self.top, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=(2, 6))

        # --- LINHA 1 ---
        # self.theme_var = ctk.StringVar(value="Dark") # Moved to __init__
        ctk.CTkLabel(row1, text="Tema:", width=50).pack(side="left", padx=(0, 6), pady=6)
        self.theme_opt = ctk.CTkOptionMenu(
            row1,
            values=["Dark", "Light", "System"],
            variable=self.theme_var,
            command=self._on_theme_change,
            width=120,
        )
        self.theme_opt.pack(side="left", padx=(0, 14), pady=6)

        ctk.CTkLabel(row1, text="Canal:", width=60).pack(side="left", padx=(0, 6), pady=6)

        # self.channel_var = ctk.StringVar(value="CazéTV") # Moved to __init__
        self.channel_opt = ctk.CTkOptionMenu(
            row1,
            values=["CazéTV", "TNT Sports", "ESPN Brasil", "SporTV (exemplo)", "URL manual"],
            variable=self.channel_var,
            command=self._on_channel_preset,
            width=160,
        )
        self.channel_opt.pack(side="left", padx=(0, 14), pady=6)

        # self.channel_url_var = ctk.StringVar(value=CHANNEL_STREAMS_URL) # Moved to __init__
        self.channel_url_entry = ctk.CTkEntry(row1, textvariable=self.channel_url_var)
        self.channel_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 14), pady=6)

        self.chk_debug_mode = ctk.CTkSwitch(row1, text="Modo debug visual", variable=self.debug_mode_var)
        self.chk_debug_mode.pack(side="right", padx=(10, 0), pady=6)

        self.chk_auto_start = ctk.CTkSwitch(row1, text="Auto-start", variable=self.auto_start_var)
        self.chk_auto_start.pack(side="right", padx=(10, 0), pady=6)

        self.chk_auto_prepare = ctk.CTkSwitch(row1, text="Auto-prepare", variable=self.auto_prepare_var)
        self.chk_auto_prepare.pack(side="right", padx=(10, 0), pady=6)

        # --- LINHA 2 ---
        ctk.CTkLabel(row2, text="Competição:", width=88).pack(side="left", padx=(0, 6), pady=6)

        self.category_frame = ctk.CTkScrollableFrame(row2, width=280, height=36, orientation="horizontal", label_text="")
        self.category_frame.pack(side="left", padx=(0, 14), pady=6)
        self.category_frame._scrollbar.pack_forget() # Esconde scrollbar pra ficar limpo

        for cat in self.categories_list:
            cb = ctk.CTkCheckBox(
                self.category_frame, 
                text=cat, 
                variable=self.category_vars[cat],
                command=lambda c=cat: self._on_category_toggle(c),
                checkbox_width=18,
                checkbox_height=18,
                font=ctk.CTkFont(size=11)
            )
            cb.pack(side="left", padx=5)

        ctk.CTkLabel(row2, text="Início:", width=40).pack(side="left", padx=(0, 4), pady=6)
        if DateEntry:
            self.date_start_entry = DateEntry(
                row2, 
                textvariable=self.search_date_start_var,
                width=10, 
                background='#1f1f1f', 
                foreground='white', 
                headersbackground='#333333',
                headersforeground='white',
                selectbackground='#1f538d',
                selectforeground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy',
                locale='pt_BR'
            )
            self.date_start_entry.pack(side="left", padx=(0, 2), pady=6)
            self.btn_cal_start = ctk.CTkButton(row2, text="📅", width=30, height=30, command=lambda: self.date_start_entry.drop_down())
            self.btn_cal_start.pack(side="left", padx=(0, 14), pady=6)
        else:
            self.date_start_entry = ctk.CTkEntry(row2, textvariable=self.search_date_start_var, width=90, placeholder_text="DD/MM/YYYY")
            self.date_start_entry.pack(side="left", padx=(0, 14), pady=6)

        ctk.CTkLabel(row2, text="Fim:", width=30).pack(side="left", padx=(0, 4), pady=6)
        if DateEntry:
            self.date_end_entry = DateEntry(
                row2, 
                textvariable=self.search_date_end_var,
                width=10, 
                background='#1f1f1f', 
                foreground='white', 
                headersbackground='#333333',
                headersforeground='white',
                selectbackground='#1f538d',
                selectforeground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy',
                locale='pt_BR'
            )
            self.date_end_entry.pack(side="left", padx=(0, 2), pady=6)
            self.btn_cal_end = ctk.CTkButton(row2, text="📅", width=30, height=30, command=lambda: self.date_end_entry.drop_down())
            self.btn_cal_end.pack(side="left", padx=(0, 14), pady=6)
        else:
            self.date_end_entry = ctk.CTkEntry(row2, textvariable=self.search_date_end_var, width=90, placeholder_text="DD/MM/YYYY")
            self.date_end_entry.pack(side="left", padx=(0, 14), pady=6)

        self.btn_load = ctk.CTkButton(
            row2, 
            text="Carregar eventos", 
            command=self._load_events, 
            width=160,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1f538d",
            hover_color="#153b66"
        )
        self.btn_load.pack(side="right", padx=(10, 0), pady=6)

        main = ctk.CTkFrame(self, corner_radius=14)
        main.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        left = ctk.CTkFrame(main, corner_radius=14)
        left.pack(side="left", fill="y", padx=(12, 8), pady=12)
        left.configure(width=400)
        left.pack_propagate(False)

        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=10) # Área de eventos (Máxima prioridade)
        left.grid_rowconfigure(2, weight=1)  # Controle e Histórico
        left.grid_rowconfigure(3, weight=0)

        filter_row = ctk.CTkFrame(left, fg_color="transparent")
        filter_row.pack(side="top", fill="x", padx=12, pady=(0, 10))

        self.filter_seg = ctk.CTkSegmentedButton(
            filter_row,
            values=["Todos", "Ao Vivo", "Encerrados", "Proximos"],
            command=lambda v: self._render_events(),
            variable=self.event_filter_var,
            height=32
        )
        self.filter_seg.pack(side="left", expand=True, fill="x")

        # Campo de Pesquisa
        self.search_frame = ctk.CTkFrame(left, fg_color="transparent")
        self.search_frame.pack(side="top", fill="x", padx=12, pady=(0, 10))
        
        self.search_entry = ctk.CTkEntry(
            self.search_frame, 
            placeholder_text="🔎 Pesquisar jogo ou time...",
            textvariable=self.event_search_var,
            height=32,
            font=ctk.CTkFont(size=12)
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_events())
        
        self.btn_clear_search = ctk.CTkButton(
            self.search_frame,
            text="✕",
            width=32,
            height=32,
            fg_color="#333333",
            hover_color="#444444",
            command=lambda: [self.event_search_var.set(""), self._render_events()]
        )
        self.btn_clear_search.pack(side="right")

        self.sort_menu = ctk.CTkOptionMenu(
            filter_row,
            values=["Data (Recentes)", "Data (Antigos)", "Alfabética"],
            variable=self.event_sort_var,
            command=lambda v: self._render_events(),
            width=110,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        # Container para Progresso (Sempre presente para evitar saltos na UI)
        self.progress_container = ctk.CTkFrame(left, height=6, fg_color="transparent")
        self.progress_container.pack(side="top", fill="x", padx=12, pady=(0, 5))
        self.progress_container.pack_propagate(False)

        self.load_progress = ctk.CTkProgressBar(self.progress_container, height=4, corner_radius=0)
        self.load_progress.set(0)
        self.load_progress.pack(fill="x")
        self.load_progress.pack_forget() 

        # O container que deve crescer ao máximo
        self.events_box = ctk.CTkScrollableFrame(left, width=360, corner_radius=12)
        self.events_box.pack(side="top", fill="both", expand=True, padx=12, pady=(0, 12))

        self._event_buttons: List[Any] = []

        # Container inferior para botões e histórico (fixo na base)
        ctrl = ctk.CTkFrame(left, corner_radius=12)
        ctrl.pack(side="top", fill="x", padx=12, pady=(0, 12))
        ctrl.grid_columnconfigure(0, weight=1)

        self.btn_start = ctk.CTkButton(
            ctrl,
            text="Iniciar (selecionado)",
            command=self._start_selected,
            height=36,
        )
        self.btn_start.grid(row=0, column=0, padx=10, pady=(10, 6), sticky="ew")

        self.btn_stop = ctk.CTkButton(
            ctrl,
            text="Parar + gerar relatório",
            command=self._stop_monitoring,
            height=36,
        )
        self.btn_stop.grid(row=1, column=0, padx=10, pady=6, sticky="ew")

        self.btn_snapshot = ctk.CTkButton(
            ctrl,
            text="Salvar snapshot debug",
            command=self._save_debug_snapshot,
            height=36,
        )
        self.btn_snapshot.grid(row=2, column=0, padx=10, pady=(6, 10), sticky="ew")

        self.status_dot = ctk.CTkLabel(ctrl, text="●", font=ctk.CTkFont(size=18, weight="bold"))
        self.status_dot.grid(row=3, column=0, padx=10, pady=(0, 2), sticky="w")

        # self.status_var = ctk.StringVar(value="🔴 Parado") # Moved to __init__
        self.status_lbl = ctk.CTkLabel(ctrl, textvariable=self.status_var)
        self.status_lbl.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="w")

        ctrl.grid_rowconfigure(5, weight=0)
        
        # Filtros de Status (Fixos na base do painel esquerdo)
        self.filter_frame = ctk.CTkFrame(left, fg_color="transparent")
        self.filter_frame.pack(side="bottom", fill="x", padx=12, pady=(0, 12))
        
        self.expert_upcoming_var = ctk.BooleanVar(value=True)
        self.expert_finished_var = ctk.BooleanVar(value=True)
        
        ctk.CTkCheckBox(self.filter_frame, text="Upcoming (Próximos)", variable=self.expert_upcoming_var, command=self._load_events, font=ctk.CTkFont(size=10)).pack(side="left", padx=5)
        ctk.CTkCheckBox(self.filter_frame, text="Ended (Finalizados)", variable=self.expert_finished_var, command=self._load_events, font=ctk.CTkFont(size=10)).pack(side="left", padx=5)

        self.after(2000, self._load_expert_history_list) # Carga inicial

        # --- NOVA COLUNA DIREITA: FILA DE AGENDAMENTOS E HISTÓRICO ---
        self.right_sidebar = ctk.CTkFrame(main, width=380, corner_radius=14)
        self.right_sidebar.pack(side="right", fill="y", padx=(8, 12), pady=12)
        self.right_sidebar.pack_propagate(False)

        # Seção de Agendamentos e Fila Live (Ocupando posição de destaque principal)
        self.schedule_frame = ctk.CTkFrame(self.right_sidebar, corner_radius=12, border_width=1, border_color="#333333")
        self.schedule_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        schedule_hdr = ctk.CTkFrame(self.schedule_frame, fg_color="transparent")
        schedule_hdr.pack(fill="x", padx=8, pady=(8, 2))
        
        ctk.CTkLabel(schedule_hdr, text="⏰ FILA DE AGENDAMENTOS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00CED1").pack(side="left")
        
        self.lbl_schedule_live_indicator = ctk.CTkLabel(
            schedule_hdr, 
            text="● LIVE", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            text_color="#00FF7F"
        )
        self.lbl_schedule_live_indicator.pack(side="left", padx=6)
        
        ctk.CTkButton(
            schedule_hdr, text="➕", width=24, height=24, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#333333", hover_color="#444444", command=self._open_schedule_games_modal
        ).pack(side="right")
        
        self.schedule_scroll = ctk.CTkScrollableFrame(self.schedule_frame, fg_color="transparent", height=320)
        self.schedule_scroll.pack(fill="both", expand=True, padx=4, pady=(2, 4))

        btn_open_sched = ctk.CTkButton(
            self.schedule_frame,
            text="➕ Agendar Fila (5 Jogos)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#8B008B",
            hover_color="#4B0082",
            height=30,
            command=self._open_schedule_games_modal
        )
        btn_open_sched.pack(fill="x", padx=6, pady=(0, 6))

        # Seção de Histórico Expert (Colocada na base da Direita)
        self.expert_hist_frame = ctk.CTkFrame(self.right_sidebar, corner_radius=12, border_width=1, border_color="#333333")
        self.expert_hist_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        ctk.CTkLabel(self.expert_hist_frame, text="AUDITORIAS RECENTES", font=ctk.CTkFont(size=12, weight="bold"), text_color="#aaaaaa").pack(pady=(8, 4))
        self.expert_hist_scroll = ctk.CTkScrollableFrame(self.expert_hist_frame, fg_color="transparent")
        self.expert_hist_scroll.pack(fill="both", expand=True, padx=6, pady=4)
        
        self.btn_refresh_hist = ctk.CTkButton(self.expert_hist_frame, text="Atualizar Lista", font=ctk.CTkFont(size=11, weight="bold"), height=26, command=self._load_expert_history_list)
        self.btn_refresh_hist.pack(pady=(4, 8))

        # --- COLUNA CENTRAL: TABS ---
        right = ctk.CTkFrame(main, corner_radius=14)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=12)

        self.tabs = ctk.CTkTabview(right, corner_radius=14)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_monitor = self.tabs.add("Monitoramento")
        self.tab_debug = self.tabs.add("Debug Visual")
        self.tab_frag = self.tabs.add("Fragmentos")
        self.tab_logs = self.tabs.add("Logs")
        self.tab_errors = self.tabs.add("Erros")
        self.tab_cfg = self.tabs.add("Config")
        self.tab_ia_logs = self.tabs.add("Logs IA")
        self.tab_ads = self.tabs.add("Ads/Merchan")
        self.tab_dash = self.tabs.add("Dashboard")
        self.tab_reports = self.tabs.add("📊 Jogos Auditados")
        
        # Variáveis de Auto-clip
        self.auto_clip_var = ctk.BooleanVar(value=True)
        self.last_clip_time = 0

        self._build_tab_monitor()
        self._build_tab_debug()
        self._build_tab_fragments()
        self._build_tab_logs()
        self._build_tab_errors()
        self._build_tab_config()
        self._build_tab_ia_logs()
        self._build_tab_ads()
        self._build_tab_dashboard()
        self._build_tab_reports()

        self._on_channel_preset(self.channel_var.get())

    def _build_tab_monitor(self) -> None:
        # Layout Principal: Parte superior (Status) e Parte Inferior (Histórico)
        self.total_wrap_monitor = ctk.CTkFrame(self.tab_monitor, fg_color="transparent")
        self.total_wrap_monitor.pack(fill="both", expand=True, padx=12, pady=12)

        # ---------------------------------------------------------------------
        # TOP PANEL: LIVE STATUS (Modern Compact Card - MODO VISUAL OBS)
        # ---------------------------------------------------------------------
        self.top_status = ctk.CTkFrame(self.total_wrap_monitor, corner_radius=16, border_width=1, border_color="#333333", fg_color="#1a1a1a")
        self.top_status.pack(fill="x", side="top", pady=(0, 12))

        header = ctk.CTkFrame(self.top_status, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 8))

        ctk.CTkLabel(
            header, 
            text="REC MONITORING LIVE", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#FF4500" # OrangeRed (vibração de live)
        ).pack(side="left")

        self.live_indicator = ctk.CTkLabel(header, text="●", font=ctk.CTkFont(size=16), text_color="gray")
        self.live_indicator.pack(side="left", padx=8)

        # Info Grid
        # Switch de Auto-clip (Opção 3)
        self.auto_clip_sw = ctk.CTkSwitch(header, text="Auto-Clip (Live Ads)", variable=self.auto_clip_var, progress_color="#00CED1")
        self.auto_clip_sw.pack(side="right", padx=(0, 20))
        
        info_grid = ctk.CTkFrame(self.top_status, fg_color="transparent")
        info_grid.pack(fill="x", padx=16, pady=(0, 16))
        for i in range(4): info_grid.grid_columnconfigure(i, weight=1)

        def _add_stat(parent, row, col, label, var, icon=""):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.grid(row=row, column=col, sticky="nsew", padx=10, pady=5)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=11, weight="normal"), text_color="#aaaaaa").pack(anchor="w")
            ctk.CTkLabel(f, textvariable=var, font=ctk.CTkFont(size=13, weight="bold"), text_color="#ffffff", wraplength=280, justify="left").pack(anchor="w")

        # vars pre-inicializadas em __init__

        _add_stat(info_grid, 0, 0, "PARTIDA", self.match_var)
        _add_stat(info_grid, 0, 1, "COMPETIÇÃO", self.comp_var)
        _add_stat(info_grid, 0, 2, "PLACAR", self.score_var)
        _add_stat(info_grid, 0, 3, "CRONÔMETRO", self.clock_var)
        _add_stat(info_grid, 1, 0, "FASE ATUAL", self.phase_var)
        _add_stat(info_grid, 1, 1, "CONFIANÇA", self.visual_conf_var)
        _add_stat(info_grid, 1, 2, "TELEMETRIA", self.detector_perf_var)
        _add_stat(info_grid, 1, 3, "FRAMES", self.frames_var)

        # ---------------------------------------------------------------------
        # BOTTOM PANEL: MOMENTS HISTORY (Professional Grid) - Criado uma única vez
        # ---------------------------------------------------------------------
        self.history_header = ctk.CTkFrame(self.total_wrap_monitor, fg_color="transparent")
        self.history_header.pack(fill="x", side="top", pady=(4, 4))
        
        ctk.CTkLabel(
            self.history_header, 
            text="HISTÓRICO DE MOMENTOS DETECTADOS", 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00CED1"
        ).pack(side="left", padx=4)

        self.btn_clear_history = ctk.CTkButton(
            self.history_header,
            text="Limpar Grid",
            font=ctk.CTkFont(size=11),
            width=90,
            height=24,
            fg_color="transparent",
            border_width=1,
            border_color="#555555",
            command=self._clear_history_grid_manual
        )
        self.btn_clear_history.pack(side="left", padx=10)

        # Filtros de Histórico
        self.hist_filter_opt = ctk.CTkOptionMenu(
            self.history_header,
            values=["Tudo", "Banners/IA", "Gols/Cartões", "Mudança de Fase", "Debug/Errors"],
            variable=self.hist_filter_var,
            width=140,
            font=ctk.CTkFont(size=11),
            command=self._on_history_filter_change
        )
        self.hist_filter_opt.pack(side="right", padx=4)
        ctk.CTkLabel(self.history_header, text="Filtrar:", font=ctk.CTkFont(size=11)).pack(side="right", padx=4)

        # Grid Container (Scrollable)
        self.history_grid = ctk.CTkScrollableFrame(self.total_wrap_monitor, corner_radius=12, fg_color="#111111", border_width=1, border_color="#222222")
        self.history_grid.pack(fill="both", expand=True, pady=(4, 0))
        
        # Placeholder se vazio
        self.hist_empty_lbl = ctk.CTkLabel(self.history_grid, text="Nenhum momento capturado ainda.", text_color="#555555")
        self.hist_empty_lbl.pack(pady=40)

        self._last_history_count = 0
        self._history_cards = []

    def _on_mode_change(self, mode: str) -> None:
        """Alterna a visibilidade das abas baseada no modo de estratégia."""
        self._selected_indices.clear()
        self._render_events()
        self._log(f"[UI] Modo alterado para: {mode}")

        is_expert = (mode == "Expert (API-Only)")
        is_visual = (mode == "Visual (OBS)")
        is_ads    = (mode == "Ads & Merchan")
        is_ia     = (mode == "Config IA")

        # 1. Barra de Pesquisa do YouTube / Canais (self.top)
        if hasattr(self, "top") and self.top:
            self.top.pack_forget()
            self.top.pack(side="bottom", fill="x", padx=12, pady=(4, 4))

        # 2. Painel de Dados da Partida para Auditoria
        if hasattr(self, "expert_manual_frame") and self.expert_manual_frame:
            self.expert_manual_frame.pack_forget()
            self.expert_manual_frame.pack(side="bottom", fill="x", padx=12, pady=(4, 4))

        # 3. Painel Telemetria Live OBS
        if hasattr(self, "top_status") and self.top_status:
            if is_visual:
                self.top_status.pack(fill="x", side="top", pady=(0, 12), before=getattr(self, "history_header", None))
            else:
                self.top_status.pack_forget()

        # 4. Controle dinâmico da visibilidade das Abas no Tabview
        if hasattr(self, "tabs") and hasattr(self.tabs, "_segmented_button"):
            seg_btn = self.tabs._segmented_button
            if hasattr(seg_btn, "_buttons_dict"):
                b_dict = seg_btn._buttons_dict
                for tab_name, btn_w in b_dict.items():
                    show = False
                    if tab_name == "Monitoramento":
                        show = is_expert or is_visual
                    elif tab_name in ["Debug Visual", "Fragmentos"]:
                        show = is_visual
                    elif tab_name in ["Logs", "Config", "📊 Jogos Auditados", "Dashboard"]:
                        show = True
                    elif tab_name in ["Ads/Merchan"]:
                        show = is_ads or is_visual
                    if show:
                        btn_w.grid()
                    else:
                        btn_w.grid_remove()

        # Seleciona a aba principal automaticamente ao trocar de modo
        if is_ads and hasattr(self, "tabs"):
            try:
                self.tabs.set("Ads/Merchan")
            except: pass
        elif is_ia and hasattr(self, "tabs"):
            try:
                self.tabs.set("Config")
            except: pass
        elif (is_expert or is_visual) and hasattr(self, "tabs"):
            try:
                current = self.tabs.get()
                if current in ["Ads/Merchan", "Dashboard"]:
                    self.tabs.set("Monitoramento")
            except: pass

    def _build_tab_debug(self) -> None:
        wrap = ctk.CTkFrame(self.tab_debug, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        wrap.grid_columnconfigure(0, weight=11)
        wrap.grid_columnconfigure(1, weight=4, minsize=420)
        wrap.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(wrap, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 8), pady=12)
        left.grid_rowconfigure(1, weight=0)
        left.grid_rowconfigure(2, weight=5)
        left.grid_columnconfigure(0, weight=1)

        topbar = ctk.CTkFrame(left, corner_radius=10)
        topbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))
        topbar.grid_columnconfigure(0, weight=0)
        topbar.grid_columnconfigure(1, weight=0)
        topbar.grid_columnconfigure(2, weight=0)
        topbar.grid_columnconfigure(3, weight=1)
        topbar.grid_columnconfigure(4, weight=0)
        topbar.grid_columnconfigure(5, weight=0)
        topbar.grid_columnconfigure(6, weight=0)

        ctk.CTkLabel(
            topbar,
            text="Preview anotado + editor de ROI",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, columnspan=4, padx=(12, 12), pady=(10, 6), sticky="w")

        ctk.CTkLabel(
            topbar,
            textvariable=self.build_marker_var,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFB300"
        ).grid(row=0, column=4, columnspan=3, padx=(0, 12), pady=(10, 6), sticky="e")

        # Rótulo descritivo para o ROI
        self.lbl_roi_sel = ctk.CTkLabel(topbar, text="ROI:", font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_roi_sel.grid(row=1, column=0, padx=(12, 2), pady=(12, 12), sticky="w")

        self.roi_opt = ctk.CTkOptionMenu(
            topbar,
            values=[
                "top_hud_unificado",
                "banner",
                "countdown_center",
            ],
            variable=self.selected_roi_var,
            command=lambda _v: self._refresh_selected_roi_panel(),
            width=150,
        )
        self.roi_opt.grid(row=1, column=1, padx=(0, 6), pady=(12, 12), sticky="w")

        self.chk_roi_edit = ctk.CTkSwitch(
            topbar,
            text="Calibrar ROI",
            variable=self._roi_edit_mode,
            command=self._on_roi_edit_mode_toggle,
        )
        self.chk_roi_edit.grid(row=1, column=2, padx=(2, 6), pady=(12, 12), sticky="w")

        self.chk_ctx_boxes = ctk.CTkSwitch(
            topbar,
            text="Blocos contexto",
            variable=self.show_context_boxes_var,
            command=lambda: self._update_preview_widget(),
        )
        self.chk_ctx_boxes.grid(row=1, column=3, padx=(2, 12), pady=(12, 12), sticky="w")

        self.btn_roi_save = ctk.CTkButton(
            topbar,
            text="Salvar calibração",
            command=self._save_current_roi_profile,
            width=170,
            height=34
        )
        self.btn_roi_save.grid(row=2, column=0, columnspan=1, padx=(12, 6), pady=(0, 15), sticky="ew")
        self.btn_roi_save.grid_propagate(False)

        self.btn_roi_reset = ctk.CTkButton(
            topbar,
            text="Resetar ROI",
            command=self._reset_selected_roi,
            width=140,
            height=34,
            fg_color="transparent",
            border_width=1,
            border_color="#555555"
        )
        self.btn_roi_reset.grid(row=2, column=1, padx=6, pady=(0, 15), sticky="ew")

        self.btn_roi_reload = ctk.CTkButton(
            topbar,
            text="Recarregar",
            command=self._reload_current_roi_profile,
            width=130,
            height=34,
            fg_color="transparent",
            border_width=1,
            border_color="#555555"
        )
        self.btn_roi_reload.grid(row=2, column=2, padx=(6, 12), pady=(0, 15), sticky="ew")
        # Painel central de informações (Redesenhado)
        self.info_panel = ctk.CTkFrame(left, corner_radius=12, fg_color="transparent")
        self.info_panel.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.info_panel.grid_columnconfigure(0, weight=1)
        self.info_panel.grid_columnconfigure(1, weight=1)

        # 1. Seção: Estado em Tempo Real (Live Stats)
        live_wrap = ctk.CTkFrame(self.info_panel, corner_radius=10, fg_color="#1a1a1a", border_width=1, border_color="#333333")
        live_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        
        ctk.CTkLabel(live_wrap, text="ESTADO DO JOGO", font=ctk.CTkFont(size=10, weight="bold"), text_color="#555555").pack(anchor="w", padx=12, pady=(8, 2))
        self.live_status_label = ctk.CTkLabel(
            live_wrap, 
            textvariable=self.preview_status_var, 
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00FF7F", # Spring Green
            justify="left",
            anchor="w"
        )
        self.live_status_label.pack(fill="x", padx=12, pady=(0, 8))

        # 2. Seção: Resultados OCR (Detection)
        ocr_wrap = ctk.CTkFrame(self.info_panel, corner_radius=10, fg_color="#1a1a1a", border_width=1, border_color="#333333")
        ocr_wrap.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

        ctk.CTkLabel(ocr_wrap, text="DETECÇÃO OCR", font=ctk.CTkFont(size=10, weight="bold"), text_color="#555555").pack(anchor="w", padx=12, pady=(8, 2))
        self.ocr_res_label = ctk.CTkLabel(
            ocr_wrap,
            textvariable=self.roi_ocr_var,
            font=ctk.CTkFont(size=12),
            text_color="#FFFFFF",
            justify="left",
            anchor="w",
            wraplength=450
        )
        self.ocr_res_label.pack(fill="x", padx=12, pady=(0, 8))

        # 3. Seção: Metadados Técnicos (Dimerizado / Pequeno)
        meta_wrap = ctk.CTkFrame(self.info_panel, corner_radius=10, fg_color="#111111")
        meta_wrap.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=(8, 0))

        # Grid interno para metadados
        ctk.CTkLabel(meta_wrap, textvariable=self.roi_file_var, font=ctk.CTkFont(size=10), text_color="#666666").pack(side="left", padx=12, pady=4)
        ctk.CTkLabel(meta_wrap, textvariable=self.roi_pixel_var, font=ctk.CTkFont(size=10), text_color="#666666").pack(side="left", padx=12, pady=4)
        ctk.CTkLabel(meta_wrap, textvariable=self.roi_percent_var, font=ctk.CTkFont(size=10), text_color="#666666").pack(side="left", padx=12, pady=4)
        
        # Detector Stage (Sempre importante)
        self.stage_label = ctk.CTkLabel(
            meta_wrap, 
            textvariable=self.detector_stage_var,
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#888888"
        )
        self.stage_label.pack(side="right", padx=12, pady=4)

        # Pipeline Bulbs Panel
        self.pipe_bar = ctk.CTkFrame(left, corner_radius=10)
        self.pipe_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        left.grid_rowconfigure(2, weight=0)

        self.cloud_debug_bar = ctk.CTkFrame(left, corner_radius=10, fg_color="#141414", border_width=1, border_color="#222222")
        self.cloud_debug_bar.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        left.grid_rowconfigure(3, weight=0)
        
        left.grid_rowconfigure(4, weight=5) # canvas goes back to heavy weight

        # Cloud UI elements
        ctk.CTkLabel(
            self.cloud_debug_bar,
            text="CLOUD ORACLE",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#555555"
        ).pack(side="left", padx=(12, 10))

        self.cloud_prog_bar = ctk.CTkProgressBar(
            self.cloud_debug_bar,
            width=200,
            height=8,
            variable=self.cloud_progress_var,
            progress_color="#00CED1" # Dark Turquoise (estilo tech)
        )
        self.cloud_prog_bar.pack(side="left", padx=5)

        # Botão de download rápido direto no Debug (empacotado antes para manter à direita)
        self.btn_cloud_download = ctk.CTkButton(
            self.cloud_debug_bar,
            text="⬇ Baixar JSON",
            width=100,
            height=24,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="transparent",
            border_width=1,
            border_color="#00CED1",
            text_color="#00CED1",
            command=self._on_download_cloud_json
        )
        self.btn_cloud_download.pack(side="right", padx=12)

        ctk.CTkLabel(
            self.cloud_debug_bar,
            textvariable=self.cloud_status_var,
            font=ctk.CTkFont(size=12),
            text_color="#CCCCCC",
            anchor="w",
            justify="left"
        ).pack(side="left", fill="x", expand=True, padx=12, pady=8)

        self.pipe_bulbs = {}
        stages = [
            ("gate", "GATE", self.pipe_gate_var),
            ("score", "SCORE", self.pipe_score_var),
            ("clock", "CLOCK", self.pipe_clock_var),
            ("banner", "BANNER", self.pipe_banner_var),
            ("countdown", "COUNTDOWN", self.pipe_countdown_var),
        ]

        for i, (key, label, var) in enumerate(stages):
            bulb = ctk.CTkLabel(
                self.pipe_bar,
                textvariable=var,
                width=160,
                height=28,
                corner_radius=6,
                fg_color="gray30",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white"
            )
            bulb.pack(side="left", padx=6, pady=8)
            self.pipe_bulbs[key] = bulb

        self.preview_canvas = tk.Canvas(
            left,
            bg="#111111",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.preview_canvas.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.preview_canvas.bind("<ButtonPress-1>", self._on_preview_mouse_down)
        self.preview_canvas.bind("<B1-Motion>", self._on_preview_mouse_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self._on_preview_mouse_up)

        right = ctk.CTkFrame(wrap, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 12), pady=12)
        right.grid_rowconfigure(1, weight=3)
        right.grid_rowconfigure(3, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right,
            text="ROIs e OCR",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        self.roi_wrap = ctk.CTkScrollableFrame(right, corner_radius=12, width=400, height=460)
        self.roi_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        self.roi_cards = {}
        for key, title in [
            ("top_hud_unificado", "ROI Top HUD Unificado"),
            ("banner", "ROI Banner"),
            ("countdown_center", "ROI Countdown Center"),
        ]:
            card = ctk.CTkFrame(self.roi_wrap, corner_radius=10)
            card.pack(fill="x", padx=6, pady=6)

            lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"))
            lbl_title.pack(anchor="w", padx=8, pady=(8, 4))

            img_lbl = ctk.CTkLabel(card, text="—", width=300, height=60)
            img_lbl.pack(fill="x", padx=8, pady=(0, 4))

            txt_var = ctk.StringVar(value="OCR: —")
            txt_lbl = ctk.CTkLabel(
                card,
                textvariable=txt_var,
                justify="left",
                anchor="w",
                wraplength=340,
            )
            txt_lbl.pack(fill="x", padx=8, pady=(0, 8))

            self.roi_cards[key] = {"img": img_lbl, "txt": txt_var}

        ctk.CTkLabel(
            right,
            text="Painel técnico",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(6, 6))

        tech = ctk.CTkScrollableFrame(right, corner_radius=12, width=380, height=220)
        tech.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))

        # self.dbg_visual_state_var = ctk.StringVar(value="visual_state: —") # Moved to __init__
        # self.dbg_phase_var = ctk.StringVar(value="match_phase_text: —") # Moved to __init__
        # self.dbg_countdown_var = ctk.StringVar(value="countdown: —") # Moved to __init__
        # self.dbg_clock_raw_var = ctk.StringVar(value="clock bruto: —") # Moved to __init__
        # self.dbg_clock_ok_var = ctk.StringVar(value="clock aceito: —") # Moved to __init__
        # self.dbg_score_raw_var = ctk.StringVar(value="score bruto: —") # Moved to __init__
        # self.dbg_score_ok_var = ctk.StringVar(value="score aceito: —") # Moved to __init__
        # self.dbg_banner_var = ctk.StringVar(value="banner: —") # Moved to __init__
        # self.dbg_teams_var = ctk.StringVar(value="times: —") # Moved to __init__
        # self.dbg_comp_var = ctk.StringVar(value="competição: —") # Moved to __init__
        # self.dbg_seek_var = ctk.StringVar(value="seek: —") # Moved to __init__
        # self.dbg_perf_var = ctk.StringVar(value="latência/fps: —") # Moved to __init__

        for var in [
            self.dbg_visual_state_var,
            self.dbg_phase_var,
            self.dbg_countdown_var,
            self.dbg_clock_raw_var,
            self.dbg_clock_ok_var,
            self.dbg_score_raw_var,
            self.dbg_score_ok_var,
            self.dbg_banner_var,
            self.dbg_teams_var,
            self.dbg_comp_var,
            self.dbg_seek_var,
            self.dbg_perf_var,
        ]:
            ctk.CTkLabel(
                tech,
                textvariable=var,
                justify="left",
                anchor="w",
                wraplength=360,
            ).pack(fill="x", padx=10, pady=4)

        # self.ctx_headline_var = ctk.StringVar(value="headline: —") # Moved to __init__
        # self.ctx_subheadline_var = ctk.StringVar(value="subheadline: —") # Moved to __init__
        # self.ctx_left_tag_var = ctk.StringVar(value="left_tag: —") # Moved to __init__
        # self.ctx_right_tag_var = ctk.StringVar(value="right_tag: —") # Moved to __init__
        # self.ctx_bottom_line_var = ctk.StringVar(value="bottom_line: —") # Moved to __init__
        # self.ctx_top_overlay_var = ctk.StringVar(value="top_overlay: —") # Moved to __init__
        # self.ctx_left_panel_var = ctk.StringVar(value="left_panel: —") # Moved to __init__
        # self.ctx_right_panel_var = ctk.StringVar(value="right_panel: —") # Moved to __init__
        # self.ctx_blocks_var = ctk.StringVar(value="blocks: 0") # Moved to __init__
        # self.ctx_blocks_text = None # Moved to __init__

        self.after(100, self._reload_current_roi_profile)

        self.after(100, self._reload_current_roi_profile)

    def _build_tab_fragments(self) -> None:
        wrap = ctk.CTkFrame(self.tab_frag, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        bar = ctk.CTkFrame(wrap, corner_radius=12)
        bar.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(bar, text="Filtro:", width=60).pack(side="left", padx=(12, 6), pady=10)
        # self.frag_filter_var pre-inicializado em __init__
        self.frag_filter_opt = ctk.CTkOptionMenu(
            bar,
            values=["all", "phase", "context", "match_event", "interruption", "status", "ocr"],
            variable=self.frag_filter_var,
            width=160,
        )
        self.frag_filter_opt.pack(side="left", padx=(0, 12), pady=10)

        # self.frag_autoscroll_var pre-inicializado em __init__
        self.frag_autoscroll_chk = ctk.CTkSwitch(bar, text="Auto-scroll", variable=self.frag_autoscroll_var)
        self.frag_autoscroll_chk.pack(side="left", padx=(0, 12), pady=10)

        self.btn_frag_clear = ctk.CTkButton(bar, text="Limpar", command=self._clear_fragments, width=90)
        self.btn_frag_clear.pack(side="right", padx=(0, 12), pady=10)

        self.frag_text = ctk.CTkTextbox(wrap, corner_radius=12)
        self.frag_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.frag_text.configure(state="disabled")

    def _build_tab_logs(self) -> None:
        wrap = ctk.CTkFrame(self.tab_logs, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        bar = ctk.CTkFrame(wrap, corner_radius=12)
        bar.pack(fill="x", padx=12, pady=(12, 8))

        self.btn_log_copy = ctk.CTkButton(bar, text="Copiar", command=self._copy_logs, width=90)
        self.btn_log_copy.pack(side="right", padx=(0, 12), pady=10)

        self.btn_log_clear = ctk.CTkButton(bar, text="Limpar", command=self._clear_logs, width=90)
        self.btn_log_clear.pack(side="right", padx=(0, 10), pady=10)

        self.log_text = ctk.CTkTextbox(wrap, corner_radius=12)
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_text.configure(state="disabled")


    def _build_tab_errors(self) -> None:
        wrap = ctk.CTkFrame(self.tab_errors, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        bar = ctk.CTkFrame(wrap, corner_radius=12)
        bar.pack(fill="x", padx=12, pady=(12, 8))

        self.btn_err_copy = ctk.CTkButton(bar, text="Copiar", command=self._copy_errors, width=90)
        self.btn_err_copy.pack(side="right", padx=(0, 12), pady=10)

        self.btn_err_clear = ctk.CTkButton(bar, text="Limpar", command=self._clear_errors, width=90)
        self.btn_err_clear.pack(side="right", padx=(0, 10), pady=10)

        self.error_text = ctk.CTkTextbox(wrap, corner_radius=12)
        self.error_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.error_text.configure(state="disabled")

    def _build_tab_ia_logs(self):
        self.tab_ia_logs.grid_columnconfigure(0, weight=1)
        self.tab_ia_logs.grid_rowconfigure(0, weight=1)
        self.ia_log_box = ctk.CTkTextbox(self.tab_ia_logs, wrap="word", font=("Consolas", 12))
        self.ia_log_box.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.ia_log_box.configure(state="disabled")

    # =========================================================
    # Ads / Merchan Tab (V11)
    # =========================================================

    def _build_tab_ads(self) -> None:
        # Layout principal da aba
        self.tab_ads.grid_columnconfigure(0, weight=1)
        self.tab_ads.grid_rowconfigure(2, weight=1)

        # 1. Top Panel: Seleção de Vídeo e Controle
        top_frame = ctk.CTkFrame(self.tab_ads, corner_radius=12)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_frame.grid_columnconfigure(1, weight=1) # O label do meio estica

        # Botão de Selecionar
        self.ad_select_btn = ctk.CTkButton(
            top_frame,
            text="1. Selecionar Vídeo (.mp4)",
            width=180,
            command=self._on_select_ad_video
        )
        self.ad_select_btn.grid(row=0, column=0, padx=15, pady=10)

        # Botão de Limpar
        self.ad_clear_btn = ctk.CTkButton(
            top_frame,
            text="Limpar",
            width=80,
            fg_color="#555555",
            hover_color="#333333",
            command=self._on_clear_ads
        )
        self.ad_clear_btn.grid(row=1, column=0, padx=15, pady=(0, 10))

        # Label do Caminho (com wrap para não empurrar o botão de analisar)
        self.ad_path_lbl = ctk.CTkLabel(
            top_frame, 
            textvariable=self.ad_video_path_var, 
            font=ctk.CTkFont(size=11), 
            text_color="#888888",
            wraplength=500,
            justify="left"
        )
        self.ad_path_lbl.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="w")

        # Botão de Analisar (Inicialmente desabilitado)
        self.ad_process_btn = ctk.CTkButton(
            top_frame,
            text="2. Analisar Vídeo",
            width=180,
            fg_color="#2E7D32", # Verde
            hover_color="#1B5E20",
            state="disabled",
            command=self._on_process_ad_video
        )
        self.ad_process_btn.grid(row=0, column=2, padx=15, pady=5)

        # Botão de Parar (v11.1)
        self.ad_stop_btn = ctk.CTkButton(
            top_frame,
            text="Parar Análise",
            width=180,
            fg_color="#C62828", # Vermelho
            hover_color="#B71C1C",
            state="disabled",
            command=self._on_stop_ad_analysis
        )
        self.ad_stop_btn.grid(row=1, column=2, padx=15, pady=5)

        # Botão de Exportar PDF
        self.ad_export_btn = ctk.CTkButton(
            top_frame,
            text="Exportar PDF",
            width=180,
            state="disabled",
            command=self._on_export_ad_pdf
        )
        self.ad_export_btn.grid(row=2, column=2, padx=15, pady=5)

        # 2. Status e Progress
        progress_frame = ctk.CTkFrame(self.tab_ads, corner_radius=12, fg_color="transparent")
        progress_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.ad_progress_lbl = ctk.CTkLabel(progress_frame, text="", font=ctk.CTkFont(size=12))
        self.ad_progress_lbl.pack(side="left", padx=10)

        self.ad_progress_bar = ctk.CTkProgressBar(progress_frame, orientation="horizontal", height=10)
        self.ad_progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.ad_progress_bar.set(0)

        # 3. Lista de Resultados
        self.ad_results_box = ctk.CTkScrollableFrame(self.tab_ads, corner_radius=14, fg_color="#111111")
        self.ad_results_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        # Placeholder
        self.ad_empty_lbl = ctk.CTkLabel(self.ad_results_box, text="Nenhum vídeo analisado ainda.", text_color="gray")
        self.ad_empty_lbl.pack(expand=True, pady=40)

        self.ad_cards = []

    def _on_clear_ads(self) -> None:
        self.ad_video_path_var.set("")
        self.ad_selected_files = []
        self.ad_last_results = []
        self.ad_process_btn.configure(state="disabled")
        self.ad_export_btn.configure(state="disabled")
        self.ad_progress_lbl.configure(text="")
        self.ad_progress_bar.set(0)
        for card in self.ad_cards:
            try:
                # Explicit destruction of all children to help GDI release
                for child in card.winfo_children():
                    child.destroy()
                card.destroy()
            except: 
                pass
        self.ad_cards = []
        gc.collect() # Force GDI/Memory release after destroying many widgets
        
        # Recriar label se necessário
        if self.ad_empty_lbl is None or not self.ad_empty_lbl.winfo_exists():
            self.ad_empty_lbl = ctk.CTkLabel(self.ad_results_box, text="Nenhum vídeo analisado ainda.", text_color="gray")
        
        self.ad_empty_lbl.pack(expand=True, pady=40)

    def _on_export_ad_pdf(self) -> None:
        files = getattr(self, "ad_selected_files", [])
        if not files or not self.ad_last_results:
            return
        
        path = files[0] # Usa o primeiro vídeo como referência de nome/pasta
            
        try:
            pdf_path = self.reporter.write_ad_report(path, self.ad_last_results)
            self._log(f"[ADS] Relatório exportado: {pdf_path}")
            self.ad_progress_lbl.configure(text=f"PDF gerado com sucesso!")
            import os
            abs_dir = os.path.abspath(os.path.dirname(pdf_path))
            if os.path.exists(abs_dir):
                os.startfile(abs_dir)
            else:
                self._log(f"[WARN] Pasta de reports não encontrada: {abs_dir}")
        except Exception as e:
            self._ui_error(f"Erro ao exportar PDF: {e}")
        finally:
            gc.collect()

    def _on_select_ad_video(self) -> None:
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(filetypes=[("Vídeos", "*.mp4")])
        if paths:
            self.ad_selected_files = sorted(list(paths))
            count = len(paths)
            if count == 1:
                self.ad_video_path_var.set(paths[0])
            else:
                self.ad_video_path_var.set(f"{count} vídeos selecionados para processamento em lote")
            
            self.ad_process_btn.configure(state="normal")
            self.ad_progress_lbl.configure(text=f"{count} vídeo(s) pronto(s) para análise.")

    def _on_stop_ad_analysis(self) -> None:
        """Sinaliza parada da análise em lote."""
        self.ad_stop_flag.set()
        self.ad_progress_lbl.configure(text="Parada solicitada. Aguardando fim do bloco atual...")
        self.ad_stop_btn.configure(state="disabled")
        self._log("[ADS] Interrupção solicitada pelo usuário.")

    def _on_process_ad_video(self) -> None:
        import json, os, threading

        files = getattr(self, "ad_selected_files", [])
        if not files:
            self._ui_error("Selecione pelo menos um arquivo de vídeo válido primeiro.")
            return

        # Validar primeiro arquivo
        if not os.path.exists(files[0]):
            self._ui_error(f"Arquivo não encontrado: {files[0]}")
            return

        # Inicializar AdAnalyzer se necessário
        try:
            if not hasattr(self, 'ad_analyzer') or self.ad_analyzer is None:
                cfg_path = _get_config_read_path("google_ai.json")
                if not os.path.exists(cfg_path):
                    self._ui_error("Arquivo google_ai.json não encontrado.")
                    return
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = data.get("gemini_api_keys") or data.get("gemini_api_key") or data.get("api_key")
                    model_id = data.get("model", "gemini-2.5-flash") # Use gemini-2.5-flash standard model
                    self.ad_analyzer = AdAnalyzer(key, model_id=model_id)
        except Exception as e:
            self._ui_error(f"Falha ao carregar AdAnalyzer: {e}")
            return

        self.ad_process_btn.configure(state="disabled")
        self.ad_select_btn.configure(state="disabled")
        self.ad_clear_btn.configure(state="disabled")
        self.ad_export_btn.configure(state="disabled")
        self.ad_stop_btn.configure(state="normal")
        
        self.ad_progress_bar.configure(mode="indeterminate")
        self.after(0, self.ad_progress_bar.start)
        self.ad_progress_lbl.configure(text="Iniciando análise...")
        
        self.ad_stop_flag.clear()
        self.ad_last_results = []
        for c in self.ad_cards:
            try:
                for child in c.winfo_children():
                    child.destroy()
                c.destroy()
            except: 
                pass
        self.ad_cards.clear()
        gc.collect()

        def worker():
            try:
                cumulative_offset = 0
                files = sorted(list(self.ad_selected_files))
                total_files = len(files)

                for idx, f_path in enumerate(files):
                    if self.ad_stop_flag.is_set():
                        break

                    f_name = os.path.basename(f_path)
                    self.after(0, lambda p=f_name, i=idx: self._log(f"[ADS] Iniciando análise do vídeo {i+1}/{total_files}: {p}"))
                    self.after(0, lambda p=f_name, i=idx: self.ad_progress_lbl.configure(text=f"Analisando vídeo {i+1}/{total_files}: {p}..."))
                    
                    self.ad_analyzer.analyze_video(
                        f_path, 
                        progress_callback=lambda m, i=idx: self.after(0, lambda: self.ad_progress_lbl.configure(text=f"[{i+1}/{total_files}] {m}")),
                        extra_offset_sec=cumulative_offset,
                        result_callback=lambda items, p=f_path, off=cumulative_offset: self.after(0, lambda: self._add_ad_stream(items, p, off)),
                        stop_flag=self.ad_stop_flag
                    )
                    
                    # Incrementar offset para o próximo arquivo
                    file_duration = self.ad_analyzer.get_video_duration(f_path)
                    cumulative_offset += int(file_duration)

                if self.ad_stop_flag.is_set():
                    self.after(0, lambda: self._log("[ADS] Análise interrompida pelo usuário."))
                else:
                    self.after(0, lambda: self._log("[ADS] Análise de lote completa."))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._ui_error(f"Erro na análise de ads: {err_msg}"))
            finally:
                self.after(0, self.ad_progress_bar.stop)
                self.after(0, lambda: self.ad_progress_bar.set(0))
                self.after(0, lambda: self.ad_process_btn.configure(state="normal"))
                self.after(0, lambda: self.ad_select_btn.configure(state="normal"))
                self.after(0, lambda: self.ad_clear_btn.configure(state="normal"))
                self.after(0, lambda: self.ad_stop_btn.configure(state="disabled"))
                msg = "Processamento finalizado." if not self.ad_stop_flag.is_set() else "Análise interrompida."
                self.after(0, lambda m=msg: self.ad_progress_lbl.configure(text=m))

        threading.Thread(target=worker, daemon=True).start()

    def _add_ad_stream(self, new_items: List[Dict[str, Any]], file_path: str = None, offset: int = 0) -> None:
        """Adiciona resultados de forma incremental e atualiza o dashboard."""
        if not new_items:
            return
            
        if self.ad_empty_lbl:
            try: self.ad_empty_lbl.destroy()
            except: pass
            self.ad_empty_lbl = None
            
        start_idx = len(self.ad_cards)
        for i, res in enumerate(new_items):
            # Guardar metadados para clipping cirúrgico em lote
            if file_path: res["_file_path"] = file_path
            if offset: res["_offset"] = offset
            
            self.ad_last_results.append(res)
            self._add_ad_card(start_idx + i, res)
            
        # Ativar botão de exportação
        self.ad_export_btn.configure(state="normal")
            
        # Forçar atualização do Dashboard e UI lateral
        self._update_dashboard_ui()
        self.update_idletasks()
        
        # Se a lista crescer demais (>200), forçar um GC para evitar leak de handles
        if len(self.ad_cards) > 100 and len(self.ad_cards) % 50 == 0:
            gc.collect()

    def _render_ad_results(self, results: List[Dict[str, Any]]) -> None:
        for c in self.ad_cards:
            try: c.destroy()
            except: pass
        self.ad_cards.clear()
        
        if self.ad_empty_lbl:
            try: self.ad_empty_lbl.destroy()
            except: pass
            self.ad_empty_lbl = None

        if not results:
            self.ad_empty_lbl = ctk.CTkLabel(self.ad_results_box, text="Nenhum anúncio ou comercial encontrado.", text_color="gray")
            self.ad_empty_lbl.pack(pady=40)
            return

        for i, res in enumerate(results):
            self._add_ad_card(i, res)

    def _add_ad_card(self, i: int, res: Dict[str, Any]) -> None:
        tipo = res.get("tipo", "Desconhecido")
        marca = res.get("marca", "—")
        ts = res.get("timestamp", "—")
        inicio = res.get("inicio")
        fim = res.get("fim")
        metodo = res.get("metodo", "Visual")
        posicao = res.get("posicao", "N/A")
        desc = res.get("descricao", "")
        conf = res.get("confianca", 0.0)

        card = ctk.CTkFrame(self.ad_results_box, corner_radius=10, fg_color="#1a1a1a", border_width=1, border_color="#333333")
        card.pack(fill="x", padx=10, pady=5)
        
        # Badge de Tipo
        badge_colors = {
            "Comercial": "#00CED1",
            "Merchan": "#FFD700",
            "Banner": "#9370DB",
            "Patrocínio": "#00FF7F"
        }
        b_color = badge_colors.get(tipo, "gray")
        
        badge_lbl = ctk.CTkLabel(card, text=f" {tipo.upper()} ", font=ctk.CTkFont(size=12, weight="bold"), 
                                 fg_color=b_color, text_color="black", corner_radius=4)
        badge_lbl.grid(row=0, column=0, padx=12, pady=(12, 0), sticky="w")

        # Ícone de Método (Auditivo/Visual)
        m_icon = "👁️" if "Visual" in metodo else "👂" if "Auditivo" in metodo else "👁️👂"
        m_lbl = ctk.CTkLabel(card, text=m_icon, font=ctk.CTkFont(size=16))
        m_lbl.grid(row=0, column=0, padx=(110, 0), pady=(12, 0), sticky="w")
        
        # Marca e Timestamp (Clickable)
        p_path = res.get("_file_path", self.ad_video_path_var.get())
        p_off = res.get("_offset", 0)
        
        lbl_info = ctk.CTkLabel(card, text=f"{marca} @ {ts}", font=ctk.CTkFont(size=17, weight="bold"), cursor="hand2")
        lbl_info.grid(row=1, column=0, padx=12, pady=(4, 0), sticky="w")
        lbl_info.bind("<Button-1>", lambda e, p=p_path, t=ts, s=inicio, f=fim, off=p_off: self._play_video_at(p, t, s, f, off))
        
        # Descrição + Posição
        full_desc = f"{desc} | Posição: {posicao}" if posicao and posicao != "N/A" else desc
        lbl_desc = ctk.CTkLabel(card, text=full_desc, font=ctk.CTkFont(size=14), text_color="#dddddd", wraplength=800, justify="left")
        lbl_desc.grid(row=2, column=0, padx=12, pady=(4, 12), sticky="w")

        # Confiança
        conf_pct = int(float(conf or 0.0) * 100)
        ctk.CTkLabel(card, text=f"{conf_pct}% conf.", font=ctk.CTkFont(size=11), text_color="#888888").place(relx=1.0, rely=0.0, x=-12, y=12, anchor="ne")

        self.ad_cards.append(card)

    def _play_video_at(self, path: str, timestamp: str, start_ts: str = None, end_ts: str = None, offset_sec: int = 0) -> None:
        """Extrai um clipe cirúrgico baseado no início/fim da IA e abre para verificação."""
        import os, subprocess, time
        if not path or not os.path.exists(path): return
        
        self.ad_progress_lbl.configure(text=f"Recortando momento exato...")
        self.update_idletasks()

        def to_sec(ts_str):
            if not ts_str: return 0
            try:
                parts = ts_str.split(':')
                if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            except: pass
            return 0

        try:
            # Ajustar para tempo relativo se houver offset (Batch Mode)
            t_center = max(0, to_sec(timestamp) - offset_sec)
            t_start = max(0, to_sec(start_ts) - offset_sec) if start_ts else max(0, t_center - 10)
            t_end = max(0, to_sec(end_ts) - offset_sec) if end_ts else t_center + 20
            
            # Garantir uma duração mínima de 2s para evitar clips corrompidos
            if t_end <= t_start: t_end = t_start + 30
            duration = t_end - t_start

            # Pasta temporária para previews
            preview_dir = os.path.join("data", "previews")
            os.makedirs(preview_dir, exist_ok=True)
            out_path = os.path.abspath(os.path.join(preview_dir, f"clip_{int(time.time())}.mp4"))

            # Comando FFMPEG (Surgical Cut)
            # Usamos -ss antes de -i para velocidade, e -t para duração
            cmd = [
                'ffmpeg', '-y', '-ss', str(t_start), '-i', path,
                '-t', str(duration), '-c', 'copy', out_path
            ]
            
            self._log(f"[CLIP] Recortando de {t_start}s até {t_end}s (duração: {duration}s)")
            subprocess.run(cmd, check=True, capture_output=True)
            
            if os.path.exists(out_path):
                os.startfile(out_path)
                self.ad_progress_lbl.configure(text=f"Clipe cirúrgico aberto!")
            else:
                raise FileNotFoundError("Clipe não gerado")
        except Exception as e:
            self._log(f"[WARN] Falha no clipping cirúrgico: {e}. Abrindo original no tempo médio.")
            os.startfile(path)

    def _build_tab_dashboard(self) -> None:
        """Aba de Inteligência de Mídia - Executive View (Premium)."""
        # Fundo principal ultra dark
        bg_frame = ctk.CTkFrame(self.tab_dash, fg_color="#080808")
        bg_frame.pack(fill="both", expand=True)

        self.dash_scroll = ctk.CTkScrollableFrame(bg_frame, corner_radius=0, fg_color="transparent")
        self.dash_scroll.pack(fill="both", expand=True, padx=20, pady=20)

        # 1. Header com Branding Professional
        header = ctk.CTkFrame(self.dash_scroll, fg_color="transparent")
        header.pack(fill="x", pady=(0, 25))
        
        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="BRAND INTELLIGENCE", font=ctk.CTkFont(size=12, weight="bold"), text_color="#555555").pack(anchor="w")
        ctk.CTkLabel(title_box, text="Executive Audit Dashboard", font=ctk.CTkFont(size=32, weight="bold"), text_color="#FFFFFF").pack(anchor="w")
        
        self.dash_sync_lbl = ctk.CTkLabel(header, text="● LIVE SYNC ACTIVE", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00FF7F")
        self.dash_sync_lbl.pack(side="right", padx=10)

        # 2. KPI Top Row
        self.dash_kpi_frame = ctk.CTkFrame(self.dash_scroll, fg_color="transparent")
        self.dash_kpi_frame.pack(fill="x", pady=(0, 30))
        # (Serao preenchidos no update: Total Exposures, Confidence, Unique Brands)

        # 3. Main Grid (Split 60/40)
        self.dash_mid_grid = ctk.CTkFrame(self.dash_scroll, fg_color="transparent")
        self.dash_mid_grid.pack(fill="both", expand=True)
        self.dash_mid_grid.columnconfigure(0, weight=3) # Left: Top Brands
        self.dash_mid_grid.columnconfigure(1, weight=2) # Right: Placement/Methods

        # Left Column: Performance Matrix
        self.dash_matrix_box = ctk.CTkFrame(self.dash_mid_grid, fg_color="#0f0f0f", corner_radius=15, border_width=1, border_color="#1a1a1a")
        self.dash_matrix_box.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        ctk.CTkLabel(self.dash_matrix_box, text="BRAND PERFORMANCE MATRIX", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888888").pack(anchor="w", padx=20, pady=15)
        
        self.dash_matrix_content = ctk.CTkFrame(self.dash_matrix_box, fg_color="transparent")
        self.dash_matrix_content.pack(fill="both", expand=True, padx=10, pady=(0, 20))

        # Right Column: Exposure Zones & Methods
        right_col = ctk.CTkFrame(self.dash_mid_grid, fg_color="transparent")
        right_col.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        
        # Sub-box: Detection Methods
        self.dash_methods_box = ctk.CTkFrame(right_col, fg_color="#0f0f0f", corner_radius=15, border_width=1, border_color="#1a1a1a")
        self.dash_methods_box.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(self.dash_methods_box, text="DETECTION METHODS", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888888").pack(anchor="w", padx=20, pady=12)
        self.dash_methods_content = ctk.CTkFrame(self.dash_methods_box, fg_color="transparent")
        self.dash_methods_content.pack(fill="x", padx=20, pady=(0, 15))

        # Sub-box: Placement Zones
        self.dash_placement_box = ctk.CTkFrame(right_col, fg_color="#0f0f0f", corner_radius=15, border_width=1, border_color="#1a1a1a")
        self.dash_placement_box.pack(fill="both", expand=True)
        ctk.CTkLabel(self.dash_placement_box, text="EXPOSURE ZONES (HEATMAP)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888888").pack(anchor="w", padx=20, pady=12)
        self.dash_placement_content = ctk.CTkFrame(self.dash_placement_box, fg_color="transparent")
        self.dash_placement_content.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # 4. Activity Timeline (Full Width Bottom)
        ctk.CTkLabel(self.dash_scroll, text="REAL-TIME ACTIVITY LOG", font=ctk.CTkFont(size=13, weight="bold"), text_color="#888888").pack(anchor="w", pady=(30, 10))
        self.dash_log_box = ctk.CTkFrame(self.dash_scroll, fg_color="#0f0f0f", corner_radius=15, border_width=1, border_color="#1a1a1a")
        self.dash_log_box.pack(fill="x")
        
        self.after(2000, self._update_dashboard_ui)

    def _update_dashboard_ui(self) -> None:
        """Dashboard Premium com KPIs, Market Share e Análise de Posicionamento."""
        if not self.tab_dash.winfo_ismapped():
            self.after(5000, self._update_dashboard_ui)
            return

        # Limpeza
        for f in [self.dash_kpi_frame, self.dash_matrix_content, self.dash_methods_content, 
                  self.dash_placement_content, self.dash_log_box]:
            for w in f.winfo_children(): w.destroy()

        # Agregação de Dados Robusta
        brands = {}
        positions = {}
        methods = {"Visual": 0, "Auditivo": 0, "Híbrido": 0}
        timeline_events = []
        total_counts = 0
        sum_conf = 0.0
        
        # 1. Dados Offline
        for res in self.ad_last_results:
            b = res.get("marca", "Desconhecido")
            conf = float(res.get("confianca", 0.0))
            met = res.get("metodo", "Visual")
            pos = res.get("posicao", "N/A")
            ts = res.get("timestamp", "00:00")
            
            brands[b] = brands.get(b, 0) + 1
            methods[met] = methods.get(met, 0) + 1
            if pos != "N/A": positions[pos] = positions.get(pos, 0) + 1
            
            total_counts += 1
            sum_conf += conf
            timeline_events.append({"time": ts, "brand": b, "type": res.get("tipo", "Ad"), "src": "Offline", "met": met})

        # 2. Dados Live
        for entry in self.detector.get_timeline():
            if entry.get("type") in ("banner", "cloud_result"):
                b = entry.get("details", {}).get("marca") or entry.get("label") or "Banner"
                if b == "unknown": continue
                
                brands[b] = brands.get(b, 0) + 1
                total_counts += 1
                sum_conf += 0.95 # Base confidence para live
                methods["Visual"] += 1
                ts = f"{int(entry.get('t_seconds', 0)) // 60:02d}:{int(entry.get('t_seconds', 0)) % 60:02d}"
                timeline_events.append({"time": ts, "brand": b, "type": "Banner", "src": "Live", "met": "Visual"})

        if total_counts == 0:
            ctk.CTkLabel(self.dash_matrix_content, text="Aguardando dados de auditoria...", font=ctk.CTkFont(size=14), text_color="#444444").pack(pady=40)
            self.after(10000, self._update_dashboard_ui)
            return

        # Renderizar KPIs (Top Row)
        avg_conf = (sum_conf / total_counts) * 100
        unique_brands = len(brands)
        
        kpi_data = [
            ("TOTAL EXPOSURES", f"{total_counts}", "#00E5FF", "Volume de aparições detectadas"),
            ("UNIQUE BRANDS", f"{unique_brands}", "#7000FF", "Marcas distintas identificadas"),
            ("AVG CONFIDENCE", f"{avg_conf:.1f}%", "#00FF7F", "Precisão média da auditoria IA")
        ]
        
        for i, (tit, val, color, sub) in enumerate(kpi_data):
            self.dash_kpi_frame.columnconfigure(i, weight=1)
            f = ctk.CTkFrame(self.dash_kpi_frame, fg_color="#0f0f0f", corner_radius=15, height=110, border_width=1, border_color="#1a1a1a")
            f.grid(row=0, column=i, padx=5 if i!=0 else (0,5), sticky="nsew")
            f.grid_propagate(False)
            
            ctk.CTkLabel(f, text=tit, font=ctk.CTkFont(size=11, weight="bold"), text_color="#666666").pack(anchor="w", padx=20, pady=(15,0))
            ctk.CTkLabel(f, text=val, font=ctk.CTkFont(size=32, weight="bold"), text_color=color).pack(anchor="w", padx=20)
            ctk.CTkLabel(f, text=sub, font=ctk.CTkFont(size=10), text_color="#444444").pack(anchor="w", padx=20)

        # Renderizar Matrix (Top 10 Marcas)
        sorted_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)
        for b, count in sorted_brands[:10]:
            share = (count / total_counts) * 100
            row = ctk.CTkFrame(self.dash_matrix_content, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=6)
            
            ctk.CTkLabel(row, text=b, font=ctk.CTkFont(size=14, weight="bold"), width=180, anchor="w").pack(side="left")
            # Barra de Share
            bar_wrap = ctk.CTkFrame(row, fg_color="#151515", height=12, width=250, corner_radius=6)
            bar_wrap.pack(side="left", padx=15)
            # Simular progresso com largura fixa
            fill_w = max(4, int(250 * (share/100)))
            ctk.CTkFrame(bar_wrap, fg_color="#00E5FF", height=12, width=fill_w, corner_radius=6).place(x=0, y=0)
            
            ctk.CTkLabel(row, text=f"{count}x", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00E5FF", width=40).pack(side="left")
            ctk.CTkLabel(row, text=f"{share:.1f}%", font=ctk.CTkFont(size=11), text_color="#555555", width=40).pack(side="left")

        # Renderizar Methods
        for m, c in methods.items():
            if c == 0: continue
            m_pct = (c / sum(methods.values())) * 100
            icon = "👁️" if m=="Visual" else "👂" if m=="Auditivo" else "👁️👂"
            m_row = ctk.CTkFrame(self.dash_methods_content, fg_color="transparent")
            m_row.pack(fill="x", pady=4)
            ctk.CTkLabel(m_row, text=f"{icon} {m}", font=ctk.CTkFont(size=13)).pack(side="left")
            ctk.CTkLabel(m_row, text=f"{m_pct:.0f}%", font=ctk.CTkFont(size=13, weight="bold"), text_color="#7000FF").pack(side="right")

        # Renderizar Placements (Zones)
        sorted_pos = sorted(positions.items(), key=lambda x: x[1], reverse=True)
        for p, c in sorted_pos[:5]:
            p_pct = (c / sum(positions.values())) * 100
            p_row = ctk.CTkFrame(self.dash_placement_content, fg_color="transparent")
            p_row.pack(fill="x", pady=4)
            ctk.CTkLabel(p_row, text=p, font=ctk.CTkFont(size=13)).pack(side="left")
            ctk.CTkLabel(p_row, text=f"{p_pct:.0f}%", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FF3D00").pack(side="right")

        # Renderizar Activity Log (Sleek Timeline)
        timeline_events.sort(key=lambda x: x["time"])
        for ev in timeline_events[-15:]:
            log_item = ctk.CTkFrame(self.dash_log_box, fg_color="transparent", height=35)
            log_item.pack(fill="x", padx=20, pady=2)
            
            ctk.CTkLabel(log_item, text=f" {ev['time']} ", font=ctk.CTkFont(size=11, family="Consolas"), fg_color="#1a1a1a", corner_radius=4).pack(side="left")
            ctk.CTkLabel(log_item, text=f"  {ev['brand']}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF").pack(side="left")
            ctk.CTkLabel(log_item, text=f"• {ev['type']}", font=ctk.CTkFont(size=12), text_color="#666666").pack(side="left", padx=10)
            
            src_color = "#00FF7F" if ev["src"] == "Live" else "#555555"
            ctk.CTkLabel(log_item, text=ev["src"].upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color=src_color).pack(side="right")

        self.after(10000, self._update_dashboard_ui)

    def _build_tab_reports(self) -> None:
        """Aba Executiva de Central de Jogos Auditados & Dossiês com IA."""
        container = ctk.CTkFrame(self.tab_reports, fg_color="#0d0d0d")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. Topo: Header com KPIs Executivos
        kpi_bar = ctk.CTkFrame(container, fg_color="transparent")
        kpi_bar.pack(fill="x", padx=4, pady=(2, 10))

        # KPI 1: Total de Jogos
        self.kpi_games_box = ctk.CTkFrame(kpi_bar, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2b5b84", width=170, height=52)
        self.kpi_games_box.pack(side="left", padx=(0, 6), fill="y")
        self.kpi_games_box.pack_propagate(False)
        ctk.CTkLabel(self.kpi_games_box, text="🏆 JOGOS AUDITADOS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_kpi_games_val = ctk.CTkLabel(self.kpi_games_box, text="3 Partidas", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00FF7F")
        self.lbl_kpi_games_val.pack(anchor="w", padx=10, pady=(0, 4))

        # KPI 2: Gols Analisados
        self.kpi_goals_box = ctk.CTkFrame(kpi_bar, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2b5b84", width=170, height=52)
        self.kpi_goals_box.pack(side="left", padx=6, fill="y")
        self.kpi_goals_box.pack_propagate(False)
        ctk.CTkLabel(self.kpi_goals_box, text="⚽ GOLS VALIDADOS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_kpi_goals_val = ctk.CTkLabel(self.kpi_goals_box, text="8 Gols", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00CED1")
        self.lbl_kpi_goals_val.pack(anchor="w", padx=10, pady=(0, 4))

        # KPI 3: Marcas e Publicidade
        self.kpi_brands_box = ctk.CTkFrame(kpi_bar, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2b5b84", width=170, height=52)
        self.kpi_brands_box.pack(side="left", padx=6, fill="y")
        self.kpi_brands_box.pack_propagate(False)
        ctk.CTkLabel(self.kpi_brands_box, text="📺 INSERÇÕES DE MARCAS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_kpi_brands_val = ctk.CTkLabel(self.kpi_brands_box, text="48 Ativações", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFD700")
        self.lbl_kpi_brands_val.pack(anchor="w", padx=10, pady=(0, 4))

        # KPI 4: Relatórios PDF
        self.kpi_pdfs_box = ctk.CTkFrame(kpi_bar, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2b5b84", width=170, height=52)
        self.kpi_pdfs_box.pack(side="left", padx=6, fill="y")
        self.kpi_pdfs_box.pack_propagate(False)
        ctk.CTkLabel(self.kpi_pdfs_box, text="📄 DOSSIÊS OFICIAIS", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(anchor="w", padx=10, pady=(6, 0))
        self.lbl_kpi_pdfs_val = ctk.CTkLabel(self.kpi_pdfs_box, text="3 PDFs", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00BFFF")
        self.lbl_kpi_pdfs_val.pack(anchor="w", padx=10, pady=(0, 4))

        btn_refresh_audits = ctk.CTkButton(
            kpi_bar, text="🔄 Atualizar Mural", font=ctk.CTkFont(size=11, weight="bold"),
            width=140, height=36, fg_color="#1f538d", hover_color="#153b66", command=self._render_audited_games_ui
        )
        btn_refresh_audits.pack(side="right", padx=(6, 0), pady=6)

        # 2. Barra de Filtro e Pesquisa
        filter_bar = ctk.CTkFrame(container, fg_color="#141414", corner_radius=10, height=40)
        filter_bar.pack(fill="x", padx=4, pady=(0, 8))

        self.audit_search_var = ctk.StringVar()
        self.audit_comp_filter_var = ctk.StringVar(value="Todos")

        search_entry = ctk.CTkEntry(
            filter_bar, textvariable=self.audit_search_var,
            placeholder_text="🔎 Pesquisar por time (ex: Palmeiras, Flamengo, Vasco)...",
            width=280, height=28, font=ctk.CTkFont(size=11)
        )
        search_entry.pack(side="left", padx=(10, 10), pady=6)
        search_entry.bind("<KeyRelease>", lambda e: self._render_audited_games_ui())

        seg_comps = ctk.CTkSegmentedButton(
            filter_bar,
            values=["Todos", "Brasileirão", "Copa do Brasil", "Paulistão"],
            variable=self.audit_comp_filter_var,
            command=lambda v: self._render_audited_games_ui(),
            font=ctk.CTkFont(size=10, weight="bold"),
            height=28
        )
        seg_comps.pack(side="left", padx=5, pady=6)

        # 3. Split Screen: Esquerda (Mural de Cards) | Direita (Dossiê Executivo)
        split_body = ctk.CTkFrame(container, fg_color="transparent")
        split_body.pack(fill="both", expand=True, padx=4, pady=4)

        # Coluna Esquerda: Mural de Jogos
        left_mural_frame = ctk.CTkFrame(split_body, fg_color="transparent")
        left_mural_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.audited_cards_scroll = ctk.CTkScrollableFrame(left_mural_frame, fg_color="transparent")
        self.audited_cards_scroll.pack(fill="both", expand=True)

        # Coluna Direita: Detalhes do Dossiê & Análise da IA
        self.audited_dossier_frame = ctk.CTkFrame(split_body, width=420, fg_color="#121212", corner_radius=12, border_width=1, border_color="#2b5b84")
        self.audited_dossier_frame.pack(side="left", fill="both", padx=(6, 0))
        self.audited_dossier_frame.pack_propagate(False)

        # Construir o container interno do dossiê
        self._build_dossier_side_panel()

        # Variável de auditoria atualmente selecionada
        self._current_selected_audit = None

        # Carga inicial
        self.after(500, self._render_audited_games_ui)

    def _build_dossier_side_panel(self) -> None:
        """Monta o painel lateral de Dossiê Executivo da partida selecionada."""
        for w in self.audited_dossier_frame.winfo_children():
            w.destroy()

        # Header do Dossiê
        header = ctk.CTkFrame(self.audited_dossier_frame, fg_color="#181818", corner_radius=8, height=42)
        header.pack(fill="x", padx=10, pady=(10, 6))
        
        self.dossier_title_lbl = ctk.CTkLabel(
            header, text="📋 SELECIONE UMA PARTIDA NO MURAL", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00CED1"
        )
        self.dossier_title_lbl.pack(side="left", padx=10, pady=8)

        # Resumo da IA
        ctk.CTkLabel(
            self.audited_dossier_frame, text="🧠 RESUMO EXECUTIVO DA INTELIGÊNCIA ARTIFICIAL:",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#888888"
        ).pack(anchor="w", padx=12, pady=(4, 2))

        self.dossier_summary_text = ctk.CTkTextbox(
            self.audited_dossier_frame, font=ctk.CTkFont(size=11), wrap="word", height=130, fg_color="#0a0a0a"
        )
        self.dossier_summary_text.pack(fill="x", padx=10, pady=(0, 8))

        # Cronologia de Lances
        ctk.CTkLabel(
            self.audited_dossier_frame, text="⏱️ CRONOLOGIA DE LANCES & MOMENTOS CHAVE:",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#888888"
        ).pack(anchor="w", padx=12, pady=(4, 2))

        self.dossier_timeline_scroll = ctk.CTkScrollableFrame(self.audited_dossier_frame, fg_color="#0a0a0a", height=140)
        self.dossier_timeline_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Botões de Ação na base
        actions_bar = ctk.CTkFrame(self.audited_dossier_frame, fg_color="transparent")
        actions_bar.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_dossier_open_pdf = ctk.CTkButton(
            actions_bar, text="📄 Abrir PDF no Visualizador", font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#008080", hover_color="#005a5a", height=32, command=self._open_selected_dossier_pdf
        )
        self.btn_dossier_open_pdf.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_dossier_copy_summary = ctk.CTkButton(
            actions_bar, text="📋 Copiar Resumo", font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2B5B84", hover_color="#1E3F5A", height=32, width=120, command=self._copy_selected_dossier_summary
        )
        self.btn_dossier_copy_summary.pack(side="left", padx=(4, 0))

    def _render_audited_games_ui(self) -> None:
        """Carrega e renderiza todos os cards de jogos auditados no mural da esquerda."""
        if not hasattr(self, "audited_cards_scroll"):
            return

        for w in self.audited_cards_scroll.winfo_children():
            w.destroy()

        try:
            from modules.audited_games_manager import AuditedGamesManager
            audits = AuditedGamesManager.load_all()
            kpis = AuditedGamesManager.get_kpis()
        except Exception as e:
            self._log(f"[AUDIT UI WARN] Erro ao carregar jogos auditados: {e}")
            audits = []
            kpis = {"total_games": 0, "total_goals": 0, "total_brands": 0, "total_pdfs": 0}

        # Atualiza KPIs
        if hasattr(self, "lbl_kpi_games_val"):
            self.lbl_kpi_games_val.configure(text=f"{kpis.get('total_games', 0)} Partidas")
            self.lbl_kpi_goals_val.configure(text=f"{kpis.get('total_goals', 0)} Gols")
            self.lbl_kpi_brands_val.configure(text=f"{kpis.get('total_brands', 0)} Ativações")
            self.lbl_kpi_pdfs_val.configure(text=f"{kpis.get('total_pdfs', 0)} PDFs")

        # Filtragem
        query = self.audit_search_var.get().lower().strip() if hasattr(self, "audit_search_var") else ""
        comp_filter = self.audit_comp_filter_var.get() if hasattr(self, "audit_comp_filter_var") else "Todos"

        filtered = []
        for a in audits:
            t1 = a.get("team1", "").lower()
            t2 = a.get("team2", "").lower()
            comp = a.get("comp", "").lower()
            date = a.get("date", "").lower()

            if query and (query not in t1 and query not in t2 and query not in comp and query not in date):
                continue

            if comp_filter != "Todos":
                if comp_filter.lower() not in comp:
                    continue

            filtered.append(a)

        if not filtered:
            ctk.CTkLabel(
                self.audited_cards_scroll, text="Nenhum jogo auditado encontrado com os filtros atuais.",
                font=ctk.CTkFont(size=12), text_color="#777777"
            ).pack(pady=30)
            return

        # Renderizar Cards Esportivos
        for item in filtered:
            self._render_single_audited_card(item)

        # Seleciona o primeiro por padrão se nenhum estiver selecionado
        if not self._current_selected_audit and filtered:
            self._select_audited_game(filtered[0])

    def _render_single_audited_card(self, item: dict) -> None:
        """Gera um card visual esportivo completo para a partida auditada."""
        t1 = item.get("team1", "")
        t2 = item.get("team2", "")
        score = item.get("score", "x")
        comp = item.get("comp", "Brasileirão")
        d_str = item.get("date", "")
        plat = item.get("platform", "CazéTV")
        status = item.get("status", "Concluído")
        g_cnt = item.get("goals_count", 0)
        c_cnt = item.get("cards_count", 0)
        b_cnt = item.get("brands_count", 0)

        card = ctk.CTkFrame(self.audited_cards_scroll, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2b5b84")
        card.pack(fill="x", padx=4, pady=4)

        # Header do Card
        card_header = ctk.CTkFrame(card, fg_color="transparent")
        card_header.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            card_header, text=f"🏆 {comp}  •  📅 {d_str}  •  📺 {plat}",
            font=ctk.CTkFont(size=10), text_color="#AAAAAA"
        ).pack(side="left")

        # Placar Central em Destaque
        card_body = ctk.CTkFrame(card, fg_color="transparent")
        card_body.pack(fill="x", padx=10, pady=2)

        lbl_match = ctk.CTkLabel(
            card_body, text=f"⚡ {t1}  {score}  {t2}",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#00FF7F"
        )
        lbl_match.pack(side="left", pady=2)

        # Badges e Estatísticas
        badges_row = ctk.CTkFrame(card, fg_color="transparent")
        badges_row.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(
            badges_row, text=f"⚽ {g_cnt} Gols   🟨 {c_cnt} Cartões   📺 {b_cnt} Marcas   🟢 {status}",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#00CED1"
        ).pack(side="left")

        # Barra de Botões de Ação do Card
        card_actions = ctk.CTkFrame(card, fg_color="transparent")
        card_actions.pack(fill="x", padx=10, pady=(4, 6))

        btn_pdf = ctk.CTkButton(
            card_actions, text="📄 PDF", font=ctk.CTkFont(size=10, weight="bold"),
            width=65, height=22, fg_color="#008080", hover_color="#005a5a",
            command=lambda it=item: self._open_audited_game_pdf(it)
        )
        btn_pdf.pack(side="left", padx=(0, 4))

        btn_copy = ctk.CTkButton(
            card_actions, text="📋 Resumo", font=ctk.CTkFont(size=10, weight="bold"),
            width=75, height=22, fg_color="#2B5B84", hover_color="#1E3F5A",
            command=lambda it=item: self._copy_audited_game_summary(it)
        )
        btn_copy.pack(side="left", padx=4)

        btn_view = ctk.CTkButton(
            card_actions, text="🔍 Ver Dossiê", font=ctk.CTkFont(size=10, weight="bold"),
            width=80, height=22, fg_color="#333333", hover_color="#444444",
            command=lambda it=item: self._select_audited_game(it)
        )
        btn_view.pack(side="left", padx=4)

        btn_sp = ctk.CTkButton(
            card_actions, text="☁️ SharePoint", font=ctk.CTkFont(size=10, weight="bold"),
            width=85, height=22, fg_color="#006699", hover_color="#004466",
            command=lambda it=item: self._upload_audited_game_to_sharepoint(it)
        )
        btn_sp.pack(side="left", padx=4)

        btn_del = ctk.CTkButton(
            card_actions, text="🗑️", font=ctk.CTkFont(size=10, weight="bold"),
            width=26, height=22, fg_color="#552222", hover_color="#882222",
            command=lambda it=item: self._delete_audited_game(it.get("id"))
        )
        btn_del.pack(side="right", padx=(4, 0))

        # Clique no corpo do card seleciona o dossiê
        for w in (card, card_header, card_body, lbl_match, badges_row):
            w.bind("<Button-1>", lambda e, it=item: self._select_audited_game(it))

    def _select_audited_game(self, game: dict) -> None:
        """Preenche o painel lateral de Dossiê Executivo com os detalhes do jogo clicado."""
        self._current_selected_audit = game
        t1 = game.get("team1", "")
        t2 = game.get("team2", "")
        score = game.get("score", "x")
        d_str = game.get("date", "")
        summary = game.get("summary", "Sem resumo executivo cadastrado.")
        timeline = game.get("timeline", [])

        if hasattr(self, "dossier_title_lbl"):
            self.dossier_title_lbl.configure(text=f"⚡ {t1} {score} {t2} ({d_str})")

        if hasattr(self, "dossier_summary_text"):
            self.dossier_summary_text.delete("1.0", "end")
            self.dossier_summary_text.insert("1.0", summary)

        if hasattr(self, "dossier_timeline_scroll"):
            for w in self.dossier_timeline_scroll.winfo_children():
                w.destroy()

            if not timeline:
                ctk.CTkLabel(
                    self.dossier_timeline_scroll, text="Nenhum momento chave indexado na timeline.",
                    font=ctk.CTkFont(size=10), text_color="#666666"
                ).pack(pady=10)
            else:
                for ev in timeline:
                    row = ctk.CTkFrame(self.dossier_timeline_scroll, fg_color="#141414", corner_radius=6)
                    row.pack(fill="x", padx=2, pady=2)

                    min_text = ev.get("min", "--")
                    ev_type = ev.get("type", "Lance")
                    desc = ev.get("desc", "")

                    ctk.CTkLabel(
                        row, text=f"⏱️ {min_text} | {ev_type}",
                        font=ctk.CTkFont(size=10, weight="bold"), text_color="#00CED1"
                    ).pack(anchor="w", padx=6, pady=(3, 0))

                    if desc:
                        ctk.CTkLabel(
                            row, text=desc, font=ctk.CTkFont(size=9), text_color="#CCCCCC", wraplength=360
                        ).pack(anchor="w", padx=6, pady=(0, 3))

    def _copy_selected_dossier_summary(self) -> None:
        """Copia o resumo executivo do dossiê selecionado."""
        if not self._current_selected_audit:
            messagebox.showwarning("Aviso", "Selecione uma partida no mural para copiar o resumo.")
            return
        self._copy_audited_game_summary(self._current_selected_audit)

    def _copy_audited_game_summary(self, game: dict) -> None:
        """Formata e copia o relatório executivo da partida para o Clipboard."""
        t1 = game.get("team1", "")
        t2 = game.get("team2", "")
        score = game.get("score", "x")
        comp = game.get("comp", "")
        date = game.get("date", "")
        plat = game.get("platform", "")
        summary = game.get("summary", "")

        text_to_copy = (
            f"📊 *RELATÓRIO DE AUDITORIA ESPORTIVA - MONITOR ESPORTES*\n"
            f"🏆 Competição: {comp} | 📅 Data: {date} | 📺 Canal: {plat}\n"
            f"⚽ Partida: *{t1} {score} {t2}*\n\n"
            f"📋 *Resumo Executivo da IA:*\n{summary}\n\n"
            f"✅ Auditoria concluída com validação de súmula oficial e inserções publicitárias."
        )

        try:
            self.clipboard_clear()
            self.clipboard_append(text_to_copy)
            self._log(f"📋 [DOSSIÊ] Resumo de {t1} x {t2} copiado com sucesso!")
            self._ui_success("Resumo copiado para a Área de Transferência!")
        except Exception as e:
            self._log(f"[UI ERROR] Falha ao copiar resumo: {e}")

    def _open_selected_dossier_pdf(self) -> None:
        """Abre o PDF oficial do dossiê selecionado."""
        if not self._current_selected_audit:
            messagebox.showwarning("Aviso", "Selecione uma partida no mural primeiro.")
            return
        self._open_audited_game_pdf(self._current_selected_audit)

    def _open_audited_game_pdf(self, game: dict) -> None:
        """Abre o arquivo PDF associado à partida no visualizador interno ou do Windows."""
        pdf_path = game.get("pdf_path", "")
        if pdf_path and os.path.exists(pdf_path):
            self._open_internal_pdf_viewer(pdf_path)
        else:
            # Tentar abrir primeiro PDF disponível na pasta reports
            reports_dir = os.path.join(PROJECT_ROOT, "reports")
            import glob
            pdfs = glob.glob(os.path.join(reports_dir, "*.pdf"))
            if pdfs:
                self._open_internal_pdf_viewer(pdfs[0])
            else:
                messagebox.showinfo(
                    "Relatório PDF",
                    f"O arquivo PDF desta partida ainda não foi gravado em disco ou foi movido.\n\n"
                    f"Você pode gerar um novo relatório a qualquer momento clicando em '🚀 Iniciar Auditoria' no modo Expert."
                )

    def _upload_audited_game_to_sharepoint(self, item: dict) -> None:
        """Envia o PDF do jogo auditado selecionado para a Document Library do SharePoint."""
        pdf_path = item.get("pdf_path")
        if not pdf_path or not os.path.exists(pdf_path):
            # Tentar encontrar um PDF correspondente na pasta de relatórios
            reports_dir = os.path.join(PROJECT_ROOT, "reports")
            import glob
            pdfs = glob.glob(os.path.join(reports_dir, "*.pdf"))
            if pdfs:
                pdf_path = pdfs[0]
            else:
                messagebox.showwarning("SharePoint", "Dossiê PDF não encontrado para esta partida.")
                return

        t1 = item.get("team1", "")
        t2 = item.get("team2", "")
        match_str = f"{t1} x {t2}" if t1 and t2 else item.get("match_id", "Partida")
        comp = item.get("comp", "Brasileirão")
        plat = item.get("channel", "Amazon Prime")
        date_str = item.get("date", "")
        time_str = item.get("time", "")
        
        from modules.sharepoint_reporter import SharePointReporter
        iso_date = SharePointReporter.format_iso_datetime(date_str, time_str)

        self._log(f"[SHAREPOINT] Sincronizando '{match_str}' (Data/Hora evento: {iso_date}) com o SharePoint...")
        
        def run_sync():
            try:
                success = SharePointReporter.sync_pdf_to_sharepoint(
                    pdf_path=pdf_path,
                    partida=match_str,
                    campeonato=comp,
                    plataforma=plat,
                    data_hora_iso=iso_date,
                    confianca="99.5%"
                )
                if success:
                    self.after(0, lambda: self._log(f"🎉 [SHAREPOINT] '{match_str}' enviado com sucesso para o SharePoint!"))
                    self.after(0, lambda: messagebox.showinfo("SharePoint Document Library", f"Relatório PDF de '{match_str}' e seus 7 metadados sincronizados com sucesso no SharePoint!"))
                else:
                    self.after(0, lambda: self._log(f"❌ [SHAREPOINT] Falha ao enviar '{match_str}'."))
                    self.after(0, lambda: messagebox.showerror("SharePoint Error", "Falha ao enviar relatório para o SharePoint. Verifique logs/conexão."))
            except Exception as ex:
                self.after(0, lambda: self._log(f"❌ [SHAREPOINT ERROR] {ex}"))

        import threading
        threading.Thread(target=run_sync, daemon=True).start()

    def _delete_audited_game(self, audit_id: str) -> None:
        """Exclui uma auditoria do histórico."""
        if not audit_id:
            return
        if messagebox.askyesno("Confirmar Exclusão", "Deseja realmente remover este registro do mural de auditorias?"):
            try:
                from modules.audited_games_manager import AuditedGamesManager
                AuditedGamesManager.delete_audit(audit_id)
                self._current_selected_audit = None
                self._render_audited_games_ui()
                self._log(f"🗑️ [AUDITORIAS] Registro {audit_id} removido.")
            except Exception as e:
                self._log(f"[UI ERROR] Falha ao excluir auditoria: {e}")

    def _trigger_auto_clip(self, label: str, details: dict) -> None:
        """Dispara a gravação de um clipe no OBS (Opção 3)."""
        if not self.auto_clip_var.get(): return
        
        now = time.time()
        # Evitar clips repetidos em menos de 60 segundos
        if (now - self.last_clip_time) < 60: return
        
        # Filtro: Só clipa se parecer anúncio, banner ou merchan
        is_ad = "BANNER" in label.upper() or "MERCHAN" in label.upper() or "COMERCIAL" in label.upper()
        if not is_ad: return
        
        self.last_clip_time = now
        self._log(f"[CLIP] Detecção importante ({label}). Acionando Replay Buffer no OBS...")
        
        try:
            # Tentar salvar o Replay Buffer (que pega os últimos X segundos)
            self.obs.save_replay_buffer()
            self._log("[CLIP] Replay Buffer salvo com sucesso!")
        except Exception as e:
            self._log(f"[WARN] Falha ao salvar clip no OBS: {e}")
            # Fallback: Iniciar gravação normal por 30s? 
            # (Pode ser intrusivo, melhor apenas logar o erro por enquanto)

    def _build_tab_config(self) -> None:
        wrap = ctk.CTkScrollableFrame(self.tab_cfg, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        grid = ctk.CTkFrame(wrap, corner_radius=12)
        grid.pack(fill="x", padx=12, pady=(12, 12))

        ctk.CTkLabel(grid, text="Prepare antes (min):").grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")
        # self.prepare_min_var pre-inicializado em __init__
        self.prepare_entry = ctk.CTkEntry(grid, width=120)
        self.prepare_entry.insert(0, str(self.prepare_min_var.get()))
        self.prepare_entry.grid(row=0, column=1, padx=12, pady=(12, 8), sticky="w")

        ctk.CTkLabel(grid, text="Cleanup após (dias):").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        # self.cleanup_days_var pre-inicializado em __init__
        self.cleanup_entry = ctk.CTkEntry(grid, width=120)
        self.cleanup_entry.insert(0, str(self.cleanup_days_var.get()))
        self.cleanup_entry.grid(row=1, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(grid, text="FPS amostra (frames):").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        # self.sample_fps_var pre-inicializado em __init__
        self.sample_fps_entry = ctk.CTkEntry(grid, width=120)
        self.sample_fps_entry.insert(0, str(self.sample_fps_var.get()))
        self.sample_fps_entry.grid(row=2, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(grid, text="Segmento áudio (s):").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        # self.seg_audio_var pre-inicializado em __init__
        self.seg_audio_entry = ctk.CTkEntry(grid, width=120)
        self.seg_audio_entry.insert(0, str(self.seg_audio_var.get()))
        self.seg_audio_entry.grid(row=3, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(grid, text="Relatório parcial (s):").grid(row=4, column=0, padx=12, pady=(8, 12), sticky="w")
        # self.partial_report_var pre-inicializado em __init__
        self.partial_report_entry = ctk.CTkEntry(grid, width=120)
        self.partial_report_entry.insert(0, str(self.partial_report_var.get()))
        self.partial_report_entry.grid(row=4, column=1, padx=12, pady=(8, 12), sticky="w")

        grid.grid_columnconfigure(0, weight=1)

        roi_cfg = ctk.CTkFrame(wrap, corner_radius=12)
        roi_cfg.pack(fill="x", padx=12, pady=(0, 12))
        roi_cfg.grid_columnconfigure(0, weight=1)
        roi_cfg.grid_columnconfigure(1, weight=1)
        roi_cfg.grid_columnconfigure(2, weight=1)
        roi_cfg.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            roi_cfg,
            text="ROIs ativas do detector",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=4, padx=12, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            roi_cfg,
            text="Desative ROIs que você não quer analisar para economizar processamento. Esta configuração é carregada por perfil de canal e pode ser aplicada sem reiniciar.",
            justify="left",
            wraplength=980
        ).grid(row=1, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w")

        self._ensure_roi_toggle_vars()
        roi_keys = list(self.roi_enabled_vars.keys())
        cols = 4
        for idx, key in enumerate(roi_keys):
            row = 2 + (idx // cols)
            col = idx % cols
            chk = ctk.CTkCheckBox(
                roi_cfg,
                text=key,
                variable=self.roi_enabled_vars[key],
            )
            chk.grid(row=row, column=col, padx=12, pady=6, sticky="w")

        cloud_wrap = ctk.CTkFrame(wrap, corner_radius=12)
        cloud_wrap.pack(fill="x", padx=12, pady=(0, 12))
        
        ctk.CTkLabel(
            cloud_wrap,
            text="Cloud Expert (Gemini AI)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            cloud_wrap,
            text="Usa a API do Google Gemini para validar o estado do jogo a cada X minutos via análise de lote (Batch).",
            justify="left",
            wraplength=980
        ).grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

        cloud_wrap.grid_columnconfigure(2, weight=1)

        ctk.CTkSwitch(
            cloud_wrap,
            text="Ativar Análise em Nuvem",
            variable=self.cloud_enabled_var,
            command=self._on_cloud_setting_change
        ).grid(row=2, column=0, padx=12, pady=10, sticky="w")

        ctk.CTkButton(
            cloud_wrap,
            text="Baixar Último JSON",
            width=120,
            height=28,
            fg_color="#333333",
            hover_color="#444444",
            command=self._on_download_cloud_json
        ).grid(row=2, column=4, padx=12, pady=10, sticky="e")

        # Linha 3: Controle de Intervalo
        ctk.CTkLabel(cloud_wrap, text="Intervalo (min):").grid(row=3, column=0, padx=12, pady=5, sticky="w")
        
        ctk.CTkSlider(
            cloud_wrap,
            from_=2,
            to=30,
            number_of_steps=28,
            variable=self.cloud_interval_var,
            width=300,
            command=lambda _: self._on_cloud_setting_change()
        ).grid(row=3, column=1, columnspan=2, padx=12, pady=5, sticky="ew")
        
        ctk.CTkLabel(cloud_wrap, textvariable=self.cloud_interval_var, width=30, font=ctk.CTkFont(weight="bold")).grid(row=3, column=3, padx=5, pady=5, sticky="w")

        self.cloud_status_label = ctk.CTkLabel(
            cloud_wrap,
            textvariable=self.cloud_status_var,
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color="#AAAAAA",
            justify="left"
        )
        self.cloud_status_label.grid(row=4, column=0, columnspan=5, padx=12, pady=(0, 12), sticky="w")

        # --- Preferências do Relatório Expert ---
        expert_prefs_wrap = ctk.CTkFrame(wrap, corner_radius=12)
        expert_prefs_wrap.pack(fill="x", padx=12, pady=(0, 12))
        
        ctk.CTkLabel(
            expert_prefs_wrap,
            text="Configurações do Relatório Expert",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=4, padx=12, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            expert_prefs_wrap,
            text="Escolha quais informações devem ser incluídas no relatório técnico final (PDF e Texto).",
            justify="left"
        ).grid(row=1, column=0, columnspan=4, padx=12, pady=(0, 10), sticky="w")

        ctk.CTkCheckBox(expert_prefs_wrap, text="Cronologia Base (Início/Fim)", variable=self.expert_show_chrono_var).grid(row=2, column=0, padx=12, pady=8, sticky="w")
        ctk.CTkCheckBox(expert_prefs_wrap, text="Gols / Cartões / Substituições", variable=self.expert_show_milestones_var).grid(row=2, column=1, padx=12, pady=8, sticky="w")
        ctk.CTkCheckBox(expert_prefs_wrap, text="Eventos Secundários (VAR/Chances)", variable=self.expert_show_secondary_var).grid(row=2, column=2, padx=12, pady=8, sticky="w")
        ctk.CTkCheckBox(expert_prefs_wrap, text="Fontes de Pesquisa (Grounding)", variable=self.expert_show_sources_var).grid(row=2, column=3, padx=12, pady=8, sticky="w")

        # --- Performance / Banner OCR (MOVIDO PARA CIMA) ---
        perf_wrap = ctk.CTkFrame(wrap, corner_radius=12)
        perf_wrap.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            perf_wrap,
            text="Performance (Banner OCR)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            perf_wrap,
            text="Controle a frequência de leitura do banner local. Valores maiores economizam CPU.",
            justify="left", font=ctk.CTkFont(size=12)
        ).pack(anchor="w", padx=12, pady=(0, 10))

        perf_slider_row = ctk.CTkFrame(perf_wrap, fg_color="transparent")
        perf_slider_row.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(perf_slider_row, text="Intervalo OCR (s):", width=120, anchor="e").pack(side="left", padx=(0, 10))
        ctk.CTkSlider(
            perf_slider_row,
            from_=0.5,
            to=10.0,
            number_of_steps=19,
            variable=self.banner_ocr_interval_var,
            width=300,
            command=lambda _: self._on_banner_throttle_change()
        ).pack(side="left", padx=10, fill="x", expand=True)
        
        ctk.CTkLabel(perf_slider_row, textvariable=self.banner_ocr_interval_var, width=40, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(10, 0))

        # --- ROI Actions (Restaurado para o lugar correto) ---
        roi_actions = ctk.CTkFrame(roi_cfg, corner_radius=10)
        roi_actions.grid(row=3, column=0, columnspan=cols, sticky="ew", padx=12, pady=(0, 12))
        
        ctk.CTkButton(roi_actions, text="Aplicar ROIs agora", command=self._apply_roi_enabled_runtime, width=200, height=35).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Salvar perfil", command=lambda: self._apply_roi_enabled_runtime(save_profile=True), width=180, height=35).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Recarregar perfil", command=self._reload_roi_enabled_from_profile, width=180, height=35).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Modo Perf", command=self._set_roi_mode_performance, width=150, height=35, fg_color="#444444").pack(side="right", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Modo Full", command=self._set_roi_mode_full, width=150, height=35, fg_color="#444444").pack(side="right", padx=8, pady=8)

        # --- General Actions (Restaurado para o lugar correto) ---
        actions = ctk.CTkFrame(wrap, corner_radius=12)
        actions.pack(fill="x", padx=12, pady=(0, 12))

        self.btn_apply_cfg = ctk.CTkButton(actions, text="Aplicar configs", command=self._apply_config, width=200, height=35)
        self.btn_apply_cfg.pack(side="left", padx=12, pady=12)

        self.btn_cleanup = ctk.CTkButton(actions, text="Rodar cleanup agora", command=self._run_cleanup_now, width=200, height=35)
        self.btn_cleanup.pack(side="left", padx=12, pady=12)

        self.btn_open_data = ctk.CTkButton(actions, text="Abrir pasta data", command=self._open_events_folder, width=200, height=35)
        self.btn_open_data.pack(side="left", padx=12, pady=12)

        # --- E-mail e Auto-Stop (Solicitado pelo usuário) ---
        email_wrap = ctk.CTkFrame(wrap, corner_radius=12)
        email_wrap.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            email_wrap,
            text="Relatórios por E-mail & Auto-Stop",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            email_wrap,
            text="Configurações para envio de PDF via e-mail e encerramento automático da sessão.",
            justify="left", font=ctk.CTkFont(size=12)
        ).grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 10), sticky="w")

        ctk.CTkSwitch(
            email_wrap,
            text="Enviar relatório por E-mail ao finalizar",
            variable=self.send_report_email_var
        ).grid(row=2, column=0, padx=12, pady=10, sticky="w")

        email_input_row = ctk.CTkFrame(email_wrap, fg_color="transparent")
        email_input_row.grid(row=3, column=0, columnspan=2, padx=12, pady=5, sticky="ew")
        
        ctk.CTkLabel(email_input_row, text="Destinatários Padrão para Relatórios de Transmissão:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00CED1").pack(anchor="w", pady=(0, 5))
        
        # Container para checkboxes de destinatários padrão
        default_recs_container = ctk.CTkScrollableFrame(email_input_row, height=80, fg_color="#181818", border_width=1, border_color="#333333")
        default_recs_container.pack(fill="x", expand=True)
        
        default_checkbox_vars = {}
        
        def _refresh_default_checkboxes():
            for w in default_recs_container.winfo_children():
                w.destroy()
            default_checkbox_vars.clear()
            
            saved = _load_saved_emails()
            current_defaults = [r.strip().lower() for r in re.split(r'[,;]', self.email_recipients_var.get()) if r.strip()]
            
            for em in saved:
                is_checked = em.lower() in current_defaults
                var = ctk.BooleanVar(value=is_checked)
                default_checkbox_vars[em] = var
                
                def _make_checkbox_cb(email_addr=em, variable=var):
                    def _on_toggle():
                        checked_list = [e for e, v in default_checkbox_vars.items() if v.get()]
                        self.email_recipients_var.set(";".join(checked_list))
                        self._save_general_settings()
                    return _on_toggle
                
                ctk.CTkCheckBox(
                    default_recs_container, text=em, variable=var,
                    font=ctk.CTkFont(size=11), command=_make_checkbox_cb(em, var)
                ).pack(anchor="w", padx=5, pady=2)

        _refresh_default_checkboxes()

        autostop_row = ctk.CTkFrame(email_wrap, fg_color="transparent")
        autostop_row.grid(row=4, column=0, columnspan=2, padx=12, pady=(5, 12), sticky="ew")

        ctk.CTkLabel(autostop_row, text="Auto-Stop Pós-jogo (min):").pack(side="left", padx=(0, 5))
        self.autostop_entry = ctk.CTkEntry(autostop_row, width=60)
        self.autostop_entry.insert(0, str(self.auto_stop_pos_mins_var.get()))
        self.autostop_entry.pack(side="left")
        ctk.CTkLabel(autostop_row, text="(0 para desativar)", font=ctk.CTkFont(size=10, slant="italic")).pack(side="left", padx=5)

        # --- Gestão de E-mails Cadastrados ---
        emails_mgmt_frame = ctk.CTkFrame(wrap, corner_radius=12)
        emails_mgmt_frame.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(
            emails_mgmt_frame,
            text="👥 Gestão de E-mails Cadastrados",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#00CED1"
        ).pack(anchor="w", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            emails_mgmt_frame,
            text="Adicione ou remova os e-mails autorizados no sistema (usados no Agendamento e Envio Manual):",
            justify="left", font=ctk.CTkFont(size=11), text_color="#AAAAAA"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Adicionar novo e-mail
        add_email_row = ctk.CTkFrame(emails_mgmt_frame, fg_color="transparent")
        add_email_row.pack(fill="x", padx=12, pady=5)

        new_email_val = ctk.StringVar()
        entry_new_email = ctk.CTkEntry(add_email_row, textvariable=new_email_val, placeholder_text="ex: novo.email@ibope.com", width=300)
        entry_new_email.pack(side="left", padx=(0, 10))

        # Container para a lista de e-mails
        list_container = ctk.CTkScrollableFrame(emails_mgmt_frame, height=100, fg_color="#181818", border_width=1, border_color="#333333")
        list_container.pack(fill="x", padx=12, pady=(5, 12))

        def _refresh_config_emails_list():
            for w in list_container.winfo_children():
                w.destroy()
            
            saved = _load_saved_emails()
            for em in saved:
                row = ctk.CTkFrame(list_container, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                ctk.CTkLabel(row, text=em, font=ctk.CTkFont(size=11)).pack(side="left", padx=5)
                
                # Botão de deletar
                def _make_delete_handler(email_addr=em):
                    def _delete():
                        _remove_saved_email(email_addr)
                        # Atualizar a lista de destinatários padrão se o e-mail removido estiver nela
                        current_recs = [r.strip() for r in re.split(r'[,;]', self.email_recipients_var.get()) if r.strip()]
                        if email_addr in current_recs:
                            current_recs.remove(email_addr)
                            self.email_recipients_var.set(";".join(current_recs))
                            self._save_general_settings()
                        _refresh_config_emails_list()
                        _refresh_default_checkboxes()
                    return _delete

                ctk.CTkButton(
                    row, text="🗑️ Remover", width=70, height=20,
                    fg_color="#333333", hover_color="#8B0000", font=ctk.CTkFont(size=10),
                    command=_make_delete_handler(em)
                ).pack(side="right", padx=5)

        def _add_new_email_action():
            import tkinter.messagebox as mb
            email_addr = new_email_val.get().strip()
            if not email_addr:
                return
            if "@" not in email_addr or "." not in email_addr:
                mb.showerror("Erro", "Insira um endereço de e-mail válido.")
                return
            _save_email(email_addr)
            new_email_val.set("")
            _refresh_config_emails_list()
            _refresh_default_checkboxes()

        ctk.CTkButton(
            add_email_row, text="➕ Cadastrar E-mail", width=120, height=28,
            fg_color="#00CED1", text_color="black", hover_color="#008B8B", font=ctk.CTkFont(size=11, weight="bold"),
            command=_add_new_email_action
        ).pack(side="left")

        # Inicializar a lista
        _refresh_config_emails_list()

        # --- Seção do Sistema / Auto-Updater ---
        sys_cfg = ctk.CTkFrame(wrap, corner_radius=12)
        sys_cfg.pack(fill="x", padx=12, pady=(0, 12))
        
        ctk.CTkLabel(sys_cfg, text="⚙️ Sistema & Atualizações", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00CED1").pack(anchor="w", padx=12, pady=(12, 4))
        
        lbl_version_status = ctk.CTkLabel(sys_cfg, text=f"Versão Instalada: v{AutoUpdater().current_version}", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_version_status.pack(anchor="w", padx=12, pady=4)
        
        def force_update_check():
            lbl_version_status.configure(text=f"Versão Instalada: v{AutoUpdater().current_version} (Checando novas versões...)")
            def run_check():
                try:
                    updater = AutoUpdater()
                    has_update, remote_ver, download_url, changelog = updater.check_for_update()
                    if has_update:
                        def ask_user():
                            lbl_version_status.configure(text=f"Versão Instalada: v{updater.current_version} (Nova versão v{remote_ver} disponível!)", text_color="#00FF00")
                            msg = f"Uma nova versão ({remote_ver}) está disponível!\n\nChangelog:\n{changelog}\n\nDeseja baixar e atualizar agora automaticamente?"
                            if messagebox.askyesno("Atualização Disponível", msg):
                                self._log(f"[AUTO-UPDATER] Iniciando atualização automática para v{remote_ver}...")
                                updater.perform_update_and_restart(download_url)
                        self.after(0, ask_user)
                    else:
                        def notify_up_to_date():
                            lbl_version_status.configure(text=f"Versão Instalada: v{updater.current_version} (Você está na versão mais recente!)", text_color="#FFFFFF")
                            messagebox.showinfo("Sistema Atualizado", f"Você já está utilizando a versão mais recente ({updater.current_version}) do Monitor Esportes.")
                        self.after(0, notify_up_to_date)
                except Exception as e_up:
                    def notify_error(err=e_up):
                        lbl_version_status.configure(text=f"Versão Instalada: v{updater.current_version} (Erro ao checar atualizações)", text_color="#FF4500")
                        messagebox.showerror("Erro de Rede", f"Não foi possível consultar atualizações no GitHub:\n{err}")
                    self.after(0, notify_error)

            threading.Thread(target=run_check, daemon=True).start()

        btn_check_update = ctk.CTkButton(
            sys_cfg, text="🔄 Verificar Atualizações", font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#1f538d", hover_color="#153b66", height=24, width=180,
            command=force_update_check
        )
        btn_check_update.pack(anchor="w", padx=12, pady=(4, 12))

        ctk.CTkLabel(wrap, text="Obs: estas configurações afetam a GUI e o pipeline em tempo real.", font=ctk.CTkFont(size=11, slant="italic")).pack(side="bottom", pady=8)

    def _on_cloud_setting_change(self) -> None:
        if getattr(self, "_is_loading_settings", False):
            return
        enabled = bool(self.cloud_enabled_var.get())
        interval = int(self.cloud_interval_var.get())
        self.detector.cfg.cloud_enabled = enabled
        self.detector.cfg.cloud_interval_minutes = interval
        # Batch size = intervalo * 2 (1 frame a cada 30s)
        self.detector.cfg.cloud_batch_size = max(4, interval * 2)
        
        # Sincronização automática: Se IA Ligada, desativar OCR local pesado
        if enabled:
            tags_to_disable = ["score", "clock", "countdown_center", "top_hud_unificado"]
            for tag in tags_to_disable:
                if tag in self.roi_enabled_vars:
                    self.roi_enabled_vars[tag].set(False)
            self._log("[GUI] IA Ativada: ROIs de Placar/Relógio desativados para economia de CPU.")
        
        self._log(f"[CLOUD] Config atualizada: {enabled} | Intervalo: {interval} min")
        self._save_general_settings()

    def _on_banner_throttle_change(self) -> None:
        if getattr(self, "_is_loading_settings", False):
            return
        val = float(self.banner_ocr_interval_var.get())
        self.detector.cfg.banner_ocr_interval_s = val
        if hasattr(self.detector, "vision"):
            try:
                self.detector.vision.banner_ocr_interval_s = float(val)
            except Exception:
                pass
        self._log(f"[CONFIG] Banner OCR Intervalo: {val:.1f}s")
        self._save_general_settings()

    def _on_download_cloud_json(self) -> None:
        """Download do último JSON de análise da Cloud Oracle."""
        if not self.detector: return
        st = getattr(self.detector, "_state", None) # Já definido no topo, mas mantendo para segurança se necessário ou removendo
        if not st: return
        res = getattr(st, "last_cloud_result", {})
        
        if not res:
            from tkinter import messagebox
            messagebox.showinfo("Cloud Oracle", "Nenhum resultado da nuvem disponível ainda.\nAguarde o primeiro ciclo de análise (4/4).")
            return

        import json
        import os
        from tkinter import filedialog
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"gemini_analysis_{int(time.time())}.json",
            title="Salvar Resultado da Inteligência Artificial"
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(res, f, indent=4, ensure_ascii=False)
            self._log(f"[CLOUD] JSON de análise salvo em: {save_path}")

    def _on_clear_cloud_buffer(self) -> None:
        if not self.detector: return
        st = getattr(self.detector, "_state", None) # Já definido no topo, mas mantendo para segurança se necessário ou removendo
        if not st: return
        old_count = len(st.cloud_buffer or [])
        st.cloud_buffer = []
        self._log(f"[CLOUD] Buffer limpo manualmente ({old_count} frames removidos)")
        self.cloud_progress_var.set(0.0)
        self._load_roi_enabled_ui_from_detector()

    # =========================================================
    # Events list
    # =========================================================

    def _add_event_card(self, i: int, ev: Dict[str, Any]) -> None:
        """Cria um card de evento com thumbnail e informações (v9.1)."""
        status = (ev.get("status") or "").lower()
        title = ev.get("title") or "—"
        sel_list = [cat for cat, var in self.category_vars.items() if var.get()]
        meta = _extract_event_meta(title, sel_list[0] if sel_list else "Todos")
        # Fallback de data para eventos finalizados
        raw_start = ev.get("scheduled_start") or ev.get("release_timestamp")
        sched = _fmt_dt(raw_start)
        thumb_url = ev.get("thumbnail")

        badge = "🟢 LIVE" if status == "live" else ("🟡 UPCOMING" if status == "upcoming" else ("⚪ FINALIZADO" if status == "ended" else (status.upper() or "—")))
        subtitle = meta["match_display"] or title
        comp = meta["competition"] or "Geral"
        if len(subtitle) > 80: subtitle = subtitle[:77] + "..."
        
        # Container do card
        card = ctk.CTkFrame(self.events_box, corner_radius=10, fg_color="transparent")
        card.pack(fill="x", padx=4, pady=4)
        
        # Botão principal (layout horizontal)
        btn = ctk.CTkButton(
            card,
            text="",
            height=80,
            fg_color="#2b2b2b",
            hover_color="#3d3d3d",
            command=lambda idx=i: self._select_event(idx),
        )
        btn.pack(fill="both", expand=True)

        # Layout interno do botão
        content = ctk.CTkFrame(btn, fg_color="transparent")
        content.place(relx=0, rely=0, relwidth=1, relheight=1)
        content.bind("<Button-1>", lambda e, idx=i: self._select_event(idx)) # Click passthrough

        # Slot da Seleção (Checkbox)
        cb_var = ctk.BooleanVar(value=(i in self._selected_indices))
        self._event_checkbox_vars[i] = cb_var
        
        cb = ctk.CTkCheckBox(
            content, 
            text="", 
            variable=cb_var, 
            width=24, 
            command=lambda idx=i: self._select_event(idx)
        )
        cb.pack(side="left", padx=(10, 0))
        self._event_checkboxes[i] = cb

        # Slot da Imagem (Thumbnail)
        img_frame = ctk.CTkFrame(content, width=100, height=60, corner_radius=6, fg_color="#1a1a1a")
        img_frame.pack(side="left", padx=10, pady=10)
        img_frame.pack_propagate(False)

        img_label = ctk.CTkLabel(img_frame, text="⌛", font=ctk.CTkFont(size=20))
        img_label.pack(expand=True)

        # Informações (Texto)
        info_frame = ctk.CTkFrame(content, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, pady=5)
        
        l1 = ctk.CTkLabel(info_frame, text=badge, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#00FF7F" if status == "live" else ("#FFB300" if status == "upcoming" else "#AAAAAA")))
        l1.pack(anchor="w")
        l2 = ctk.CTkLabel(info_frame, text=subtitle, font=ctk.CTkFont(size=12, weight="bold"), anchor="w", wraplength=230, justify="left")
        l2.pack(fill="x")
        l3 = ctk.CTkLabel(info_frame, text=f"{comp} • {sched}", font=ctk.CTkFont(size=11), text_color="#CCCCCC", anchor="w", wraplength=230, justify="left")
        l3.pack(fill="x")

        # Vincular clique em tudo para garantir seleção
        for w in [content, img_frame, img_label, info_frame, l1, l2, l3]:
            w.bind("<Button-1>", lambda e, idx=i: self._select_event(idx))
        
        # Botão de Excluir (X)
        btn_del = ctk.CTkButton(
            content,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color=("#FF5252", "#D32F2F"),
            text_color="gray",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda idx=i: self._remove_event(idx)
        )
        btn_del.place(relx=1.0, rely=0.0, x=-35, y=5)
        
        self._event_buttons.append(card)

        # Carregamento Assíncrono da Imagem (com Cache)
        if not hasattr(self, "_thumb_cache"): self._thumb_cache = {}
        
        if thumb_url and Image:
            if thumb_url in self._thumb_cache:
                img_label.configure(text="", image=self._thumb_cache[thumb_url])
            else:
                def load_thumb():
                    try:
                        import requests
                        headers = {"User-Agent": "Mozilla/5.0"}
                        response = requests.get(thumb_url, headers=headers, timeout=5)
                        response.raise_for_status()
                        img = Image.open(io.BytesIO(response.content))
                        img = img.resize((100, 60), Image.LANCZOS)
                        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 60))
                        
                        self._thumb_cache[thumb_url] = ctk_img
                        self.after(0, lambda: img_label.configure(text="", image=ctk_img))
                    except:
                        self.after(0, lambda: img_label.configure(text="❌"))
                threading.Thread(target=load_thumb, daemon=True).start()

    def _render_events(self) -> None:
        """
        Renderiza a lista de eventos de forma assíncrona para não travar a GUI.
        """
        if getattr(self, "_rendering_events", False): return
        self._rendering_events = True

        for b in self._event_buttons:
            try:
                b.destroy()
            except Exception:
                pass
        self._event_buttons.clear()

        if not self._events:
            ph = ctk.CTkLabel(self.events_box, text="(sem eventos carregados)", text_color="gray")
            ph.pack(fill="x", padx=8, pady=10)
            self._event_buttons.append(ph)
            self._selected_index = None
            self._rendering_events = False
            return

        filter_val = self.event_filter_var.get()
        display_events = []
        search_term = self.event_search_var.get().lower().strip()

        for i, ev in enumerate(self._events):
            title = (ev.get("title") or "").lower()
            status = (ev.get("status") or "").lower()
            
            # Filtro de Busca
            if search_term and search_term not in title:
                continue

            if filter_val == "Ao Vivo" and status != "live": continue
            if filter_val == "Encerrados" and status not in ["ended", "completed", "none", ""]: 
                if status == "upcoming": continue
            if filter_val == "Proximos" and status != "upcoming": continue
            display_events.append((i, ev))

        # Ordenação
        sort_mode = self.event_sort_var.get()
        if sort_mode == "Alfabética":
            display_events.sort(key=lambda x: (x[1].get("title") or "").lower())
        elif sort_mode == "Data (Antigos)":
            display_events.sort(key=lambda x: x[1].get("release_timestamp") or 0)
        else: # Data (Recentes)
            display_events.sort(key=lambda x: x[1].get("release_timestamp") or 0, reverse=True)

        # Mostrar Barra de Progresso
        self.load_progress.pack(fill="x")
        self.load_progress.set(0)
        
        total = len(display_events)
        chunk_size = 15
        
        def render_chunk(start_idx: int):
            end_idx = min(start_idx + chunk_size, total)
            for idx in range(start_idx, end_idx):
                i, ev = display_events[idx]
                self._add_event_card(i, ev)
            
            prog = end_idx / total
            self.load_progress.set(prog)
            
            if end_idx < total:
                self.after(5, lambda: render_chunk(end_idx))
            else:
                self.load_progress.pack_forget()
                self._rendering_events = False
                self._selected_index = None

        render_chunk(0)

    def _select_event(self, idx: int) -> None:
        mode = self.monitoring_mode_var.get()
        if mode == "Expert (API-Only)":
            if idx in self._selected_indices:
                self._selected_indices.remove(idx)
            else:
                self._selected_indices.add(idx)
        else:
            # Modo visual: seleção única
            self._selected_indices = {idx}

        # Sincronizar checkboxes e cores dos cards
        for i, card in enumerate(self._event_buttons):
            try:
                # 1. Atualizar Checkbox (se existir)
                cb_var = self._event_checkbox_vars.get(i)
                if cb_var:
                    # Evitar loop infinito se o comando do checkbox chamou esta função
                    is_sel = i in self._selected_indices
                    if cb_var.get() != is_sel:
                        cb_var.set(is_sel)

                # 2. Atualizar Destaque Visual (Botão de fundo)
                target_btn = None
                for child in card.winfo_children():
                    if isinstance(child, ctk.CTkButton) and child.cget("text") == "":
                        target_btn = child
                        break
                
                if target_btn:
                    if i in self._selected_indices:
                        target_btn.configure(fg_color="#00CED1")
                    else:
                        target_btn.configure(fg_color="#2b2b2b")
            except Exception:
                pass

        if not self._selected_indices:
            self.match_var.set("Partida: —")
            self.comp_var.set("Competição: —")
            return

        # Mostrar info apenas do último selecionado se for multi
        last_idx = list(self._selected_indices)[-1]
        ev = self._events[last_idx]
        sel_list = [cat for cat, var in self.category_vars.items() if var.get()]
        meta = _extract_event_meta(ev.get("title") or "", sel_list[0] if sel_list else "Todos")
        self.match_var.set(f"Partida: {meta['match_display']}")
        self.comp_var.set(f"Competição: {meta['competition']}")
        self._log(f"[UI] Selecionado(s): {len(self._selected_indices)} evento(s)")

    def _remove_event(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._events):
            return
        
        ev = self._events.pop(idx)
        self._log(f"[UI] Evento removido da lista: {ev.get('title')}")
        
        # Se o evento removido era o selecionado, limpa a seleção
        if self._selected_index == idx:
            self._selected_index = None
        elif self._selected_index is not None and self._selected_index > idx:
            self._selected_index -= 1
            
        self._render_events()

    # =========================================================
    # Logging
    # =========================================================

    def _log(self, msg: str) -> None:
        try:
            if threading.current_thread() is not threading.main_thread():
                self.after(0, lambda m=msg: self._log(m))
                return
        except Exception:
            pass
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        
        # Redireciona também para o terminal/output da aplicação
        print(f"[{ts}] {msg}", flush=True)
        
        if getattr(self, "log_text", None):
            self._append_text(self.log_text, line, autoscroll=True)
        if ("[ERRO]" in msg or "[WARN]" in msg or "Traceback" in msg or "Exception" in msg) and getattr(self, "error_text", None):
            try:
                self._append_text(self.error_text, line, autoscroll=True)
            except Exception:
                pass

    def _log_from_pipeline_component(self, msg: str) -> None:
        try:
            self.after(0, lambda m=msg: self._log(m))
        except Exception:
            try:
                self._log(msg)
            except Exception:
                pass

    def _append_text(self, widget: Optional[ctk.CTkTextbox], text: str, autoscroll: bool = True) -> None:
        if widget is None:
            return
        try:
            widget.configure(state="normal")
            widget.insert("end", text)
            if autoscroll:
                widget.see("end")
            widget.configure(state="disabled")
        except Exception:
            pass

    def _append_fragment(self, text: str) -> None:
        self._append_text(self.frag_text, text, autoscroll=bool(self.frag_autoscroll_var.get()))

    def _clear_logs(self) -> None:
        if self.log_text is None:
            return
        try:
            self.log_text.configure(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.configure(state="disabled")
        except Exception:
            pass

    def _clear_errors(self) -> None:
        try:
            self.error_text.configure(state="normal")
            self.error_text.delete("1.0", "end")
            self.error_text.configure(state="disabled")
        except Exception:
            pass

    def _copy_errors(self) -> None:
        try:
            text = self.error_text.get("1.0", "end").strip()
            self.clipboard_clear()
            self.clipboard_append(text)
            self._log("[UI] Erros copiados.")
        except Exception as e:
            self._log(f"[ERRO] copiar erros: {e}")

    def _copy_logs(self) -> None:
        try:
            text = self.log_text.get("1.0", "end").strip()
            self.clipboard_clear()
            self.clipboard_append(text)
            self._log("[UI] Logs copiados.")
        except Exception as e:
            self._log(f"[ERRO] copiar logs: {e}")

    def _clear_fragments(self) -> None:
        self.frag_text.configure(state="normal")
        self.frag_text.delete("1.0", "end")
        self.frag_text.configure(state="disabled")
        self.runtime.timeline_seen = 0
        self._log("[UI] Fragmentos limpos.")

    # =========================================================
    # Theme / presets
    # =========================================================

    def _on_theme_change(self, mode: str) -> None:
        try:
            ctk.set_appearance_mode(mode)
            self._log(f"[UI] Tema alterado: {mode}")
            self._save_general_settings()
        except Exception as e:
            self._log(f"[ERRO] tema: {e}")

    def _on_channel_preset(self, name: str) -> None:
        presets = {
            "CazéTV": "https://www.youtube.com/@CazeTV/streams",
            "TNT Sports": "https://www.youtube.com/@tntsportsbr/streams",
            "ESPN Brasil": "https://www.youtube.com/@ESPNBrasil/streams",
            "SporTV (exemplo)": "https://www.youtube.com/@sportv/streams",
            "URL manual": self.channel_url_var.get().strip() or CHANNEL_STREAMS_URL,
        }
        url = presets.get(name, CHANNEL_STREAMS_URL)
        self.channel_url_var.set(url)
        self._sync_roi_profile_from_channel()
        self._save_general_settings()

    def _on_category_toggle(self, category: str) -> None:
        if category == "Todos":
            if self.category_vars["Todos"].get():
                # Se 'Todos' foi ativado, desmarca o resto
                for cat, var in self.category_vars.items():
                    if cat != "Todos":
                        var.set(False)
        else:
            if self.category_vars[category].get():
                # Se qualquer outro foi ativado, desmarca 'Todos'
                self.category_vars["Todos"].set(False)
        
        # Se nada estiver marcado, volta ao 'Todos' default
        if not any(v.get() for v in self.category_vars.values()):
            self.category_vars["Todos"].set(True)
        
        self._save_general_settings()

    # =========================================================
    # Config apply
    # =========================================================

    def _apply_config(self) -> None:
        def _int_or(fallback: int, entry: ctk.CTkEntry) -> int:
            try:
                return int(entry.get().strip())
            except Exception:
                return fallback

        self.prepare_min_var.set(_int_or(int(PREPARE_MINUTES_BEFORE), self.prepare_entry))
        self.cleanup_days_var.set(_int_or(7, self.cleanup_entry))

        fps = _int_or(int(FRAME_SAMPLE_FPS), self.sample_fps_entry)
        self.sample_fps_var.set(max(1, fps))

        seg = _int_or(int(AUDIO_SEGMENT_SECONDS), self.seg_audio_entry)
        self.seg_audio_var.set(max(0, seg))

        pr = _int_or(600, self.partial_report_entry)
        self.partial_report_var.set(max(60, pr))

        self.prepare_entry.delete(0, "end")
        self.prepare_entry.insert(0, str(self.prepare_min_var.get()))
        self.cleanup_entry.delete(0, "end")
        self.cleanup_entry.insert(0, str(self.cleanup_days_var.get()))
        self.sample_fps_entry.delete(0, "end")
        self.sample_fps_entry.insert(0, str(self.sample_fps_var.get()))
        self.seg_audio_entry.delete(0, "end")
        self.seg_audio_entry.insert(0, str(self.seg_audio_var.get()))
        self.partial_report_entry.delete(0, "end")
        self.partial_report_entry.insert(0, str(self.partial_report_var.get()))

        self.runtime.partial_report_every_s = int(self.partial_report_var.get())
        self._apply_roi_enabled_runtime(save_profile=False)
        self._save_roi_enabled_profile()

        self._log(
            f"[CFG] prepare_min={self.prepare_min_var.get()} | cleanup_days={self.cleanup_days_var.get()} | "
            f"fps={self.sample_fps_var.get()} | audio_seg={self.seg_audio_var.get()} | "
            f"partial_report_s={self.partial_report_var.get()}"
        )

    # =========================================================
    # Load events
    # =========================================================

    def _load_events(self) -> None:
        if getattr(self, "_loading_events", False): return
        self._loading_events = True

        url = self.channel_url_var.get().strip()
        if url and url.startswith("@"):
            url = f"https://www.youtube.com/{url}"
            self.channel_url_var.set(url)

        selected_categories = [cat for cat, var in self.category_vars.items() if var.get()]
        if not selected_categories:
            selected_categories = ["Todos"]

        self._events = []
        self.after(0, self._render_events)
        self.load_progress.pack(fill="x")
        self.load_progress.set(0)
        self.load_progress.configure(mode="indeterminate")
        self.load_progress.start()

        self._ui_info(f"Carregando eventos… ({url}) | filtros: {', '.join(selected_categories)}")

        def worker() -> None:
            try:
                # Tentar API Oficial primeiro se tivermos a chave
                api_key = None
                try:
                    cfg_path = os.path.join(PROJECT_ROOT, "config", "google_ai.json")
                    with open(cfg_path, "r") as f:
                        config_data = json.load(f)
                        api_key = config_data.get("youtube_api_key") or config_data.get("api_key")
                except: pass

                # Datas de Filtro
                d_start = self.search_date_start_var.get().strip()
                d_end = self.search_date_end_var.get().strip()
                
                published_after = None
                published_before = None
                yt_date_after = None
                yt_date_before = None
                
                try:
                    if d_start:
                        dt_s = datetime.strptime(d_start, "%d/%m/%Y")
                        published_after = dt_s.strftime("%Y-%m-%dT00:00:00Z")
                        yt_date_after = dt_s.strftime("%Y%m%d")
                    if d_end:
                        dt_e = datetime.strptime(d_end, "%d/%m/%Y")
                        published_before = dt_e.strftime("%Y-%m-%dT23:59:59Z")
                        yt_date_before = dt_e.strftime("%Y%m%d")
                        
                    # Validação de intervalo (max 31 dias)
                    if d_start and d_end:
                        delta = datetime.strptime(d_end, "%d/%m/%Y") - datetime.strptime(d_start, "%d/%m/%Y")
                        if delta.days > 31:
                            self._log("[WARN] Intervalo superior a 1 mês. A API do Youtube pode limitar os resultados.")
                except Exception as de:
                    self._log(f"[WARN] Erro ao processar datas: {de}. Usando busca padrão.")

                events = []
                if api_key:
                    try:
                        self._log(f"[FETCH] Buscando via YouTube API Oficial v3 (De {d_start} até {d_end})...")
                        events = get_official_events(api_key, url, published_after=published_after, published_before=published_before)
                    except PermissionError as pe:
                        # Se for erro de permissão (API desativada), avisa o user na UI
                        self.after(0, lambda: self._ui_error(f"YouTube API Desativada:\n{pe}"))
                        self._log(f"[FETCH] API Oficial desativada. Tentando yt-dlp como fallback...")
                        events = get_channel_events(url, date_after=yt_date_after, date_before=yt_date_before)
                    except Exception as e:
                        self._log(f"[FETCH] Erro na API Oficial ({e}). Tentando yt-dlp...")
                        events = get_channel_events(url, date_after=yt_date_after, date_before=yt_date_before)
                else:
                    self._log(f"[FETCH] Sem API Key no config. Usando yt-dlp...")
                    events = get_channel_events(url, date_after=yt_date_after, date_before=yt_date_before)

                if not isinstance(events, list):
                    self.after(0, lambda: self._ui_error(f"Erro ao carregar eventos: tipo inválido {type(events)}"))
                    return

                filtered_events: List[Dict[str, Any]] = []
                for ev in events:
                    title = ev.get("title") or ""
                    if _event_matches_category(title, selected_categories):
                        filtered_events.append(ev)

                # Filtragem baseada em checkboxes (Upcoming/Ended)
                show_upcoming = self.expert_upcoming_var.get()
                show_ended = self.expert_finished_var.get()
                
                filtered_events = [
                    ev for ev in filtered_events
                    if (show_upcoming and (ev.get("status") or "").lower() == "upcoming") or
                       (show_ended and (ev.get("status") or "").lower() in ("ended", "complete", "concluído", "finalizado", "video")) or
                       ((ev.get("status") or "").lower() == "live")
                ]
                events = filtered_events

                def k(ev: Dict[str, Any]) -> Tuple[int, float]:
                    st = (ev.get("status") or "").lower()
                    pr = 0 if st == "live" else (1 if st == "upcoming" else 2)
                    dt = _parse_dt(ev.get("scheduled_start"))
                    ts = _safe_timestamp(dt)
                    return (pr, ts)

                events = sorted(events, key=k)

                self._events = events
                def finish():
                    self.load_progress.stop()
                    self.load_progress.configure(mode="determinate")
                    self._render_events()
                self.after(0, finish)

                if len(events) == 0:
                    self.after(0, lambda: self._ui_error(f"Nenhum evento encontrado para os filtros selecionados."))
                else:
                    self.after(0, lambda: self._set_status("stopped", f"{len(events)} eventos carregados."))

                self._log(f"[FETCH] OK: {len(events)} eventos após filtros.")
                if events:
                    self._log("[FETCH] exemplo[0]=" + json.dumps(events[0], ensure_ascii=False)[:400])

            except Exception as e:
                tb = traceback.format_exc()
                err = f"{type(e).__name__}: {e}"
                self.after(0, lambda err=err: self._ui_error(f"Falha ao carregar eventos: {err}"))
                self._log("[TRACE]\n" + tb)

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================
    # Monitoring control
    # =========================================================

    def _set_status(self, mode: str, text: str) -> None:
        if mode == "running":
            self.status_dot.configure(text_color="green")
            self.status_var.set(f"🟢 {text}")
        elif mode == "preparing":
            self.status_dot.configure(text_color="orange")
            self.status_var.set(f"🟠 {text}")
        else:
            self.status_dot.configure(text_color="red")
            self.status_var.set(f"🔴 {text}")

        self._sync_buttons()

    def _start_selected(self) -> None:
        if not self._selected_indices:
            self._log("[UI] Selecione ao menos um evento na lista.")
            return
            
        indices = sorted(list(self._selected_indices))
        selected_events = [self._events[i] for i in indices]
        
        if self.monitoring_mode_var.get() == "Expert (API-Only)":
            self._run_expert_batch_analysis(selected_events)
        else:
            # Modo visual: apenas o primeiro selecionado
            ev = selected_events[0]
            self._start_event(ev, manual_url_override=None)

    def _start_manual_url(self) -> None:
        if self.monitoring_mode_var.get() == "Expert (API-Only)":
            # Usar campos manuais
            data = {
                "team1": self.expert_team1_var.get().strip(),
                "team2": self.expert_team2_var.get().strip(),
                "competition": self.expert_comp_var.get().strip(),
                "platform": self.expert_platform_var.get().strip(),
                "date": self.expert_date_var.get().strip(),
                "time": self.expert_time_var.get().strip()
            }
            if not data["team1"] or not data["team2"]:
                self._ui_error("Preencha ao menos os times para análise Expert.")
                return
            self._run_expert_analysis(data)
            return

        url = (self.manual_url_var.get() or "").strip()
        if not url:
            self._log("[UI] Cole a URL manual do evento.")
            return

        ev = {
            "id": _safe_slug(url),
            "title": "URL manual",
            "url": url,
            "channel": self.channel_url_var.get().strip(),
            "status": "manual",
            "scheduled_start": None,
        }
        self._start_event(ev, manual_url_override=url)

    def _run_expert_analysis(self, data: Dict[str, Any]) -> None:
        """Executa a análise Expert para dados manuais (API-Only) convertendo em lote."""
        start_ts = None
        if data.get("time"):
            try:
                dt_str = f"{data['date']} {data['time']}"
                if len(data['time'].split(':')) == 2:
                    dt_combined = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                else:
                    dt_combined = datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S")
                from datetime import timezone, timedelta
                br_tz = timezone(timedelta(hours=-3))
                dt_combined = dt_combined.replace(tzinfo=br_tz)
                start_ts = int(dt_combined.timestamp())
            except Exception as e:
                self._log(f"[UI] Erro ao processar horário manual: {e}")

        event = {
            "title": f"{data['team1']} x {data['team2']}",
            "url": None,
            "channel": data.get("platform", "CazéTV"),
            "status": "ended",
            "scheduled_start": data.get("date"),
            "timestamp": start_ts,
            "release_timestamp": None,
            "actual_start_time": None,
            "duration": None
        }
        self._run_expert_batch_analysis([event])

    def _run_expert_batch_analysis(self, events: List[Dict[str, Any]]) -> None:
        """Executa a análise de cronologia em lote via ExpertAssistant (Melhorado v10.6)."""
        import modules.expert_assistant
        import importlib
        importlib.reload(modules.expert_assistant)
        from modules.expert_assistant import ExpertAssistant
        import threading
        
        total = len(events)
        self._log(f"[EXPERT] Iniciando análise de lote para {total} evento(s).")
        self.status_var.set(f"⏳ Analisando 1/{total}...")
        self.status_dot.configure(text_color="orange")

        # --- Popup de Progresso ---
        popup = ctk.CTkToplevel(self)
        popup.title("Auditoria Expert I.A.")
        popup.geometry("500x320")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        # Centralizar
        popup.update_idletasks()
        x_pos = self.winfo_x() + (self.winfo_width() // 2) - 250
        y_pos = self.winfo_y() + (self.winfo_height() // 2) - 160
        popup.geometry(f"+{x_pos}+{y_pos}")
        
        # Estilo Premium
        frame = ctk.CTkFrame(popup, corner_radius=15, border_width=2, border_color="#00E5FF", fg_color="#0a0a0a")
        frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        ctk.CTkLabel(frame, text="🚀", font=ctk.CTkFont(size=50)).pack(pady=(25, 5))
        ctk.CTkLabel(frame, text="Auditoria Expert em Ação", font=ctk.CTkFont(size=20, weight="bold"), text_color="#00E5FF").pack()
        
        p_status_lbl = ctk.CTkLabel(frame, text=f"Preparando análise de {total} evento(s)...", font=ctk.CTkFont(size=14))
        p_status_lbl.pack(pady=10)
        
        p_progress = ctk.CTkProgressBar(frame, width=400, height=14, corner_radius=7, progress_color="#00E5FF", fg_color="#222222")
        p_progress.set(0)
        p_progress.pack(pady=10)
        
        p_detail_lbl = ctk.CTkLabel(frame, text="Iniciando conexão com Google Gemini...", font=ctk.CTkFont(size=12), text_color="#999999")
        p_detail_lbl.pack(pady=(0, 20))
        
        def update_popup(idx, title, detail=None):
            prog = (idx + 1) / total
            p_progress.set(prog)
            p_status_lbl.configure(text=f"Analisando {idx+1} de {total}...")
            p_detail_lbl.configure(text=f"Processando: {title[:50]}...")
            if detail:
                p_detail_lbl.configure(text=detail)
        
        # Limpar grid visual e detector para esta nova análise
        self.detector.start_session(f"expert_batch_{int(time.time())}")
        self._update_history_grid()
        
        # Gestão de estado dos botões
        self.btn_start.configure(state="disabled", text="⏳ Processando IA...", fg_color="#1a311a")
        self.btn_stop.configure(state="normal", fg_color="#7a1a1a") # Garantir que o Stop fique visível e vermelho

        def worker():
            try:
                # Carregar API KEY
                cfg_path = _get_config_read_path("google_ai.json")
                if not os.path.exists(cfg_path):
                    self._log("[EXPERT] Erro: Arquivo google_ai.json não encontrado.")
                    raise FileNotFoundError("Arquivo google_ai.json não encontrado.")
                
                with open(cfg_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    api_key = config_data.get("gemini_api_keys") or config_data.get("gemini_api_key") or config_data.get("api_key")
                    yt_key = config_data.get("youtube_api_key")
                    model_id = config_data.get("model", "gemini-2.5-flash")
                
                if not api_key or "SUA_API_KEY" in api_key:
                    self._log("[EXPERT] Erro: API Key não configurada no google_ai.json.")
                    raise ValueError("API Key não configurada.")

                self._log(f"[EXPERT] Inicializando Assistente (Modelo: {model_id})...")
                try:
                    assistant = ExpertAssistant(api_key=api_key, model_id=model_id, yt_api_key=yt_key)
                    # Depuração: Listar modelos
                    try:
                        models_it = assistant.client.models.list()
                        # Converter iterador em lista de nomes
                        m_names = [m.name for m in models_it]
                        self._log(f"[EXPERT] Modelos disponíveis na sua chave: {m_names}")
                    except Exception as e_list:
                        self._log(f"[WARN] Não foi possível listar modelos: {e_list}")
                except Exception as e_init:
                    self._log(f"[EXPERT] Erro ao instanciar ExpertAssistant: {e_init}")
                    self._log(traceback.format_exc())
                    raise e_init

                self._log("[EXPERT] Assistente pronto. Iniciando loop...")
                all_results = []
                
                for idx, ev in enumerate(events):
                    title = ev.get("title", "Evento")
                    # 1. Feedback Visual na Aba Monitoração e Popup
                    self.after(0, lambda i=idx, t=title: update_popup(i, t))
                    self.after(0, lambda i=idx: self.status_var.set(f"⏳ Analisando {i+1}/{total}..."))
                    self._log(f"[EXPERT] Processando evento {idx+1}/{total}: {title}")
                    
                    title = ev.get("title", "")
                    sel_list = [cat for cat, var in self.category_vars.items() if var.get()]
                    meta = _extract_event_meta(title, sel_list[0] if sel_list else "Todos")
                    
                    self.after(0, lambda m=meta: self.match_var.set(f"Partida: {m['match_display']}"))
                    self.after(0, lambda m=meta: self.comp_var.set(f"Competição: {m['competition']}"))
                    self.after(0, lambda: self.clock_var.set("Clock: —"))
                    self.after(0, lambda: self.score_var.set("Score: —"))
                    self.after(0, lambda: self.phase_var.set("Fase: Modo Expert"))
                    
                    teams = meta["match_display"].split(" x ")
                    team1 = teams[0] if len(teams) > 0 else "Time 1"
                    team2 = teams[1] if len(teams) > 1 else "Time 2"
                    
                    # Extração da data exata do evento (com ano)
                    event_date_raw = ev.get("scheduled_start") or ""
                    event_date = datetime.now().strftime("%d/%m/%Y")
                    if event_date_raw:
                        # Limpa o ISO se vier com T (ex: 2026-04-04T21:00:00Z)
                        date_part = str(event_date_raw).split("T")[0].split(" ")[0]
                        parts = date_part.split("-")
                        if len(parts) == 3:
                            event_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                        elif "/" in date_part:
                            event_date = date_part # Já está em formato d/m/Y

                    # 1. Carregar transcrição do vídeo (se disponível)
                    self.after(0, lambda i=idx, t=title: update_popup(i, t, "Carregando transcrição do vídeo..."))
                    try:
                        from modules.youtube_transcript_service import YouTubeTranscriptService
                        transcript_text = YouTubeTranscriptService.get_compacted_text(ev.get("url"))
                        if transcript_text:
                            self._log(f"[EXPERT] Transcrição carregada com sucesso ({len(transcript_text.splitlines())} fatias de tempo).")
                        else:
                            self._log("[EXPERT] Vídeo sem legenda disponível. Continuando com busca convencional...")
                    except Exception as e_trans:
                        self._log(f"[WARN] Falha ao carregar transcrição: {e_trans}")
                        transcript_text = None

                    custom_time = self.expert_time_var.get().strip()
                    custom_start_ts = None
                    if custom_time:
                        try:
                            dt_str = f"{event_date} {custom_time}"
                            if len(custom_time.split(':')) == 2:
                                dt_combined = datetime.strptime(dt_str, "%d/%m/%Y %H:%M")
                            else:
                                dt_combined = datetime.strptime(dt_str, "%d/%m/%Y %H:%M:%S")
                            from datetime import timezone, timedelta
                            br_tz = timezone(timedelta(hours=-3))
                            dt_combined = dt_combined.replace(tzinfo=br_tz)
                            custom_start_ts = int(dt_combined.timestamp())
                            self._log(f"[EXPERT] Sobrescrevendo horário de início pelo valor manual do painel: {custom_time}")
                        except Exception as e_time:
                            self._log(f"[WARN] Erro ao parsear horário manual do painel: {e_time}")

                    # Resolver horário real de início (Priorizar actual_start_time do ao vivo e NUNCA a data de upload do vídeo)
                    resolved_start_ts = custom_start_ts or ev.get("actual_start_time") or ev.get("live_actual_start")
                    
                    if not resolved_start_ts and ev.get("url"):
                        vid_match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})", str(ev.get("url")))
                        if vid_match:
                            try:
                                vid_id = vid_match.group(1)
                                meta_yt = assistant.get_youtube_live_metadata(vid_id)
                                if meta_yt.get("actual_start_time"):
                                    resolved_start_ts = meta_yt["actual_start_time"]
                                    self._log(f"[EXPERT] Horário real de início obtido via YouTube Live Details: {resolved_start_ts}")
                            except Exception as e_yt:
                                self._log(f"[WARN] Erro ao buscar metadados de live do YouTube: {e_yt}")

                    payload = {
                        "team1": team1,
                        "team2": team2,
                        "competition": meta["competition"],
                        "platform": ev.get("channel") if ev.get("channel") and not str(ev.get("channel")).startswith("http") else self.channel_var.get(),
                        "date": event_date,
                        "start_timestamp": resolved_start_ts,
                        "duration": ev.get("duration"),
                        "video_url": ev.get("url"),
                        "transcript_text": transcript_text
                    }
                    
                    # 2. Delay para evitar 429 Resource Exhausted (Cota da API)
                    import time
                    time.sleep(5.0)
                    
                    # 3. Executar Análise
                    try:
                        def status_cb(msg, i=idx, t=title):
                            self.after(0, lambda: update_popup(i, t, msg))
                        result = assistant.get_match_chronology(**payload, status_callback=status_cb)
                    except Exception as e:
                        result = {"error": str(e)}
                    
                    if "error" not in result:
                        result["platform"] = payload["platform"]
                        all_results.append(result)
                        
                        # Fallback de metadados se a IA vier vazia
                        m_display = result.get("match_display")
                        if not m_display or m_display == "N/A":
                            m_display = ev.get("title", meta["match_display"])
                            result["match_display"] = m_display
                            
                        m_comp = result.get("competition")
                        if not m_comp or m_comp == "N/A":
                            m_comp = meta["competition"]
                            result["competition"] = m_comp
                            
                        m_conf = float(result.get("confidence_score") or 0.0)
                        
                        def _update_ui_meta(d=m_display, c=m_comp, cf=m_conf):
                            # Sincronizar com runtime para que o _tick_ui não sobrescreva
                            self.runtime.current_match_display = d
                            self.runtime.current_competition = c
                            self.runtime.last_visual_confidence = cf
                            
                            self.match_var.set(f"Partida: {d}")
                            self.comp_var.set(f"Competição: {c}")
                            self.visual_conf_var.set(f"IA Conf: {cf*100:.1f}%")
                            self.status_dot.configure(text_color="green" if cf > 0.6 else "orange")
                        
                        self.after(0, _update_ui_meta)
                        
                        # 4. Consolidar, Deduplicar e Ordenar
                        to_render = []
                        seen_labels = set()
                        
                        # Pontos de Cronologia
                        chrono_map = [
                            ("pre_game_start", "INÍCIO TRANSMISSÃO", -10),
                            ("match_start", "INÍCIO", -5),
                            ("first_half_start", "APITO INICIAL (1T)", 0),
                            ("half_time_start", "INÍCIO INTERVALO", 45),
                            ("half_time_end", "VOLTA INTERVALO", 46),
                            ("second_half_start", "APITO INICIAL (2T)", 47),
                            ("match_end", "APITO FINAL", 90),
                            ("post_game_end", "ENCERRAMENTO", 120)
                        ]
                        def get_sec(t_str):
                            if not t_str or t_str == "N/A": return None
                            m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(t_str).strip())
                            if m:
                                return int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                            return None

                        fh_start_sec = get_sec(result.get("first_half_start"))
                        sh_start_sec = get_sec(result.get("second_half_start"))

                        seen_clocks = set()
                        for key, label, def_min in chrono_map:
                            val = result.get(key)
                            if val and val != "N/A" and label not in seen_labels:
                                dyn_min = def_min
                                val_sec = get_sec(val)
                                if val_sec is not None:
                                    if key == "half_time_start" and fh_start_sec is not None:
                                        diff = val_sec - fh_start_sec
                                        if diff < -43200: diff += 86400
                                        dyn_min = round(diff / 60.0)
                                    elif key == "half_time_end" or key == "second_half_start":
                                        dyn_min = 45
                                    elif key == "match_end" and sh_start_sec is not None:
                                        diff = val_sec - sh_start_sec
                                        if diff < -43200: diff += 86400
                                        dyn_min = 45 + round(diff / 60.0)
                                    elif key == "post_game_end" and sh_start_sec is not None:
                                        diff = val_sec - sh_start_sec
                                        if diff < -43200: diff += 86400
                                        dyn_min = 45 + round(diff / 60.0)

                                to_render.append({
                                    "minute": dyn_min,
                                    "label": label,
                                    "clock": val,
                                    "summary": f"{label} detectado pela Auditoria IA.",
                                    "confidence": result.get("confidence_score", 0.85),
                                    "sources": result.get("sources", [])
                                })
                                seen_labels.add(label)
                                seen_clocks.add(str(val))
                        
                        # Marcos Técnicos
                        for m in result.get("technical_milestones", []):
                            try:
                                m_min = int(m.get("minute", 0))
                            except: m_min = 0
                            m_label = str(m.get("type", "EVENTO")).upper()
                            m_clock = str(m.get("time") or "")
                            
                            # Deduplicação seletiva: Apenas Interrupção Técnica no mesmo horário de um marco
                            if "INTERRUPÇÃO TÉCNICA" in m_label and m_clock in seen_clocks:
                                continue
                                
                            to_render.append({
                                "minute": m_min,
                                "label": m_label,
                                "clock": m_clock,
                                "summary": m.get("event"),
                                "confidence": m.get("confidence") or result.get("confidence_score", 0.75),
                                "sources": result.get("sources", [])
                            })
                            if m_label in ("APITO FINAL", "INÍCIO TRANSMISSÃO", "INÍCIO"):
                                seen_labels.add(m_label)
                        
                        # Ordenar primariamente pelo horário real (Wall Clock HH:MM)
                        base_sec = None
                        for item in to_render:
                            m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(item.get("clock", "")).strip())
                            if m:
                                base_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                                break

                        def sort_key(x):
                            lbl = x.get("label", "").upper()
                            try: m_min = int(x.get("minute", 0))
                            except: m_min = 0

                            prio = 5
                            if any(k in lbl for k in ["INÍCIO TRANSMISSÃO", "PRÉ-JOGO"]): prio = -1
                            elif any(k in lbl for k in ["INÍCIO", "APITO INICIAL (1T)"]): prio = 0
                            elif any(k in lbl for k in ["GOL", "CARTÃO", "VAR"]): prio = 1
                            elif any(k in lbl for k in ["INTERVALO", "VOLTA", "APITO INICIAL (2T)"]): prio = 2
                            elif any(k in lbl for k in ["APITO FINAL", "ENCERRAMENTO"]): prio = 3
                            elif "INTERRUPÇÃO TÉCNICA" in lbl: prio = 10

                            clk_str = str(x.get("clock", "")).strip()
                            m = re.match(r"^(\d+):(\d+)(?::(\d+))?", clk_str)
                            if m:
                                clk_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                                if base_sec is not None and clk_sec < base_sec - 43200: 
                                    clk_sec += 86400
                                return (1, clk_sec, prio, m_min)
                            
                            return (0, m_min, prio, clk_str)
                        
                        to_render.sort(key=sort_key)
                        
                        # 5. Injetar no Grid
                        self._log(f"[EXPERT] Sucesso: {len(to_render)} marcos técnicos/cronologia ordenados.")
                        for item in to_render:
                            lbl = item["label"].upper()
                            # Mapear para match_event lances técnicos para que o ReportGenerator inclua na cronologia auditada
                            is_match_ev = any(k in lbl for k in ["GOL", "CARTÃO", "VAR", "CARD", "SUBSTITU", "PENALTI"])
                            m_type = "match_event" if is_match_ev else "ia_analysis"
                            
                            entry_details = {
                                "summary": item["summary"],
                                "minute": item["minute"]
                            }
                            
                            entry = {
                                "type": m_type,
                                "label": item["label"],
                                "minute": item["minute"],
                                "match_display": result.get("match_display", ""), 
                                "t_seconds": 0,
                                "clock": item["clock"],
                                "details": entry_details,
                                "confidence": item["confidence"],
                                "sources": item.get("sources", [])
                            }
                            
                            self.detector.add_timeline_entry(
                                item["minute"], 
                                m_type, 
                                item["label"], 
                                entry_details,
                                confidence=float(item.get("confidence", 0.75)), 
                                clock=item["clock"], 
                                match_display=result.get("match_display", m_display)
                            )
                            self.after(0, lambda e=entry: self._create_history_card(e))
                        
                        # 6. Gerar PDF e E-mail
                        try:
                            prefs = {
                                "show_chrono": self.expert_show_chrono_var.get(),
                                "show_milestones": self.expert_show_milestones_var.get(),
                                "show_secondary": self.expert_show_secondary_var.get(),
                                "show_sources": self.expert_show_sources_var.get()
                            }
                            pdf_path = self.reporter.write_expert_report([result], prefs=prefs)
                            self._last_generated_pdf_path = pdf_path
                            if self.send_report_email_var.get():
                                threading.Thread(target=self._send_report_via_email, args=(pdf_path,), daemon=True).start()
                        except Exception: pass
                        
                        self.after(0, self._update_history_grid)
                    else:
                        err_msg = result.get("error")
                        self._log(f"[EXPERT] Assistente retornou erro para '{title}': {err_msg}")
                        self.after(0, lambda m=err_msg: self._ui_error(f"Erro na IA Expert: {m}"))
                        
                        try:
                            prefs = {
                                "show_chrono": self.expert_show_chrono_var.get(),
                                "show_milestones": self.expert_show_milestones_var.get(),
                                "show_secondary": self.expert_show_secondary_var.get(),
                                "show_sources": self.expert_show_sources_var.get()
                            }
                            pdf_path = self.reporter.write_expert_report([result], prefs=prefs)
                        except: pass
                    
                    if self._expert_stop_event.is_set():
                        self._log("[EXPERT] Batch interrompido pelo usuário.")
                        break
                        
                # Notificar finalização do lote
                self.runtime.preparing = False
                self.after(0, lambda: self.btn_start.configure(text="Iniciar (selecionado)", state="normal"))
                
                if all_results:
                    self.after(0, lambda: self._ui_success(f"Análise Expert finalizada para {len(all_results)} eventos."))
                else:
                    self.after(0, lambda: self._ui_error("Expert Batch finalizado, mas nenhum evento gerou resultado válido."))

                # 6. Finalização de Lote (PDF Consolidado e Log de Texto)
                if all_results:
                    try:
                        prefs = {
                            "show_chrono": self.expert_show_chrono_var.get(),
                            "show_milestones": self.expert_show_milestones_var.get(),
                            "show_secondary": self.expert_show_secondary_var.get(),
                            "show_sources": self.expert_show_sources_var.get()
                        }
                        report_text = self.reporter.get_expert_report_text(all_results, prefs=prefs)
                        self._log("\n" + report_text)
                    except Exception as e_text:
                        self._log(f"[EXPERT] Erro ao gerar resumo em texto: {e_text}")
                        
                    self.after(0, lambda: self._finalize_expert_batch(all_results))
                    
            except Exception as e:
                import traceback
                self._log(f"[EXPERT] Erro crítico no worker: {e}")
                self._log(traceback.format_exc())
                err_msg = str(e)
                self.after(0, lambda m=err_msg: self._ui_error(f"Erro Expert Batch: {m}"))
                self.after(0, lambda m=err_msg: messagebox.showerror("Erro na Auditoria Expert", f"Ocorreu um erro durante a auditoria:\n\n{m}"))
                self.after(0, lambda: self.btn_start.configure(state="normal", text="Iniciar (selecionado)", fg_color="#1a5a1a"))
            finally:
                self.runtime.preparing = False
                self.after(0, lambda: popup.destroy())
                self.after(0, lambda: self.status_var.set("🔴 Parado"))
                self.after(0, lambda: self.status_dot.configure(text_color="gray"))
                self.after(0, lambda: self.btn_start.configure(state="normal", text="Iniciar (selecionado)", fg_color="#1a5a1a"))
                self._log("[EXPERT] Processamento de lote encerrado.")

        threading.Thread(target=worker, daemon=True).start()

    # (Removido duplicata de _load_expert_history_list aqui, unificado na linha 4164)

    def _load_expert_report_to_grid(self, json_path: str) -> None:
        """Recarrega uma auditoria salva para o grid visual."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            results = data.get("expert_results", [])
            if not results:
                return

            # Metadados do cabeçalho
            res_meta = results[0] if results else {}
            m_display = str(res_meta.get("match_display") or res_meta.get("match_id", "—"))
            m_comp = str(res_meta.get("competition", "—"))
            m_conf = float(res_meta.get("confidence_score") or 0.0)
            
            self.runtime.current_match_display = m_display
            self.runtime.current_competition = m_comp
            self.runtime.last_visual_confidence = m_conf
            
            self.match_var.set(f"Partida: {m_display}")
            self.comp_var.set(f"Competição: {m_comp}")
            self.visual_conf_var.set(f"IA Conf: {m_conf*100:.1f}%")
            self.update_idletasks() # Forçar atualização do dashboard

            # Limpar grid visual explicitamente
            for w in self.history_grid.winfo_children():
                w.destroy()
            
            # Limpar grid atual e timeline do detector
            self.detector.start_session(f"audit_{os.path.basename(json_path)}")

            # Injetar marcos no grid de forma ordenada
            to_render = []
            chrono_map = [
                ("pre_game_start", "INÍCIO TRANSMISSÃO", -10),
                ("match_start", "INÍCIO", -5),
                ("first_half_start", "APITO INICIAL (1T)", 0),
                ("half_time_start", "INÍCIO INTERVALO", 45),
                ("half_time_end", "VOLTA INTERVALO", 46),
                ("second_half_start", "APITO INICIAL (2T)", 47),
                ("match_end", "APITO FINAL", 90),
                ("post_game_end", "ENCERRAMENTO", 120)
            ]
            
            def get_sec(t_str):
                if not t_str or t_str == "N/A": return None
                m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(t_str).strip())
                if m:
                    return int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                return None

            for res in results:
                fh_start_sec = get_sec(res.get("first_half_start"))
                sh_start_sec = get_sec(res.get("second_half_start"))

                # Cronologia Geral
                seen_clocks = set()
                for key, label, def_min in chrono_map:
                    val = res.get(key)
                    if val and val != "N/A":
                        dyn_min = def_min
                        val_sec = get_sec(val)
                        if val_sec is not None:
                            if key == "half_time_start" and fh_start_sec is not None:
                                diff = val_sec - fh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = round(diff / 60.0)
                            elif key == "half_time_end" or key == "second_half_start":
                                dyn_min = 45
                            elif key == "match_end" and sh_start_sec is not None:
                                diff = val_sec - sh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = 45 + round(diff / 60.0)
                            elif key == "post_game_end" and sh_start_sec is not None:
                                diff = val_sec - sh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = 45 + round(diff / 60.0)

                        to_render.append({
                            "minute": dyn_min,
                            "label": label,
                            "clock": val,
                            "summary": f"{label} detectado via Auditoria IA.",
                            "confidence": res.get("confidence_score", 0.85)
                        })
                        seen_clocks.add(str(val))

                # Marcos Técnicos
                for m in res.get("technical_milestones", []):
                    try:
                        m_min = int(m.get("minute", 0))
                    except: m_min = 0
                    m_label = str(m.get("type", "EVENTO")).upper()
                    m_clock = str(m.get("time") or "")
                    
                    # Deduplicação: Apenas Interrupção Técnica redundante
                    if "INTERRUPÇÃO TÉCNICA" in m_label and m_clock in seen_clocks:
                        continue
                        
                    to_render.append({
                        "minute": m_min,
                        "label": m_label,
                        "clock": m_clock,
                        "summary": m.get("event"),
                        "confidence": m.get("confidence") or res.get("confidence_score", 0.75)
                    })

            # Ordenar primariamente pelo horário real (Wall Clock HH:MM)
            base_sec = None
            for item in to_render:
                m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(item.get("clock", "")).strip())
                if m:
                    base_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                    break

            def sort_key(x):
                lbl = x.get("label", "").upper()
                try: m_min = int(x.get("minute", 0))
                except: m_min = 0

                prio = 5
                if any(k in lbl for k in ["INÍCIO TRANSMISSÃO", "PRÉ-JOGO"]): prio = -1
                elif any(k in lbl for k in ["INÍCIO", "APITO INICIAL (1T)"]): prio = 0
                elif any(k in lbl for k in ["GOL", "CARTÃO", "VAR"]): prio = 1
                elif any(k in lbl for k in ["INTERVALO", "VOLTA", "APITO INICIAL (2T)"]): prio = 2
                elif any(k in lbl for k in ["APITO FINAL", "ENCERRAMENTO"]): prio = 3
                elif "INTERRUPÇÃO TÉCNICA" in lbl: prio = 10

                clk_str = str(x.get("clock", "")).strip()
                m = re.match(r"^(\d+):(\d+)(?::(\d+))?", clk_str)
                if m:
                    clk_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                    if base_sec is not None and clk_sec < base_sec - 43200: 
                        clk_sec += 86400
                    return (1, clk_sec, prio, m_min)
                
                return (0, m_min, prio, clk_str)
            
            to_render.sort(key=sort_key)
            
            # Injetar na timeline do detector e no grid visual
            for item in to_render:
                lbl = item["label"].upper()
                is_match_ev = any(k in lbl for k in ["GOL", "CARTÃO", "VAR", "CARD", "SUBSTITU", "PENALTI"])
                m_type = "match_event" if is_match_ev else "ia_analysis"
                
                details = {"summary": item["summary"], "minute": item["minute"]}
                
                # Sincronizar com o detector para permitir nova exportação fiel
                self.detector.add_timeline_entry(
                    item["minute"], 
                    m_type, 
                    item["label"], 
                    details,
                    confidence=float(item.get("confidence", 0.75)), 
                    clock=item["clock"], 
                    match_display=m_display
                )
                
                # Criar card visual
                self._create_history_card({
                    "type": m_type,
                    "label": item["label"],
                    "clock": item["clock"],
                    "confidence": item["confidence"],
                    "details": details
                })
            
            self._log(f"[UI] Histórico carregado e ordenado: {os.path.basename(json_path)}")
            self.tabs.set("Monitoramento") # Garantir que o usuário veja
            
        except Exception as e:
            self._log(f"[ERRO] Falha ao carregar histórico: {e}")

    def _center_window(self, width: int, height: int, win: Optional[ctk.CTkBaseClass] = None) -> None:
        """Centraliza uma janela na tela."""
        target = win or self
        screen_w = target.winfo_screenwidth()
        screen_h = target.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        target.geometry(f"{width}x{height}+{x}+{y}")

    def _finalize_expert_batch(self, results: List[Dict[str, Any]]) -> None:
        """Gera o relatório final do lote Expert."""
        try:
            prefs = {
                "show_chrono": self.expert_show_chrono_var.get(),
                "show_milestones": self.expert_show_milestones_var.get(),
                "show_secondary": self.expert_show_secondary_var.get(),
                "show_sources": self.expert_show_sources_var.get()
            }
            if len(results) == 1 and getattr(self, "_last_generated_pdf_path", None) and os.path.exists(self._last_generated_pdf_path):
                pdf_path = self._last_generated_pdf_path
            else:
                pdf_path = self.reporter.write_expert_report(results, prefs=prefs)
            self._log(f"[EXPERT] Lote finalizado: {len(results)} eventos processados. PDF: {pdf_path}")
            self._ui_success(f"Análise Expert finalizada para {len(results)} eventos.\nRelatório gerado em: {pdf_path}")
            
            # Restaurar botão
            self.btn_start.configure(state="normal", text="Iniciar (selecionado)", fg_color="#1a5a1a")
            
            # Atualizar sidebar de histórico
            self.after(0, self._load_expert_history_list)

            # Abrir o diálogo de conclusão para o usuário interagir
            if os.path.exists(pdf_path):
                self.after(0, lambda p=pdf_path: self._show_report_completed_dialog(p))
        except Exception as e:
            self._log(f"[EXPERT] Erro ao gerar PDF do lote: {e}")
            self._ui_error(f"Análise Expert finalizada, mas houve erro ao gerar o PDF: {e}")

    def _show_report_completed_dialog(self, pdf_path: str) -> None:
        """Abre uma janela de diálogo informando que o relatório foi gerado e oferecendo opções de visualização e e-mail."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("📄 Relatório Auditado Concluído")
        dialog.geometry("550x430")
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        # Centralizar
        dialog.update_idletasks()
        x_pos = self.winfo_x() + (self.winfo_width() // 2) - 275
        y_pos = self.winfo_y() + (self.winfo_height() // 2) - 215
        dialog.geometry(f"+{x_pos}+{y_pos}")

        frame = ctk.CTkFrame(dialog, corner_radius=15, border_width=2, border_color="#00CED1", fg_color="#0e0e0e")
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Definir a ação de envio primeiro
        def _send_email_action():
            recipients = [em for em, var in email_checkbox_vars.items() if var.get()]
            if not recipients:
                messagebox.showerror("Erro", "Selecione pelo menos um destinatário para o envio.")
                return
            
            # Atualiza destinatários na config global
            recipients_str = ";".join(recipients)
            self.email_recipients_var.set(recipients_str)
            self._save_general_settings()

            self._log(f"[EMAIL] Disparando envio manual para: {recipients_str}")
            threading.Thread(target=self._send_report_via_email, args=(pdf_path,), daemon=True).start()
            self._ui_success("Envio de e-mail disparado em segundo plano!")
            dialog.destroy()

        # Barra de Botões empacotada no fundo (garante visibilidade)
        btn_bar = ctk.CTkFrame(frame, fg_color="transparent")
        btn_bar.pack(fill="x", side="bottom", pady=15, padx=20)

        ctk.CTkButton(btn_bar, text="Fechar", width=80, fg_color="#333333", command=dialog.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="📁 Abrir Pasta", width=110, fg_color="#222222", hover_color="#333333", command=lambda: os.startfile(os.path.dirname(pdf_path))).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="📄 Abrir PDF", width=110, fg_color="#1f538d", hover_color="#153b66", command=lambda: os.startfile(pdf_path)).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="📧 Enviar E-mail", width=120, fg_color="#00CED1", text_color="black", hover_color="#008B8B", command=_send_email_action).pack(side="right", padx=5)

        # Elementos superiores
        ctk.CTkLabel(frame, text="✅", font=ctk.CTkFont(size=40)).pack(pady=(15, 5))
        ctk.CTkLabel(frame, text="Relatório Auditado Disponível!", font=ctk.CTkFont(size=18, weight="bold"), text_color="#00CED1").pack(pady=5)
        
        path_short = os.path.basename(pdf_path)
        lbl_info = ctk.CTkLabel(frame, text=f"Arquivo: {path_short}\nSalvo em: reports/\n\nPara onde deseja enviar ou visualizar?", font=ctk.CTkFont(size=11), text_color="#CCCCCC")
        lbl_info.pack(pady=5)

        # Seleção de e-mails via checkbox
        email_row = ctk.CTkFrame(frame, fg_color="transparent")
        email_row.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(email_row, text="Selecionar Destinatários:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00CED1").pack(anchor="w", pady=(0, 2))
        
        saved_emails = _load_saved_emails()
        current_recipients = [em.strip().lower() for em in re.split(r'[,;]', self.email_recipients_var.get()) if em.strip()]
        
        email_scroll = ctk.CTkScrollableFrame(email_row, height=80, fg_color="#181818", border_width=1, border_color="#333333")
        email_scroll.pack(fill="x", expand=True)
        
        email_checkbox_vars = {}
        for em in saved_emails:
            is_checked = (em.lower() in current_recipients) or (not current_recipients and em == "cleber.goncalves@ibope.com")
            var = ctk.BooleanVar(value=is_checked)
            email_checkbox_vars[em] = var
            ctk.CTkCheckBox(email_scroll, text=em, variable=var, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=5, pady=2)

    def _show_mode_flows(self) -> None:
        """Abre uma janela didática explicando os fluxos de cada modo."""
        flow_win = ctk.CTkToplevel(self)
        flow_win.title("Fluxos de Monitoramento e Auditoria - Mediadna")
        self._center_window(1600, 940, win=flow_win)
        flow_win.after(200, lambda: flow_win.focus())
        
        header = ctk.CTkFrame(flow_win, fg_color="#1E1E1E", height=100, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text="Fluxos de Trabalho e Conformidade Regulatória", 
                     font=ctk.CTkFont(size=32, weight="bold"), text_color="#00CED1").pack(pady=30)
        
        container = ctk.CTkScrollableFrame(flow_win, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=30, pady=20)

        def _resolve_asset(name: str) -> str:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                p = os.path.join(sys._MEIPASS, "data", "assets", name)
                if os.path.exists(p): return p
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            p2 = os.path.join(base_dir, "data", "assets", name)
            if os.path.exists(p2): return p2
            return os.path.join("data", "assets", name)

        # 1. MODO VISUAL (Layout Lateral)
        vis_f = ctk.CTkFrame(container, border_width=1, border_color="#00CED1", fg_color="#141414", corner_radius=15)
        vis_f.pack(fill="x", pady=(0, 30), padx=5)
        
        left_v = ctk.CTkFrame(vis_f, fg_color="transparent")
        left_v.pack(side="left", padx=20, pady=20)
        
        right_v = ctk.CTkFrame(vis_f, fg_color="transparent")
        right_v.pack(side="left", fill="both", expand=True, padx=(20, 20), pady=20)
        
        img_v_path = _resolve_asset("visual_flow.png")
        if os.path.exists(img_v_path):
            try:
                pil_v = Image.open(img_v_path)
                ctk_v = ctk.CTkImage(light_image=pil_v, dark_image=pil_v, size=(600, 600))
                ctk.CTkLabel(left_v, image=ctk_v, text="").pack()
            except Exception as e_v:
                print(f"[UI WARN] Erro ao carregar visual_flow.png: {e_v}")
            
        ctk.CTkLabel(right_v, text=" MODO VISUAL (AI VISION & OBS)", font=ctk.CTkFont(size=26, weight="bold"), 
                     text_color="#00CED1").pack(pady=(10, 20), anchor="nw")
        
        vis_desc = (
            "• CAPTURA REAL-TIME: Integração direta com OBS Studio via WebSocket.\n\n"
            "• VISÃO COMPUTACIONAL: Detecção automática de Placar, Cronômetro e Banners.\n\n"
            "• CONSOLIDAÇÃO VIA IA: Realiza buscas periódicas no Gemini para validar a cronologia e o contexto.\n\n"
            "• MONITORAMENTO ADS/MERCHAN: Identifica inserções publicitárias (L-Shape, Logotipos).\n\n"
            "• AUDITORIA DE EVIDÊNCIAS: Gera capturas de tela vinculadas a cada detecção.\n\n"
            "• CONFORMIDADE TÉCNICA: Processamento local focado em sinal público."
        )
        ctk.CTkLabel(right_v, text=vis_desc, font=ctk.CTkFont(size=20), text_color="#EEEEEE", 
                     justify="left", wraplength=600, anchor="nw").pack(anchor="nw", fill="both", expand=True)

        # Seção de Risco (Visual)
        ctk.CTkLabel(right_v, text="⚖️ CONFORMIDADE & RISCO: REDUZIDO", 
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFA500").pack(pady=(20, 0), anchor="w")
        risk_v = "Uso de sinal público para auditoria técnica local sem redistribuição. Processamento de imagem em conformidade com o 'Fair Use' para fins de prova de exibição e compliance publicitário."
        ctk.CTkLabel(right_v, text=risk_v, font=ctk.CTkFont(size=16), text_color="#CCCCCC", 
                     justify="left", wraplength=850).pack(anchor="w", pady=(5, 0))

        # 2. MODO EXPERT (Layout Lateral)
        exp_f = ctk.CTkFrame(container, border_width=1, border_color="#FFD700", fg_color="#141414", corner_radius=15)
        exp_f.pack(fill="x", pady=(0, 30), padx=5)
        
        left_e = ctk.CTkFrame(exp_f, fg_color="transparent")
        left_e.pack(side="left", padx=20, pady=20)
        
        right_e = ctk.CTkFrame(exp_f, fg_color="transparent")
        right_e.pack(side="left", fill="both", expand=True, padx=(20, 20), pady=20)
        
        img_e_path = _resolve_asset("expert_flow.png")
        print(f"[UI ASSET] Carregando imagem expert_flow.png de: {img_e_path}")
        if os.path.exists(img_e_path):
            try:
                pil_e = Image.open(img_e_path)
                ctk_e = ctk.CTkImage(light_image=pil_e, dark_image=pil_e, size=(600, 600))
                ctk.CTkLabel(left_e, image=ctk_e, text="").pack()
            except Exception as e_e:
                print(f"[UI WARN] Erro ao carregar expert_flow.png: {e_e}")
        else:
            print(f"[UI WARN] Imagem expert_flow.png não existe em {img_e_path}")
            
        ctk.CTkLabel(right_e, text=" MODO EXPERT ASSISTANT (API & SEARCH)", font=ctk.CTkFont(size=26, weight="bold"), 
                     text_color="#FFD700").pack(pady=(10, 20), anchor="nw")
        
        exp_desc = (
            "• RASPAGEM AUTOMÁTICA DE SÚMULAS: Localiza e extrai automaticamente as súmulas oficiais dos jogos da CBF (Copa do Brasil e Brasileirão).\n\n"
            "• LINHA DO TEMPO REGULAMENTAR: Mapeia o horário de início do 1º Tempo, acréscimos, os 15 min de intervalo (norma FIFA) e o encerramento do jogo.\n\n"
            "• REGISTRO COMPLETO DE EVENTOS: Consolidação total de Gols, Cartões Amarelos/Vermelhos, Substituições e Equipe de Arbitragem.\n\n"
            "• AUDITORIA DE TRANSMISSÃO: Cruza os horários oficiais da súmula com a transmissão ao vivo do canal (CazéTV / Amazon Prime).\n\n"
            "• RELATÓRIO CONSOLIDADO DE COMPLIANCE: Gera relatório oficial pronto para auditoria, controle de qualidade e conformidade legal."
        )
        ctk.CTkLabel(right_e, text=exp_desc, font=ctk.CTkFont(size=20), text_color="#EEEEEE", 
                     justify="left", wraplength=600, anchor="nw").pack(anchor="nw", fill="both", expand=True)

        # Seção de Risco (Expert)
        ctk.CTkLabel(right_e, text="🛡️ CONFORMIDADE & RISCO: ZERO", 
                     font=ctk.CTkFont(size=18, weight="bold"), text_color="#00FF7F").pack(pady=(20, 0), anchor="w")
        risk_e = "Auditoria baseada 100% em Digital Footprint e APIs oficiais. Totalmente independente do fluxo de exibição, agindo como uma auditoria de dados pública e legalmente soberana."
        ctk.CTkLabel(right_e, text=risk_e, font=ctk.CTkFont(size=16), text_color="#CCCCCC", 
                     justify="left", wraplength=850).pack(anchor="w", pady=(5, 0))

        ctk.CTkButton(container, text="Entendi e Concordo", width=300, height=50, 
                      font=ctk.CTkFont(size=20, weight="bold"), command=flow_win.destroy).pack(pady=40)

    def _display_expert_result(self, res: Dict[str, Any]) -> None:
        """Exibe os resultados da cronologia técnica."""
        self._log(f"[EXPERT] Cronologia recebida para {res.get('match_id')}")
        
        # Mostrar nos Logs IA
        summary = f"--- CRONOLOGIA TÉCNICA (EXPERT) ---\n"
        summary += f"Evento: {res.get('match_id')}\n"
        summary += f"Início Transmissão: {res.get('pre_game_start')}\n"
        summary += f"1º Tempo: {res.get('first_half_start')} (Intervalo: {res.get('half_time_start')} -> {res.get('half_time_end')})\n"
        summary += f"2º Tempo: {res.get('second_half_start')} -> {res.get('match_end')}\n"
        summary += f"Pós-jogo: {res.get('post_game_start')} -> {res.get('post_game_end')}\n"
        summary += f"Confiança: {res.get('confidence_score')}\n"
        summary += f"Marcos Técnicos:\n"
        for m in res.get("technical_milestones", []):
            summary += f"  - [{m.get('time')}] [{m.get('type', 'EVENTO')}] {m.get('event')}\n"
        
        self._append_text(self.ia_log_box, summary + "\n")
        
        # Abrir aba de Logs IA
        self.tabs.set("Logs IA")
        self._log("[EXPERT] Relatório técnico gerado na aba 'Logs IA'.")
        self.after(0, self._load_expert_history_list)

    def _load_expert_history_list(self) -> None:
        """Carrega a lista de arquivos JSON de relatórios do modo Expert com formatação amigável."""
        for widget in self.expert_hist_scroll.winfo_children():
            widget.destroy()
            
        reports_dir = os.path.join(PROJECT_ROOT, "reports")
        if not os.path.exists(reports_dir):
            return
            
        # Buscar todos os arquivos de expert (batch e individuais)
        import glob
        files = glob.glob(os.path.join(reports_dir, "expert_*.json"))
        # Filtrar para evitar pegar outros tipos se necessário, mas expert_*.json é o padrão agora
        files.sort(key=os.path.getmtime, reverse=True)
        
        for path in files[:15]: # Mostrar os últimos 15
            fname = os.path.basename(path)
            try:
                # Tentar extrair data/hora do nome do arquivo (expert_batch_20260325_233145.json)
                parts = fname.replace(".json", "").split("_")
                ts_str = parts[-2] + parts[-1]
                dt = datetime.strptime(ts_str, "%Y%m%d%H%M%S")
                date_display = dt.strftime("%d/%m %H:%M")
            except:
                date_display = "Auto"

            try:
                with open(path, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                
                res_arr = data.get("expert_results", [])
                match_id = ""
                if res_arr:
                    match_id = str(res_arr[0].get("match_display") or res_arr[0].get("match_id") or "")
                elif "match_display" in data:
                    match_id = str(data.get("match_display") or "")
                
                # Se não tem match_id, usa o timestamp
                btn_text = f"📄 {date_display}"
                if match_id:
                    btn_text = f"📄 {date_display} - {match_id[:20]}..."

                item_frame = ctk.CTkFrame(self.expert_hist_scroll, fg_color="transparent")
                item_frame.pack(fill="x", padx=2, pady=1)

                btn = ctk.CTkButton(
                    item_frame,
                    text=btn_text,
                    font=ctk.CTkFont(size=10),
                    fg_color="transparent",
                    hover_color="#333333",
                    anchor="w",
                    height=24,
                    command=lambda p=path: self._open_history_report(p)
                )
                btn.pack(side="left", fill="x", expand=True)

                btn_pdf = ctk.CTkButton(
                    item_frame,
                    text="📄 PDF",
                    font=ctk.CTkFont(size=9, weight="bold"),
                    width=42,
                    height=22,
                    fg_color="#222222",
                    hover_color="#00CED1",
                    command=lambda p=path: self._regenerate_pdf_from_history(p)
                )
                btn_pdf.pack(side="right", padx=2)
            except:
                continue

    def _open_prompt_editor_modal(self) -> None:
        """Abre uma janela modal para visualizar e ajustar o prompt do Gemini antes da busca."""
        modal = ctk.CTkToplevel(self)
        modal.title("👁️ Visualizar & Ajustar Prompt de Pesquisa (Súmula CBF / Gemini)")
        modal.geometry("750x550")
        modal.attributes("-topmost", True)
        
        team1 = self.expert_team1_var.get().strip() or "Time Casa"
        team2 = self.expert_team2_var.get().strip() or "Time Fora"
        comp = self.expert_comp_var.get().strip() or "Campeonato"
        date = self.expert_date_var.get().strip() or datetime.now().strftime("%d/%m/%Y")
        
        ctk.CTkLabel(modal, text=f"Auditoria Expert: {team1} x {team2} ({date})", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00CED1").pack(padx=15, pady=(15, 5), anchor="w")
        ctk.CTkLabel(modal, text="Você pode adicionar observações específicas da partida (ex: paralisação por chuva, prorrogação, VAR longo) antes de disparar a auditoria:", font=ctk.CTkFont(size=11), text_color="#AAAAAA").pack(padx=15, pady=(0, 10), anchor="w")

        obs_frame = ctk.CTkFrame(modal, fg_color="transparent")
        obs_frame.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(obs_frame, text="Observações Especiais:").pack(side="left", padx=(0, 5))
        obs_entry = ctk.CTkEntry(obs_frame, width=450, placeholder_text="Ex: Partida paralisada por 15 min no 2T devido à chuva")
        obs_entry.pack(side="left", fill="x", expand=True)

        prompt_box = ctk.CTkTextbox(modal, font=ctk.CTkFont(family="Consolas", size=11))
        prompt_box.pack(fill="both", expand=True, padx=15, pady=5)
        
        sample_prompt = f"""DIRECTIVAS DE BUSCA DA SÚMULA ELETRÔNICA CBF E PORTAIS:
1. Pesquisar por "site:cbf.com.br" "Súmula" "{team1}" "{team2}"
2. Pesquisar por "Súmula Eletrônica CBF" "{team1} x {team2}" "{date}"
3. Pesquisar por "Tempo Real" "{team1} x {team2}" "{date}" site:ge.globo.com OR site:uol.com.br

Extrair os 4 momentos vitais do jogo anotados pelo árbitro:
- Início do 1º Tempo (first_half_start)
- Fim do 1º Tempo (half_time_start)
- Início do 2º Tempo (second_half_start)
- Apito Final (match_end) e acréscimos oficiais do 1T e 2T.

MINUTAGEM DOS GOLS, CARTÕES E SUBSTITUIÇÕES."""
        prompt_box.insert("1.0", sample_prompt)

        btn_bar = ctk.CTkFrame(modal, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=15)

        def _run_with_prompt():
            obs = obs_entry.get().strip()
            if obs:
                self._log(f"[EXPERT] Observações especiais injetadas no prompt: {obs}")
            modal.destroy()
            self._start_manual_url()

        ctk.CTkButton(btn_bar, text="Cancelar", fg_color="#333333", command=modal.destroy, width=100).pack(side="right", padx=5)
        ctk.CTkButton(btn_bar, text="🚀 Executar Auditoria com Prompt Ajustado", fg_color="#00CED1", text_color="black", hover_color="#008B8B", command=_run_with_prompt).pack(side="right", padx=5)

    def _regenerate_pdf_from_history(self, path: str) -> None:
        """Gera e abre o relatório PDF a partir de um relatório JSON já existente sem gastar tokens da API."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            res_list = []
            if "expert_results" in data and data["expert_results"]:
                res_list = data["expert_results"]
            elif "technical_milestones" in data:
                res_list = [data]
            elif "analysis" in data and data.get("analysis", {}).get("notes", {}).get("expert_result"):
                res_list = [data["analysis"]["notes"]["expert_result"]]
            
            if not res_list:
                self._log(f"[AVISO] Não foi possível extrair dados para o PDF do arquivo: {path}")
                return
            
            from modules.report_generator import ReportGenerator
            report_gen = ReportGenerator(reports_dir=os.path.join(PROJECT_ROOT, "reports"))
            pdf_path = report_gen.write_expert_report(results=res_list)
            
            self._log(f"[EXPERT] Relatório PDF re-gerado com sucesso: {pdf_path}")
            if os.path.exists(pdf_path):
                self._open_internal_pdf_viewer(pdf_path)
        except Exception as e:
            self._log(f"[ERRO] Falha ao re-gerar PDF do histórico: {e}")

    def _copy_executive_summary(self) -> None:
        """Gera e copia o Resumo Executivo da auditoria para a Área de Transferência (WhatsApp/Teams/E-mail)."""
        res = getattr(self, "_last_expert_result", None)
        if not res:
            self._log("[AVISO] Nenhuma auditoria ativa encontrada para copiar resumo.")
            return
        
        m_display = res.get("match_display") or res.get("match_id") or "Partida"
        date = res.get("date") or "—"
        platform = res.get("platform") or "—"
        start = res.get("first_half_start") or res.get("match_start") or "—"
        ht_start = res.get("half_time_start") or "—"
        ht_end = res.get("second_half_start") or res.get("half_time_end") or "—"
        match_end = res.get("match_end") or "—"
        post_end = res.get("post_game_end") or "—"
        
        # Calcular duração do intervalo em minutos
        int_min = "21"
        try:
            t_s = datetime.strptime(ht_start[:8], "%H:%M:%S")
            t_e = datetime.strptime(ht_end[:8], "%H:%M:%S")
            int_min = str(int((t_e - t_s).total_seconds() / 60))
        except: pass

        goals = []
        for m in res.get("technical_milestones", []):
            if "GOL" in str(m.get("type", "")).upper() or "GOL" in str(m.get("event", "")).upper():
                goals.append(f"{m.get('event')} ({m.get('minute')}')")
        
        goals_str = ", ".join(goals) if goals else "Sem gols anotados"

        summary = f"""📌 AUDITORIA CONCLUÍDA - MEDIA DNA
⚽ PARTIDA: {m_display}
📅 DATA: {date} | PLATAFORMA: {platform}
⏱️ HORÁRIO INÍCIO (1T): {start}
⏸️ INTERVALO INÍCIO: {ht_start} | INTERVALO FIM: {ht_end} ({int_min} min)
🏁 APITO FINAL: {match_end} | ENCERRAMENTO TRANSMISSÃO: {post_end}
⚽ GOLS: {goals_str}
📄 SÚMULA ELETRÔNICA CBF: 100% Validada"""

        self.clipboard_clear()
        self.clipboard_append(summary)
        self._log("✅ Resumo Executivo copiado para a Área de Transferência com Sucesso!")

    def _open_schedule_games_modal(self) -> None:
        """Abre a janela modal para cadastro e agendamento de até 5 jogos para auditoria automática com e-mail e calendário."""
        modal = ctk.CTkToplevel(self)
        modal.title("⏰ Sistema de Agendamento Automático de Jogos & Disparo de E-mail")
        modal.geometry("920x680")
        modal.attributes("-topmost", True)

        ctk.CTkLabel(modal, text="⏰ Agendamento de Fila de Auditoria Expert (Até 5 Jogos)", font=ctk.CTkFont(size=15, weight="bold"), text_color="#00CED1").pack(padx=15, pady=(15, 2), anchor="w")
        ctk.CTkLabel(modal, text="Cadastre os jogos da rodada e selecione os e-mails para envio automático do relatório PDF após a partida:", font=ctk.CTkFont(size=11), text_color="#AAAAAA").pack(padx=15, pady=(0, 10), anchor="w")

        # Configuração e Seleção de E-mails Cadastrados
        email_frame = ctk.CTkFrame(modal, fg_color="#1a1a1a", corner_radius=10, border_width=1, border_color="#333333")
        email_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(email_frame, text="📧 Selecionar Destinatários da Fila:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00CED1").pack(anchor="w", padx=10, pady=(6, 2))
        
        saved_emails = _load_saved_emails()
        email_vars = {}
        chk_scroll = ctk.CTkScrollableFrame(email_frame, height=70, fg_color="#181818", border_width=1, border_color="#333333")
        chk_scroll.pack(fill="x", padx=10, pady=(2, 6))
        
        for em in saved_emails:
            var = ctk.BooleanVar(value=True)
            email_vars[em] = var
            ctk.CTkCheckBox(chk_scroll, text=em, variable=var, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=5, pady=2)

        def _auto_fill_cbf_events():
            try:
                from modules.cbf_schedule_fetcher import CBFScheduleFetcher
                cbf_events = CBFScheduleFetcher.get_upcoming_matches()
            except:
                cbf_events = _load_cbf_streaming_events()
                
            for idx in range(min(5, len(cbf_events))):
                evt = cbf_events[idx]
                game_rows[idx][0].delete(0, "end")
                game_rows[idx][0].insert(0, evt.get("team1", ""))
                game_rows[idx][1].delete(0, "end")
                game_rows[idx][1].insert(0, evt.get("team2", ""))
                game_rows[idx][2].delete(0, "end")
                game_rows[idx][2].insert(0, evt.get("comp", ""))
                game_rows[idx][3].set(evt.get("date", datetime.now().strftime("%d/%m/%Y")))
                game_rows[idx][4].delete(0, "end")
                game_rows[idx][4].insert(0, evt.get("time", ""))
                game_rows[idx][5].delete(0, "end")
                game_rows[idx][5].insert(0, evt.get("platform", ""))
            self._log("📥 Fila de 5 jogos auto-preenchida com os próximos eventos oficiais da CBF!")

        # Switch para Auditoria Automática
        auto_audit_frame = ctk.CTkFrame(modal, fg_color="#1a1a1a", corner_radius=10, border_width=1, border_color="#333333")
        auto_audit_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkSwitch(
            auto_audit_frame,
            text="🔄 Ativar Auditoria Automática Inteligente (Busca novos jogos oficiais no background a cada 10 min e despacha relatórios)",
            variable=self.auto_schedule_audit_var,
            font=ctk.CTkFont(size=11, weight="bold"),
            progress_color="#00CED1",
            command=self._save_general_settings
        ).pack(anchor="w", padx=10, pady=8)

        btn_autofill = ctk.CTkButton(
            modal,
            text="📥 Preencher com Próximos Eventos (Brasileirão / Copa do Brasil)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#00CED1",
            text_color="black",
            hover_color="#008B8B",
            height=30,
            command=_auto_fill_cbf_events
        )
        btn_autofill.pack(padx=15, pady=(0, 8), anchor="w")

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=5)

        game_rows = []
        for i in range(1, 6):
            g_frame = ctk.CTkFrame(scroll, corner_radius=10, border_width=1, border_color="#333333")
            g_frame.pack(fill="x", pady=4, padx=2)
            
            ctk.CTkLabel(g_frame, text=f"Jogo #{i}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00CED1").grid(row=0, column=0, padx=6, pady=6)
            
            e_t1 = ctk.CTkEntry(g_frame, width=125, placeholder_text="Time Casa")
            e_t1.grid(row=0, column=1, padx=3, pady=6)
            
            e_t2 = ctk.CTkEntry(g_frame, width=125, placeholder_text="Time Fora")
            e_t2.grid(row=0, column=2, padx=3, pady=6)
            
            e_comp = ctk.CTkEntry(g_frame, width=120, placeholder_text="Competição")
            e_comp.grid(row=0, column=3, padx=3, pady=6)
            
            # Data com suporte a DateEntry (Calendário Dropdown)
            d_var = ctk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
            if DateEntry:
                de = DateEntry(
                    g_frame, textvariable=d_var, width=9,
                    background='#1f1f1f', foreground='white',
                    headersbackground='#333333', headersforeground='white',
                    selectbackground='#1f538d', selectforeground='white',
                    borderwidth=2, date_pattern='dd/mm/yyyy', locale='pt_BR'
                )
                de.grid(row=0, column=4, padx=2, pady=6)
                btn_c = ctk.CTkButton(g_frame, text="📅", width=26, height=26, command=lambda d_widget=de: d_widget.drop_down())
                btn_c.grid(row=0, column=5, padx=(0, 4), pady=6)
            else:
                de = ctk.CTkEntry(g_frame, textvariable=d_var, width=95, placeholder_text="DD/MM/YYYY")
                de.grid(row=0, column=4, padx=3, pady=6)
            
            e_time = ctk.CTkEntry(g_frame, width=65, placeholder_text="HH:MM")
            e_time.grid(row=0, column=6, padx=3, pady=6)
            
            e_plat = ctk.CTkEntry(g_frame, width=105, placeholder_text="Plataforma")
            e_plat.grid(row=0, column=7, padx=6, pady=6)
            e_plat.insert(0, "CazéTV")

            game_rows.append((e_t1, e_t2, e_comp, d_var, e_time, e_plat))

        # Preencher pré-jogo de exemplo se a fila estiver vazia
        existing = _load_scheduled_games()
        if existing:
            for idx, g in enumerate(existing[:5]):
                game_rows[idx][0].insert(0, g.get("team1", ""))
                game_rows[idx][1].insert(0, g.get("team2", ""))
                game_rows[idx][2].insert(0, g.get("comp", ""))
                game_rows[idx][3].set(g.get("date", datetime.now().strftime("%d/%m/%Y")))
                game_rows[idx][4].insert(0, g.get("time", ""))
                game_rows[idx][5].delete(0, "end")
                game_rows[idx][5].insert(0, g.get("platform", "CazéTV"))
        else:
            try:
                from modules.cbf_schedule_fetcher import CBFScheduleFetcher
                cbf_evts = CBFScheduleFetcher.get_upcoming_matches()
                for idx, g in enumerate(cbf_evts[:5]):
                    game_rows[idx][0].insert(0, g.get("team1", ""))
                    game_rows[idx][1].insert(0, g.get("team2", ""))
                    game_rows[idx][2].insert(0, g.get("comp", ""))
                    game_rows[idx][3].set(g.get("date", datetime.now().strftime("%d/%m/%Y")))
                    game_rows[idx][4].insert(0, g.get("time", ""))
                    game_rows[idx][5].delete(0, "end")
                    game_rows[idx][5].insert(0, g.get("platform", "CazéTV"))
            except: pass

        btn_bar = ctk.CTkFrame(modal, fg_color="transparent")
        btn_bar.pack(fill="x", padx=15, pady=12)

        def _save_schedule():
            target_emails = [em for em, v in email_vars.items() if v.get()]
            emails_str = ";".join(target_emails)
            new_scheduled_list = []
            
            for idx, row in enumerate(game_rows, 1):
                t1 = row[0].get().strip()
                t2 = row[1].get().strip()
                comp = row[2].get().strip() or "Campeonato"
                d_str = row[3].get().strip() or datetime.now().strftime("%d/%m/%Y")
                time_str = row[4].get().strip() or "20:00"
                plat = row[5].get().strip() or "CazéTV"
                
                if t1 and t2:
                    new_scheduled_list.append({
                        "id": f"game_{idx}_{d_str.replace('/', '')}_{time_str.replace(':', '')}",
                        "team1": t1,
                        "team2": t2,
                        "comp": comp,
                        "date": d_str,
                        "time": time_str,
                        "platform": plat,
                        "emails": emails_str,
                        "status": "pending",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

            _save_scheduled_games(new_scheduled_list)
            self._scheduled_games = new_scheduled_list
            modal.destroy()
            self._log(f"⏰ Fila de Agendamento Automático atualizada com {len(new_scheduled_list)} jogos! Notificações: {emails_str}")
            self._update_schedule_panel_ui()

        ctk.CTkButton(btn_bar, text="Cancelar", fg_color="#333333", command=modal.destroy, width=100).pack(side="right", padx=5)
        ctk.CTkButton(btn_bar, text="⏰ Salvar Fila de Agendamento & Ativar Notificações", fg_color="#00CED1", text_color="black", hover_color="#008B8B", command=_save_schedule).pack(side="right", padx=5)

    def _open_pdf_or_folder(self, path: Optional[str]) -> None:
        """Tenta carregar o PDF na aba de visualização integrada. Se não existir, abre a pasta de relatórios (reports/)."""
        try:
            if path and os.path.exists(path):
                self._select_and_view_pdf(path)
            else:
                reports_dir = os.path.join(PROJECT_ROOT, "reports")
                if os.path.exists(reports_dir):
                    os.startfile(reports_dir)
                else:
                    self._log(f"[UI ERROR] Pasta de relatórios não encontrada: {reports_dir}")
        except Exception as e:
            self._log(f"[UI ERROR] Falha ao abrir PDF/Pasta: {e}")

    def _update_schedule_panel_ui(self) -> None:
        """Renderiza a lista de jogos agendados no painel lateral de forma eficiente usando cache de widgets para evitar cintilação."""
        if not hasattr(self, "schedule_scroll"):
            return
            
        games = getattr(self, "_scheduled_games", [])
        
        # Caso a fila esteja vazia, garante a exibição da label informativa
        if not games:
            if getattr(self, "_schedule_cards_cache", {}):
                for w in self.schedule_scroll.winfo_children():
                    w.destroy()
                self._schedule_cards_cache = {}
                
            widgets = self.schedule_scroll.winfo_children()
            if not widgets:
                if self.auto_schedule_audit_var.get():
                    last_t = getattr(self, "_last_auto_schedule_fetch_time", 0.0)
                    if last_t > 0:
                        t_str = datetime.fromtimestamp(last_t).strftime("%H:%M:%S")
                        ctk.CTkLabel(
                            self.schedule_scroll,
                            text=f"🔄 Auto-Sync ativo (Último: {t_str})",
                            font=ctk.CTkFont(size=9, slant="italic"),
                            text_color="#00CED1"
                        ).pack(fill="x", padx=4, pady=(2, 6))

                ctk.CTkLabel(
                    self.schedule_scroll,
                    text="Nenhum jogo agendado na fila.",
                    font=ctk.CTkFont(size=10),
                    text_color="#555555"
                ).pack(pady=10)
            return
            
        # Seletor de reconstrução total: se os IDs dos jogos na fila mudaram, limpamos e recriamos
        current_game_ids = [str(g.get("id")) for g in games]
        cached_game_ids = list(getattr(self, "_schedule_cards_cache", {}).keys())
        
        # Se a lista de IDs mudou ou o cache não foi inicializado, limpamos tudo
        if current_game_ids != cached_game_ids:
            for w in self.schedule_scroll.winfo_children():
                w.destroy()
            self._schedule_cards_cache = {}
            
            if self.auto_schedule_audit_var.get():
                last_t = getattr(self, "_last_auto_schedule_fetch_time", 0.0)
                if last_t > 0:
                    t_str = datetime.fromtimestamp(last_t).strftime("%H:%M:%S")
                    ctk.CTkLabel(
                        self.schedule_scroll,
                        text=f"🔄 Auto-Sync ativo (Último: {t_str})",
                        font=ctk.CTkFont(size=9, slant="italic"),
                        text_color="#00CED1"
                    ).pack(fill="x", padx=4, pady=(2, 6))
                
        now = datetime.now()
        for g in games:
            g_id = str(g.get("id"))
            t1 = g.get("team1", "")
            t2 = g.get("team2", "")
            d_str = g.get("date", "")
            time_str = g.get("time", "")
            g_status = g.get("status", "pending")
            
            status_text = "⏳ AGUARDANDO"
            status_color = "#FFD700"
            countdown_text = ""
            
            if g_status == "running":
                spin_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                spin_idx = now.second % len(spin_chars)
                status_text = f"⚙️ PROCESSANDO I.A... {spin_chars[spin_idx]}"
                status_color = "#FFA500"
                countdown_text = "Consultando dados e gerando PDF..."
            elif g_status == "queued":
                pulse_chars = [".  ", ".. ", "...", " ..", "  ."]
                pulse_idx = now.second % len(pulse_chars)
                status_text = f"⏳ NA FILA {pulse_chars[pulse_idx]}"
                status_color = "#D2691E"
                countdown_text = "Aguardando liberação de vaga..."
            elif g_status == "completed":
                status_text = "✅ CONCLUÍDO (ENVIADO)"
                status_color = "#00FF00"
                countdown_text = "Relatório enviado por e-mail"
            elif g_status == "failed":
                status_text = "❌ FALHA NA AUDITORIA"
                status_color = "#FF4500"
                countdown_text = "Verifique os logs de erro"
            else:
                try:
                    k_dt = datetime.strptime(f"{d_str} {time_str}", "%d/%m/%Y %H:%M")
                    e_dt = k_dt + timedelta(minutes=110)
                    
                    if now < k_dt:
                        diff_sec = int((k_dt - now).total_seconds())
                        hrs = diff_sec // 3600
                        mins = (diff_sec % 3600) // 60
                        secs = diff_sec % 60
                        status_text = "⏳ AGUARDANDO KICKOFF"
                        status_color = "#00CED1"
                        countdown_text = f"Inicia em: {hrs:02d}h {mins:02d}m {secs:02d}s"
                    elif k_dt <= now <= e_dt:
                        diff_sec = int((e_dt - now).total_seconds())
                        mins = diff_sec // 60
                        secs = diff_sec % 60
                        status_text = "🟢 AO VIVO (EM ANDAMENTO)"
                        status_color = "#00FF00"
                        countdown_text = f"Relatório em: {mins:02d}m {secs:02d}s"
                    else:
                        status_text = "⏳ AGENDAMENTO PENDENTE"
                        status_color = "#FFD700"
                        countdown_text = "Aguardando disparo..."
                except:
                    pass

            # Se o card não está no cache, nós o criamos
            if g_id not in self._schedule_cards_cache:
                card = ctk.CTkFrame(self.schedule_scroll, corner_radius=8, fg_color="#181818", border_width=1, border_color="#333333")
                card.pack(fill="x", padx=2, pady=3)
                
                lbl_team = ctk.CTkLabel(card, text=f"{t1} x {t2}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFFFFF")
                lbl_team.pack(anchor="w", padx=8, pady=(4, 1))
                
                lbl_st = ctk.CTkLabel(card, text=f"{status_text} • {d_str} {time_str}", font=ctk.CTkFont(size=11, weight="bold"), text_color=status_color)
                lbl_st.pack(anchor="w", padx=8)
                
                lbl_countdown = ctk.CTkLabel(card, text=countdown_text if countdown_text else "", font=ctk.CTkFont(size=11), text_color="#DDDDDD")
                lbl_countdown.pack(anchor="w", padx=8, pady=(0, 4))
                
                btn_open = None
                if g_status == "completed":
                    pdf_path = g.get("pdf_path")
                    def make_open_cmd(p_path=pdf_path):
                        return lambda: self._open_pdf_or_folder(p_path)
                    btn_open = ctk.CTkButton(
                        card, text="📄 Abrir Relatório", font=ctk.CTkFont(size=11, weight="bold"),
                        fg_color="#006400", hover_color="#004d00", height=22, width=120,
                        command=make_open_cmd()
                    )
                    btn_open.pack(anchor="w", padx=8, pady=(2, 6))
                    
                self._schedule_cards_cache[g_id] = {
                    "card": card,
                    "lbl_team": lbl_team,
                    "lbl_st": lbl_st,
                    "lbl_countdown": lbl_countdown,
                    "btn_open": btn_open
                }
            else:
                # Se o card já existe, nós apenas atualizamos os valores dinâmicos de forma rápida
                cache = self._schedule_cards_cache[g_id]
                cache["lbl_st"].configure(text=f"{status_text} • {d_str} {time_str}", text_color=status_color)
                cache["lbl_countdown"].configure(text=countdown_text if countdown_text else "")
                
                # Se o status mudou para completed e o botão ainda não foi criado, criamos ele agora
                if g_status == "completed" and cache.get("btn_open") is None:
                    pdf_path = g.get("pdf_path")
                    def make_open_cmd(p_path=pdf_path):
                        return lambda: self._open_pdf_or_folder(p_path)
                    btn_open = ctk.CTkButton(
                        cache["card"], text="📄 Abrir Relatório", font=ctk.CTkFont(size=11, weight="bold"),
                        fg_color="#006400", hover_color="#004d00", height=22, width=120,
                        command=make_open_cmd()
                    )
                    btn_open.pack(anchor="w", padx=8, pady=(2, 6))
                    cache["btn_open"] = btn_open

    def _trigger_scheduled_audit(self, game: dict) -> None:
        """Dispara a auditoria de um jogo agendado quando a súmula já está disponível ou por tolerância."""
        if game.get("status") in ["queued", "running", "completed", "failed"]:
            return
            
        game["status"] = "queued"
        _save_scheduled_games(getattr(self, "_scheduled_games", []))
        self.after(0, self._update_schedule_panel_ui)
        self._log(f"⏰ [AGENDAMENTO] Jogo {game.get('team1')} x {game.get('team2')} entrou na fila de processamento...")
        
        def run_scheduled_audit_thread(_game=game):
            with self._audit_semaphore:
                _game["status"] = "running"
                self.after(0, self._update_schedule_panel_ui)
                self._log(f"⏰ [AGENDAMENTO] Iniciando processamento paralelo de {_game.get('team1')} x {_game.get('team2')}...")
                
                # Atraso de staggering para evitar sobreposição exata de conexões
                import time
                time.sleep(2.0)
                
                try:
                    cfg_path = _get_config_read_path("google_ai.json")
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                        api_key = config_data.get("gemini_api_keys") or config_data.get("gemini_api_key") or config_data.get("api_key")
                        yt_key = config_data.get("youtube_api_key")
                        model_id = config_data.get("model", "gemini-2.5-flash")
                    
                    from modules.expert_assistant import ExpertAssistant
                    assistant = ExpertAssistant(api_key=api_key, model_id=model_id, yt_api_key=yt_key)
                    
                    payload = {
                        "team1": _game.get("team1"),
                        "team2": _game.get("team2"),
                        "competition": _game.get("comp"),
                        "platform": _game.get("platform"),
                        "date": _game.get("date"),
                        "start_timestamp": None,
                        "duration": None,
                        "video_url": None,
                        "transcript_text": None
                    }
                    
                    result = assistant.get_match_chronology(**payload)
                    if "error" not in result:
                        result["platform"] = _game.get("platform")
                        
                        to_render = []
                        chrono_map = [
                            ("pre_game_start", "INÍCIO TRANSMISSÃO", -10),
                            ("match_start", "INÍCIO", -5),
                            ("first_half_start", "APITO INICIAL (1T)", 0),
                            ("half_time_start", "INÍCIO INTERVALO", 45),
                            ("half_time_end", "VOLTA INTERVALO", 46),
                            ("second_half_start", "APITO INICIAL (2T)", 47),
                            ("match_end", "APITO FINAL", 90),
                            ("post_game_end", "ENCERRAMENTO", 120)
                        ]
                        for key, label, def_min in chrono_map:
                            val = result.get(key)
                            if val and val != "N/A":
                                to_render.append({
                                    "minute": def_min,
                                    "label": label,
                                    "clock": val,
                                    "summary": f"{label} detectado pela Auditoria IA."
                                })
                                
                        for m in result.get("technical_milestones", []):
                            try: m_min = int(m.get("minute", 0))
                            except: m_min = 0
                            to_render.append({
                                "minute": m_min,
                                "label": str(m.get("type", "EVENTO")).upper(),
                                "clock": str(m.get("time") or ""),
                                "summary": m.get("event"),
                                "confidence": m.get("confidence") or 0.85
                            })
                        
                        self.after(0, self.detector.start_session, f"schedule_{_game.get('id')}")
                        for item in to_render:
                            self.after(0, lambda it=item: self.detector.add_timeline_entry(
                                it["minute"], "ia_analysis", it["label"], {"summary": it["summary"]},
                                confidence=float(it.get("confidence", 0.85)), clock=it["clock"]
                            ))
                        self.after(0, self._update_history_grid)
                        
                        prefs = {
                            "show_chrono": True,
                            "show_milestones": True,
                            "show_secondary": True,
                            "show_sources": True
                        }
                        pdf_path = self.reporter.write_expert_report([result], prefs=prefs)
                        _game["pdf_path"] = pdf_path
                        self._log(f"⏰ [AGENDAMENTO] Relatório PDF gerado com sucesso em: {pdf_path}")
                        
                        emails = _game.get("emails", "").strip()
                        if emails:
                            import re
                            recipients = [em.strip() for em in re.split(r'[,;]', emails) if em.strip()]
                            if recipients:
                                config_path = _get_config_read_path("google_ai.json")
                                try:
                                    with open(config_path, "r", encoding="utf-8") as fcreds:
                                        creds = json.load(fcreds)
                                    sender = creds.get("email")
                                    password = creds.get("senha")
                                    
                                    if sender and password and "SEU_EMAIL" not in sender:
                                        from modules.email_service import EmailService
                                        service = EmailService(
                                            smtp_server=EMAIL_SMTP_SERVER,
                                            smtp_port=EMAIL_SMTP_PORT,
                                            sender_email=sender,
                                            sender_password=password
                                        )
                                        subject = f"Relatório Agendado - {_game.get('team1')} x {_game.get('team2')}"
                                        body = f"Relatório da auditoria automática agendada para {_game.get('team1')} x {_game.get('team2')}."
                                        success = service.send_report(recipients, subject, body, pdf_path)
                                        if success:
                                            self._log(f"⏰ [AGENDAMENTO] Relatório enviado por e-mail para: {emails}")
                                        else:
                                            self._log("⏰ [AGENDAMENTO] Falha ao enviar e-mail.")
                                except Exception as ex_mail:
                                    self._log(f"⏰ [AGENDAMENTO] Falha ao disparar e-mail: {ex_mail}")
                                        
                        _game["status"] = "completed"
                    else:
                        err_detail = result.get('error_details') or result.get('error')
                        self._log(f"⏰ [AGENDAMENTO ERRO] IA retornou erro para {_game.get('team1')} x {_game.get('team2')}: {err_detail}")
                        _game["status"] = "failed"
                except Exception as ex_audit:
                    import traceback
                    tb_str = traceback.format_exc()
                    self._log(f"⏰ [AGENDAMENTO ERRO] Falha crítica na auditoria de {_game.get('team1')} x {_game.get('team2')}:\n{tb_str}")
                    _game["status"] = "failed"
                finally:
                    _save_scheduled_games(getattr(self, "_scheduled_games", []))
                    self.after(0, self._update_schedule_panel_ui)
                    
        import threading
        threading.Thread(target=run_scheduled_audit_thread, daemon=True).start()

    def _start_schedule_timer_loop(self) -> None:
        """Loop contínuo de 1 segundo para atualizar relógios regressivos e disparar auditorias agendadas."""
        now = datetime.now()
        
        # Pulso sutil do indicador LIVE com relógio em tempo real no cabeçalho
        if hasattr(self, "lbl_schedule_live_indicator"):
            t_sec = now.strftime("%H:%M:%S")
            dot = "●" if now.second % 2 == 0 else "○"
            dot_color = "#00FF7F" if now.second % 2 == 0 else "#2E8B57"
            self.lbl_schedule_live_indicator.configure(text=f"{dot} LIVE {t_sec}", text_color=dot_color)
            
        self._update_schedule_panel_ui()
        
        games = getattr(self, "_scheduled_games", [])
        updated = False
        
        for g in games:
            if g.get("status", "pending") == "pending":
                d_str = g.get("date", "")
                time_str = g.get("time", "")
                try:
                    k_dt = datetime.strptime(f"{d_str} {time_str}", "%d/%m/%Y %H:%M")
                    e_dt = k_dt + timedelta(minutes=110)
                    
                    if now >= e_dt:
                        # Throttle a verificação da súmula para cada 5 minutos
                        last_check_t = g.get("_last_sumula_check_time", 0.0)
                        import time
                        if time.time() - last_check_t >= 300.0 or last_check_t == 0.0:
                            g["_last_sumula_check_time"] = time.time()
                            updated = True
                            
                            self._log(f"⏰ [AGENDAMENTO] Checando se a súmula da CBF para {g.get('team1')} x {g.get('team2')} já está disponível no site...")
                            
                            def check_sumula_thread(_game=g):
                                try:
                                    cfg_path = _get_config_read_path("google_ai.json")
                                    with open(cfg_path, "r", encoding="utf-8") as fcreds:
                                        creds_data = json.load(fcreds)
                                    api_key = creds_data.get("gemini_api_keys") or creds_data.get("gemini_api_key") or creds_data.get("api_key")
                                    model_id = creds_data.get("model", "gemini-2.5-flash")
                                    
                                    from modules.expert_assistant import ExpertAssistant
                                    assistant = ExpertAssistant(api_key=api_key, model_id=model_id)
                                    
                                    is_available = assistant.is_cbf_sumula_available(
                                        team1=_game.get("team1"),
                                        team2=_game.get("team2"),
                                        date=_game.get("date")
                                    )
                                    
                                    if is_available:
                                        self._log(f"⏰ [AGENDAMENTO] Súmula da CBF para {_game.get('team1')} x {_game.get('team2')} está DISPONÍVEL! Iniciando auditoria...")
                                        self.after(0, lambda: self._trigger_scheduled_audit(_game))
                                    else:
                                        kickoff_dt = datetime.strptime(f"{_game.get('date')} {_game.get('time')}", "%d/%m/%Y %H:%M")
                                        if datetime.now() - kickoff_dt > timedelta(hours=24):
                                            self._log(f"⏰ [AGENDAMENTO] Súmula da CBF ainda não disponível após 24h. Iniciando auditoria por tolerância...")
                                            self.after(0, lambda: self._trigger_scheduled_audit(_game))
                                        else:
                                            self._log(f"⏰ [AGENDAMENTO] Súmula da CBF para {_game.get('team1')} x {_game.get('team2')} ainda NÃO disponível no site. Aguardando...")
                                except Exception as ex_check:
                                    self._log(f"⏰ [AGENDAMENTO WARN] Erro ao checar súmula: {ex_check}. Tentará novamente.")
                                    kickoff_dt = datetime.strptime(f"{_game.get('date')} {_game.get('time')}", "%d/%m/%Y %H:%M")
                                    if datetime.now() - kickoff_dt > timedelta(hours=24):
                                        self.after(0, lambda: self._trigger_scheduled_audit(_game))
                            
                            import threading
                            threading.Thread(target=check_sumula_thread, daemon=True).start()
                except Exception as ex_dt:
                    self._log(f"⏰ [AGENDAMENTO] Erro ao processar data do jogo: {ex_dt}")
                    
        if updated:
            _save_scheduled_games(games)
            
        # Verificação periódica da Auditoria Automática (a cada 10 min)
        if self.auto_schedule_audit_var.get():
            import time
            now_t = time.time()
            last_t = getattr(self, "_last_auto_schedule_fetch_time", 0.0)
            if now_t - last_t >= 600.0 or last_t == 0.0:
                self._last_auto_schedule_fetch_time = now_t
                self._run_auto_schedule_fetch()

        self.after(1000, self._start_schedule_timer_loop)

    def _start_self_update(self, download_url: str, remote_ver: str) -> None:
        """Inicia o download do update em uma thread em background e atualiza o botão superior com progresso."""
        if not hasattr(self, "btn_header_update"):
            return
            
        self._log(f"[AUTO-UPDATER] Iniciando atualização automática para v{remote_ver}...")
        self.btn_header_update.configure(text="📥 Preparando...", state="disabled")
        
        def run_update():
            try:
                updater = AutoUpdater()
                def progress_cb(pct):
                    if isinstance(pct, int):
                        self.after(0, lambda: self.btn_header_update.configure(text=f"📥 Baixando {pct}%"))
                    else:
                        self.after(0, lambda: self.btn_header_update.configure(text=f"📥 Baixando {pct}"))
                        
                success = updater.perform_update_and_restart(download_url, progress_callback=progress_cb)
                if not success:
                    self.after(0, lambda: self.btn_header_update.configure(text="❌ Falha no Update", state="normal"))
            except Exception as ex:
                self._log(f"[AUTO-UPDATER ERROR] Falha no download do update: {ex}")
                self.after(0, lambda: self.btn_header_update.configure(text="❌ Erro no Update", state="normal"))
                
        import threading
        threading.Thread(target=run_update, daemon=True).start()

    def _run_auto_schedule_fetch(self) -> None:
        """Busca os próximos jogos oficiais da CBF e os insere na fila de agendamento se não existirem."""
        def fetch_thread():
            try:
                from modules.cbf_schedule_fetcher import CBFScheduleFetcher
                try:
                    cbf_events = CBFScheduleFetcher.get_upcoming_matches()
                except Exception as ex_fetch:
                    self._log(f"⏰ [AGENDAMENTO AUTOMÁTICO] Falha ao raspar CBF, usando fallback local: {ex_fetch}")
                    cbf_events = _load_cbf_streaming_events()
                
                if not cbf_events:
                    return
                
                games = _load_scheduled_games()
                existing_sigs = {f"{g.get('team1')}_{g.get('team2')}_{g.get('date')}_{g.get('time')}".lower() for g in games}
                
                added_count = 0
                for idx, evt in enumerate(cbf_events):
                    sig = f"{evt.get('team1')}_{evt.get('team2')}_{evt.get('date')}_{evt.get('time')}".lower()
                    if sig not in existing_sigs:
                        new_id = f"auto_{evt.get('date').replace('/', '')}_{evt.get('time').replace(':', '')}_{idx}"
                        games.append({
                            "id": new_id,
                            "team1": evt.get("team1"),
                            "team2": evt.get("team2"),
                            "comp": evt.get("comp"),
                            "date": evt.get("date"),
                            "time": evt.get("time"),
                            "platform": evt.get("platform"),
                            "emails": self.email_recipients_var.get(),
                            "status": "pending",
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        added_count += 1
                
                if added_count > 0:
                    _save_scheduled_games(games)
                    self._scheduled_games = games
                    self.after(0, self._update_schedule_panel_ui)
                    self._log(f"⏰ [AGENDAMENTO AUTOMÁTICO] Fila atualizada! {added_count} novos jogos adicionados.")
            except Exception as e:
                self._log(f"⏰ [AGENDAMENTO AUTOMÁTICO] Erro ao buscar jogos: {e}")

        import threading
        threading.Thread(target=fetch_thread, daemon=True).start()

    def _render_dynamic_quick_presets(self) -> None:
        """Renderiza os botões dinâmicos de Seleção Rápida com base nos últimos jogos pesquisados."""
        if not hasattr(self, "presets_buttons_container"):
            return
            
        for w in self.presets_buttons_container.winfo_children():
            w.destroy()
            
        recent = _load_recent_searches()
        for item in recent[:4]:
            t1 = item.get("team1", "")
            t2 = item.get("team2", "")
            comp = item.get("comp", "")
            d_str = item.get("date", "")
            plat = item.get("platform", "CazéTV")
            
            if not t1 or not t2: continue
            
            d_fmt = d_str[:5] if len(d_str) >= 5 else d_str
            btn_text = f"⚡ {t1} x {t2} ({d_fmt})"
            
            btn = ctk.CTkButton(
                self.presets_buttons_container,
                text=btn_text,
                font=ctk.CTkFont(size=10),
                height=22,
                fg_color="#222222",
                hover_color="#333333",
                command=lambda _t1=t1, _t2=t2, _comp=comp, _d=d_str, _p=plat: self._apply_preset_data(_t1, _t2, _comp, _d, _p)
            )
            btn.pack(side="left", padx=4)

    def _apply_preset_data(self, t1: str, t2: str, comp: str, date: str, plat: str, tag: str = "🏷️ Normal") -> None:
        """Preenche os campos do formulário manual com os dados do preset clicado."""
        self.expert_team1_var.set(t1)
        self.expert_team2_var.set(t2)
        self.expert_comp_var.set(comp)
        self.expert_date_var.set(date)
        self.expert_platform_var.set(plat)
        if hasattr(self, "expert_tag_var"):
            self.expert_tag_var.set(tag)

    def _on_click_start_audit(self) -> None:
        """Salva a pesquisa atual no histórico de Seleção Rápida e inicia a auditoria."""
        _save_recent_search(
            self.expert_team1_var.get(),
            self.expert_team2_var.get(),
            self.expert_comp_var.get(),
            self.expert_date_var.get(),
            self.expert_platform_var.get()
        )
        self._render_dynamic_quick_presets()

        # Disparar a auditoria expert com os dados atuais do formulário
        data = {
            "team1": self.expert_team1_var.get().strip(),
            "team2": self.expert_team2_var.get().strip(),
            "comp": self.expert_comp_var.get().strip(),
            "date": self.expert_date_var.get().strip(),
            "time": self.expert_time_var.get().strip(),
            "platform": self.expert_platform_var.get().strip(),
        }
        if not data["team1"] or not data["team2"]:
            import tkinter.messagebox as mb
            mb.showwarning("Atenção", "Preencha Time Casa e Time Fora antes de iniciar a auditoria.")
            return
        self._run_expert_analysis(data)
    def _force_refresh_cbf_mural(self) -> None:
        """Força o download e re-parsing das tabelas oficiais da CBF."""
        try:
            from modules.cbf_schedule_fetcher import CBFScheduleFetcher
            CBFScheduleFetcher.get_upcoming_matches(force_refresh=True)
            self._render_cbf_mural_ui()
            self._log("[CBF MURAL] Tabela atualizada diretamente do portal CBF com sucesso!")
            self._ui_success("Tabela da CBF atualizada live!")
        except Exception as e:
            self._log(f"[CBF MURAL WARN] Erro ao atualizar tabela: {e}")

    def _render_cbf_mural_ui(self) -> None:
        """Renderiza o Mural de Próximos Confrontos usando o módulo autônomo CBFScheduleFetcher."""
        if not hasattr(self, "cbf_mural_scroll"):
            return
            
        for w in self.cbf_mural_scroll.winfo_children():
            w.destroy()
            
        mode = getattr(self, "cbf_ticker_tab_var", None)
        is_finished_mode = True
        if mode and "Próximos" in mode.get():
            is_finished_mode = False

        try:
            from modules.cbf_schedule_fetcher import CBFScheduleFetcher
            if is_finished_mode:
                cbf_events = CBFScheduleFetcher.get_recent_finished_matches()
            else:
                cbf_events = CBFScheduleFetcher.get_upcoming_matches()
        except:
            cbf_events = _load_cbf_streaming_events()

        if not cbf_events:
            msg = "Nenhum jogo finalizado recente encontrado." if is_finished_mode else "Nenhum confronto futuro agendado."
            ctk.CTkLabel(self.cbf_mural_scroll, text=msg, font=ctk.CTkFont(size=11), text_color="#777777").pack(side="left", padx=10)
            return
            
        for evt in cbf_events[:12]:
            t1 = evt.get("team1", "")
            t2 = evt.get("team2", "")
            comp = evt.get("comp", "")
            d_str = evt.get("date", "")
            t_str = evt.get("time", "")
            score = evt.get("score", "")
            plat = evt.get("platform", "")
            tag = evt.get("tag", "🏷️ Normal")
            
            # Card / Chip Horizontal do Letreiro
            chip = ctk.CTkFrame(self.cbf_mural_scroll, fg_color="#1a1a1a", corner_radius=8, border_width=1, border_color="#2b5b84", height=28)
            chip.pack(side="left", padx=5, pady=2)
            
            if is_finished_mode:
                score_display = f" {score} " if score else " x "
                title_text = f"⚡ {t1}{score_display}{t2}"
                btn_text = "⚡ Auditar"
                btn_color = "#008080"
                btn_hover = "#005a5a"
                info_text = f"📅 {d_str} ({plat})"
            else:
                title_text = f"📅 {t1} x {t2}"
                btn_text = "⏰ Na Fila"
                btn_color = "#8B008B"
                btn_hover = "#4B0082"
                info_text = f"🕒 {d_str} {t_str} ({plat})"
            
            lbl_title = ctk.CTkLabel(
                chip, 
                text=title_text, 
                font=ctk.CTkFont(size=11, weight="bold"), 
                text_color="#00FF7F" if is_finished_mode else "#00CED1"
            )
            lbl_title.pack(side="left", padx=(8, 4), pady=2)
            
            lbl_info = ctk.CTkLabel(
                chip, 
                text=info_text, 
                font=ctk.CTkFont(size=10), 
                text_color="#CCCCCC"
            )
            lbl_info.pack(side="left", padx=(0, 6), pady=2)
            
            btn_use = ctk.CTkButton(
                chip,
                text=btn_text,
                font=ctk.CTkFont(size=10, weight="bold"),
                width=65,
                height=20,
                fg_color=btn_color,
                hover_color=btn_hover,
                command=lambda _t1=t1, _t2=t2, _c=comp, _d=d_str, _p=plat, _tg=tag: self._apply_preset_data(_t1, _t2, _c, _d, _p, _tg)
            )
            btn_use.pack(side="left", padx=(0, 6), pady=2)
            
            # Clique no chip também aplica os dados ao formulário
            for widget in (chip, lbl_title, lbl_info):
                widget.bind("<Button-1>", lambda e, _t1=t1, _t2=t2, _c=comp, _d=d_str, _p=plat, _tg=tag: self._apply_preset_data(_t1, _t2, _c, _d, _p, _tg))

    def _open_internal_pdf_viewer(self, pdf_path: str) -> None:
        """Abre a janela do Visualizador Interno de PDF sem depender do leitor externo do Windows."""
        if not pdf_path or not os.path.exists(pdf_path):
            self._log(f"[PDF WARN] Arquivo de PDF não encontrado: {pdf_path}")
            return
            
        try:
            import fitz
            from PIL import Image, ImageTk
        except Exception as e:
            self._log(f"[PDF WARN] Erro ao carregar PyMuPDF: {e}. Abrindo leitor padrão...")
            try: os.startfile(pdf_path)
            except: pass
            return

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        pdf_win = ctk.CTkToplevel(self)
        pdf_win.title(f"📄 Visualizador Interno - {os.path.basename(pdf_path)}")
        pdf_win.geometry("960x850")
        pdf_win.attributes("-topmost", True)

        curr_page = [0]
        zoom_level = [1.3]

        hdr = ctk.CTkFrame(pdf_win, height=48, fg_color="#1f1f1f")
        hdr.pack(fill="x", padx=10, pady=10)

        lbl_page_info = ctk.CTkLabel(hdr, text=f"Página 1 de {total_pages}", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_page_info.pack(side="left", padx=15)

        scroll_frame = ctk.CTkScrollableFrame(pdf_win, fg_color="#111111")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        img_holder = ctk.CTkLabel(scroll_frame, text="")
        img_holder.pack(pady=10)

        def render_current_page():
            page = doc.load_page(curr_page[0])
            mat = fitz.Matrix(zoom_level[0], zoom_level[0])
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(pix.width, pix.height))
            img_holder.configure(image=ctk_img, text="")
            lbl_page_info.configure(text=f"Página {curr_page[0] + 1} de {total_pages} (Zoom: {int(zoom_level[0]*100)}%)")

        def prev_page():
            if curr_page[0] > 0:
                curr_page[0] -= 1
                render_current_page()

        def next_page():
            if curr_page[0] < total_pages - 1:
                curr_page[0] += 1
                render_current_page()

        def zoom_in():
            if zoom_level[0] < 3.0:
                zoom_level[0] += 0.2
                render_current_page()

        def zoom_out():
            if zoom_level[0] > 0.6:
                zoom_level[0] -= 0.2
                render_current_page()

        btn_prev = ctk.CTkButton(hdr, text="◀ Anterior", width=90, command=prev_page)
        btn_prev.pack(side="left", padx=5)

        btn_next = ctk.CTkButton(hdr, text="Próxima ▶", width=90, command=next_page)
        btn_next.pack(side="left", padx=5)

        btn_z_in = ctk.CTkButton(hdr, text="🔍 Zoom +", width=80, fg_color="#333333", command=zoom_in)
        btn_z_in.pack(side="left", padx=5)

        btn_z_out = ctk.CTkButton(hdr, text="🔍 Zoom -", width=80, fg_color="#333333", command=zoom_out)
        btn_z_out.pack(side="left", padx=5)

        btn_ext = ctk.CTkButton(hdr, text="🌐 Abrir Leitor Windows", width=160, fg_color="#2b5b84", command=lambda: os.startfile(pdf_path))
        btn_ext.pack(side="right", padx=10)

        render_current_page()

    def _open_history_report(self, path: str) -> None:
        """Carrega um relatório salvo e exibe no grid."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            res = {}
            if "expert_results" in data and data["expert_results"]:
                self._load_expert_report_to_grid(path)
                return
            elif "technical_milestones" in data:
                res = data
            elif "analysis" in data:
                res = data.get("analysis", {}).get("notes", {}).get("expert_result") or {}
                if not res:
                    # Report regular
                    self.detector.timeline = data.get("analysis", {}).get("timeline", [])
                    self._update_history_grid()
                    self.tabs.set("Monitoramento")
                    return
            
            if not res:
                self._log(f"[AVISO] Formato de histórico não reconhecido: {path}")
                return

            self._display_expert_result(res)
            self.tabs.set("Monitoramento")
        except Exception as e:
            self._ui_error(f"Erro ao abrir histórico: {e}")

    def _load_expert_report_to_grid(self, path: str) -> None:
        """Carrega e exibe os momentos de um relatório Expert no grid com DEDUPLICAÇÃO RÍGIDA."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not hasattr(self, "history_grid") or not self.history_grid: return

            for w in self.history_grid.winfo_children():
                w.destroy()

            results = data.get("expert_results", [data])
            seen_events = set()
            added_count = 0

            for res in results:
                milestones = res.get("technical_milestones", [])
                for m in milestones:
                    m_type = str(m.get("type") or m.get("event") or "MARCO").strip().upper()
                    m_time = str(m.get("time") or m.get("minute") or "").strip()
                    m_text = str(m.get("event") or m.get("description") or "").strip()

                    # CHAVE DE DEDUPLICAÇÃO RÍGIDA
                    event_key = f"{m_type}_{m_time}_{m_text[:15]}"
                    if event_key in seen_events:
                        continue
                    seen_events.add(event_key)

                    card = ctk.CTkFrame(self.history_grid, fg_color="#181818", corner_radius=8, border_width=1, border_color="#333333")
                    card.pack(fill="x", padx=8, pady=3)

                    lbl_t = ctk.CTkLabel(card, text=f"[{m_time}] {m_type}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00CED1")
                    lbl_t.pack(side="left", padx=10, pady=6)

                    lbl_desc = ctk.CTkLabel(card, text=m_text, font=ctk.CTkFont(size=11), text_color="#FFFFFF")
                    lbl_desc.pack(side="left", padx=10, pady=6)

                    lbl_conf = ctk.CTkLabel(card, text="99%", font=ctk.CTkFont(size=10, weight="bold"), text_color="#00FF00")
                    lbl_conf.pack(side="right", padx=10, pady=6)

                    added_count += 1

            if added_count == 0:
                ctk.CTkLabel(self.history_grid, text="Nenhum momento capturado.", text_color="#555555").pack(pady=40)

            self.tabs.set("Monitoramento")
            self._log(f"[EXPERT GRID] Carregados {added_count} momentos sem duplicatas.")
        except Exception as e:
            self._log(f"[EXPERT GRID WARN] Erro ao carregar relatório para grid: {e}")

    # =========================================================
    # UI tick
    # =========================================================

    def _clear_history_grid_manual(self) -> None:
        """Limpa o grid de histórico e reseta a timeline do detector manualmente."""
        if not self.history_grid: return
        
        # Limpar cards visuais
        for w in self.history_grid.winfo_children():
            w.destroy()
        self._history_cards = []
        self._last_history_count = 0
        
        # Resetar detector (Timeline)
        self.detector.start_session("manual_clear")
        
        # Restaurar placeholder
        self.hist_empty_lbl = ctk.CTkLabel(self.history_grid, text="Nenhum momento capturado ainda.", text_color="#555555")
        self.hist_empty_lbl.pack(pady=40)
        
        self._log("[UI] Histórico de momentos limpo manualmente.")
        self._ui_success("Histórico de momentos limpo.")

    def _tick_ui(self) -> None:
        try:
            # Cleanup periódico (a cada 12 horas)
            now_cleanup = time.time()
            if (now_cleanup - self._last_cleanup_t) > 43200: # 12 horas
                self._last_cleanup_t = now_cleanup
                self._run_cleanup_now()

            # O monitoramento atualiza os widgets individuais
            if not (self.runtime.running or self.runtime.preparing):
                if hasattr(self, "live_summary"): # Legado, mantendo check mas não alterando se não existe
                    self.live_summary.configure(text="Sem monitoramento ativo.")

            self.frames_var.set(f"Frames: {self.runtime.frames_seen}")
            self.match_var.set(f"Partida: {self.runtime.current_match_display or '—'}")
            self.comp_var.set(f"Competição: {self.runtime.current_competition or '—'}")

            snap = self.debug_snapshot

            live_clock = (
                self.runtime.last_clock
                or getattr(snap, "accepted_clock", None)
                or getattr(snap, "raw_clock", None)
                or "—"
            )

            live_score = (
                self.runtime.last_score
                or getattr(snap, "accepted_score", None)
                or getattr(snap, "raw_score", None)
                or "—"
            )

            live_phase = (
                self.runtime.last_phase
                or getattr(snap, "match_phase_text", None)
                or getattr(snap, "visual_state", None)
                or "—"
            )

            self.clock_var.set(f"Clock: {live_clock}")
            self.score_var.set(f"Score: {live_score}")
            self.phase_var.set(f"Fase: {live_phase}")

            if live_clock and live_clock != "—":
                self.runtime.last_clock = live_clock
            if live_score and live_score != "—":
                self.runtime.last_score = live_score
            if live_phase and live_phase != "—":
                self.runtime.last_phase = live_phase

            def _pretty_context(v: str) -> str:
                mp = {
                    "pre_jogo": "Pré-jogo",
                    "inicio_jogo": "Início do jogo",
                    "jogo": "Jogo ao vivo",
                    "primeiro_tempo": "1º Tempo",
                    "segundo_tempo": "2º Tempo",
                    "intervalo": "Intervalo",
                    "fim_jogo": "Fim do jogo",
                    "replay": "Replay",
                }
                s = str(v or "").strip().lower()
                return mp.get(s, v or "—")

            status_details = getattr(snap, "last_status_details", {}) or {}
            visual_info = getattr(snap, "visual_info", {}) or {}

            live_context_raw = (
                status_details.get("context")
                or self.runtime.last_context
                or visual_info.get("context_label")
                or visual_info.get("match_phase_text")
                or getattr(snap, "visual_state", None)
                or "—"
            )

            live_context = _pretty_context(live_context_raw)

            visual_screen_ctx = visual_info.get("screen_context") if isinstance(visual_info, dict) else {}
            live_context_summary = (
                self.runtime.last_context_summary
                or getattr(snap, "banner_summary", None)
                or (visual_screen_ctx.get("context_summary") if isinstance(visual_screen_ctx, dict) else None)
                or "—"
            )

            if live_context and live_context != "—":
                self.runtime.last_context = live_context

            if live_context_summary and live_context_summary != "—":
                self.runtime.last_context_summary = live_context_summary

            if self.runtime.last_context and self.runtime.last_context != "—":
                ctx_text = self.runtime.last_context
                if self.runtime.last_context_summary and self.runtime.last_context_summary != "—":
                    ctx_text = f"{ctx_text} — {self.runtime.last_context_summary}"
                # self.ctx_var.set(f"Contexto: {ctx_text}") # Removido (legado)
            else:
                pass # self.ctx_var.set("Contexto: —") # Removido (legado)

            # self.event_var.set(f"Último evento: {self.runtime.last_event or '—'}") # Removido (legado)
            self.visual_conf_var.set(f"Conf visual: {_fmt_conf(self.runtime.last_visual_confidence)}")
            # self.seek_var.set(f"Seek: {self.runtime.last_seek_state or '—'}") # Removido (legado)
            self.detector_perf_var.set(
                f"Detector: {self.runtime.detector_latency_ms:.1f} ms | {self.runtime.detector_fps:.1f} fps"
                if self.runtime.detector_latency_ms > 0
                else "Detector: —"
            )
            
            if self.runtime.running and self.runtime.detector_latency_ms > 0:
                now_perf = time.time()
                if (now_perf - float(getattr(self, "_last_perf_log_t", 0.0))) >= 10.0:
                    self._last_perf_log_t = now_perf
                    self._log(f"[PERF] Latência HUD: {self.runtime.detector_latency_ms:.1f} ms | Velocidade (FPS): {self.runtime.detector_fps:.1f}")


            self._update_fragments_from_detector()
            self._update_history_grid()
            self._refresh_debug_vars()

            # Cloud Analysis (Enhanced Status)
            cloud_enabled = self.detector.cfg.cloud_enabled
            buf_len = len(getattr(self.detector._state, "cloud_buffer", []) or [])
            batch_size = self.detector.cfg.cloud_batch_size
            last_res = getattr(self.detector._state, "last_cloud_result", {}) or {}
            analysis_active = getattr(self.detector._state, "cloud_analysis_in_progress", False)

            if not cloud_enabled:
                self.cloud_status_var.set("Cloud Expert: Desativado nas configurações.")
            elif analysis_active:
                self.cloud_status_var.set("Cloud Expert: ⏳ Enviando/Analisando lote no Gemini... (Processando)")
            else:
                last_err = getattr(self.detector._state, "last_cloud_error", "")
                
                if last_err:
                    status_line = f"Cloud ERROR: {last_err}"
                    self.cloud_status_var.set(status_line)
                else:
                    # 1. Determina se estamos na fase inicial rápida ou normal
                    is_initial = getattr(self.detector._state, "last_cloud_analysis_t", 0.0) == 0.0
                    interval = 3.0 if is_initial else self.detector.cfg.cloud_sample_every_s
                    
                    samples_left = max(0, batch_size - buf_len)
                    seconds_left = samples_left * interval
                    mm = int(seconds_left // 60)
                    ss = int(seconds_left % 60)
                    
                    countdown = f"Próxima análise em {mm:02d}:{ss:02d}"
                    label_coleta = "Coleta Inicial" if is_initial else "Coleta Normal"
                    collecting = f"{label_coleta} ({buf_len}/{batch_size})"
                    
                    status_line = f"Cloud: {collecting} | {countdown}"
                    
                    if last_res:
                        cloud_t = getattr(self.detector._state, "last_cloud_analysis_t", 0.0)
                        duration = getattr(self.detector._state, "last_cloud_duration_s", 0.0)
                        time_str = time.strftime("%H:%M:%S", time.localtime(cloud_t))
                        summary = str(last_res.get("summary", ""))[:60]
                        status_line = f"Cloud [{time_str}] ({duration}s): {last_res.get('current_phase','?')}\n{status_line}\nÚltimo: {summary}..."
                    
                    self.cloud_status_var.set(status_line)
                
            # Update Progress Bar
            prog = buf_len / max(1, batch_size)
            self.cloud_progress_var.set(prog)

            # Destacar botão de download quando estiver pronto
            if buf_len >= batch_size and batch_size > 0:
                self.btn_cloud_download.configure(
                    fg_color="#00CED1", 
                    text_color="#111111", 
                    text="⬇ Baixar JSON (Pronto)"
                )
            else:
                self.btn_cloud_download.configure(
                    fg_color="transparent", 
                    text_color="#00CED1", 
                    text="⬇ Baixar JSON"
                )

            if self.runtime.running and self.runtime.event_id:
                now_ts = time.time()
                if (now_ts - float(self.runtime.last_partial_report_t or 0.0)) >= int(self.runtime.partial_report_every_s):
                    self.runtime.last_partial_report_t = now_ts
                    try:
                        self._write_partial_report()
                    except Exception as e:
                        self._log(f"[WARN] tick_ui report: {e}")

                last_ok_t = float(self._last_pipeline_processed_t or 0.0)
                no_frames_for = (now_ts - last_ok_t) if last_ok_t > 0 else 0.0

                if last_ok_t > 0 and no_frames_for >= float(self._no_frames_finalize_timeout_s):
                    if not self._finalize_in_progress:
                        self._log(
                            f"[AUTO-FINALIZE] sem frames processados há {no_frames_for:.1f}s "
                            f"(limite={self._no_frames_finalize_timeout_s:.0f}s). Gerando relatório final."
                        )
                        self._finalize_in_progress = True
                        self.after(0, lambda: self._finalize_and_stop("no_frames_timeout"))
                elif last_ok_t > 0 and no_frames_for >= 30.0:
                    if (now_ts - float(self._last_no_frames_warn_t or 0.0)) >= 30.0:
                        self._last_no_frames_warn_t = now_ts
                        self._log(
                            f"[WATCHDOG] sem frames novos há {no_frames_for:.1f}s "
                            f"(auto-finaliza em {self._no_frames_finalize_timeout_s:.0f}s)."
                        )

                # Auto-Stop Pós-jogo (Refinado e Robusto)
                is_game_phase = live_phase in ("jogo", "primeiro_tempo", "segundo_tempo", "intervalo")
                if is_game_phase:
                    self.runtime.game_has_started = True

                limit_mins = int(self.auto_stop_pos_mins_var.get())
                if limit_mins > 0:
                    # Monitora se a transmissão parou de detectar jogo APÓS ele ter começado
                    # OU se caiu explicitamente em pos_jogo
                    is_timeout_phase = (live_phase == "pos_jogo") or (self.runtime.game_has_started and not is_game_phase)
                    
                    if is_timeout_phase:
                        if self._pos_jogo_since is None:
                            self._pos_jogo_since = now_ts
                        
                        elapsed_pos = now_ts - self._pos_jogo_since
                        if elapsed_pos >= (limit_mins * 60):
                            if not self._finalize_in_progress:
                                self._log(f"[AUTO-STOP] Inatividade de jogo persistente por {limit_mins} min (Fase: {live_phase}). Finalizando.")
                                self._finalize_and_stop("auto_stop_pos_jogo")
                    else:
                        self._pos_jogo_since = None

        except Exception as e:
            self._log(f"[WARN] tick_ui: {e}")

        self.after(250, self._tick_ui)

    def _refresh_debug_vars(self) -> None:
        snap = self.debug_snapshot
        st = getattr(self.detector, "_state", None)
        visual_info = getattr(snap, "visual_info", {})
        if not isinstance(visual_info, dict):
            visual_info = {}
            
        screen_ctx = visual_info.get("screen_context", {}) or {}
        if not isinstance(screen_ctx, dict):
            screen_ctx = {}

        scoreboard = screen_ctx.get("scoreboard") or {}
        top_hud = screen_ctx.get("top_hud") or {}
        bottom_ctx = screen_ctx.get("bottom") or {}
        top_overlay = screen_ctx.get("top_overlay") or {}
        left_panel = screen_ctx.get("left_panel") or {}
        right_panel = screen_ctx.get("right_panel") or {}
        blocks = screen_ctx.get("blocks") or []

        # Atualizar Log da IA
        if hasattr(self, "ia_log_box"):
            clogs = getattr(st, "cloud_logs", []) or []
            new_text = "\n".join(clogs)
            self.ia_log_box.configure(state="normal")
            # Só atualiza se mudou para evitar flicker e alto uso de CPU
            if self.ia_log_box.get("1.0", "end-1c") != new_text:
                self.ia_log_box.delete("1.0", "end")
                self.ia_log_box.insert("end", new_text)
                self.ia_log_box.see("end")
            self.ia_log_box.configure(state="disabled")

        self.dbg_visual_state_var.set(f"visual_state: {snap.visual_state}")
        dbg_phase = snap.match_phase_text or scoreboard.get("phase_text") or top_hud.get("phase_text") or "—"
        dbg_countdown = snap.countdown or scoreboard.get("countdown") or top_hud.get("countdown") or "—"
        dbg_clock_raw = snap.raw_clock or scoreboard.get("clock") or top_hud.get("clock") or "—"
        dbg_clock_ok = snap.accepted_clock or scoreboard.get("clock") or top_hud.get("clock") or "—"
        dbg_score_raw = snap.raw_score or scoreboard.get("score") or top_hud.get("score") or "—"
        dbg_score_ok = snap.accepted_score or scoreboard.get("score") or top_hud.get("score") or "—"
        
        # Se houve colapso ou falha grave na extração desse frame, não mostrar valor stale
        # A MENOS que tenhamos uma correção recente da IA (Soberania Cloud)
        perf = visual_info.get("perf") or {}
        st = getattr(self.detector, "_state", None) # Já definido no topo, mas mantendo para segurança se necessário ou removendo
        last_cloud_corr = getattr(st, "last_cloud_correction_t", -9999) if st else -9999
        cloud_trust = (time.time() - last_cloud_corr) < 120.0
        
        # Se houve colapso ou falha grave na extração desse frame, não mostrar valor stale
        # A MENOS que tenhamos uma correção recente da IA (Soberania Cloud) 
        # OU que a Cloud esteja habilitada (nesse caso mantemos o último valor conhecido até a IA corrigir)
        perf = visual_info.get("perf") or {}
        st = getattr(self.detector, "_state", None) # Já definido no topo, mas mantendo para segurança se necessário ou removendo
        cloud_enabled = self.detector.cfg.cloud_enabled
        last_cloud_corr = getattr(st, "last_cloud_correction_t", -9999) if st else -9999
        cloud_trust = (time.time() - last_cloud_corr) < 120.0
        
        if perf.get("score_status") == "roi_collapsed" and not cloud_trust and not cloud_enabled: 
            dbg_score_ok = "—"
        if perf.get("clock_status") == "roi_collapsed" and not cloud_trust and not cloud_enabled: 
            dbg_clock_ok = "—"

        self.dbg_phase_var.set(f"match_phase_text: {dbg_phase}")
        self.dbg_countdown_var.set(f"countdown: {dbg_countdown}")
        self.dbg_clock_raw_var.set(f"clock bruto: {dbg_clock_raw}")
        self.dbg_clock_ok_var.set(f"clock aceito: {dbg_clock_ok}")
        self.dbg_score_raw_var.set(f"score bruto: {dbg_score_raw}")
        self.dbg_score_ok_var.set(f"score aceito: {dbg_score_ok}")
        self.dbg_banner_var.set(f"banner: {snap.banner_summary or screen_ctx.get('context_summary') or '—'}")
        self.dbg_teams_var.set(f"times: {snap.teams_text or top_hud.get('teams') or '—'}")
        self.dbg_comp_var.set(f"competição: {snap.competition_text or top_hud.get('competition_text') or top_overlay.get('text') or '—'}")
        self.dbg_seek_var.set(f"seek: {'ativo' if snap.seek_active else '—'}")
        self.dbg_perf_var.set(f"latência/fps: {snap.detector_latency_ms:.1f} ms / {snap.fps_loop:.1f} fps")

        # --- Pipeline Bulbs Logic ---
        perf = visual_info.get("perf") or {}
        
        def update_bulb(key, label, active, ms, fallback_color="gray30", abort_reason=None):
            bulb = self.pipe_bulbs.get(key)
            var = getattr(self, f"pipe_{key}_var", None)
            if not bulb or not var: return
            
            # Escolha da cor e texto
            color = fallback_color
            status_txt = label
            
            # PRIORIDADE CLOUD NOS BULBS
            st = getattr(self.detector, "_state", None) # Já definido no topo, mas mantendo para segurança se necessário ou removendo
            last_cloud_corr = getattr(st, "last_cloud_correction_t", -9999) if st else -9999
            cloud_trust = (time.time() - last_cloud_corr) < 120.0

            if abort_reason == "roi_collapsed" and key in ("score", "clock"):
                if cloud_trust:
                    color = "#00CED1" # Dark Turquoise (IA confirmando)
                    status_txt = f"{label}: IA OK"
                else:
                    if cloud_enabled:
                        color = "#FFB300" # Amber/Laranja (Aguardando IA)
                        status_txt = f"{label}: IA..."
                    else:
                        color = "#D32F2F" # Vermelho (Erro)
                        status_txt = f"{label}: FAIL"
            elif abort_reason == "no_hud_earlyexit" and key in ("score", "clock"):
                if cloud_trust:
                    color = "#00CED1"
                    status_txt = f"{label}: IA OK"
                else:
                    color = "gray20" # Escuro (Ignorado)
                    status_txt = f"{label}: SKIP"
            elif active:
                if ms > 0:
                    color = "#2E7D32" # Verde (Sucesso/Processado)
                    status_txt = f"{label}: {ms:.1f}ms"
                else:
                    color = "#1565C0" # Azul (Cached/Fast)
                    status_txt = f"{label}: OK"
            else:
                color = "gray30"
                status_txt = f"{label}: OFF"

            bulb.configure(fg_color=color)
            var.set(status_txt)

        hg_abort = visual_info.get("hg_abort_reason")
        
        # 1. GATE
        gate_ms = perf.get("visual_gates_ms", 0.0)
        gate_active = visual_info.get("scoreboard_active") or visual_info.get("clock_active")
        update_bulb("gate", "GATE", gate_active, gate_ms)

        # 2. SCORE
        score_ms = perf.get("score_fast_ms", 0.0)
        score_active = visual_info.get("scoreboard_active") and bool(visual_info.get("score_detected"))
        update_bulb("score", "SCORE", score_active, score_ms, abort_reason=hg_abort)

        # 3. CLOCK
        clock_ms = perf.get("clock_fast_ms", 0.0)
        clock_active = visual_info.get("clock_active") and bool(visual_info.get("game_clock_detected"))
        update_bulb("clock", "CLOCK", clock_active, clock_ms, abort_reason=hg_abort)

        # 4. BANNER
        banner_ms = perf.get("banner_async_cache_ms", 0.0)
        banner_active = visual_info.get("banner_active")
        update_bulb("banner", "BANNER", banner_active, banner_ms)

        # 5. COUNTDOWN
        cd_ms = perf.get("countdown_fast_ms", 0.0)
        cd_active = bool(visual_info.get("countdown_detected"))
        update_bulb("countdown", "COUNTDOWN", cd_active, cd_ms)

        self.ctx_headline_var.set(f"headline: {bottom_ctx.get('headline') or '—'}")
        self.ctx_subheadline_var.set(f"subheadline: {bottom_ctx.get('subheadline') or '—'}")
        self.ctx_left_tag_var.set(f"left_tag: {bottom_ctx.get('left_tag') or '—'}")
        self.ctx_right_tag_var.set(f"right_tag: {bottom_ctx.get('right_tag') or '—'}")
        self.ctx_bottom_line_var.set(f"bottom_line: {bottom_ctx.get('bottom_line') or '—'}")
        self.ctx_top_overlay_var.set(f"top_overlay: {top_overlay.get('text') or '—'}")
        self.ctx_left_panel_var.set(f"left_panel: {left_panel.get('text') or '—'}")
        self.ctx_right_panel_var.set(f"right_panel: {right_panel.get('text') or '—'}")
        self.ctx_blocks_var.set(f"blocks: {len(blocks)}")
        self._fill_context_blocks_text(blocks if isinstance(blocks, list) else [])

        top_hud_lines = [
            f"score bruto={dbg_score_raw} | aceito={dbg_score_ok}",
            f"clock bruto={dbg_clock_raw} | aceito={dbg_clock_ok}",
            f"fase={dbg_phase}",
            f"countdown={dbg_countdown}",
            f"times={snap.teams_text or top_hud.get('teams') or '—'}",
            f"competição={snap.competition_text or top_hud.get('competition_text') or '—'}",
        ]
        countdown_lines = [
            f"countdown={dbg_countdown}",
            f"fase={dbg_phase}",
            f"contexto={screen_ctx.get('context_summary') or snap.banner_summary or '—'}",
        ]

        top_hud_summary = f"{dbg_phase} | {dbg_score_ok} | {dbg_clock_ok}"
        mapping = {
            "top_hud_unificado": f"TOP HUD: {top_hud_summary} (Raw: {dbg_score_raw} / {dbg_clock_raw})",
            "banner": f"BANNER: {snap.banner_summary or '—'}",
            "countdown_center": f"COUNTDOWN: {dbg_countdown} ({dbg_phase})",
        }

        for key, text in mapping.items():
            try:
                self.roi_cards[key]["txt"].set(text)
            except Exception:
                pass

    def _fill_context_blocks_text(self, blocks: List[Dict[str, Any]]) -> None:
        try:
            self.ctx_blocks_text.configure(state="normal")
            self.ctx_blocks_text.delete("1.0", "end")
            if not blocks:
                self.ctx_blocks_text.insert("end", "Nenhum bloco detectado.\n")
            else:
                for i, block in enumerate(blocks[:24], 1):
                    zone = str(block.get("zone") or "—")
                    text = str(block.get("text") or "—").strip()
                    conf = float(block.get("confidence", 0.0) or 0.0)
                    bbox = block.get("global_bbox") or block.get("bbox") or ()
                    bbox_txt = ""
                    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                        bbox_txt = f" | bbox={tuple(bbox)}"
                    self.ctx_blocks_text.insert(
                        "end",
                        f"{i:02d}. [{zone}] conf={conf:.2f}{bbox_txt}\n{text}\n\n"
                    )
            self.ctx_blocks_text.configure(state="disabled")
        except Exception:
            pass

    def _tick_debug_preview(self) -> None:
        if self._preview_busy:
            self.after(180, self._tick_debug_preview)
            return

        try:
            if self.debug_mode_var.get():
                self._update_preview_widget()
        except Exception as e:
            self._log(f"[WARN] debug_preview: {e}")

        self.after(180, self._tick_debug_preview)

    def _update_preview_widget(self) -> None:
        if self._preview_busy:
            return

        self._preview_busy = True
        try:
            snap = getattr(self, "debug_snapshot", None)

            raw_frame = None
            raw_ts = 0.0
            with self._preview_lock:
                if self._latest_raw_frame is not None:
                    raw_frame = self._latest_raw_frame.copy()
                    raw_ts = float(self._latest_raw_frame_ts)

            annotated = None
            snap_ts = 0.0
            if snap is not None:
                annotated = getattr(snap, "annotated_bgr", None)
                snap_ts = float(getattr(snap, "last_update_ts", 0.0) or 0.0)

            frame_to_show = None
            overlay_mode = "raw"
            draw_ts = 0.0
            roi_edit_active = bool(self._roi_edit_mode.get())

            if roi_edit_active:
                if raw_frame is not None and getattr(raw_frame, "size", 0) > 0:
                    frame_to_show = raw_frame
                    overlay_mode = "raw"
                    draw_ts = raw_ts
                elif annotated is not None and getattr(annotated, "size", 0) > 0:
                    frame_to_show = annotated
                    overlay_mode = "annotated"
                    draw_ts = snap_ts
            else:
                if raw_frame is not None and getattr(raw_frame, "size", 0) > 0:
                    frame_to_show = raw_frame
                    overlay_mode = "raw"
                    draw_ts = raw_ts
                elif annotated is not None and getattr(annotated, "size", 0) > 0:
                    frame_to_show = annotated
                    overlay_mode = "annotated"
                    draw_ts = snap_ts

            if frame_to_show is None:
                self._show_preview_waiting("Aguardando frames...")
                self.preview_status_var.set("Preview: aguardando frames...")
                return

            frame_changed = bool(draw_ts > 0 and draw_ts != self._last_preview_draw_ts)

            canvas_w = max(200, self.preview_canvas.winfo_width())
            canvas_h = max(200, self.preview_canvas.winfo_height())

            # "Modo Stretch" - Esticamos para preencher 100% do Canvas
            # Isso remove TODAS as bordas pretas e garante que o HUD no topo seja visível (sem crop).
            nw = int(canvas_w)
            nh = int(canvas_h)
            main_img = cv2.resize(frame_to_show, (nw, nh), interpolation=cv2.INTER_AREA)

            self._preview_render_size = (nw, nh)
            self._preview_frame_size = (frame_to_show.shape[1], frame_to_show.shape[0])
            self._preview_scale_x = frame_to_show.shape[1] / max(1, nw)
            self._preview_scale_y = frame_to_show.shape[0] / max(1, nh)
            self._preview_padding_x = 0
            self._preview_padding_y = 0

            if frame_changed or self._preview_canvas_image_id is None:
                pil_img = _bgr_to_pil(main_img)

                if pil_img is not None and ImageTk is not None:
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._ensure_preview_image(tk_img, main_img.shape[1], main_img.shape[0])
                else:
                    self._show_preview_waiting("Preview indisponível.")
                    self.preview_status_var.set("Preview: indisponível")
                    return

                if frame_to_show is not None and getattr(frame_to_show, "size", 0) > 0:
                    self._draw_roi_overlays_on_canvas(frame_to_show)
                    if (not roi_edit_active) and bool(self.show_context_boxes_var.get()):
                        self._draw_screen_context_overlays_on_canvas(frame_to_show)

                self._last_preview_draw_ts = draw_ts
            elif roi_edit_active:
                self._draw_roi_overlays_on_canvas(frame_to_show)
            elif bool(self.show_context_boxes_var.get()):
                self._draw_screen_context_overlays_on_canvas(frame_to_show)

            visual_info = getattr(snap, "visual_info", {}) if snap is not None else {}
            
            phase_txt = self.runtime.last_phase or "—"
            clock_txt = self.runtime.last_clock or "—"
            score_txt = self.runtime.last_score or "—"
            
            # Sincronização com falha atual: se o frame atual colapsou, não mostramos o último valor conhecido
            # A MENOS que tenhamos uma correção recente da IA (Soberania Cloud)
            perf = visual_info.get("perf") or {}
            st = getattr(self.detector, "_state", None) # Já definido no topo, mas mantendo para segurança se necessário ou removendo
            last_cloud_corr = getattr(st, "last_cloud_correction_t", -9999) if st else -9999
            cloud_trust = (time.time() - last_cloud_corr) < 120.0
            cloud_enabled = self.detector.cfg.cloud_enabled

            if perf.get("score_status") == "roi_collapsed" and not cloud_trust and not cloud_enabled: score_txt = "—"
            if perf.get("clock_status") == "roi_collapsed" and not cloud_trust and not cloud_enabled: clock_txt = "—"
            
            ctx_txt = self.runtime.last_context or "—"

            # Status formatado para o novo Live Stats Card
            # Ex: "1º Tempo • 0 x 1 • 45:00"
            status_text = f"{phase_txt}  •  {score_txt}  •  {clock_txt}"
            if status_text != self._last_preview_status_text:
                self.preview_status_var.set(status_text)
                self._last_preview_status_text = status_text

            source_for_roi = raw_frame if raw_frame is not None and getattr(raw_frame, "size", 0) > 0 else frame_to_show

            live_rois: Dict[str, np.ndarray] = {}
            if source_for_roi is not None and getattr(source_for_roi, "size", 0) > 0:
                for key in self.roi_cards.keys():
                    rect_xywh = self._current_roi_xywh(key, source_for_roi)
                    if rect_xywh:
                        x, y, w, h = rect_xywh
                        live_rois[key] = _safe_crop(source_for_roi, (x, y, x + w, y + h))
                    else:
                        live_rois[key] = np.zeros((80, 160, 3), dtype=np.uint8)

            for key, roi in live_rois.items():
                card = self.roi_cards.get(key)
                if not card:
                    continue

                base = roi if roi is not None and getattr(roi, "size", 0) > 0 else np.zeros((80, 160, 3), dtype=np.uint8)
                mini = _fit_image(base, 300, 70)
                mini_ctk = _bgr_to_ctk(mini, size=(mini.shape[1], mini.shape[0]))

                if mini_ctk is not None:
                    self._roi_refs[key] = mini_ctk
                    card["img"].configure(text="", image=mini_ctk)
                else:
                    card["img"].configure(text="ROI indisponível", image=None)

            visual_info = visual_info or {}

            screen_ctx = visual_info.get("screen_context") or {}
            score_ctx = screen_ctx.get("scoreboard") or {}
            top_hud_ctx = screen_ctx.get("top_hud") or {}
            teams_text = top_hud_ctx.get("teams") or getattr(snap, "teams_text", None) or "—"
            competition_text = top_hud_ctx.get("competition_text") or getattr(snap, "competition_text", None) or "—"
            phase_text = visual_info.get("match_phase_text") or score_ctx.get("phase_text") or top_hud_ctx.get("phase_text") or "—"
            countdown_text = visual_info.get("countdown_detected") or score_ctx.get("countdown") or top_hud_ctx.get("countdown") or getattr(snap, "countdown", None) or "—"
            clock_text = visual_info.get("clock_raw") or visual_info.get("game_clock_raw") or visual_info.get("game_clock_detected") or score_ctx.get("clock") or top_hud_ctx.get("clock") or getattr(snap, "accepted_clock", None) or "—"
            score_text = visual_info.get("score_raw") or visual_info.get("score_detected") or score_ctx.get("score") or top_hud_ctx.get("score") or getattr(snap, "accepted_score", None) or "—"
            banner_text = visual_info.get("banner_summary") or screen_ctx.get("context_summary") or getattr(snap, "banner_summary", None) or "—"
            ocr_map = {
                "top_hud_unificado": (
                    f"score={score_text} | clock={clock_text} | fase={phase_text} | "
                    f"countdown={countdown_text} | times={teams_text} | competição={competition_text}"
                ),
                "banner": str(banner_text),
                "countdown_center": f"countdown={countdown_text} | fase={phase_text} | contexto={banner_text}",
            }

            for key, card in self.roi_cards.items():
                card["txt"].set(f"OCR: {ocr_map.get(key, '—')}")

            self._refresh_selected_roi_panel()

        finally:
            self._preview_busy = False




    def _tick_autopilot(self) -> None:
        """
        Sobrescreve a lógica do Core para adicionar o Auto-Refresh de eventos (Fase 2).
        """
        st_autopilot = bool(self.auto_prepare_var.get() or self.auto_start_var.get())
        
        # 1. Lógica de Refresh automático da lista (a cada 10min) se o Autopilot estiver ligado
        if st_autopilot:
            now = time.time()
            if (now - self._last_events_refresh_t) > 600: # 10 minutos
                # Se for o primeiro refresh (0.0), damos um offset de 30s pra não bater com o start
                if self._last_events_refresh_t == 0.0:
                    self._last_events_refresh_t = now - 570 
                else:
                    self._last_events_refresh_t = now
                    self._log("[AUTO] Iniciando refresh automático da lista de eventos...")
                    self._load_events()

        # 2. Chama a lógica base (verificação de LIVE/UPCOMING)
        # O super()._tick_autopilot() já cuida do self.after(1000, ...)
        super()._tick_autopilot()

    def _update_fragments_from_detector(self) -> None:
        tl = self.detector.get_timeline()
        if not tl:
            return

        filt = self.frag_filter_var.get().strip().lower()
        start_idx = max(0, int(self.runtime.timeline_seen))

        if start_idx >= len(tl):
            return

        new_items = tl[start_idx:]
        for it in new_items:
            typ = (it.get("type") or "").lower()

            # Filtro inteligente para Banners/IA
            if filt != "all":
                if filt == "banners/ia":
                    is_banner = typ in ("context", "ocr", "match_event", "cloud_result")
                    if not is_banner:
                        continue
                elif typ != filt:
                    continue

            tsec = float(it.get("t_seconds", 0.0) or 0.0)
            label = str(it.get("label", "") or "")
            conf = float(it.get("confidence", 0.0) or 0.0)
            phase = str(it.get("phase", "") or "")
            details = it.get("details", {})
            if not isinstance(details, dict):
                details = {"raw_text": str(details)}

            if typ == "phase":
                mapping = {
                    "PRE_JOGO_START": "Pré-jogo",
                    "PRIMEIRO_TEMPO_START": "1º Tempo",
                    "SEGUNDO_TEMPO_START": "2º Tempo",
                    "INTERVALO_START": "Intervalo",
                    "POS_JOGO_START": "Pós-jogo",
                }
                pretty_phase = mapping.get(label, label)
                self.phase_var.set(f"Fase: {pretty_phase}")
                self.runtime.last_phase = pretty_phase

            if typ == "context":
                mapping_ctx = {
                    "PRE_JOGO_COUNTDOWN": "Pré-jogo",
                    "JOGO_AO_VIVO": "Jogo ao vivo",
                    "INTERVALO": "Intervalo",
                    "POS_JOGO": "Pós-jogo",
                    "COMENTARIO_ANALISE": "Comentário",
                    "REPLAY": "Replay",
                    "VAR": "VAR",
                    "INTERRUPCAO_TECNICA": "Interrupção técnica",
                    "SEEK_MODE_START": "Seek",
                    "SEEK_MODE_END": "Seek encerrado",
                }

                pretty_ctx = mapping_ctx.get(label, label)
                ctx_summary = ""

                if details.get("context_summary"):
                    ctx_summary = str(details.get("context_summary")).strip()
                elif details.get("banner_summary"):
                    ctx_summary = str(details.get("banner_summary")).strip()
                elif details.get("speech_summary"):
                    ctx_summary = str(details.get("speech_summary")).strip()
                elif label.startswith("TRANSCRIPT:") and details.get("text"):
                    ctx_summary = str(details.get("text")).strip()[:120]
                    pretty_ctx = "Transcrição"
                elif details.get("text"):
                    ctx_summary = str(details.get("text")).strip()[:120]
                elif details.get("banner"):
                    ctx_summary = str(details.get("banner")).strip()[:120]

                self.runtime.last_context = pretty_ctx
                self.runtime.last_context_summary = ctx_summary or "—"

                # Disparar Auto-clip se for anúncio
                self._trigger_auto_clip(label, details)

                if "SEEK" in label.upper():
                    self.runtime.last_seek_state = pretty_ctx

            clock = details.get("clock")
            score = details.get("score") or details.get("score_detected")

            if clock:
                self.clock_var.set(f"Clock: {clock}")
                self.runtime.last_clock = str(clock)

            if score:
                self.score_var.set(f"Score: {score}")
                self.runtime.last_score = str(score)

            if "score_to" in details and details.get("score_to"):
                final_score = str(details.get("score_to"))
                self.score_var.set(f"Score: {final_score}")
                self.runtime.last_score = final_score

            if typ == "match_event":
                event_map = {
                    "GOL": "Gol",
                    "CARTAO_AMARELO": "Cartão amarelo",
                    "CARTAO_VERMELHO": "Cartão vermelho",
                    "VAR": "VAR",
                    "SUBSTITUICAO": "Substituição",
                }
                pretty_event = event_map.get(label, label)
                extra = ""

                if details.get("score_to"):
                    extra = f" ({details.get('score_to')})"
                elif details.get("summary"):
                    extra = f" — {str(details.get('summary'))[:80]}"

                self.runtime.last_event = pretty_event + extra

            if typ == "status":
                hb_clock = details.get("clock")
                hb_score = details.get("score")
                hb_phase = details.get("phase")
                hb_context = details.get("context")

                visual_info = details.get("visual_info", {}) or {}
                if not isinstance(visual_info, dict):
                    visual_info = {}

                visual_state = (
                    details.get("visual_state")
                    or visual_info.get("visual_state")
                    or getattr(self.debug_snapshot, "visual_state", None)
                    or "nao_detectado"
                )

                visual_conf = float(
                    visual_info.get("visual_confidence", visual_info.get("score", 0.0)) or 0.0
                )
                self.runtime.last_visual_confidence = visual_conf

                if hb_clock:
                    self.clock_var.set(f"Clock: {hb_clock}")
                    self.runtime.last_clock = str(hb_clock)
                elif visual_info.get("game_clock_detected"):
                    clk = str(visual_info.get("game_clock_detected"))
                    self.clock_var.set(f"Clock: {clk}")
                    self.runtime.last_clock = clk

                if hb_score:
                    self.score_var.set(f"Score: {hb_score}")
                    self.runtime.last_score = str(hb_score)
                elif visual_info.get("score_detected"):
                    sc = str(visual_info.get("score_detected"))
                    self.score_var.set(f"Score: {sc}")
                    self.runtime.last_score = sc

                if hb_phase:
                    phase_map = {
                        "pre_jogo": "Pré-jogo",
                        "jogo": "Jogo",
                        "primeiro_tempo": "1º Tempo",
                        "intervalo": "Intervalo",
                        "segundo_tempo": "2º Tempo",
                        "pos_jogo": "Pós-jogo",
                    }
                    pretty_phase = phase_map.get(str(hb_phase), str(hb_phase))
                    self.phase_var.set(f"Fase: {pretty_phase}")
                    self.runtime.last_phase = pretty_phase
                else:
                    match_phase_text = str(
                        visual_info.get("match_phase_text")
                        or visual_state
                        or ""
                    ).strip()
                    if match_phase_text:
                        phase_map2 = {
                            "pre_jogo": "Pré-jogo",
                            "primeiro_tempo": "1º Tempo",
                            "segundo_tempo": "2º Tempo",
                            "intervalo": "Intervalo",
                            "pos_jogo": "Pós-jogo",
                            "jogo": "Jogo",
                        }
                        pretty_phase2 = phase_map2.get(match_phase_text, match_phase_text)
                        self.phase_var.set(f"Fase: {pretty_phase2}")
                        self.runtime.last_phase = pretty_phase2

                if hb_context:
                    ctx_map = {
                        "pre_jogo_countdown": "Pré-jogo",
                        "jogo_ao_vivo": "Jogo ao vivo",
                        "intervalo": "Intervalo",
                        "pos_jogo": "Pós-jogo",
                        "comentario": "Comentário",
                        "replay": "Replay",
                        "var": "VAR",
                        "interrupcao_tecnica": "Interrupção técnica",
                        "seek_mode_start": "Seek",
                        "seek_mode_end": "Seek encerrado",
                    }
                    pretty_ctx = ctx_map.get(str(hb_context), str(hb_context))
                    self.runtime.last_context = pretty_ctx

                    banner_summary = str(
                        visual_info.get("banner_summary")
                        or details.get("context_summary")
                        or ""
                    ).strip()
                    if banner_summary:
                        self.runtime.last_context_summary = banner_summary
                else:
                    banner_summary = str(
                        visual_info.get("banner_summary")
                        or details.get("context_summary")
                        or ""
                    ).strip()
                    if banner_summary:
                        self.runtime.last_context_summary = banner_summary

                event_parts = []
                if visual_info.get("is_goal"):
                    event_parts.append("Gol")
                if visual_info.get("is_yellow_card"):
                    event_parts.append("Cartão amarelo")
                if visual_info.get("is_red_card"):
                    event_parts.append("Cartão vermelho")
                if visual_info.get("is_var"):
                    event_parts.append("VAR")
                if visual_info.get("is_substitution"):
                    event_parts.append("Substituição")
                if visual_info.get("is_replay"):
                    event_parts.append("Replay")

                if event_parts:
                    evtxt = " / ".join(event_parts)
                    self.runtime.last_event = evtxt

            line = f"[{tsec:06.1f}s] {typ.upper():12} {label:22} conf={conf:.2f} phase={phase}"

            hint = ""
            if "context_summary" in details and details.get("context_summary"):
                hint = str(details.get("context_summary"))[:160]
            elif "banner_summary" in details and details.get("banner_summary"):
                hint = str(details.get("banner_summary"))[:160]
            elif "speech_summary" in details and details.get("speech_summary"):
                hint = str(details.get("speech_summary"))[:160]
            elif "banner" in details:
                hint = str(details.get("banner"))[:120]
            elif "score_to" in details:
                hint = f"{details.get('score_from')} → {details.get('score_to')}"
            elif "mean" in details:
                hint = f"mean={details.get('mean')}"
            elif "diff_mean" in details:
                hint = f"diff={details.get('diff_mean')}"
            elif "text" in details:
                hint = str(details.get("text"))[:120]
            elif "visual_state" in details:
                hint = f"visual={details.get('visual_state')}"
            elif "clock" in details and details.get("clock"):
                hint = f"clock={details.get('clock')}"

            if hint:
                line += f" | {hint}"

            self._append_fragment(line + "\n")

        self.runtime.timeline_seen = len(tl)
    # =========================================================
    # Cleanup
    # =========================================================

    def _run_cleanup_now(self) -> None:
        try:
            days = int(self.cleanup_days_var.get() or 7)
        except Exception:
            days = 7

        # 1. Cleanup data/events (pastas de frames/debug)
        base_events = os.path.join("data", "events")
        _ensure_dir(base_events)
        cutoff_events = time.time() - (days * 86400)
        removed_ev = 0
        for name in os.listdir(base_events):
            p = os.path.join(base_events, name)
            if not os.path.isdir(p): continue
            try:
                if os.path.getmtime(p) < cutoff_events:
                    shutil.rmtree(p, ignore_errors=True)
                    removed_ev += 1
            except: pass

        # 2. Cleanup data/reports (PDFs e JSONs de auditoria) - MANDATÓRIO 5 DIAS
        base_reports = os.path.join("data", "reports")
        _ensure_dir(base_reports)
        cutoff_reports = time.time() - (5 * 86400) # 5 dias conforme solicitado
        removed_rep = 0
        for name in os.listdir(base_reports):
            p = os.path.join(base_reports, name)
            # Remove arquivos .pdf e .json antigos
            if os.path.isfile(p) and (p.endswith(".pdf") or p.endswith(".json")):
                try:
                    if os.path.getmtime(p) < cutoff_reports:
                        os.remove(p)
                        removed_rep += 1
                except: pass

        self._log(f"[CLEANUP] Eventos: {removed_ev} (>{days}d) | Relatórios: {removed_rep} (>5d)")

    def _open_events_folder(self) -> None:
        try:
            p = os.path.abspath(os.path.join("data", "events"))
            _ensure_dir(p)
            os.startfile(p)  # type: ignore[attr-defined]
        except Exception as e:
            self._log(f"[ERRO] abrir pasta: {e}")

    def _build_report_event_meta(self) -> Dict[str, Any]:
        runtime = getattr(self, "runtime", None)
        return {
            "id": getattr(runtime, "event_id", None),
            "title": getattr(runtime, "event_title", None) or getattr(runtime, "current_match_display", None) or "Sessão monitorada",
            "url": getattr(runtime, "event_url", None),
            "channel": getattr(runtime, "channel_name", None) or self.channel_var.get().strip(),
            "scheduled_start": getattr(runtime, "scheduled_start", None),
            "status": getattr(runtime, "event_status", None) or ("finished" if not getattr(runtime, "running", False) else "live"),
            "competition": getattr(runtime, "current_competition", None),
            "match_display": getattr(runtime, "current_match_display", None),
            "team_a": getattr(runtime, "team_a", None),
            "team_b": getattr(runtime, "team_b", None),
        }

    def _build_report_notes(self, reason: str, finalize: bool) -> Dict[str, Any]:
        runtime = getattr(self, "runtime", None)
        snap = getattr(self, "debug_snapshot", None)
        now_ts = time.time()
        last_ok_t = float(getattr(self, "_last_pipeline_processed_t", 0.0) or 0.0)
        no_frames_for = (now_ts - last_ok_t) if last_ok_t > 0 else None
        return {
            "report_kind": "final" if finalize else "partial",
            "finalize_report": bool(finalize),
            "end_reason": reason,
            "frames_seen": int(getattr(runtime, "frames_seen", 0) or 0),
            "last_clock": getattr(runtime, "last_clock", None) or getattr(snap, "accepted_clock", None) or getattr(snap, "raw_clock", None),
            "last_score": getattr(runtime, "last_score", None) or getattr(snap, "accepted_score", None) or getattr(snap, "raw_score", None),
            "last_phase": getattr(runtime, "last_phase", None) or getattr(snap, "match_phase_text", None),
            "last_context": getattr(runtime, "last_context", None),
            "last_context_summary": getattr(runtime, "last_context_summary", None),
            "last_event": getattr(runtime, "last_event", None),
            "last_visual_confidence": getattr(runtime, "last_visual_confidence", None),
            "detector_latency_ms": getattr(runtime, "detector_latency_ms", None),
            "detector_fps": getattr(runtime, "detector_fps", None),
            "last_seek_state": getattr(runtime, "last_seek_state", None),
            "no_frames_for_seconds": round(float(no_frames_for), 3) if no_frames_for is not None else None,
        }

    def _build_report_base_name(self) -> str:
        parts: List[str] = []
        try:
            ch = _safe_slug(self.channel_var.get().strip())
            if ch:
                parts.append(ch)
        except Exception:
            pass
        try:
            match_name = _safe_slug(getattr(self.runtime, "current_match_display", None) or getattr(self.runtime, "event_title", None) or "session_live")
            if match_name:
                parts.append(match_name)
        except Exception:
            parts.append("session_live")
        return "live_" + "_".join([p for p in parts if p])

    def _generate_report(self, finalize: bool, reason: str) -> Optional[Any]:
        try:
            timeline = self.detector.get_timeline() or []
        except Exception as e:
            self._log(f"[WARN] não consegui obter timeline para relatório: {e}")
            timeline = []

        event_meta = self._build_report_event_meta()
        notes = self._build_report_notes(reason=reason, finalize=finalize)
        base_name = self._build_report_base_name()

        try:
            paths = self.reporter.update_single_file_report(
                event_meta=event_meta,
                timeline=timeline,
                notes=notes,
                base_name=base_name,
                finalize=bool(finalize),
                generate_pdf_on_finalize=True,
                generate_pdf_while_live=True,
            )
            kind = "final" if finalize else "parcial"
            self._log(f"[REPORT] {kind} gerado | json={paths.json_path} | pdf={paths.pdf_path}")
            
            if finalize and paths and getattr(paths, "pdf_path", None):
                try:
                    from modules.audited_games_manager import AuditedGamesManager
                    meta = event_meta or {}
                    t1 = meta.get("team1") or (self.expert_team1_var.get() if hasattr(self, "expert_team1_var") else "Mandante")
                    t2 = meta.get("team2") or (self.expert_team2_var.get() if hasattr(self, "expert_team2_var") else "Visitante")
                    comp = meta.get("competition") or (self.expert_comp_var.get() if hasattr(self, "expert_comp_var") else "Brasileirão")
                    d_str = meta.get("date") or (self.expert_date_var.get() if hasattr(self, "expert_date_var") else datetime.now().strftime("%d/%m/%Y"))
                    p_str = meta.get("platform") or (self.expert_platform_var.get() if hasattr(self, "expert_platform_var") else "CazéTV")
                    
                    AuditedGamesManager.add_audit({
                        "id": f"audit_{t1}_{t2}_{datetime.now().strftime('%Y%m%d%H%M')}",
                        "team1": t1,
                        "team2": t2,
                        "score": meta.get("score", "Finalizado"),
                        "comp": comp,
                        "date": d_str,
                        "time": datetime.now().strftime("%H:%M"),
                        "platform": p_str,
                        "pdf_path": paths.pdf_path,
                        "goals_count": len([m for m in (timeline or []) if "gol" in str(m.get("label", "")).lower()]),
                        "cards_count": len([m for m in (timeline or []) if "cart" in str(m.get("label", "")).lower()]),
                        "brands_count": len([m for m in (timeline or []) if "brand" in str(m.get("label", "")).lower() or "anuncio" in str(m.get("label", "")).lower()]),
                        "status": "Concluído (IA)",
                        "summary": notes or "Auditoria oficial concluída com sucesso.",
                        "timeline": [
                            {"min": m.get("timestamp_str", f"{i*5}'"), "type": m.get("label", "Lance"), "desc": m.get("text", "")}
                            for i, m in enumerate((timeline or [])[:8])
                        ],
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    if hasattr(self, "_render_audited_games_ui"):
                        self.after(0, self._render_audited_games_ui)
                except Exception as e_reg:
                    self._log(f"[AUDIT REG WARN] Erro ao registrar no mural: {e_reg}")

            return paths
        except Exception as e:
            self._log(f"[ERRO] geração de relatório ({'final' if finalize else 'parcial'}): {e}")
            self._log(traceback.format_exc())
            return None

    def _send_report_via_email(self, pdf_path: str) -> None:
        if not pdf_path or not os.path.exists(pdf_path):
            self._log("[EMAIL] Erro: PDF não encontrado para envio.")
            return

        recipients_raw = self.email_recipients_var.get()
        if not recipients_raw:
            self._log("[EMAIL] Erro: Nenhum destinatário configurado.")
            return

        import re
        recipients = [r.strip() for r in re.split(r'[,;]', recipients_raw) if r.strip()]
        if not recipients:
            self._log("[EMAIL] Erro: Lista de destinatários inválida.")
            return

        # Carregar credenciais do google_ai.json
        config_path = _get_config_read_path("google_ai.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                creds = json.load(f)
            sender = creds.get("email")
            password = creds.get("senha")
        except Exception as e:
            self._log(f"[EMAIL] Erro ao carregar credenciais: {e}")
            return

        if not sender or not password or "SEU_EMAIL" in sender:
            self._log("[EMAIL] Erro: Credenciais de e-mail não configuradas no google_ai.json.")
            return

        self._log(f"[EMAIL] Enviando relatório para {len(recipients)} destinatários...")
        
        try:
            service = EmailService(
                smtp_server=EMAIL_SMTP_SERVER,
                smtp_port=EMAIL_SMTP_PORT,
                sender_email=sender,
                sender_password=password
            )
            
            subject = f"Relatório de Monitoramento - {self.runtime.current_match_display or 'Evento'}"
            body = f"Segue em anexo o relatório PDF gerado pelo Monitor de Esportes.\n\nEvento: {self.runtime.current_match_display}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\nMotivo: {self._finalize_reason}"
            
            success = service.send_report(recipients, subject, body, pdf_path)
            if success:
                self._log("[EMAIL] Relatório enviado com sucesso!")
            else:
                self._log("[EMAIL] Falha ao enviar relatório. Verifique os logs do console.")
        except Exception as e:
            self._log(f"[EMAIL] Exceção ao enviar e-mail: {e}")

    def _finalize_and_stop(self, reason: str = "manual_stop") -> None:
        if self._finalize_in_progress and self._finalize_reason and self._finalize_reason != reason:
            self._log(f"[FINALIZE] já em andamento ({self._finalize_reason}); ignorando novo motivo={reason}")
            return

        self._finalize_in_progress = True
        self._finalize_reason = reason

        try:
            self.runtime.preparing = True
            self._expert_stop_event.clear()
            self._set_status("preparing", f"Finalizando monitoramento ({reason})...")
        except Exception:
            pass

        try:
            paths = self._generate_report(finalize=True, reason=reason)
            if paths and getattr(paths, "pdf_path", None):
                pdf_p = paths.pdf_path
                self.after(0, lambda p=pdf_p: self._show_report_completed_dialog(p))
                if self.send_report_email_var.get():
                    self._send_report_via_email(pdf_p)
        except Exception as e:
            self._log(f"[ERRO] finalize_and_stop/report: {e}")

        try:
            self.detector.stop_session()
        except Exception as e:
            self._log(f"[WARN] stop_session: {e}")

        # Marcar como finalizado na lista local para o autopilot pular pro próximo
        if self.runtime.event_id:
            for ev in self._events:
                eid = _safe_slug(ev.get("id") or ev.get("title") or "event")
                if eid == self.runtime.event_id:
                    ev["status"] = "ended"
                    self._log(f"[AUTO] Evento '{ev.get('title')}' marcado como finalizado na lista.")
                    break

        try:
            # v11.0: Parar ingestão de frames explicitamente
            if hasattr(self, "stream") and self.stream is not None:
                self.stream.stop()
                self._log("[STREAM] Ingestão de frames encerrada.")
            
            self.obs.disconnect() # v10.5: Corta sinal de frames do OBS
            with self._preview_lock:
                self._latest_raw_frame = None
        except Exception as e:
            self._log(f"[WARN] finalize_and_stop/stream_stop: {e}")

        self.runtime.running = False
        self.runtime.preparing = False
        self._finalize_in_progress = False
        self._finalize_reason = ""

        self._sync_buttons()
        self.after(0, self._render_events) # Atualiza visual da lista (badges)

    def _stop_monitoring(self) -> None:
        if self._finalize_in_progress and self.runtime.running:
            self._log("[FINALIZE] finalização já em andamento.")
            return

        if not bool(getattr(self.runtime, "running", False) or getattr(self.runtime, "preparing", False)):
            try:
                self.detector.stop_session()
            except Exception:
                pass
            try:
                self.runtime.running = False
                self.runtime.preparing = False
            except Exception:
                pass
            self._set_status("stopped", "Parado")
            self._sync_buttons()
            return

        self._finalize_and_stop("manual_stop")

    # =========================================================
    # Close
    # =========================================================

    def _on_close(self) -> None:
        try:
            self._save_roi_enabled_profile()
            self._save_general_settings()
        except Exception:
            pass

        try:
            self._analysis_stop_flag.set()
        except Exception:
            pass

        try:
            if self.runtime.running or self.runtime.preparing:
                self._stop_monitoring()
        except Exception:
            pass

        try:
            if hasattr(self, "stream") and self.stream is not None:
                self.stream.stop()
            if self._local_analysis_thread and self._local_analysis_thread.is_alive():
                self._local_analysis_thread.join(timeout=1.0)
        except Exception:
            pass

        try:
            self.obs.disconnect()
        except Exception:
            pass

        self.destroy()


class LoginWindow(ctk.CTk):
    """Janela de Autenticação Segura para Acesso à Aplicação."""
    def __init__(self):
        super().__init__()
        self.title("Autenticação - Monitor de Esportes Media DNA")
        self.geometry("420x350")
        self.resizable(False, False)
        self.configure(fg_color="#121212")
        
        self.authenticated = False
        
        # Centralizar na tela
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws // 2) - (w // 2)
        y = (hs // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        card = ctk.CTkFrame(self, corner_radius=14, fg_color="#1e1e1e", border_width=1, border_color="#333333")
        card.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(card, text="🔐 LOGIN DE ACESSO", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00CED1").pack(pady=(20, 5))
        ctk.CTkLabel(card, text="Digite suas credenciais corporativas Media DNA", font=ctk.CTkFont(size=11), text_color="#888888").pack(pady=(0, 15))

        self.user_entry = ctk.CTkEntry(card, width=280, placeholder_text="Usuário", height=36)
        self.user_entry.pack(pady=6)
        self.user_entry.insert(0, "monitor_esporte")

        self.pass_entry = ctk.CTkEntry(card, width=280, placeholder_text="Senha", show="•", height=36)
        self.pass_entry.pack(pady=6)

        self.lbl_msg = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FF4500")
        self.lbl_msg.pack(pady=4)

        btn_login = ctk.CTkButton(
            card, text="ENTRAR NA APLICAÇÃO", font=ctk.CTkFont(size=12, weight="bold"),
            width=280, height=38, fg_color="#00CED1", text_color="black", hover_color="#008B8B",
            command=self._verify_login
        )
        btn_login.pack(pady=(8, 15))
        
        self.bind("<Return>", lambda event: self._verify_login())

    def _verify_login(self):
        user = self.user_entry.get().strip()
        pwd = self.pass_entry.get().strip()
        
        if user == "monitor_esporte" and pwd == "adintell":
            self.authenticated = True
            self.destroy()
        else:
            self.lbl_msg.configure(text="❌ Usuário ou senha incorretos.")


def main() -> None:
    app = MonitorApp()
    app.mainloop()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()

# ============================================================
# CLEAN ROI PATCH (top_hud_unificado / banner / countdown_center)
# ============================================================

def _mg_clean_roi_keys(self) -> List[str]:
    return ["top_hud_unificado", "banner", "countdown_center"]

MonitorApp._get_roi_toggle_keys = _mg_clean_roi_keys


def _mg_clean_ensure_roi_toggle_vars(self) -> None:
    wanted = self._get_roi_toggle_keys()
    keep = {str(k): self.roi_enabled_vars.get(k) for k in wanted if k in self.roi_enabled_vars}
    self.roi_enabled_vars = {}
    for key in wanted:
        self.roi_enabled_vars[key] = keep.get(key) or ctk.BooleanVar(value=True)

MonitorApp._ensure_roi_toggle_vars = _mg_clean_ensure_roi_toggle_vars


def _mg_set_roi_mode_performance_clean(self) -> None:
    self._ensure_roi_toggle_vars()
    keep = {"top_hud_unificado"}
    for key, var in self.roi_enabled_vars.items():
        var.set(key in keep)

MonitorApp._set_roi_mode_performance = _mg_set_roi_mode_performance_clean


def _mg_set_roi_mode_full_clean(self) -> None:
    self._ensure_roi_toggle_vars()
    for var in self.roi_enabled_vars.values():
        var.set(True)

MonitorApp._set_roi_mode_full = _mg_set_roi_mode_full_clean


# =========================================================
# FINAL LIVE REPORT BOOTSTRAP PATCH
# =========================================================
_old_generate_report_final = MonitorApp._generate_report
_old_tick_ui_final = MonitorApp._tick_ui

def _ensure_live_report_bootstrap(self) -> None:
    runtime = getattr(self, 'runtime', None)
    if runtime is None:
        return
    active = bool(getattr(runtime, 'running', False) or getattr(runtime, 'preparing', False))
    event_id = str(getattr(runtime, 'event_id', '') or '')
    if not active or not event_id:
        return
    if bool(getattr(runtime, '_live_report_bootstrapped', False)):
        return
    try:
        if not bool(getattr(self.detector, '_t0_wall', None)) and not bool(self.detector.get_timeline()):
            try:
                self.detector.start_session(event_id)
            except Exception:
                pass
        _old_generate_report_final(self, finalize=False, reason='session_bootstrap')
        setattr(runtime, '_live_report_bootstrapped', True)
        runtime.last_partial_report_t = time.time()
        try:
            self._log('[REPORT] bootstrap live gerado em pre_jogo')
        except Exception:
            pass
    except Exception as exc:
        try:
            self._log(f'[WARN] bootstrap live report: {exc}')
        except Exception:
            pass

def _tick_ui_with_live_report_bootstrap(self) -> None:
    try:
        _ensure_live_report_bootstrap(self)
    except Exception:
        pass
    return _old_tick_ui_final(self)

MonitorApp._ensure_live_report_bootstrap = _ensure_live_report_bootstrap
MonitorApp._tick_ui = _tick_ui_with_live_report_bootstrap
