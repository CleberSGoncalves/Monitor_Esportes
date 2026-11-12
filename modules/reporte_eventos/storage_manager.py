# -*- coding: utf-8 -*-
"""
Gerenciador de armazenamento e configurações locais para o Reporte de Eventos.
Garante isolamento 100% autônomo dentro de Monitor_Esportes/config.
"""

import os
import sys
import json
import csv
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .crypto_utils import get_app_path, get_config_dir, get_base_dir

logger = logging.getLogger(__name__)

DEFAULT_YOUTUBE_CHANNELS = [
    {"nome": "Gaúcha", "url": "https://www.youtube.com/@gaucha", "ativo": True},
    {"nome": "Gaúcha Esportes", "url": "https://www.youtube.com/@gauchaesportes", "ativo": True},
    {"nome": "Atlântida TV", "url": "https://www.youtube.com/@atlantida_tv", "ativo": True},
    {"nome": "Baldasso TV", "url": "https://www.youtube.com/@BaldassoTV", "ativo": True},
    {"nome": "Bagé TV", "url": "https://www.youtube.com/@Bag%C3%A9TvOficial", "ativo": True},
    {"nome": "Esporte Band RS", "url": "https://www.youtube.com/@EsporteBandRS", "ativo": True},
]

def carregar_youtube_channels_config() -> List[Dict[str, Any]]:
    """Carrega lista de canais do YouTube monitorados de youtube_channels.json."""
    caminho = get_app_path("youtube_channels.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and data:
                    return data
        except Exception as e:
            logger.warning(f"[Storage] Erro ao carregar {caminho}: {e}")
    salvar_youtube_channels_config(DEFAULT_YOUTUBE_CHANNELS)
    return DEFAULT_YOUTUBE_CHANNELS

def salvar_youtube_channels_config(lista: List[Dict[str, Any]]) -> None:
    """Salva lista de canais do YouTube monitorados em youtube_channels.json."""
    caminho = get_app_path("youtube_channels.json")
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(lista, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[Storage] Erro ao salvar {caminho}: {e}")

DEFAULT_CAMPEONATOS = [
    {"campeonato": "CBF - Brasileirão Série A", "plataforma": "Amazon Prime", "url": "https://www.primevideo.com", "ativo": True},
    {"campeonato": "CBF - Brasileirão Série B", "plataforma": "Disney", "url": "https://www.disneyplus.com", "ativo": True},
    {"campeonato": "CBF - Copa do Brasil", "plataforma": "Amazon Prime", "url": "https://www.primevideo.com", "ativo": True},
    {"campeonato": "Copa do Mundo FIFA 2026", "plataforma": "Cazé TV", "url": "https://www.youtube.com/@CazeTV", "ativo": True},
    {"campeonato": "Mundial de Clubes FIFA", "plataforma": "Dazn", "url": "https://www.dazn.com", "ativo": True},
    {"campeonato": "Campeonato Paulista", "plataforma": "Max", "url": "https://www.max.com", "ativo": True},
    {"campeonato": "CONMEBOL Libertadores", "plataforma": "Disney", "url": "https://www.disneyplus.com", "ativo": True},
    {"campeonato": "CONMEBOL Sudamericana", "plataforma": "Disney", "url": "https://www.disneyplus.com", "ativo": True},
]

def carregar_campeonatos_config() -> List[Dict[str, Any]]:
    """Carrega campeonatos customizados de campeonatos_config.json, inicializando com os padrões se vazio."""
    caminho = get_app_path("campeonatos_config.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            logger.warning(f"[Storage] Erro ao carregar {caminho}: {e}")
    salvar_campeonatos_config(DEFAULT_CAMPEONATOS)
    return DEFAULT_CAMPEONATOS

def salvar_campeonatos_config(lista: List[Dict[str, Any]]) -> None:
    """Salva campeonatos customizados em campeonatos_config.json."""
    caminho = get_app_path("campeonatos_config.json")
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(lista, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[Storage] Erro ao salvar {caminho}: {e}")

def carregar_streaming_csv() -> List[List[str]]:
    """Carrega dados da grade com priorização inteligente entre streaming_data.csv, data.csv e diretório da aplicação."""
    base_dir = get_base_dir()
    cfg_dir = get_config_dir()
    candidates = [
        get_app_path("streaming_data.csv"),
        get_app_path("data.csv"),
        str(base_dir / "data.csv"),
        str(base_dir / "config" / "streaming_data.csv"),
        str(cfg_dir / "streaming_data.csv"),
        str(cfg_dir / "data.csv"),
        os.path.join(os.getcwd(), "data.csv"),
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        meipass = Path(sys._MEIPASS)
        candidates.append(str(meipass / "data.csv"))
        candidates.append(str(meipass / "config" / "streaming_data.csv"))

    caminho = None
    for c in candidates:
        if c and os.path.exists(c) and os.path.getsize(c) > 20:
            caminho = c
            break

    rows = []
    if caminho and os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for r in reader:
                    if not r:
                        continue
                    # Pula linha de cabeçalho
                    if str(r[0]).strip().lower() == "campeonato" and "partida" in [str(x).strip().lower() for x in r]:
                        continue
                    rows.append(r)
            logger.info(f"[Storage] Carregados {len(rows)} eventos de {caminho}")
        except Exception as e:
            logger.warning(f"[Storage] Erro ao ler CSV {caminho}: {e}")
    return rows

def salvar_streaming_csv(linhas: List[List[Any]]) -> None:
    """Salva dados da grade simultaneamente no streaming_data.csv e data.csv para compatibilidade 100%."""
    targets = [
        get_app_path("streaming_data.csv"),
        str(get_base_dir() / "data.csv"),
        os.path.join(os.getcwd(), "data.csv"),
    ]
    header = ["Campeonato", "Partida", "Data", "Horário", "Navegador", "Min antes para ação", "Canal de Transmissão", "Url"]
    for caminho in targets:
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                for r in linhas:
                    if not r:
                        continue
                    if str(r[0]).strip().lower() == "campeonato":
                        continue
                    writer.writerow(r)
            logger.info(f"[Storage] Grade salva com sucesso ({len(linhas)} linhas) em {caminho}")
        except Exception as e:
            logger.error(f"[Storage] Erro ao salvar CSV {caminho}: {e}")

def carrega_config_xml(caminho_ou_arquivo=None, secao=None) -> Any:
    """Carrega dicionário com todas as configurações do config.xml (ou seção específica)."""
    caminho = get_app_path(caminho_ou_arquivo or "config.xml")
    cfg = {
        "emails": "binhole@gmail.com",
        "refresh": "20",
        "hora_automatico": "09:00",
        "check_automatico_Email": False,
        "check_automatico_Evento": False,
        "somente_relatorio": False,
        "plataformas": {
            "Amazon Prime": True,
            "Disney": True,
            "Cazé TV": True,
            "Dazn": True,
            "Max": True,
            "CBF": True,
        },
        "campeonatos": {
            "Brasileirão serie A": True,
            "Brasileirão serie B": True,
            "Copa do Brasil": True,
            "Copa do Mundo": True,
            "Mundial de Clubes FIFA": True,
            "Campeonato Paulista": True,
            "CONMEBOL Libertadores": True,
            "CONMEBOL Sudamericana": True,
        }
    }
    if not os.path.exists(caminho):
        return cfg.get(secao, {}) if secao else cfg

    try:
        tree = ET.parse(caminho)
        root = tree.getroot()
        
        def _get_val(tag, default=""):
            el = root.find(tag)
            return el.text.strip() if el is not None and el.text else default

        def _get_bool(tag, default=True):
            el = root.find(tag)
            if el is None or not el.text:
                return default
            v = el.text.strip().lower()
            return v in ("true", "1", "yes", "sim")

        cfg["emails"] = _get_val("emails", cfg["emails"])
        cfg["refresh"] = _get_val("refresh", cfg["refresh"])
        cfg["hora_automatico"] = _get_val("hora_automatico", cfg["hora_automatico"])
        cfg["check_automatico_Email"] = _get_bool("check_automatico_Email", False)
        cfg["check_automatico_Evento"] = _get_bool("check_automatico_Evento", False)
        cfg["somente_relatorio"] = _get_bool("somente_relatorio", False)

        # Plataformas (Padrão: todas ativas, idêntico ao Streaming_Scheduler)
        cfg["plataformas"]["Amazon Prime"] = _get_bool("plataforma_prime", True)
        cfg["plataformas"]["Disney"] = _get_bool("plataforma_disney", True)
        cfg["plataformas"]["Cazé TV"] = _get_bool("plataforma_caze", True)
        cfg["plataformas"]["Dazn"] = _get_bool("plataforma_dazn", True)
        cfg["plataformas"]["Max"] = _get_bool("plataforma_max", True)
        cfg["plataformas"]["CBF"] = _get_bool("plataforma_cbf", True)

        # Campeonatos
        cfg["campeonatos"]["Brasileirão serie A"] = _get_bool("camp_brasileirao_serie_a", True)
        cfg["campeonatos"]["Brasileirão serie B"] = _get_bool("camp_brasileirao_serie_b", True)
        cfg["campeonatos"]["Copa do Brasil"] = _get_bool("camp_copa_do_brasil", True)
        cfg["campeonatos"]["Copa do Mundo"] = _get_bool("camp_copa_do_mundo", True)
        cfg["campeonatos"]["Mundial de Clubes FIFA"] = _get_bool("camp_mundial_de_clubes_fifa", True)
        cfg["campeonatos"]["Campeonato Paulista"] = _get_bool("camp_campeonato_paulista", True)
        cfg["campeonatos"]["CONMEBOL Libertadores"] = _get_bool("camp_conmebol_libertadores", True)
        cfg["campeonatos"]["CONMEBOL Sudamericana"] = _get_bool("camp_conmebol_sudamericana", True)

    except Exception as e:
        logger.warning(f"[Storage] Erro ao processar config.xml: {e}")
    return cfg.get(secao, {}) if secao else cfg

def salvar_config_xml(cfg: Dict[str, Any]) -> None:
    """Grava as configurações no config.xml."""
    caminho = get_app_path("config.xml")
    try:
        root = ET.Element("credenciais")
        
        def _add(tag, val):
            el = ET.SubElement(root, tag)
            el.text = str(val).lower() if isinstance(val, bool) else str(val)

        _add("emails", cfg.get("emails", ""))
        _add("refresh", cfg.get("refresh", "20"))
        _add("hora_automatico", cfg.get("hora_automatico", "09:00"))
        _add("check_automatico_Email", cfg.get("check_automatico_Email", False))
        _add("check_automatico_Evento", cfg.get("check_automatico_Evento", False))
        _add("somente_relatorio", cfg.get("somente_relatorio", False))

        plats = cfg.get("plataformas", {})
        _add("plataforma_dazn", plats.get("Dazn", False))
        _add("plataforma_prime", plats.get("Amazon Prime", True))
        _add("plataforma_caze", plats.get("Cazé TV", True))
        _add("plataforma_disney", plats.get("Disney", False))
        _add("plataforma_max", plats.get("Max", False))
        _add("plataforma_cbf", plats.get("CBF", True))

        camps = cfg.get("campeonatos", {})
        _add("camp_brasileirao_serie_a", camps.get("Brasileirão serie A", True))
        _add("camp_brasileirao_serie_b", camps.get("Brasileirão serie B", True))
        _add("camp_copa_do_brasil", camps.get("Copa do Brasil", True))
        _add("camp_copa_do_mundo", camps.get("Copa do Mundo", True))
        _add("camp_mundial_de_clubes_fifa", camps.get("Mundial de Clubes FIFA", True))
        _add("camp_campeonato_paulista", camps.get("Campeonato Paulista", True))
        _add("camp_conmebol_libertadores", camps.get("CONMEBOL Libertadores", True))
        _add("camp_conmebol_sudamericana", camps.get("CONMEBOL Sudamericana", True))

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(caminho, encoding="utf-8", xml_declaration=True)
    except Exception as e:
        logger.error(f"[Storage] Erro ao salvar config.xml: {e}")
