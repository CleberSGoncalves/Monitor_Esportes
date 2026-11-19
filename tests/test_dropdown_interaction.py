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
        driver.get('file:///e:/desenvolvimento/Monitor_Esportes/portal_web/index.html')
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
            
        # 4. Test generic list viewer data rendering
        driver.execute_script("showPane('capacitacao');")
        time.sleep(0.1)
        viewer_title = driver.find_element(By.ID, 'list-viewer-title').text
        assert 'Ficha de Capacitação' in viewer_title, f"Expected 'Ficha de Capacitação' in title, got '{viewer_title}'"
        rows = driver.find_elements(By.CSS_SELECTOR, '#list-viewer-tbody tr')
        assert len(rows) >= 5, f"Expected at least 5 rows in Capacitação, got {len(rows)}"
        print(f"✓ Generic List Viewer 'capacitacao' rendered {len(rows)} rows with title '{viewer_title}'")
        
        # 5. Test Painel de Ocorrências (13 columns)
        driver.execute_script("showPane('ocorrencias');")
        time.sleep(0.1)
        oco_title = driver.find_element(By.CSS_SELECTOR, '#pane-ocorrencias .sp-list-main-title').text
        assert 'Painel de Ocorrências' in oco_title
        oco_headers = driver.find_elements(By.CSS_SELECTOR, '#pane-ocorrencias .sp-list-table th')
        assert len(oco_headers) == 13, f"Expected 13 columns in Ocorrências, got {len(oco_headers)}"
        print(f"✓ Painel de Ocorrências has {len(oco_headers)} columns verified.")
        
        print("\n==============================================")
        print("ALL E2E NAVIGATION TESTS PASSED WITH 100% SUCCESS!")
        print("==============================================")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    test_full_portal_navigation()
