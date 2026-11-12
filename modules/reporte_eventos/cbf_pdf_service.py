# -*- coding: utf-8 -*-
"""
Serviço de extração, parsing e indexação de direitos oficiais da CBF (PDFs 2026)
e Copa do Mundo FIFA 2026 (Planilha Excel).
Aplica rigorosamente:
- Regra de Fuso CBF: -1 hora em todos os jogos de PDFs
- Regra de Fuso Copa do Mundo: -2 horas na planilha Excel
- Indexação de Colunas de Direitos (BSA Col 4=Prime, Col 5=CazéTV; CDB Col 3=Prime)
"""

import os
import sys
import re
import time
import logging
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Optional, Any, Callable
import requests

from .crypto_utils import get_app_path, get_config_dir, get_base_dir
from .sharepoint_client import _deep_normalize_partida

logger = logging.getLogger(__name__)

# --- Padronização e Nomes Canônicos de Clubes ---

def canonical_team_name(t: str) -> str:
    """Padroniza o nome do clube para um formato visual canônico."""
    if not t:
        return ""
    original = str(t).strip()
    
    t_lower = t.lower()
    t_lower = "".join(c for c in unicodedata.normalize('NFD', t_lower) if unicodedata.category(c) != 'Mn')
    t_lower = t_lower.replace("-", " ").replace(".", " ").replace("_", " ")

    prefixes = [
        r"\besporte clube\b", r"\be c\b", r"\bf c\b", r"\bfutebol clube\b",
        r"\bfc\b", r"\bec\b", r"\bsaf\b", r"\bclube de regatas\b",
        r"\bsociedade esportiva\b", r"\bassociacao atletica\b",
        r"\bgremio recreativo\b", r"\bgremio esportivo\b",
        r"\bsport club\b", r"\bclube atletico\b", r"\bassociacao\b",
        r"\bsc\b", r"\bse\b", r"\bcr\b", r"\bfr\b", r"\baf\b", r"\bca\b", r"\baa\b"
    ]
    t_clean = t_lower
    for p in prefixes:
        t_clean = re.sub(p, " ", t_clean)
    t_clean = re.sub(r'\s+', ' ', t_clean).strip()

    state_strip_exceptions = ["atletico", "athletico", "america", "botafogo", "operario"]
    if not any(exc in t_clean for exc in state_strip_exceptions):
        t_clean = re.sub(r"\s+(mg|sp|rj|rs|pr|sc|ba|go|mt|ce|pe|al|rn|pb|am|pa|se|df|es|ma|pi|to|ro|ac|ap|rr)$", "", t_clean).strip()
    
    canonical_map = [
        (r"\b(vasco da gama|cr vasco da gama|vasco|vascao)\b", "Vasco da Gama"),
        (r"\b(athletico paranaense|atletico paranaense|athletico pr|atletico pr|cap|athletico|furacao)\b", "Athletico-PR"),
        (r"\b(atletico goianiense|atletico go|acg|dragao)\b", "Atlético-GO"),
        (r"\b(atletico mineiro|atletico mg|cam|galo|atletico)\b", "Atlético-MG"),
        (r"\b(red bull bragantino|rb bragantino|bragantino sp|bragantino|massa bruta)\b", "Red Bull Bragantino"),
        (r"\b(corinthians paulista|corinthians sp|corinthians|sccp|timao)\b", "Corinthians"),
        (r"\b(sao paulo fc|sao paulo sp|sao paulo|spfc|tricolor paulista)\b", "São Paulo"),
        (r"\b(se palmeiras|palmeiras sp|palmeiras|verdao|alviverde)\b", "Palmeiras"),
        (r"\b(flamengo rj|cr flamengo|flamengo|mengao|fla|mengo)\b", "Flamengo"),
        (r"\b(fluminense rj|fluminense fc|fluminense|flu|tricolor carioca|tricolor das laranjeiras)\b", "Fluminense"),
        (r"\b(santos fc|santos sp|santos|peixe)\b", "Santos"),
        (r"\b(botafogo de ribeirao preto|botafogo sp)\b", "Botafogo-SP"),
        (r"\b(botafogo pb|botafogo da paraiba)\b", "Botafogo-PB"),
        (r"\b(botafogo fr|botafogo rj|botafogo|fogao|bota)\b", "Botafogo"),
        (r"\b(gremio novorizontino|novorizontino sp|novorizontino|tigre do vale)\b", "Novorizontino"),
        (r"\b(gremio fbpa|gremio porto alegrense|gremio rsg|gremio rs|gremio)\b", "Grêmio"),
        (r"\b(internacional de limeira|inter de limeira|inter limeira)\b", "Inter de Limeira"),
        (r"\b(internacional rs|inter de porto alegre|inter rs|internacional|inter|colorado)\b", "Internacional"),
        (r"\b(cruzeiro ec|cruzeiro mg|cruzeiro|raposa)\b", "Cruzeiro"),
        (r"\b(juventude rs|juventude|papo)\b", "Juventude"),
        (r"\b(fortaleza ec|fortaleza ce|fortaleza|leao do pici)\b", "Fortaleza"),
        (r"\b(ceara sc|ceara ce|ceara|vozao|vovo)\b", "Ceará"),
        (r"\b(bahia ba|ec bahia|bahia|esquadrao|tricolor de aco)\b", "Bahia"),
        (r"\b(vitoria ba|ec vitoria|vitoria|leao da barra)\b", "Vitória"),
        (r"\b(cuiaba ec|cuiaba mt|cuiaba|dourado)\b", "Cuiabá"),
        (r"\b(criciuma ec|criciuma sc|criciuma|tigre)\b", "Criciúma"),
        (r"\b(coritiba fcf|coritiba pr|coritiba|coxa)\b", "Coritiba"),
        (r"\b(goias ec|goias go|goias|esmeraldino)\b", "Goiás"),
        (r"\b(sport club do recife|sport recife|sport pe|sport|leao da ilha)\b", "Sport"),
        (r"\b(america de natal|america rn)\b", "América-RN"),
        (r"\b(america mineiro|america mg|coelho|america)\b", "América-MG"),
        (r"\b(chapecoense af|chapecoense sc|chapecoense|chape)\b", "Chapecoense"),
        (r"\b(mirassol fc|mirassol sp|mirassol|leaozinho)\b", "Mirassol"),
        (r"\b(operario ferroviario|operario pr|operario|fantasma)\b", "Operário-PR"),
        (r"\b(vila nova fc|vila nova go|vila nova|tigrao)\b", "Vila Nova"),
        (r"\b(ponte preta sp|a a ponte preta|ponte preta|macaca)\b", "Ponte Preta"),
        (r"\b(guarani fc|guarani sp|guarani|bugre)\b", "Guarani"),
        (r"\b(amazonas fc|amazonas am|amazonas|onca)\b", "Amazonas"),
        (r"\b(brusque fc|brusque sc|brusque|quadricolor)\b", "Brusque"),
        (r"\b(ituano fc|ituano sp|ituano|galo de itu)\b", "Ituano"),
        (r"\b(paysandu sc|paysandu pa|paysandu|papao)\b", "Paysandu"),
        (r"\b(clube do remo|remo pa|remo|leao azul)\b", "Remo"),
        (r"\b(avai fc|avai sc|avai|leao da ilha)\b", "Avaí"),
        (r"\b(clube de regatas brasil|crb al|crb|galo da praia)\b", "CRB"),
        (r"\b(centro sportivo alagoano|csa al|csa|azulino)\b", "CSA"),
        (r"\b(athletic club|athletic mg|athletic)\b", "Athletic Club"),
        (r"\b(ferroviaria sp|ferroviaria|locomotiva)\b", "Ferroviária"),
        (r"\b(volta redonda rj|volta redonda|voltaco)\b", "Volta Redonda"),
        (r"\b(nautico pe|nautico|timbu)\b", "Náutico"),
        (r"\b(figueirense fc|figueirense sc|figueirense|figueira)\b", "Figueirense"),
        (r"\b(sampaio correa|sampaio correa ma|bolivia querida)\b", "Sampaio Corrêa"),
        (r"\b(confianca se|confianca|dragao do bairro industrial)\b", "Confiança"),
        (r"\b(abc fc|abc rn|abc)\b", "ABC"),
        (r"\b(londrina ec|londrina pr|londrina|tubarao)\b", "Londrina"),
    ]
    for pattern, pretty_name in canonical_map:
        if re.search(pattern, t_clean):
            return pretty_name
    return original.title()

