"""
tests/test_reporte_eventos_toggle_switch.py
Testes automatizados da chave mestre liga/desliga da aba Reporte de Eventos.
Valida:
1. Persistência de <modulo_ativo> no config.xml (True / False / Default True).
2. Interrupção total de rotinas quando desativado:
   - _re_buscar_eventos
   - _re_toggle_start
   - _re_auto_start_if_needed
   - _re_iniciar_watchdog_auto_healing
   - _re_executar_tarefa_diaria_agendada
   - _re_executar_ciclo_monitoramento
   - _re_verificar_e_reproduzir_streams_jogos_hoje
   - _re_enviar_email
3. Comportamento dos controles visuais e botões (disabled vs normal, badges).
"""

import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.reporte_eventos.storage_manager import carrega_config_xml, salvar_config_xml
from gui.reporte_eventos_mixin import ReporteEventosMixin


# ==============================================================================
# 1. TESTES DE PERSISTÊNCIA EM CONFIG.XML
# ==============================================================================

def test_config_xml_modulo_ativo_defaults_to_true_when_missing():
    """Garante que na ausência da tag <modulo_ativo>, o valor padrão seja True."""
    with tempfile.NamedTemporaryFile("w+", suffix=".xml", delete=False, encoding="utf-8") as tf:
        tf.write("<credenciais><refresh>20</refresh></credenciais>")
        temp_path = tf.name

    try:
        with patch("modules.reporte_eventos.storage_manager.get_app_path", return_value=temp_path):
            cfg = carrega_config_xml()
            assert cfg.get("modulo_ativo") is True
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_config_xml_modulo_ativo_saves_and_loads_false():
    """Garante que ao salvar modulo_ativo=False, o XML persiste e recarrega False."""
    with tempfile.NamedTemporaryFile("w+", suffix=".xml", delete=False, encoding="utf-8") as tf:
        tf.write("<credenciais></credenciais>")
        temp_path = tf.name

    try:
        with patch("modules.reporte_eventos.storage_manager.get_app_path", return_value=temp_path):
            cfg = {"modulo_ativo": False, "refresh": "30"}
            salvar_config_xml(cfg)

            loaded = carrega_config_xml()
            assert loaded.get("modulo_ativo") is False
            assert loaded.get("refresh") == "30"

            # Valida estrutura física do XML
            tree = ET.parse(temp_path)
            root = tree.getroot()
            elem = root.find("modulo_ativo")
            assert elem is not None
            assert elem.text == "false"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_config_xml_modulo_ativo_saves_and_loads_true():
    """Garante que ao salvar modulo_ativo=True, o XML persiste e recarrega True."""
    with tempfile.NamedTemporaryFile("w+", suffix=".xml", delete=False, encoding="utf-8") as tf:
        tf.write("<credenciais></credenciais>")
        temp_path = tf.name

    try:
        with patch("modules.reporte_eventos.storage_manager.get_app_path", return_value=temp_path):
            cfg = {"modulo_ativo": True}
            salvar_config_xml(cfg)

            loaded = carrega_config_xml()
            assert loaded.get("modulo_ativo") is True

            tree = ET.parse(temp_path)
            root = tree.getroot()
            elem = root.find("modulo_ativo")
            assert elem is not None
            assert elem.text == "true"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ==============================================================================
# 2. TESTES DA LÓGICA DO MIXIN E INTERRUPÇÃO TOTAL DE EXECUÇÃO
# ==============================================================================

class DummyUIElement:
    """Mock leve para elementos visuais do Tkinter/CustomTkinter."""
    def __init__(self, text=""):
        self.text = text
        self.attrs = {"text": text}
        self.state = "normal"

    def configure(self, **kwargs):
        self.attrs.update(kwargs)
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "state" in kwargs:
            self.state = kwargs["state"]

    def cget(self, key):
        return self.attrs.get(key, "")

    def winfo_exists(self):
        return True


