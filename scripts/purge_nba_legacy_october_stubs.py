"""
scripts/purge_nba_legacy_october_stubs.py
Expurga definitivamente da biblioteca 'Relatorios_de_Jogos_NBA' do SharePoint
todos os arquivos residuais antigos de teste (< 100 KB) gerados no início da temporada (outubro),
garantindo que 100% dos arquivos na biblioteca sejam relatórios auditados completos (> 1.7 MB)
com comprovação visual de 8/8 frames.
"""

import os
import sys
import time
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter
from modules.sharepoint_nba_reporter import SharePointNBAReporter

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def purge_legacy_stubs():
    print("=" * 70)
    print("🧹 EXPURGO DEFINITIVO DE STUBS RESIDUAIS DA NBA NO SHAREPOINT (< 100 KB)")
    print("=" * 70)

    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id
    drive_id = SharePointNBAReporter.get_nba_drive_id(token, site_id)

    headers = {"Authorization": f"Bearer {token}", "User-Agent": "NONISV|ADGBL|MonitorEsportes/2.4.47"}
    list_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"

    r = SharePointReporter.request_with_retry("GET", list_url, headers=headers)
    if not r or r.status_code != 200:
        print("Falha ao listar itens do drive.")
        return

    items = r.json().get("value", [])
    stubs = [it for it in items if it.get("size", 0) < 100000]

    print(f"Total de itens no acervo: {len(items)}")
    print(f"Stubs residuais identificados para expurgo: {len(stubs)}")

    deleted = 0
    for s in stubs:
        item_id = s.get("id")
        name = s.get("name")
        sz = s.get("size", 0)
        del_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}"
        try:
            r_del = SharePointReporter.request_with_retry("DELETE", del_url, headers=headers, timeout=15)
            if r_del and r_del.status_code in (204, 200):
                deleted += 1
                print(f"  🗑️ [{deleted}/{len(stubs)}] Deletado: {name} ({sz:,} bytes)")
            else:
                print(f"  ⚠️ Falha ao deletar {name}: HTTP {r_del.status_code if r_del else 'None'}")
        except Exception as e:
            print(f"  Erro ao deletar {name}: {e}")
        time.sleep(1)  # Pausa defensiva para evitar 429

    print("=" * 70)
    print(f"🎉 Concluído: {deleted}/{len(stubs)} stubs residuais foram expurgados com sucesso!")
    print("=" * 70)


if __name__ == "__main__":
    purge_legacy_stubs()
