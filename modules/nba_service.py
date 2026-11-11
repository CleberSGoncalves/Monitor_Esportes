"""
Módulo Oficial de Integração e Monitoramento da NBA.
Responsável por:
1. Coletar a agenda de jogos da NBA (passados, ao vivo e futuros) via ESPN NBA API.
2. Baixar e analisar o Game Book oficial da NBA (statsdmz.nba.com).
3. Extrair tempos exatos de cada quarto (1Q, 2Q, Halftime, 3Q, 4Q, OT), pontuação e estatísticas.
4. Orquestrar a geração de relatórios de auditoria para transmissões no Amazon Prime e Disney/ESPN.
"""

import os
import sys
import re
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NBA_CACHE_DIR = os.path.join(PROJECT_ROOT, "config", "nba_cache")
os.makedirs(NBA_CACHE_DIR, exist_ok=True)

# Mapeamento oficial de Tricodes dos times da NBA
NBA_TEAM_TIMEZONES = {
    # Eastern Time (America/New_York)
    "ATL": "America/New_York", "BOS": "America/New_York", "BKN": "America/New_York",
    "CHA": "America/New_York", "CLE": "America/New_York", "DET": "America/New_York",
    "IND": "America/New_York", "MIA": "America/New_York", "NYK": "America/New_York",
    "ORL": "America/New_York", "PHI": "America/New_York", "TOR": "America/Toronto",
    "WAS": "America/New_York",
    
    # Central Time (America/Chicago)
    "CHI": "America/Chicago", "DAL": "America/Chicago", "HOU": "America/Chicago",
    "MEM": "America/Chicago", "MIL": "America/Chicago", "MIN": "America/Chicago",
    "NOP": "America/Chicago", "OKC": "America/Chicago", "SAS": "America/Chicago",
    
    # Mountain Time (America/Denver)
    "DEN": "America/Denver", "UTA": "America/Denver",
    
    # Arizona / Phoenix (America/Phoenix - MST sem DST)
    "PHX": "America/Phoenix",
    
    # Pacific Time (America/Los_Angeles)
    "GSW": "America/Los_Angeles", "LAC": "America/Los_Angeles", "LAL": "America/Los_Angeles",
    "POR": "America/Los_Angeles", "SAC": "America/Los_Angeles",
}

NBA_TEAMS = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS"
}

# Emissoras oficiais monitoradas no projeto para NBA
BROADCASTER_MAPPING = {
    "PRIME": "Amazon Prime",
    "AMAZON": "Amazon Prime",
    "DISNEY": "Disney",
    "ESPN": "Disney",
    "STAR+": "Disney",
    "DISNEY+": "Disney"
}

