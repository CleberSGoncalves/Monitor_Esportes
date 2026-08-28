from __future__ import annotations

# --- bootstrap de path (pra rodar no VSCode / python gui/main_gui.py) ---
import sys
from pathlib import Path
from datetime import datetime

import tkinter as tk
import unicodedata

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ------------------------------------------------------------------------

import os
import re
import json
import time
import shutil
import threading
import traceback
from typing import Any, Dict, List, Optional, Tuple

from modules.perf_logger import PerfLogger

import customtkinter as ctk
import cv2
import numpy as np

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

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
)
from modules.youtube_metadata import get_youtube_metadata
from modules.youtube_events import get_channel_events
from modules.obs_controller import OBSController
from modules.event_detector import EventDetector
from modules.report_generator import ReportGenerator
from core.monitor_core import MonitorCoreMixin
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
    ("Eliminatórias", ["eliminatorias", "eliminatórias", "qualifiers"]),
    ("Amistoso", ["amistoso", "friendly"]),
]


class MonitorApp(MonitorCoreMixin, ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_default_color_theme("blue")
        ctk.set_appearance_mode("Dark")

        self.perf = PerfLogger()

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

        self.preview_status_var = ctk.StringVar(value="Preview: aguardando frames...")
        self.detector_stage_var = ctk.StringVar(value="Detector: ocioso")
        self.build_marker_var = ctk.StringVar(value="")

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

        self.stream = None

        self.title("Monitor_Esportes • GUI V4 Debug • BUILD NOVA")
        self.geometry("1600x940")
        self.minsize(1280, 760)

        self.runtime = MonitorRuntime()
        self.debug_snapshot = DebugSnapshot()

        self.obs = OBSController(
            host=OBS_HOST,
            port=OBS_PORT,
            password=OBS_PASSWORD,
            obs_exe_path=OBS_EXE_PATH,
            obs_args=OBS_ARGS,
        )
        self.detector = EventDetector()
        self.detector.set_logger(self._log_from_pipeline_component)
        self.reporter = ReportGenerator(reports_dir="data/reports")

        self._preview_display_size: Tuple[int, int] = (920, 560)
        self._preview_render_size: Tuple[int, int] = (1, 1)
        self._preview_frame_size: Tuple[int, int] = (1, 1)
        self._preview_scale_x: float = 1.0
        self._preview_scale_y: float = 1.0

        self._preview_drag_start: Optional[Tuple[int, int]] = None
        self._preview_drag_rect_id: Optional[int] = None
        self._preview_drag_label_id: Optional[int] = None
        self._last_roi_crop_applied: bool = False

        self._roi_edit_mode = ctk.BooleanVar(value=False)
        self.selected_roi_var = ctk.StringVar(value="clock")
        self.show_context_boxes_var = ctk.BooleanVar(value=False)

        self.roi_pixel_var = ctk.StringVar(value="px = —")
        self.roi_percent_var = ctk.StringVar(value="pct = —")
        self.roi_ocr_var = ctk.StringVar(value="OCR = —")
        self.roi_file_var = ctk.StringVar(value="arquivo = —")

        self.roi_cards: Dict[str, Dict[str, Any]] = {}
        self._roi_refs: Dict[str, Any] = {}
        self.roi_enabled_vars: Dict[str, ctk.BooleanVar] = {}
        self._roi_enabled_checks_built: bool = False

        self._events: List[Dict[str, Any]] = []
        self._selected_index: Optional[int] = None

        self._analysis_stop_flag = threading.Event()
        self._local_analysis_thread: Optional[threading.Thread] = None
        self._last_local_analyzed_raw_ts: float = 0.0
        self._last_local_analyze_wall_t: float = 0.0
        self._last_pipeline_watchdog_t: float = 0.0
        self._last_pipeline_processed_t: float = 0.0
        self._pipeline_seq_local: int = 0
        self._no_frames_finalize_timeout_s: float = 600.0
        self._last_no_frames_warn_t: float = 0.0
        self._finalize_in_progress: bool = False
        self._finalize_reason: str = ""

        self._stop_flag = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._ingest_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._log("[BUILD] GUI BUILD NOVA carregada")
        self._log("[BUILD] chamando _start_local_analysis_worker")
        self._start_local_analysis_worker()

        self.after(250, self._tick_ui)
        self.after(180, self._tick_debug_preview)
        self.after(1000, self._tick_autopilot)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._sync_buttons()

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

        if self._preview_canvas_image_id is None:
            self._preview_canvas_image_id = self.preview_canvas.create_image(
                0, 0, anchor="nw", image=self._preview_img_ref
            )
        else:
            self.preview_canvas.itemconfig(self._preview_canvas_image_id, image=self._preview_img_ref)
            self.preview_canvas.coords(self._preview_canvas_image_id, 0, 0)

    def _draw_roi_overlays_on_canvas(self, frame: np.ndarray) -> None:
        vision = getattr(self.detector, "vision", None)
        if vision is None:
            self._clear_preview_overlay_items()
            return

        colors = {
            "score": "#00FF7F",
            "clock": "#FFFF00",
            "phase": "#00BFFF",
            "pre_jogo": "#8A2BE2",
            "jogo": "#00FFAA",
            "intervalo": "#FF66CC",
            "replay": "#4FC3F7",
            "fim_jogo": "#FF00FF",
            "inicio_jogo": "#FF00FF",
            "banner": "#FF9800",
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

            sx1 = int(round(x / max(1e-9, self._preview_scale_x)))
            sy1 = int(round(y / max(1e-9, self._preview_scale_y)))
            sx2 = int(round((x + w) / max(1e-9, self._preview_scale_x)))
            sy2 = int(round((y + h) / max(1e-9, self._preview_scale_y)))

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
            sx1 = int(round(x / max(1e-9, self._preview_scale_x)))
            sy1 = int(round(y / max(1e-9, self._preview_scale_y)))
            sx2 = int(round((x + w) / max(1e-9, self._preview_scale_x)))
            sy2 = int(round((y + h) / max(1e-9, self._preview_scale_y)))
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
        fx = int(round(px * self._preview_scale_x))
        fy = int(round(py * self._preview_scale_y))

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
            "score",
            "clock",
            "phase",
            "countdown_center",
            "banner",
            "pre_jogo",
            "jogo",
            "intervalo",
            "replay",
            "inicio_jogo",
            "fim_jogo",
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
            return True
        except Exception as e:
            self._log(f"[WARN] save roi enabled: {e}")
            return False

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
        keep = {"score", "clock"}
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
        top = ctk.CTkFrame(self, corner_radius=14)
        top.pack(fill="x", padx=12, pady=(12, 8))

        self.theme_var = ctk.StringVar(value="Dark")
        ctk.CTkLabel(top, text="Tema:", width=50).pack(side="left", padx=(12, 6), pady=10)
        self.theme_opt = ctk.CTkOptionMenu(
            top,
            values=["Dark", "Light", "System"],
            variable=self.theme_var,
            command=self._on_theme_change,
            width=120,
        )
        self.theme_opt.pack(side="left", padx=(0, 14), pady=10)

        ctk.CTkLabel(top, text="Canal:", width=60).pack(side="left", padx=(0, 6), pady=10)

        self.channel_var = ctk.StringVar(value="CazéTV")
        self.channel_opt = ctk.CTkOptionMenu(
            top,
            values=["CazéTV", "TNT Sports", "ESPN Brasil", "SporTV (exemplo)", "URL manual"],
            variable=self.channel_var,
            command=self._on_channel_preset,
            width=160,
        )
        self.channel_opt.pack(side="left", padx=(0, 10), pady=10)

        ctk.CTkLabel(top, text="Competição:", width=88).pack(side="left", padx=(0, 6), pady=10)

        self.category_var = ctk.StringVar(value="Todos")
        self.category_opt = ctk.CTkOptionMenu(
            top,
            values=[
                "Todos",
                "Campeonato Paulista",
                "Brasileirao",
                "Copa do Brasil",
                "Libertadores",
                "Sul-Americana",
                "Champions League",
                "Copa do Mundo",
                "Eliminatorias",
                "Amistoso",
            ],
            variable=self.category_var,
            width=180,
        )
        self.category_opt.pack(side="left", padx=(0, 10), pady=10)

        self.channel_url_var = ctk.StringVar(value=CHANNEL_STREAMS_URL)
        self.channel_url_entry = ctk.CTkEntry(top, textvariable=self.channel_url_var, width=360)
        self.channel_url_entry.pack(side="left", padx=(0, 10), pady=10)

        self.btn_load = ctk.CTkButton(top, text="Carregar eventos", command=self._load_events, width=140)
        self.btn_load.pack(side="left", padx=(0, 10), pady=10)

        self.auto_prepare_var = ctk.BooleanVar(value=True)
        self.auto_start_var = ctk.BooleanVar(value=bool(AUTO_MONITOR_WHEN_LIVE))
        self.debug_mode_var = ctk.BooleanVar(value=True)

        self.chk_auto_prepare = ctk.CTkSwitch(top, text="Auto-prepare", variable=self.auto_prepare_var)
        self.chk_auto_prepare.pack(side="left", padx=(0, 10), pady=10)

        self.chk_auto_start = ctk.CTkSwitch(top, text="Auto-start", variable=self.auto_start_var)
        self.chk_auto_start.pack(side="left", padx=(0, 10), pady=10)

        self.chk_debug_mode = ctk.CTkSwitch(top, text="Modo debug visual", variable=self.debug_mode_var)
        self.chk_debug_mode.pack(side="left", padx=(0, 12), pady=10)

        bar2 = ctk.CTkFrame(self, corner_radius=14)
        bar2.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(bar2, text="URL manual do evento (opcional):").pack(side="left", padx=(12, 8), pady=10)
        self.manual_url_var = ctk.StringVar(value="")
        self.manual_url_entry = ctk.CTkEntry(bar2, textvariable=self.manual_url_var, width=640)
        self.manual_url_entry.pack(side="left", padx=(0, 10), pady=10)

        self.btn_start_manual = ctk.CTkButton(
            bar2,
            text="Monitorar URL manual",
            command=self._start_manual_url,
            width=180,
        )
        self.btn_start_manual.pack(side="left", padx=(0, 10), pady=10)

        main = ctk.CTkFrame(self, corner_radius=14)
        main.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        left = ctk.CTkFrame(main, corner_radius=14)
        left.pack(side="left", fill="y", padx=(12, 8), pady=12)
        left.configure(width=340)
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Eventos (LIVE / UPCOMING)", font=ctk.CTkFont(size=14, weight="bold")).pack(
            fill="x", padx=12, pady=(12, 6)
        )

        self.events_box = ctk.CTkScrollableFrame(left, width=300, height=560, corner_radius=12)
        self.events_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._event_buttons: List[Any] = []

        ctrl = ctk.CTkFrame(left, corner_radius=12)
        ctrl.pack(fill="x", padx=12, pady=(0, 12))

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

        self.status_var = ctk.StringVar(value="🔴 Parado")
        self.status_lbl = ctk.CTkLabel(ctrl, textvariable=self.status_var)
        self.status_lbl.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="w")

        ctrl.grid_columnconfigure(0, weight=1)

        right = ctk.CTkFrame(main, corner_radius=14)
        right.pack(side="left", fill="both", expand=True, padx=(8, 12), pady=12)

        self.tabs = ctk.CTkTabview(right, corner_radius=14)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self.tab_monitor = self.tabs.add("Monitoramento")
        self.tab_debug = self.tabs.add("Debug Visual")
        self.tab_frag = self.tabs.add("Fragmentos")
        self.tab_logs = self.tabs.add("Logs")
        self.tab_errors = self.tabs.add("Erros")
        self.tab_cfg = self.tabs.add("Config")

        self._build_tab_monitor()
        self._build_tab_debug()
        self._build_tab_fragments()
        self._build_tab_logs()
        self._build_tab_errors()
        self._build_tab_config()

        self._on_channel_preset(self.channel_var.get())

    def _build_tab_monitor(self) -> None:
        wrap = ctk.CTkFrame(self.tab_monitor, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        title = ctk.CTkLabel(wrap, text="Status ao vivo", font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))

        self.live_summary = ctk.CTkLabel(
            wrap,
            text="Sem monitoramento ativo.",
            justify="left",
            anchor="w",
            wraplength=700,
        )
        self.live_summary.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

        grid = ctk.CTkFrame(wrap, corner_radius=12)
        grid.grid(row=2, column=0, sticky="nsew", padx=12, pady=10)

        self.frames_var = ctk.StringVar(value="Frames: 0")
        self.phase_var = ctk.StringVar(value="Fase: —")
        self.ctx_var = ctk.StringVar(value="Contexto: —")
        self.clock_var = ctk.StringVar(value="Clock: —")
        self.score_var = ctk.StringVar(value="Score: —")
        self.event_var = ctk.StringVar(value="Último evento: —")
        self.match_var = ctk.StringVar(value="Partida: —")
        self.comp_var = ctk.StringVar(value="Competição: —")
        self.visual_conf_var = ctk.StringVar(value="Conf visual: —")
        self.seek_var = ctk.StringVar(value="Seek: —")
        self.detector_perf_var = ctk.StringVar(value="Detector: —")

        items = [
            ("Frames", self.frames_var),
            ("Fase", self.phase_var),
            ("Contexto", self.ctx_var),
            ("Clock", self.clock_var),
            ("Score", self.score_var),
            ("Último evento", self.event_var),
            ("Partida", self.match_var),
            ("Competição", self.comp_var),
            ("Confiança visual", self.visual_conf_var),
            ("Seek", self.seek_var),
            ("Performance", self.detector_perf_var),
        ]

        for i, (lbl, var) in enumerate(items):
            box = ctk.CTkFrame(grid, corner_radius=12)
            box.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")
            ctk.CTkLabel(box, text=lbl, font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=12, pady=(10, 2))
            ctk.CTkLabel(
                box,
                textvariable=var,
                justify="left",
                anchor="w",
                wraplength=230,
            ).pack(anchor="w", padx=12, pady=(0, 10))

        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_columnconfigure(2, weight=1)
        wrap.grid_rowconfigure(2, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

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

        ctk.CTkLabel(topbar, text="ROI:").grid(row=1, column=0, padx=(12, 6), pady=(6, 8), sticky="w")

        self.roi_opt = ctk.CTkOptionMenu(
            topbar,
            values=[
                "score",
                "clock",
                "phase",
                "pre_jogo",
                "jogo",
                "intervalo",
                "replay",
                "fim_jogo",
                "inicio_jogo",
                "banner",
            ],
            variable=self.selected_roi_var,
            command=lambda _v: self._refresh_selected_roi_panel(),
            width=150,
        )
        self.roi_opt.grid(row=1, column=1, padx=(0, 8), pady=(6, 8), sticky="w")

        self.chk_roi_edit = ctk.CTkSwitch(
            topbar,
            text="Calibrar ROI",
            variable=self._roi_edit_mode,
            command=self._on_roi_edit_mode_toggle,
        )
        self.chk_roi_edit.grid(row=1, column=2, padx=(0, 8), pady=(6, 8), sticky="w")

        self.chk_ctx_boxes = ctk.CTkSwitch(
            topbar,
            text="Blocos contexto",
            variable=self.show_context_boxes_var,
            command=lambda: self._update_preview_widget(),
        )
        self.chk_ctx_boxes.grid(row=1, column=3, padx=(0, 8), pady=(6, 8), sticky="w")

        self.btn_roi_save = ctk.CTkButton(
            topbar,
            text="Salvar calibração",
            command=self._save_current_roi_profile,
            width=170,
            height=34
        )
        self.btn_roi_save.grid(row=2, column=0, padx=(12, 8), pady=(0, 10), sticky="ew")
        self.btn_roi_save.grid_propagate(False)

        self.btn_roi_reset = ctk.CTkButton(
            topbar,
            text="Resetar ROI",
            command=self._reset_selected_roi,
            width=140,
            height=34
        )
        self.btn_roi_reset.grid(row=2, column=1, padx=(0, 8), pady=(0, 10), sticky="ew")

        self.btn_roi_reload = ctk.CTkButton(
            topbar,
            text="Recarregar",
            command=self._reload_current_roi_profile,
            width=130,
            height=34
        )
        self.btn_roi_reload.grid(row=2, column=2, padx=(0, 12), pady=(0, 10), sticky="ew")
        info_bar = ctk.CTkFrame(left, corner_radius=10)
        info_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))

        ctk.CTkLabel(info_bar, textvariable=self.roi_file_var, anchor="w").pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(info_bar, textvariable=self.roi_pixel_var, anchor="w").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(info_bar, textvariable=self.roi_percent_var, anchor="w").pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(
            info_bar,
            textvariable=self.roi_ocr_var,
            anchor="w",
            justify="left",
            wraplength=860
        ).pack(fill="x", padx=12, pady=(2, 8))

        ctk.CTkLabel(
            info_bar,
            textvariable=self.preview_status_var,
            anchor="w",
            justify="left",
            wraplength=860
        ).pack(fill="x", padx=12, pady=(2, 2))

        ctk.CTkLabel(
            info_bar,
            textvariable=self.detector_stage_var,
            anchor="w",
            justify="left",
            wraplength=860
        ).pack(fill="x", padx=12, pady=(2, 8))

        self.preview_canvas = tk.Canvas(
            left,
            bg="#111111",
            highlightthickness=0,
            cursor="crosshair"
        )
        self.preview_canvas.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))
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
            ("score", "ROI Score"),
            ("clock", "ROI Clock"),
            ("phase", "ROI Phase"),
            ("pre_jogo", "ROI Pré-jogo"),
            ("jogo", "ROI Jogo"),
            ("intervalo", "ROI Intervalo"),
            ("replay", "ROI Replay"),
            ("inicio_jogo", "ROI Início de Jogo"),
            ("fim_jogo", "ROI Fim de Jogo"),
            ("banner", "ROI Banner"),
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

        self.dbg_visual_state_var = ctk.StringVar(value="visual_state: —")
        self.dbg_phase_var = ctk.StringVar(value="match_phase_text: —")
        self.dbg_countdown_var = ctk.StringVar(value="countdown: —")
        self.dbg_clock_raw_var = ctk.StringVar(value="clock bruto: —")
        self.dbg_clock_ok_var = ctk.StringVar(value="clock aceito: —")
        self.dbg_score_raw_var = ctk.StringVar(value="score bruto: —")
        self.dbg_score_ok_var = ctk.StringVar(value="score aceito: —")
        self.dbg_banner_var = ctk.StringVar(value="banner: —")
        self.dbg_teams_var = ctk.StringVar(value="times: —")
        self.dbg_comp_var = ctk.StringVar(value="competição: —")
        self.dbg_seek_var = ctk.StringVar(value="seek: —")
        self.dbg_perf_var = ctk.StringVar(value="latência/fps: —")

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

        self.ctx_headline_var = ctk.StringVar(value="headline: —")
        self.ctx_subheadline_var = ctk.StringVar(value="subheadline: —")
        self.ctx_left_tag_var = ctk.StringVar(value="left_tag: —")
        self.ctx_right_tag_var = ctk.StringVar(value="right_tag: —")
        self.ctx_bottom_line_var = ctk.StringVar(value="bottom_line: —")
        self.ctx_top_overlay_var = ctk.StringVar(value="top_overlay: —")
        self.ctx_left_panel_var = ctk.StringVar(value="left_panel: —")
        self.ctx_right_panel_var = ctk.StringVar(value="right_panel: —")
        self.ctx_blocks_var = ctk.StringVar(value="blocks: 0")
        self.ctx_blocks_text = None

        self.after(100, self._reload_current_roi_profile)

    def _build_tab_fragments(self) -> None:
        wrap = ctk.CTkFrame(self.tab_frag, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        bar = ctk.CTkFrame(wrap, corner_radius=12)
        bar.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkLabel(bar, text="Filtro:", width=60).pack(side="left", padx=(12, 6), pady=10)
        self.frag_filter_var = ctk.StringVar(value="all")
        self.frag_filter_opt = ctk.CTkOptionMenu(
            bar,
            values=["all", "phase", "context", "match_event", "interruption", "status", "ocr"],
            variable=self.frag_filter_var,
            width=160,
        )
        self.frag_filter_opt.pack(side="left", padx=(0, 12), pady=10)

        self.frag_autoscroll_var = ctk.BooleanVar(value=True)
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

    def _build_tab_config(self) -> None:
        wrap = ctk.CTkFrame(self.tab_cfg, corner_radius=14)
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        grid = ctk.CTkFrame(wrap, corner_radius=12)
        grid.pack(fill="x", padx=12, pady=(12, 12))

        ctk.CTkLabel(grid, text="Prepare antes (min):").grid(row=0, column=0, padx=12, pady=(12, 8), sticky="w")
        self.prepare_min_var = ctk.IntVar(value=int(PREPARE_MINUTES_BEFORE))
        self.prepare_entry = ctk.CTkEntry(grid, width=120)
        self.prepare_entry.insert(0, str(self.prepare_min_var.get()))
        self.prepare_entry.grid(row=0, column=1, padx=12, pady=(12, 8), sticky="w")

        ctk.CTkLabel(grid, text="Cleanup após (dias):").grid(row=1, column=0, padx=12, pady=8, sticky="w")
        self.cleanup_days_var = ctk.IntVar(value=7)
        self.cleanup_entry = ctk.CTkEntry(grid, width=120)
        self.cleanup_entry.insert(0, str(self.cleanup_days_var.get()))
        self.cleanup_entry.grid(row=1, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(grid, text="FPS amostra (frames):").grid(row=2, column=0, padx=12, pady=8, sticky="w")
        self.sample_fps_var = ctk.IntVar(value=int(FRAME_SAMPLE_FPS))
        self.sample_fps_entry = ctk.CTkEntry(grid, width=120)
        self.sample_fps_entry.insert(0, str(self.sample_fps_var.get()))
        self.sample_fps_entry.grid(row=2, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(grid, text="Segmento áudio (s):").grid(row=3, column=0, padx=12, pady=8, sticky="w")
        self.seg_audio_var = ctk.IntVar(value=int(AUDIO_SEGMENT_SECONDS))
        self.seg_audio_entry = ctk.CTkEntry(grid, width=120)
        self.seg_audio_entry.insert(0, str(self.seg_audio_var.get()))
        self.seg_audio_entry.grid(row=3, column=1, padx=12, pady=8, sticky="w")

        ctk.CTkLabel(grid, text="Relatório parcial (s):").grid(row=4, column=0, padx=12, pady=(8, 12), sticky="w")
        self.partial_report_var = ctk.IntVar(value=600)
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

        roi_actions = ctk.CTkFrame(roi_cfg, corner_radius=10)
        roi_actions.grid(
            row=2 + ((len(roi_keys) + cols - 1) // cols),
            column=0,
            columnspan=4,
            sticky="ew",
            padx=12,
            pady=(10, 12),
        )

        ctk.CTkButton(roi_actions, text="Aplicar ROIs agora", command=self._apply_roi_enabled_runtime, width=180).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Salvar perfil de ROI", command=lambda: self._apply_roi_enabled_runtime(save_profile=True), width=180).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Recarregar perfil", command=self._reload_roi_enabled_from_profile, width=160).pack(side="left", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Modo Performance", command=self._set_roi_mode_performance, width=160).pack(side="right", padx=8, pady=8)
        ctk.CTkButton(roi_actions, text="Modo Completo", command=self._set_roi_mode_full, width=150).pack(side="right", padx=8, pady=8)

        self._load_roi_enabled_ui_from_detector()

        actions = ctk.CTkFrame(wrap, corner_radius=12)
        actions.pack(fill="x", padx=12, pady=(0, 12))

        self.btn_apply_cfg = ctk.CTkButton(actions, text="Aplicar configs", command=self._apply_config, width=160)
        self.btn_apply_cfg.pack(side="left", padx=12, pady=12)

        self.btn_cleanup = ctk.CTkButton(actions, text="Rodar cleanup agora", command=self._run_cleanup_now, width=180)
        self.btn_cleanup.pack(side="left", padx=12, pady=12)

        self.btn_open_data = ctk.CTkButton(actions, text="Abrir pasta data/events", command=self._open_events_folder, width=200)
        self.btn_open_data.pack(side="left", padx=12, pady=12)

        note = ctk.CTkLabel(
            wrap,
            text="Obs: estas configs afetam o comportamento da GUI e do pipeline desta sessão.",
            justify="left",
        )
        note.pack(fill="x", padx=12, pady=(0, 12))

    # =========================================================
    # Events list
    # =========================================================

    def _render_events(self) -> None:
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
            return

        for i, ev in enumerate(self._events):
            status = (ev.get("status") or "").lower()
            title = ev.get("title") or "—"
            meta = _extract_event_meta(title, self.category_var.get().strip())
            sched = _fmt_dt(ev.get("scheduled_start"))

            badge = "🟢 LIVE" if status == "live" else ("🟡 UPCOMING" if status == "upcoming" else (status.upper() or "—"))
            subtitle = meta["match_display"]
            comp = meta["competition"]
            line = f"{badge}\n{subtitle}\n{comp} • Início: {sched}"

            btn = ctk.CTkButton(
                self.events_box,
                text=line,
                anchor="w",
                height=76,
                command=lambda idx=i: self._select_event(idx),
            )
            btn.pack(fill="x", padx=8, pady=6)
            self._event_buttons.append(btn)

        self._selected_index = None

    def _select_event(self, idx: int) -> None:
        self._selected_index = idx
        for i, b in enumerate(self._event_buttons):
            try:
                b.configure(fg_color=("gray75", "gray25") if i == idx else None)
            except Exception:
                pass

        ev = self._events[idx]
        meta = _extract_event_meta(ev.get("title") or "", self.category_var.get().strip())
        self.match_var.set(f"Partida: {meta['match_display']}")
        self.comp_var.set(f"Competição: {meta['competition']}")
        self._log(f"[UI] Selecionado: {ev.get('title')} | status={ev.get('status')}")

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
        self._append_text(self.log_text, line, autoscroll=True)
        if ("[ERRO]" in msg or "[WARN]" in msg or "Traceback" in msg or "Exception" in msg) and hasattr(self, "error_text"):
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

    def _append_text(self, widget: ctk.CTkTextbox, text: str, autoscroll: bool = True) -> None:
        widget.configure(state="normal")
        widget.insert("end", text)
        if autoscroll:
            widget.see("end")
        widget.configure(state="disabled")

    def _append_fragment(self, text: str) -> None:
        self._append_text(self.frag_text, text, autoscroll=bool(self.frag_autoscroll_var.get()))

    def _clear_logs(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

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
        url = self.channel_url_var.get().strip()
        selected_category = self.category_var.get().strip()

        if not url:
            self._ui_error("Informe a URL do /streams do canal.")
            return

        self._events = []
        self.after(0, self._render_events)
        self._ui_info(f"Carregando eventos… ({url}) | filtro: {selected_category}")

        def worker() -> None:
            try:
                self._log(f"[FETCH] get_channel_events(url={url})")
                events = get_channel_events(url)

                if not isinstance(events, list):
                    self.after(0, lambda: self._ui_error(f"get_channel_events retornou tipo inválido: {type(events)}"))
                    return

                filtered_events: List[Dict[str, Any]] = []
                for ev in events:
                    title = ev.get("title") or ""
                    if _event_matches_category(title, selected_category):
                        filtered_events.append(ev)

                events = filtered_events

                def k(ev: Dict[str, Any]) -> Tuple[int, float]:
                    st = (ev.get("status") or "").lower()
                    pr = 0 if st == "live" else (1 if st == "upcoming" else 2)
                    dt = _parse_dt(ev.get("scheduled_start"))
                    ts = _safe_timestamp(dt)
                    return (pr, ts)

                events = sorted(events, key=k)

                self._events = events
                self.after(0, self._render_events)

                if len(events) == 0:
                    self.after(0, lambda: self._ui_error(f"Nenhum evento encontrado para o filtro: {selected_category}"))
                else:
                    self.after(0, lambda: self._set_status("stopped", f"{len(events)} eventos carregados para: {selected_category}"))

                self._log(f"[FETCH] OK: {len(events)} eventos após filtro '{selected_category}'.")
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
        if self._selected_index is None or self._selected_index >= len(self._events):
            self._log("[UI] Selecione um evento na lista.")
            return
        ev = self._events[self._selected_index]
        self._start_event(ev, manual_url_override=None)

    def _start_manual_url(self) -> None:
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

    # =========================================================
    # UI tick
    # =========================================================

    def _tick_ui(self) -> None:
        try:
            if self.runtime.running or self.runtime.preparing:
                summary_lines = [
                    f"Evento: {self.runtime.event_title[:90]}",
                    f"Partida: {self.runtime.current_match_display}",
                    f"Competição: {self.runtime.current_competition}",
                ]
                self.live_summary.configure(text="\n".join(summary_lines))
            else:
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
                self.ctx_var.set(f"Contexto: {ctx_text}")
            else:
                self.ctx_var.set("Contexto: —")

            self.event_var.set(f"Último evento: {self.runtime.last_event or '—'}")
            self.visual_conf_var.set(f"Conf visual: {_fmt_conf(self.runtime.last_visual_confidence)}")
            self.seek_var.set(f"Seek: {self.runtime.last_seek_state or '—'}")
            self.detector_perf_var.set(
                f"Detector: {self.runtime.detector_latency_ms:.1f} ms | {self.runtime.detector_fps:.1f} fps"
                if self.runtime.detector_latency_ms > 0
                else "Detector: —"
            )

            self._update_fragments_from_detector()
            self._refresh_debug_vars()

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

        except Exception as e:
            self._log(f"[WARN] tick_ui: {e}")

        self.after(250, self._tick_ui)

    def _refresh_debug_vars(self) -> None:
        snap = self.debug_snapshot

        self.dbg_visual_state_var.set(f"visual_state: {snap.visual_state}")
        self.dbg_phase_var.set(f"match_phase_text: {snap.match_phase_text}")
        self.dbg_countdown_var.set(f"countdown: {snap.countdown}")
        self.dbg_clock_raw_var.set(f"clock bruto: {snap.raw_clock}")
        self.dbg_clock_ok_var.set(f"clock aceito: {snap.accepted_clock}")
        self.dbg_score_raw_var.set(f"score bruto: {snap.raw_score}")
        self.dbg_score_ok_var.set(f"score aceito: {snap.accepted_score}")
        visual_info = getattr(snap, "visual_info", {}) or {}
        screen_ctx = visual_info.get("screen_context") or {}
        top_hud = screen_ctx.get("top_hud") or {}
        bottom_ctx = screen_ctx.get("bottom") or {}
        top_overlay = screen_ctx.get("top_overlay") or {}
        left_panel = screen_ctx.get("left_panel") or {}
        right_panel = screen_ctx.get("right_panel") or {}
        blocks = screen_ctx.get("blocks") or []
        self.dbg_banner_var.set(f"banner: {snap.banner_summary or screen_ctx.get('context_summary') or '—'}")
        self.dbg_teams_var.set(f"times: {snap.teams_text or top_hud.get('teams') or '—'}")
        self.dbg_comp_var.set(f"competição: {snap.competition_text or top_hud.get('competition_text') or screen_ctx.get('top_overlay', {}).get('text', '—')}")
        self.dbg_seek_var.set(f"seek: {'ativo' if snap.seek_active else '—'}")
        self.dbg_perf_var.set(f"latência/fps: {snap.detector_latency_ms:.1f} ms / {snap.fps_loop:.1f} fps")

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

        score_text = f"OCR: bruto={snap.raw_score} | ok={snap.accepted_score}"
        clock_text = f"OCR: bruto={snap.raw_clock} | ok={snap.accepted_clock}"

        mapping = {
            "score": score_text,
            "clock": clock_text,
            "phase": f"OCR: {snap.match_phase_text}",
            "pre_jogo": f"OCR: {snap.countdown}",
            "jogo": f"OCR: {snap.visual_state}",
            "intervalo": f"OCR: {snap.match_phase_text}",
            "replay": f"OCR: {snap.teams_text}",
            "fim_jogo": f"OCR: {snap.competition_text}",
            "inicio_jogo": f"OCR: {snap.banner_summary}",
            "banner": f"OCR: {snap.banner_summary}",
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

            main_img = _fit_image(frame_to_show, canvas_w, canvas_h)

            self._preview_render_size = (main_img.shape[1], main_img.shape[0])
            self._preview_frame_size = (frame_to_show.shape[1], frame_to_show.shape[0])
            self._preview_scale_x = frame_to_show.shape[1] / max(1, main_img.shape[1])
            self._preview_scale_y = frame_to_show.shape[0] / max(1, main_img.shape[0])

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

            phase_txt = self.runtime.last_phase or "—"
            clock_txt = self.runtime.last_clock or "—"
            score_txt = self.runtime.last_score or "—"
            ctx_txt = self.runtime.last_context or "—"

            status_text = (
                f"Preview: modo={overlay_mode} | frames={self.runtime.frames_seen} | "
                f"clock={clock_txt} | score={score_txt} | fase={phase_txt} | contexto={ctx_txt}"
            )
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

            visual_info = getattr(snap, "visual_info", {}) if snap is not None else {}

            screen_ctx = visual_info.get("screen_context") or {}
            score_ctx = screen_ctx.get("scoreboard") or {}
            ocr_map = {
                "score": str(visual_info.get("score_raw") or visual_info.get("score_detected") or score_ctx.get("score") or getattr(snap, "accepted_score", None) or "—"),
                "clock": str(visual_info.get("clock_raw") or visual_info.get("game_clock_raw") or visual_info.get("game_clock_detected") or score_ctx.get("clock") or getattr(snap, "accepted_clock", None) or "—"),
                "phase": str(visual_info.get("match_phase_text") or score_ctx.get("phase_text") or "—"),
                "pre_jogo": str(visual_info.get("countdown_detected") or score_ctx.get("countdown") or "—"),
                "jogo": str(visual_info.get("visual_state") or getattr(snap, "visual_state", None) or "—"),
                "intervalo": str(visual_info.get("match_phase_text") or score_ctx.get("phase_text") or "—"),
                "replay": str(getattr(snap, "replay_text", None) or "—"),
                "fim_jogo": str(getattr(snap, "fim_jogo_text", None) or score_ctx.get("phase_text") or "—"),
                "inicio_jogo": str(getattr(snap, "inicio_jogo_text", None) or screen_ctx.get("top_overlay", {}).get("text", "—") or "—"),
                "banner": str(visual_info.get("banner_summary") or screen_ctx.get("context_summary") or getattr(snap, "banner_summary", None) or "—"),
            }

            for key, card in self.roi_cards.items():
                card["txt"].set(f"OCR: {ocr_map.get(key, '—')}")

            self._refresh_selected_roi_panel()

        finally:
            self._preview_busy = False

    def _start_local_analysis_worker(self) -> None:
        if self._local_analysis_thread and self._local_analysis_thread.is_alive():
            self._log("[PIPELINE] local analysis worker já ativo")
            return
        self._analysis_stop_flag.clear()
        self._local_analysis_thread = threading.Thread(
            target=self._local_analysis_worker_loop,
            name="gui-local-analysis",
            daemon=True,
        )
        self._local_analysis_thread.start()
        self._log("[PIPELINE] local analysis worker iniciado")
        self.after(1000, self._verify_local_analysis_worker_alive)

    def _verify_local_analysis_worker_alive(self) -> None:
        try:
            alive = bool(self._local_analysis_thread and self._local_analysis_thread.is_alive())
            if alive:
                self._log("[PIPELINE] local analysis worker vivo")
            else:
                self._log("[ERRO] local analysis worker não ficou vivo")
                try:
                    self.error_summary_var.set("Erro: worker local não ficou vivo")
                    self.error_count_var.set(f"Erros: {int(str(self.error_count_var.get()).split(':')[-1].strip() or '0') + 1}")
                except Exception:
                    pass
        except Exception as e:
            self._log(f"[WARN] verify worker: {e}")

    def _local_pipeline_log(self, msg: str) -> None:
        try:
            self.after(0, lambda m=msg: self._log(m))
        except Exception:
            try:
                self._log(msg)
            except Exception:
                pass

    def _set_detector_stage_safe(self, msg: str) -> None:
        try:
            self.after(0, lambda m=msg: self.detector_stage_var.set(m))
        except Exception:
            pass

    def _update_pipeline_counters_safe(self, processed_inc: int = 0) -> None:
        try:
            self._pipeline_stats["processed"] = int(self._pipeline_stats.get("processed", 0)) + int(processed_inc)
        except Exception:
            pass

    def _extract_last_status_details(self) -> Dict[str, Any]:
        try:
            tl = self.detector.get_timeline() or []
        except Exception:
            return {}
        for item in reversed(tl):
            if str(item.get("type") or "").lower() == "status":
                details = item.get("details", {}) or {}
                if isinstance(details, dict):
                    return details
        return {}

    def _build_debug_snapshot_from_detector(self, frame_bgr: np.ndarray, analyze_ms: float, t_seconds: float) -> None:
        snap = self.debug_snapshot
        try:
            st = getattr(self.detector, "_state", None)
            visual_info = dict(getattr(st, "last_visual_info", {}) or {}) if st is not None else {}
            perf = dict(getattr(st, "last_perf", {}) or {}) if st is not None else {}
            status_details = self._extract_last_status_details()

            setattr(snap, "frame_bgr", frame_bgr)
            setattr(snap, "annotated_bgr", frame_bgr.copy())
            setattr(snap, "last_update_ts", time.time())
            setattr(snap, "visual_info", visual_info)
            setattr(snap, "visual_state", str(getattr(st, "last_visual_state", "nao_detectado") if st is not None else visual_info.get("visual_state") or "nao_detectado"))
            setattr(snap, "match_phase_text", str(visual_info.get("match_phase_text") or (getattr(st, "phase", "") if st is not None else "")))
            setattr(snap, "countdown", visual_info.get("countdown_detected"))
            setattr(snap, "raw_clock", visual_info.get("game_clock_raw") or visual_info.get("game_clock_detected") or (getattr(st, "last_clock_text", None) if st is not None else None))
            setattr(snap, "accepted_clock", visual_info.get("game_clock_detected") or (getattr(st, "confirmed_clock", None) if st is not None else None) or (getattr(st, "last_clock_text", None) if st is not None else None))
            setattr(snap, "raw_score", visual_info.get("score_raw") or visual_info.get("score_detected") or (getattr(st, "last_score_text", None) if st is not None else None))
            setattr(snap, "accepted_score", visual_info.get("score_detected") or (getattr(st, "confirmed_score", None) if st is not None else None) or (getattr(st, "last_score_text", None) if st is not None else None))
            setattr(snap, "banner_summary", visual_info.get("banner_summary") or visual_info.get("context_summary") or (getattr(st, "last_banner_text", "") if st is not None else ""))
            top_hud = (visual_info.get("screen_context") or {}).get("top_hud") or {}
            setattr(snap, "teams_text", top_hud.get("teams") or (" x ".join([getattr(st, "current_team_a", "—"), getattr(st, "current_team_b", "—")]).strip(" x") if st is not None else ""))
            setattr(snap, "competition_text", top_hud.get("competition_text") or (getattr(st, "current_competition", "") if st is not None else ""))
            setattr(snap, "seek_active", bool((getattr(st, "seek_mode_until", 0.0) if st is not None else 0.0) > float(t_seconds)))
            setattr(snap, "detector_latency_ms", float(perf.get("total_ingest_ms", analyze_ms) or analyze_ms))
            wall_delta = time.time() - float(self._last_local_analyze_wall_t or time.time()) if self._last_local_analyze_wall_t else 0.0
            fps_loop = (1.0 / wall_delta) if wall_delta > 0 else 0.0
            setattr(snap, "fps_loop", float(fps_loop))
            setattr(snap, "replay_text", visual_info.get("replay_text"))
            setattr(snap, "fim_jogo_text", visual_info.get("fim_jogo_text"))
            setattr(snap, "inicio_jogo_text", visual_info.get("inicio_jogo_text"))
            setattr(snap, "last_status_details", status_details)

            self.runtime.frames_seen = int(self.runtime.frames_seen or 0) + 1
            self.runtime.detector_latency_ms = float(perf.get("total_ingest_ms", analyze_ms) or analyze_ms)
            self.runtime.detector_fps = float(fps_loop)
            self.runtime.last_visual_confidence = float(visual_info.get("visual_confidence", 0.0) or 0.0)
            if getattr(snap, "accepted_clock", None):
                self.runtime.last_clock = str(getattr(snap, "accepted_clock"))
            if getattr(snap, "accepted_score", None):
                self.runtime.last_score = str(getattr(snap, "accepted_score"))
            if getattr(snap, "match_phase_text", None):
                self.runtime.last_phase = str(getattr(snap, "match_phase_text"))
            banner_summary = getattr(snap, "banner_summary", None)
            if banner_summary:
                self.runtime.last_context_summary = str(banner_summary)
            self._last_pipeline_processed_t = time.time()
        except Exception as e:
            self._local_pipeline_log(f"[PIPELINE][ERRO] snapshot update: {type(e).__name__}: {e}")

    def _local_analysis_worker_loop(self) -> None:
        self._local_pipeline_log("[PIPELINE] local analysis loop ativo")
        idle_loops = 0
        while not self._analysis_stop_flag.is_set():
            try:
                if not bool(getattr(self.runtime, "running", False)):
                    time.sleep(0.10)
                    continue

                raw_frame = None
                raw_ts = 0.0
                with self._preview_lock:
                    if self._latest_raw_frame is not None:
                        raw_frame = self._latest_raw_frame.copy()
                        raw_ts = float(self._latest_raw_frame_ts or 0.0)

                if raw_frame is None or getattr(raw_frame, "size", 0) == 0 or raw_ts <= 0.0:
                    idle_loops += 1
                    if idle_loops % 50 == 0:
                        self._local_pipeline_log("[PIPELINE] aguardando raw frame para análise local")
                    time.sleep(0.05)
                    continue

                if raw_ts <= float(self._last_local_analyzed_raw_ts or 0.0):
                    if (time.time() - float(self._last_pipeline_watchdog_t or 0.0)) >= 5.0:
                        age = time.time() - raw_ts if raw_ts > 0 else -1.0
                        self._last_pipeline_watchdog_t = time.time()
                        self._local_pipeline_log(
                            f"[PIPELINE] sem frame novo para análise local | raw_age={age:.2f}s | processed={self._pipeline_stats.get('processed', 0)} | queued={self._pipeline_stats.get('queued', 0)}"
                        )
                    time.sleep(0.03)
                    continue

                idle_loops = 0
                self._pipeline_seq_local += 1
                seq = int(self._pipeline_seq_local)
                self._set_detector_stage_safe(f"Detector(local): analisando seq={seq}")
                t0 = time.perf_counter()
                try:
                    elapsed = float(self.detector.elapsed_seconds() or 0.0)
                except Exception:
                    elapsed = 0.0
                if elapsed <= 0.0:
                    elapsed = max(0.0, time.time() - float(self.runtime.last_partial_report_t or time.time()))

                self._local_pipeline_log(f"[PIPELINE] ingest start | seq={seq} | raw_ts={raw_ts:.3f} | shape={getattr(raw_frame, 'shape', None)}")
                self.detector.ingest_frame(raw_frame, elapsed)
                analyze_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                self._last_local_analyzed_raw_ts = raw_ts
                self._last_local_analyze_wall_t = time.time()
                self._update_pipeline_counters_safe(processed_inc=1)
                self._build_debug_snapshot_from_detector(raw_frame, analyze_ms, elapsed)
                self._set_detector_stage_safe(f"Detector(local): OK seq={seq} | {analyze_ms:.1f}ms")
                self._local_pipeline_log(f"[PIPELINE] ingest ok | seq={seq} | {analyze_ms:.1f} ms | processed={self._pipeline_stats.get('processed', 0)}")
            except Exception as e:
                self._set_detector_stage_safe(f"Detector(local): ERRO {type(e).__name__}")
                self._local_pipeline_log(f"[PIPELINE][ERRO] local analyze: {type(e).__name__}: {e}")
                self._local_pipeline_log(traceback.format_exc())
                time.sleep(0.25)

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
            if filt != "all" and typ != filt:
                continue

            tsec = float(it.get("t_seconds", 0.0) or 0.0)
            label = str(it.get("label", "") or "")
            conf = float(it.get("confidence", 0.0) or 0.0)
            phase = str(it.get("phase", "") or "")
            details = it.get("details", {}) or {}

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

                if "SEEK" in label.upper():
                    self.runtime.last_seek_state = pretty_ctx

                if ctx_summary:
                    self.ctx_var.set(f"Contexto: {pretty_ctx} — {ctx_summary}")
                else:
                    self.ctx_var.set(f"Contexto: {pretty_ctx}")

            clock = details.get("clock")
            score = details.get("score_detected")

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
                self.event_var.set(f"Último evento: {pretty_event}{extra}")

            if typ == "status":
                hb_clock = details.get("clock")
                hb_score = details.get("score")
                hb_phase = details.get("phase")
                hb_context = details.get("context")
                visual_info = details.get("visual_info", {}) or {}

                visual_conf = float(visual_info.get("visual_confidence", visual_info.get("score", 0.0)) or 0.0)
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

                match_phase_text = str(visual_info.get("match_phase_text") or "").strip()
                if match_phase_text:
                    phase_map2 = {
                        "pre_jogo": "Pré-jogo",
                        "primeiro_tempo": "1º Tempo",
                        "segundo_tempo": "2º Tempo",
                        "intervalo": "Intervalo",
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
                        self.ctx_var.set(f"Contexto: {pretty_ctx} — {banner_summary}")

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
                    self.event_var.set(f"Último evento: {evtxt}")

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

        base = os.path.join("data", "events")
        _ensure_dir(base)

        cutoff = time.time() - (days * 86400)
        removed = 0

        for name in os.listdir(base):
            p = os.path.join(base, name)
            if not os.path.isdir(p):
                continue
            try:
                mt = os.path.getmtime(p)
                if mt < cutoff:
                    shutil.rmtree(p, ignore_errors=True)
                    removed += 1
            except Exception:
                pass

        self._log(f"[CLEANUP] removidos: {removed} (>{days} dias)")

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
            return paths
        except Exception as e:
            self._log(f"[ERRO] geração de relatório ({'final' if finalize else 'parcial'}): {e}")
            self._log(traceback.format_exc())
            return None

    def _finalize_and_stop(self, reason: str = "manual_stop") -> None:
        if self._finalize_in_progress and self._finalize_reason and self._finalize_reason != reason:
            self._log(f"[FINALIZE] já em andamento ({self._finalize_reason}); ignorando novo motivo={reason}")
            return

        self._finalize_in_progress = True
        self._finalize_reason = reason

        try:
            self._set_status("preparing", f"Finalizando monitoramento ({reason})...")
        except Exception:
            pass

        try:
            self._generate_report(finalize=True, reason=reason)
        except Exception as e:
            self._log(f"[ERRO] finalize_and_stop/report: {e}")

        try:
            self.detector.stop_session()
        except Exception as e:
            self._log(f"[WARN] stop_session: {e}")

        try:
            self.runtime.running = False
            self.runtime.preparing = False
        except Exception:
            pass

        try:
            self._set_status("stopped", f"Monitoramento encerrado ({reason})")
        except Exception:
            pass

        self._sync_buttons()

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
            if self._local_analysis_thread and self._local_analysis_thread.is_alive():
                self._local_analysis_thread.join(timeout=1.0)
        except Exception:
            pass

        try:
            self.obs.disconnect()
        except Exception:
            pass

        self.destroy()


def main() -> None:
    app = MonitorApp()
    app.mainloop()


if __name__ == "__main__":
    main()