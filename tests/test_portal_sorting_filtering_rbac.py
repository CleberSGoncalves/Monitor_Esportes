import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

def test_portal_sorting_filtering_and_rbac():
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--window-size=1600,1000')
    driver = webdriver.Chrome(options=opts)

    try:
        html_file = os.path.abspath('docs/index.html').replace('\\', '/')
        driver.get(f'file:///{html_file}')
        time.sleep(1)

        print("\n--- TEST 1: Escala de Trabalho movida para Administração e desvinculação total do SharePoint ---")
        # 1.1 Validar que Escala está no menu Administração
        admin_links = driver.find_elements(By.CSS_SELECTOR, ".sp-menu-item:nth-child(3) .sp-dropdown-link")
        admin_texts = [l.get_attribute("textContent").strip() for l in admin_links]
        print("Links no menu Administração:", admin_texts)
        assert any("Escala de Trabalho 2026" in t for t in admin_texts), "Escala de Trabalho 2026 DEVE estar no menu Administração"

        # 1.2 Validar que Escala NÃO está no menu Documentos
        doc_links = driver.find_elements(By.CSS_SELECTOR, ".sp-menu-item:nth-child(2) .sp-dropdown-link")
        doc_texts = [l.get_attribute("textContent").strip() for l in doc_links]
        print("Links no menu Documentos:", doc_texts)
        assert not any("Escala de Trabalho 2026" in t for t in doc_texts), "Escala de Trabalho 2026 NÃO pode estar no menu Documentos"

        # 1.3 Validar que não existe botão ou link para o SharePoint antigo no pane da Escala
        driver.execute_script("showPane('escala');")
        time.sleep(0.3)
        escala_pane_html = driver.find_element(By.ID, "pane-escala").get_attribute("innerHTML")
        assert "adgbl.sharepoint.com" not in escala_pane_html, "NÃO pode haver nenhum link apontando para adgbl.sharepoint.com na escala"
        assert "Editar no Excel Online" not in escala_pane_html, "Botão 'Editar no Excel Online' antigo deve ter sido removido"

        # 1.4 Validar badge de governança da Escala
        badge = driver.find_element(By.ID, "escala-perm-badge")
        assert badge.is_displayed(), "Badge de status de permissões da escala deve estar visível"
        print("Badge de permissões da Escala:", badge.text)
        print("✅ TEST 1 PASSOU: Escala em Administração e desvinculação completa do SharePoint confirmada!")

        print("\n--- TEST 2: Programação Streaming - Ordenação por Colunas Estilo SharePoint ---")
        driver.execute_script("showPane('streaming');")
        time.sleep(0.3)

        # 2.1 Ordenar por Campeonato
        th_camp = driver.find_element(By.CSS_SELECTOR, "th[onclick*=\"sortStreamBy('campeonato')\"]")
        th_camp.click()
        time.sleep(0.3)
        assert "sorted-asc" in th_camp.get_attribute("class"), "Cabeçalho Campeonato deve ficar sorted-asc"
        first_row_camp_asc = driver.find_element(By.CSS_SELECTOR, "#table-body tr td:nth-child(5)").text
        print("Primeiro campeonato após sort ASC:", first_row_camp_asc)

        th_camp.click()
        time.sleep(0.3)
        assert "sorted-desc" in th_camp.get_attribute("class"), "Cabeçalho Campeonato deve ficar sorted-desc"
        first_row_camp_desc = driver.find_element(By.CSS_SELECTOR, "#table-body tr td:nth-child(5)").text
        print("Primeiro campeonato após sort DESC:", first_row_camp_desc)
        assert first_row_camp_asc != first_row_camp_desc, "Ordenação ASC e DESC devem apresentar resultados distintos"

        # 2.2 Ordenar por Data
        th_data = driver.find_element(By.CSS_SELECTOR, "th[onclick*=\"sortStreamBy('data')\"]")
        th_data.click()
        time.sleep(0.3)
        assert "sorted-asc" in th_data.get_attribute("class"), "Cabeçalho Data deve ficar sorted-asc"

        # 2.3 Ordenar por Canal
        th_canal = driver.find_element(By.CSS_SELECTOR, "th[onclick*=\"sortStreamBy('canal')\"]")
        th_canal.click()
        time.sleep(0.3)
        assert "sorted-asc" in th_canal.get_attribute("class"), "Cabeçalho Canal deve ficar sorted-asc"
        print("✅ TEST 2 PASSOU: Ordenação por colunas na Programação Streaming validada com sucesso!")

        print("\n--- TEST 3: Programação Streaming - Filtros por Mês, Campeonato, Canal e Status ---")
        # 3.1 Filtrar por Canal
        canal_select = Select(driver.find_element(By.ID, "filter-canal"))
        canal_select.select_by_value("cazé")
        time.sleep(0.3)
        caze_count = int(driver.find_element(By.ID, "showing-count").text)
        print("Eventos Cazé TV filtrados:", caze_count)
        assert caze_count > 0, "Deve haver eventos Cazé TV"

        # 3.2 Filtrar por Mês
        mes_select = Select(driver.find_element(By.ID, "filter-mes"))
        mes_select.select_by_value("Janeiro")
        time.sleep(0.3)
        jan_caze_count = int(driver.find_element(By.ID, "showing-count").text)
        print("Eventos Cazé TV em Janeiro:", jan_caze_count)
        assert jan_caze_count <= caze_count

        # 3.3 Limpar filtros
        clear_btn = driver.find_element(By.ID, "btn-clear-stream-filters")
        clear_btn.click()
        time.sleep(0.3)
        total_restored = int(driver.find_element(By.ID, "showing-count").text)
        print("Total de eventos após limpar filtros:", total_restored)
        assert total_restored == 862, f"Total restaurado deve ser 862, obtido: {total_restored}"
        print("✅ TEST 3 PASSOU: Filtros multi-coluna e botão Limpar Filtros validados!")

        print("\n--- TEST 4: Contatos Hospedeiros - Ordenação por Colunas ---")
        driver.execute_script("showPane('hospedeiros');")
        time.sleep(0.3)
        th_hosp_cidade = driver.find_element(By.CSS_SELECTOR, "th[onclick*=\"sortHospBy('Title')\"]")
        th_hosp_cidade.click()
        time.sleep(0.3)
        assert "sorted-asc" in th_hosp_cidade.get_attribute("class")
        first_hosp_asc = driver.find_element(By.CSS_SELECTOR, "#hosp-table-body tr td:nth-child(2)").text
        print("Primeira cidade hospedeiro ASC:", first_hosp_asc)

        th_hosp_cidade.click()
        time.sleep(0.3)
        assert "sorted-desc" in th_hosp_cidade.get_attribute("class")
        first_hosp_desc = driver.find_element(By.CSS_SELECTOR, "#hosp-table-body tr td:nth-child(2)").text
        print("Primeira cidade hospedeiro DESC:", first_hosp_desc)
        assert first_hosp_asc != first_hosp_desc
        print("✅ TEST 4 PASSOU: Ordenação por colunas em Hospedeiros validada!")

        print("\n--- TEST 5: Painel de Ocorrências - Ordenação por Múltiplas Colunas ---")
        driver.execute_script("showPane('ocorrencias');")
        time.sleep(0.3)
        th_oco_host = driver.find_element(By.CSS_SELECTOR, "th[onclick*=\"sortOcoBy('HostName')\"]")
        th_oco_host.click()
        time.sleep(0.3)
        assert "sorted-asc" in th_oco_host.get_attribute("class")

        th_oco_status = driver.find_element(By.CSS_SELECTOR, "th[onclick*=\"sortOcoBy('Status')\"]")
        th_oco_status.click()
        time.sleep(0.3)
        assert "sorted-asc" in th_oco_status.get_attribute("class")
        print("✅ TEST 5 PASSOU: Ordenação dinâmica no Painel de Ocorrências validada!")

        print("\n--- TEST 6: Listas Genéricas do SharePoint - Ordenação Dinâmica ---")
        driver.execute_script("showPane('pane-list-viewer'); openRealList('Cadastro - Hosts', 'Cadastro - Hosts');")
        time.sleep(0.3)
        gen_th = driver.find_elements(By.CSS_SELECTOR, "#list-viewer-thead .th-sortable")
        assert len(gen_th) > 0, "Lista genérica deve conter cabeçalhos ordenáveis .th-sortable"
        gen_th[0].click()
        time.sleep(0.3)
        assert "sorted-asc" in gen_th[0].get_attribute("class"), "Primeira coluna genérica deve ficar sorted-asc"
        print("✅ TEST 6 PASSOU: Ordenação dinâmica em lista genérica validada!")

        print("\n--- TEST 7: Matriz de Permissões RBAC (Admin, Operador, Visitante) ---")
        # 7.1 Admin: Acesso total
        driver.execute_script("document.getElementById('user-role-select').value = 'admin'; onRoleChange();")
        time.sleep(0.2)
        driver.execute_script("showPane('escala');")
        time.sleep(0.2)
        badge_admin = driver.find_element(By.ID, "escala-perm-badge").text
        assert "Permissão de Edição (Administrador)" in badge_admin, f"Badge incorreto para admin: {badge_admin}"
        perm_tab = driver.find_element(By.ID, "nav-tab-permissoes")
        assert perm_tab.is_displayed(), "Aba Permissões deve estar visível para admin"

        # 7.2 Operador: Escrita operacional, sem gestão administrativa da escala
        driver.execute_script("document.getElementById('user-role-select').value = 'operador'; onRoleChange();")
        time.sleep(0.2)
        badge_operador = driver.find_element(By.ID, "escala-perm-badge").text
        assert "Somente Leitura" in badge_operador, f"Badge incorreto para operador: {badge_operador}"
        assert not perm_tab.is_displayed(), "Aba Permissões deve ser oculta para operadores"
        # Ocorrências continuam com botão de criação
        driver.execute_script("showPane('ocorrencias');")
        time.sleep(0.2)
        assert driver.find_element(By.CSS_SELECTOR, "#pane-ocorrencias .sp-btn-new").is_displayed(), "+ Novo em Ocorrências deve estar visível para operador"

        # 7.3 Visitante / Leitor: Estritamente leitura (sem botões de criação ou edição em lugar nenhum)
        driver.execute_script("document.getElementById('user-role-select').value = 'leitor'; onRoleChange(); showPane('escala');")
        time.sleep(0.2)
        badge_leitor = driver.find_element(By.ID, "escala-perm-badge").text
        assert "Visitante / Consulta" in badge_leitor, f"Badge incorreto para visitante: {badge_leitor}"
        driver.execute_script("showPane('ocorrencias');")
        time.sleep(0.2)
        assert not driver.find_element(By.CSS_SELECTOR, "#pane-ocorrencias .sp-btn-new").is_displayed(), "+ Novo em Ocorrências deve estar oculto para visitante"
        assert not driver.find_element(By.ID, "btn-grid-oco").is_displayed(), "Modo grade de ocorrências deve estar oculto para visitante"
        print("✅ TEST 7 PASSOU: RBAC validado com precisão cirúrgica (Admin, Operador, Leitor)!")

        print("\n🎉 TODOS OS 7 TESTES E2E DE FIDELIDADE, ORDENAÇÃO E RBAC PASSARAM COM SUCESSO!")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_portal_sorting_filtering_and_rbac()
