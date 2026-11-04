import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SharePointReporter
import requests
import json

reporter = SharePointReporter()
access_token = reporter.obter_token_graph()
site_id = reporter._cached_site_id or "adgbl.sharepoint.com,d07ee50e-7901-4f11-be80-5b6e66ff7284,796df1ff-b631-4122-b52e-ec5f884a44b1"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json"
}

import time

def graph_get(url):
    for attempt in range(5):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 4))
            print(f"Throttled (429). Aguardando {retry_after}s (tentativa {attempt+1}/5)...")
            time.sleep(retry_after)
            continue
        return resp
    return resp

def inspect_list(list_name):
    print(f"\n================ LISTA: {list_name} ================")
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_name}/items?expand=fields&$top=100"
    resp = graph_get(url)
    if resp.status_code != 200:
        print(f"Erro ao acessar {list_name}: {resp.status_code} - {resp.text}")
        return []
    items = resp.json().get('value', [])
    print(f"Total de itens em '{list_name}': {len(items)}")
    for it in items:
        f = it.get('fields', {})
        iid = it.get('id')
        title = f.get('Title') or f.get('Jogo') or f.get('Match') or 'Sem Titulo'
        data = f.get('Data') or f.get('DataJogo') or f.get('DataPartida') or ''
        plat = f.get('Plataforma') or f.get('Canal') or ''
        aud = f.get('Auditado')
        pdf = f.get('RelatorioPDF') or f.get('LinkPDF') or ''
        print(f"ID: {iid:<3} | Data: {data:<12} | Plat: {plat:<18} | Título: {title:<30} | Auditado: {aud}")
    return items

yt_items = inspect_list("Relatorio Jogos Youtube")
oficial_items = inspect_list("Relatorios_de_Jogos")
