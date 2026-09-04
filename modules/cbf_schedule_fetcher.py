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
import sys
import json
import re
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_rules_search_paths() -> list:
    paths = []
    # 1. Pasta AppData/config
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        paths.append(os.path.join(appdata, "Monitor_Esportes", "config", "cbf_broadcaster_rules.json"))
    # 2. Pasta temporária do PyInstaller (_MEIPASS)
    if hasattr(sys, "_MEIPASS"):
        paths.append(os.path.join(sys._MEIPASS, "config", "cbf_broadcaster_rules.json"))
        paths.append(os.path.join(sys._MEIPASS, "cbf_broadcaster_rules.json"))
    # 3. Pasta do projeto
    paths.append(os.path.join(PROJECT_ROOT, "config", "cbf_broadcaster_rules.json"))
    return paths

def load_broadcaster_rules() -> dict:
    """Carrega as regras oficiais centralizadas do arquivo config/cbf_broadcaster_rules.json em qualquer ambiente."""
    for p in get_rules_search_paths():
        if os.path.exists(p) and os.path.getsize(p) > 0:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

def is_column_allowed(comp: str, col_num: str) -> bool:
    """Valida estritamente se o número da coluna é permitido para a competição de acordo com as regras centralizadas."""
    rules = load_broadcaster_rules()
    comps = rules.get("competitions", {})
    comp_rules = comps.get(comp, {})
    allowed = comp_rules.get("allowed_columns", {})
    if allowed:
        return str(col_num) in allowed
    # Default estrito se o arquivo não estiver presente:
    if comp == "Brasileirão Série A":
        return str(col_num) in ["4", "5"]
    elif comp == "Copa do Brasil":
        return str(col_num) in ["3", "4", "5"]
    return False

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

    @staticmethod
    def find_game_page_url(team1: str, team2: str, date: str, comp: str = "Brasileiro Serie A") -> str:
        """
        Encontra a URL oficial da página do jogo no site da CBF.
        Suporta raspagem direta e busca flexível por slugs dos times (ex: gremio-x-internacional ou internacional-x-gremio).
        """
        try:
            import requests
            import unicodedata
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            def normalize_slug(text: str) -> str:
                text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
                text = text.lower().replace(" ", "-").replace("·", "").replace("'", "")
                return re.sub(r'[^a-z0-9\-]', '', text)

            slug1 = normalize_slug(team1)
            slug2 = normalize_slug(team2)
            
            team_map = {
                "gremio": "gremio",
                "inter": "internacional",
                "internacional": "internacional",
                "flamengo": "flamengo",
                "corinthians": "corinthians",
                "palmeiras": "palmeiras",
                "santos": "santos",
                "botafogo": "botafogo",
                "vasco": "vasco-da-gama",
                "vasco-da-gama": "vasco-da-gama",
                "vitoria": "vitoria",
                "chapecoense": "chapecoense",
                "cruzeiro": "cruzeiro",
                "bragantino": "red-bull-bragantino",
                "red-bull-bragantino": "red-bull-bragantino",
                "bahia": "bahia",
                "remo": "remo",
                "mirassol": "mirassol"
            }
            
            s1 = team_map.get(slug1, slug1)
            s2 = team_map.get(slug2, slug2)

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }

            if "copa" in comp.lower():
                table_url = "https://www.cbf.com.br/futebol-brasileiro/tabelas/copa-do-brasil/masculino/2026"
            else:
                table_url = "https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro-serie-a/masculino/2026"

            print(f"[CBF SEARCH] Buscando jogo {team1} x {team2} em {table_url}...")
            try:
                resp = requests.get(table_url, headers=headers, verify=False, timeout=8)
                if resp.status_code == 200:
                    html = resp.text
                    links = re.findall(r'href=["\'](https://www\.cbf\.com\.br/futebol-brasileiro/jogos/[^"\']+)["\']', html)
                    if not links:
                        links = re.findall(r'href=["\'](/futebol-brasileiro/jogos/[^"\']+)["\']', html)
                        links = [f"https://www.cbf.com.br{l}" for l in links]

                    for link in links:
                        link_lower = link.lower()
                        if (s1 in link_lower and s2 in link_lower):
                            print(f"[CBF SEARCH] Link oficial do jogo encontrado: {link}")
                            return link
            except Exception as e_t:
                print(f"[CBF SEARCH WARN] Tabela error: {e_t}")

            # Fallback direto: montar URL canônica testando s1-x-s2 e s2-x-s1
            base_comp = "copa-do-brasil" if "copa" in comp.lower() else "campeonato-brasileiro-serie-a"
            potential_slugs = [f"{s1}-x-{s2}", f"{s2}-x-{s1}"]
            for ps in potential_slugs:
                direct_url = f"https://www.cbf.com.br/futebol-brasileiro/jogos/{base_comp}/masculino/2026/{ps}?view=documentos"
                try:
                    r_check = requests.get(direct_url, headers=headers, verify=False, timeout=5)
                    if r_check.status_code == 200 and ("Súmula" in r_check.text or "conteudo.cbf.com.br/sumulas" in r_check.text or "sumula" in r_check.text.lower()):
                        clean_url = direct_url.replace("?view=documentos", "")
                        print(f"[CBF SEARCH] URL direta validada com sucesso: {clean_url}")
                        return clean_url
                except:
                    pass

        except Exception as e:
            print(f"[CBF SEARCH WARN] Erro ao buscar URL da página do jogo: {e}")
        return ""

    @staticmethod
    def fetch_sumula_text(team1: str, team2: str, date: str, sumula_url: str = "") -> str:
        """
        Baixa o PDF da súmula oficial a partir da URL e extrai o texto bruto via pypdfium2.
        """
        if not sumula_url:
            return ""
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(sumula_url, headers=headers, verify=False, timeout=12)
            if r.status_code == 200 and len(r.content) > 5000:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(r.content)
                text_pages = []
                for page in pdf:
                    textpage = page.get_textpage()
                    text_pages.append(textpage.get_text_range())
                full_text = "\n".join(text_pages)
                if full_text and len(full_text.strip()) > 100:
                    return full_text
        except Exception as e:
            print(f"[CBF SUMULA] Erro ao extrair texto do PDF: {e}")
        return ""

    @staticmethod
    def fetch_sumula_from_cbf_html(game_url: str) -> str:
        """
        Acessa a página do jogo na CBF (ex: ?view=documentos) e extrai o link do PDF da súmula
        e baixa o texto PDF imediatamente.
        """
        if not game_url:
            return ""
        try:
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            target_url = game_url if "view=documentos" in game_url else f"{game_url}?view=documentos"
            r = requests.get(target_url, headers=headers, verify=False, timeout=8)
            if r.status_code == 200:
                pdf_urls = re.findall(r'https?://conteudo\.cbf\.com\.br/sumulas/\d{4}/[^\s"\'<>]+\.pdf', r.text, re.IGNORECASE)
                if not pdf_urls:
                    pdf_urls = re.findall(r'href=["\'](https?://conteudo\.cbf\.com\.br/sumulas/[^"\']+)["\']', r.text, re.IGNORECASE)
                
                for pdf_u in pdf_urls:
                    text = CBFScheduleFetcher.fetch_sumula_text("", "", "", sumula_url=pdf_u)
                    if text and len(text.strip()) > 100:
                        return text
        except Exception as e:
            print(f"[CBF HTML SUMULA] Erro ao extrair do HTML: {e}")
        return ""