def prettify_match_name(match_name: str) -> str:
    """Padroniza 'Time A x Time B' para nomes canônicos limpos."""
    text_work = re.sub(r'\s+[vVxX]\s+', ' x ', str(match_name))
    parts = text_work.split(" x ")
    if len(parts) >= 2:
        t1, t2 = canonical_team_name(parts[0]), canonical_team_name(parts[1])
        return f"{t1} x {t2}"
    return canonical_team_name(match_name)

# --- Índices e Validação de Direitos CBF ---

_CBF_RIGHTS_CACHE: Dict[str, Dict[Tuple[str, ...], Set[str]]] = {}

def get_latest_cbf_url(comp_type: str) -> Optional[str]:
    """Retorna a URL mais recente da Tabela Detalhada no portal CBF ou fallback homologado."""
    fallbacks = {
        "BSA": "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_BSA_2026_05_10_cd1e0860b2.pdf",
        "CDB": "https://stcbfsiteprdimgbrs.blob.core.windows.net/img-site/cdn/Tabela_Detalhada_Copa_do_Brasil_2026_07_10_0c40ca55b3.pdf"
    }
    return fallbacks.get(comp_type)

def get_cbf_rights_index(force_reload: bool = False) -> Dict[str, Dict[Tuple[str, ...], Set[str]]]:
    """
    Indexa os confrontos e colunas de TV dos PDFs oficiais da CBF.
    Retorna dict com 'brasileirao' e 'copa_do_brasil'.
    """
    global _CBF_RIGHTS_CACHE
    if _CBF_RIGHTS_CACHE and not force_reload:
        return _CBF_RIGHTS_CACHE

    index: Dict[str, Dict[Tuple[str, ...], Set[str]]] = {'brasileirao': {}, 'copa_do_brasil': {}}

    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.warning("[CBF Rights] pypdfium2 não instalado.")
        return index

    # Arquivos locais prioritários
    bsa_candidates = [
        get_app_path("temp_Brasileirão_Série_A.pdf"),
        get_app_path("latest_bsa.pdf"),
        get_app_path("real_BSA.pdf")
    ]
    for fn in bsa_candidates:
        if os.path.exists(fn):
            try:
                doc = pdfium.PdfDocument(fn)
                full_text = ""
                for i in range(len(doc)):
                    page = doc.get_page(i)
                    tp = page.get_textpage()
                    full_text += tp.get_text_bounded() + "\n"
                    tp.close()
                    page.close()
                doc.close()

                for line in full_text.split('\n'):
                    line = line.strip()
                    if ' x ' in line and re.search(r'\d{2}:\d{2}', line):
                        if re.search(r'\b\d+\s+x\s+\d+\b', line): continue
                        if re.search(r'\(\d+\)', line): continue
                        m_tv = re.search(r'(?:[A-Z]{2}\s+)?([1-7](?:\s+[1-7])*)\s*$', line)
                        cols = set(m_tv.group(1).split()) if m_tv else set()
                        parts = line.split(' x ')
                        pt1 = parts[0]
                        m_time = re.search(r'\d{2}:\d{2}', pt1)
                        if m_time: pt1 = pt1[m_time.end():].strip()
                        pt1 = re.sub(r'^\d+\s+', '', pt1).strip()
                        pt1 = re.sub(r'^\d+ª?\s+', '', pt1).strip()
                        pt1 = re.sub(r'\(.*?\)', '', pt1).strip()
                        pt1 = re.sub(r'\b[A-Z]{2}\b$', '', pt1).strip()
                        pt1 = re.sub(r'\b[A-Z]{2}\b', '', pt1).strip()
                        pt2 = parts[1]
                        pt2 = re.sub(r'\(.*?\)', '', pt2).strip()
                        pt2 = re.sub(r'\s[A-Z]{2}\b.*$', '', pt2).strip()
                        jogo = f'{pt1.strip()} x {pt2.strip()}'
                        p_t = _deep_normalize_partida(jogo)
                        if p_t and p_t != ('',):
                            index['brasileirao'][p_t] = cols
                if index['brasileirao']:
                    break
            except Exception as e:
                logger.warning(f"[CBF Rights] Erro ao ler PDF BSA {fn}: {e}")

    cdb_candidates = [
        get_app_path("temp_Copa_do_Brasil.pdf"),
        get_app_path("latest_cdb.pdf"),
        get_app_path("real_CDB.pdf")
    ]
    for fn in cdb_candidates:
        if os.path.exists(fn):
            try:
                doc = pdfium.PdfDocument(fn)
                full_text = ""
                for i in range(len(doc)):
                    page = doc.get_page(i)
                    tp = page.get_textpage()
                    full_text += tp.get_text_bounded() + "\n"
                    tp.close()
                    page.close()
                doc.close()

                for line in full_text.split('\n'):
                    line = line.strip()
                    if ' x ' in line and re.search(r'\d{2}:\d{2}', line):
                        if re.search(r'\b\d+\s+x\s+\d+\b', line): continue
                        if re.search(r'\(\d+\)', line): continue
                        m_tv = re.search(r'(?:[A-Z]{2}\s+)?([1-7](?:\s+[1-7])*)\s*$', line)
                        cols = set(m_tv.group(1).split()) if m_tv else set()
                        parts = line.split(' x ')
                        pt1 = parts[0]
                        m_time = re.search(r'\d{2}:\d{2}', pt1)
                        if m_time: pt1 = pt1[m_time.end():].strip()
                        pt1 = re.sub(r'^\d+\s+', '', pt1).strip()
                        pt1 = re.sub(r'^\d+ª?\s+', '', pt1).strip()
                        pt1 = re.sub(r'\(.*?\)', '', pt1).strip()
                        pt1 = re.sub(r'\b[A-Z]{2}\b$', '', pt1).strip()
                        pt1 = re.sub(r'\b[A-Z]{2}\b', '', pt1).strip()
                        pt2 = parts[1]
                        pt2 = re.sub(r'\(.*?\)', '', pt2).strip()
                        pt2 = re.sub(r'\s[A-Z]{2}\b.*$', '', pt2).strip()
                        jogo = f'{pt1.strip()} x {pt2.strip()}'
                        p_t = _deep_normalize_partida(jogo)
                        if p_t and p_t != ('',):
                            index['copa_do_brasil'][p_t] = cols
                if index['copa_do_brasil']:
                    break
            except Exception as e:
                logger.warning(f"[CBF Rights] Erro ao ler PDF CDB {fn}: {e}")

    _CBF_RIGHTS_CACHE = index
    return index

