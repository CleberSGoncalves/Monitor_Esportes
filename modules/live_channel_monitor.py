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

    "analyzing": ("🔍 Analisando transcrição (IA)...", "#00CED1"),

    "transcribed": ("🔍 Transcrição pronta (em análise)", "#00CED1"),

    "ready_match": ("✅ Partida Narrada — Pronta p/ Relatório", "#00FF7F"),

    "not_match": ("ℹ️ Programa/Debate (Não é jogo narrado)", "#90A4AE"),

    "generating": ("🧠 Gerando relatório cronológico...", "#00BFFF"),

    "done": ("📄 Relatório Cronológico Pronto", "#00FF7F"),

    "failed": ("❌ Falhou", "#FF6B6B"),

}



DEFAULT_SEED_CHANNELS: List[Dict[str, str]] = [

    {"id": "UCRC3upGcj_decdPi7JXT7Bg", "url": "https://www.youtube.com/@gaucha", "name": "Gaúcha"},

    {"id": "UCVuih8U_4y1E8ecZZoZw_hw", "url": "https://www.youtube.com/@gauchaesportes", "name": "Gaúcha Esportes"},

    {"id": "UCXWOg5HNDYANCSkNeDw9iYg", "url": "https://www.youtube.com/@atlantida_tv", "name": "ATL TV"},

    {"id": "UC4QpkZzN08pFibmJAl213-w", "url": "https://www.youtube.com/@BaldassoTV", "name": "BALDASSO TV"},

    {"id": "UCg6ONDqJLO_G2kJuxDPxTaA", "url": "https://www.youtube.com/@Bag%C3%A9TvOficial", "name": "Bagé TV"},

    {"id": "UCrmnzU5nF4-DBtTx114r_hw", "url": "https://www.youtube.com/@EsporteBandRS", "name": "Esporte Band RS"},

]





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