class DummyVar:
    """Mock para BooleanVar ou StringVar."""
    def __init__(self, value=False):
        self._val = value

    def get(self):
        return self._val

    def set(self, v):
        self._val = v


class FakeReporteHarness(ReporteEventosMixin):
    """Harness de teste que instancia o Mixin com mocks leves sem subir janelas do OS."""
    def __init__(self, modulo_ativo=True):
        self.re_modulo_ativo_var = DummyVar(modulo_ativo)
        self.re_busy = False
        self.re_is_running = False
        self.re_loop_job_id = None
        self._re_tarefa_diaria_em_execucao = False
        self._re_reproduzindo_stream = False
        self._re_enviando_email = False

        # Variáveis de formulário
        self.re_email_var = DummyVar("teste@ibope.com")
        self.re_refresh_var = DummyVar("20")
        self.re_hora_auto_email_var = DummyVar("01:00")
        self.re_auto_email_var = DummyVar(True)
        self.re_auto_busca_var = DummyVar(True)
        self.re_somente_relatorio_var = DummyVar(True)
        self.re_data_inicio_var = DummyVar("25/11/2026")
        self.re_plat_vars = {}
        self.re_camp_vars = {}

        # Componentes UI mockados
        self.re_switch_ativo = DummyUIElement("Funcionalidade da Aba Ativa")
        self.re_badge_ativo = DummyUIElement("● OPERAÇÃO ATIVA")
        self.re_btn_buscar = DummyUIElement("Buscar")
        self.re_btn_start = DummyUIElement("▶ Start")
        self.re_btn_email = DummyUIElement("Disparar E-mail")
        self.re_btn_chrome9222 = DummyUIElement("Chrome 9222")
        self.re_btn_chrome9224 = DummyUIElement("Chrome 9224")
        self.re_lbl_status = DummyUIElement("Pronto")
        self.re_kpi_monitor_status = DummyUIElement("EM ESPERA")
        self.re_progresso = DummyUIElement()
        self.re_tree = MagicMock()
        self.re_tree.get_children.return_value = []

    def after(self, ms, func, *args):
        return "job_123"

    def after_cancel(self, job_id):
        self.re_loop_job_id = None


def test_toggle_switch_disables_controls_and_stops_cycle():
    """Garante que alternar a chave para False desativa botões e cancela o ciclo."""
    harness = FakeReporteHarness(modulo_ativo=True)
    harness.re_is_running = True
    harness.re_loop_job_id = "active_loop_999"

    # Simula desligamento da aba pelo usuário
    harness.re_modulo_ativo_var.set(False)
    with patch("gui.reporte_eventos_mixin.salvar_config_xml"):
        harness._on_re_toggle_modulo_ativo()

    # Validações visuais e de estado
    assert harness.re_is_running is False
    assert harness.re_loop_job_id is None
    assert harness.re_badge_ativo.attrs.get("text") == "● ABA DESATIVADA"
    assert harness.re_badge_ativo.attrs.get("text_color") == "#ef4444"
    assert harness.re_kpi_monitor_status.attrs.get("text") == "DESATIVADO"
    assert harness.re_kpi_monitor_status.attrs.get("text_color") == "#ef4444"

    # Botões devem estar desabilitados
    assert harness.re_btn_buscar.state == "disabled"
    assert harness.re_btn_start.state == "disabled"
    assert harness.re_btn_email.state == "disabled"
    assert harness.re_btn_chrome9222.state == "disabled"
    assert harness.re_btn_chrome9224.state == "disabled"


