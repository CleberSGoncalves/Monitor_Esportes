# -*- coding: utf-8 -*-
"""
Serviço de busca, parsing e validação de transmissões ao vivo de canais do YouTube.
Valida estritamente se o confronto extraído existe na tabela oficial da CBF.
"""

import re
import logging
import unicodedata
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple

import yt_dlp

from .sharepoint_client import _deep_normalize_partida
from .cbf_pdf_service import (
    get_cbf_rights_index,
    is_cbf_broadcast_authorized,
    prettify_match_name
)

logger = logging.getLogger(__name__)

class _QuietLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

SEP_RE = re.compile(r"\s*(?:\||-|–|—|·|•|/|\[|\]|\(|\))\s*")
BRASILEIRAO_RE = re.compile(r"brasileir[aã]o\s*(\d{4})?", re.I)
COPA_MUNDO_RE = re.compile(r"copa do mundo\s*(fifa)?\s*(\d{4})?", re.I)
RODADA_RE = re.compile(r"(\d{1,2})\s*(?:ª|a)?\s*rodad[ao]\b", re.I)
PAULISTA_RE = re.compile(r"(campeonato\s+paulista|paulist[aã]o)\s*(\d{4})?", re.I)

YOUTUBE_PROGRAM_BLACKLIST = [
    'roda de bobo', 'pos-jogo', 'pós-jogo', 'pos jogo', 'pós jogo',
    'pre-jogo', 'pré-jogo', 'pre jogo', 'pré jogo',
    'resenha', 'react', 'podcast', 'bastidores', 'coletiva', 'debate',
    'mesa redonda', 'aquecimento', 'zona mista', 'melhores momentos',
    'highlights', 'compacto', 'gols da rodada', 'entrevista', 'sem imagens', 'sem imagem'
]

def norm(txt: str) -> str:
    """Normaliza texto para comparações seguras."""
    if not txt:
        return ""
    t = unicodedata.normalize("NFKD", txt)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    t = t.lower().strip()
    t = re.sub(r"^\s*ao vivo[:\- ]*\s*", "", t)
    return re.sub(r"\s+", " ", t)

