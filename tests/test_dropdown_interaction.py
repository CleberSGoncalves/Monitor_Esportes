import os, sys, time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def test_full_portal_navigation():
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--window-size=1600,1000')
    driver = webdriver.Chrome(options=opts)
    
    try:
        html_file = os.path.abspath('portal_web/index.html').replace('\\', '/')
        driver.get(f'file:///{html_file}')
        time.sleep(1)
        
        # 1. Test top menu buttons and dropdowns
        menu_items = driver.find_elements(By.CSS_SELECTOR, '.sp-menu-item')
        print(f"Total menu items: {len(menu_items)}")
        assert len(menu_items) >= 9, f"Expected at least 9 menu items, got {len(menu_items)}"
        
        tested_dropdowns = 0
        tested_links = 0
        
        for item in menu_items:
            btn = item.find_element(By.CSS_SELECTOR, '.sp-menu-btn')
            btn_text = btn.text.strip().replace('\n', ' ')
            dropdowns = item.find_elements(By.CSS_SELECTOR, '.sp-dropdown-menu')
            
            if len(dropdowns) > 0:
                tested_dropdowns += 1
                dd = dropdowns[0]
                
                # Initially dropdown should not be open
                assert not ('open' in item.get_attribute('class')), f"Item '{btn_text}' should not be open initially"
                
                # Click to open dropdown
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.1)
                
                assert 'open' in item.get_attribute('class'), f"Item '{btn_text}' failed to get 'open' class"
                assert dd.is_displayed(), f"Dropdown for '{btn_text}' is not visible"
                
                links = dd.find_elements(By.CSS_SELECTOR, '.sp-dropdown-link')
                assert len(links) > 0, f"Dropdown '{btn_text}' has no links"
                print(f"✓ Menu '{btn_text}': {len(links)} links displayed")
                
                # Test clicking each link in this dropdown
                for link in links:
                    link_text = link.text.strip().replace('\n', ' ')
                    tested_links += 1
                    
                    # Re-open if closed
                    if not dd.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.1)
                    
                    # Click link
                    driver.execute_script("arguments[0].click();", link)
                    time.sleep(0.1)
                    
                    # Verify dropdown closes
                    assert not ('open' in item.get_attribute('class')), f"Dropdown '{btn_text}' did not close after clicking '{link_text}'"
                    
                    # Verify an active pane exists
                    active_panes = driver.find_elements(By.CSS_SELECTOR, '.pane-container.active')
                    assert len(active_panes) == 1, f"Expected exactly 1 active pane, found {len(active_panes)}"
                    active_id = active_panes[0].get_attribute('id')
                    print(f"    -> Link '{link_text}' navigated to: {active_id}")
                    
        print(f"\nTested {tested_dropdowns} dropdown menus and {tested_links} sub-links successfully.")
        
        # 2. Test direct home navigation
        home_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Página Inicial')]")
        driver.execute_script("arguments[0].click();", home_btn)
        time.sleep(0.1)
        active_pane = driver.find_element(By.CSS_SELECTOR, '.pane-container.active')
        assert active_pane.get_attribute('id') == 'pane-home', "Failed to navigate back to pane-home"
        print("✓ 'Página Inicial' navigation verified.")
        
        # 3. Test 3x3 Hero cards on Home page
        hero_cards = driver.find_elements(By.CSS_SELECTOR, '.hero-card')
        assert len(hero_cards) == 9, f"Expected 9 hero cards, found {len(hero_cards)}"
        for card in hero_cards:
            card_text = card.text.strip().replace('\n', ' ')
            driver.execute_script("arguments[0].click();", card)
            time.sleep(0.1)
            active_id = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
            assert active_id != 'pane-home', f"Card '{card_text}' did not change active pane"
            print(f"✓ Hero card '{card_text}' -> {active_id}")
            # return home
            driver.execute_script("arguments[0].click();", home_btn)
            time.sleep(0.05)
            
        # 4. Test Procedimentos Drive (Breadcrumb navigation + folder entering)
        driver.execute_script("showPane('procedimentos');")
        time.sleep(0.1)
        active_id = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
        assert active_id == 'pane-drive-viewer', f"Expected pane-drive-viewer for procedimentos, got {active_id}"
        proc_title = driver.find_element(By.ID, 'drive-viewer-title').text
        assert 'Procedimentos' in proc_title
        proc_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        assert len(proc_rows) == 3, f"Expected 3 root folders in Procedimentos, got {len(proc_rows)}"
        print(f"✓ Procedimentos Drive root has {len(proc_rows)} folders: Monitorao, Procedimentos Suporte N1, Tratamento de chamados")
        
        # Click on folder 'Monitorao'
        folder_link = driver.find_element(By.XPATH, "//span[contains(text(), 'Monitorao')]")
        driver.execute_script("arguments[0].click();", folder_link)
        time.sleep(0.1)
        crumbs = driver.find_element(By.ID, 'drive-breadcrumbs').text
        assert 'Monitorao' in crumbs, f"Expected 'Monitorao' in breadcrumbs, got: {crumbs}"
        sub_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        assert len(sub_rows) >= 10, f"Expected at least 10 items inside Monitorao, got {len(sub_rows)}"
        print(f"✓ Navigated into 'Monitorao': {len(sub_rows)} files/folders displayed. Breadcrumbs: {crumbs}")
        
        # Navigate back using breadcrumb
        parent_crumb = driver.find_element(By.CSS_SELECTOR, '.sp-crumb')
        driver.execute_script("arguments[0].click();", parent_crumb)
        time.sleep(0.1)
        proc_rows_back = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        assert len(proc_rows_back) == 3, f"Expected 3 root folders after navigating back, got {len(proc_rows_back)}"
        print("✓ Navigated back to Procedimentos root via breadcrumb.")

        # 5. Test Metas Drive (METAS 2019 to METAS 2026 + Excel files)
        driver.execute_script("showPane('metas');")
        time.sleep(0.1)
        meta_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        assert len(meta_rows) == 8, f"Expected 8 year folders in Metas, got {len(meta_rows)}"
        print(f"✓ Metas Drive has {len(meta_rows)} folders (METAS 2019 to METAS 2026)")
        
        # Enter METAS 2026
        meta26_link = driver.find_element(By.XPATH, "//span[contains(text(), 'METAS 2026')]")
        driver.execute_script("arguments[0].click();", meta26_link)
        time.sleep(0.1)
        meta26_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        assert len(meta26_rows) >= 3, f"Expected 3 items in METAS 2026, got {len(meta26_rows)}"
        meta26_text = driver.find_element(By.ID, 'drive-viewer-tbody').text
        assert 'Metas 2026_Acompanhamento.xlsx' in meta26_text
        print("✓ METAS 2026 verified containing 'Metas 2026_Acompanhamento.xlsx'!")

        # 6. Test Relatórios de Jogos (260 official reports with 3 tabs)
        driver.execute_script("showPane('relatoriosjogos');")
        time.sleep(0.1)
        active_id = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
        assert active_id == 'pane-relatoriosjogos'
        nba_count = int(driver.find_element(By.ID, 'count-rel-nba').text)
        yt_count = int(driver.find_element(By.ID, 'count-rel-yt').text)
        fut_count = int(driver.find_element(By.ID, 'count-rel-fut').text)
        assert nba_count == 168, f"Expected 168 NBA reports, got {nba_count}"
        assert yt_count == 51, f"Expected 51 YouTube reports, got {yt_count}"
        assert fut_count == 41, f"Expected 41 Futebol reports, got {fut_count}"
        assert (nba_count + yt_count + fut_count) == 260
        print(f"✓ Relatórios de Jogos verified: {nba_count} NBA + {yt_count} YouTube + {fut_count} Futebol = 260 total official reports!")
        
        # Switch to YouTube tab
        yt_pill = driver.find_element(By.ID, 'pill-relatorios-yt')
        driver.execute_script("arguments[0].click();", yt_pill)
        time.sleep(0.1)
        yt_rows = driver.find_elements(By.CSS_SELECTOR, '#relatorios-table-body tr')
        assert len(yt_rows) == 51, f"Expected 51 rows in YouTube tab, got {len(yt_rows)}"
        print("✓ Tab YouTube & CazéTV displays all 51 official PDF reports.")

        # Switch to Futebol tab
        fut_pill = driver.find_element(By.ID, 'pill-relatorios-fut')
        driver.execute_script("arguments[0].click();", fut_pill)
        time.sleep(0.1)
        fut_rows = driver.find_elements(By.CSS_SELECTOR, '#relatorios-table-body tr')
        assert len(fut_rows) == 41, f"Expected 41 rows in Futebol tab, got {len(fut_rows)}"
        print("✓ Tab Auditoria Futebol displays all 41 official PDF reports.")

        # 7. Test Real Lists: Redmine, Configurações de Rede, Monitoramento de Canais, CPD
        driver.execute_script("showPane('redmine');")
        time.sleep(0.1)
        active_id = driver.find_element(By.CSS_SELECTOR, '.pane-container.active').get_attribute('id')
        assert active_id == 'pane-list-viewer'
        redmine_rows = driver.find_elements(By.CSS_SELECTOR, '#list-viewer-tbody tr')
        assert len(redmine_rows) == 300, f"Expected 300 rows in Redmine, got {len(redmine_rows)}"
        print(f"✓ List 'Redmine' rendered {len(redmine_rows)} real operational rows.")

        driver.execute_script("showPane('redescs');")
        time.sleep(0.1)
        rede_rows = driver.find_elements(By.CSS_SELECTOR, '#list-viewer-tbody tr')
        assert len(rede_rows) == 137, f"Expected 137 rows in Configurações de Rede do CS, got {len(rede_rows)}"
        print(f"✓ List 'Configurações de Rede do CS' rendered {len(rede_rows)} real rows.")

        driver.execute_script("showPane('monitoramentocanais');")
        time.sleep(0.1)
        canal_rows = driver.find_elements(By.CSS_SELECTOR, '#list-viewer-tbody tr')
        assert len(canal_rows) == 300, f"Expected 300 rows in Monitoramento de Canais CS, got {len(canal_rows)}"
        print(f"✓ List 'Monitoramento de Canais CS' rendered {len(canal_rows)} real rows.")

        driver.execute_script("showPane('contratos');")
        time.sleep(0.1)
        contrato_rows = driver.find_elements(By.CSS_SELECTOR, '#drive-viewer-tbody tr')
        assert len(contrato_rows) == 114, f"Expected 114 contract PDFs, got {len(contrato_rows)}"
        print(f"✓ Drive 'Controle de contratos parceiros' rendered {len(contrato_rows)} real contract PDFs.")

        # 8. Test Painel de Ocorrências (500 casos)
        driver.execute_script("showPane('ocorrencias');")
        time.sleep(0.1)
        oco_title = driver.find_element(By.CSS_SELECTOR, '#pane-ocorrencias .sp-list-main-title').text
        assert 'Painel de Ocorrências' in oco_title
        oco_headers = driver.find_elements(By.CSS_SELECTOR, '#pane-ocorrencias .sp-list-table th')
        assert len(oco_headers) == 13, f"Expected 13 columns in Ocorrências, got {len(oco_headers)}"
        print(f"✓ Painel de Ocorrências has {len(oco_headers)} columns verified.")
        
        print("\n========================================================")
        print("ALL REAL SHAREPOINT DATA AND E2E TESTS PASSED WITH 100% SUCCESS!")
        print("========================================================")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    test_full_portal_navigation()
