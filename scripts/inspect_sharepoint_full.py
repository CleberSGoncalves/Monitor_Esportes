import sys
import json
sys.path.insert(0, '.')
from modules.reporte_eventos.sharepoint_client import _obter_token_graph, _obter_site_e_lista_ids, _graph_request

token = _obter_token_graph()
headers = {'Authorization': f'Bearer {token}'}
site_id, list_id = _obter_site_e_lista_ids(headers)

url = f'https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{list_id}/items?expand=fields&$top=100'
items = []
while url:
    r = _graph_request('GET', url, headers=headers)
    if not r or r.status_code != 200:
        print('Error:', r.status_code if r else 'No response')
        break
    data = r.json()
    items.extend(data.get('value', []))
    url = data.get('@odata.nextLink')

print(f"Total SharePoint items fetched: {len(items)}")

# Sort by numeric id descending
items_sorted = sorted(items, key=lambda x: int(x.get('id', 0)), reverse=True)

print("\n--- TOP 10 LATEST ITEMS ---")
for it in items_sorted[:10]:
    f = it.get('fields', {})
    print(f"ID {it.get('id')}: {f.get('Data', '')[:10]} {f.get('Hor_x00e1_rio')} - {f.get('Title')} - {f.get('Partida')} - Canal: {f.get('Transmiss_x00e3_o')} - Resp: {f.get('BKP_x0020__x0028_Uso_x0020_Supor')} - PVID: {f.get('PVID')} - Status: {f.get('StatusdeEntrega')} - Prog: {f.get('Programado_x0020_TV_x0020_BOX_x0')}")

# Save all items to a json file for inspection
with open('config/sharepoint_all_items_dump.json', 'w', encoding='utf-8') as f_out:
    json.dump(items, f_out, ensure_ascii=False, indent=2)
print("Dumped to config/sharepoint_all_items_dump.json")
