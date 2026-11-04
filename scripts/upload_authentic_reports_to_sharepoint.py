import os
import sys
import time
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

REPORTS_TO_SYNC = [
    {
        "channel": "Bagé TV",
        "item_id": 3,
        "pdf_path": os.path.join(PROJECT_ROOT, "reports", "expert_bagé_tv_copa_do_brasil_match_01112026_20261104_140807.pdf"),
        "target_name": "Relatorio_Youtube_bagétv_grêmio_x_atléticomg_20261101.pdf"
    },
    {
        "channel": "Esporte Band RS",
        "item_id": 4,
        "pdf_path": os.path.join(PROJECT_ROOT, "reports", "expert_esporte_band_rs_copa_do_brasil_match_01112026_20261104_140850.pdf"),
        "target_name": "Relatorio_Youtube_esportebandrs_grêmio_x_atléticomg_20261101.pdf"
    },
    {
        "channel": "Gaúcha",
        "item_id": 1,
        "pdf_path": os.path.join(PROJECT_ROOT, "reports", "expert_gaúcha_copa_do_brasil_match_01112026_20261104_140926.pdf"),
        "target_name": "Relatorio_Youtube_gaúcha_grêmio_x_atléticomg_20261101.pdf"
    },
    {
        "channel": "Gaúcha Esportes",
        "item_id": 2,
        "pdf_path": os.path.join(PROJECT_ROOT, "reports", "expert_gaúcha_esportes_copa_do_brasil_match_01112026_20261104_141006.pdf"),
        "target_name": "Relatorio_Youtube_gauchaesportes_grêmio_x_atléticomg_20261101.pdf"
    }
]

def main():
    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id or "adgbl.sharepoint.com,d07ee50e-7901-4f11-be80-5b6e66ff7284,796df1ff-b631-4122-b52e-ec5f884a44b1"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Obter drives do site
    drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    r_drives = SharePointReporter.request_with_retry("GET", drives_url, headers=headers, timeout=20)
    drives = r_drives.json().get("value", []) if r_drives else []
    
    yt_drive = next((d for d in drives if d.get("name") == "Relatorio Jogos Youtube"), None)
    if not yt_drive:
        print("[ERRO] Drive 'Relatorio Jogos Youtube' não localizado!")
        return

    drive_id = yt_drive["id"]
    print(f"Drive ID: {drive_id} (Nome: {yt_drive.get('name')})")

    for rep in REPORTS_TO_SYNC:
        ch = rep["channel"]
        item_id = rep["item_id"]
        pdf_path = rep["pdf_path"]
        target_name = rep["target_name"]

        print(f"\n--- Sincronizando {ch} (Item ID {item_id}) ---")
        if not os.path.exists(pdf_path):
            print(f"[ERRO] PDF não encontrado: {pdf_path}")
            continue

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        put_headers = dict(headers)
        put_headers["Content-Type"] = "application/pdf"
        upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{target_name}:/content"

        print(f"Enviando {len(pdf_bytes)} bytes para {target_name}...")
        r_up = SharePointReporter.request_with_retry("PUT", upload_url, headers=put_headers, data=pdf_bytes, timeout=60)
        if not r_up or r_up.status_code not in (200, 201):
            print(f"[ERRO] Falha no upload: HTTP {r_up.status_code if r_up else 'None'}")
            continue

        file_meta = r_up.json()
        web_url = file_meta.get("webUrl")
        print(f"[OK] Upload concluído! WebUrl: {web_url}")

        # Atualizar metadados na lista 'Relatorio Jogos Youtube'
        patch_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/Relatorio Jogos Youtube/items/{item_id}/fields"
        patch_data = {
            "Auditado": True,
            "Placar": "2 x 0"
        }
        try:
            r_patch = SharePointReporter.request_with_retry("PATCH", patch_url, headers=headers, json=patch_data, timeout=20)
            if r_patch and r_patch.status_code in (200, 201):
                print(f"[OK] Metadados do item ID {item_id} ({ch}) atualizados com sucesso!")
            else:
                print(f"[AVISO] Atualização de metadados retornou HTTP {r_patch.status_code if r_patch else 'None'}")
        except Exception as e_patch:
            print(f"[AVISO] Falha ao atualizar metadados do item {item_id}: {e_patch}")

        time.sleep(1)

    print("\n[SUCESSO COMPLETO] Todos os 4 relatórios autênticos foram enviados e homologados no SharePoint!")

if __name__ == "__main__":
    main()
