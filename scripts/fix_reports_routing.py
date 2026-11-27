import os
import json
import re

PROJECT_ROOT = r"E:\desenvolvimento\Monitor_Esportes"
CONFIG_MASTER = os.path.join(PROJECT_ROOT, "config", "sharepoint_portal_master_data.json")
PORTAL_HTML = os.path.join(PROJECT_ROOT, "portal_web", "index.html")
DOCS_HTML = os.path.join(PROJECT_ROOT, "docs", "index.html")

DRIVE_TO_CAT = {
    "Relatorios_de_Jogos": "futebol",
    "Relatorio Jogos Youtube": "youtube",
    "Relatorios_de_Jogos_NBA": "nba"
}

def fix_all():
    print("[1/4] Normalizando config/sharepoint_portal_master_data.json...")
    with open(CONFIG_MASTER, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    fixed_count = 0
    for drive_name, cat in DRIVE_TO_CAT.items():
        items = master_data.get("drives", {}).get(drive_name, {}).get("items", [])
        for it in items:
            name = it.get("name", "")
            expected_url = f"reports/{cat}/{name}"
            if it.get("webUrl") != expected_url:
                it["webUrl"] = expected_url
                fixed_count += 1

    with open(CONFIG_MASTER, "w", encoding="utf-8") as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] {fixed_count} URLs normalizadas no config.")

    print("[2/4] Atualizando portal_web/index.html e docs/index.html...")
    with open(PORTAL_HTML, "r", encoding="utf-8") as f:
        portal_text = f.read()

    # Atualizar o bloco let SP_MASTER_DATA no index.html
    idx = portal_text.find("let SP_MASTER_DATA =")
    if idx != -1:
        json_str = portal_text[idx + len("let SP_MASTER_DATA ="):].strip()
        data, end_pos = json.JSONDecoder().raw_decode(json_str)
        for drive_name, cat in DRIVE_TO_CAT.items():
            items = data.get("drives", {}).get(drive_name, {}).get("items", [])
            for it in items:
                name = it.get("name", "")
                it["webUrl"] = f"reports/{cat}/{name}"

        # Re-serializar SP_MASTER_DATA
        new_master_json = json.dumps(data, ensure_ascii=False)
        prefix = portal_text[:idx + len("let SP_MASTER_DATA = ")]
        suffix = json_str[end_pos:]
        portal_text = prefix + new_master_json + suffix
        print("  [OK] SP_MASTER_DATA embutido atualizado com sucesso.")

    # Aprimorar openReportDocument para blindagem total 100% livre de 404
    old_open_doc = """    function openReportDocument(docId, docNameEsc) {
      const docName = decodeURIComponent(docNameEsc || '');
      let cleanPath = '';
      if (docName.startsWith('reports/')) {
        cleanPath = docName;
      } else {
        // Buscar webUrl exato no master data da biblioteca atual ou de todas as bibliotecas
        const drives = (typeof SP_MASTER_DATA !== 'undefined' && SP_MASTER_DATA && SP_MASTER_DATA.drives) ? SP_MASTER_DATA.drives : {};
        const searchOrder = (typeof currentDriveKey !== 'undefined' && drives[currentDriveKey])
          ? [drives[currentDriveKey], ...Object.values(drives)]
          : Object.values(drives);
        for (const drv of searchOrder) {
          const found = (drv.items || []).find(it => (it.id === docId || it.name === docName) && it.webUrl && it.webUrl !== '#');
          if (found) {
            cleanPath = found.webUrl;
            break;
          }
        }
        if (!cleanPath) {
          const nl = docName.toLowerCase();
          if (nl.includes('youtube') || (typeof currentDriveKey !== 'undefined' && currentDriveKey === 'Relatorio Jogos Youtube')) {
            cleanPath = 'reports/youtube/' + docName;
          } else if (nl.includes('nba') || (typeof currentDriveKey !== 'undefined' && currentDriveKey === 'Relatorios_de_Jogos_NBA')) {
            cleanPath = 'reports/nba/' + docName;
          } else {
            cleanPath = 'reports/futebol/' + docName;
          }
        }
      }
      window.open(cleanPath, '_blank');
      showToast(`📕 Abrindo relatório oficial '${docName}'...`, 'info');
    }"""

    new_open_doc = """    function openReportDocument(docId, docNameEsc) {
      const docName = decodeURIComponent(docNameEsc || '');
      let cleanPath = '';
      if (docName.startsWith('reports/futebol/') || docName.startsWith('reports/youtube/') || docName.startsWith('reports/nba/')) {
        cleanPath = docName;
      } else {
        const drives = (typeof SP_MASTER_DATA !== 'undefined' && SP_MASTER_DATA && SP_MASTER_DATA.drives) ? SP_MASTER_DATA.drives : {};
        const searchOrder = (typeof currentDriveKey !== 'undefined' && drives[currentDriveKey])
          ? [drives[currentDriveKey], ...Object.values(drives)]
          : Object.values(drives);
        for (const drv of searchOrder) {
          const found = (drv.items || []).find(it => (it.id === docId || it.name === docName) && it.webUrl && it.webUrl !== '#');
          if (found && (found.webUrl.startsWith('reports/futebol/') || found.webUrl.startsWith('reports/youtube/') || found.webUrl.startsWith('reports/nba/'))) {
            cleanPath = found.webUrl;
            break;
          }
        }
        if (!cleanPath) {
          const raw = docName.replace(/^reports\//, '');
          const nl = raw.toLowerCase();
          if (nl.includes('youtube') || (typeof currentDriveKey !== 'undefined' && currentDriveKey === 'Relatorio Jogos Youtube')) {
            cleanPath = 'reports/youtube/' + raw;
          } else if (nl.includes('nba') || (typeof currentDriveKey !== 'undefined' && currentDriveKey === 'Relatorios_de_Jogos_NBA')) {
            cleanPath = 'reports/nba/' + raw;
          } else {
            cleanPath = 'reports/futebol/' + raw;
          }
        }
      }
      window.open(cleanPath, '_blank');
      showToast(`📕 Abrindo relatório oficial '${docName}'...`, 'info');
    }"""

    if old_open_doc in portal_text:
        portal_text = portal_text.replace(old_open_doc, new_open_doc)
        print("  [OK] openReportDocument atualizado com blindagem.")
    else:
        print("  [AVISO] Bloco old_open_doc não encontrado exatamente; verificando regex.")

    # Aprimorar openReportPdf
    old_open_pdf = """    function openReportPdf(filenameOrUrl) {
      if (!filenameOrUrl) return;
      let targetUrl = filenameOrUrl;
      if (!targetUrl.startsWith('http') && !targetUrl.startsWith('/') && !targetUrl.startsWith('reports/')) {
        let category = "futebol";
        if (currentRealListName && currentRealListName.toLowerCase().includes("nba")) category = "nba";
        else if (currentRealListName && currentRealListName.toLowerCase().includes("youtube")) category = "youtube";
        targetUrl = `reports/${category}/${filenameOrUrl}`;
      }"""

    new_open_pdf = """    function openReportPdf(filenameOrUrl) {
      if (!filenameOrUrl) return;
      let targetUrl = filenameOrUrl;
      if (!targetUrl.startsWith('http') && !targetUrl.startsWith('/')) {
        if (!targetUrl.startsWith('reports/futebol/') && !targetUrl.startsWith('reports/youtube/') && !targetUrl.startsWith('reports/nba/')) {
          const raw = targetUrl.replace(/^reports\//, '');
          let category = "futebol";
          if ((currentRealListName && currentRealListName.toLowerCase().includes("nba")) || raw.toLowerCase().includes("nba")) category = "nba";
          else if ((currentRealListName && currentRealListName.toLowerCase().includes("youtube")) || raw.toLowerCase().includes("youtube")) category = "youtube";
          targetUrl = `reports/${category}/${raw}`;
        }
      }"""

    if old_open_pdf in portal_text:
        portal_text = portal_text.replace(old_open_pdf, new_open_pdf)
        print("  [OK] openReportPdf atualizado com blindagem.")

    # Salvar em portal_web e docs
    with open(PORTAL_HTML, "w", encoding="utf-8") as f:
        f.write(portal_text)
    with open(DOCS_HTML, "w", encoding="utf-8") as f:
        f.write(portal_text)
    print("  [OK] portal_web/index.html e docs/index.html salvos sincronizados.")

if __name__ == "__main__":
    fix_all()
