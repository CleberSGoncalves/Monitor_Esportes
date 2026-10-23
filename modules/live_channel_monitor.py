# modules/live_channel_monitor.py
"""
Monitor de Canais Live (YouTube) — narrações de estúdio.

- Cadastro de canais.
- Varredura periódica dos eventos futuros (upcoming) e ao vivo de cada canal.
- O usuário marca quais eventos analisar.
- Acompanha upcoming → live → encerrado.
- Ao encerrar: transcreve a narração completa (legendas do YouTube → fallback áudio + Gemini).
- Gera a cronologia automaticamente (e sob demanda pelo botão), cria PDF e opcionalmente envia e-mail
  com o PDF + o .txt da narração. NÃO publica no SharePoint.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

SCAN_INTERVAL_S = 600          # varredura de canais
CHECK_UPCOMING_S = 300         # checagem de status dos eventos selecionados
CHECK_LIVE_S = 120
CAPTION_RETRY_S = 900          # nova tentativa de legendas
AUDIO_FALLBACK_AFTER_S = 2700  # 45 min após o fim sem legendas → áudio + Gemini
AUDIO_FORCE_AFTER_S = 4 * 3600
MAX_AUDIO_ATTEMPTS = 3
TOP_ENTRIES_PER_CHANNEL = 15
KEEP_ENDED_UNSELECTED_S = 2 * 86400

PIPELINE_LABELS = {
    "waiting": ("⏳ Aguardando início", "#FFD700"),
    "live": ("🔴 AO VIVO — acompanhando", "#FF4C4C"),
    "ended": ("⌛ Encerrada — aguardando transcrição", "#FFA500"),
    "transcribing": ("🎙️ Transcrevendo narração...", "#00BFFF"),
    "transcribed": ("✅ Narração pronta", "#00FF7F"),
    "generating": ("🧠 Gerando cronologia...", "#00BFFF"),
    "done": ("📄 Relatório pronto", "#00FF7F"),
    "failed": ("❌ Falhou", "#FF6B6B"),
}


def _data_dir() -> str:
    base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Monitor_Esportes", "live_channels")
    os.makedirs(base, exist_ok=True)
    return base


def _safe(s: str, n: int = 60) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:n] or "evento"


def normalize_channel_url(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if s.startswith("@"):
        s = f"https://www.youtube.com/{s}"
    elif not s.startswith("http"):
        if re.match(r"^UC[\w-]{20,}$", s):
            s = f"https://www.youtube.com/channel/{s}"
        else:
            s = f"https://www.youtube.com/@{s.lstrip('@')}"
    s = re.split(r"/(streams|videos|live|featured|shorts|search)(\b|/|\?)", s)[0].rstrip("/")
    return s


def _ydl_flat(url: str, n: int) -> Dict[str, Any]:
    import yt_dlp
    with yt_dlp.YoutubeDL({"extract_flat": True, "playlistend": n, "quiet": True, "no_warnings": True,
                           "ignoreerrors": True, "skip_download": True}) as y:
        return y.extract_info(url, download=False) or {}


def video_info(video_id: str) -> Dict[str, Any]:
    """Status rápido de um vídeo (sem baixar formatos)."""
    import yt_dlp
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True,
                               "ignore_no_formats_error": True}) as y:
            d = y.extract_info(url, download=False, process=False) or {}
        return {
            "live_status": (d.get("live_status") or "").lower(),
            "release_timestamp": d.get("release_timestamp"),
            "timestamp": d.get("timestamp"),
            "duration": d.get("duration"),
            "title": d.get("title"),
            "channel": d.get("channel") or d.get("uploader"),
            "channel_url": d.get("channel_url") or d.get("uploader_url"),
            "ok": True,
        }
    except Exception as ex:  # noqa: BLE001
        msg = str(ex).lower()
        if "will begin" in msg or "premieres" in msg or "upcoming" in msg:
            return {"live_status": "is_upcoming", "ok": True}
        return {"ok": False, "error": str(ex)[:200]}


def _status_from_live(ls: str) -> str:
    if ls in ("is_live",):
        return "live"
    if ls in ("is_upcoming",):
        return "upcoming"
    if ls in ("was_live", "post_live"):
        return "ended"
    return "video"


class LiveNarrationService:
    def __init__(self, reporter, config_provider: Callable[[], Dict[str, Any]],
                 log: Optional[Callable[[str], None]] = None, on_change: Optional[Callable[[], None]] = None):
        self.reporter = reporter
        self.config_provider = config_provider
        self._log_cb = log
        self.on_change = on_change
        self.lock = threading.RLock()
        self.state_path = os.path.join(_data_dir(), "state.json")
        self.narr_dir = os.path.join(_data_dir(), "narracoes")
        os.makedirs(self.narr_dir, exist_ok=True)
        self.state: Dict[str, Any] = {"channels": [], "events": {}, "settings": {"auto_email": True}}
        self._load()
        self._job_lock = threading.Lock()   # um job pesado por vez
        self._busy: set = set()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_scan = 0.0
        self.last_scan_at: Optional[str] = None
        self.scanning = False

    # ------------------------------------------------------------------ util
    def log(self, msg: str) -> None:
        line = f"📡 [CANAIS LIVE] {msg}"
        try:
            if self._log_cb:
                self._log_cb(line)
            else:
                print(line, flush=True)
        except Exception:
            pass

    def _changed(self) -> None:
        self._save()
        if self.on_change:
            try:
                self.on_change()
            except Exception:
                pass

    def _load(self) -> None:
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.state.update({k: v for k, v in data.items() if k in ("channels", "events", "settings")})
                # jobs interrompidos por reinício voltam para a fila
                for ev in self.state["events"].values():
                    if ev.get("pipeline") == "transcribing":
                        ev["pipeline"] = "ended"
                        ev["next_attempt"] = 0
                    elif ev.get("pipeline") == "generating":
                        ev["pipeline"] = "transcribed"
        except Exception as ex:  # noqa: BLE001
            print(f"[CANAIS LIVE] Erro ao ler estado: {ex}")

    def _save(self) -> None:
        with self.lock:
            tmp = self.state_path + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, ensure_ascii=False, indent=2)
                os.replace(tmp, self.state_path)
            except Exception as ex:  # noqa: BLE001
                print(f"[CANAIS LIVE] Erro ao salvar estado: {ex}")

    # -------------------------------------------------------------- settings
    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.state.setdefault("settings", {}).get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        with self.lock:
            self.state.setdefault("settings", {})[key] = value
        self._save()

    # -------------------------------------------------------------- channels
    def list_channels(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [dict(c) for c in self.state["channels"]]

    def add_channel(self, raw_url: str, name: str = "") -> Dict[str, Any]:
        url = normalize_channel_url(raw_url)
        if not url:
            raise ValueError("Informe a URL ou o @ do canal.")
        with self.lock:
            for c in self.state["channels"]:
                if c["url"].lower() == url.lower():
                    raise ValueError("Canal já cadastrado.")
        info = _ydl_flat(url + "/streams", 1)
        real_name = info.get("channel") or info.get("uploader") or ""
        if not info:
            raise ValueError("Não consegui acessar esse canal no YouTube. Confira a URL/@.")
        ch = {
            "id": info.get("channel_id") or _safe(url),
            "url": url,
            "name": name.strip() or real_name or url.rsplit("/", 1)[-1],
            "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self.lock:
            self.state["channels"].append(ch)
        self.log(f"Canal cadastrado: {ch['name']} ({url})")
        self._changed()
        threading.Thread(target=self.scan_channels, kwargs={"only": ch["id"]}, daemon=True).start()
        return ch

    def remove_channel(self, channel_id: str) -> None:
        with self.lock:
            self.state["channels"] = [c for c in self.state["channels"] if c["id"] != channel_id]
            for vid in list(self.state["events"].keys()):
                ev = self.state["events"][vid]
                if ev.get("channel_id") == channel_id and not ev.get("selected"):
                    del self.state["events"][vid]
        self._changed()

    # ---------------------------------------------------------------- events
    def list_events(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [dict(e) for e in self.state["events"].values()]

    def get_event(self, vid: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            ev = self.state["events"].get(vid)
            return dict(ev) if ev else None

    def update_event(self, vid: str, **fields) -> None:
        with self.lock:
            ev = self.state["events"].get(vid)
            if ev is None:
                return
            ev.update(fields)
            ev["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._changed()

    def set_selected(self, vid: str, selected: bool) -> None:
        with self.lock:
            ev = self.state["events"].get(vid)
            if not ev:
                return
            ev["selected"] = bool(selected)
            if selected and ev.get("pipeline") in (None, "", "idle"):
                st = ev.get("status")
                ev["pipeline"] = "live" if st == "live" else ("ended" if st == "ended" else "waiting")
                ev["next_attempt"] = 0
                ev["last_check"] = 0
            elif not selected and ev.get("pipeline") in ("waiting", "live", "ended", "failed"):
                ev["pipeline"] = "idle"
        self.log(("✅ Evento selecionado para análise: " if selected else "Evento removido da análise: ") + ev.get("title", vid))
        self._changed()

    def add_video_manually(self, url: str) -> Dict[str, Any]:
        """Permite incluir uma live já encerrada (ou futura) pela URL do vídeo."""
        m = re.search(r"(?:v=|/live/|youtu\.be/|/shorts/|embed/)([A-Za-z0-9_-]{11})", url or "")
        vid = m.group(1) if m else (url.strip() if re.match(r"^[A-Za-z0-9_-]{11}$", (url or "").strip()) else None)
        if not vid:
            raise ValueError("URL de vídeo inválida.")
        info = video_info(vid)
        if not info.get("ok"):
            raise ValueError(f"Não consegui ler o vídeo: {info.get('error')}")
        ev = self._upsert_event(vid, info, channel=None)
        self.set_selected(vid, True)
        return ev

    def _upsert_event(self, vid: str, info: Dict[str, Any], channel: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        status = _status_from_live(info.get("live_status") or "")
        with self.lock:
            ev = self.state["events"].get(vid)
            if ev is None:
                ev = {
                    "video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
                    "selected": False, "pipeline": "idle",
                    "found_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                self.state["events"][vid] = ev
            ev["title"] = info.get("title") or ev.get("title") or vid
            ev["status"] = status
            ev["live_status"] = info.get("live_status") or ev.get("live_status")
            if channel:
                ev["channel_id"], ev["channel_name"], ev["channel_url"] = channel["id"], channel["name"], channel["url"]
            else:
                ev.setdefault("channel_name", info.get("channel") or "YouTube")
                ev.setdefault("channel_url", info.get("channel_url") or "")
            rts = info.get("release_timestamp")
            if status == "upcoming" and rts:
                ev["scheduled_epoch"] = int(rts)
            if status in ("live", "ended") and rts:
                ev["actual_start_epoch"] = int(rts)
            if info.get("duration"):
                ev["duration"] = int(info["duration"])
            return ev

    def scan_channels(self, only: Optional[str] = None) -> int:
        """Varre os canais e atualiza a lista de eventos futuros/ao vivo. Retorna nº de eventos novos."""
        if self.scanning and not only:
            return 0
        self.scanning = True
        new_count = 0
        try:
            chans = [c for c in self.list_channels() if not only or c["id"] == only]
            for ch in chans:
                try:
                    flat = _ydl_flat(ch["url"] + "/streams", TOP_ENTRIES_PER_CHANNEL)
                    ids = [e.get("id") for e in (flat.get("entries") or []) if e and e.get("id")]
                    with self.lock:
                        known = self.state["events"]
                        # Só consulta detalhes de IDs novos ou ainda não encerrados
                        to_check = [v for v in ids if v not in known or known[v].get("status") in ("upcoming", "live", None)]
                    with cf.ThreadPoolExecutor(max_workers=8) as ex:
                        infos = dict(zip(to_check, ex.map(video_info, to_check)))
                    for vid in to_check:
                        info = infos.get(vid) or {}
                        if not info.get("ok"):
                            continue
                        st = _status_from_live(info.get("live_status") or "")
                        is_new = vid not in self.state["events"]
                        if is_new and st not in ("upcoming", "live"):
                            continue  # só listamos eventos futuros/ao vivo
                        self._upsert_event(vid, info, ch)
                        new_count += 1 if is_new else 0
                except Exception as ex:  # noqa: BLE001
                    self.log(f"⚠️ Erro ao varrer {ch.get('name')}: {str(ex)[:160]}")
            self._prune()
            self.last_scan_at = datetime.now().strftime("%d/%m %H:%M:%S")
            if new_count:
                self.log(f"Varredura concluída: {new_count} novo(s) evento(s) encontrado(s).")
        finally:
            self.scanning = False
            self._changed()
        return new_count

    def _prune(self) -> None:
        now = time.time()
        with self.lock:
            for vid in list(self.state["events"].keys()):
                ev = self.state["events"][vid]
                if ev.get("selected"):
                    continue
                if ev.get("status") in ("ended", "video"):
                    ref = ev.get("scheduled_epoch") or ev.get("actual_start_epoch") or 0
                    if not ref or now - ref > KEEP_ENDED_UNSELECTED_S:
                        del self.state["events"][vid]

    # ------------------------------------------------------------ main loop
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="LiveNarrationService", daemon=True)
        self._thread.start()
        self.log("Serviço de monitoramento de canais iniciado (varredura a cada 10 min).")

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        time.sleep(8)
        while not self._stop.is_set():
            try:
                if self.state["channels"] and time.time() - self._last_scan >= SCAN_INTERVAL_S:
                    self._last_scan = time.time()
                    self.scan_channels()
                self._tick_selected()
            except Exception as ex:  # noqa: BLE001
                self.log(f"⚠️ Erro no ciclo: {ex}")
            self._stop.wait(30)

    def scan_now_async(self) -> None:
        self._last_scan = time.time()
        threading.Thread(target=self.scan_channels, daemon=True).start()

    def _tick_selected(self) -> None:
        now = time.time()
        for ev in self.list_events():
            if not ev.get("selected"):
                continue
            vid = ev["video_id"]
            pipe = ev.get("pipeline")
            if pipe in ("waiting", "live"):
                interval = CHECK_LIVE_S if pipe == "live" else CHECK_UPCOMING_S
                sched = ev.get("scheduled_epoch") or 0
                if pipe == "waiting" and sched and sched - now > 3600:
                    interval = 1800  # falta mais de 1h: checa a cada 30 min
                if now - (ev.get("last_check") or 0) < interval:
                    continue
                info = video_info(vid)
                if not info.get("ok"):
                    self.update_event(vid, last_check=now)
                    continue
                self._upsert_event(vid, info, None)
                st = _status_from_live(info.get("live_status") or "")
                if st == "live" and pipe != "live":
                    self.log(f"🔴 AO VIVO: {ev.get('title')}")
                    self.update_event(vid, pipeline="live", last_check=now)
                elif st == "ended":
                    self.log(f"🏁 Live encerrada: {ev.get('title')} — iniciando transcrição.")
                    self.update_event(vid, pipeline="ended", ended_detected_at=now, next_attempt=0,
                                      last_check=now, audio_attempts=0)
                else:
                    self.update_event(vid, last_check=now)
            elif pipe == "ended" and now >= (ev.get("next_attempt") or 0) and vid not in self._busy:
                self.run_transcription_async(vid)
            elif pipe == "transcribed" and not ev.get("auto_generated") and vid not in self._busy:
                self.update_event(vid, auto_generated=True)
                self.run_generation_async(vid, meta=None, auto=True)

    # ---------------------------------------------------------- transcrição
    def run_transcription_async(self, vid: str, force_audio: bool = False) -> None:
        if vid in self._busy:
            return
        self._busy.add(vid)
        threading.Thread(target=self._transcribe_job, args=(vid, force_audio), daemon=True).start()

    def _transcribe_job(self, vid: str, force_audio: bool) -> None:
        from modules.narration_transcriber import transcribe_event
        try:
            with self._job_lock:
                ev = self.get_event(vid)
                if not ev:
                    return
                # Garante metadados finais (início/duração) antes de transcrever
                info = video_info(vid)
                if info.get("ok"):
                    self._upsert_event(vid, info, None)
                    ev = self.get_event(vid) or ev
                if not ev.get("actual_start_epoch") and ev.get("scheduled_epoch"):
                    ev["actual_start_epoch"] = ev["scheduled_epoch"]
                cfg = self.config_provider() or {}
                now = time.time()
                ended_at = ev.get("ended_detected_at") or now
                waited = now - ended_at
                vod_ready = (ev.get("live_status") == "was_live")
                allow_audio = force_audio or (vod_ready and waited >= AUDIO_FALLBACK_AFTER_S) or waited >= AUDIO_FORCE_AFTER_S
                self.update_event(vid, pipeline="transcribing", progress="Iniciando...")

                def plog(m: str) -> None:
                    self.log(f"[{ev.get('title', vid)[:40]}] {m}")
                    self.update_event(vid, progress=m)

                fname = f"narracao_{_safe(ev.get('channel_name'), 25)}_{_safe(ev.get('title'), 50)}_{vid}.txt"
                out = os.path.join(self.narr_dir, fname)
                res = transcribe_event(ev, out, api_key=cfg.get("api_key"), model_id=cfg.get("model_id") or "gemini-2.5-flash",
                                       allow_audio=allow_audio, log=plog)
                if res.get("ok"):
                    label = "Legendas do YouTube" if res["source"] == "youtube_captions" else "Áudio transcrito pelo Gemini"
                    self.update_event(vid, pipeline="transcribed", narration_path=res["path"], transcript_source=res["source"],
                                      transcript_source_label=label, narration_lines=res["lines"], error="", progress="",
                                      auto_generated=False)
                    return
                attempts = int(ev.get("audio_attempts") or 0) + (1 if allow_audio else 0)
                if allow_audio and attempts >= MAX_AUDIO_ATTEMPTS:
                    self.update_event(vid, pipeline="failed", error=res.get("error") or "Falha na transcrição", progress="",
                                      audio_attempts=attempts)
                    self.log(f"❌ Transcrição falhou definitivamente: {res.get('error')}")
                else:
                    nxt = now + (1800 if allow_audio else CAPTION_RETRY_S)
                    self.update_event(vid, pipeline="ended", next_attempt=nxt, audio_attempts=attempts,
                                      progress=f"{res.get('error')} Nova tentativa às {datetime.fromtimestamp(nxt).strftime('%H:%M')}.")
        except Exception as ex:  # noqa: BLE001
            self.update_event(vid, pipeline="ended", next_attempt=time.time() + 1800, progress=f"Erro: {ex}")
            self.log(f"⚠️ Erro na transcrição: {traceback.format_exc()[-400:]}")
        finally:
            self._busy.discard(vid)

    # ------------------------------------------------------------ cronologia
    def default_meta(self, ev: Dict[str, Any]) -> Dict[str, str]:
        from modules.narration_chronology import guess_match_from_title
        meta = dict(ev.get("meta") or {})
        g = guess_match_from_title(ev.get("title", ""))
        for k in ("team1", "team2", "competition"):
            meta.setdefault(k, g.get(k, ""))
        if not meta.get("date"):
            ref = ev.get("actual_start_epoch") or ev.get("scheduled_epoch")
            meta["date"] = datetime.fromtimestamp(ref).strftime("%d/%m/%Y") if ref else ""
        return meta

    def run_generation_async(self, vid: str, meta: Optional[Dict[str, str]] = None, auto: bool = False,
                             progress_cb: Optional[Callable[[str], None]] = None,
                             done_cb: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:
        if vid in self._busy:
            return False
        self._busy.add(vid)
        threading.Thread(target=self._generate_job, args=(vid, meta, auto, progress_cb, done_cb), daemon=True).start()
        return True

    def _generate_job(self, vid, meta, auto, progress_cb, done_cb) -> None:
        from modules.narration_chronology import generate_narration_chronology
        out: Dict[str, Any] = {}
        prev_pipe = "transcribed"
        try:
            with self._job_lock:
                ev = self.get_event(vid)
                if not ev or not ev.get("narration_path"):
                    out = {"error": "Narração ainda não disponível."}
                    return
                prev_pipe = ev.get("pipeline") if ev.get("pipeline") in ("transcribed", "done") else "transcribed"
                meta = meta or self.default_meta(ev)
                self.update_event(vid, pipeline="generating", meta=meta, progress="Iniciando...")
                cfg = self.config_provider() or {}

                def plog(m: str) -> None:
                    self.log(f"[{ev.get('title', vid)[:40]}] {m}")
                    self.update_event(vid, progress=m)
                    if progress_cb:
                        try:
                            progress_cb(m)
                        except Exception:
                            pass

                result = generate_narration_chronology(ev, meta, api_key=cfg.get("api_key"),
                                                       model_id=cfg.get("model_id") or "gemini-2.5-flash", log=plog)
                if result.get("error"):
                    self.update_event(vid, pipeline=prev_pipe, error=result["error"], progress="")
                    plog(f"❌ {result['error']}")
                    out = result
                    return
                plog("📄 Gerando PDF do relatório...")
                prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
                pdf = self.reporter.write_expert_report([result], prefs=prefs, sync_sharepoint=False, name_prefix="narracao")
                self.update_event(vid, pipeline="done", pdf_path=pdf, error="", progress="",
                                  generated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                plog(f"✅ Relatório pronto: {os.path.basename(pdf)}")
                out = {"ok": True, "pdf_path": pdf}
                if auto and self.get_setting("auto_email", True):
                    self.send_email(vid)
        except Exception as ex:  # noqa: BLE001
            self.update_event(vid, pipeline=prev_pipe, error=str(ex), progress="")
            self.log(f"⚠️ Erro ao gerar cronologia: {traceback.format_exc()[-400:]}")
            out = {"error": str(ex)}
        finally:
            self._busy.discard(vid)
            if done_cb:
                try:
                    done_cb(out)
                except Exception:
                    pass

    # ---------------------------------------------------------------- email
    def send_email(self, vid: str, recipients: Optional[List[str]] = None) -> bool:
        from modules.email_service import EmailService
        ev = self.get_event(vid)
        if not ev:
            return False
        cfg = self.config_provider() or {}
        recipients = recipients or cfg.get("emails") or []
        if not recipients:
            self.log("⚠️ Nenhum destinatário de e-mail configurado.")
            return False
        if not cfg.get("sender") or not cfg.get("password"):
            self.log("⚠️ Remetente de e-mail não configurado (Config).")
            return False
        attachments = [p for p in (ev.get("narration_path"),) if p and os.path.exists(p)]
        pdf = ev.get("pdf_path") if ev.get("pdf_path") and os.path.exists(ev.get("pdf_path")) else None
        meta = ev.get("meta") or {}
        jogo = f"{meta.get('team1')} x {meta.get('team2')}" if meta.get("team1") else ev.get("title", "")
        body = (
            f"Relatório de narração da live \"{ev.get('title')}\"\n"
            f"Canal: {ev.get('channel_name')}\nVídeo: {ev.get('url')}\n"
            f"Jogo: {jogo}\n\n"
            f"Anexos: {'relatório PDF + ' if pdf else ''}narração completa (.txt).\n"
            "— Monitor de Esportes (Canais Live)"
        )
        try:
            svc = EmailService(cfg.get("smtp_server"), int(cfg.get("smtp_port") or 587), cfg["sender"], cfg["password"])
            ok = svc.send_report(recipients, f"Narração Live — {ev.get('channel_name')} — {jogo}", body, pdf,
                                 extra_attachments=attachments)
            if ok:
                self.update_event(vid, emailed_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                self.log(f"✉️ E-mail enviado para: {', '.join(recipients)}")
            return bool(ok)
        except Exception as ex:  # noqa: BLE001
            self.log(f"⚠️ Falha ao enviar e-mail: {ex}")
            return False