def is_cbf_broadcast_authorized(camp_name: str, match_name: str, platform_name: str) -> bool:
    """Valida se o canal/plataforma tem autorização oficial na tabela CBF."""
    c_lower = str(camp_name).lower()
    p_lower = str(platform_name).lower()

    is_bsa = 'brasileir' in c_lower or 'serie a' in c_lower
    is_cdb = 'copa do brasil' in c_lower
    if not (is_bsa or is_cdb):
        return True

    idx = get_cbf_rights_index()
    p_tuple = _deep_normalize_partida(match_name)

    if is_bsa:
        cols = idx['brasileirao'].get(p_tuple)
        if cols is not None:
            if 'prime' in p_lower or 'amazon' in p_lower:
                return '4' in cols
            elif 'caze' in p_lower or 'cazé' in p_lower or 'youtube' in p_lower:
                return '5' in cols
            return True
        return True

    if is_cdb:
        cols = idx['copa_do_brasil'].get(p_tuple)
        if cols is not None:
            if 'prime' in p_lower or 'amazon' in p_lower:
                return '3' in cols
            return True
        return True

    return True

# --- Parsing de PDF com -1 Hora Obrigatória ---

def parse_cbf_pdf(pdf_path: str, nome_original: str) -> List[Dict[str, Any]]:
    """Extrai confrontos, datas e horários de PDF da CBF, aplicando a regra de -1 hora."""
    extracted = []
    if not os.path.exists(pdf_path):
        return extracted

    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(pdf_path)
        full_text = ""
        for i in range(len(doc)):
            page = doc.get_page(i)
            tp = page.get_textpage()
            full_text += tp.get_text_bounded() + "\n"
            tp.close()
            page.close()
        doc.close()

        is_cdb = "Copa do Brasil" in nome_original
        legend = {"3": "Amazon Prime"} if is_cdb else {"4": "Amazon Prime", "5": "Cazé TV"}
        target_ids = ["3"] if is_cdb else ["4", "5"]

        lines = full_text.split("\n")
        current_date = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            date_match = re.search(r'(\d{2}/\d{2})\s+(?:seg|ter|qua|qui|sex|sáb|sab|dom)', line, re.I)
            if date_match:
                current_date = date_match.group(1) + "/2026"

            if " x " in line:
                time_match = re.search(r'(\d{2}:\d{2})', line)
                if time_match:
                    hora = time_match.group(1)
                    if re.search(r'\b\d+\s+x\s+\d+\b', line): continue
                    if re.search(r'\(\d+\)', line): continue

                    m_tv = re.search(r'(?:[A-Z]{2}\s+)?([1-7](?:\s+[1-7])*)\s*$', line)
                    if not m_tv:
                        continue
                    tv_col_nums = m_tv.group(1).split()
                    relevant_nums = [n for n in tv_col_nums if n in target_ids]
                    if not relevant_nums:
                        continue

                    tv_str = ", ".join([legend.get(n, n) for n in relevant_nums])

                    parts = line.split(" x ")
                    pt1 = parts[0]
                    m_time = re.search(r'\d{2}:\d{2}', pt1)
                    if m_time: pt1 = pt1[m_time.end():].strip()
                    pt1 = re.sub(r'^\d+\s+', '', pt1).strip()
                    pt1 = re.sub(r'^\d+ª?\s+', '', pt1).strip()
                    pt1 = re.sub(r'\(.*?\)', '', pt1).strip()
                    pt1 = re.sub(r'\b[A-Z]{2}\b$', '', pt1).strip()
                    pt1 = re.sub(r'\b[A-Z]{2}\b', '', pt1).strip()

                    pt2 = parts[1]
                    pt2 = re.sub(r'\(.*?\)', '', pt2).strip()
                    pt2 = re.sub(r'\s[A-Z]{2}\b.*$', '', pt2).strip()

                    jogo_clean = prettify_match_name(f"{pt1.strip()} x {pt2.strip()}")

                    extracted.append({
                        "Camp": nome_original,
                        "Jogo": jogo_clean,
                        "Data": current_date,
                        "Hora": hora,
                        "TV": tv_str
                    })
    except Exception as e:
        logger.error(f"[CBF Parse] Erro ao parsear PDF {pdf_path}: {e}")
    return extracted

