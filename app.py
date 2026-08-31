# app.py
from __future__ import annotations

import os
import time
from datetime import datetime

from config.settings import (
    CHANNEL_STREAMS_URL,
    POLL_SECONDS,
    PREPARE_MINUTES_BEFORE,
    OPEN_OBS_MINUTES_BEFORE,
    AUTO_MONITOR_WHEN_LIVE,
    OBS_HOST,
    OBS_PORT,
    OBS_PASSWORD,
    OBS_SCENE_MONITOR,
    OBS_BROWSER_SOURCE,
    SRT_INPUT_URL,
    RTMP_INPUT_URL,  # só pra notes
    FRAMES_DIR,
    AUDIO_DIR,
    REPORTS_DIR,
    FRAME_SAMPLE_FPS,
    AUDIO_SEGMENT_SECONDS,
    OBS_EXE_PATH,
    OBS_ARGS,
    OBS_AUTO_START,
)

from modules.obs_controller import OBSController
from modules.scheduler import run_scheduler
from modules.speech_analyzer import SpeechAnalyzer
from modules.event_detector import EventDetector
from modules.report_generator import ReportGenerator


def _safe_event_id(ev: dict) -> str:
    return (ev.get("id") or ev.get("title") or "event").strip().replace(" ", "_")[:80]


def main() -> None:
    # Pastas
    os.makedirs(FRAMES_DIR, exist_ok=True)
    os.makedirs(AUDIO_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)

    print("[DEBUG] CWD:", os.getcwd())
    print("[DEBUG] FRAMES_DIR:", os.path.abspath(FRAMES_DIR))
    print("[DEBUG] AUDIO_DIR :", os.path.abspath(AUDIO_DIR))
    print("[DEBUG] REPORTS_DIR:", os.path.abspath(REPORTS_DIR))
    print("[DEBUG] SRT_INPUT_URL:", SRT_INPUT_URL)

    # OBS
    obs = OBSController(
        host=OBS_HOST,
        port=OBS_PORT,
        password=OBS_PASSWORD,
        obs_exe_path=OBS_EXE_PATH,
        obs_args=OBS_ARGS,
    )

    # Detector + Relatório
    detector = EventDetector()
    reporter = ReportGenerator(reports_dir=REPORTS_DIR)

    # ✅ ÚNICO capturador: 1 ffmpeg só (áudio + frames) conectado no SRT
    speech = SpeechAnalyzer(
        input_url=SRT_INPUT_URL,         # importante: um só cliente SRT
        audio_dir=AUDIO_DIR,
        frames_dir=FRAMES_DIR,
        segment_seconds=AUDIO_SEGMENT_SECONDS,
        sample_fps=FRAME_SAMPLE_FPS,
        ffmpeg_path="ffmpeg",
        loglevel="info",
        force_caller_if_listener=True,   # se settings estiver mode=listener, ele troca pra caller
        jpg_qv=4,
        scale_width=1280,
        scale_height=720,
    )

    stream_running_event_id: str | None = None
    obs_ready: bool = False

    # ✅ Para gerar relatório no CTRL+C
    last_ev: dict | None = None
    monitoring_active: bool = False

    def ensure_obs_ready() -> None:
        """Garante que o OBS está aberto e o WebSocket conectado."""
        nonlocal obs_ready
        if obs_ready:
            return
        try:
            obs.connect(auto_start=bool(OBS_AUTO_START))
            obs_ready = True
        except Exception as e:
            obs_ready = False
            print("[ERRO] OBS connect:", e)

    def on_start(ev: dict) -> None:
        nonlocal stream_running_event_id, last_ev, monitoring_active

        last_ev = ev
        monitoring_active = True

        event_id = _safe_event_id(ev)
        stream_running_event_id = event_id

        print(f"[PIPELINE] MONITORAMENTO START | event_id={event_id} | {ev.get('title')}")

        # sessão de detecção
        detector.start_session(event_id)
        detector.ingest_transcript("monitoramento iniciado", t_seconds=0.0, source="system")

        # OBS (tenta preparar a cena / injetar URL)
        ensure_obs_ready()
        if obs_ready:
            try:
                obs.prepare_monitoring(
                    watch_url=ev.get("url") or "",
                    monitor_scene=OBS_SCENE_MONITOR,
                    browser_source=OBS_BROWSER_SOURCE,
                )
            except Exception as e:
                print("[ERRO] OBS prepare_monitoring:", e)

        # ✅ inicia CAPTURA ÚNICA (áudio + frames)
        try:
            speech.start(event_id)
        except Exception as e:
            print("[ERRO] SpeechAnalyzer.start:", e)

    def on_stop(ev: dict) -> None:
        nonlocal stream_running_event_id, monitoring_active

        monitoring_active = False

        event_id = stream_running_event_id or _safe_event_id(ev)
        print(f"[PIPELINE] MONITORAMENTO STOP | event_id={event_id}")

        # Para captura (FFmpeg)
        try:
            speech.stop()
        except Exception:
            pass

        # Fecha detector e gera relatório
        try:
            detector.ingest_transcript(
                "monitoramento encerrado",
                t_seconds=max(0.0, detector._elapsed_seconds()),  # ok por enquanto
                source="system",
            )
        except Exception:
            pass

        try:
            detector.stop_session()
        except Exception:
            pass

        event_meta = {
            "id": ev.get("id") or event_id,
            "title": ev.get("title"),
            "url": ev.get("url"),
            "channel": ev.get("channel"),
            "scheduled_start": ev.get("scheduled_start"),
            "status": ev.get("status"),
        }

        payload = reporter.build_report_payload(
            event_meta=event_meta,
            timeline=detector.get_timeline(),
            notes={
                "input": "SRT (single-client)",
                "srt_input_url": SRT_INPUT_URL,
                "rtmp_input_url": RTMP_INPUT_URL,
                "frames_dir": FRAMES_DIR,
                "audio_dir": AUDIO_DIR,
                "principle": "derived_data_only",
                "generated_from": "Monitor_Esportes",
                "ended_at_utc": datetime.utcnow().isoformat() + "Z",
            },
        )

        base_name = f"relatorio_{event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        paths = reporter.write_report(payload, base_name=base_name)

        print("[OK] Relatório gerado:")
        print(" - JSON:", paths.json_path)
        print(" - PDF :", paths.pdf_path)

        stream_running_event_id = None

    try:
        run_scheduler(
            channel_streams_url=CHANNEL_STREAMS_URL,
            poll_seconds=POLL_SECONDS,
            prepare_minutes_before=PREPARE_MINUTES_BEFORE,
            open_obs_minutes_before=OPEN_OBS_MINUTES_BEFORE,
            auto_monitor_when_live=AUTO_MONITOR_WHEN_LIVE,
            obs_controller=obs,
            obs_scene_monitor=OBS_SCENE_MONITOR,
            obs_browser_source=OBS_BROWSER_SOURCE,
            on_monitoring_start=on_start,
            on_monitoring_stop=on_stop,
        )

    except KeyboardInterrupt:
        print("\n[INFO] CTRL+C recebido. Encerrando com flush de relatório...")
        if monitoring_active and (last_ev is not None):
            try:
                on_stop(last_ev)  # ✅ gera JSON/PDF antes de sair
            except Exception as e:
                print("[WARN] Falha ao gerar relatório no shutdown:", e)

    finally:
        # shutdown seguro
        try:
            speech.stop()
        except Exception:
            pass
        try:
            detector.stop_session()
        except Exception:
            pass
        try:
            obs.disconnect()
        except Exception:
            pass
        try:
            time.sleep(0.2)
        except Exception:
            pass


if __name__ == "__main__":
    main()