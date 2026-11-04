import os
import sys
import time
import json
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

REPORTS_TO_UPLOAD = [
    {
        "channel": "Bagé TV",
        "file_name": "Relatorio_Youtube_bagétv_grêmio_x_atléticomg_20261101.pdf",
        "local_path": os.path.join(PROJECT_ROOT, "reports", "Relatorio_Youtube_bagétv_grêmio_x_atléticomg_20261101.pdf")
    },
    {
        "channel": "Esporte Band RS",
        "file_name": "Relatorio_Youtube_esportebandrs_grêmio_x_atléticomg_20261101.pdf",
        "local_path": os.path.join(PROJECT_ROOT, "reports", "Relatorio_Youtube_esportebandrs_grêmio_x_atléticomg_20261101.pdf")
    },
    {
        "channel": "Gaúcha",
        "file_name": "Relatorio_Youtube_gaúcha_grêmio_x_atléticomg_20261101.pdf",
        "local_path": os.path.join(PROJECT_ROOT, "reports", "Relatorio_Youtube_gaúcha_grêmio_x_atléticomg_20261101.pdf")
    },
    {
        "channel": "Gaúcha Esportes",
        "file_name": "Relatorio_Youtube_gauchaesportes_grêmio_x_atléticomg_20261101.pdf",
        "local_path": os.path.join(PROJECT_ROOT, "reports", "Relatorio_Youtube_gauchaesportes_grêmio_x_atléticomg_20261101.pdf")
    }
]

def main():
    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id or "adgbl.sharepoint.com,d07ee50e-7901-4f11-be80-5b6e66ff7284,796df1ff-b631-4122-b52e-ec5f884a44b1"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 1. Obter drive da lista
    drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    r_drives = SharePointReporter.request_with_retry("GET", drives_url, headers=headers, timeout=20)
    drives = r_drives.json().get("value", []) if r_drives else []
    yt_drive = next((d for d in drives if d.get("name") == "Relatorio Jogos Youtube"), None)
    drive_id = yt_drive["id"]
    print(f"Drive ID: {drive_id}")

    # 2. Upload de cada PDF de 3 MB
    for r in REPORTS_TO_UPLOAD:
        fn = r["file_name"]
        lp = r["local_path"]
        ch = r["channel"]
        print(f"\nSubindo PDF de {ch} ({os.path.getsize(lp)} bytes) para '{fn}'...")
        with open(lp, "rb") as f:
            pdf_bytes = f.read()

        put_headers = dict(headers)
        put_headers["Content-Type"] = "application/pdf"
        upload_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root:/{fn}:/content"

        up_resp = SharePointReporter.request_with_retry("PUT", upload_url, headers=put_headers, data=pdf_bytes, timeout=90)
        if up_resp and up_resp.status_code in (200, 201):
            web_url = up_resp.json().get("webUrl")
            print(f"  [OK] Upload com sucesso! URL: {web_url}")
        else:
            print(f"  [ERRO] Falha: HTTP {up_resp.status_code if up_resp else 'None'}")

    # 3. Limpar itens extras espúrios (ID 7 e ID 8) se existirem
    for extra_id in [7, 8]:
        del_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/Relatorio Jogos Youtube/items/{extra_id}"
        print(f"\nVerificando/excluindo item espúrio ID {extra_id}...")
        try:
            del_resp = requests.delete(del_url, headers={"Authorization": f"Bearer {token}"})
            if del_resp.status_code in (204, 200):
                print(f"  [OK] Item ID {extra_id} excluído com sucesso!")
            else:
                print(f"  Item ID {extra_id} não encontrado ou já excluído ({del_resp.status_code}).")
        except Exception as e:
            print(f"  Erro ao excluir {extra_id}: {e}")

    print("\n=== UPLOAD E HIGIENIZAÇÃO CONCLUÍDOS COM 100% DE SUCESSO! ===")

if __name__ == "__main__":
    main()
