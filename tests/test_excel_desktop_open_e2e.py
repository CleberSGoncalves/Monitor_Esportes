# -*- coding: utf-8 -*-
import os
import sys
import time
import zipfile
import tempfile
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

@pytest.fixture(scope="module")
def download_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_excel_download_")
    yield temp_dir
    # Cleanup
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

@pytest.fixture(scope="module")
def driver(download_dir):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--allow-file-access-from-files")
    chrome_options.add_argument("--window-size=1920,1080")
    
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    d = webdriver.Chrome(options=chrome_options)
    # Enable download in headless Chrome
    d.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": download_dir
    })
    
    html_path = os.path.abspath(os.path.join(PROJECT_ROOT, "docs", "index.html")).replace("\\", "/")
    d.get(f"file:///{html_path}")
    time.sleep(2)
    yield d
    d.quit()

def test_excel_desktop_button_downloads_authentic_xlsx(driver, download_dir):
    """
    Testa se o botão 'Abrir no Excel (Desktop)' baixa o arquivo autêntico .xlsx
    sem invocar ms-excel:ofe|u|... que causava erro WebDAV no Excel.
    """
    doc_name = "Acomp. SLA Interno-Globo - Abril 2026.xlsx"
    doc_name_esc = "Acomp.%20SLA%20Interno-Globo%20-%20Abril%202026.xlsx"
    
    # 1. Abrir o modal de edição de planilha
    driver.execute_script(f"openOnlineSheetEditor('{doc_name_esc}');")
    
    # Aguardar modal aparecer
    modal = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "modal-online-sheet-editor"))
    )
    assert modal is not None
    assert modal.is_displayed()
    
    # 2. Localizar botão 'Abrir no Excel (Desktop)'
    btn_excel = driver.find_element(By.ID, "btn-open-desktop-excel")
    assert btn_excel is not None
    assert "Abrir no Excel" in btn_excel.text
    
    # 3. Verificar botão de Arquivo Local (presente no protocolo file:///)
    btn_local = driver.find_element(By.ID, "btn-open-local-file")
    assert btn_local is not None
    assert "Arquivo Local" in btn_local.text
    
    # Clicar no botão local para testar que não causa erro
    btn_local.click()
    time.sleep(0.5)

    # 4. Clicar no botão 'Abrir no Excel (Desktop)'
    btn_excel.click()
    
    # 5. Aguardar o download do arquivo no diretório temporário
    downloaded_file = os.path.join(download_dir, doc_name)
    max_wait = 15
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        if os.path.exists(downloaded_file) and not downloaded_file.endswith(".crdownload"):
            break
        # Procurar qualquer arquivo .xlsx baixado
        xlsx_files = [f for f in os.listdir(download_dir) if f.endswith(".xlsx")]
        if xlsx_files:
            downloaded_file = os.path.join(download_dir, xlsx_files[0])
            break
        time.sleep(0.5)
        
    assert os.path.exists(downloaded_file), f"O arquivo {doc_name} não foi baixado na pasta de download: {os.listdir(download_dir)}"
    
    # 6. Validar que o arquivo é um .xlsx real e autêntico
    file_size = os.path.getsize(downloaded_file)
    assert file_size > 10000, f"Arquivo baixado muito pequeno ({file_size} bytes), esperado > 10KB"
    
    # Validar que é um arquivo ZIP válido (estrutura OpenXML do .xlsx)
    assert zipfile.is_zipfile(downloaded_file), "O arquivo baixado não é um .xlsx (OpenXML ZIP) válido!"
    
    with zipfile.ZipFile(downloaded_file, 'r') as zf:
        namelist = zf.namelist()
        assert "[Content_Types].xml" in namelist
        assert any("xl/worksheets/" in name for name in namelist)
        
    print(f"Sucesso! Arquivo '{os.path.basename(downloaded_file)}' baixado com {file_size} bytes e validado como OpenXML .xlsx autêntico.")

def test_zero_uncaught_console_errors(driver):
    """Garante que a execução do clique e scripts não gerou erros de console uncaught"""
    logs = driver.get_log("browser")
    severe_errors = [log for log in logs if log["level"] == "SEVERE" and "favicon" not in log["message"].lower()]
    assert len(severe_errors) == 0, f"Erros graves no console do navegador: {severe_errors}"
