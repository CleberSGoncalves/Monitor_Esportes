# modules/youtube_events.py
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional


def _run_yt_dlp(args: List[str]) -> Dict[str, Any]:
    import yt_dlp
    
    # Extrair url do final do args
    url = args[-1]
    
    # Mapear args para ydl_opts
    ydl_opts = {
        'extract_flat': True,
        'playlistend': 100,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'skip_download': True,
    }
    
    # Tratar dateafter / datebefore se presentes no args
    for i in range(len(args)):
        if args[i] == "--dateafter" and i + 1 < len(args):
            ydl_opts['dateafter'] = args[i+1]
        elif args[i] == "--datebefore" and i + 1 < len(args):
            ydl_opts['datebefore'] = args[i+1]
            
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise RuntimeError("yt-dlp retornou saída vazia.")
        return info


def _ts_to_local_str(ts: Optional[int]) -> Optional[str]:
    if not ts:
        return None
    return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")


import concurrent.futures

def get_channel_events(channel_url: str, limit: int = 100, date_after: Optional[str] = None, date_before: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Escaneia eventos de um canal usando execução paralela para múltiplas abas.
    """
    urls_to_scan = [channel_url.strip()]
    
    if ("@" in channel_url or "channel/" in channel_url or "user/" in channel_url or "c/" in channel_url):
        base = channel_url.strip().split("/streams")[0].split("/videos")[0].split("/live")[0].split("/search")[0].rstrip("/")
        urls_to_scan = [
            f"{base}/streams",
            f"{base}/videos",
            f"{base}/search?query=jogo+completo"
        ]

    all_results: List[Dict[str, Any]] = []
    seen_ids = set()

    def _scan_single_url(scan_url: str) -> List[Dict[str, Any]]:
        page_results = []
        try:
            yt_args = [
                "--flat-playlist",
                "--playlist-end", "100",
            ]
            if date_after:
                # yt-dlp espera YYYYMMDD
                yt_args.extend(["--dateafter", date_after.replace("-", "").replace("/", "")])
            if date_before:
                yt_args.extend(["--datebefore", date_before.replace("-", "").replace("/", "")])
                
            yt_args.append(scan_url)
            
            data = _run_yt_dlp(yt_args)
            entries = data.get("entries") or []
            for e in entries:
                if not e: continue
                vid = e.get("id")
                if not vid: continue
                
                title = (e.get("title") or "").strip()
                live_status = (e.get("live_status") or "").lower()
                
                # BUSCA POR TIMESTAMPS PRECISOS
                # actual_start_time: Quando a live começou de fato
                # timestamp: Upload inicial
                # release_timestamp: Lançamento público
                actual_start = e.get("actual_start_time")
                release_ts = e.get("release_timestamp")
                upload_ts = e.get("timestamp")
                
                # Âncora: Prioridade absoluta para o início real da live
                ts = actual_start or release_ts or upload_ts

                if live_status in ("is_live", "live"):
                    status = "live"
                elif live_status in ("is_upcoming", "upcoming"):
                    status = "upcoming"
                elif live_status in ("was_live", "post_live"):
                    status = "ended"
                else:
                    status = "video"

                dur = e.get("duration")
                dur_str = e.get("duration_string")
                if not dur_str and dur:
                    try:
                        d = int(float(dur))
                        h, m, s = d // 3600, (d % 3600) // 60, d % 60
                        dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
                    except: pass

                page_results.append({
                    "id": vid,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "status": status,
                    "scheduled_start": _ts_to_local_str(ts),
                    "release_timestamp": ts,  # Mantemos o nome da chave p/ compatibilidade
                    "actual_start_time": actual_start,
                    "duration": dur,
                    "duration_string": dur_str,
                    "view_count": e.get("view_count"),
                })
        except Exception as ex:
            print(f"[YT SCAN WARN] Erro ao escanear {scan_url}: {ex}")
        return page_results

    # Execução Paralela
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls_to_scan)) as executor:
        futures = [executor.submit(_scan_single_url, u) for u in urls_to_scan]
        for future in concurrent.futures.as_completed(futures):
            res_list = future.result()
            for r in res_list:
                if r["id"] not in seen_ids:
                    seen_ids.add(r["id"])
                    all_results.append(r)

    # Ordenação: Live > Upcoming > Ended/Video (por data)
    def sort_score(x):
        st = x.get("status")
        base_ts = x.get("release_timestamp") or 0
        prio = 100 if st == "live" else (50 if st == "upcoming" else 0)
        return (prio, base_ts)

    all_results.sort(key=sort_score, reverse=True)
    return all_results[:limit]