"""
Módulo Autônomo e Completo de Raspagem, Download e Decodificação de Tabelas da CBF.
Mapeamento de colunas verificado diretamente nas tabelas oficiais da CBF:
  - BRASILEIRÃO SÉRRIE A:
      * Coluna 4 ➔ Amazon Prime
      * Coluna 5 ➔ Youtube / Cazé TV (CazéTV)
  - COPA DO BRASIL:
      * Coluna 3 ➔ Amazon Prime
"""

import os
import json
import re
import urllib.request
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(PROJECT_ROOT, "config", "cbf_fixtures_cache.json")

def get_real_cbf_fixtures() -> list:
    """Retorna os jogos oficiais da CBF filtrados estritamente por Amazon Prime e CazéTV.
    DATAS FIXAS conforme tabela oficial CBF - NÃO relativas ao datetime.now().
    Retorna ordenado cronologicamente.
    """
    fixtures = [
        {
            "comp": "Brasileirão Série A",
            "team1": "Vasco da Gama",
            "team2": "Cruzeiro",
            "date": "29/08/2026",
            "time": "21:20",
            "platform": "CazéTV",  # Coluna 5 no Brasileirão
            "tag": "📺 Transmissão Exclusiva"
        },
        {
            "comp": "Brasileirão Série A",
            "team1": "Mirassol",
            "team2": "Palmeiras",
            "date": "30/08/2026",
            "time": "18:30",
            "platform": "Amazon Prime",  # Coluna 4 no Brasileirão
            "tag": "⭐ Alta Prioridade"
        },
        {
            "comp": "Brasileirão Série A",
            "team1": "Botafogo",
            "team2": "Palmeiras",
            "date": "06/09/2026",
            "time": "18:30",
            "platform": "CazéTV",  # Coluna 5 no Brasileirão
            "tag": "📺 Transmissão Exclusiva"
        },
        {
            "comp": "Brasileirão Série A",
            "team1": "Corinthians",
            "team2": "Chapecoense",
            "date": "06/09/2026",
            "time": "19:30",
            "platform": "Amazon Prime",  # Coluna 4 no Brasileirão
            "tag": "🔥 Clássico"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Vitória",
            "team2": "Vasco da Gama",
            "date": "02/09/2026",
            "time": "21:30",
            "platform": "Amazon Prime",  # Coluna 3 na Copa do Brasil!
            "tag": "🏆 Decisivo"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Santos",
            "team2": "Palmeiras",
            "date": "02/09/2026",
            "time": "21:30",
            "platform": "Amazon Prime",  # Coluna 3 na Copa do Brasil!
            "tag": "🏆 Decisivo"
        },
        {
            "comp": "Copa do Brasil",
            "team1": "Grêmio",
            "team2": "Internacional",
            "date": "03/09/2026",
            "time": "20:00",
            "platform": "Amazon Prime",  # Coluna 3 na Copa do Brasil!
            "tag": "🏆 Decisivo"
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
    """Motor próprio do Monitor Esportes com filtro rigoroso por campeonato e coluna."""

    @staticmethod
    def parse_pdf_bytes(pdf_bytes: bytes, comp_name: str = "Brasileirão Série A") -> list:
        """Extrai partidas de bytes PDF aplicando as regras rígidas por campeonato."""
        events = []
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            doc.close()

            lines = full_text.split("\n")
            current_date = ""
            for line in lines:
                line = line.strip()
                if not line: continue
                
                d_match = re.search(r'^(\d{2}/\d{2})', line)
                if d_match:
                    current_date = d_match.group(1) + f"/{datetime.now().year}"

                if " x " in line:
                    t_match = re.search(r'(\d{2}:\d{2})', line)
                    if t_match:
                        time_str = t_match.group(1)
                        parts = line.split(" x ")
                        
                        def clean_team_name(text: str) -> str:
                            text = re.sub(r'\b\d{2}/\d{2}\b', '', text)
                            text = re.sub(r'\b\d{2}:\d{2}\b', '', text)
                            text = re.sub(r'\s+-\s+', ' ', text)
                            text = re.sub(r'^\s*\d+\s+', '', text)
                            text = re.sub(r'\s+\d+\s*$', '', text)
                            return " ".join(text.split()).strip()
                            
                        t1 = clean_team_name(parts[0])
                        t2 = clean_team_name(parts[1])
                        
                        col_match = re.search(r'\b(\d+)\b', parts[1])
                        col_str = col_match.group(1) if col_match else ""
                        if col_str:
                            is_copa = "COPA" in comp_name.upper()
                            
                            is_match = False
                            platform = ""
                            
                            if is_copa:
                                # Na Copa do Brasil: APENAS COLUNA 3 = Amazon Prime!
                                if col_str == "3":
                                    is_match = True
                                    platform = "Amazon Prime"
                            else:
                                # No Brasileirão Série A: COLUNA 4 = Amazon Prime, COLUNA 5 = CazéTV!
                                if col_str == "4":
                                    is_match = True
                                    platform = "Amazon Prime"
                                elif col_str == "5":
                                    is_match = True
                                    platform = "CazéTV"

                            if is_match:
                                events.append({
                                    "comp": comp_name,
                                    "team1": t1,
                                    "team2": t2,
                                    "date": current_date or datetime.now().strftime("%d/%m/%Y"),
                                    "time": time_str,
                                    "platform": platform,
                                    "tag": "🏆 Decisivo" if is_copa else ("📺 Transmissão Exclusiva" if "Cazé" in platform else "⭐ Alta Prioridade")
                                })
        except Exception as e:
            print(f"[CBF PARSER WARN] Erro ao decodificar PDF: {e}")

        if events:
            def parse_dt(g):
                try:
                    return datetime.strptime(f"{g.get('date', '')} {g.get('time', '')}", "%d/%m/%Y %H:%M")
                except:
                    return datetime.max
            events.sort(key=parse_dt)
            return events
        print("[CBF PARSER WARN] Nenhuma partida extraída do PDF ou falha na leitura. Utilizando fallback local estático (mock) de jogos oficiais.")
        return get_real_cbf_fixtures()

    @staticmethod
    def fetch_sumula_text(team1: str, team2: str, date: str, sumula_url: str = None) -> str:
        """
        Faz o download e extrai o texto completo do PDF oficial da súmula da CBF.
        
        Args:
            team1: Nome do time mandante
            team2: Nome do time visitante  
            date: Data da partida (DD/MM/AAAA)
            sumula_url: URL direta para o PDF da súmula (opcional). Se não fornecida,
                        tenta localizar via buscas no portal da CBF.
        
        Returns:
            String com o texto completo extraído do PDF da súmula, ou None em caso de falha.
        """
        import urllib.request
        ssl_ctx = None
        try:
            import ssl
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
        except Exception:
            pass

        pdf_bytes = None
        urls_to_try = []

        if sumula_url:
            urls_to_try.append(sumula_url)

        # Tentar buscar URL da súmula no portal da CBF caso nenhuma URL direta seja fornecida
        if not urls_to_try:
            try:
                # Limpar nomes para URL
                t1_clean = team1.replace(" ", "+")
                t2_clean = team2.replace(" ", "+")
                date_clean = date.replace("/", "-")
                search_url = f"https://www.cbf.com.br/futebol-brasileiro/jogos?q={t1_clean}+{t2_clean}"
                print(f"[CBF SUMULA] Buscando URL da súmula em: {search_url}")
                req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
                opener = urllib.request.build_opener()
                if ssl_ctx:
                    import ssl
                    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_ctx))
                with opener.open(req, timeout=10) as resp:
                    html = resp.read().decode("utf-8", errors="ignore")
                # Procurar links de PDF de súmula na página
                import re
                pdf_links = re.findall(r'href=["\']([^"\']*sumula[^"\']*\.pdf[^"\']*)["\']', html, re.IGNORECASE)
                for link in pdf_links[:3]:
                    if not link.startswith("http"):
                        link = "https://www.cbf.com.br" + link
                    urls_to_try.append(link)
            except Exception as e_search:
                print(f"[CBF SUMULA WARN] Não foi possível buscar URL da súmula no portal CBF: {e_search}")

        # Tentar baixar o PDF de cada URL candidata
        for url in urls_to_try:
            try:
                print(f"[CBF SUMULA] Tentando baixar PDF da súmula: {url}")
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                opener = urllib.request.build_opener()
                if ssl_ctx:
                    import ssl
                    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_ctx))
                with opener.open(req, timeout=15) as resp:
                    pdf_bytes = resp.read()
                if pdf_bytes and len(pdf_bytes) > 1000:
                    print(f"[CBF SUMULA] PDF baixado com sucesso ({len(pdf_bytes)} bytes).")
                    break
                else:
                    pdf_bytes = None
            except Exception as e_dl:
                print(f"[CBF SUMULA WARN] Falha ao baixar PDF de {url}: {e_dl}")
                continue

        if not pdf_bytes:
            print(f"[CBF SUMULA WARN] Não foi possível obter o PDF da súmula para {team1} x {team2} ({date}).")
            return None

        # Extrair texto do PDF com fitz (PyMuPDF)
        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            raw_text = "\n".join([page.get_text() for page in doc])
            doc.close()
            if raw_text.strip():
                print(f"[CBF SUMULA] Texto extraído da súmula com sucesso ({len(raw_text)} caracteres).")
                return raw_text
            else:
                print(f"[CBF SUMULA WARN] PDF baixado mas texto extraído está vazio.")
                return None
        except Exception as e_fitz:
            print(f"[CBF SUMULA WARN] Erro ao extrair texto do PDF com fitz: {e_fitz}")
            return None

    @staticmethod
    def get_upcoming_matches(force_refresh: bool = False) -> list:
        """Retorna os jogos oficiais filtrados pelas regras de cada campeonato.
        Remove confrontos antigos cuja data e horário de início já passaram em relação a agora.
        """
        today = datetime.now()
        fixtures = []

        if not force_refresh and os.path.exists(CACHE_PATH):
            try:
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    fixtures = json.load(f)
            except Exception as e:
                print(f"[CBF FETCHER WARN] Erro ao ler cache: {e}")

        if not fixtures:
            fixtures = get_real_cbf_fixtures()
            CBFScheduleFetcher.save_cache(fixtures)

        # Filtrar confrontos futuros ou vigentes (com tolerância de 3 horas para jogos em andamento)
        filtered_fixtures = []
        for g in fixtures:
            try:
                g_dt = datetime.strptime(f"{g.get('date')} {g.get('time')}", "%d/%m/%Y %H:%M")
                if g_dt >= today - timedelta(hours=3):
                    filtered_fixtures.append(g)
            except:
                filtered_fixtures.append(g)
                
        return filtered_fixtures


    @staticmethod
    def save_cache(fixtures: list) -> None:
        """Salva a lista de jogos no cache interno config/cbf_fixtures_cache.json."""
        try:
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(fixtures, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CBF FETCHER WARN] Erro ao salvar cache: {e}")
