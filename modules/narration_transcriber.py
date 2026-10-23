# modules/narration_transcriber.py
"""
Transcrição completa da narração de uma live do YouTube já encerrada.

Estratégia (definida com o usuário):
1. Legendas automáticas/manuais do YouTube (gratuito, sem cota).
2. Fallback: baixa o áudio com yt-dlp, divide em blocos com ffmpeg e transcreve
   cada bloco com o Gemini (API), com rotação de chaves.

Saída: arquivo .txt com cabeçalho e linhas no formato
    [HH:MM:SS do vídeo | HH:MM:SS relógio real] texto
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

AUDIO_CHUNK_SECONDS = 900  # 15 min por bloco enviado ao Gemini
CAPTION_BLOCK_SECONDS = 15


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def fmt_hms(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _real_clock(live_start_epoch: Optional[float], offset_s: float) -> str:
    if not live_start_epoch:
        return "--:--:--"
    return datetime.fromtimestamp(float(live_start_epoch) + offset_s).strftime("%H:%M:%S")


def find_ffmpeg() -> Optional[str]:
    """Procura o ffmpeg no PATH, em C:\\ffmpeg\\bin ou no pacote imageio-ffmpeg (embutido no .exe)."""
    p = shutil.which("ffmpeg")
    if p:
        return p
    import sys
    for cand in (r"C:\ffmpeg\bin\ffmpeg.exe", os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe")):
        if os.path.exists(cand):
            return cand
    try:
        import imageio_ffmpeg  # type: ignore
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return None


def make_gemini_client(api_key: str, read_timeout_s: float = 600.0):
    """Cliente google-genai com o mesmo perfil de rede do ExpertAssistant, mas com timeout longo (áudio)."""
    import httpx
    from google import genai
    from google.genai import types

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    h_client = httpx.Client(
        verify=False, http2=False,
        timeout=httpx.Timeout(read_timeout_s, connect=15.0),
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=5),
        headers=headers,
    )
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(headers=headers, httpx_client=h_client))


def split_keys(api_key: Any) -> List[str]:
    if isinstance(api_key, (list, tuple)):
        raw = ",".join(str(k) for k in api_key)
    else:
        raw = str(api_key or "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def _is_quota_error(ex: Exception) -> bool:
    s = str(ex).lower()
    return any(k in s for k in ("429", "resource_exhausted", "quota", "rate limit", "spend"))


def gemini_generate_text(api_key: Any, model_id: str, contents: list, *, json_mode: bool = False,
                         log: Optional[Callable[[str], None]] = None, client_factory=None) -> str:
    """Executa generate_content (streaming, para não estourar timeout) com rotação de chaves."""
    from google.genai import types

    keys = split_keys(api_key)
    if not keys:
        raise RuntimeError("Nenhuma chave da API do Gemini configurada (Config IA).")
    cfg = types.GenerateContentConfig(temperature=0.1, max_output_tokens=65536,
                                      response_mime_type="application/json" if json_mode else None)
    last_err: Optional[Exception] = None
    for attempt in range(len(keys) * 2):
        key = keys[attempt % len(keys)]
        try:
            client = (client_factory or make_gemini_client)(key)
            parts: List[str] = []
            for chunk in client.models.generate_content_stream(model=model_id, contents=contents, config=cfg):
                if getattr(chunk, "text", None):
                    parts.append(chunk.text)
            txt = "".join(parts).strip()
            if txt:
                return txt
            last_err = RuntimeError("Gemini retornou resposta vazia.")
        except Exception as ex:  # noqa: BLE001
            last_err = ex
            if log:
                log(f"⚠️ Gemini (chave ...{key[-6:]}): {str(ex)[:160]}")
            if not _is_quota_error(ex):
                time.sleep(3)
    raise RuntimeError(f"Falha no Gemini após rotação de chaves: {last_err}")


# ---------------------------------------------------------------------------
# 1) Legendas do YouTube
# ---------------------------------------------------------------------------
def _entry_fields(entry: Any) -> Tuple[Optional[float], str]:
    try:
        if hasattr(entry, "start"):
            return float(entry.start), str(entry.text)
        if isinstance(entry, dict):
            return float(entry.get("start", 0)), str(entry.get("text", ""))
    except Exception:
        pass
    return None, ""


def fetch_caption_lines(video_url: str, live_start_epoch: Optional[float]) -> Tuple[List[str], str]:
    """Retorna (linhas, idioma). Lista vazia se não houver legenda disponível."""
    from modules.youtube_transcript_service import YouTubeTranscriptService

    transcript = YouTubeTranscriptService.get_transcript(video_url)
    if not transcript:
        return [], ""
    blocks: Dict[int, List[str]] = {}
    for entry in transcript:
        start, text = _entry_fields(entry)
        text = re.sub(r"\s+", " ", text.replace("\n", " ")).strip()
        if start is None or not text or text in ("[Música]", "[Music]", "[Aplausos]"):
            continue
        blocks.setdefault(int(start // CAPTION_BLOCK_SECONDS), []).append(text)
    lines = []
    for idx in sorted(blocks):
        off = idx * CAPTION_BLOCK_SECONDS
        lines.append(f"[{fmt_hms(off)} | {_real_clock(live_start_epoch, off)}] {' '.join(blocks[idx])}")
    return lines, "pt"


# ---------------------------------------------------------------------------
# 2) Áudio + Gemini
# ---------------------------------------------------------------------------
def download_audio(video_url: str, work_dir: str, log: Callable[[str], None]) -> str:
    import yt_dlp

    last_pct = {"v": -10}

    def hook(d):
        if d.get("status") == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            if tot:
                pct = int(d.get("downloaded_bytes", 0) * 100 / tot)
                if pct >= last_pct["v"] + 10:
                    last_pct["v"] = pct
                    log(f"⬇️ Baixando áudio da live... {pct}%")

    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": os.path.join(work_dir, "audio.%(ext)s"),
        "quiet": True, "no_warnings": True, "noprogress": True,
        "progress_hooks": [hook],
        "retries": 5, "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        path = ydl.prepare_filename(info)
    if not os.path.exists(path):
        cands = [os.path.join(work_dir, f) for f in os.listdir(work_dir) if f.startswith("audio.")]
        if not cands:
            raise RuntimeError("Download do áudio não gerou arquivo.")
        path = cands[0]
    return path


def split_audio(ffmpeg: str, src: str, work_dir: str) -> List[str]:
    pattern = os.path.join(work_dir, "chunk_%03d.mp3")
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
           "-b:a", "32k", "-f", "segment", "-segment_time", str(AUDIO_CHUNK_SECONDS), "-reset_timestamps", "1", pattern]
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    subprocess.run(cmd, check=True, capture_output=True, creationflags=flags)
    return sorted(os.path.join(work_dir, f) for f in os.listdir(work_dir) if f.startswith("chunk_") and f.endswith(".mp3"))


_TS_LINE = re.compile(r"^\s*\[?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?\s*\]?\s*[-–:]?\s*(.+)$")

TRANSCRIBE_PROMPT = (
    "Transcreva INTEGRALMENTE e LITERALMENTE, em português do Brasil, toda a fala deste áudio "
    "(narração/comentários esportivos de uma transmissão ao vivo). Não resuma, não omita trechos, não traduza.\n"
    "Formato OBRIGATÓRIO: uma linha a cada ~15 segundos de fala, começando com o tempo decorrido "
    "desde o início DESTE arquivo de áudio entre colchetes no formato [MM:SS], seguido do texto falado.\n"
    "Exemplo:\n[00:00] Boa tarde, torcedor, está começando...\n[00:15] Bola rolando...\n"
    "Trechos sem fala: escreva [MM:SS] (sem fala / música). Não escreva nada além das linhas."
)


def _upload_and_wait(client, path: str, timeout_s: int = 300):
    f = client.files.upload(file=path)
    t0 = time.time()
    while True:
        state = str(getattr(getattr(f, "state", None), "name", getattr(f, "state", "")) or "")
        if "ACTIVE" in state.upper() or not state:
            return f
        if "FAILED" in state.upper():
            raise RuntimeError("Gemini não conseguiu processar o arquivo de áudio.")
        if time.time() - t0 > timeout_s:
            raise RuntimeError("Timeout aguardando processamento do áudio no Gemini.")
        time.sleep(3)
        f = client.files.get(name=f.name)


def transcribe_chunk_gemini(api_key: Any, model_id: str, path: str, log: Callable[[str], None]) -> List[Tuple[int, str]]:
    """Retorna [(segundos_relativos, texto)]."""
    keys = split_keys(api_key)
    last_err: Optional[Exception] = None
    for attempt in range(max(1, len(keys)) * 2):
        key = keys[attempt % len(keys)]
        client = make_gemini_client(key)
        uploaded = None
        try:
            uploaded = _upload_and_wait(client, path)
            txt = gemini_generate_text(key, model_id, [uploaded, TRANSCRIBE_PROMPT], log=log,
                                       client_factory=lambda _k, c=client: c)
            out: List[Tuple[int, str]] = []
            for ln in txt.splitlines():
                m = _TS_LINE.match(ln)
                if not m:
                    if out and ln.strip():
                        out[-1] = (out[-1][0], out[-1][1] + " " + ln.strip())
                    continue
                a, b, c, body = m.groups()
                secs = int(a) * 3600 + int(b) * 60 + int(c) if c else int(a) * 60 + int(b)
                out.append((secs, body.strip()))
            if out:
                return out
            last_err = RuntimeError("Transcrição do bloco veio sem timestamps.")
        except Exception as ex:  # noqa: BLE001
            last_err = ex
            log(f"⚠️ Bloco {os.path.basename(path)}: {str(ex)[:160]}")
        finally:
            try:
                if uploaded is not None:
                    client.files.delete(name=uploaded.name)
            except Exception:
                pass
    raise RuntimeError(f"Falha ao transcrever {os.path.basename(path)}: {last_err}")


def transcribe_audio_gemini(video_url: str, api_key: Any, model_id: str, live_start_epoch: Optional[float],
                            log: Callable[[str], None]) -> List[str]:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg não encontrado (necessário para dividir o áudio).")
    work = tempfile.mkdtemp(prefix="narracao_")
    try:
        src = download_audio(video_url, work, log)
        log("✂️ Dividindo o áudio em blocos de 15 min...")
        chunks = split_audio(ffmpeg, src, work)
        if not chunks:
            raise RuntimeError("ffmpeg não gerou blocos de áudio.")
        lines: List[str] = []
        for i, ch in enumerate(chunks):
            log(f"🎙️ Transcrevendo bloco {i + 1}/{len(chunks)} com o Gemini...")
            base = i * AUDIO_CHUNK_SECONDS
            for rel, text in transcribe_chunk_gemini(api_key, model_id, ch, log):
                off = base + min(rel, AUDIO_CHUNK_SECONDS)
                lines.append(f"[{fmt_hms(off)} | {_real_clock(live_start_epoch, off)}] {text}")
        return lines
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------
def build_header(event: Dict[str, Any], source_label: str) -> str:
    start = event.get("actual_start_epoch")
    dur = event.get("duration") or 0
    s_txt = datetime.fromtimestamp(start).strftime("%d/%m/%Y %H:%M:%S") if start else "N/D"
    e_txt = datetime.fromtimestamp(start + dur).strftime("%d/%m/%Y %H:%M:%S") if (start and dur) else "N/D"
    return "\n".join([
        f"NARRAÇÃO COMPLETA — {event.get('title', '')}",
        f"Canal: {event.get('channel_name', '')}  |  Vídeo: {event.get('url', '')}",
        f"Início da live: {s_txt}  |  Fim da live: {e_txt}  |  Duração: {fmt_hms(dur) if dur else 'N/D'}",
        f"Fonte da transcrição: {source_label}",
        f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "Formato: [tempo no vídeo | horário real] fala",
        "=" * 90,
    ])


def transcribe_event(event: Dict[str, Any], out_path: str, *, api_key: Any = None, model_id: str = "gemini-2.5-flash",
                     allow_audio: bool = True, log: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """
    Transcreve a live. Retorna {ok, source, path, lines, error, captions_missing}.
    allow_audio=False força apenas a tentativa por legendas (usado enquanto o VOD ainda está processando).
    """
    log = log or (lambda m: print(f"[NARRAÇÃO] {m}"))
    url = event.get("url") or f"https://www.youtube.com/watch?v={event.get('video_id')}"
    start = event.get("actual_start_epoch")
    result: Dict[str, Any] = {"ok": False, "source": "", "path": "", "lines": 0, "error": "", "captions_missing": False}

    lines: List[str] = []
    source_label = ""
    try:
        log("📝 Buscando legendas do YouTube...")
        lines, _ = fetch_caption_lines(url, start)
        if lines:
            source_label = "Legendas do YouTube"
            result["source"] = "youtube_captions"
    except Exception as ex:  # noqa: BLE001
        log(f"⚠️ Legendas indisponíveis: {str(ex)[:160]}")

    if not lines:
        result["captions_missing"] = True
        if not allow_audio:
            result["error"] = "Legendas ainda não disponíveis no YouTube."
            return result
        if not split_keys(api_key):
            result["error"] = "Sem legendas e sem chave do Gemini para transcrever o áudio."
            return result
        try:
            log("🔊 Sem legendas — transcrevendo o áudio com o Gemini (pode levar alguns minutos)...")
            lines = transcribe_audio_gemini(url, api_key, model_id, start, log)
            source_label = f"Áudio transcrito pelo Gemini ({model_id})"
            result["source"] = "gemini_audio"
        except Exception as ex:  # noqa: BLE001
            result["error"] = f"Falha na transcrição do áudio: {ex}"
            return result

    if not lines:
        result["error"] = "Transcrição vazia."
        return result

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(build_header(event, source_label) + "\n")
        f.write("\n".join(lines) + "\n")
    result.update(ok=True, path=out_path, lines=len(lines))
    log(f"✅ Narração salva ({len(lines)} trechos): {out_path}")
    return result


def read_narration_body(path: str) -> str:
    """Lê o .txt e devolve apenas as linhas de fala (sem o cabeçalho)."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    sep = "=" * 90
    return content.split(sep, 1)[1].strip() if sep in content else content
