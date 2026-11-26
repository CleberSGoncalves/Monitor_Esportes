"""
tests/test_audit_timestamps_and_broadcaster_fidelity.py
Testes automatizados que comprovam a resolução dos bugs reportados por Arthur Vinicius (25/11/2026):
1. Eliminação dos horários idênticos (19:15 / 19:30): cada relatório calcula os marcos a partir do horário real do jogo.
2. Trava de transmissão: apenas jogos transmitidos na CazéTV ou Amazon Prime Video geram relatórios.
3. Remoção de confrontos espúrios/fictícios (como Remo x Chapecoense na Série A com CazéTV).
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.autonomous_auditor import AutonomousAuditor
from modules.cbf_schedule_fetcher import get_real_cbf_fixtures, get_recent_finished_matches


def test_canonical_match_data_calculates_dynamic_timestamps():
    """Garante que jogos com horários distintos geram cronologias distintas e não mais 19:15/19:30 fixos."""
    auditor = AutonomousAuditor(email_recipients=["test@test.com"])

    # Jogo das 16:00 (ex: domingo à tarde)
    data_16h = auditor._build_canonical_match_data(
        "expert_time1_time2_16h",
        "TimeA x TimeB",
        {"team1": "TimeA", "team2": "TimeB", "date": "15/11/2026", "time": "16:00", "platform": "CazéTV"}
    )
    assert data_16h is not None
    assert data_16h["time"] == "16:00"
    assert data_16h["live_start_time"] == "15:45:00"
    assert data_16h["first_half_start"] == "16:00:00"
    assert data_16h["half_time_start"] == "16:48:00"
    assert data_16h["second_half_start"] == "17:03:00"

    # Jogo das 21:30 (ex: quarta-feira à noite)
    data_21h = auditor._build_canonical_match_data(
        "expert_time3_time4_21h",
        "TimeC x TimeD",
        {"team1": "TimeC", "team2": "TimeD", "date": "18/11/2026", "time": "21:30", "platform": "Amazon Prime"}
    )
    assert data_21h is not None
    assert data_21h["time"] == "21:30"
    assert data_21h["live_start_time"] == "21:15:00"
    assert data_21h["first_half_start"] == "21:30:00"
    assert data_21h["half_time_start"] == "22:18:00"
    assert data_21h["second_half_start"] == "22:33:00"

    # Garante que os horários são completamente diferentes
    assert data_16h["live_start_time"] != data_21h["live_start_time"]
    assert data_16h["first_half_start"] != data_21h["first_half_start"]


def test_broadcaster_filter_blocks_matches_outside_caze_and_amazon():
    """Garante que jogos fora de CazéTV / Amazon Prime (ex: Premiere, SporTV) são descartados."""
    auditor = AutonomousAuditor(email_recipients=["test@test.com"])

    # Simula lista com jogo do Premiere e jogo da CazéTV
    fake_finished = [
        {"team1": "Cruzeiro", "team2": "Palmeiras", "date": "18/11/2026", "time": "20:30", "platform": "Premiere", "comp": "Brasileirão Série A"},
        {"team1": "Coritiba", "team2": "Santos", "date": "18/11/2026", "time": "19:30", "platform": "CazéTV", "comp": "Brasileirão Série A"}
    ]

    # Mock get_recent_finished_matches
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("modules.cbf_schedule_fetcher.get_recent_finished_matches", lambda: fake_finished)
        # Mock SharePoint sync para não fazer chamadas de rede
        mp.setattr("modules.sharepoint_reporter.SharePointReporter.sync_pdf_to_sharepoint", lambda **kwargs: True)
        mp.setattr("modules.report_generator.ReportGenerator.write_expert_report", lambda *args, **kwargs: "dummy.pdf")

        recovered = auditor.check_and_recover_missing_cbf_matches(audited_reports=[])

        # Apenas Coritiba x Santos (CazéTV) deve ter sido recuperado; Cruzeiro x Palmeiras (Premiere) deve ser bloqueado
        rec_names = [r["partida"] for r in recovered]
        assert "Coritiba x Santos" in rec_names
        assert "Cruzeiro x Palmeiras" not in rec_names


def test_get_real_cbf_fixtures_does_not_contain_false_matches():
    """Garante que a lista de fixtures da CBF não contém partidas falsas reportadas por Arthur."""
    fixtures = get_real_cbf_fixtures()
    partidas = [f"{f['team1']} x {f['team2']}" for f in fixtures]

    # As 4 partidas reclamadas por Arthur não pertencem ao pacote CazéTV/Amazon naquelas datas
    assert "Remo x Chapecoense" not in partidas
    assert "Flamengo x Athletico-PR" not in partidas
    assert "Cruzeiro x Palmeiras" not in partidas
    assert "Corinthians x Botafogo" not in partidas

    # Todas as fixtures presentes devem ser estritamente CazéTV ou Amazon Prime
    for f in fixtures:
        assert f["platform"] in ["CazéTV", "Amazon Prime", "Amazon Prime Video"], f"Plataforma inválida encontrada: {f}"
