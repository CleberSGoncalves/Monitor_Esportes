import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

def test_portal_interactive_creation_and_grid_edit():
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--window-size=1600,1000')
    driver = webdriver.Chrome(options=opts)

    try:
        html_file = os.path.abspath('docs/index.html').replace('\\', '/')
        driver.get(f'file:///{html_file}')
        time.sleep(1)

        print("\n--- TEST 1: Painel de Ocorrências + Novo (Criação de Ocorrência) ---")
        driver.execute_script("showPane('ocorrencias');")
        time.sleep(0.3)

        # Verificar se o botão + Novo está visível
        new_btn = driver.find_element(By.CSS_SELECTOR, "#pane-ocorrencias .sp-btn-new")
        assert new_btn.is_displayed(), "Botão + Novo em Ocorrências deve estar visível"
        assert "action-admin-only" not in new_btn.get_attribute("class"), "Botão + Novo não pode ter restrição action-admin-only"

        # Clicar no botão + Novo
        new_btn.click()
        time.sleep(0.3)

        modal_oco = driver.find_element(By.ID, "modal-new-oco")
        assert modal_oco.is_displayed(), "Modal de nova ocorrência #modal-new-oco deve abrir"

        # Preencher os campos
        driver.find_element(By.ID, "new-oco-host").send_keys("Curitiba / BRP-CUR-TDT")
        Select(driver.find_element(By.ID, "new-oco-status")).select_by_value("Em andamento")
        driver.find_element(By.ID, "new-oco-cs").send_keys("01, 02")
        driver.find_element(By.ID, "new-oco-veiculo").send_keys("GLOBO")
        driver.find_element(By.ID, "new-oco-equipamento").send_keys("ATRIA")
        Select(driver.find_element(By.ID, "new-oco-tipo")).select_by_value("Não está gravando")
        driver.find_element(By.ID, "new-oco-acoes").send_keys("Reiniciado decoder e reconfigurado streaming.")
        driver.find_element(By.ID, "new-oco-redmine").send_keys("9999")

        oper_check = driver.find_element(By.ID, "new-oco-operacao")
        if not oper_check.is_selected():
            oper_check.click()

        # Submeter formulário
        driver.find_element(By.CSS_SELECTOR, "#form-new-oco button[type='submit']").click()
        time.sleep(0.5)

        # Validar que modal fechou
        assert not modal_oco.is_displayed(), "Modal #modal-new-oco deve fechar após submissão"

        # Validar que a nova linha aparece na tabela
        first_row_text = driver.find_element(By.CSS_SELECTOR, "#oco-table-body tr").text
        print("Primeira linha da tabela de ocorrências após criação:", first_row_text)
        assert "Curitiba / BRP-CUR-TDT" in first_row_text, "Nova ocorrência deve constar no topo da tabela"
        assert "GLOBO" in first_row_text, "Veículo GLOBO deve constar na linha criada"

        # Validar persistência em localStorage
        local_saved = driver.execute_script("return localStorage.getItem('sp_custom_ocorrencias');")
        assert local_saved is not None, "Ocorrência deve ser salva no localStorage"
        saved_data = json.loads(local_saved)
        assert len(saved_data) > 0 and saved_data[0]["HostName"] == "Curitiba / BRP-CUR-TDT"
        print("✅ TEST 1 PASSOU: Criação de ocorrência interativa 100% validada!")

        print("\n--- TEST 2: Painel de Ocorrências - Editar no modo de exibição de grade ---")
        grid_btn = driver.find_element(By.ID, "btn-grid-oco")
        grid_btn.click()
        time.sleep(0.3)

        # Validar ativação do modo grade
        assert "btn-grid-active" in grid_btn.get_attribute("class"), "Botão deve receber classe btn-grid-active"
        btn_text = driver.find_element(By.ID, "btn-grid-oco-text").text
        assert "Sair do modo de exibição de grade" in btn_text, f"Texto do botão deve mudar, obtido: {btn_text}"

        alert_banner = driver.find_element(By.ID, "oco-grid-mode-alert")
        assert alert_banner.is_displayed(), "Banner de modo grade ativado deve estar visível"

        # Validar que as células se tornaram editáveis (contenteditable ou select)
        editable_cells = driver.find_elements(By.CSS_SELECTOR, "#oco-table-body .sp-grid-cell")
        assert len(editable_cells) > 0, "Deve haver células com classe sp-grid-cell no modo grade"
        assert editable_cells[0].get_attribute("contenteditable") == "true", "Células devem ter contenteditable='true'"

        grid_selects = driver.find_elements(By.CSS_SELECTOR, "#oco-table-body .sp-grid-select")
        assert len(grid_selects) > 0, "Deve haver dropdowns inline para status no modo grade"

        # Modificar o status inline da primeira ocorrência para Concluído
        Select(grid_selects[0]).select_by_value("Concluído")
        time.sleep(0.2)

        # Sair do modo grade
        grid_btn.click()
        time.sleep(0.3)

        assert "btn-grid-active" not in grid_btn.get_attribute("class"), "Botão deve perder classe btn-grid-active ao sair"
        assert not alert_banner.is_displayed(), "Banner deve ser ocultado ao sair do modo grade"

        # Validar persistência da edição no localStorage
        local_edits = driver.execute_script("return localStorage.getItem('sp_custom_ocorrencias_edits');")
        print("Edições salvas em localStorage:", local_edits)
        assert local_edits is not None, "Edição no modo grade deve persistir no localStorage"
        print("✅ TEST 2 PASSOU: Modo de exibição de grade no Painel de Ocorrências 100% validado!")

        print("\n--- TEST 3: Listas Genéricas do SharePoint (Criação de Item + Novo) ---")
        driver.execute_script("showPane('pane-list-viewer'); openRealList('Cadastro - Hosts', 'Cadastro - Hosts');")
        time.sleep(0.3)

        list_new_btn = driver.find_element(By.CSS_SELECTOR, "#pane-list-viewer .sp-btn-new")
        assert list_new_btn.is_displayed(), "Botão + Novo em lista genérica deve estar visível"
        assert "action-admin-only" not in list_new_btn.get_attribute("class"), "Botão + Novo em listas não pode ter action-admin-only"

        list_new_btn.click()
        time.sleep(0.3)

        modal_list = driver.find_element(By.ID, "modal-new-list-item")
        assert modal_list.is_displayed(), "Modal #modal-new-list-item deve abrir"

        # Preencher input dinâmico
        dyn_inputs = driver.find_elements(By.CSS_SELECTOR, ".list-dyn-input")
        assert len(dyn_inputs) > 0, "Deve haver campos gerados dinamicamente para as colunas da lista"
        dyn_inputs[0].send_keys("HOST-E2E-TESTE-999")

        # Submeter
        driver.find_element(By.CSS_SELECTOR, "#form-new-list-item button[type='submit']").click()
        time.sleep(0.5)

        assert not modal_list.is_displayed(), "Modal deve fechar após submissão"

        # Validar nova linha na tabela genérica
        first_list_row = driver.find_element(By.CSS_SELECTOR, "#list-viewer-tbody tr").text
        print("Primeira linha da lista genérica:", first_list_row)
        assert "HOST-E2E-TESTE-999" in first_list_row, "Novo item deve constar no topo da lista genérica"
        print("✅ TEST 3 PASSOU: Inclusão em lista genérica 100% validada!")

        print("\n--- TEST 4: Listas Genéricas - Editar no modo de exibição de grade ---")
        grid_generic_btn = driver.find_element(By.ID, "btn-grid-generic")
        grid_generic_btn.click()
        time.sleep(0.3)

        assert "btn-grid-active" in grid_generic_btn.get_attribute("class"), "Botão genérico deve ativar"
        assert driver.find_element(By.ID, "generic-grid-mode-alert").is_displayed(), "Banner deve exibir"

        cells_gen = driver.find_elements(By.CSS_SELECTOR, "#list-viewer-tbody .sp-grid-cell")
        assert len(cells_gen) > 0, "Células da lista genérica devem ser editáveis"
        assert cells_gen[0].get_attribute("contenteditable") == "true"

        grid_generic_btn.click()
        time.sleep(0.3)
        assert "btn-grid-active" not in grid_generic_btn.get_attribute("class")
        print("✅ TEST 4 PASSOU: Modo grade em lista genérica 100% validado!")

        print("\n--- TEST 5: Permissões de Operador (Nenhum botão bloqueado para operadores) ---")
        driver.execute_script("document.getElementById('user-role-select').value = 'operador'; onRoleChange();")
        time.sleep(0.2)

        driver.execute_script("showPane('ocorrencias');")
        time.sleep(0.2)
        oco_btn = driver.find_element(By.CSS_SELECTOR, "#pane-ocorrencias .sp-btn-new")
        assert oco_btn.is_displayed(), "+ Novo em Ocorrências deve estar visível para operadores"

        driver.execute_script("showPane('pane-list-viewer');")
        time.sleep(0.2)
        list_btn = driver.find_element(By.CSS_SELECTOR, "#pane-list-viewer .sp-btn-new")
        assert list_btn.is_displayed(), "+ Novo em Listas deve estar visível para operadores"

        driver.execute_script("showPane('antenistas');")
        time.sleep(0.2)
        ante_btn = driver.find_element(By.CSS_SELECTOR, "#pane-antenistas .sp-btn-new")
        assert ante_btn.is_displayed(), "+ Novo em Antenistas deve estar visível para operadores"

        driver.execute_script("showPane('hosts');")
        time.sleep(0.2)
        hosts_btn = driver.find_element(By.CSS_SELECTOR, "#pane-hosts .sp-btn-new")
        assert hosts_btn.is_displayed(), "+ Novo em Hosts deve estar visível para operadores"

        print("✅ TEST 5 PASSOU: Operadores têm acesso pleno a todas as ações de criação!")

        print("\n🎉 TODOS OS 5 TESTES E2E PASSARAM COM 100% DE SUCESSO!")

    finally:
        driver.quit()

if __name__ == "__main__":
    test_portal_interactive_creation_and_grid_edit()
