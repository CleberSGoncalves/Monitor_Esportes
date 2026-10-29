import os
import sys
import time
import json
import requests
from datetime import datetime

# Configurar stdout UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter
from modules.report_generator import ReportGenerator

def graph_call(method, url, **kwargs):
    """Executa chamadas Graph tratando throttling 429 rigorosamente."""
    max_attempts = 15
    for attempt in range(max_attempts):
        try:
            r = requests.request(method, url, **kwargs)
            if r.status_code == 429:
                wait_sec = int(r.headers.get("Retry-After", 10))
                try:
                    body = r.json()
                    wait_sec = int(body.get("retryAfterSeconds") or wait_sec)
                except Exception:
                    pass
                wait_sec = max(wait_sec, 5)
                print(f"[Graph API 429] Throttled. Aguardando {wait_sec}s (tentativa {attempt+1}/{max_attempts})...", flush=True)
                time.sleep(wait_sec)
                continue
            return r
        except Exception as e:
            print(f"[Graph API Exception] {e}. Aguardando 5s...", flush=True)
            time.sleep(5)
    return None

def main():
    token = SharePointReporter.obter_token_graph()
    site_id = SharePointReporter._cached_site_id
    drive_id = SharePointReporter._cached_drive_id
    list_id = "ae3e2afa-d937-41ad-af48-ecd65fd86143" # Relatorios_de_Jogos
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    print("=== ETAPA 1: Identificar Itens de Teste/Ocorrência do YouTube no SharePoint ===")
    url_items = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?$expand=fields&$top=150"
    r = graph_call("GET", url_items, headers=headers)
    if not r or r.status_code != 200:
        print("Falha ao listar itens:", r.status_code if r else 'None')
        return

    items = r.json().get("value", [])
    print(f"Total de itens na lista: {len(items)}")

    items_to_delete = []
    for it in items:
        f = it.get("fields", {})
        partida = f.get("Partida") or f.get("Title") or ""
        plat = f.get("Plataforma") or ""
        data_h = f.get("Data_Hora") or ""
        item_id = it.get("id")

        p_low = partida.lower()
        # Critérios para exclusão de testes/ocorrências dos canais:
        is_case = "[ocorrência]" in p_low or "[ocorrencia]" in p_low
        is_bage = "bagé" in p_low or "bage" in p_low
        is_jornada = "jornada" in p_low and ("digital" in p_low or "super" in p_low or "bagé" in p_low)
        is_outro_test = plat == "Outro" and ("3 x 0" in p_low or "coritiba x grêmio" in p_low or "inter x botafogo" in p_low)
        is_corrupt_vasco = ("vasco x remo" in p_low or "vasco da gama x remo" in p_low) and not data_h

        if is_case or is_bage or is_jornada or is_outro_test or is_corrupt_vasco:
            items_to_delete.append((item_id, partida, plat))

    print(f"\nEncontrados {len(items_to_delete)} itens impróprios para exclusão:")
    for item_id, partida, plat in items_to_delete:
        print(f" - ID {item_id}: '{partida}' (Plat: {plat})")

    # Excluir da lista
    for item_id, partida, plat in items_to_delete:
        del_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items/{item_id}"
        r_del = graph_call("DELETE", del_url, headers=headers)
        if r_del and r_del.status_code in (200, 204):
            print(f" -> Item {item_id} ('{partida}') excluído com sucesso da lista.")
        else:
            print(f" -> Falha ao excluir item {item_id}: {r_del.status_code if r_del else 'None'}")

    print("\n=== ETAPA 2: Identificar e Excluir PDFs de Ocorrência/Teste na Biblioteca ===")
    url_files = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$top=150"
    r_f = graph_call("GET", url_files, headers=headers)
    if r_f and r_f.status_code == 200:
        files = r_f.json().get("value", [])
        print(f"Total de arquivos na biblioteca: {len(files)}")
        for f in files:
            name = f.get("name", "")
            f_id = f.get("id")
            n_low = name.lower()
            if "caso_ocorrencia" in n_low or "auditoria_geral_lives" in n_low or "bage" in n_low or "jornada" in n_low:
                print(f" -> Excluindo arquivo PDF impróprio: {name} (ID: {f_id})")
                del_file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{f_id}"
                r_df = graph_call("DELETE", del_file_url, headers=headers)
                if r_df and r_df.status_code in (200, 204):
                    print(f"    OK! {name} excluído.")
                else:
                    print(f"    Falha ao excluir {name}: {r_df.status_code if r_df else 'None'}")

if __name__ == "__main__":
    main()