# --- Parsing de Copa do Mundo Excel com -2 Horas ---

def parse_copa_mundo_excel(excel_path: str) -> List[Dict[str, Any]]:
    """Extrai confrontos da planilha da Copa do Mundo 2026 com -2 horas aplicadas."""
    extracted = []
    if not os.path.exists(excel_path):
        return extracted
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        sheet = wb.active
        rows_iter = list(sheet.iter_rows(values_only=True))
        if not rows_iter:
            return extracted

        headers = [str(h or '').upper() for h in rows_iter[0]]
        idx_data = next((i for i, h in enumerate(headers) if 'DATA' in h), None)
        idx_hora = next((i for i, h in enumerate(headers) if 'HORA' in h), None)
        idx_jogo = next((i for i, h in enumerate(headers) if 'JOGO' in h), None)

        if idx_data is None or idx_hora is None or idx_jogo is None:
            return extracted

        for r_vals in rows_iter[1:]:
            data_raw = str(r_vals[idx_data] or '').strip()
            hora_raw = str(r_vals[idx_hora] or '').strip()
            jogo_raw = str(r_vals[idx_jogo] or '').strip()

            if not jogo_raw or jogo_raw.lower() in ("nan", "none", ""):
                continue

            try:
                if " " in data_raw: data_raw = data_raw.split(" ")[0]
                if "-" in data_raw:
                    dt_obj = datetime.strptime(data_raw, "%Y-%m-%d")
                    data_formatada = dt_obj.strftime("%d/%m/%Y")
                else:
                    data_formatada = data_raw
            except Exception:
                data_formatada = data_raw

            data_ajustada = data_formatada
            hora_ajustada = hora_raw
            try:
                for fmt_h in ("%H:%M", "%H:%M:%S"):
                    try:
                        dt_combined = datetime.strptime(f"{data_formatada} {hora_raw}", f"%d/%m/%Y {fmt_h}")
                        dt_ajustada = dt_combined - timedelta(hours=2)
                        data_ajustada = dt_ajustada.strftime("%d/%m/%Y")
                        hora_ajustada = dt_ajustada.strftime("%H:%M")
                        break
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"[Copa Mundo] Erro ao ajustar fuso: {e}")

            extracted.append({
                "Camp": "Copa do Mundo",
                "Jogo": prettify_match_name(jogo_raw),
                "Data": data_ajustada,
                "Hora": hora_ajustada,
                "TV": "Cazé TV"
            })
    except Exception as e:
        logger.error(f"[Copa Mundo] Erro ao ler planilha {excel_path}: {e}")
    return extracted


