# modules/scheduler.py
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable

from modules.youtube_events import get_channel_events


def _now() -> datetime:
    return datetime.now()


def _parse_scheduled(ev: Dict[str, Any]) -> Optional[datetime]:
    s = ev.get("scheduled_start")
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def pick_best_event(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for ev in events:
        if ev.get("status") == "live":
            return ev
    upcoming = [e for e in events if e.get("status") == "upcoming" and e.get("scheduled_start")]
    if not upcoming:
        return None
    upcoming.sort(key=lambda e: _parse_scheduled(e) or datetime.max)
    return upcoming[0]


def run_scheduler(
    channel_streams_url: str,
    poll_seconds: int,
    prepare_minutes_before: int,
    open_obs_minutes_before: int,
    auto_monitor_when_live: bool,
    obs_controller,
    obs_scene_monitor: str,
    obs_browser_source: str,
    on_monitoring_start: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_monitoring_stop: Optional[Callable[[Dict[str, Any]], None]] = None,
    stop_grace_polls: int = 4,  # quantos polls sem achar LIVE para encerrar
):
    state = {
        "armed_event_id": None,
        "obs_prepared_for_event_id": None,
        "monitoring_event_id": None,
        "monitoring_event": None,
        "live_missed_polls": 0,
    }

    print("[INFO] Scheduler iniciado.")
    print("[INFO] Canal:", channel_streams_url)

    while True:
        try:
            events = get_channel_events(channel_streams_url, limit=30)
            target = pick_best_event(events)

            # Se está monitorando e NÃO achou live, conta miss
            if state["monitoring_event_id"] is not None:
                if not target or target.get("status") != "live" or target.get("id") != state["monitoring_event_id"]:
                    state["live_missed_polls"] += 1
                else:
                    state["live_missed_polls"] = 0

                if state["live_missed_polls"] >= stop_grace_polls:
                    ev = state["monitoring_event"] or {"id": state["monitoring_event_id"]}
                    print("🛑 LIVE sumiu/terminou. Encerrando monitoramento.")
                    state["monitoring_event_id"] = None
                    state["monitoring_event"] = None
                    state["live_missed_polls"] = 0
                    if on_monitoring_stop:
                        on_monitoring_stop(ev)

            if not target:
                print("[INFO] Nenhum evento encontrado. Rechecando...")
                time.sleep(poll_seconds)
                continue

            ev_id = target.get("id")
            title = target.get("title", "")
            status = target.get("status")
            url = target.get("url")
            sched_dt = _parse_scheduled(target)

            print(f"[INFO] Alvo: {status.upper()} | {title}")

            if status == "live":
                if auto_monitor_when_live and state["monitoring_event_id"] != ev_id:
                    state["monitoring_event_id"] = ev_id
                    state["monitoring_event"] = target
                    state["live_missed_polls"] = 0

                    print(f"🟢 MONITORANDO AGORA: {title}")
                    try:
                        obs_controller.prepare_monitoring(
                            watch_url=url,
                            monitor_scene=obs_scene_monitor,
                            browser_source=obs_browser_source,
                            template_scene=obs_scene_monitor,
                            template_source=obs_browser_source,
                        )
                    except Exception as e:
                        print("[ERRO] OBS prepare_monitoring:", e)

                    if on_monitoring_start:
                        on_monitoring_start(target)

                time.sleep(poll_seconds)
                continue

            if status == "upcoming" and sched_dt:
                now = _now()
                t_prepare = sched_dt - timedelta(minutes=prepare_minutes_before)
                t_open_obs = sched_dt - timedelta(minutes=open_obs_minutes_before)

                if now >= t_prepare and state["armed_event_id"] != ev_id:
                    state["armed_event_id"] = ev_id
                    print(f"[ARMADO] Evento armado: {title} (previsto {sched_dt})")

                if now >= t_open_obs and state["obs_prepared_for_event_id"] != ev_id:
                    state["obs_prepared_for_event_id"] = ev_id
                    print("[INFO] Preparando OBS (carregando URL)...")
                    obs_controller.prepare_monitoring(
                        watch_url=url,
                        monitor_scene=obs_scene_monitor,
                        browser_source=obs_browser_source,
                        template_scene=obs_scene_monitor,
                        template_source=obs_browser_source,
                    )
                    print("[OK] OBS preparado (aguardando entrar LIVE).")

                time.sleep(poll_seconds)
                continue

            time.sleep(poll_seconds)

        except Exception as e:
            print("[ERRO]", e)
            time.sleep(poll_seconds)