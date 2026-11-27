# -*- coding: utf-8 -*-
import os
import sys
import time
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def test_portal_drive_reports_filters_and_delete_selenium():
    html_file = os.path.join(PROJECT_ROOT, "docs", "index.html")
    assert os.path.exists(html_file), "docs/index.html deve existir"

    file_url = "file:///" + os.path.abspath(html_file).replace("\\", "/")

    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--window-size=1600,1000')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=opts)

    try:
        driver.get(file_url)
        time.sleep(1)

        # 1. 0 erros graves nos logs do console
        logs = driver.get_log('browser')
        errors = [l['message'] for l in logs if l['level'] == 'SEVERE' and 'favicon' not in l['message'].lower()]
        assert len(errors) == 0, f"Erros graves no console: {errors}"

        # 2. Abrir Relatórios de Jogos (Futebol)
        driver.execute_script("openDrive('Relatorios_de_Jogos', 'Relatórios de Jogos');")
        time.sleep(0.5)

        # 3. Validar cabeçalho e linha de filtros
        th_elements = driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-thead tr:nth-child(1) th")
        th_titles = [th.text.strip() for th in th_elements]
        print("Títulos colunas:", th_titles)
        assert any("Data / Hora" in t for t in th_titles), f"Coluna Data / Hora ausente: {th_titles}"
        assert any("Campeonato" in t for t in th_titles), f"Coluna Campeonato ausente: {th_titles}"
        assert any("Partida" in t for t in th_titles), f"Coluna Partida ausente: {th_titles}"
        assert any("Ações" in t for t in th_titles), f"Coluna Ações ausente: {th_titles}"

        # Verificar linha de filtros por coluna (.table-filter-row)
        filter_rows = driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-thead .table-filter-row")
        assert len(filter_rows) == 1, "Linha .table-filter-row ausente no thead"
        assert driver.find_element(By.ID, "df-data").is_displayed(), "Input #df-data ausente"
        assert driver.find_element(By.ID, "df-camp").is_displayed(), "Input #df-camp ausente"
        assert driver.find_element(By.ID, "df-partida").is_displayed(), "Input #df-partida ausente"

        # 4. Validar ordenação cronológica decrescente (mais recente no topo)
        is_sorted = driver.execute_script("""
            const trs = Array.from(document.querySelectorAll('#drive-viewer-tbody tr'));
            const timestamps = trs.map(tr => {
                const dtStr = tr.querySelector('td:nth-child(3)')?.innerText?.trim() || '';
                const m = dtStr.match(/(\\d{1,2})\\/(\\d{1,2})\\/(\\d{4})(?:\\s+(\\d{1,2}):(\\d{1,2}))?/);
                if (m) return new Date(parseInt(m[3]), parseInt(m[2])-1, parseInt(m[1]), parseInt(m[4]||0), parseInt(m[5]||0)).getTime();
                return 0;
            }).filter(t => t > 0);
            for (let i = 0; i < timestamps.length - 1; i++) {
                if (timestamps[i] < timestamps[i+1]) return false;
            }
            return true;
        """)
        assert is_sorted, "Tabela NÃO está ordenada com datas decrescentes (mais recentes no topo)!"
        print("✅ Ordenação decrescente validada!")

        # 5. Testar filtro por coluna (Campeonato)
        rows_initial = driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-tbody tr")
        total_initial = len(rows_initial)
        print(f"Total inicial de relatórios: {total_initial}")

        inp_camp = driver.find_element(By.ID, "df-camp")
        inp_camp.send_keys("Copa")
        time.sleep(0.3)
        rows_filtered = driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-tbody tr")
        copa_count = len(rows_filtered)
        print(f"Total filtrado por Copa: {copa_count}")
        assert 0 < copa_count < total_initial, f"Filtro por coluna falhou: initial={total_initial}, filtered={copa_count}"

        # Limpar filtros
        driver.execute_script("clearDriveColFilters();")
        time.sleep(0.3)
        rows_reset = driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-tbody tr")
        assert len(rows_reset) == total_initial, "clearDriveColFilters não restaurou o total inicial"
        print("✅ Filtro por coluna e limpeza de filtros validados!")

        # 6. Testar botão de exclusão individual (in-DOM modal)
        btn_del = driver.find_element(By.CSS_SELECTOR, "#drive-viewer-tbody tr:nth-child(1) .btn-doc-delete")
        assert btn_del.is_displayed(), "Botão 🗑️ de exclusão deve estar visível em cada linha"
        btn_del.click()
        time.sleep(0.3)

        modal_del = driver.find_element(By.ID, "modal-generic-confirm-delete")
        assert modal_del.is_displayed(), "Modal de confirmação #modal-generic-confirm-delete deve abrir"

        # Confirmar exclusão no modal
        btn_confirm = driver.find_element(By.ID, "modal-delete-confirm-btn")
        btn_confirm.click()
        time.sleep(0.5)

        rows_after_del = driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-tbody tr")
        assert len(rows_after_del) == total_initial - 1, "Linha não foi excluída da tabela"

        footer_text = driver.find_element(By.ID, "drive-viewer-footer").text
        assert "excluído" in footer_text.lower(), "Footer não indicou item excluído"
        print("✅ Exclusão individual com modal in-DOM validada!")

        # 7. Restaurar itens excluídos
        driver.execute_script("restoreDeletedDriveItems();")
        time.sleep(0.3)
        assert modal_del.is_displayed(), "Modal de restauração deve abrir"
        btn_confirm.click()
        time.sleep(0.5)

        rows_restored = driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-tbody tr")
        assert len(rows_restored) == total_initial, "Itens não foram restaurados"
        print("✅ Restauração de itens excluídos validada!")

        # 8. Validar Relatório Jogos YouTube
        driver.execute_script("openDrive('Relatorio Jogos Youtube', 'Relatório Jogos Youtube');")
        time.sleep(0.5)
        yt_titles = [th.text.strip() for th in driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-thead tr:nth-child(1) th")]
        assert any("Canal" in t for t in yt_titles), f"Coluna Canal ausente no YouTube: {yt_titles}"
        assert driver.find_element(By.ID, "df-canal").is_displayed(), "Input #df-canal ausente no YouTube"
        print("✅ Relatório Jogos YouTube validado!")

        # 9. Validar Relatórios de Jogos NBA
        driver.execute_script("openDrive('Relatorios_de_Jogos_NBA', 'Relatórios de Jogos NBA');")
        time.sleep(0.5)
        nba_titles = [th.text.strip() for th in driver.find_elements(By.CSS_SELECTOR, "#drive-viewer-thead tr:nth-child(1) th")]
        assert any("Placar" in t for t in nba_titles), f"Coluna Placar ausente na NBA: {nba_titles}"
        assert driver.find_element(By.ID, "df-placar").is_displayed(), "Input #df-placar ausente na NBA"
        print("✅ Relatórios de Jogos NBA validado!")

        print("\n🎉 TODOS OS TESTES PASSARAM COM SUCESSO (100% HOMOLOGADO)!")

    finally:
        driver.quit()
