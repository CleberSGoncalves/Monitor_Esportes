import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

@pytest.fixture(scope="module")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    d = webdriver.Chrome(options=chrome_options)
    html_path = os.path.abspath("portal_web/index.html").replace("\\", "/")
    d.get(f"file:///{html_path}")
    time.sleep(1)
    yield d
    d.quit()

def test_streaming_highlights_panel_and_default_sort(driver):
    """Verifica que a Programação Streaming tem o quadro de destaque de HOJE e AMANHÃ e vem ordenada por data decrescente"""
    driver.execute_script("showPane('streaming');")
    time.sleep(0.5)

    # 1. Container de Destaques
    panel = driver.find_element(By.ID, "streaming-highlights-panel")
    assert panel.is_displayed(), "Painel de Destaques (Hoje / Amanhã) deve estar visível"
    panel_text = panel.text
    assert "CONFRONTOS PROGRAMADOS PARA HOJE" in panel_text, "Quadro de Hoje deve estar presente"
    assert "PROGRAMAÇÃO DE AMANHÃ" in panel_text, "Quadro de Amanhã deve estar presente"

    # 2. Checkboxes de seleção em lote existem na tabela
    checkall = driver.find_element(By.ID, "checkall-stream")
    assert checkall is not None, "Checkbox checkall deve existir no thead da Programação Streaming"
    
    # Selecionar todos os eventos
    driver.execute_script("document.getElementById('checkall-stream').click();")
    time.sleep(0.3)
    btn_del = driver.find_element(By.ID, "btn-delete-stream-selected")
    assert btn_del.is_displayed(), "Botão Excluir Selecionados deve aparecer ao marcar checkboxes"

def test_game_reports_sharepoint_table_and_badges(driver):
    """Verifica se os relatórios de jogos exibem as colunas especializadas 1:1 com o SharePoint e badges oficiais"""
    # 1. Futebol (Relatorios_de_Jogos)
    driver.execute_script("openDrive('Relatorios_de_Jogos', '⚽ Relatórios de Jogos');")
    time.sleep(0.5)

    thead = driver.find_element(By.ID, "drive-viewer-thead")
    thead_text = thead.text
    assert "Data / Hora" in thead_text, "Coluna Data / Hora deve estar no thead de Futebol"
    assert "Campeonato" in thead_text, "Coluna Campeonato deve estar no thead"
    assert "Partida" in thead_text, "Coluna Partida deve estar no thead"
    assert "Plataforma" in thead_text, "Coluna Plataforma deve estar no thead"
    assert "Auditado" in thead_text, "Coluna Auditado deve estar no thead"
    assert "PDF Oficial" in thead_text, "Coluna PDF Oficial deve estar no thead"

    tbody = driver.find_element(By.ID, "drive-viewer-tbody")
    tbody_text = tbody.text
    assert "Brasileiro Serie A" in tbody_text or "Copa do Brasil" in tbody_text, "Badges de Campeonato devem ser renderizados"
    assert "Caze TV" in tbody_text or "Amazon Prime" in tbody_text, "Badges de Plataforma devem ser renderizados"

    # 2. YouTube (Relatorio Jogos Youtube)
    driver.execute_script("openDrive('Relatorio Jogos Youtube', '🔴 Relatórios YouTube');")
    time.sleep(0.5)
    tbody_yt = driver.find_element(By.ID, "drive-viewer-tbody")
    assert "Bagé TV" in tbody_yt.text or "ATL TV" in tbody_yt.text, "Canais do YouTube devem ser renderizados com badges"

    # 3. NBA (Relatorios_de_Jogos_NBA)
    driver.execute_script("openDrive('Relatorios_de_Jogos_NBA', '🏀 Relatórios NBA');")
    time.sleep(0.5)
    tbody_nba = driver.find_element(By.ID, "drive-viewer-tbody")
    assert "NBA" in tbody_nba.text, "Badge NBA deve ser exibido"
    assert "x" in tbody_nba.text or "Homologado" in tbody_nba.text or "Agendado" in tbody_nba.text

def test_bulk_selection_and_rbac_protection(driver):
    """Verifica se a seleção em lote e exclusão respeitam rigorosamente o RBAC"""
    driver.execute_script("openDrive('Relatorios_de_Jogos', '⚽ Relatórios de Jogos');")
    time.sleep(0.5)

    # 1. Checkall em Drive de Relatórios
    checkall = driver.find_element(By.ID, "checkall-drive")
    driver.execute_script("document.getElementById('checkall-drive').click();")
    time.sleep(0.3)
    btn_del = driver.find_element(By.ID, "btn-delete-drive-selected")
    assert btn_del.is_displayed(), "Botão Excluir Selecionados deve aparecer em Drive ao marcar checkall"

    # 2. Como Admin / Operador, exclusão é permitida (cancela no confirm)
    can_admin_del = driver.execute_script("return canUserDelete();")
    assert can_admin_del is True, "Admin deve ter permissão de exclusão"

    # 3. Mudar para perfil Leitor / Visitante
    driver.execute_script("document.getElementById('user-role-select').value = 'leitor'; onRoleChange();")
    time.sleep(0.3)
    can_leitor_del = driver.execute_script("return canUserDelete();")
    assert can_leitor_del is False, "Leitor / Visitante NÃO pode ter permissão de exclusão"

    # Restaurar Admin
    driver.execute_script("document.getElementById('user-role-select').value = 'admin'; onRoleChange();")
    time.sleep(0.3)