def limpar_time_yt(t: str) -> str:
    """Remove ruídos comuns de títulos do YouTube."""
    if not t:
        return ""
    t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', t)
    noise = [
        r'\bao vivo\b', r'\bcom imagens\b', r'\bcom imagem\b',
        r'\btransmissao ao vivo\b', r'\btransmissao\b', r'\btransmissão\b',
        r'\bhd\b', r'\b4k\b', r'\b1080p\b', r'\bexclusivo\b', r'\bdireto\b', r'\bfull hd\b'
    ]
    for n in noise:
        t = re.sub(n, ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'[^\w\s\-\.]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()

def extrair_partida_youtube(titulo_full: str) -> Optional[str]:
    """Extrai confronto 'Time A x Time B' do título do YouTube descartando programas de estúdio."""
    if not titulo_full:
        return None
    t_lower = titulo_full.lower()
    for b in YOUTUBE_PROGRAM_BLACKLIST:
        if b in t_lower:
            return None

    partes = re.split(r'[|–—]', titulo_full)
    for p in partes:
        p_clean = re.sub(r'^(?:ao vivo(?:\s*com\s*imagens)?|com imagens|transmissao ao vivo)[:\s-]*', '', p.strip(), flags=re.IGNORECASE).strip()
        if re.search(r'\s+[xXvV]\s+|\s+vs\s+|\s+contra\s+', p_clean):
            subparts = re.split(r'\s+[xXvV]\s+|\s+vs\s+|\s+contra\s+', p_clean, maxsplit=1)
            if len(subparts) == 2:
                t1 = limpar_time_yt(subparts[0])
                t2 = limpar_time_yt(subparts[1])
                if len(t1) >= 2 and len(t2) >= 2:
                    return prettify_match_name(f'{t1} x {t2}')
    return None

def parse_youtube_title(raw_title: str, raw_desc: str = "") -> Dict[str, Any]:
    """Identifica campeonato, ano e rodada de live do YouTube."""
    t = norm(raw_title)
    d = norm(raw_desc)

    for b in YOUTUBE_PROGRAM_BLACKLIST:
        if b in t:
            return {
                "is_brasileirao": False,
                "is_copa_mundo": False,
                "is_paulista": False,
                "is_libertadores": False,
                "is_sudamericana": False,
                "is_copa_brasil": False,
                "is_carioca": False,
                "is_bundesliga": False,
                "year": None,
                "rodada": None
            }

    tokens = SEP_RE.split(t) + [t]
    year = None
    rodada = None

    for tok in tokens:
        m = re.search(r"\b(20\d{2})\b", tok)
        if m:
            year = int(m.group(1))
            break

    for tok in tokens:
        m = RODADA_RE.search(tok)
        if m:
            try:
                rodada = int(m.group(1))
                break
            except Exception:
                pass

    is_brasileirao = bool(BRASILEIRAO_RE.search(t) or BRASILEIRAO_RE.search(d))
    is_copa_mundo = bool(COPA_MUNDO_RE.search(t) or COPA_MUNDO_RE.search(d))
    is_paulista = bool(PAULISTA_RE.search(t) or PAULISTA_RE.search(d))
    is_libertadores = "libertadores" in t or "libertadores" in d
    is_sudamericana = "sudamericana" in t or "sul-americana" in t or "sudamericana" in d
    is_copa_brasil = "copa do brasil" in t or "copa do brasil" in d
    is_carioca = "carioca" in t or "cariocao" in t
    is_bundesliga = "bundesliga" in t

    return {
        "is_brasileirao": is_brasileirao,
        "is_copa_mundo": is_copa_mundo,
        "is_paulista": is_paulista,
        "is_libertadores": is_libertadores,
        "is_sudamericana": is_sudamericana,
        "is_copa_brasil": is_copa_brasil,
        "is_carioca": is_carioca,
        "is_bundesliga": is_bundesliga,
        "year": year,
        "rodada": rodada
    }

def obter_eventos_canal_youtube(
    canal_nome: str,
    canal_url: str,
    data_inicio_obj: Optional[datetime] = None,
    cbf_idx: Optional[Dict[str, Any]] = None
) -> List[Tuple[Any, ...]]:
    """
    Busca eventos agendados no YouTube via yt-dlp e valida na tabela oficial CBF.
    Retorna tuplas prontas para o Treeview / SharePoint:
    (campeonato, partida_bonita, data_str, hora_str, "Esquerda", 15, canal_nome, vid_url)
    """
    if cbf_idx is None:
        cbf_idx = get_cbf_rights_index()

    if data_inicio_obj is None:
        data_inicio_obj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    eventos = []
    seen = set()

    urls_para_consultar = []
    base_clean = canal_url.strip().rstrip('/')
    if not base_clean.endswith('/streams'):
        urls_para_consultar.append(base_clean + '/streams')
    urls_para_consultar.append(base_clean)

    ydl_opts_list = {
        'quiet': True, 'no_warnings': True, 'skip_download': True,
        'extract_flat': True, 'playlistend': 15, 'ignoreerrors': True,
        'socket_timeout': 8,
        'logger': _QuietLogger(),
    }

    ydl_opts_video = {
        'quiet': True, 'no_warnings': True, 'skip_download': True,
        'ignore_no_formats_error': True, 'extractor_retries': 1,
        'socket_timeout': 6,
        'logger': _QuietLogger(),
    }

    for target_url in urls_para_consultar:
        try:
            with yt_dlp.YoutubeDL(ydl_opts_list) as ydll:
                info = ydll.extract_info(target_url, download=False) or {}
            entries = info.get('entries') or []
            if not entries:
                continue

            for entry in entries:
                vid_id = entry.get('id')
                vid_url = (
                    entry.get('url')
                    or entry.get('webpage_url')
                    or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else None)
                )
                if not vid_url or vid_url in seen:
                    continue
                seen.add(vid_url)

                titulo_raw = (entry.get('title') or '').strip()
                if not titulo_raw:
                    continue

                partida_extraida = extrair_partida_youtube(titulo_raw)
                if not partida_extraida:
                    continue

                p_norm = _deep_normalize_partida(partida_extraida)
                in_bsa = p_norm in cbf_idx.get('brasileirao', {})
                in_cdb = p_norm in cbf_idx.get('copa_do_brasil', {})

                if not (in_bsa or in_cdb):
                    logger.info(
                        f"[YouTube Scanner] Jogo '{partida_extraida}' ({canal_nome}) descartado: "
                        "não consta na tabela oficial da CBF."
                    )
                    continue

                camp_atribuido = "Brasileirão serie A" if in_bsa else "Copa do Brasil"

                try:
                    with yt_dlp.YoutubeDL(ydl_opts_video) as ydv:
                        vinfo = ydv.extract_info(vid_url, download=False) or {}
                except Exception:
                    vinfo = {}

                ts = (
                    vinfo.get('scheduled_start_time')
                    or vinfo.get('release_timestamp')
                    or vinfo.get('timestamp')
                )

                if ts:
                    try:
                        dt_utc = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                        dt_local = dt_utc.astimezone().replace(tzinfo=None)
                    except Exception:
                        dt_local = datetime.now()
                else:
                    ds = vinfo.get('release_date') or vinfo.get('upload_date')
                    if ds and len(ds) == 8:
                        try:
                            dt_local = datetime.strptime(ds, '%Y%m%d')
                        except Exception:
                            dt_local = datetime.now()
                    else:
                        dt_local = datetime.now()

                if dt_local.replace(hour=0, minute=0, second=0, microsecond=0) < data_inicio_obj:
                    continue

                data_formatada = dt_local.strftime('%d/%m/%Y')
                hora_formatada = dt_local.strftime('%H:%M') if ts else "19:00"
                partida_bonita = prettify_match_name(partida_extraida)

                evento_tuple = (
                    camp_atribuido,
                    partida_bonita,
                    data_formatada,
                    hora_formatada,
                    "Esquerda",
                    15,
                    canal_nome,
                    vid_url
                )
                eventos.append(evento_tuple)
        except Exception as e:
            logger.warning(f"[YouTube Scanner] Erro ao escanear {target_url}: {e}")

    return eventos

def obter_eventos_caze_tv(data_inicio_obj: Optional[datetime] = None) -> List[Tuple[Any, ...]]:
    """Scanner especializado para o canal CazéTV."""
    return obter_eventos_canal_youtube(
        canal_nome="Cazé TV",
        canal_url="https://www.youtube.com/@CazeTV/streams",
        data_inicio_obj=data_inicio_obj
    )
