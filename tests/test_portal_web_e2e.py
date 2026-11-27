import os
import re
import subprocess
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_syntax():
    print("--- 1. VALIDANDO SINTAXE JS COM NODE -C ---")
    html_path = r'E:\desenvolvimento\Monitor_Esportes\docs\index.html'
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    scripts = re.findall(r'<script(?:\s+[^>]*)?>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    print(f"Total de blocos de script encontrados: {len(scripts)}")
    
    for idx, s in enumerate(scripts):
        if not s.strip():
            continue
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as tmp:
            tmp.write(s)
            tmp_path = tmp.name
        try:
            res = subprocess.run(['node', '-c', tmp_path], capture_output=True, text=True, check=True)
            print(f"  Script #{idx+1}: OK (Sintaxe válida)")
        except subprocess.CalledProcessError as e:
            print(f"  Script #{idx+1} ERRO:\n{e.stderr}")
            raise
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

def test_selenium_e2e():
    print("\n--- 2. EXECUTANDO TESTE AUTOMATIZADO E2E COM SELENIUM CHROME ---")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1600,1000')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    try:
        portal_url = 'file:///' + r'E:/desenvolvimento/Monitor_Esportes/docs/index.html'.replace('\\', '/')
        print(f"Navegando para: {portal_url}")
        driver.get(portal_url)
        time.sleep(2)
        
        # 1. Testar biblioteca "Relatorios_de_Jogos" (Futebol)
        print("\n[TEST 1] Abrindo biblioteca 'Relatorios_de_Jogos' (Futebol)...")
        driver.execute_script("openDrive('Relatorios_de_Jogos', 'Relatórios de Jogos');")
        time.sleep(1)
        
        # Verificar ícone de ordenação padrão (Data ▼)
        ico_data = driver.find_element(By.ID, 'sort-ico-Data').text
        print(f"  Ícone padrão Data: '{ico_data}' (Esperado: '▼')")
        assert '▼' in ico_data, f"Esperado ▼ em Data, obtido {ico_data}"
        
        # Verificar linhas renderizadas
        rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        print(f"  Total de relatórios de Futebol exibidos: {len(rows)}")
        assert len(rows) > 0, "Nenhuma linha renderizada em Relatorios_de_Jogos"
        
        # Verificar que a primeira linha NÃO é um mock ou inválido
        first_row_text = rows[0].text
        print(f"  Linha #1: {first_row_text[:80]}...")
        assert "test_auto_audit_unit_test" not in first_row_text, "Mock test_auto_audit_unit_test ainda presente!"
        
        # Testar ordenação clicando na coluna "Campeonato"
        print("  Testando clique no cabeçalho 'Campeonato' (ordenação A-Z)...")
        th_camp = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-thead th.th-sortable[onclick*='Campeonato']")
        driver.execute_script("arguments[0].click();", th_camp)
        time.sleep(0.5)
        ico_camp = driver.find_element(By.ID, 'sort-ico-Campeonato').text
        print(f"  Ícone Campeonato após 1º clique: '{ico_camp}' (Esperado: '▲')")
        assert '▲' in ico_camp, f"Esperado ▲ em Campeonato, obtido {ico_camp}"
        
        # Clicar novamente em "Campeonato" (ordenação Z-A)
        driver.execute_script("arguments[0].click();", th_camp)
        time.sleep(0.5)
        ico_camp2 = driver.find_element(By.ID, 'sort-ico-Campeonato').text
        print(f"  Ícone Campeonato após 2º clique: '{ico_camp2}' (Esperado: '▼')")
        assert '▼' in ico_camp2, f"Esperado ▼ em Campeonato, obtido {ico_camp2}"
        
        # Testar ordenação clicando na coluna "Partida"
        print("  Testando clique no cabeçalho 'Partida' (ordenação A-Z)...")
        th_partida = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-thead th.th-sortable[onclick*='Partida']")
        driver.execute_script("arguments[0].click();", th_partida)
        time.sleep(0.5)
        ico_partida = driver.find_element(By.ID, 'sort-ico-Partida').text
        print(f"  Ícone Partida após clique: '{ico_partida}' (Esperado: '▲')")
        assert '▲' in ico_partida, f"Esperado ▲ em Partida, obtido {ico_partida}"
        
        # Voltar para ordenação por Data (mais recente)
        th_data = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-thead th.th-sortable[onclick*='Data']")
        driver.execute_script("arguments[0].click();", th_data)
        time.sleep(0.5)
        
        # Testar abertura do modal oficial de visualização de PDF
        print("  Testando abertura do PDF oficial via modal in-DOM...")
        btn_pdf = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-tbody .btn-doc-download")
        driver.execute_script("arguments[0].click();", btn_pdf)
        time.sleep(1)
        
        modal = driver.find_element(By.ID, "modal-pdf-viewer")
        assert modal.is_displayed(), "Modal de visualização de PDF não abriu!"
        frame = driver.find_element(By.ID, "pdf-viewer-frame")
        frame_src = frame.get_attribute("src")
        print(f"  Modal exibido com sucesso! Frame SRC: {frame_src}")
        assert "reports/futebol/" in frame_src and frame_src.endswith(".pdf"), f"Frame SRC inválido: {frame_src}"
        
        btn_dl = driver.find_element(By.ID, "pdf-viewer-download")
        dl_href = btn_dl.get_attribute("href")
        print(f"  Link de Download direto: {dl_href}")
        assert "reports/futebol/" in dl_href, f"Download href inválido: {dl_href}"
        
        btn_newtab = driver.find_element(By.ID, "pdf-viewer-newtab")
        newtab_href = btn_newtab.get_attribute("href")
        print(f"  Link de Abrir em Nova Aba: {newtab_href}")
        assert "reports/futebol/" in newtab_href, f"Newtab href inválido: {newtab_href}"
        
        # Fechar modal
        driver.execute_script("closePdfModal();")
        time.sleep(0.5)
        assert not modal.is_displayed(), "Modal de PDF deveria estar fechado."
        print("  [PASS] Relatórios de Jogos (Futebol): 100% Validado!")
        
        # 2. Testar biblioteca "Relatorio Jogos Youtube"
        print("\n[TEST 2] Abrindo biblioteca 'Relatorio Jogos Youtube'...")
        driver.execute_script("openDrive('Relatorio Jogos Youtube', 'Relatório Jogos YouTube');")
        time.sleep(1)
        
        rows_yt = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        print(f"  Total de relatórios de YouTube exibidos: {len(rows_yt)}")
        assert len(rows_yt) > 0, "Nenhuma linha renderizada em Relatorio Jogos Youtube"
        
        # Ordenar por Canal
        th_canal = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-thead th.th-sortable[onclick*='Canal']")
        driver.execute_script("arguments[0].click();", th_canal)
        time.sleep(0.5)
        ico_canal = driver.find_element(By.ID, 'sort-ico-Canal').text
        print(f"  Ícone Canal: '{ico_canal}' (Esperado: '▲')")
        assert '▲' in ico_canal
        
        # Testar modal em YouTube
        btn_pdf_yt = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-tbody .btn-doc-download")
        driver.execute_script("arguments[0].click();", btn_pdf_yt)
        time.sleep(1)
        assert modal.is_displayed(), "Modal não abriu para YouTube"
        frame_src_yt = frame.get_attribute("src")
        print(f"  YouTube Frame SRC: {frame_src_yt}")
        assert "reports/youtube/" in frame_src_yt
        driver.execute_script("closePdfModal();")
        time.sleep(0.5)
        print("  [PASS] Relatório Jogos YouTube: 100% Validado!")
        
        # 3. Testar biblioteca "Relatorios_de_Jogos_NBA"
        print("\n[TEST 3] Abrindo biblioteca 'Relatorios_de_Jogos_NBA'...")
        driver.execute_script("openDrive('Relatorios_de_Jogos_NBA', 'Relatórios de Jogos NBA');")
        time.sleep(1)
        
        rows_nba = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        print(f"  Total de relatórios de NBA exibidos: {len(rows_nba)}")
        assert len(rows_nba) > 0, "Nenhuma linha renderizada em Relatorios_de_Jogos_NBA"
        
        # Ordenar por Placar
        th_placar = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-thead th.th-sortable[onclick*='Placar']")
        driver.execute_script("arguments[0].click();", th_placar)
        time.sleep(0.5)
        ico_placar = driver.find_element(By.ID, 'sort-ico-Placar').text
        print(f"  Ícone Placar: '{ico_placar}' (Esperado: '▲')")
        assert '▲' in ico_placar
        
        # Testar modal em NBA
        btn_pdf_nba = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-tbody .btn-doc-download")
        driver.execute_script("arguments[0].click();", btn_pdf_nba)
        time.sleep(1)
        assert modal.is_displayed(), "Modal não abriu para NBA"
        frame_src_nba = frame.get_attribute("src")
        print(f"  NBA Frame SRC: {frame_src_nba}")
        assert "reports/nba/" in frame_src_nba
        driver.execute_script("closePdfModal();")
        time.sleep(0.5)
        print("  [PASS] Relatórios de Jogos NBA: 100% Validado!")
        
        # Verificar erros de console do navegador
        logs = driver.get_log('browser')
        severe_errors = [l for l in logs if l['level'] == 'SEVERE']
        print(f"\nVerificando logs do console: {len(severe_errors)} erros severos encontrados.")
        if severe_errors:
            for err in severe_errors:
                print("  Console ERROR:", err['message'])
        assert len(severe_errors) == 0, f"Erros severos no console: {severe_errors}"
        
        print("\n✅ TODOS OS TESTES E2E PASSARAM COM 100% DE SUCESSO!")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    test_syntax()
    test_selenium_e2e()
