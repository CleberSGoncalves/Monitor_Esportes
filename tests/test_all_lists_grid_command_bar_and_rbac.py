import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

@pytest.fixture(scope="module")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    d = webdriver.Chrome(options=chrome_options)
    html_path = os.path.abspath("portal_web/index.html").replace("\\", "/")
    d.get(f"file:///{html_path}")
    time.sleep(1)
    yield d
    d.quit()

def test_all_lists_have_command_bar(driver):
    """Verifica se todas as listas possuem a barra de comandos SharePoint padrão"""
    panes = [
        "pane-streaming",
        "pane-ocorrencias",
        "pane-hospedeiros",
        "pane-antenistas",
        "pane-hosts",
        "pane-permissoes",
        "pane-list-viewer"
    ]
    for p in panes:
        pane_el = driver.find_element(By.ID, p)
        cmd_bar = pane_el.find_element(By.CLASS_NAME, "sp-command-bar")
        assert cmd_bar is not None, f"Barra de comandos ausente no pane {p}"
        # Verifica se tem botão + Novo e Atualizar
        btn_new = cmd_bar.find_element(By.CLASS_NAME, "sp-btn-new")
        assert btn_new is not None, f"Botão + Novo ausente na barra do pane {p}"

def test_streaming_new_modal_and_grid_edit(driver):
    """Testa criação e modo de exibição de grade na Programação Streaming"""
    driver.execute_script("showPane('streaming')")
    time.sleep(0.5)

    # 1. Abrir Modal de Novo Confronto
    driver.execute_script("openNewStreamModal()")
    time.sleep(0.3)
    modal = driver.find_element(By.ID, "modal-new-stream-event")
    assert modal.value_of_css_property("display") == "flex"

    driver.find_element(By.ID, "new-stream-partida").send_keys("Equipe Alfa x Equipe Beta")
    driver.find_element(By.ID, "new-stream-campeonato").send_keys("Torneio Automação")
    driver.find_element(By.ID, "new-stream-data").send_keys("20/11/2026")
    driver.find_element(By.ID, "new-stream-horario").send_keys("21:30")
    
    # Salvar
    driver.execute_script("saveNewStreamEvent(event)")
    time.sleep(0.5)

    # Verificar se aparece na tabela
    tbody = driver.find_element(By.ID, "table-body")
    assert "Equipe Alfa x Equipe Beta" in tbody.text

    # 2. Testar Modo de exibição de grade
    driver.execute_script("toggleStreamGridEdit()")
    time.sleep(0.3)
    alert = driver.find_element(By.ID, "stream-grid-mode-alert")
    assert alert.value_of_css_property("display") == "flex"

    # Verificar se células têm contenteditable
    editable_cell = tbody.find_element(By.CSS_SELECTOR, "div.sp-grid-cell")
    assert editable_cell is not None

    # Sair do modo grade
    driver.execute_script("toggleStreamGridEdit()")
    time.sleep(0.3)
    assert alert.value_of_css_property("display") == "none"

def test_hospedeiros_new_modal_and_grid_edit(driver):
    """Testa criação e modo de exibição de grade nos Contatos de Hospedeiros"""
    driver.execute_script("showPane('hospedeiros')")
    time.sleep(0.5)

    # 1. Abrir Modal de Novo Hospedeiro
    driver.execute_script("openNewHospedeiroModal()")
    time.sleep(0.3)
    modal = driver.find_element(By.ID, "modal-new-hospedeiro")
    assert modal.value_of_css_property("display") == "flex"

    driver.find_element(By.ID, "new-hosp-cidade").send_keys("Belo Horizonte / MG")
    driver.find_element(By.ID, "new-hosp-nome").send_keys("Técnico E2E Selenium")
    driver.find_element(By.ID, "new-hosp-telcom").send_keys("(31) 3333-4444")
    
    driver.execute_script("saveNewHospedeiro(event)")
    time.sleep(0.5)

    tbody = driver.find_element(By.ID, "hosp-table-body")
    assert "Técnico E2E Selenium" in tbody.text

    # 2. Testar Modo Grade Hospedeiros
    driver.execute_script("toggleHospGridEdit()")
    time.sleep(0.3)
    alert = driver.find_element(By.ID, "hosp-grid-mode-alert")
    assert alert.value_of_css_property("display") == "flex"

    driver.execute_script("toggleHospGridEdit()")
    time.sleep(0.3)
    assert alert.value_of_css_property("display") == "none"

def test_antenistas_and_hosts_grid_edit(driver):
    """Testa modo grade em antenistas e hosts"""
    # Antenistas
    driver.execute_script("showPane('antenistas')")
    time.sleep(0.3)
    driver.execute_script("toggleAnteGridEdit()")
    time.sleep(0.3)
    ante_alert = driver.find_element(By.ID, "ante-grid-mode-alert")
    assert ante_alert.value_of_css_property("display") == "flex"
    driver.execute_script("toggleAnteGridEdit()")
    time.sleep(0.3)

    # Hosts
    driver.execute_script("showPane('hosts')")
    time.sleep(0.3)
    driver.execute_script("toggleHostGridEdit()")
    time.sleep(0.3)
    hosts_alert = driver.find_element(By.ID, "hosts-grid-mode-alert")
    assert hosts_alert.value_of_css_property("display") == "flex"
    driver.execute_script("toggleHostGridEdit()")
    time.sleep(0.3)

