from __future__ import annotations

# --- bootstrap de path (pra rodar no VSCode / python gui/main_gui.py) ---
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ------------------------------------------------------------------------

import json
import os
import shutil
import threading
import time
import traceback
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

from config.settings import (
    FRAME_SAMPLE_FPS,
    OBS_BROWSER_SOURCE,
    OBS_SCENE_MONITOR,
    PREPARE_MINUTES_BEFORE,
    SRT_INPUT_URL,
)
from modules.youtube_metadata import get_youtube_metadata
from core.models import (
    DebugSnapshot,
    MonitorRuntime,
    _clean_hud_text,
    _draw_rect,
    _event_paths,
    _fmt_conf,
    _human_age,
    _normalize_rect,
    _now,
    _parse_dt,
    _safe_crop,
    _safe_slug,
    normalize_watch_url_to_embed,
)


class MonitorCoreMixin:
    def _start_analysis_worker(self) -> None:
        self._frame_processing = False
        self._pending_analysis_frame = None
        self._pending_analysis_ts = 0.0
        self._pending_analysis_seq = 0
        self._last_processed_seq = 0
        self._pipeline_stats = {"queued": 0, "processed": 0, "dropped": 0}
        self._last_report_cloud_t = 0.0

        self._analysis_worker_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="analysis_worker",
        )
        self._analysis_worker_thread.start()

    def _stop_analysis_worker(self) -> None:
        try:
            with self._analysis_cv:
                self._pending_analysis_frame = None
                self._pending_analysis_ts = 0.0
                self._analysis_cv.notify_all()
        except Exception:
            pass

    def _enqueue_analysis_frame(self, frame: np.ndarray, ts: float) -> None:
        if frame is None or getattr(frame, "size", 0) == 0:
            return

        with self._analysis_cv:
            if self._pending_analysis_frame is not None:
                self._pipeline_stats["dropped"] += 1

            self._pending_analysis_frame = frame.copy()
            self._pending_analysis_ts = float(ts or time.time())
            self._pending_analysis_enqueue_t = time.perf_counter() # DIAGNÓSTICO
            self._pending_analysis_seq += 1
            self._pipeline_stats["queued"] += 1
            self._analysis_cv.notify()

    def _analysis_loop(self) -> None:
        while not self._stop_flag.is_set():
            with self._analysis_cv:
                self._analysis_cv.wait_for(
                    lambda: self._stop_flag.is_set() or self._pending_analysis_frame is not None,
                    timeout=0.25,
                )

                if self._stop_flag.is_set():
                    break

                frame = self._pending_analysis_frame
                ts = self._pending_analysis_ts
                seq = self._pending_analysis_seq
                enqueue_t = getattr(self, "_pending_analysis_enqueue_t", time.perf_counter())
                
                self._pending_analysis_frame = None
                self._pending_analysis_ts = 0.0

            if frame is None:
                continue

            # Calcular delay na fila
            queue_delay_ms = (time.perf_counter() - enqueue_t) * 1000.0

            try:
                self._process_frame_pipeline(frame, ts, seq, queue_delay_ms=queue_delay_ms)
            except Exception as e:
                self._log(f"[WARN] analysis_loop: {type(e).__name__}: {e}")
                self._log(traceback.format_exc())

    def _process_frame_pipeline(self, frame: np.ndarray, ts: float, seq: int, queue_delay_ms: float = 0.0) -> None:
        if frame is None or getattr(frame, "size", 0) == 0:
            return

        self._frame_processing = True
        t_start = time.perf_counter()

        try:
            self.after(0, lambda: self.detector_stage_var.set("Detector: analisando visão / OCR"))
        except Exception:
            pass

        try:
            t0 = time.perf_counter()
            tsec = self.detector.elapsed_seconds()

            frame_preview = frame
            # OTIMIZAÇÃO: Se o frame já vem em 960x540 do StreamAnalyzer, evitamos resize pesado
            H, W = frame.shape[:2]
            if W == 960 and H == 540:
                frame_960 = frame
            else:
                frame_960 = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)

            # OTIMIZAÇÃO: frame_854 só se realmente necessário. 
            # Se a precisão é baixa, usamos o 960 que já temos (ganho marginal de CPU no classify vs custo do resize)
            frame_fast = frame_960 
            
            frame_main = frame_960

            self.detector.ingest_frame(
                frame_main=frame_main,
                t_seconds=tsec,
                frame_fast=frame_fast,
            )

            t1 = time.perf_counter()
            detector_ms = (t1 - t0) * 1000.0
            self.runtime.frames_seen += 1

            try:
                self.after(0, lambda: self.detector_stage_var.set("Detector: extraindo metadados HUD"))
            except Exception:
                pass

            # Throttle metadados HUD para economizar CPU
            now_meta = time.time()
            if (now_meta - getattr(self, "_last_meta_update_ts", 0.0)) >= 3.0:
                self._last_meta_update_ts = now_meta
                self._update_runtime_match_from_frame(frame_main)
            t1 = time.perf_counter()
            hud_ms = (t1 - t0) * 1000.0

            now_loop = time.time()
            fps_loop = 0.0
            if self._last_frame_loop_ts > 0:
                dt = now_loop - self._last_frame_loop_ts
                if dt > 0:
                    fps_loop = min(60.0, 1.0 / dt)
            self._last_frame_loop_ts = now_loop

            try:
                self.after(0, lambda: self.detector_stage_var.set("Detector: montando snapshot debug"))
            except Exception:
                pass

            t0 = time.perf_counter()
            
            # Update status
            total_ms = (time.perf_counter() - t_start) * 1000.0
            
            # Log de diagnóstico periódico (a cada 30 frames ~ 10s em 3fps)
            if self.runtime.frames_seen % 30 == 0:
                self._log(f"[DIAG] Processamento: total={total_ms:.1f}ms | fila={queue_delay_ms:.1f}ms | detector={detector_ms:.1f}ms")
            
            self._update_debug_snapshot("ram_frame", frame_preview, total_ms, fps_loop)
            t1 = time.perf_counter()
            snapshot_ms = (t1 - t0) * 1000.0

            total_ms = (time.perf_counter() - t_start) * 1000.0
            self.runtime.detector_latency_ms = total_ms
            self.runtime.detector_fps = fps_loop
            self._last_processed_seq = seq
            self._pipeline_stats["processed"] += 1
            self._last_pipeline_processed_t = time.time()

            try:
                if hasattr(self, "perf") and self.perf is not None:
                    self.perf.log({
                        "frame": int(self.runtime.frames_seen),
                        "detector_ms": round(detector_ms, 2),
                        "hud_ms": round(hud_ms, 2),
                        "snapshot_ms": round(snapshot_ms, 2),
                        "total_ms": round(total_ms, 2),
                        "fps_loop": round(fps_loop, 2),
                        "ts": round(float(ts or 0.0), 3),
                        "queue_dropped": int(self._pipeline_stats.get("dropped", 0)),
                    })
            except Exception as e:
                self._log(f"[WARN] perf log: {e}")

            try:
                self.after(
                    0,
                    lambda total_ms=total_ms, detector_ms=detector_ms, hud_ms=hud_ms, snapshot_ms=snapshot_ms: (
                        self.detector_stage_var.set(
                            f"Detector: pronto | total={total_ms:.1f} ms | "
                            f"detector={detector_ms:.1f} | hud={hud_ms:.1f} | snapshot={snapshot_ms:.1f} | "
                            f"drop={int(self._pipeline_stats.get('dropped', 0))}"
                        )
                    )
                )
            except Exception:
                pass

            try:
                # 🔥 SINCRONIZAÇÃO DE RELATÓRIO PÓS-IA (Solicitado pelo usuário)
                # Verifica se houve uma nova análise do Gemini e gera relatório parcial imediato.
                st = getattr(self.detector, "_state", None)
                if st is not None:
                    cloud_t = float(getattr(st, "last_cloud_analysis_t", 0.0))
                    if cloud_t > self._last_report_cloud_t:
                        self._last_report_cloud_t = cloud_t
                        self._log(f"[IA-REPORT] Novo resultado Gemini detectado ({cloud_t}). Atualizando JSON/PDF...")
                        # Dispara em uma thread separada para não travar o pipeline principal
                        threading.Thread(target=self._write_partial_report, daemon=True).start()
            except Exception as e:
                self._log(f"[WARN] IA-REPORT trigger: {e}")

            try:
                self.after(0, self._update_preview_widget)
            except Exception:
                pass

        finally:
            self._frame_processing = False

    def _start_event(self, ev: Dict[str, Any], manual_url_override: Optional[str]) -> None:
        if self.runtime.running or self.runtime.preparing:
            self._log("[UI] Já existe monitoramento em andamento. Pare antes.")
            return

        event_id = _safe_slug(ev.get("id") or ev.get("title") or "event")
        raw_url = (manual_url_override or ev.get("url") or "").strip()

        if not raw_url:
            self._log("[ERRO] Evento sem URL.")
            return

        watch_url = normalize_watch_url_to_embed(raw_url)
        fallback_title = (ev.get("title") or event_id).strip()

        meta = {}
        try:
            meta = get_youtube_metadata(raw_url) or {}
        except Exception as e:
            self._log(f"[WARN] metadata: {e}")
            meta = {}

        title = meta.get("title") or fallback_title or "—"
        match_display = meta.get("match_display") or "—"
        competition = meta.get("competition") or "—"
        team_a = meta.get("team_a") or "—"
        team_b = meta.get("team_b") or "—"

        self.runtime = MonitorRuntime(
            running=False,
            preparing=True,
            event_id=event_id,
            event_title=title,
            event_url=watch_url,
            started_at=time.time(),
            last_partial_report_t=time.time(),
            partial_report_every_s=int(self.partial_report_var.get() if hasattr(self, "partial_report_var") else 600),
            current_match_display=match_display,
            current_competition=competition,
            current_team_a=team_a,
            current_team_b=team_b,
        )
        self.debug_snapshot = DebugSnapshot()

        try:
            self.match_var.set(f"Partida: {self.runtime.current_match_display}")
            self.comp_var.set(f"Competição: {self.runtime.current_competition}")
        except Exception:
            pass

        self._set_status("preparing", f"Preparando: {title}")

        paths = _event_paths(event_id)

        try:
            self.detector.start_session(event_id)
            self.detector.ingest_transcript("monitoramento iniciado", t_seconds=0.0, source="system")
        except Exception as e:
            self._log(f"[WARN] detector start_session: {e}")

        def worker() -> None:
            try:
                self._log(f"[URL] raw={raw_url}")
                self._log(f"[URL] embed={watch_url}")

                self._log("[OBS] Garantindo OBS aberto...")
                self.obs.connect(auto_start=True)
                self._log("[OBS] OK conectado.")

                self._log("[OBS] Preparando cena + URL...")
                self.obs.prepare_monitoring(
                    watch_url=watch_url,
                    monitor_scene=OBS_SCENE_MONITOR,
                    browser_source=OBS_BROWSER_SOURCE,
                )
                self._log("[OBS] OK cena no ar.")

                # Força Fullscreen no Player (Browser Source)
                try:
                    time.sleep(1.0)
                    self.obs.force_browser_fullscreen(OBS_BROWSER_SOURCE)
                    self.obs.send_browser_hotkey(OBS_BROWSER_SOURCE, "OBS_KEY_F")
                    self._log("[OBS] Comandos de Fullscreen injetados.")
                except Exception as e:
                    self._log(f"[WARN] Erro ao injetar fullscreen: {e}")

             
                time.sleep(2.5)

                self._log("[CAP] Iniciando leitura RAM do SRT...")
                self._stop_flag.clear()

                ok = self._start_ingest_thread(
                    event_id,
                    paths["frames"],
                    paths["audio"],
                    paths["debug_templates"],
                    paths["debug_snapshots"],
                )
                if not ok:
                    raise RuntimeError("Falha ao iniciar StreamAnalyzer")

                self.runtime.preparing = False
                self.runtime.running = True
                self.after(0, lambda: self._set_status("running", f"Monitorando: {title}"))
                self._log(f"[PIPELINE] RUNNING | event_id={event_id}")

            except Exception as e:
                tb = traceback.format_exc()
                err = f"{type(e).__name__}: {e}"
                self.runtime.preparing = False
                self.runtime.running = False
                self.after(0, lambda err=err: self._set_status("stopped", f"Erro: {err}"))
                self._log("[TRACE]\n" + tb)

                try:
                    if self.stream is not None:
                        self.stream.stop()
                except Exception:
                    pass

                try:
                    self._stop_analysis_worker()
                except Exception:
                    pass

        self._worker_thread = threading.Thread(target=worker, daemon=True, name="start_event_worker")
        self._worker_thread.start()

    def _update_runtime_match_from_frame(self, frame_bgr: Any) -> None:
        now = time.time()
        if (now - float(getattr(self, "_last_meta_update_t", 0.0))) < 2.5:
            return

        self._last_meta_update_t = now

        try:
            vision = getattr(self.detector, "vision", None)
            if vision is None:
                return

            team_a = None
            team_b = None
            competition = None

            # OTIMIZAÇÃO: Pular OCR pesado de nomes/competição se a IA estiver no comando
            if getattr(vision, "cloud_sovereignty_mode", False):
                # Se estivermos em modo Cloud, a IA cuidará dos metadados da partida.
                # Não queremos centenas de milissegundos de Tesseract/Paddle bloqueando o pipeline.
                return

            try:
                team_a, team_b = vision.read_team_names(frame_bgr)
            except Exception:
                team_a, team_b = None, None

            try:
                competition = vision.read_competition(frame_bgr)
            except Exception:
                competition = None

            team_a = _clean_hud_text(team_a)
            team_b = _clean_hud_text(team_b)
            competition = _clean_hud_text(competition)

            if self.runtime.current_team_a == "—" and team_a != "—":
                self.runtime.current_team_a = team_a

            if self.runtime.current_team_b == "—" and team_b != "—":
                self.runtime.current_team_b = team_b

            if (
                self.runtime.current_match_display == "—"
                and self.runtime.current_team_a != "—"
                and self.runtime.current_team_b != "—"
            ):
                self.runtime.current_match_display = f"{self.runtime.current_team_a} x {self.runtime.current_team_b}"

            if self.runtime.current_competition == "—" and competition != "—":
                self.runtime.current_competition = competition

        except Exception as e:
            self._log(f"[WARN] HUD meta frame: {e}")

    def _extract_latest_status_details(self) -> Dict[str, Any]:
        try:
            tl = self.detector.get_timeline()
            for it in reversed(tl):
                if str(it.get("type") or "").lower() == "status":
                    return dict(it.get("details", {}) or {})
        except Exception:
            pass
        return {}

    def _guess_debug_rois(
        self,
        frame_bgr: np.ndarray,
        visual_info: Dict[str, Any],
    ) -> Dict[str, Tuple[int, int, int, int]]:
        rois: Dict[str, Tuple[int, int, int, int]] = {}
        vision = getattr(self.detector, "vision", None)

        labels = [
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
        ]

        if vision is not None:
            for key in labels:
                try:
                    rect = vision.get_roi_pixels(frame_bgr, key)
                    if rect:
                        x, y, w, h = rect
                        rois[key] = (x, y, x + w, y + h)
                except Exception:
                    pass

            try:
                saved = dict(vision.get_last_debug_rois() or {})
                for key in labels:
                    rect = saved.get(f"{key}_roi")
                    if rect and key not in rois:
                        rois[key] = tuple(map(int, rect))
            except Exception:
                pass

        for key in [f"{name}_roi" for name in labels]:
            rect = _normalize_rect(visual_info.get(key), frame_bgr.shape)
            if rect is not None:
                rois[key.replace("_roi", "")] = rect

        return rois

    def _build_annotated_frame(
        self,
        frame_bgr: np.ndarray,
        status_details: Dict[str, Any],
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        visual_info = dict(status_details.get("visual_info", {}) or {})
        rois_rect = self._guess_debug_rois(frame_bgr, visual_info)

        out = frame_bgr.copy()

        _draw_rect(out, rois_rect.get("score"), "score", (0, 255, 0))
        _draw_rect(out, rois_rect.get("clock"), "clock", (255, 255, 0))
        _draw_rect(out, rois_rect.get("phase"), "phase", (255, 191, 0))
        _draw_rect(out, rois_rect.get("pre_jogo"), "pre_jogo", (138, 43, 226))
        _draw_rect(out, rois_rect.get("jogo"), "jogo", (0, 255, 170))
        _draw_rect(out, rois_rect.get("intervalo"), "intervalo", (255, 102, 204))
        _draw_rect(out, rois_rect.get("replay"), "replay", (255, 0, 0))
        _draw_rect(out, rois_rect.get("fim_jogo"), "fim_jogo", (255, 0, 255))
        _draw_rect(out, rois_rect.get("inicio_jogo"), "inicio_jogo", (0, 165, 255))
        _draw_rect(out, rois_rect.get("banner"), "banner", (0, 165, 255))

        lines = [
            f"state={status_details.get('visual_state') or '—'}",
            f"phase={visual_info.get('match_phase_text', '—')}",
            f"clock={status_details.get('clock') or visual_info.get('game_clock_detected') or '—'}",
            f"countdown={visual_info.get('countdown_detected') or '—'}",
            f"score={status_details.get('score') or visual_info.get('score_detected') or '—'}",
            f"conf={_fmt_conf(visual_info.get('visual_confidence', visual_info.get('score', 0.0)))}",
        ]

        y = 26
        for line in lines:
            cv2.putText(out, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (20, 20, 20), 4, cv2.LINE_AA)
            cv2.putText(out, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
            y += 24

        roi_imgs = {
            "score": _safe_crop(frame_bgr, rois_rect.get("score")),
            "clock": _safe_crop(frame_bgr, rois_rect.get("clock")),
            "phase": _safe_crop(frame_bgr, rois_rect.get("phase")),
            "pre_jogo": _safe_crop(frame_bgr, rois_rect.get("pre_jogo")),
            "jogo": _safe_crop(frame_bgr, rois_rect.get("jogo")),
            "intervalo": _safe_crop(frame_bgr, rois_rect.get("intervalo")),
            "replay": _safe_crop(frame_bgr, rois_rect.get("replay")),
            "fim_jogo": _safe_crop(frame_bgr, rois_rect.get("fim_jogo")),
            "inicio_jogo": _safe_crop(frame_bgr, rois_rect.get("inicio_jogo")),
            "banner": _safe_crop(frame_bgr, rois_rect.get("banner")),
        }
        return out, roi_imgs

    def _update_debug_snapshot(self, frame_path: str, frame_bgr: np.ndarray, elapsed_ms: float, fps_loop: float) -> None:
        try:
            status_details = self._extract_latest_status_details()
            vision = getattr(self.detector, "vision", None)

            visual_info: Dict[str, Any] = {}
            if vision is not None:
                try:
                    visual_info = dict(vision.get_last_debug_info() or {})
                except Exception:
                    visual_info = {}

            if not visual_info:
                visual_info = dict(status_details.get("visual_info", {}) or {})

            annotated, rois = self._build_annotated_frame(frame_bgr, status_details)

            teams_text = self.runtime.current_match_display or "—"
            comp_text = self.runtime.current_competition or "—"

            accepted_clock = str(status_details.get("clock") or visual_info.get("game_clock_detected") or "—")
            accepted_score = str(status_details.get("score") or visual_info.get("score_detected") or "—")
            raw_clock = str(visual_info.get("game_clock_raw") or visual_info.get("clock_raw") or accepted_clock or "—")
            raw_score = str(visual_info.get("score_raw") or accepted_score or "—")

            seek_active = False
            try:
                for it in reversed(self.detector.get_timeline()):
                    typ = str(it.get("type") or "").lower()
                    lbl = str(it.get("label") or "").upper()
                    if typ == "context" and "SEEK" in lbl:
                        seek_active = True
                        break
                    if typ == "status":
                        break
            except Exception:
                pass

            self.debug_snapshot = DebugSnapshot(
                frame_path=frame_path,
                frame_bgr=frame_bgr.copy(),
                annotated_bgr=annotated,
                rois=rois,
                visual_info=visual_info,
                last_status_details=status_details,
                last_update_ts=time.time(),
                detector_latency_ms=elapsed_ms,
                fps_loop=fps_loop,
                seek_active=seek_active,
                raw_clock=raw_clock,
                accepted_clock=accepted_clock,
                raw_score=raw_score,
                accepted_score=accepted_score,
                countdown=str(visual_info.get("countdown_detected") or "—"),
                visual_state=str(status_details.get("visual_state") or "—"),
                match_phase_text=str(visual_info.get("match_phase_text") or "—"),
                visual_confidence=float(visual_info.get("visual_confidence", visual_info.get("score", 0.0)) or 0.0),
                banner_summary=str(
                    visual_info.get("banner_summary")
                    or status_details.get("context_summary")
                    or status_details.get("banner_summary")
                    or "—"
                ),
                teams_text=teams_text,
                competition_text=comp_text,
                replay_text=str(visual_info.get("replay_text") or "—"),
                fim_jogo_text=str(visual_info.get("fim_jogo_text") or "—"),
                inicio_jogo_text=str(visual_info.get("inicio_jogo_text") or "—"),
            )

            self.runtime.detector_latency_ms = elapsed_ms
            self.runtime.detector_fps = fps_loop
            self.runtime.last_visual_confidence = self.debug_snapshot.visual_confidence
            self.runtime.last_seek_state = "ativo" if seek_active else "—"

        except Exception as e:
            self._log(f"[WARN] debug_snapshot: {e}")

    def _start_ingest_thread(
        self,
        event_id: str,
        frames_dir: str,
        audio_dir: str,
        debug_templates_dir: str,
        debug_snapshots_dir: str,
    ) -> bool:
        def on_frame(frame: np.ndarray, ts: float) -> None:
            try:
                if frame is None or getattr(frame, "size", 0) == 0:
                    return

                now_frame_ts = time.time()

                with self._preview_lock:
                    self._latest_raw_frame = frame.copy()
                    self._latest_raw_frame_ts = now_frame_ts

                self._enqueue_analysis_frame(frame, ts)

                # Throttle de updates de UI durante a ingestão (max 5 FPS para status/preview)
                if (now_frame_ts - getattr(self, "_last_ui_ingest_update_t", 0.0)) > 0.2:
                    self._last_ui_ingest_update_t = now_frame_ts
                    try:
                        self.after(0, self._update_preview_widget)
                        self.after(0, lambda: self.detector_stage_var.set("Detector: frame enfileirado"))
                    except Exception:
                        pass

            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                self._log(f"[WARN] frame callback: {err}")

        def on_ffmpeg_stderr(msg: str) -> None:
            try:
                self.after(0, lambda m=msg: self._log(f"[FFMPEG] {m}"))
            except Exception:
                pass

        try:
            from modules.stream_analyzer import StreamAnalyzer

            self._start_analysis_worker()

            # 🔥 garante OBS + virtual cam ANTES
            self.obs.ensure_virtual_camera_active(OBS_SCENE_MONITOR)

            # pequena espera pra estabilizar
            time.sleep(1.5)

            # 🔥 cria stream via câmera virtual
            # 🔥 captura em 960x540 (Resolução nativa de saída para o detector)
            # Isso evita que o Python tenha que redimensionar frames 1080p -> 960p 
            # economizando dramaticamente CPU e largura de banda de memória.
            self.stream = StreamAnalyzer(
                srt_url="camera://5",
                width=960,
                height=540,
                sample_fps=int(self.sample_fps_var.get() or FRAME_SAMPLE_FPS),
                force_caller_if_listener=True,
                loglevel="warning",
                max_queue_size=2,
                stderr_callback=on_ffmpeg_stderr,
                source_mode="virtual_camera",
                camera_index=5,
                camera_backend="CAP_DSHOW",
            )

            # 🔥 inicia ingestão
            self.stream.start(on_frame)
            self._log("[STREAM] ingestão via OBS VirtualCam iniciada")         
            return True

        except Exception as e:
            self._log(f"[ERRO] iniciar stream: {e}")
            self._stop_analysis_worker()
            return False

    def _save_debug_snapshot(self) -> None:
        if not self.runtime.event_id:
            self._log("[UI] Snapshot indisponível sem evento ativo.")
            return

        snap = self.debug_snapshot
        if snap.annotated_bgr is None:
            self._log("[UI] Snapshot indisponível: nenhum frame processado ainda.")
            return

        try:
            paths = _event_paths(self.runtime.event_id)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            img_path = os.path.join(paths["debug_snapshots"], f"debug_{ts}.jpg")
            json_path = os.path.join(paths["debug_snapshots"], f"debug_{ts}.json")

            cv2.imwrite(img_path, snap.annotated_bgr)

            payload = {
                "event_id": self.runtime.event_id,
                "event_title": self.runtime.event_title,
                "frame_path": snap.frame_path,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "visual_info": snap.visual_info,
                "status_details": snap.last_status_details,
                "runtime": {
                    "phase": self.runtime.last_phase,
                    "context": self.runtime.last_context,
                    "clock": self.runtime.last_clock,
                    "score": self.runtime.last_score,
                    "event": self.runtime.last_event,
                    "match": self.runtime.current_match_display,
                    "competition": self.runtime.current_competition,
                    "visual_confidence": self.runtime.last_visual_confidence,
                    "detector_latency_ms": self.runtime.detector_latency_ms,
                    "detector_fps": self.runtime.detector_fps,
                },
            }

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            self._log(f"[DEBUG] Snapshot salvo: {os.path.basename(img_path)}")

        except Exception as e:
            self._log(f"[ERRO] snapshot debug: {e}")

    def _write_partial_report(self) -> None:
        if not (self.runtime.running and self.runtime.event_id):
            return

        event_id = self.runtime.event_id
        title = self.runtime.event_title or event_id
        paths = _event_paths(event_id)

        event_meta = {
            "id": event_id,
            "title": title,
            "url": self.runtime.event_url,
            "channel": self.channel_var.get().strip() if hasattr(self, "channel_var") else "",
            "scheduled_start": None,
            "status": "running_partial",
            "competition": self.runtime.current_competition,
            "match_display": self.runtime.current_match_display,
            "team_a": self.runtime.current_team_a,
            "team_b": self.runtime.current_team_b,
        }

        payload = self.reporter.build_report_payload(
            event_meta=event_meta,
            timeline=self.detector.get_timeline(),
            notes={
                "input": "SRT (single-client)",
                "srt_input_url": SRT_INPUT_URL,
                "frames_dir": paths["frames"],
                "debug_templates_dir": paths["debug_templates"],
                "debug_snapshots_dir": paths["debug_snapshots"],
                "audio_dir": paths["audio"],
                "generated_from": "Monitor_Esportes GUI V4 Debug",
                "report_kind": "partial",
                "generated_at_session_seconds": round(self.detector.elapsed_seconds(), 1),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "current_phase": self.runtime.last_phase,
                "current_context": self.runtime.last_context,
                "current_context_summary": self.runtime.last_context_summary,
                "current_clock": self.runtime.last_clock or "—",
                "current_score": self.runtime.last_score or "—",
                "current_match_display": self.runtime.current_match_display,
                "current_competition": self.runtime.current_competition,
                "last_event": self.runtime.last_event,
                "visual_confidence": self.runtime.last_visual_confidence,
                "detector_latency_ms": self.runtime.detector_latency_ms,
                "detector_fps": self.runtime.detector_fps,
            },
        )

        base_name = f"parcial_{event_id}_latest"
        out_json = os.path.join(paths["reports"], base_name + ".json")
        out_pdf = os.path.join(paths["reports"], base_name + ".pdf")

        try:
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"[ERRO] salvar parcial json: {e}")

        try:
            gen_paths = self.reporter.write_report(payload, base_name=base_name)
            try:
                if os.path.isfile(gen_paths.json_path):
                    shutil.copy2(gen_paths.json_path, out_json)
                if os.path.isfile(gen_paths.pdf_path):
                    shutil.copy2(gen_paths.pdf_path, out_pdf)
            except Exception:
                pass
            self._log(f"[RELATORIO] parcial gerado: {os.path.basename(out_pdf)}")
        except Exception as e:
            self._log(f"[ERRO] gerar parcial pdf: {e}")

    def _stop_monitoring(self) -> None:
        if not (self.runtime.running or self.runtime.preparing):
            self._log("[UI] Nada para parar.")
            return

        event_id = self.runtime.event_id or "event"
        title = self.runtime.event_title or event_id
        self._log(f"[PIPELINE] STOP solicitado | event_id={event_id}")

        self._stop_flag.set()

        try:
            if hasattr(self, "stream") and self.stream is not None:
                self.stream.stop()
        except Exception:
            pass

        try:
            self._stop_analysis_worker()
        except Exception:
            pass

        try:
            self.obs.stop_streaming()
        except Exception:
            pass

        try:
            self.detector.ingest_transcript(
                "monitoramento encerrado",
                t_seconds=self.detector.elapsed_seconds(),
                source="system",
            )
        except Exception:
            pass

        try:
            self.detector.stop_session()
        except Exception:
            pass

        paths = _event_paths(event_id)
        event_meta = {
            "id": event_id,
            "title": title,
            "url": self.runtime.event_url,
            "channel": self.channel_var.get().strip() if hasattr(self, "channel_var") else "",
            "scheduled_start": None,
            "status": "stopped",
            "competition": self.runtime.current_competition,
            "match_display": self.runtime.current_match_display,
            "team_a": self.runtime.current_team_a,
            "team_b": self.runtime.current_team_b,
        }

        payload = self.reporter.build_report_payload(
            event_meta=event_meta,
            timeline=self.detector.get_timeline(),
            notes={
                "input": "SRT (single-client)",
                "srt_input_url": SRT_INPUT_URL,
                "frames_dir": paths["frames"],
                "audio_dir": paths["audio"],
                "debug_snapshots_dir": paths["debug_snapshots"],
                "generated_from": "Monitor_Esportes GUI V4 Debug",
                "ended_at_utc": datetime.now(timezone.utc).isoformat(),
                "current_phase": self.runtime.last_phase,
                "current_context": self.runtime.last_context,
                "current_context_summary": self.runtime.last_context_summary,
                "current_clock": self.runtime.last_clock or "—",
                "current_score": self.runtime.last_score or "—",
                "current_match_display": self.runtime.current_match_display,
                "current_competition": self.runtime.current_competition,
                "last_event": self.runtime.last_event,
                "visual_confidence": self.runtime.last_visual_confidence,
                "detector_latency_ms": self.runtime.detector_latency_ms,
                "detector_fps": self.runtime.detector_fps,
            },
        )

        base_name = f"relatorio_{event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        out_json = os.path.join(paths["reports"], base_name + ".json")
        out_pdf = os.path.join(paths["reports"], base_name + ".pdf")

        try:
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"[ERRO] salvar json: {e}")

        try:
            gen_paths = self.reporter.write_report(payload, base_name=base_name)
            try:
                if os.path.isfile(gen_paths.json_path):
                    shutil.copy2(gen_paths.json_path, out_json)
                if os.path.isfile(gen_paths.pdf_path):
                    shutil.copy2(gen_paths.pdf_path, out_pdf)
            except Exception:
                pass
        except Exception as e:
            self._log(f"[ERRO] gerar pdf: {e}")

        self.runtime.running = False
        self.runtime.preparing = False
        self.runtime.event_id = None
        self._set_status("stopped", "Parado")
        self._log(f"[OK] Relatório: {paths['reports']}")

    def _tick_autopilot(self) -> None:
        try:
            if not (self.auto_prepare_var.get() or self.auto_start_var.get()):
                self.after(1000, self._tick_autopilot)
                return

            if self.runtime.running or self.runtime.preparing:
                self.after(1000, self._tick_autopilot)
                return

            if not self._events:
                self.after(1000, self._tick_autopilot)
                return

            prepare_min = int(self.prepare_min_var.get() or PREPARE_MINUTES_BEFORE)

            if self.auto_start_var.get():
                for ev in self._events:
                    if (ev.get("status") or "").lower() == "live":
                        self._log("[AUTO] Detectou LIVE → iniciando monitoramento.")
                        self._start_event(ev, manual_url_override=None)
                        self.after(1000, self._tick_autopilot)
                        return

            if self.auto_prepare_var.get():
                now = _now()
                for ev in self._events:
                    if (ev.get("status") or "").lower() != "upcoming":
                        continue

                    dt = _parse_dt(ev.get("scheduled_start"))
                    if not dt:
                        continue

                    if now <= dt and (dt - now) <= timedelta(minutes=prepare_min):
                        self._log(f"[AUTO] Faltando {_human_age(dt)} → iniciando monitoramento.")
                        self._start_event(ev, manual_url_override=None)
                        self.after(1000, self._tick_autopilot)
                        return

        except Exception as e:
            self._log(f"[WARN] autopilot: {e}")

        self.after(1000, self._tick_autopilot)