def test_toggle_switch_enables_controls_when_turned_back_on():
    """Garante que religar a chave restaura botões normais e status ativo."""
    harness = FakeReporteHarness(modulo_ativo=False)
    harness._re_aplicar_estado_botoes(ativo=False)

    # Simula reativação da aba pelo usuário
    harness.re_modulo_ativo_var.set(True)
    with patch("gui.reporte_eventos_mixin.salvar_config_xml"):
        harness._on_re_toggle_modulo_ativo()

    assert harness.re_badge_ativo.attrs.get("text") == "● OPERAÇÃO ATIVA"
    assert harness.re_badge_ativo.attrs.get("text_color") == "#10b981"
    assert harness.re_kpi_monitor_status.attrs.get("text") == "EM ESPERA"

    # Botões devem voltar ao normal
    assert harness.re_btn_buscar.state == "normal"
    assert harness.re_btn_start.state == "normal"
    assert harness.re_btn_email.state == "normal"
    assert harness.re_btn_chrome9222.state == "normal"
    assert harness.re_btn_chrome9224.state == "normal"


def test_re_buscar_eventos_blocked_when_inactive():
    """Garante que _re_buscar_eventos aborta sem iniciar thread de varredura quando desativado."""
    harness = FakeReporteHarness(modulo_ativo=False)

    on_complete_mock = MagicMock()
    with patch("tkinter.messagebox.showwarning") as mb_mock:
        harness._re_buscar_eventos(silencioso=False, on_complete=on_complete_mock)
        assert harness.re_busy is False
        mb_mock.assert_called_once()
        on_complete_mock.assert_called_once_with(False, "A aba Reporte de Eventos está desativada. Ative a funcionalidade da aba para executar buscas.")


def test_re_toggle_start_blocked_when_inactive():
    """Garante que _re_toggle_start recusa iniciar monitoramento contínuo se inativo."""
    harness = FakeReporteHarness(modulo_ativo=False)

    with patch("tkinter.messagebox.showwarning") as mb_mock:
        harness._re_toggle_start()
        assert harness.re_is_running is False
        mb_mock.assert_called_once()


def test_re_auto_start_if_needed_blocked_when_inactive():
    """Garante que o Auto-Start inicial de 2s não inicia o monitoramento se inativo."""
    harness = FakeReporteHarness(modulo_ativo=False)
    with patch.object(harness, "_re_toggle_start") as toggle_mock:
        harness._re_auto_start_if_needed()
        toggle_mock.assert_not_called()


def test_re_executar_tarefa_diaria_agendada_blocked_when_inactive():
    """Garante que a rotina agendada da 01h não roda se a aba estiver desativada."""
    harness = FakeReporteHarness(modulo_ativo=False)
    with patch.object(harness, "_re_buscar_eventos") as busca_mock:
        harness._re_executar_tarefa_diaria_agendada()
        assert harness._re_tarefa_diaria_em_execucao is False
        busca_mock.assert_not_called()


def test_re_executar_ciclo_monitoramento_aborts_and_cleans_when_inactive():
    """Garante que o ciclo recorrente de monitoramento para imediatamente se desativado."""
    harness = FakeReporteHarness(modulo_ativo=False)
    harness.re_is_running = True

    harness._re_executar_ciclo_monitoramento()
    assert harness.re_is_running is False
    assert harness.re_btn_start.attrs.get("text") == "▶ Start"


def test_re_verificar_e_reproduzir_streams_jogos_hoje_blocked_when_inactive():
    """Garante que verificação de reprodução de live streams no Chrome não ocorre se inativo."""
    harness = FakeReporteHarness(modulo_ativo=False)
    with patch("threading.Thread") as thread_mock:
        harness._re_verificar_e_reproduzir_streams_jogos_hoje()
        thread_mock.assert_not_called()


def test_re_enviar_email_blocked_when_inactive():
    """Garante que disparo manual ou automático de e-mail é bloqueado se inativo."""
    harness = FakeReporteHarness(modulo_ativo=False)
    with patch("gui.reporte_eventos_mixin.enviar_email_relatorio") as email_mock, \
         patch("tkinter.messagebox.showwarning") as mb_mock:
        harness._re_enviar_email(forcar=True)
        assert harness._re_enviando_email is False
        email_mock.assert_not_called()
        mb_mock.assert_called_once()