class NBAService:
    @staticmethod
    def get_team_tricode(team_name: str) -> str:
        """Retorna o tricode de 3 letras do time da NBA (ex: Boston Celtics -> BOS)."""
        clean = (team_name or "").strip()
        if clean in NBA_TEAMS:
            return NBA_TEAMS[clean]
        for name, tri in NBA_TEAMS.items():
            if name.lower() in clean.lower() or clean.lower() in name.lower():
                return tri
            # Checa apenas o apelido (ex: Celtics)
            short = name.split()[-1]
            if short.lower() in clean.lower():
                return tri
        return clean[:3].upper()

    @classmethod
    def fetch_games_for_date(cls, date_str: str) -> List[Dict[str, Any]]:
        """
        Coleta todos os jogos da NBA para uma data específica (formato YYYYMMDD ou YYYY-MM-DD).
        Utiliza a ESPN Scoreboard API pública de altíssima velocidade.
        """
        date_clean = date_str.replace("-", "").strip()
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date_clean}"
        
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[NBA] Erro ao consultar ESPN Scoreboard para {date_clean}: {e}")
            return []

        games = []
        events = data.get("events", [])
        for ev in events:
            comp = ev.get("competitions", [{}])[0]
            competitors = comp.get("competitors", [])
            
            home_team = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away_team = next((c for c in competitors if c.get("homeAway") == "away"), {})

            home_name = home_team.get("team", {}).get("displayName", "Home Team")
            away_name = away_team.get("team", {}).get("displayName", "Away Team")
            
            home_tri = cls.get_team_tricode(home_name) or home_team.get("team", {}).get("abbreviation")
            away_tri = cls.get_team_tricode(away_name) or away_team.get("team", {}).get("abbreviation")

            home_score = home_team.get("score")
            away_score = away_team.get("score")

            status_type = ev.get("status", {}).get("type", {})
            status_desc = status_type.get("description", "Scheduled")
            status_state = status_type.get("state", "pre")  # pre, in, post
            
            # Formatação de Horário no Fuso de Brasília
            iso_utc = ev.get("date", "")
            brt_time_str = "Horário a confirmar"
            dt_game = None
            if iso_utc:
                try:
                    dt_utc = datetime.strptime(iso_utc.replace("Z", "+0000"), "%Y-%m-%dT%H:%M%z")
                    # Converte para UTC-3 (Brasília)
                    dt_brt = dt_utc.astimezone(timezone(timedelta(hours=-3)))
                    brt_time_str = dt_brt.strftime("%H:%M")
                    dt_game = dt_brt
                except Exception:
                    pass

            # Detectar Emissora e Plataformas de Transmissão Oficiais
            broadcasts = comp.get("broadcasts", [])
            broadcaster_raw = []
            raw_broadcast_str = ""
            for b in broadcasts:
                for b_name in b.get("names", []):
                    broadcaster_raw.append(b_name)
                    raw_broadcast_str += " " + b_name.upper()

            # Todo jogo da NBA possui transmissão garantida pelo NBA League Pass
            detected_platforms = ["NBA League Pass"]
            broadcaster_name = "NBA League Pass"

            if any(k in raw_broadcast_str for k in ["PRIME", "AMAZON"]):
                broadcaster_name = "Amazon Prime"
                if "Amazon Prime" not in detected_platforms:
                    detected_platforms.append("Amazon Prime")
            elif any(k in raw_broadcast_str for k in ["DISNEY", "STAR+"]):
                broadcaster_name = "Disney"
                if "Disney" not in detected_platforms:
                    detected_platforms.append("Disney")
            elif "ESPN" in raw_broadcast_str:
                broadcaster_name = "Disney"
                if "Disney" not in detected_platforms:
                    detected_platforms.append("Disney")
                if "ESPN" not in detected_platforms:
                    detected_platforms.append("ESPN")
            elif "ABC" in raw_broadcast_str:
                broadcaster_name = "Disney"
                if "Disney" not in detected_platforms:
                    detected_platforms.append("Disney")

            # URL determinística do Game Book oficial da NBA
            gamebook_filename = f"{date_clean}_{away_tri}{home_tri}_book.pdf"
            gamebook_url = f"https://statsdmz.nba.com/pdfs/{date_clean}/{gamebook_filename}"
            local_gamebook_path = os.path.join(NBA_CACHE_DIR, gamebook_filename)

            game_obj = {
                "id": ev.get("id"),
                "date_clean": date_clean,
                "date_display": dt_game.strftime("%d/%m/%Y") if dt_game else date_str,
                "time_brt": brt_time_str,
                "iso_utc": iso_utc,
                "match_display": f"{away_name} @ {home_name}",
                "away_team": away_name,
                "home_team": home_name,
                "away_tri": away_tri,
                "home_tri": home_tri,
                "away_score": away_score,
                "home_score": home_score,
                "score_display": f"{away_score} - {home_score}" if (away_score is not None and home_score is not None) else "—",
                "status": status_desc,
                "is_finished": (status_state == "post" or "FINAL" in status_desc.upper()) and (away_score is not None and home_score is not None) and not (away_score == 0 and home_score == 0) and not any(k in status_desc.upper() for k in ["POSTP", "CANCEL", "SUSP"]),
                "is_live": status_state == "in",
                "platform": broadcaster_name,
                "platforms": detected_platforms,
                "broadcasts_raw": broadcaster_raw,
                "gamebook_url": gamebook_url,
                "gamebook_filename": gamebook_filename,
                "local_gamebook_path": local_gamebook_path,
                "has_gamebook": os.path.exists(local_gamebook_path)
            }
            games.append(game_obj)

        return games

    @classmethod
    def download_gamebook(cls, game: Dict[str, Any], force: bool = False) -> Optional[str]:
        """Baixa o PDF oficial do Game Book da NBA de forma determinística."""
        local_path = game.get("local_gamebook_path")
        if not force and local_path and os.path.exists(local_path) and os.path.getsize(local_path) > 1000:
            return local_path

        url = game.get("gamebook_url")
        if not url:
            return None

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if len(data) < 1000:
                    return None
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(data)
                return local_path
        except Exception as e:
            print(f"[NBA] Gamebook ainda não disponível ou erro no download ({url}): {e}")
            return None

    @classmethod
    def parse_gamebook(cls, pdf_path: str, home_tri: str = "", date_clean: str = "") -> Dict[str, Any]:
        """
        Extrai todas as informações de auditoria técnica do PDF oficial do Game Book da NBA:
        - Duração total
        - Horários reais de início e término de cada quarto (1Q, 2Q, Halftime, 3Q, 4Q, OT)
        - Local, Árbitros, Público
        - Placar por quarto
        """
        if not os.path.exists(pdf_path):
            return {"error": "Arquivo PDF não encontrado."}

        parsed = {
            "game_duration": "N/D",
            "attendance": "N/D",
            "arena": "N/D",
            "officials": [],
            "periods": [],
            "score_by_period": {},
            "milestones": []
        }

        try:
            pages_text = []
            if pdfplumber is not None:
                with pdfplumber.open(pdf_path) as p:
                    pages_text = [page.extract_text() or "" for page in p.pages]
            elif fitz is not None:
                doc = fitz.open(pdf_path)
                pages_text = [page.get_text() or "" for page in doc]
            else:
                print("⚠️ [NBA] Nenhum parser de PDF disponível (pdfplumber ou pymupdf).")
                return parsed

            if not pages_text:
                return parsed

            full_text_p1 = pages_text[0]
            
            # 1. Duração e Público
            m_dur = re.search(r"Game Duration:\s*([\d:]+)", full_text_p1)
            if m_dur: parsed["game_duration"] = m_dur.group(1)

            m_att = re.search(r"Attendance:\s*(\d+)", full_text_p1)
            if m_att: parsed["attendance"] = m_att.group(1)

            m_off = re.search(r"Officials:\s*(.+)", full_text_p1)
            if m_off:
                parsed["officials"] = [o.strip() for o in m_off.group(1).split(",")]

            # 2. Local / Data na linha superior
            lines_p1 = full_text_p1.split("\n")
            if len(lines_p1) > 2:
                parsed["arena"] = lines_p1[2].strip()

            # 3. Identificar Home Team e Data da Partida para conversão precisa de Fuso Horário para BRT (Brasília / UTC-3)
            home_tri_found = home_tri
            date_clean_found = date_clean

            # Extração a partir do nome do arquivo (ex: 20261027_BKNBOS_book.pdf)
            m_fn = re.search(r"(\d{8})_([A-Z]{3})([A-Z]{3})_book\.pdf", os.path.basename(pdf_path))
            if m_fn:
                if not date_clean_found: date_clean_found = m_fn.group(1)
                if not home_tri_found: home_tri_found = m_fn.group(3)

            # Fallback pelo texto do Game Book (HOME: Time)
            if not home_tri_found:
                m_home = re.search(r"HOME:\s*([A-Za-z\s]+)", full_text_p1)
                if m_home:
                    home_tri_found = cls.get_team_tricode(m_home.group(1).split("(")[0].strip())

            arena_tz_name = NBA_TEAM_TIMEZONES.get(home_tri_found, "America/New_York")
            try:
                from zoneinfo import ZoneInfo
                home_tz = ZoneInfo(arena_tz_name)
                brt_tz = ZoneInfo("America/Sao_Paulo")
            except Exception:
                home_tz = None
                brt_tz = None

            y_dt, m_dt, d_dt = 2026, 10, 25
            if date_clean_found and len(date_clean_found) == 8 and date_clean_found.isdigit():
                y_dt = int(date_clean_found[:4])
                m_dt = int(date_clean_found[4:6])
                d_dt = int(date_clean_found[6:8])

            def _convert_local_to_brt(local_time_str: str) -> str:
                if not (home_tz and brt_tz):
                    return local_time_str
                try:
                    dt_loc = datetime.strptime(f"{y_dt}-{m_dt:02d}-{d_dt:02d} {local_time_str.strip().upper()}", "%Y-%m-%d %I:%M %p")
                    dt_aware = dt_loc.replace(tzinfo=home_tz)
                    dt_brt = dt_aware.astimezone(brt_tz)
                    return dt_brt.strftime("%H:%M:%S")
                except Exception:
                    return local_time_str

            period_events = []
            for txt in pages_text:
                for line in txt.split("\n"):
                    m_start = re.search(r"Start of Period\s*\(([\d:]+\s*(?:AM|PM))\)", line, re.I)
                    m_end = re.search(r"End of Period\s*\(([\d:]+\s*(?:AM|PM))\)", line, re.I)
                    
                    period_name = ""
                    if "1st QUARTER" in txt: period_name = "1º Quarto"
                    elif "2nd QUARTER" in txt: period_name = "2º Quarto"
                    elif "3rd QUARTER" in txt: period_name = "3º Quarto"
                    elif "4th QUARTER" in txt: period_name = "4º Quarto"
                    elif "OVERTIME" in txt or "OT" in txt: period_name = "Prorrogação (OT)"

                    if m_start:
                        raw_t = m_start.group(1)
                        t_brt = _convert_local_to_brt(raw_t)
                        period_events.append({
                            "type": "start",
                            "period": period_name,
                            "time": t_brt,
                            "time_brt": t_brt,
                            "time_local": raw_t,
                            "time_local_str": f"{raw_t} (Local)"
                        })
                    if m_end:
                        raw_t = m_end.group(1)
                        t_brt = _convert_local_to_brt(raw_t)
                        period_events.append({
                            "type": "end",
                            "period": period_name,
                            "time": t_brt,
                            "time_brt": t_brt,
                            "time_local": raw_t,
                            "time_local_str": f"{raw_t} (Local)"
                        })

                # Deduplicar e estruturar marcos em ordem cronológica
                seen = set()
                clean_periods = []
                for ev in period_events:
                    k = (ev["period"], ev["type"], ev["time"])
                    if k not in seen:
                        seen.add(k)
                        clean_periods.append(ev)

                parsed["milestones"] = clean_periods

        except Exception as e:
            parsed["error"] = f"Falha na extração do Game Book: {e}"

        return parsed

    @classmethod
    def set_game_platform(cls, game: Dict[str, Any], platform_name: str) -> None:
        """
        Define as plataformas auditadas do jogo, garantindo que o Game Book (NBA League Pass)
        seja sempre o marco #1 e a plataforma de streaming selecionada seja o marco secundário.
        """
        p_up = platform_name.upper()
        if "DISNEY + ESPN" in p_up:
            game["platform"] = "Disney"
            game["platforms"] = ["NBA League Pass", "Disney", "ESPN"]
        elif "DISNEY" in p_up:
            game["platform"] = "Disney"
            game["platforms"] = ["NBA League Pass", "Disney"]
        elif "AMAZON" in p_up or "PRIME" in p_up:
            game["platform"] = "Amazon Prime"
            game["platforms"] = ["NBA League Pass", "Amazon Prime"]
        elif "ESPN" in p_up:
            game["platform"] = "ESPN"
            game["platforms"] = ["NBA League Pass", "ESPN"]
        elif "LEAGUE" in p_up or "NBA" in p_up:
            game["platform"] = "NBA"
            game["platforms"] = ["NBA League Pass"]
        else:
            game["platform"] = platform_name
            game["platforms"] = ["NBA League Pass", platform_name]

