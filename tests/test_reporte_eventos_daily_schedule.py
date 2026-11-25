# -*- coding: utf-8 -*-
"""
Testes automatizados para validação da tarefa diária agendada (01h / hora_automatico)
e paridade completa com o Streaming_Scheduler no ReporteEventosMixin.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import customtkinter as ctk

from gui.reporte_eventos_mixin import ReporteEventosMixin


class DummyTree:
    """Mock leve do ttk.Treeview para testes rápidos."""
    def __init__(self):
        self.items = {}
        self._counter = 0

    def insert(self, parent, index, values=()):
        self._counter += 1
        iid = f"item_{self._counter}"
        self.items[iid] = list(values)
        return iid

    def get_children(self):
        return list(self.items.keys())

    def item(self, iid, option=None):
        if option == "values":
            return self.items.get(iid, [])
        return {"values": self.items.get(iid, [])}

    def delete(self, iid):
        if iid in self.items:
            del self.items[iid]


class DummyReporteApp(ReporteEventosMixin):
    """Subclasse de teste que inicializa os atributos do ReporteEventosMixin sem janela Tk."""
    def __init__(self):
        self.re_is_running = True
        self.re_busy = False
        self._re_enviando_email = False
        self._re_ultimo_agendamento_data = None
        self._re_ultima_hora_config = "01:00"
        self._re_tarefa_diaria_em_execucao = False
        self._re_streams_reproduzidos_hoje = set()
        self._re_reproduzindo_stream = False

        self.re_data_inicio_var = MagicMock()
        self.re_data_inicio_var.get.return_value = "01/01/2026"
        self.re_hora_auto_email_var = MagicMock()
        self.re_hora_auto_email_var.get.return_value = "01:00"
        self.re_auto_email_var = MagicMock()
        self.re_auto_email_var.get.return_value = True
        self.re_auto_busca_var = MagicMock()
        self.re_auto_busca_var.get.return_value = True
        self.re_somente_relatorio_var = MagicMock()
        self.re_somente_relatorio_var.get.return_value = True
        self.re_refresh_var = MagicMock()
        self.re_refresh_var.get.return_value = "20"

        self.re_lbl_status = MagicMock()
        self.re_lbl_process = MagicMock()
        self.re_progresso = MagicMock()
        self.re_btn_buscar = MagicMock()

        self.re_tree = DummyTree()
        self.re_plat_vars = {"CBF": MagicMock(), "Amazon Prime": MagicMock()}
        for k, v in self.re_plat_vars.items():
            v.get.return_value = True
        self.re_camp_vars = {"Brasileirão serie A": MagicMock()}
        for k, v in self.re_camp_vars.items():
            v.get.return_value = True

    def after(self, delay, callback, *args):
        # Simula agendamento de timer do Tkinter sem bloquear
        return "job_id_test"

    def _re_atualizar_kpis(self):
        pass

    def _re_salvar_config_atual(self):
        pass


class TestReporteEventosDailySchedule(unittest.TestCase):

    def setUp(self):
        self.app = DummyReporteApp()

    def test_ciclo_monitoramento_triggers_scheduled_task_at_target_time(self):
        """Valida que quando o horário (01:00) chega, o ciclo dispara _re_executar_tarefa_diaria_agendada."""
        agora = datetime.now()
        hora_alvo = (agora - timedelta(minutes=5)).strftime("%H:%M")
        self.app.re_hora_auto_email_var.get.return_value = hora_alvo
        # Simula que a última execução foi ontem
        self.app._re_ultimo_agendamento_data = (agora - timedelta(days=1)).date()

        with patch.object(self.app, "_re_executar_tarefa_diaria_agendada") as mock_exec:
            self.app._re_executar_ciclo_monitoramento()
            mock_exec.assert_called_once()
            self.assertEqual(self.app._re_ultimo_agendamento_data, agora.date())

    def test_ciclo_monitoramento_does_not_trigger_twice_on_same_day(self):
        """Valida que não executa repetidamente no mesmo dia."""
        agora = datetime.now()
        hora_alvo = (agora - timedelta(minutes=5)).strftime("%H:%M")
        self.app.re_hora_auto_email_var.get.return_value = hora_alvo
        # Já executou hoje!
        self.app._re_ultimo_agendamento_data = agora.date()

        with patch.object(self.app, "_re_executar_tarefa_diaria_agendada") as mock_exec:
            self.app._re_executar_ciclo_monitoramento()
            mock_exec.assert_not_called()

    def test_ciclo_monitoramento_boot_does_not_trigger_retroactively_if_past(self):
        """No boot (quando _ultimo_agendamento_data é None), se o horário já passou hoje, agenda para amanhã."""
        agora = datetime.now()
        hora_passada = (agora - timedelta(minutes=10)).strftime("%H:%M")
        self.app.re_hora_auto_email_var.get.return_value = hora_passada
        self.app._re_ultimo_agendamento_data = None

        with patch.object(self.app, "_re_executar_tarefa_diaria_agendada") as mock_exec:
            self.app._re_executar_ciclo_monitoramento()
            mock_exec.assert_not_called()
            # Deve marcar como data de hoje para esperar a próxima volta de amanhã
            self.assertEqual(self.app._re_ultimo_agendamento_data, agora.date())

    def test_executar_tarefa_diaria_updates_date_to_today_and_starts_search(self):
        """Valida que a tarefa diária atualiza a data da busca para hoje e dispara _re_buscar_eventos silencioso."""
        hoje_str = datetime.now().strftime("%d/%m/%Y")
        self.app.re_auto_busca_var.get.return_value = True

        with patch.object(self.app, "_re_buscar_eventos") as mock_busca:
            self.app._re_executar_tarefa_diaria_agendada()

            # Data de início deve ser atualizada para hoje
            self.app.re_data_inicio_var.set.assert_called_with(hoje_str)
            mock_busca.assert_called_once_with(
                silencioso=True,
                on_complete=self.app._re_pos_busca_tarefa_diaria
            )
            self.assertTrue(self.app._re_tarefa_diaria_em_execucao)

    def test_pos_busca_tarefa_diaria_syncs_sharepoint_google_and_sends_email(self):
        """Valida que após a busca, sincroniza SharePoint, Google Sheets e dispara o e-mail."""
        # Insere linhas simuladas na grade
        self.app.re_tree.insert("", "end", values=[
            "CBF - Brasileirão Série A",
            "Flamengo x Palmeiras",
            datetime.now().strftime("%d/%m/%Y"),
            "16:00",
            "ESQUERDA",
            "10",
            "Amazon Prime",
            "https://primevideo.com/event/1"
        ])

        with patch("gui.reporte_eventos_mixin.push_events_from_tuples") as mock_sp_sync, \
             patch("gui.reporte_eventos_mixin.trigger_parallel_google_sheets_sync") as mock_gs_sync, \
             patch.object(self.app, "_re_enviar_email") as mock_email:

            mock_sp_sync.return_value = {"inserted": 1, "skipped_existing": 0}

            self.app._re_pos_busca_tarefa_diaria(sucesso=True, msg="Ok")

            # Verifica chamadas com os dados da grade
            mock_sp_sync.assert_called_once()
            mock_gs_sync.assert_called_once()
            mock_email.assert_called_once_with(forcar=False)
            self.assertFalse(self.app._re_tarefa_diaria_em_execucao)

    def test_verificar_e_reproduzir_streams_jogos_hoje(self):
        """Valida que jogos de hoje cujo horário - min_antes já chegou disparam o worker de stream."""
        hoje_str = date.today().strftime("%d/%m/%Y")
        agora = datetime.now()
        # Jogo daqui a 5 minutos, com antecedência de 10 minutos (ou seja, já deve abrir!)
        hora_jogo = (agora + timedelta(minutes=5)).strftime("%H:%M")

        self.app.re_tree.insert("", "end", values=[
            "CBF - Brasileirão Série A",
            "Corinthians x Santos",
            hoje_str,
            hora_jogo,
            "ESQUERDA",
            "10",
            "Amazon Prime",
            "https://primevideo.com/event/test"
        ])

        with patch.object(self.app, "_re_worker_reproduzir_stream") as mock_worker:
            self.app._re_verificar_e_reproduzir_streams_jogos_hoje()
            # Chave foi registrada nos reproduzidos
            self.assertTrue(len(self.app._re_streams_reproduzidos_hoje) > 0)


if __name__ == "__main__":
    unittest.main()
