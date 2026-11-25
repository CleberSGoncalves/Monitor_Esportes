import os
import re
import json

BASE_DIR = r"E:\desenvolvimento\Monitor_Esportes"
PORTAL_HTML_PATH = os.path.join(BASE_DIR, "portal_web", "index.html")
DOCS_HTML_PATH = os.path.join(BASE_DIR, "docs", "index.html")

def run():
    print("[*] Iniciando processamento unificado no Portal Web...")
    with open(PORTAL_HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Extrai o RDP_MASTER_DATASET do próprio JS para gerar o HTML estático das 151 linhas
    match_rdp = re.search(r"let RDP_MASTER_DATASET\s*=\s*(\[.*?\]);", content, re.DOTALL)
    if not match_rdp:
        print("[ERRO] RDP_MASTER_DATASET não encontrado no JS!")
        return

    rdp_items = json.loads(match_rdp.group(1))
    print(f"[OK] {len(rdp_items)} praças extraídas de RDP_MASTER_DATASET.")

    # Construtor do HTML estático das 151 linhas
    static_rows = []
    for idx, h in enumerate(rdp_items):
        ip1 = h.get("cs1_ip", "")
        ip2 = h.get("cs2_ip", "")
        ip3 = h.get("cs3_ip", "")
        pdu = h.get("pdu_ip", "")
        pdu_tipo = h.get("pdu_tipo", "Volt")
        router = h.get("router", "")
        praca = h.get("praca", "")
        pais = h.get("pais", "Brasil")
        regiao = h.get("regiao", "Brasil")
        flag = "🇧🇷" if pais == "Brasil" else "🌎"

        def render_cs(ip, role):
            if not ip or ip == "N/A":
                return '<span style="color:#94A3B8; font-size:11px;">-</span>'
            return f'''<div style="display:flex; align-items:center; gap:6px;">
              <code style="font-family:'JetBrains Mono',monospace; font-size:11.5px; color:#1E293B;">{ip}</code>
              <button class="sp-btn-cmd" style="padding:2px 6px; font-size:10.5px; border-radius:3px; background:#EFF6FC; border-color:#BFDBFE; color:#0078D4;" onclick="openRdpConnectModal('{ip}', '{praca}', '{role}', '{pais}', '{router}', '{pdu}', '{pdu_tipo}')" title="Conectar RDP 1-clique ({role})">
                🖥️ RDP
              </button>
              <button class="sp-btn-cmd" style="padding:2px 5px; font-size:10px; border-radius:3px; color:#64748B;" onclick="copyTextToClipboard('{ip}')" title="Copiar IP">
                📋
              </button>
            </div>'''

        def render_router(ip):
            if not ip or ip == "N/A":
                return '<span style="color:#94A3B8; font-size:11px;">-</span>'
            return f'''<div style="display:flex; align-items:center; gap:6px;">
              <code style="font-family:'JetBrains Mono',monospace; font-size:11.5px; color:#0F766E;">{ip}</code>
              <a href="http://{ip}" target="_blank" class="sp-btn-cmd" style="padding:2px 6px; font-size:10.5px; border-radius:3px; text-decoration:none; color:#0F766E; background:#F0FDFA; border-color:#99F6E4;" title="Abrir Web GUI do Roteador">
                🌐 Web
              </a>
            </div>'''

        def render_pdu(ip, tipo):
            if not ip or ip == "N/A":
                return '<span style="color:#94A3B8; font-size:11px;">Sem PDU</span>'
            return f'''<div style="display:flex; align-items:center; gap:6px;">
              <span class="badge" style="background:#FEF3C7; color:#92400E; font-size:10.5px; border:1px solid #FDE68A; padding:2px 6px;">⚡ {tipo or "Volt"}</span>
              <code style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#78350F;">{ip}</code>
              <a href="http://{ip}" target="_blank" class="sp-btn-cmd" style="padding:2px 6px; font-size:10px; border-radius:3px; text-decoration:none; color:#92400E; background:#FFFBEB; border-color:#FDE68A;" title="Acessar painel da Régua Volt">
                Reset
              </a>
            </div>'''

        row_html = f'''          <tr>
            <td style="text-align:center; color:#64748B; font-size:11.5px;">{idx + 1}</td>
            <td><b>{flag} {pais}</b> <span style="color:#64748B; font-size:11px;">({regiao})</span></td>
            <td><b style="color:#0078D4;">{praca}</b></td>
            <td>{render_router(router)}</td>
            <td>{render_cs(ip1, "CS1")}</td>
            <td>{render_cs(ip2, "CS2")}</td>
            <td>{render_cs(ip3, "CS3")}</td>
            <td>{render_pdu(pdu, pdu_tipo)}</td>
            <td><span class="badge" style="background:#DCFCE7; color:#166534; border:1px solid #BBF7D0; font-size:10.5px; padding:2px 6px;">● Online</span></td>
          </tr>'''
        static_rows.append(row_html)

    all_static_tbody = "\n".join(static_rows)

    # Injeta as 151 linhas pré-renderizadas no <tbody id="rdp-table-body">
    old_tbody_pattern = r'<tbody id="rdp-table-body">.*?</tbody>'
    new_tbody_block = f'<tbody id="rdp-table-body">\n{all_static_tbody}\n          </tbody>'
    content = re.sub(old_tbody_pattern, new_tbody_block, content, flags=re.DOTALL)
    print("[OK] Pré-renderização das 151 praças no <tbody id=\"rdp-table-body\"> injetada.")

    # 2. Atualiza buildSmartFieldHtml
    old_smart_field_pattern = r'function buildSmartFieldHtml\(colId, colTitle, currentValue\) \{.*?\n    \}'
    new_smart_field_code = '''function buildSmartFieldHtml(colId, colTitle, currentValue) {
      const titleLower = (colTitle || colId || '').toLowerCase();
      const val = currentValue !== null && currentValue !== undefined ? String(currentValue) : '';

      // 1. Host / Praça
      if (titleLower.includes("praça") || titleLower.includes("praca") || titleLower.includes("cidade") || titleLower.includes("host") || colId.toLowerCase().includes("host") || colId.toLowerCase().includes("praca")) {
        const options = OFICIAL_PRACAS.map(p => `<option value="${p}" ${val.toLowerCase() === p.toLowerCase() ? "selected" : ""}>${p}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle} *</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;" required>
              <option value="">Selecione a Praça / Host...</option>
              ${options}
            </select>
          </div>
        `;
      }

      // 2. Equipamento
      if (titleLower.includes("equipamento") || colId.toLowerCase().includes("equipamento")) {
        const equipList = ["ATRIA", "Maquina", "Switch / Roteador", "Receptor / TV BOX", "WADT", "Nobreak / PDU", "Antena", "LNB", "Cabo / Conector", "Placa de Captura", "Tomate", "Outro"];
        const options = equipList.map(e => `<option value="${e}" ${val.toLowerCase() === e.toLowerCase() ? "selected" : ""}>${e}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="">Selecione o Equipamento...</option>
              ${options}
            </select>
          </div>
        `;
      }

      // 3. CS (Canal de Serviço / Máquina)
      if (titleLower.includes("cs") || colId.toLowerCase() === "cs" || titleLower.includes("canal de serviço")) {
        const csList = ["01", "02", "03", "01, 02", "01, 02, 03", "02, 03", "CS1", "CS2", "CS3", "Todos"];
        const options = csList.map(c => `<option value="${c}" ${val.toLowerCase() === c.toLowerCase() ? "selected" : ""}>${c}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="">Selecione o CS...</option>
              ${options}
            </select>
          </div>
        `;
      }

      // 4. Emissora / Veículo
      if (titleLower.includes("emissora") || titleLower.includes("rede") || titleLower.includes("veículo") || titleLower.includes("veiculo")) {
        const options = OFICIAL_EMISSORAS.map(e => `<option value="${e}" ${val.toLowerCase() === e.toLowerCase() ? "selected" : ""}>${e}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="">Selecione a Emissora / Veículo...</option>
              ${options}
            </select>
          </div>
        `;
      }

      // 5. Data / Horas
      if (titleLower.includes("data") || titleLower.includes("hora") || titleLower.includes("solicita") || titleLower.includes("início") || titleLower.includes("inicio") || titleLower.includes("fim")) {
        let dateVal = val;
        if (dateVal.includes("T")) dateVal = dateVal.substring(0, 16);
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <div style="display: flex; gap: 6px;">
              <input type="datetime-local" name="${colId}" class="sp-form-input list-dyn-input" value="${dateVal}" style="flex: 1; height: 38px;">
              <button type="button" class="sp-btn-cmd" style="padding: 0 10px; font-size: 11.5px;" onclick="setFieldNow(this, '${colId}')">Agora</button>
            </div>
          </div>
        `;
      }

      // 6. Área Responsável (Completa e Alinhada com SharePoint)
      if (titleLower.includes("área") || titleLower.includes("area") || titleLower.includes("responsavel") || titleLower.includes("responsável")) {
        const areasList = ["N1", "N2", "Infraestrutura / Redes", "Engenharia", "Operação", "Parceiro Local", "TI Corporativa", "Preços / SAC", "Vinicius Dantas", "Lucieudes Victor", "Cassio Esteves", "Cleber Gonçalves", "Solucionado", "Outro"];
        const options = areasList.map(a => `<option value="${a}" ${val.toLowerCase() === a.toLowerCase() ? "selected" : ""}>${a}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="">Selecione a Área / Responsável...</option>
              ${options}
            </select>
          </div>
        `;
      }

      // 7. Retorno / Status
      if (titleLower.includes("retorno") || titleLower === "status_retorno" || titleLower.includes("status do retorno")) {
        const options = OFICIAL_STATUS_RETORNO.map(s => `<option value="${s}" ${val.toLowerCase() === s.toLowerCase() ? "selected" : ""}>${s}</option>`).join('');
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              ${options}
            </select>
          </div>
        `;
      }

      // 8. Booleanos (Sim / Não)
      if (titleLower.includes("presente") || titleLower.includes("recuperacao") || titleLower.includes("recuperação") || titleLower.includes("gravacao") || titleLower.includes("gravação") || titleLower.includes("informar")) {
        const isSim = val.toLowerCase() === "sim" || val.toLowerCase() === "true" || val === "1";
        return `
          <div class="sp-form-group">
            <label class="sp-form-label">${colTitle}</label>
            <select name="${colId}" class="sp-form-input list-dyn-input" style="width: 100%; height: 38px;">
              <option value="Sim" ${isSim ? "selected" : ""}>Sim</option>
              <option value="Não" ${!isSim ? "selected" : ""}>Não</option>
            </select>
          </div>
        `;
      }

      // 9. Textarea para descrições longas
      if (titleLower.includes("indício") || titleLower.includes("indicio") || titleLower.includes("descri") || titleLower.includes("ação") || titleLower.includes("acao") || titleLower.includes("observa") || titleLower.includes("resposta")) {
        return `
          <div class="sp-form-group" style="grid-column: 1 / -1;">
            <label class="sp-form-label">${colTitle}</label>
            <textarea name="${colId}" class="sp-form-input list-dyn-input" rows="4" placeholder="Descreva os detalhes..." style="width: 100%; font-family: inherit; resize: vertical;">${val}</textarea>
          </div>
        `;
      }

      // 10. Padrão
      return `
        <div class="sp-form-group">
          <label class="sp-form-label">${colTitle}</label>
          <input type="text" name="${colId}" class="sp-form-input list-dyn-input" value="${val}" placeholder="Informe ${colTitle}...">
        </div>
      `;
    }'''

    content = re.sub(old_smart_field_pattern, new_smart_field_code, content, flags=re.DOTALL)

    # 3. Modal RDP Connect HTML
    modal_rdp_html = '''
  <!-- MODAL DE CONEXÃO RDP E ACESSO REMOTO NATIVO -->
  <div class="modal-overlay" id="modal-rdp-connect" style="display: none; align-items: center; justify-content: center; z-index: 10000; position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px);">
    <div class="modal-card" style="max-width: 600px; width: 95%; background: white; border-radius: 8px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); overflow: hidden;">
      <div class="modal-header" style="background: #0078D4; color: white; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center;">
        <div style="display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 20px;">🖥️</span>
          <h3 id="rdp-modal-title" style="margin: 0; font-size: 16px; font-weight: 700;">Conectar via RDP &mdash; Altamira (CS1)</h3>
        </div>
        <button type="button" class="modal-close-btn" onclick="closeRdpModal()" style="background: none; border: none; color: white; font-size: 22px; cursor: pointer;">&times;</button>
      </div>
      <div class="modal-body" style="padding: 20px;">
        <div style="background: #F0F9FF; border: 1px solid #BAE6FD; border-left: 4px solid #0078D4; padding: 10px 14px; border-radius: 4px; margin-bottom: 16px; font-size: 12.5px; color: #0369A1;">
          <b>Central de Acesso Remoto Oficial:</b> Conecte-se com segurança à estação via protocolo Remote Desktop (RDP - Porta 3389).
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
          <div>
            <label style="font-size: 11.5px; color: #64748B; font-weight: 700; display: block; margin-bottom: 4px;">IP da Estação / Host</label>
            <div style="display: flex; gap: 6px;">
              <input type="text" id="rdp-modal-ip" readonly style="flex: 1; padding: 6px 10px; font-family: monospace; font-size: 12px; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;" value="">
              <button class="sp-btn-cmd" onclick="copyRdpIp()" title="Copiar IP">📋 Copiar</button>
            </div>
          </div>
          <div>
            <label style="font-size: 11.5px; color: #64748B; font-weight: 700; display: block; margin-bottom: 4px;">Comando Direto (mstsc)</label>
            <div style="display: flex; gap: 6px;">
              <input type="text" id="rdp-modal-cmd" readonly style="flex: 1; padding: 6px 10px; font-family: monospace; font-size: 11.5px; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px;" value="">
              <button class="sp-btn-cmd" onclick="copyRdpMstscCmd()" title="Copiar comando">📋</button>
            </div>
          </div>
        </div>
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 12px; margin-bottom: 16px; font-size: 12px; color: #334155;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span>Gateway / Roteador: <b id="rdp-modal-router">--</b></span>
            <span>Régua Volt (PDU): <b id="rdp-modal-pdu">--</b></span>
          </div>
          <div>Região: <b id="rdp-modal-regiao">--</b></div>
        </div>
      </div>
      <div class="sp-modal-footer" style="padding: 12px 20px; background: #F8FAFC; border-top: 1px solid #E2E8F0; display: flex; justify-content: space-between; align-items: center;">
        <button type="button" class="btn-action btn-action-secondary" onclick="closeRdpModal()">Fechar</button>
        <button type="button" class="btn-action btn-action-primary" onclick="downloadCleanRdpFile()" style="display: flex; align-items: center; gap: 8px;">
          <span>📥</span> Baixar Conexão (.rdp)
        </button>
      </div>
    </div>
  </div>
'''

    if 'id="modal-rdp-connect"' not in content:
        content = content.replace("</body>", f"{modal_rdp_html}\n</body>")

    # 4. JS Funções RDP
    js_rdp_funcs = '''
    let currentRdpModalData = {};

    function openRdpConnectModal(ip, praca, role, pais, router, pdu, pdu_tipo) {
      currentRdpModalData = { ip, praca, role, pais, router, pdu, pdu_tipo };
      const modal = document.getElementById("modal-rdp-connect");
      if (!modal) return;
      const titleEl = document.getElementById("rdp-modal-title");
      if (titleEl) titleEl.innerText = `Conectar via RDP — ${praca} (${role})`;
      const ipEl = document.getElementById("rdp-modal-ip");
      if (ipEl) ipEl.value = ip;
      const cmdEl = document.getElementById("rdp-modal-cmd");
      if (cmdEl) cmdEl.value = `mstsc /v:${ip}`;
      const routerEl = document.getElementById("rdp-modal-router");
      if (routerEl) routerEl.innerText = router || "--";
      const pduEl = document.getElementById("rdp-modal-pdu");
      if (pduEl) pduEl.innerText = pdu ? `${pdu} (${pdu_tipo || 'Volt'})` : "Sem PDU";
      const regiaoEl = document.getElementById("rdp-modal-regiao");
      if (regiaoEl) regiaoEl.innerText = `${pais || 'Brasil'}`;

      modal.style.display = "flex";
    }
    window.openRdpConnectModal = openRdpConnectModal;

    function closeRdpModal() {
      const modal = document.getElementById("modal-rdp-connect");
      if (modal) modal.style.display = "none";
    }
    window.closeRdpModal = closeRdpModal;

    function copyRdpIp() {
      if (currentRdpModalData.ip) copyTextToClipboard(currentRdpModalData.ip);
    }
    window.copyRdpIp = copyRdpIp;

    function copyRdpMstscCmd() {
      if (currentRdpModalData.ip) copyTextToClipboard(`mstsc /v:${currentRdpModalData.ip}`);
    }
    window.copyRdpMstscCmd = copyRdpMstscCmd;

    function downloadCleanRdpFile() {
      if (currentRdpModalData.ip) {
        triggerRdpConnect(currentRdpModalData.ip, currentRdpModalData.praca, currentRdpModalData.role, 3389);
      }
    }
    window.downloadCleanRdpFile = downloadCleanRdpFile;
'''

    if 'function openRdpConnectModal' not in content:
        content = content.replace("function triggerRdpConnect", f"{js_rdp_funcs}\n    function triggerRdpConnect")

    # Garante que renderRdpTable não zere as linhas estáticas caso RDP_MASTER_DATASET ainda não tenha sido filtrado
    old_render_rdp = r'function renderRdpTable\(\) \{.*?tbody\.innerHTML = "";'
    new_render_rdp = '''function renderRdpTable() {
      const tbody = document.getElementById("rdp-table-body");
      if (!tbody) return;'''
    content = re.sub(old_render_rdp, new_render_rdp, content, flags=re.DOTALL)

    # Substitui qualquer menção a SharePoint no botão de exportar/abrir da barra RDP
    content = content.replace("Abrir Pasta no SharePoint", "Biblioteca de Pastas RDP")
    content = content.replace("https://adgbl.sharepoint.com/sites/suportecaptacao/Acesso%20Remoto", "javascript:openDrive('Acesso Remoto')")

    with open(PORTAL_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    with open(DOCS_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("[SUCESSO] Atualização completa e salva em portal_web/index.html e docs/index.html!")

if __name__ == "__main__":
    run()