def test_permissoes_new_and_grid_edit(driver):
    """Testa criação e edição de permissões RBAC"""
    driver.execute_script("showPane('permissoes')")
    time.sleep(0.5)

    # 1. Abrir Modal
    driver.execute_script("openNewPermModal()")
    time.sleep(0.3)
    modal = driver.find_element(By.ID, "modal-new-perm")
    assert modal.value_of_css_property("display") == "flex"

    driver.find_element(By.ID, "new-perm-nome").send_keys("Auditor Especialista E2E")
    driver.find_element(By.ID, "new-perm-email").send_keys("auditor.e2e@ibope.com")
    driver.execute_script("saveNewPerm(event)")
    time.sleep(0.5)

    tbody = driver.find_element(By.ID, "perms-table-body")
    assert "Auditor Especialista E2E" in tbody.text

    # 2. Modo Grade Permissões
    driver.execute_script("togglePermsGridEdit()")
    time.sleep(0.3)
    perms_alert = driver.find_element(By.ID, "perms-grid-mode-alert")
    assert perms_alert.value_of_css_property("display") == "flex"
    driver.execute_script("togglePermsGridEdit()")
    time.sleep(0.3)

def test_rbac_roles_visibility(driver):
    """Valida a restrição de botões conforme o perfil do usuário (RBAC)"""
    role_select = Select(driver.find_element(By.ID, "user-role-select"))

    # 1. Teste como Administrador (Gestor)
    role_select.select_by_value("admin")
    time.sleep(0.3)
    driver.execute_script("showPane('permissoes')")
    time.sleep(0.3)
    btn_new_perm = driver.find_element(By.CSS_SELECTOR, "#pane-permissoes .sp-btn-new")
    assert btn_new_perm.value_of_css_property("display") != "none", "Admin deve ver botão + Novo em permissões"

    # 2. Teste como Operador
    role_select.select_by_value("operador")
    time.sleep(0.3)
    assert btn_new_perm.value_of_css_property("display") == "none", "Operador NÃO deve ver botão + Novo em permissões"

    # Mas em streaming ou ocorrências, Operador deve ver botões de criação e modo grade!
    driver.execute_script("showPane('streaming')")
    time.sleep(0.3)
    btn_new_stream = driver.find_element(By.CSS_SELECTOR, "#pane-streaming .sp-btn-new")
    btn_grid_stream = driver.find_element(By.ID, "btn-grid-stream")
    assert btn_new_stream.value_of_css_property("display") != "none", "Operador deve ter botão + Novo no streaming"
    assert btn_grid_stream.value_of_css_property("display") != "none", "Operador deve ter botão Modo Grade no streaming"

    # 3. Teste como Visitante / Leitor (Consulta)
    role_select.select_by_value("leitor")
    time.sleep(0.3)
    assert btn_new_stream.value_of_css_property("display") == "none", "Leitor NÃO deve ver botão + Novo no streaming"
    assert btn_grid_stream.value_of_css_property("display") == "none", "Leitor NÃO deve ver botão Modo Grade no streaming"

    # Retorna para Admin
    role_select.select_by_value("admin")
    time.sleep(0.3)

def test_acesso_remoto_guatemala_rdp_drilldown(driver):
    """Verifica que a biblioteca Acesso Remoto permite navegar em Guatemala > Bloco 02 e ver os arquivos RDP reais"""
    # Abre o drive Acesso Remoto via menu
    driver.execute_script("handleMenuClick('remoto', '🎮 Acesso Remoto & América Central')")
    time.sleep(0.5)

    tbody = driver.find_element(By.ID, "drive-viewer-tbody")
    assert "Guatemala" in tbody.text, "Pasta Guatemala deve estar presente na raiz de Acesso Remoto"

    # Localiza ID da pasta Guatemala
    guat_id = driver.execute_script("""
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      const g = currentLevel.items.find(it => it.name === 'Guatemala');
      return g ? g.id : null;
    """)
    assert guat_id is not None, "ID da pasta Guatemala deve ser encontrado"

    # Entra na pasta Guatemala
    driver.execute_script(f"openDriveFolder('{guat_id}')")
    time.sleep(0.5)
    tbody = driver.find_element(By.ID, "drive-viewer-tbody")
    assert "Bloco 02" in tbody.text, "Bloco 02 deve estar dentro de Guatemala"

    # Localiza ID do Bloco 02
    b2_id = driver.execute_script("""
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      const b2 = currentLevel.items.find(it => it.name === 'Bloco 02');
      return b2 ? b2.id : null;
    """)
    assert b2_id is not None, "ID do Bloco 02 deve ser encontrado"

    # Entra na pasta Bloco 02
    driver.execute_script(f"openDriveFolder('{b2_id}')")
    time.sleep(0.5)
    tbody = driver.find_element(By.ID, "drive-viewer-tbody")

    # Verifica que NÃO está vazia e contém os arquivos .rdp reais!
    assert "Esta pasta está vazia" not in tbody.text
    assert "CS-GUA-CGT-BL02-01.rdp" in tbody.text or "CS-GUA-CGT-BL02-02.rdp" in tbody.text
    assert "Abrir ↗" in tbody.text
