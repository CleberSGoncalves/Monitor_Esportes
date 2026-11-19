import os, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

opts = Options()
opts.add_argument('--headless')
opts.add_argument('--window-size=1600,1000')
driver = webdriver.Chrome(options=opts)

try:
    html_file = os.path.abspath('docs/index.html').replace('\\', '/')
    driver.get(f'file:///{html_file}')
    time.sleep(1)

    print("=== TEST 1: ESCALA DE TRABALHO ===")
    driver.execute_script("showPane('escala');")
    time.sleep(0.2)
    pills = driver.find_elements(By.CSS_SELECTOR, '.month-pill-btn')
    print(f"Escala month pills: {len(pills)}")
    assert len(pills) >= 12, f"Expected at least 12 pills, got {len(pills)}"
    escala_rows = driver.find_elements(By.CSS_SELECTOR, '#escala-table-body tr')
    print(f"Escala rows: {len(escala_rows)}")
    assert len(escala_rows) >= 10, f"Expected at least 10 rows in Escala, got {len(escala_rows)}"

    print("\n=== TEST 2: HOSPEDEIROS (500) ===")
    driver.execute_script("showPane('hospedeiros');")
    time.sleep(0.2)
    hosp_rows = driver.find_elements(By.CSS_SELECTOR, '#hosp-table-body tr')
    print(f"Hospedeiros rows: {len(hosp_rows)}")
    assert len(hosp_rows) == 500, f"Expected 500 hospedeiros, got {len(hosp_rows)}"

    print("\n=== TEST 3: OCORRÊNCIAS (1000) ===")
    driver.execute_script("showPane('ocorrencias');")
    time.sleep(0.2)
    oco_rows_active = driver.find_elements(By.CSS_SELECTOR, '#oco-table-body tr')
    print(f"Ocorrências em andamento: {len(oco_rows_active)}")
    assert len(oco_rows_active) > 0, "Expected at least 1 ocorrência em andamento"
    
    # Switch to "Todos os Itens"
    driver.execute_script("switchOcoView('todos');")
    time.sleep(0.2)
    oco_rows_all = driver.find_elements(By.CSS_SELECTOR, '#oco-table-body tr')
    print(f"Ocorrências todos os itens: {len(oco_rows_all)}")
    assert len(oco_rows_all) >= 500, f"Expected at least 500 ocorrências in 'todos', got {len(oco_rows_all)}"

    print("\n=== TEST 4: PROGRAMAÇÃO STREAMING (862) ===")
    driver.execute_script("showPane('streaming');")
    time.sleep(0.2)
    stream_rows = driver.find_elements(By.CSS_SELECTOR, '#table-body tr')
    print(f"Streaming rows: {len(stream_rows)}")
    assert len(stream_rows) == 862, f"Expected 862 streaming events, got {len(stream_rows)}"

    print("\n=== TEST 5: FORNECEDORES (DRIVE) ===")
    driver.execute_script("showPane('fornecedores');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-drive-viewer', f"Expected pane-drive-viewer for fornecedores, got {pane}"
    forn_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Fornecedores drive rows: {len(forn_rows)}")
    assert len(forn_rows) >= 5, f"Expected at least 5 items in fornecedores, got {len(forn_rows)}"

    print("\n=== TEST 6: SLA (DRIVE) ===")
    driver.execute_script("showPane('sla');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-drive-viewer', f"Expected pane-drive-viewer for sla, got {pane}"
    sla_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"SLA drive rows: {len(sla_rows)}")
    assert len(sla_rows) >= 5, f"Expected at least 5 items in SLA, got {len(sla_rows)}"

    print("\n=== TEST 7: NOTIFICAÇÕES (DRIVE) ===")
    driver.execute_script("showPane('notificacoes');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-drive-viewer', f"Expected pane-drive-viewer for notificacoes, got {pane}"
    notif_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Notificações drive rows: {len(notif_rows)}")
    assert len(notif_rows) >= 5, f"Expected at least 5 items in Notificações, got {len(notif_rows)}"

    print("\n=== TEST 8: ACESSO REMOTO (DRIVE & RDP FILES) ===")
    driver.execute_script("showPane('remoto');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-drive-viewer', f"Expected pane-drive-viewer for remoto, got {pane}"
    remoto_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Acesso Remoto drive root rows: {len(remoto_rows)}")
    assert len(remoto_rows) >= 5, f"Expected at least 5 items in Acesso Remoto, got {len(remoto_rows)}"

    # Navigate into Guatemala -> Bloco 02
    driver.execute_script("""
      const guat = driveBreadcrumbs[0].items.find(it => it.name === 'Guatemala');
      openDriveFolder(guat.id);
    """)
    time.sleep(0.2)
    guat_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Guatemala children rows: {len(guat_rows)}")
    assert len(guat_rows) == 8, f"Expected 8 blocks in Guatemala, got {len(guat_rows)}"

    # Open Bloco 02
    driver.execute_script("""
      const currentLevel = driveBreadcrumbs[driveBreadcrumbs.length - 1];
      const b02 = currentLevel.items.find(it => it.name === 'Bloco 02');
      openDriveFolder(b02.id);
    """)
    time.sleep(0.2)
    b02_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Bloco 02 files rows: {len(b02_rows)}")
    assert len(b02_rows) == 2, f"Expected 2 RDP files in Bloco 02, got {len(b02_rows)}"
    b02_text = driver.find_element(By.ID, 'drive-viewer-tbody').text
    assert 'CS-GUA-CGT-BL02-01.rdp' in b02_text
    assert 'CS-GUA-CGT-BL02-02.rdp' in b02_text
    print("Guatemala > Bloco 02 RDP files verified with 100% success!")

    print("\n=== TEST 9: OS 3 RELATÓRIOS SEPARADOS (DRIVES) ===")
    driver.execute_script("showPane('relatorios_futebol');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-drive-viewer'
    fut_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Relatórios de Jogos Futebol: {len(fut_rows)} files")
    assert len(fut_rows) == 41

    driver.execute_script("showPane('relatorios_youtube');")
    time.sleep(0.2)
    yt_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Relatório Jogos Youtube: {len(yt_rows)} files")
    assert len(yt_rows) == 51

    driver.execute_script("showPane('relatorios_nba');")
    time.sleep(0.2)
    nba_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
    print(f"Relatórios de Jogos NBA: {len(nba_rows)} files")
    assert len(nba_rows) == 168

    print("\n=== TEST 10: DASHBOARD & INDICADORES (POWER BI OFICIAL) ===")
    driver.execute_script("showPane('dashboard');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-dashboard'
    dash_text = driver.find_element(By.ID, 'pane-dashboard').text
    assert 'Suporte N2 (Redmine)' in dash_text
    assert 'Suporte N1 (Recuperação e Monitor de Incidentes)' in dash_text
    assert 'Power BI' in dash_text
    print("Dashboard verified with authentic Power BI panels!")

    print("\n=== TEST 11: CONTROLE DE ACESSOS & RBAC (52) ===")
    driver.execute_script("showPane('permissoes');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-permissoes', f"Expected pane-permissoes, got {pane}"
    perm_rows = driver.find_elements(By.CSS_SELECTOR, '#perms-table-body tr')
    print(f"Permissões rows: {len(perm_rows)}")
    assert len(perm_rows) == 52, f"Expected 52 permissions, got {len(perm_rows)}"
    
    # Test search filter
    search_box = driver.find_element(By.ID, 'search-perm-box')
    search_box.send_keys('Cleber')
    time.sleep(0.2)
    search_rows = driver.find_elements(By.CSS_SELECTOR, '#perms-table-body tr')
    print(f"Permissões search 'Cleber': {len(search_rows)}")
    assert len(search_rows) == 2, f"Expected 2 matches for Cleber, got {len(search_rows)}"
    search_box.clear()
    driver.execute_script("document.getElementById('search-perm-box').value = ''; renderPermsTable();")

    print("\n=== TEST 12: ESCALA DE TRABALHO (DESVINCULAÇÃO SHAREPOINT & GOVERNANÇA) ===")
    driver.execute_script("showPane('escala');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-escala'
    escala_html = driver.find_element(By.ID, 'pane-escala').get_attribute('outerHTML')
    assert 'adgbl.sharepoint.com' not in escala_html, "Nenhum link para o SharePoint legado pode existir na escala"
    assert 'Editar no Excel Online' not in escala_html, "Link antigo Editar no Excel Online deve estar removido"
    assert 'escala-perm-badge' in escala_html, "Badge de governança de permissão da escala deve estar presente"

    # Open drive_escala
    driver.execute_script("showPane('drive_escala');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-drive-viewer'
    escala_drive_text = driver.find_element(By.ID, 'drive-viewer-tbody').text
    assert 'Escala de trabalho 2026.xlsx' in escala_drive_text
    print("Escala de Trabalho desvinculação e governança verificadas com 100% de sucesso!")

    print("\n=== TEST 13: PÁGINA INICIAL (MONITOR 8092, ORGANOGRAMA, GOOGLE CHAT) ===")
    driver.execute_script("showPane('home');")
    time.sleep(0.2)
    pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
    assert pane == 'pane-home', f"Expected pane-home, got {pane}"
    home_text = driver.find_element(By.ID, 'pane-home').text
    home_html = driver.find_element(By.ID, 'pane-home').get_attribute('outerHTML')
    assert '10.1.30.1:8092' in home_html
    assert 'Monitor de Incidentes (Monitor_Serviços)' in home_text
    assert 'Conheça Nossa Equipe' in home_text
    assert 'Luiz De Sa Lemos' in home_text
    assert 'Cleber De Souza Gonçalves' in home_text
    assert 'chat.google.com' in home_html
    assert 'Google Chat' in home_text
    print("Página Inicial with Incident Monitor, Organograma & Google Chat verified with 100% success!")

    print("\n========================================================")
    print("ALL 13 VERIFICATIONS PASSED WITH 100% SUCCESS!")
    print("========================================================")

finally:
    driver.quit()
