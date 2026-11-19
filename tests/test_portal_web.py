# -*- coding: utf-8 -*-
import os
import pytest
from scripts.build_portal_web import generate_portal

def test_build_portal_web_creates_file():
    html_path = generate_portal()
    assert os.path.exists(html_path)
    assert os.path.getsize(html_path) > 100000

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verifica blocos essenciais da intranet
    assert "Suporte Captação | Streaming Operations Hub" in content
    assert "Programação Streaming" in content
    assert "Receptores & TV BOX" in content
    assert "Equipe & Escala de Plantão" in content
    assert "Links & Sistemas Oficiais" in content
    assert "Métricas & Auditorias" in content
    assert "allEvents" in content
    assert "PV3623" in content  # Cazé TV PVID
    assert "PV3687" in content  # Prime Video PVID
    assert "PV3679" in content  # Netflix PVID