def run_eventos_cbf(
    camps_ativos: Optional[Dict[str, bool]] = None,
    data_inicio_str: str = "",
    existing_matches: Optional[List[Tuple[str, str]]] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> List[Tuple[Any, ...]]:
    """
    Executa a extração oficial de partidas dos PDFs da CBF (Brasileirão Série A e Copa do Brasil)
    e da planilha da Copa do Mundo FIFA 2026 com ajuste de fuso (-1h CBF / -2h Copa) e filtro estrito de duplicatas.
    Implementação 100% fiel à rotina run_eventos_cbf do Streaming_Scheduler.
    """
    from .sharepoint_client import _deep_normalize_partida

    eventos: List[Tuple[Any, ...]] = []
    if camps_ativos is None:
        camps_ativos = {"Brasileirão serie A": True, "Copa do Brasil": True, "Copa do Mundo": True}

    # Data de início para filtro
    try:
        data_inicio_obj = datetime.strptime(data_inicio_str, "%d/%m/%Y")
    except Exception:
        data_inicio_obj = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Conjunto de jogos já existentes no grid para evitar sobreposição com scrapers de streaming
    existing_set = set()
    if existing_matches:
        for j, d in existing_matches:
            try:
                norm_p = _deep_normalize_partida(str(j))
                existing_set.add((norm_p, str(d).strip()))
            except Exception:
                pass

    camps_to_process = []
    if camps_ativos.get("Brasileirão serie A") or camps_ativos.get("Brasileirão Série A"):
        url_bsa = get_latest_cbf_url("BSA")
        if url_bsa:
            camps_to_process.append({"nome": "Brasileirão Série A", "url_pdf": url_bsa})
    if camps_ativos.get("Copa do Brasil"):
        url_cdb = get_latest_cbf_url("CDB")
        if url_cdb:
            camps_to_process.append({"nome": "Copa do Brasil", "url_pdf": url_cdb})

    cfg_dir = get_config_dir()
    base_dir = get_base_dir()

    for idx_camp, camp_info in enumerate(camps_to_process):
        nome_camp = camp_info["nome"]
        url_pdf = camp_info["url_pdf"]
        if progress_callback:
            progress_callback(f"Baixando PDF oficial: {nome_camp}...", 0.85 + (idx_camp * 0.04))

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            resp = requests.get(url_pdf, headers=headers, verify=False, timeout=15)
            if resp.status_code != 200 or len(resp.content) < 5000:
                logger.warning(f"[CBF] PDF {nome_camp} indisponível (Status: {resp.status_code}, Tamanho: {len(resp.content)})")
                continue

            pdf_path = cfg_dir / f"temp_{nome_camp.replace(' ', '_')}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(resp.content)

            extracted = parse_cbf_pdf(str(pdf_path), nome_camp)
            logger.info(f"[CBF] PDF {nome_camp} extraiu {len(extracted)} jogos.")

            # Checa se há jogos futuros na tabela da CBF em relação à data solicitada
            tem_futuros = False
            for ev in extracted:
                try:
                    d_dt = datetime.strptime(ev["Data"], "%d/%m/%Y")
                    if d_dt >= data_inicio_obj:
                        tem_futuros = True
                        break
                except Exception:
                    pass

            if not tem_futuros:
                logger.info(
                    f"[CBF] Jogos do PDF {nome_camp} são da rodada oficial mais recente publicada pela CBF "
                    f"(< {data_inicio_obj.strftime('%d/%m/%Y')}). Preservando todos os {len(extracted)} jogos."
                )

            var_nav = "Esquerda"
            for ev in extracted:
                # Regra oficial CBF: subtrai 1 hora dos horários de tabela da CBF
                data_ajustada = ev["Data"]
                hora_ajustada = ev["Hora"]
                try:
                    for fmt_h in ("%H:%M", "%H:%M:%S"):
                        try:
                            dt_combined = datetime.strptime(f"{ev['Data']} {ev['Hora']}", f"%d/%m/%Y {fmt_h}")
                            dt_ajustada = dt_combined - timedelta(hours=1)
                            data_ajustada = dt_ajustada.strftime("%d/%m/%Y")
                            hora_ajustada = dt_ajustada.strftime("%H:%M")
                            break
                        except Exception:
                            pass
                except Exception as e_fuso:
                    logger.warning(f"[CBF] Erro ao ajustar fuso CBF ({ev['Data']} {ev['Hora']}): {e_fuso}")

                # Filtro de data: se houver jogos futuros, aplica o corte; se for rodada recente da CBF, mantém
                if tem_futuros:
                    try:
                        ev_date_obj = datetime.strptime(data_ajustada, "%d/%m/%Y")
                        if ev_date_obj < data_inicio_obj:
                            continue
                    except Exception:
                        continue

                # Prioridade: se a partida já foi capturada diretamente pela plataforma (ex: Prime), descarta o PDF
                norm_part = _deep_normalize_partida(ev["Jogo"])
                if (norm_part, data_ajustada) in existing_set or (norm_part, ev["Data"]) in existing_set:
                    logger.info(f"[CBF] Ignorando duplicata PDF (já coletada via plataforma): {ev['Jogo']} em {data_ajustada}")
                    continue

                plataformas_evento = [p.strip() for p in ev["TV"].split(",") if p.strip()]
                plat_display = plataformas_evento[0] if plataformas_evento else "CBF"
                cbf_camp = f"CBF - {nome_camp}" if "CBF" not in nome_camp.upper() else nome_camp
                jogo_bonito = prettify_match_name(ev["Jogo"])

                row = (cbf_camp, jogo_bonito, data_ajustada, hora_ajustada, var_nav, "15", plat_display, url_pdf)
                eventos.append(row)
                existing_set.add((norm_part, data_ajustada))
                var_nav = "Direita" if var_nav == "Esquerda" else "Esquerda"
        except Exception as e_camp:
            logger.error(f"[CBF] Erro ao processar PDF {nome_camp}: {e_camp}")

    # Copa do Mundo FIFA 2026 (Planilha Excel com -2 Horas)
    if camps_ativos.get("Copa do Mundo"):
        if progress_callback:
            progress_callback("Lendo tabela oficial da Copa do Mundo FIFA 2026...", 0.93)
        xls_candidates = [
            cfg_dir / "Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx",
            base_dir / "Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx",
            Path(os.getcwd()) / "Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx",
            Path(r"E:\desenvolvimento\Streaming_Scheduler\Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx"),
        ]
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            xls_candidates.append(Path(sys._MEIPASS) / "Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx")
            xls_candidates.append(Path(sys._MEIPASS) / "config" / "Tabela_Completa_Copa_Mundo_2026_Fase_Grupos.xlsx")

        xls_found = None
        for xc in xls_candidates:
            if xc.exists():
                xls_found = str(xc)
                break

        if xls_found:
            try:
                copa_extracted = parse_copa_mundo_excel(xls_found)
                copa_tem_futuros = False
                for c_ev in copa_extracted:
                    try:
                        c_dt = datetime.strptime(c_ev["Data"], "%d/%m/%Y")
                        if c_dt >= data_inicio_obj:
                            copa_tem_futuros = True
                            break
                    except Exception:
                        pass

                var_nav_copa = "Esquerda"
                for c_ev in copa_extracted:
                    if copa_tem_futuros:
                        try:
                            c_date_obj = datetime.strptime(c_ev["Data"], "%d/%m/%Y")
                            if c_date_obj < data_inicio_obj:
                                continue
                        except Exception:
                            pass

                    norm_copa = _deep_normalize_partida(c_ev["Jogo"])
                    if (norm_copa, c_ev["Data"]) in existing_set:
                        continue

                    row = ("CBF - Copa do Mundo FIFA 2026", c_ev["Jogo"], c_ev["Data"], c_ev["Hora"], var_nav_copa, "15", c_ev["TV"], "https://www.youtube.com/@CazeTV/streams")
                    eventos.append(row)
                    existing_set.add((norm_copa, c_ev["Data"]))
                    var_nav_copa = "Direita" if var_nav_copa == "Esquerda" else "Esquerda"
                logger.info(f"[CBF] Copa do Mundo carregou {len(copa_extracted)} jogos da planilha oficial.")
            except Exception as e_copa_proc:
                logger.error(f"[CBF] Erro ao processar tabela Copa do Mundo: {e_copa_proc}")

    return eventos

