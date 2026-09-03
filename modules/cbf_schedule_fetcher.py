"""
Módulo Autônomo de Tabela Oficial da CBF para o Monitor de Esportes.
Tabela REAL baseada estritamente no recorte do PDF Oficial da CBF (EDIÇÃO 2026).

Regra Fundamental de Colunas da CBF:
  - BRASILEIRÃO SÉRRIE A:
      * Coluna 4 ➔ Amazon Prime (APENAS Coluna 4!)
      * Coluna 5 ➔ CazéTV / Youtube (APENAS Coluna 5!)
      * Colunas 1, 2, 3, 6, 7 ➔ IGNORAR TOTALMENTE (Premiere / SporTV / Globo)
  - COPA DO BRASIL:
      * Coluna 3 ou 4 ➔ Amazon Prime
"""

import os
import json
import re
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(PROJECT_ROOT, "config", "cbf_broadcaster_rules.json")
CACHE_PATH = os.path.join(PROJECT_ROOT, "config", "cbf_fixtures_cache.json")

def load_broadcaster_rules() -> dict:
    """Carrega as regras oficiais centralizadas do arquivo config/cbf_broadcaster_rules.json."""
    if os.path.exists(RULES_PATH):
        try:
            with open(RULES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def get_recent_finished_matches() -> list:
    """Retorna os jogos finalizados monitorados."""
    finished = [
        {
            "comp": "Brasileirão Série A",
            "team1": "Chapecoense",
            "team2": "São Paulo",
            "score": "1 x 0",
            "date": "23/08/2026",
            "time": "18:30",
            "platform": "CazéTV",
            "tag": "⚡ Auditoria Concluída"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Palmeiras",
            "team2": "Santos",
            "score": "3 x 0",
            "date": "26/08/2026",
            "time": "21:30",
            "platform": "CazéTV",
            "tag": "⚡ Auditoria Concluída"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Cruzeiro",
            "team2": "Flamengo",
            "score": "1 x 1",
            "date": "22/08/2026",
            "time": "21:00",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Internacional",
            "team2": "Grêmio",
            "score": "2 x 1",
            "date": "27/08/2026",
            "time": "21:30",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Vitória",
            "team2": "Vasco da Gama",
            "score": "1 x 0",
            "date": "02/09/2026",
            "time": "21:30",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Santos",
            "team2": "Palmeiras",
            "score": "0 x 0",
            "date": "02/09/2026",
            "time": "21:30",
            "platform": "Amazon Prime",
            "tag": "⚡ Auditoria Concluída"
        }
    ]
    return finished


def get_real_cbf_fixtures() -> list:
    """
    Retorna estritamente os jogos monitorados que possuem marcação nas colunas:
    - Brasileirão Série A: Coluna 4 (Amazon Prime) ou Coluna 5 (CazéTV).
    - Copa do Brasil: Coluna 3 (Amazon Prime).
    Conforme imagem oficial do PDF da CBF.
    """
    fixtures = [
        # 03/09 (qui) 20:00 - Copa do Brasil (Coluna 3 = Amazon Prime)
        {
            "comp": "Copa do Brasil",
            "team1": "Grêmio",
            "team2": "Internacional",
            "date": "03/09/2026",
            "time": "20:00",
            "platform": "Amazon Prime",
            "tag": "🏆 Decisivo (Copa do Brasil)"
        },
        # 06/09 (dom) 18:30 - Brasileirão Série A (Coluna 5 = CazéTV)
        {
            "comp": "Brasileirão Série A",
            "team1": "Botafogo",
            "team2": "Palmeiras",
            "date": "06/09/2026",
            "time": "18:30",
            "platform": "CazéTV",
            "tag": "📺 Transmissão Exclusiva (CazéTV - Coluna 5)"
        },
        # 06/09 (dom) 19:30 - Brasileirão Série A (Coluna 4 = Amazon Prime)
        {
            "comp": "Brasileirão Série A",
            "team1": "Corinthians",
            "team2": "Chapecoense",
            "date": "06/09/2026",
            "time": "19:30",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Coluna 4)"
        },
        # 12/09 (sáb) 17:00 - Brasileirão Série A (Coluna 5 = CazéTV)
        {
            "comp": "Brasileirão Série A",
            "team1": "Chapecoense",
            "team2": "Internacional",
            "date": "12/09/2026",
            "time": "17:00",
            "platform": "CazéTV",
            "tag": "📺 Transmissão Exclusiva (CazéTV - Coluna 5)"
        },
        # 12/09 (sáb) 20:30 - Brasileirão Série A (Coluna 4 = Amazon Prime)
        {
            "comp": "Brasileirão Série A",
            "team1": "Botafogo",
            "team2": "Red Bull Bragantino",
            "date": "12/09/2026",
            "time": "20:30",
            "platform": "Amazon Prime",
            "tag": "⭐ Transmissão Exclusiva (Amazon Prime - Coluna 4)"
        },
        # 19/09 (sáb) 17:00 - Brasileirão Série A (Coluna 5 = CazéTV)
        {
            "comp": "Brasileirão Série A",
            "team1": "Mirassol",
            "team2": "Botafogo",
            "date": "19/09/2026",
            "time": "17:00",
            "platform": "CazéTV",
            "tag": "📺 Transmissão Exclusiva (CazéTV - Coluna 5)"
        },
        # 19/09 (sáb) 20:30 - Brasileirão Série A (Coluna 4 = Amazon Prime)
        {
            "comp": "Brasileirão Série A",
            "team1": "Vasco da Gama",
            "team2": "Coritiba",
            "date": "19/09/2026",
            "time": "20:30",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Coluna 4)"
        }
    ]

    def parse_dt(g):
        try:
            return datetime.strptime(f"{g.get('date', '')} {g.get('time', '')}", "%d/%m/%Y %H:%M")
        except:
            return datetime.max

    fixtures.sort(key=parse_dt)
    return fixtures


class CBFScheduleFetcher:
    """Motor de Tabela Oficial da CBF para o Monitor Esportes."""

    @staticmethod
    def get_upcoming_matches(force_refresh: bool = True) -> list:
        """
        Retorna estritamente os próximos 5 jogos oficiais futuros da CBF
        filtrados unicamente pelas Colunas 4 e 5 (Brasileirão) e Coluna 3 (Copa do Brasil).
        """
        today = datetime.now()
        fixtures = get_real_cbf_fixtures()
        
        # Salvar cache limpo
        try:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(fixtures, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # Filtrar confrontos com data/hora >= agora (com 2 horas de tolerância)
        filtered = []
        for g in fixtures:
            try:
                g_dt = datetime.strptime(f"{g.get('date')} {g.get('time')}", "%d/%m/%Y %H:%M")
                if g_dt >= today - timedelta(hours=2):
                    filtered.append(g)
            except:
                filtered.append(g)

        if len(filtered) < 5:
            return fixtures[:5]

        return filtered[:5]

    @staticmethod
    def get_recent_finished_matches() -> list:
        return get_recent_finished_matches()

    @staticmethod
    def save_cache(fixtures: list) -> None:
        try:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(fixtures, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