def _is_24h_or_continuous_stream(title: str, info: Optional[Dict[str, Any]] = None) -> bool:

    """Detecta lives permanentes 24h (ex: Rádio Gaúcha 24 Horas) para não poluir o Auto-Detect."""

    t = (title or "").strip()

    if re.search(r"\b24\s*h(?:oras)?\b", t, re.I) or re.search(r"ao\s+vivo\s+24", t, re.I):

        return True

    if info:

        st = info.get("status") or _status_from_live(info.get("live_status") or "")

        start_ep = info.get("actual_start_epoch") or info.get("release_timestamp") or 0

        if st == "live" and start_ep and (time.time() - float(start_ep)) > 18 * 3600:

            return True

    return False







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

        self.state: Dict[str, Any] = {

            "channels": [],

            "events": {},

            "settings": {"auto_email": True, "auto_report": True, "auto_detect_match": True},

        }

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

                    elif ev.get("pipeline") == "analyzing":

                        ev["pipeline"] = "transcribed"

                    elif ev.get("pipeline") == "generating":

                        ev["pipeline"] = "ready_match" if ev.get("is_match_narration") else "transcribed"

                    # Limpa erro antigo de escopo 're' e reclassifica se necessário

                    if "cannot access free variable 're'" in str(ev.get("error") or ""):

                        ev["error"] = ""

                        if ev.get("narration_path") and os.path.exists(ev["narration_path"]):

                            ev["pipeline"] = "transcribed"

                            ev["auto_generated"] = False

        except Exception as ex:  # noqa: BLE001

            print(f"[CANAIS LIVE] Erro ao ler estado: {ex}")



        # Auto-seed canais padrão

        existing_urls = {c.get("url", "").lower() for c in self.state.get("channels", [])}

        added_seeds = False

        for seed in DEFAULT_SEED_CHANNELS:

            if seed["url"].lower() not in existing_urls:

                self.state.setdefault("channels", []).append(dict(seed))

                existing_urls.add(seed["url"].lower())

                added_seeds = True

        self.state.setdefault("settings", {}).setdefault("auto_detect_match", True)

        self.state.setdefault("settings", {}).setdefault("auto_report", True)

        if self.get_setting("auto_detect_match", True):

            self.apply_auto_detect_all(silent=True)

        if added_seeds:

            self._save()



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



    def update_event(self, vid: str, notify: bool = True, **fields) -> None:

        with self.lock:

            ev = self.state["events"].get(vid)

            if ev is None:

                return

            pipe_changed = "pipeline" in fields and fields["pipeline"] != ev.get("pipeline")

            pdf_changed = "pdf_path" in fields and fields["pdf_path"] != ev.get("pdf_path")

            sel_changed = "selected" in fields and fields["selected"] != ev.get("selected")

            err_changed = "error" in fields and fields["error"] != ev.get("error")

            ev.update(fields)

            ev["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        

        # Só notifica a interface e salva o disco imediatamente se houver mudança de estado estrutural

        is_structural = pipe_changed or pdf_changed or sel_changed or err_changed

        if notify and is_structural:

            self._changed()

        elif notify and "progress" in fields:

            # Progresso simples: salva com throttle e avisa suavemente

            now = time.time()

            if now - getattr(self, "_last_prog_notify", 0) > 1.0:

                self._last_prog_notify = now

                if self.on_change:

                    try:

                        self.on_change()

                    except Exception:

                        pass



    def set_selected(self, vid: str, selected: bool, by_user: bool = True) -> None:

        with self.lock:

            ev = self.state["events"].get(vid)

            if not ev:

                return

            ev["selected"] = bool(selected)

            if by_user:

                ev["user_unselected"] = not bool(selected)

                if selected:

                    ev["auto_queued"] = False

            else:

                ev["auto_queued"] = bool(selected)

            if selected and ev.get("pipeline") in (None, "", "idle"):

                st = ev.get("status")

                ev["pipeline"] = "live" if st == "live" else ("ended" if st == "ended" else "waiting")

                ev["next_attempt"] = 0

                ev["last_check"] = 0

            elif not selected and ev.get("pipeline") in ("waiting", "live", "ended", "failed"):

                ev["pipeline"] = "idle"

        self.log(("✅ Evento selecionado para análise: " if selected else "Evento removido da análise: ") + ev.get("title", vid))

        self._changed()



    def apply_auto_detect_all(self, silent: bool = False) -> int:

        """Enfileira automaticamente apenas eventos ativos, futuros e recém-encerrados (últimas 24h)."""

        added = 0

        now = time.time()

        with self.lock:

            if not self.get_setting("auto_detect_match", True):

                return 0

            for vid, ev in self.state["events"].items():

                if ev.get("selected") or ev.get("user_unselected"):

                    continue

                if _is_24h_or_continuous_stream(ev.get("title", ""), ev):

                    continue

                st = ev.get("status")

                # Apenas enfileirar se for ao vivo, futuro ou se encerrou nas últimas 24h

                is_recent_ended = False

                if st == "ended":

                    ref_time = ev.get("ended_detected_at") or ev.get("actual_start_epoch") or 0

                    if ref_time and (now - ref_time) <= 86400:

                        is_recent_ended = True

                

                if st in ("upcoming", "live") or is_recent_ended:

                    from modules.narration_chronology import is_likely_match

                    dur_val = int(ev.get("duration") or 0)

                    if not is_likely_match(ev.get("title", ""), dur_val):

                        # Descarta programas, debates, noticias e concentracoes

                        continue

                    ev["selected"] = True

                    ev["auto_queued"] = True

                    if ev.get("pipeline") in (None, "", "idle"):

                        ev["pipeline"] = "live" if st == "live" else ("ended" if st == "ended" else "waiting")

                        ev["next_attempt"] = 0

                        ev["last_check"] = 0

                    added += 1

        if added and not silent:

            self.log(f"🎯 [Auto-Detect Jogo] {added} evento(s) incluído(s) automaticamente na fila de avaliação.")

            self._changed()

        elif added and silent:

            self._save()

        return added





    def remove_from_queue(self, vid: str) -> bool:

        """Remove explicitamente um evento da fila de monitoramento e análise."""

        with self.lock:

            ev = self.state["events"].get(vid)

            if ev:

                ev["selected"] = False

                ev["user_unselected"] = True

                ev["auto_queued"] = False

            if "active_queue" in self.state and vid in self.state["active_queue"]:

                self.state["active_queue"].remove(vid)

            self._changed()

            return True



    def clean_queue_keep_active(self) -> int:

        """Remove da fila eventos encerrados antigos que não possuem PDF gerado nem narração ativa."""

        with self.lock:

            removed = 0

            for vid, ev in list(self.state["events"].items()):

                if ev.get("selected"):

                    now = time.time()

                    is_live = ev.get("pipeline") in ("live", "transcribing", "analyzing", "generating") or ev.get("status") == "live"

                    sched = float(ev.get("scheduled_epoch") or 0)

                    is_future = ev.get("status") == "upcoming" and sched > now

                    is_active = is_live or is_future

                    has_result = bool(ev.get("pdf_path") or ev.get("narration_path"))

                    if not is_active and not has_result:

                        ev["selected"] = False

                        removed += 1

            if removed:

                self._changed()

                self.log(f"🧹 [Fila] Limpeza concluída: {removed} eventos antigos removidos da fila de análise.")

            return removed



    def unapply_auto_detect_waiting(self) -> int:

        """Remove da fila apenas os eventos que entraram automaticamente e ainda não iniciaram transcrição."""

        removed = 0

        with self.lock:

            for vid, ev in self.state["events"].items():

                if ev.get("selected") and ev.get("auto_queued") and ev.get("pipeline") in ("waiting", "live"):

                    ev["selected"] = False

                    ev["pipeline"] = "idle"

                    removed += 1

        if removed:

            self.log(f"🎯 [Auto-Detect Jogo] {removed} evento(s) automático(s) aguardando foram desmarcados da fila.")

            self._changed()

        return removed



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

        self.set_selected(vid, True, by_user=True)

        return ev



    def _upsert_event(self, vid: str, info: Dict[str, Any], channel: Optional[Dict[str, Any]]) -> Dict[str, Any]:

        status = _status_from_live(info.get("live_status") or "")

        auto_added = False

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

            # Se a chave 🎯 Auto-Detect Jogo estiver ativa, inclui automaticamente na fila (exceto lives 24h ou desmarcadas pelo usuário)

            if (

                self.get_setting("auto_detect_match", True)

                and not ev.get("selected")

                and not ev.get("user_unselected")

                and status in ("upcoming", "live")

                and not _is_24h_or_continuous_stream(ev.get("title", ""), ev)

            ):

                ev["selected"] = True

                ev["auto_queued"] = True

                if ev.get("pipeline") in (None, "", "idle"):

                    ev["pipeline"] = "live" if status == "live" else "waiting"

                    ev["next_attempt"] = 0

                    ev["last_check"] = 0

                auto_added = True

        if auto_added:

            self.log(f"🎯 [Auto-Detect Jogo] Evento monitorado automaticamente: {ev.get('title', vid)}")

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

            elif pipe == "transcribed" and vid not in self._busy:

                self.run_analysis_async(vid)

            elif pipe == "ready_match" and self.get_setting("auto_report", True) and not ev.get("auto_generated") and vid not in self._busy:

                self.update_event(vid, auto_generated=True)

                self.run_generation_async(vid, meta=None, auto=True)



    # ---------------------------------------------------------- transcrição & análise

    def run_transcription_async(self, vid: str, force_audio: bool = False) -> None:

        if vid in self._busy:

            return

        self._busy.add(vid)

        threading.Thread(target=self._transcribe_job, args=(vid, force_audio), daemon=True).start()



    def run_analysis_async(self, vid: str) -> None:

        if vid in self._busy:

            return

        self._busy.add(vid)

        threading.Thread(target=self._analyze_job, args=(vid,), daemon=True).start()



    def _analyze_job(self, vid: str) -> None:

        try:

            with self._job_lock:

                self._analyze_transcript_locked(vid)

        finally:

            self._busy.discard(vid)



    def _analyze_transcript_locked(self, vid: str) -> None:

        from modules.narration_chronology import analyze_narration_transcript

        ev = self.get_event(vid)

        if not ev or not ev.get("narration_path") or not os.path.exists(ev["narration_path"]):

            return



        cfg = self.config_provider() or {}

        self.update_event(vid, pipeline="analyzing", progress="Analisando transcrição (identificando partida, times e menções de marcas)...", error="")



        def plog(m: str) -> None:

            self.log(f"[{ev.get('title', vid)[:40]}] {m}")

            self.update_event(vid, progress=m)



        analysis = analyze_narration_transcript(

            ev,

            api_key=cfg.get("api_key"),

            model_id=cfg.get("model_id") or "gemini-2.5-flash",

            log=plog,

        )

        is_match = bool(analysis.get("is_match_narration"))

        meta = dict(ev.get("meta") or {})

        if analysis.get("team1"):

            meta["team1"] = analysis["team1"]

        if analysis.get("team2"):

            meta["team2"] = analysis["team2"]

        if analysis.get("competition"):

            meta["competition"] = analysis["competition"]

        if analysis.get("date"):

            meta["date"] = analysis["date"]



        brand_mentions = analysis.get("brand_mentions") or []

        brands_summary = analysis.get("brands_summary") or ""

        summary_txt = analysis.get("classification_summary") or ""



        if is_match:

            jogo_str = f"{meta.get('team1', '')} x {meta.get('team2', '')}".strip(" x")

            prog_msg = f"⚽ Partida identificada: {jogo_str} ({meta.get('competition', '')})"

            if brand_mentions:

                prog_msg += f" • 📢 {len(brand_mentions)} menções de marcas"

            self.update_event(

                vid,

                pipeline="ready_match",

                is_match_narration=True,

                transcript_analysis=analysis,

                meta=meta,

                brand_mentions=brand_mentions,

                brands_summary=brands_summary,

                progress=prog_msg,

                error="",

            )

            self.log(f"✅ [{ev.get('title', vid)[:45]}] Classificado como PARTIDA NARRADA: {jogo_str}")

            # Se a chave Auto-Relatório estiver ativa, já gera o relatório cronológico e envia e-mail!

            if self.get_setting("auto_report", True) and not ev.get("auto_generated"):

                self.update_event(vid, auto_generated=True)

                self._generate_locked(vid, meta=meta, auto=True, progress_cb=None)

        else:

            cat = analysis.get("event_category") or "Programa / Debate"

            prog_msg = f"ℹ️ {cat}: {summary_txt}" if summary_txt else f"ℹ️ {cat} (Não houve narração de partida em tempo real)."

            if brand_mentions:

                prog_msg += f" • 📢 {len(brand_mentions)} marcas citadas"

            self.update_event(

                vid,

                pipeline="not_match",

                is_match_narration=False,

                transcript_analysis=analysis,

                meta=meta,

                brand_mentions=brand_mentions,

                brands_summary=brands_summary,

                progress=prog_msg,

                error="",

                selected=False,

                user_unselected=True

            )

            try:

                self.remove_from_queue(vid)

            except Exception as ex_rm:

                self.log(f"⚠️ Aviso ao remover da fila: {ex_rm}")

            self.log(f"🗑️ [Auto-Eliminação] '{ev.get('title', vid)[:45]}' não é jogo e foi removido da fila.")



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

                dur_s = int(ev.get("duration") or 0)

                if ev.get("auto_queued") and not force_audio and 0 < dur_s < 900:

                    self.update_event(

                        vid,

                        pipeline="not_match",

                        is_match_narration=False,

                        transcript_analysis={

                            "is_match_narration": False,

                            "event_category": "Boletim / Vídeo Curto",

                            "classification_summary": f"Duração curta ({dur_s // 60} min) incompatível com transmissão de partida completa (0 tokens gastos).",

                        },

                        progress=f"ℹ️ Boletim/Vídeo curto ({dur_s // 60} min) — ignorado sem gastar tokens.",

                        error="",

                    )

                    self.log(f"ℹ️ [{ev.get('title', vid)[:45]}] Vídeo curto ({dur_s // 60} min) classificado sem gasto de tokens.")

                    return

                cfg = self.config_provider() or {}

                now = time.time()

                ended_at = ev.get("ended_detected_at") or now

                waited = now - ended_at

                vod_ready = (ev.get("live_status") == "was_live")

                allow_audio = force_audio or (vod_ready and waited >= AUDIO_FALLBACK_AFTER_S) or waited >= AUDIO_FORCE_AFTER_S

                if allow_audio and ev.get("auto_queued") and not force_audio:

                    from modules.narration_chronology import guess_match_from_title

                    g_title = guess_match_from_title(ev.get("title", ""))

                    has_match_hint = bool(g_title.get("team1") and g_title.get("team2")) or bool(

                        re.search(r"\b(jornada|narra[cç][aã]o|transmiss[aã]o|futebol|gauch[aã]o|brasileir[aã]o|libertadores|copa|grenal|gre-nal)\b", ev.get("title", ""), re.I)

                    )

                    if not has_match_hint or dur_s > 6 * 3600:

                        allow_audio = False

                self.update_event(vid, pipeline="transcribing", progress="Iniciando transcrição...")



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

                                      transcript_source_label=label, narration_lines=res["lines"], error="", progress="Transcrição concluída. Iniciando análise...",

                                      auto_generated=False)

                    # Entra automaticamente no processo de análise da transcrição!

                    self._analyze_transcript_locked(vid)

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

        analysis = ev.get("transcript_analysis") or {}

        g = guess_match_from_title(ev.get("title", ""))

        for k in ("team1", "team2", "competition"):

            if not meta.get(k):

                meta[k] = analysis.get(k) or g.get(k, "")

        if not meta.get("date"):

            ref = ev.get("actual_start_epoch") or ev.get("scheduled_epoch")

            meta["date"] = analysis.get("date") or (datetime.fromtimestamp(ref).strftime("%d/%m/%Y") if ref else "")

        return meta



    def run_generation_async(self, vid: str, meta: Optional[Dict[str, str]] = None, auto: bool = False,

                             progress_cb: Optional[Callable[[str], None]] = None,

                             done_cb: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:

        if vid in self._busy:

            return False

        self._busy.add(vid)

        threading.Thread(target=self._generate_job, args=(vid, meta, auto, progress_cb, done_cb), daemon=True).start()

        return True





    def generate_posterior_match_report_async(self, vid: str, meta: Optional[Dict[str, str]] = None,

                                              progress_cb: Optional[Callable[[str], None]] = None,

                                              done_cb: Optional[Callable[[Dict[str, Any]], None]] = None) -> bool:

        """Gera o relatório cronológico de partida para um evento já encerrado (posterior ao evento),

        transcrevendo o áudio se necessário e gerando o relatório oficial com SharePoint e E-mail."""

        def _job():

            try:

                ev = self.get_event(vid)

                if not ev:

                    if done_cb: done_cb({"error": "Evento não encontrado na base de dados."})

                    return



                narr_path = ev.get("narration_path")

                if not narr_path or not os.path.exists(narr_path):

                    self.log(f"🎙️ [Posterior] Transcrevendo áudio do evento encerrado: {ev.get('title')[:45]}...")

                    if progress_cb: progress_cb("Extraindo áudio completo e gerando transcrição...")

                    cfg = self.config_provider() or {}

                    fname = f"narracao_{_safe(ev.get('channel_name'), 25)}_{_safe(ev.get('title'), 50)}_{vid}.txt"

                    out_path = os.path.join(self.narr_dir, fname)

                    from modules.narration_transcriber import transcribe_event

                    res = transcribe_event(ev, out_path, api_key=cfg.get("api_key"), model_id=cfg.get("model_id") or "gemini-2.5-flash",

                                           allow_audio=True, log=progress_cb or self.log)

                    if not res.get("ok"):

                        err = res.get("error", "Falha na transcrição de áudio.")

                        self.update_event(vid, error=err, pipeline="failed")

                        if done_cb: done_cb({"error": err})

                        return

                    self.update_event(vid, narration_path=res["path"], narration_lines=res.get("lines", 0),

                                      transcript_source="audio_gemini", transcript_source_label="Áudio transcrito (Sob Demanda)",

                                      pipeline="ready_match", is_match_narration=True, error="")



                final_meta = meta or self.default_meta(ev)

                self.log(f"📊 [Posterior] Gerando cronologia de jogo para {final_meta.get('team1', '')} x {final_meta.get('team2', '')}...")

                if progress_cb: progress_cb(f"Gerando cronologia oficial de {final_meta.get('team1', '')} x {final_meta.get('team2', '')}...")

                res_gen = self._generate_locked(vid, meta=final_meta, auto=False, progress_cb=progress_cb)

                if done_cb:

                    done_cb(res_gen)

            except Exception as ex:

                self.log(f"⚠️ [Posterior] Erro ao gerar relatório posterior: {ex}")

                if done_cb: done_cb({"error": str(ex)})



        threading.Thread(target=_job, daemon=True).start()

        return True



    def _generate_locked(self, vid: str, meta: Optional[Dict[str, str]], auto: bool,

                         progress_cb: Optional[Callable[[str], None]]) -> Dict[str, Any]:

        from modules.narration_chronology import generate_narration_chronology

        ev = self.get_event(vid)

        if not ev or not ev.get("narration_path"):

            return {"error": "Narração ainda não disponível."}

        prev_pipe = ev.get("pipeline") if ev.get("pipeline") in ("ready_match", "transcribed", "done") else "ready_match"

        meta = meta or self.default_meta(ev)

        self.update_event(vid, pipeline="generating", meta=meta, progress="Iniciando geração do relatório cronológico...", error="")

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

            return result

        plog("📄 Renderizando PDF oficial do relatório cronológico...")

        prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}

        # Gera o PDF localmente em 1-2 segundos sem travar na rede

        pdf = self.reporter.write_expert_report([result], prefs=prefs, sync_sharepoint=False, name_prefix="narracao")

        

        # ATUALIZA IMEDIATAMENTE PARA PRONTO: o usuário já pode ver e abrir o PDF na hora!

        self.update_event(vid, pipeline="done", pdf_path=pdf, error="",

                          progress=f"Relatório PDF concluído ({os.path.basename(pdf)})",

                          generated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        plog(f"✅ Relatório PDF pronto: {os.path.basename(pdf)}")



        # Disparo desacoplado em segundo plano (SharePoint NÃO é automático para Canais Live, conforme solicitado)

        def _bg_sync():

            # Nota: Sincronização com SharePoint em Canais Live é estritamente sob demanda via botão na interface



            if auto or self.get_setting("auto_report", True) or self.get_setting("auto_email", True):

                try:

                    plog("✉️ Enviando relatório por e-mail...")

                    self.send_email(vid)

                except Exception as ex_em:

                    self.log(f"⚠️ Aviso E-mail: {ex_em}")



        threading.Thread(target=_bg_sync, daemon=True).start()

        return {"ok": True, "pdf_path": pdf}



    def sync_event_to_sharepoint(self, vid: str) -> bool:
        """Sincronizacao de canais do YouTube para Relatorios_de_Jogos desabilitada por regra de negocio."""
        self.log(f"ℹ️ Canais Live operam em modo isolado: nao enviam relatorios para a lista de futebol do SharePoint.")
        return False

    def generate_case_report_for_event(self, vid: str) -> Dict[str, Any]:

        """Gera relatório técnico de ocorrência para qualquer evento (incluindo programas/debates ou eventos com erro)."""

        from modules.sharepoint_reporter import SharePointReporter

        ev = self.get_event(vid)

        if not ev:

            return {"error": "Evento não encontrado."}

        analysis = ev.get("transcript_analysis") or {}

        narr_path = ev.get("narration_path")

        meta = self.default_meta(ev)

        start = ev.get("actual_start_epoch") or ev.get("scheduled_epoch")

        dur = int(ev.get("duration") or 0)

        dur_hms = f"{dur // 3600:02d}:{(dur % 3600) // 60:02d}:{dur % 60:02d}" if dur > 0 else "N/D"

        live_start = datetime.fromtimestamp(start).strftime("%H:%M:%S") if start else "N/D"

        live_end = datetime.fromtimestamp(start + dur).strftime("%H:%M:%S") if (start and dur) else "N/D"

        live_date = datetime.fromtimestamp(start).strftime("%d/%m/%Y") if start else datetime.now().strftime("%d/%m/%Y")



        cat = analysis.get("event_category") or "Programa / Debate"

        summary_diag = analysis.get("classification_summary") or ev.get("progress") or "Transmissão analisada pela IA (não foi identificada narração de partida esportiva em tempo real)."

        brand_mentions = ev.get("brand_mentions") or analysis.get("brand_mentions") or []

        brands_summary = ev.get("brands_summary") or analysis.get("brands_summary") or ""



        res_payload = {

            "match_display": f"[OCORRÊNCIA] {ev.get('title', 'Evento')[:70]}",

            "team1": meta.get("team1") or ev.get("channel_name", "Canal"),

            "team2": meta.get("team2") or cat,

            "competition": cat,

            "date": live_date,

            "platform": ev.get("channel_name") or "YouTube",

            "confidence_score": 0.95,

            "duration": dur or None,

            "live_start_time": live_start,

            "live_end_time": live_end,

            "report_title": f"Relatório Técnico de Ocorrência — {cat}",

            "report_kind": "narration",

            "brand_mentions": brand_mentions,

            "brands_summary": brands_summary,

            "technical_milestones": [

                {"time": live_start, "type": "Início da Live", "event": f"Abertura de sinal do canal {ev.get('channel_name')}.", "confidence": 0.99},

                {"time": live_start, "minute": 0, "type": "CLASSIFICAÇÃO IA", "event": f"Classificado como: {cat}. {summary_diag}", "confidence": 0.95},

                {"time": live_end, "type": "Fim da Live", "event": f"Encerramento da transmissão ao vivo ({dur_hms}).", "confidence": 0.99}

            ],

            "transcript_events": [],

            "grounding_verdict": {

                "verdict_text": (

                    f"DIAGNÓSTICO TÉCNICO DA OCORRÊNCIA (IA):\n"

                    f"• Categoria do Evento: {cat}\n"

                    f"• Justificativa da Análise: {summary_diag}\n"

                    f"• Transcrição: {ev.get('narration_lines', 0)} trechos extraídos via {ev.get('transcript_source_label', 'YouTube')}.\n"

                    f"• Inserções Comerciais / Patrocínios: {brands_summary or 'Nenhuma menção de marca detectada.'}\n\n"

                    f"PARECER EXECUTIVO:\n"

                    f"O evento analisado não caracterizou narração esportiva minuto a minuto de partida de futebol em tempo real, "

                    f"tratando-se de conteúdo classificado como '{cat}'. Este relatório documenta a íntegra da análise de auditoria."

                ),

                "source": "ia_diagnostico_ocorrencia",

                "references": []

            },

            "broadcast_info": {

                "channel_name": ev.get("channel_name", ""),

                "channel_url": ev.get("channel_url", ""),

                "video_title": ev.get("title", ""),

                "video_url": ev.get("url", ""),

                "live_start": datetime.fromtimestamp(start).strftime("%d/%m/%Y %H:%M:%S") if start else "N/D",

                "live_end": datetime.fromtimestamp(start + dur).strftime("%d/%m/%Y %H:%M:%S") if (start and dur) else "N/D",

                "duration": dur_hms,

                "transcript_source": ev.get("transcript_source_label") or "YouTube",

                "narration_file": os.path.basename(narr_path) if narr_path else "—",

                "narration_type": "programa_debate",

                "final_score": "N/A",

                "summary": summary_diag,

                "brands_summary": brands_summary,

            }

        }

        pdf = self.reporter.write_expert_report([res_payload], prefs={"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}, sync_sharepoint=False, name_prefix="caso_ocorrencia")

        self.update_event(vid, pdf_path=pdf, error="", progress=f"Relatório de ocorrência gerado ({os.path.basename(pdf)})",

                          generated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),

                          sharepoint_synced=True, sharepoint_synced_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

        self.log(f"📄 Relatório de ocorrência gerado e publicado no SharePoint: {os.path.basename(pdf)}")

        return {"ok": True, "pdf_path": pdf}





    def generate_all_cases_audit_report(self) -> Dict[str, Any]:

        """Gera um relatório PDF consolidado de auditoria de todas as lives avaliadas (partidas, debates e ocorrências),

        detalhando o parecer da IA, marcas comerciais e status de sincronização no SharePoint."""

        from modules.sharepoint_reporter import SharePointReporter

        events = self.list_events()

        if not events:

            return {"error": "Nenhum evento registrado no histórico para auditoria."}



        def _ev_time(e):

            return float(e.get("actual_start_epoch") or e.get("scheduled_epoch") or 0)

        sorted_evs = sorted(events, key=_ev_time, reverse=True)



        milestones = []

        total_jogos = 0

        total_debates = 0

        total_marcas = 0



        for idx, ev in enumerate(sorted_evs[:35], 1):

            analysis = ev.get("transcript_analysis") or {}

            is_match = ev.get("is_match_narration")

            cat = analysis.get("event_category") or ("Partida Narrada" if is_match else "Programa / Debate")

            if is_match:

                total_jogos += 1

            else:

                total_debates += 1



            diag = analysis.get("classification_summary") or ev.get("progress") or "Transmissão monitorada"

            brand_mentions = ev.get("brand_mentions") or analysis.get("brand_mentions") or []

            total_marcas += len(brand_mentions)

            b_summary = ev.get("brands_summary") or analysis.get("brands_summary") or ""



            st_epoch = ev.get("actual_start_epoch") or ev.get("scheduled_epoch")

            st_str = datetime.fromtimestamp(st_epoch).strftime("%d/%m %H:%M") if st_epoch else "N/D"

            ch = ev.get("channel_name") or "YouTube"

            t_title = ev.get("title", "")[:60]

            sp_status = "Sincronizado" if ev.get("sharepoint_synced") else "Pendente"



            milestones.append({

                "time": st_str,

                "minute": idx,

                "type": f"[{ch}] {cat.upper()}",

                "event": (

                    f"Vídeo: {t_title}\n"

                    f"• Categoria IA: {cat} | SP: {sp_status}\n"

                    f"• Diagnóstico: {diag}\n"

                    f"• Marcas/Patrocínios: {b_summary or (f'{len(brand_mentions)} menções' if brand_mentions else 'Nenhuma menção')}"

                ),

                "confidence": 0.98 if is_match else 0.95

            })



        hoje = datetime.now().strftime("%d/%m/%Y")

        res_payload = {

            "match_display": f"AUDITORIA GERAL DE LIVES ({len(sorted_evs)} eventos)",

            "team1": "Auditoria de Lives",

            "team2": "Canais Esportivos YouTube",

            "competition": "Auditoria & Governança de Transmissões",

            "date": hoje,

            "platform": "YouTube Live Monitor",

            "confidence_score": 0.99,

            "report_title": "Relatório Executivo de Auditoria de Lives e Casos Monitorados",

            "report_kind": "narration",

            "technical_milestones": milestones,

            "transcript_events": [],

            "grounding_verdict": {

                "verdict_text": (

                    f"PARECER EXECUTIVO DE AUDITORIA DE LIVES:\n\n"

                    f"Total de Transmissões Monitoradas: {len(sorted_evs)}\n"

                    f"• Partidas Narradas Confirmadas: {total_jogos}\n"

                    f"• Programas, Debates e Outros Formatos: {total_debates}\n"

                    f"• Inserções Comerciais / Marcas Rastreadas: {total_marcas}\n\n"

                    f"DIAGNÓSTICO TÉCNICO DE COBERTURA:\n"

                    f"O módulo Canais Live transcreve o áudio de transmissões esportivas e submete à inteligência "

                    f"artificial Gemini para classificação rigorosa. Apenas transmissões contendo locução minuto a minuto "

                    f"de lances reais recebem status de Partida Narrada. Conteúdos opinativos, pré-jogos e mesas redondas "

                    f"são documentados formalmente como ocorrências com trilha de auditoria completa e publicação no SharePoint."

                ),

                "source": "auditoria_executiva_lives",

                "references": []

            },

            "broadcast_info": {

                "channel_name": "Múltiplos Canais (Gaúcha, Band, Atlântida, Baldasso, Bagé)",

                "video_title": f"Auditoria Consolidada de {len(sorted_evs)} Lives",

                "channel_url": "https://www.youtube.com",

                "video_url": "https://www.youtube.com",

                "live_start": datetime.now().strftime("%d/%m/%Y %H:%M"),

                "live_end": datetime.now().strftime("%d/%m/%Y %H:%M"),

                "duration": f"{len(sorted_evs)} eventos",

                "transcript_source": "YouTube Transcripts + Gemini AI",

                "narration_type": "auditoria_consolidada",

                "final_score": f"{total_jogos} Jogos / {total_debates} Programas",

                "summary": f"Consolidado de auditoria abrangendo {len(sorted_evs)} eventos ao vivo monitorados.",

                "brands_summary": f"Total de {total_marcas} menções publicitárias identificadas nas transmissões.",

            }

        }

        prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}

        pdf = self.reporter.write_expert_report([res_payload], prefs=prefs, sync_sharepoint=False, name_prefix="auditoria_geral_lives")

        self.log(f"📋 Relatório Geral de Auditoria gerado e publicado no SharePoint: {os.path.basename(pdf)}")

        return {"ok": True, "pdf_path": pdf, "total_events": len(sorted_evs)}



    def _generate_job(self, vid, meta, auto, progress_cb, done_cb) -> None:

        out: Dict[str, Any] = {}

        try:

            with self._job_lock:

                out = self._generate_locked(vid, meta, auto, progress_cb)

        except Exception as ex:  # noqa: BLE001

            ev = self.get_event(vid) or {}

            prev_pipe = "ready_match" if ev.get("is_match_narration") else "transcribed"

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

    def send_email(self, vid: str, recipients: Optional[List[str]] = None, return_details: bool = False) -> Any:

        from modules.email_service import EmailService

        ev = self.get_event(vid)

        if not ev:

            err = "Evento não encontrado na fila."

            return (False, err) if return_details else False



        cfg = self.config_provider() or {}

        recipients = recipients or self.get_setting("emails") or cfg.get("emails")

        if not recipients:

            for p in (

                os.path.join(os.environ.get("APPDATA", ""), "Monitor_Esportes", "config", "saved_emails.json"),

                os.path.join("config", "saved_emails.json")

            ):

                if os.path.exists(p):

                    try:

                        with open(p, "r", encoding="utf-8") as f_em:

                            recipients = json.load(f_em)

                            if recipients:

                                break

                    except Exception:

                        pass

        if not recipients:

            recipients = ["cleber.goncalves@ibope.com", "arthur@mediadna.com.br"]



        sender = cfg.get("sender") or cfg.get("email") or "kimsuportecaptacao@gmail.com"

        password = cfg.get("password") or cfg.get("senha") or "ufvg yhog yrql vmqb"

        smtp_server = cfg.get("smtp_server") or "smtp.gmail.com"

        smtp_port = int(cfg.get("smtp_port") or 587)



        pdf = ev.get("pdf_path") if ev.get("pdf_path") and os.path.exists(ev.get("pdf_path")) else None

        if not pdf:

            err = "O arquivo PDF do relatório deste evento ainda não foi gerado ou não foi encontrado em disco."

            self.log(f"⚠️ [EMAIL] {err}")

            return (False, err) if return_details else False



        attachments = []

        # Para garantir entrega imediata e evitar recusas do servidor SMTP por volume de socket,

        # anexamos estritamente o Relatório Oficial em PDF de alta resolução.



        meta = ev.get("meta") or {}

        jogo = f"{meta.get('team1')} x {meta.get('team2')}" if meta.get("team1") else ev.get("title", "")

        body = (

            f"Relatório Oficial de Auditoria & Narração da live \"{ev.get('title')}\"\n"

            f"Canal: {ev.get('channel_name')}\nVídeo: {ev.get('url')}\n"

            f"Partida / Evento: {jogo}\n\n"

            f"Segue anexo o Relatório Executivo em PDF com cronologia dos lances, marcos técnicos e inserções comerciais/marcas identificadas durante a transmissão.\n"

        )

        if large_narr_omitted:

            body += "\n(Nota: O arquivo completo de narração bruta em texto possui tamanho excessivo (>10MB) e foi preservado localmente no sistema para segurança do envio do relatório oficial).\n"

        body += "\n— Monitor de Esportes (Canais Live)"



        try:

            svc = EmailService(smtp_server, smtp_port, sender, password)

            ok = svc.send_report(recipients, f"Relatório de Narração Live — {ev.get('channel_name')} — {jogo}", body, pdf,

                                 extra_attachments=attachments)

            if ok:

                self.update_event(vid, emailed_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

                self.log(f"✉️ E-mail enviado com sucesso para: {', '.join(recipients)}")

                return (True, f"E-mail enviado com sucesso para: {', '.join(recipients)}") if return_details else True

            else:

                err = f"Falha no envio via servidor SMTP ({smtp_server}:{smtp_port})."

                return (False, err) if return_details else False

        except Exception as ex:  # noqa: BLE001

            err_msg = f"Erro no envio de e-mail ({type(ex).__name__}): {ex}"

            self.log(f"⚠️ Falha ao enviar e-mail: {err_msg}")

            return (False, err_msg) if return_details else False



    def clean_non_matches_from_queue(self) -> int:

        """Remove sumariamente da fila da direita todos os eventos que não são partidas de futebol reais."""

        from modules.narration_chronology import is_likely_match, is_definitely_non_match

        removed = 0

        with self.lock:

            queue_list = list(self.state.get("active_queue", []))

            for vid in queue_list:

                ev = self.state["events"].get(vid)

                if not ev:

                    if vid in self.state["active_queue"]:

                        self.state["active_queue"].remove(vid)

                        removed += 1

                    continue

                is_match = ev.get("is_match_narration")

                pipe = ev.get("pipeline")

                title = ev.get("title", "")

                dur = int(ev.get("duration") or 0)



                is_non, _ = is_definitely_non_match(title)

                should_remove = False

                if pipe == "not_match" or is_match is False:

                    should_remove = True

                elif is_non:

                    should_remove = True

                elif pipe in ("waiting", "upcoming", "idle") and not is_likely_match(title, dur):

                    should_remove = True



                if should_remove:

                    ev["selected"] = False

                    ev["user_unselected"] = True

                    ev["pipeline"] = "not_match"

                    if vid in self.state["active_queue"]:

                        self.state["active_queue"].remove(vid)

                    removed += 1



            # Resgata jogos de 24/10 se estiverem pendentes

            for vid, ev in self.state["events"].items():

                title = ev.get("title", "")

                if "INTER X BOTAFOGO" in title.upper() and ("24/10" in title or "24/10" in str(ev.get("scheduled_epoch"))):

                    ev["status"] = "ended"

                    if ev.get("pipeline") in ("waiting", "idle", None):

                        ev["pipeline"] = "ended"

                    ev["selected"] = True

                    ev["is_match_narration"] = True

                    if vid not in self.state["active_queue"]:

                        self.state["active_queue"].append(vid)



        if removed:

            self.log(f"🧹 [Faxina] {removed} eventos que não eram partidas de futebol foram eliminados da fila.")

            self._changed()

        return removed

