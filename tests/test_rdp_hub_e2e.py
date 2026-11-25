from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=options)
try:
    url = "file:///E:/desenvolvimento/Monitor_Esportes/portal_web/index.html"
    driver.get(url)
    time.sleep(2)
    
    # 1. Checar título
    title = driver.title
    print(f"[TESTE] Titulo da pagina: {title}")
    
    # 2. Navegar para a aba de RDP via showPane('remoto')
    driver.execute_script("showPane('remoto');")
    time.sleep(1)
    
    # 3. Verificar linhas no rdp-table-body
    rows = driver.find_elements(By.CSS_SELECTOR, "#rdp-table-body tr")
    print(f"[TESTE] Linhas renderizadas na tabela RDP: {len(rows)}")
    assert len(rows) == 151, f"Esperado 151 linhas, mas obteve {len(rows)}"
    
    # 4. Verificar se o botao de Drive local esta presente e o do SharePoint foi removido
    btn_text = driver.find_element(By.CSS_SELECTOR, "#pane-remoto .sp-command-left").text
    print(f"[TESTE] Botoes na barra RDP: {btn_text}")
    assert "SharePoint" not in btn_text, "Ainda contem SharePoint no texto do botao!"
    assert "Biblioteca de Pastas RDP" in btn_text, "Botao Biblioteca de Pastas RDP nao encontrado!"
    
    # 5. Testar abertura do modal de conexao RDP
    driver.execute_script("openRdpConnectModal('192.168.176.20', 'Altamira', 'CS1', 'Brasil', '192.168.176.29', '192.168.176.19', 'MCosta');")
    time.sleep(0.5)
    modal = driver.find_element(By.ID, "modal-rdp-connect")
    assert modal.is_displayed(), "Modal de conexao RDP nao esta visivel!"
    modal_title = driver.find_element(By.ID, "rdp-modal-title").get_attribute("textContent")
    print(f"[TESTE] Modal RDP aberto com sucesso: {modal_title}")
    assert "Altamira" in modal_title
    
    # 6. Fechar modal
    driver.execute_script("closeRdpModal();")
    time.sleep(0.5)
    assert not modal.is_displayed(), "Modal nao fechou!"
    print("\n[SUCESSO COMPLETO] Todos os testes E2E do Centro de Gerenciamento RDP passaram com 100% de sucesso!")
finally:
    driver.quit()
