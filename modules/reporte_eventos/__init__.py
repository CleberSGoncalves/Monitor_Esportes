# -*- coding: utf-8 -*-
"""
Pacote Reporte de Eventos — Integração completa e nativa do Streaming_Scheduler no Monitor_Esportes.
Centraliza extração CBF PDF, Copa do Mundo, varreduras de canais do YouTube,
sincronização SharePoint Graph API, automações Chrome DevTools e disparos de e-mail.
"""

from .crypto_utils import (
    get_app_path,
    get_config_dir,
    criptografar,
    descriptografar,
    get_config_value,
    get_auth_value,
    get_env_value,
)

from .sharepoint_client import (
    push_events_to_sharepoint,
    _deep_normalize_partida,
    _mapear_canal,
    _obter_titulo_oficial_campeonato,
    CANONICAL_CHAMPIONSHIP_TITLES,
)

from .cbf_pdf_service import (
    get_latest_cbf_url,
    get_cbf_rights_index,
    is_cbf_broadcast_authorized,
    parse_cbf_pdf,
    parse_copa_mundo_excel,
    prettify_match_name,
    canonical_team_name,
)

from .youtube_scanner_service import (
    extrair_partida_youtube,
    parse_youtube_title,
    obter_eventos_canal_youtube,
    obter_eventos_caze_tv,
    norm,
)

from .selenium_browser_service import (
    verificar_chrome_debug,
    abrir_chrome,
    fechar_chrome_seguro,
    obter_driver_conectado,
)

from .email_report_service import (
    extrair_dados_html,
    enviar_email_relatorio,
)

from .storage_manager import (
    carregar_youtube_channels_config,
    salvar_youtube_channels_config,
    carregar_campeonatos_config,
    salvar_campeonatos_config,
    DEFAULT_CAMPEONATOS,
    carregar_streaming_csv,
    salvar_streaming_csv,
    carrega_config_xml,
    salvar_config_xml,
)

__all__ = [
    "get_app_path",
    "get_config_dir",
    "criptografar",
    "descriptografar",
    "get_config_value",
    "get_auth_value",
    "get_env_value",
    "push_events_to_sharepoint",
    "_deep_normalize_partida",
    "_mapear_canal",
    "_obter_titulo_oficial_campeonato",
    "CANONICAL_CHAMPIONSHIP_TITLES",
    "get_latest_cbf_url",
    "get_cbf_rights_index",
    "is_cbf_broadcast_authorized",
    "parse_cbf_pdf",
    "parse_copa_mundo_excel",
    "prettify_match_name",
    "canonical_team_name",
    "extrair_partida_youtube",
    "parse_youtube_title",
    "obter_eventos_canal_youtube",
    "obter_eventos_caze_tv",
    "norm",
    "verificar_chrome_debug",
    "abrir_chrome",
    "fechar_chrome_seguro",
    "obter_driver_conectado",
    "extrair_dados_html",
    "enviar_email_relatorio",
    "carregar_youtube_channels_config",
    "salvar_youtube_channels_config",
    "carregar_campeonatos_config",
    "salvar_campeonatos_config",
    "DEFAULT_CAMPEONATOS",
    "carregar_streaming_csv",
    "salvar_streaming_csv",
    "carrega_config_xml",
    "salvar_config_xml",
]
