# modules/youtube_api_v3.py
import requests
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

class YouTubeAPIv3:
    """
    Interface oficial com a API do YouTube v3.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"

    def get_channel_id(self, handle: str) -> Optional[str]:
        """Resolve um handle (ex: @CazeTV) para um ID de canal."""
        if not handle.startswith("@"):
            handle = "@" + handle
            
        url = f"{self.base_url}/channels?part=id&forHandle={handle}&key={self.api_key}"
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            if "items" in data and len(data["items"]) > 0:
                return data["items"][0]["id"]
        elif res.status_code == 403:
            raise PermissionError("YouTube API desativada no console do Google. Ative em: https://console.developers.google.com/apis/api/youtube.googleapis.com/overview")
        return None

    def get_events(self, channel_id: str, limit: int = 150, published_after: Optional[str] = None, published_before: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca eventos de um canal com metadados exaustivos (actualStartTime e durations).
        Suporta paginação para ultrapassar o limite de 50 resultados da API.
        """
        video_ids = []
        # Tipos de eventos para buscar
        # Nota: 'completed' e 'live' são os mais importantes para VODs e transmissões atuais
        # 'none' busca por vídeos regulares (uploads)
        for event_type in ["live", "upcoming", "completed", "none"]:
            next_page_token = None
            type_ids = []
            
            while len(type_ids) < limit:
                # maxResults por página é 50
                page_size = min(50, limit - len(type_ids))
                url = (
                    f"{self.base_url}/search?part=id&channelId={channel_id}"
                    f"&type=video&order=date&maxResults={page_size}"
                    f"&key={self.api_key}"
                )
                if event_type != "none":
                    url += f"&eventType={event_type}"
                
                if published_after:
                    url += f"&publishedAfter={published_after}"
                if published_before:
                    url += f"&publishedBefore={published_before}"
                if next_page_token:
                    url += f"&pageToken={next_page_token}"
                    
                res = requests.get(url)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("items") or []
                    ids = [it["id"]["videoId"] for it in items]
                    type_ids.extend(ids)
                    
                    next_page_token = data.get("nextPageToken")
                    if not next_page_token or not items:
                        break
                elif res.status_code == 403:
                    raise PermissionError("YouTube API desativada ou quota excedida.")
                else:
                    break
                    
            video_ids.extend(type_ids)

        if not video_ids:
            return []

        # Remover duplicatas mantendo ordem
        seen = set()
        unique_ids = [x for x in video_ids if not (x in seen or seen.add(x))]
        
        # Buscar Detalhes Reais (parts: snippet, liveStreamingDetails, contentDetails)
        # Processamos em lotes de 50 (limite da API)
        events = []
        for i in range(0, len(unique_ids), 50):
            batch = unique_ids[i:i+50]
            ids_str = ",".join(batch)
            url_v = (
                f"{self.base_url}/videos?part=snippet,liveStreamingDetails,contentDetails"
                f"&id={ids_str}&key={self.api_key}"
            )
            res_v = requests.get(url_v)
            if res_v.status_code == 200:
                items_v = res_v.json().get("items") or []
                for item in items_v:
                    v_id = item["id"]
                    snippet = item["snippet"]
                    live_details = item.get("liveStreamingDetails") or {}
                    content_details = item.get("contentDetails") or {}
                    
                    # TIMESTAMPS PRECISOS
                    # Prioridade: actualStartTime > scheduledStartTime > publishAt
                    actual_start = live_details.get("actualStartTime")
                    scheduled_start = live_details.get("scheduledStartTime")
                    published_at = snippet.get("publishedAt")
                    
                    # Converter ISO8601 -> Timestamp (int) se possível
                    def _iso_to_ts(iso_str):
                        if not iso_str: return None
                        try:
                            # Tenta converter '2026-03-22T20:30:00Z'
                            dt = datetime.strptime(iso_str.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                            return int(dt.timestamp())
                        except: return None

                    ts = _iso_to_ts(actual_start) or _iso_to_ts(scheduled_start) or _iso_to_ts(published_at)
                    
                    # Duração (ISO8601 ex: PT3H50M10S)
                    iso_dur = content_details.get("duration")
                    def _iso_dur_to_sec(iso_duration):
                        if not iso_duration: return 0
                        import re
                        dur_match = re.search(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
                        if not dur_match: return 0
                        h = int(dur_match.group(1) or 0)
                        m = int(dur_match.group(2) or 0)
                        s = int(dur_match.group(3) or 0)
                        return h * 3600 + m * 60 + s

                    duration_sec = _iso_dur_to_sec(iso_dur)
                    
                    # Status Humano
                    st_val = snippet.get("liveBroadcastContent", "none")
                    if st_val == "live": status = "live"
                    elif st_val == "upcoming": status = "upcoming"
                    else: status = "ended"

                    events.append({
                        "id": v_id,
                        "title": snippet["title"],
                        "url": f"https://www.youtube.com/watch?v={v_id}",
                        "thumbnail": snippet["thumbnails"].get("high", snippet["thumbnails"].get("default"))["url"],
                        "status": status,
                        "timestamp": ts,
                        "release_timestamp": ts,
                        "actual_start_time": actual_start,
                        "scheduled_start": actual_start or scheduled_start or published_at,
                        "duration": duration_sec,
                        "duration_string": iso_dur,
                        "view_count": item.get("statistics", {}).get("viewCount"),
                    })
        return events

def get_official_events(api_key: str, channel_url: str, limit: int = 250, published_after: Optional[str] = None, published_before: Optional[str] = None) -> List[Dict[str, Any]]:
    """Helper compatível com a interface antiga."""
    api = YouTubeAPIv3(api_key)
    
    # Extrair handle da URL (ex: https://www.youtube.com/@CazeTV/streams -> @CazeTV)
    import re
    match = re.search(r"(@[A-Za-z0-9_-]+)", channel_url)
    if not match:
        raise ValueError("URL do canal não contém um handle @ (necessário para a API Oficial).")
    
    handle = match.group(1)
    channel_id = api.get_channel_id(handle)
    if not channel_id:
        raise ValueError(f"Não foi possível resolver o ID do canal para o handle {handle}.")
        
    return api.get_events(channel_id, limit, published_after, published_before)

