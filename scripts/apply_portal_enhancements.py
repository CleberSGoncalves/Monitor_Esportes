import os, sys, json, re

def main():
    root = r"E:\desenvolvimento\Monitor_Esportes"
    build_script = os.path.join(root, "scripts", "build_portal_web.py")
    master_data_file = os.path.join(root, "config", "sharepoint_portal_master_data.json")

    with open(build_script, "r", encoding="utf-8") as f:
        code = f.read()

    print(f"Loaded build_portal_web.py, size: {len(code)}")

    # 1. Obter as 151 linhas estáticas de RDP para embutir no build
    # Carregar do portal_web/index.html atual se já tiver
    portal_current = os.path.join(root, "portal_web", "index.html")
    static_rdp_rows = ""
    if os.path.exists(portal_current):
        with open(portal_current, "r", encoding="utf-8") as f_cur:
            cur_html = f_cur.read()
        m_rdp = re.search(r'<tbody id="rdp-table-body">\s*([\s\S]*?)\s*</tbody>', cur_html)
        if m_rdp and "tr" in m_rdp.group(1):
            static_rdp_rows = m_rdp.group(1).strip()
            print(f"Captured {static_rdp_rows.count('<tr')} static RDP rows from portal_web/index.html")

    # 2. Injetar Cards de Destaque Hoje e Amanhã em #pane-streaming
    today_tomorrow_html = '''
      <!-- QUADRO DE DESTAQUE: JOGOS & EVENTOS PROGRAMADOS PARA HOJE E AMANHÃ -->
      <div class="today-tomorrow-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; margin-bottom: 20px;">
        <!-- CARD HOJE -->
        <div class="schedule-highlight-card card-hoje" style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-top: 4px solid #10B981;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #F1F5F9; padding-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 18px;">⚽</span>
              <span style="font-size: 13.5px; font-weight: 700; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px;">Jogos & Eventos de Hoje</span>
              <span id="badge-count-hoje" style="background: #ECFDF5; color: #059669; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 12px; border: 1px solid #A7F3D0;">0 jogos</span>
            </div>
            <span id="label-data-hoje" style="font-size: 12px; font-weight: 600; color: #64748B;">--/--</span>
          </div>
          <div id="list-eventos-hoje" style="display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto;">
            <div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Carregando eventos de hoje...</div>
          </div>
        </div>

        <!-- CARD AMANHÃ -->
        <div class="schedule-highlight-card card-amanha" style="background: #ffffff; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-top: 4px solid #3B82F6;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid #F1F5F9; padding-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 18px;">📅</span>
              <span style="font-size: 13.5px; font-weight: 700; color: #0F172A; text-transform: uppercase; letter-spacing: 0.5px;">Jogos & Eventos de Amanhã</span>
              <span id="badge-count-amanha" style="background: #EFF6FF; color: #2563EB; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 12px; border: 1px solid #BFDBFE;">0 jogos</span>
            </div>
            <span id="label-data-amanha" style="font-size: 12px; font-weight: 600; color: #64748B;">--/--</span>
          </div>
          <div id="list-eventos-amanha" style="display: flex; flex-direction: column; gap: 8px; max-height: 240px; overflow-y: auto;">
            <div style="color: #94A3B8; font-size: 12px; text-align: center; padding: 12px;">Carregando eventos de amanhã...</div>
          </div>
        </div>
      </div>
'''

    if 'today-tomorrow-grid' not in code:
        # Inserir logo após a kpi-row do pane-streaming
        target_kpi_end = '<div id="pane-streaming" class="pane-container">\n      <div class="kpi-row">'
        # achar o fechamento desta kpi-row
        pos_kpi = code.find(target_kpi_end)
        if pos_kpi != -1:
            pos_close = code.find('</div>\n\n      <!-- BARRA DE COMANDOS DO SHAREPOINT -->', pos_kpi)
            if pos_close != -1:
                insert_pos = pos_close + len('</div>\n')
                code = code[:insert_pos] + today_tomorrow_html + code[insert_pos:]
                print("Injected today_tomorrow_html successfully into build_portal_web.py")

    # 3. Injetar botão de Excluir Selecionados na barra de comandos de pane-list-viewer
    btn_del_html = '<button id="btn-delete-generic" class="sp-btn-cmd" style="display:none; color: #EF4444; border-color: rgba(239, 68, 68, 0.4); font-weight: 600;" onclick="deleteSelectedGenericItems()" title="Excluir registros selecionados"><span>🗑️</span> Excluir (<span id="delete-count-generic">0</span>)</button>'
    if 'id="btn-delete-generic"' not in code:
        target_bar = '<button id="btn-grid-generic" class="sp-btn-cmd btn-grid-edit" onclick="toggleGenericListGridEdit()" title="Editar linhas e colunas diretamente no navegador"><span id="btn-grid-generic-icon">田</span> <span id="btn-grid-generic-text">Editar no modo de exibição de grade</span></button>'
        if target_bar in code:
            code = code.replace(target_bar, target_bar + "\n          " + btn_del_html)
            print("Injected btn-delete-generic into command bar")

    # 4. Injetar Modal Oficial de Visualização de PDF
    modal_pdf_html = '''
  <!-- MODAL OFICIAL DE VISUALIZAÇÃO DE RELATÓRIO PDF -->
  <div id="modal-pdf-viewer" class="sp-modal-overlay" style="display: none; z-index: 999999; position: fixed; inset: 0; background: rgba(0,0,0,0.65); align-items: center; justify-content: center; backdrop-filter: blur(4px);">
    <div class="sp-modal-content" style="max-width: 980px; width: 95vw; height: 92vh; display: flex; flex-direction: column; background: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4); border: 1px solid #CBD5E1;">
      <div style="background: linear-gradient(135deg, #004578 0%, #002d50 100%); color: #fff; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1);">
        <div style="display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 14.5px;">
          <span style="font-size: 18px;">📄</span>
          <span id="pdf-viewer-title">Relatório Oficial de Auditoria</span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <a id="pdf-viewer-download" href="#" download class="sp-btn-cmd" style="color: #fff; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); text-decoration: none; padding: 5px 12px; font-size: 12px; border-radius: 6px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
            <span>⬇️</span> Baixar PDF
          </a>
          <button onclick="closePdfModal()" style="background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 4px 8px; border-radius: 4px; line-height: 1;" title="Fechar">✕</button>
        </div>
      </div>
      <div style="flex: 1; background: #525659; position: relative;">
        <iframe id="pdf-viewer-frame" style="width: 100%; height: 100%; border: none;"></iframe>
      </div>
    </div>
  </div>
'''
    if 'id="modal-pdf-viewer"' not in code:
        code = code.replace('</body>', modal_pdf_html + '\n</body>')
        print("Injected modal-pdf-viewer into HTML")

    # 5. Embutir as 151 linhas de RDP no rdp-table-body do build_portal_web.py se houver
    if static_rdp_rows and 'id="rdp-table-body">\n            <!-- Renderizado dinamicamente via JS -->' in code:
        code = code.replace(
            'id="rdp-table-body">\n            <!-- Renderizado dinamicamente via JS -->',
            f'id="rdp-table-body">\n            {static_rdp_rows}'
        )
        print("Embedded static 151 rows inside build_portal_web.py rdp-table-body")

    with open(build_script, "w", encoding="utf-8") as f:
        f.write(code)

    print("Step 1 complete: build_portal_web.py HTML skeleton updated.")

if __name__ == "__main__":
    main()
