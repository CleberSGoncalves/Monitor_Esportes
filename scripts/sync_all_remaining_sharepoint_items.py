import requests
import json
import time

url = 'https://script.google.com/macros/s/AKfycbxzWKi1dNiGUiF15Ysl_69Pe2dt2vUpe1UBQ9xadPenmnsH68VOk6W1ZMwhRQkRpkBX/exec'

print("1. Carregando registros limpos do SharePoint...")
with open('config/sharepoint_clean_migrated_events.json', encoding='utf-8') as f:
    all_sp_records = json.load(f)
print(f"Total de registros na base do SharePoint: {len(all_sp_records)}")

print("2. Consultando registros atualmente presentes no Google Sheets...")
r_get = requests.get(url, timeout=30)
if r_get.status_code != 200:
    print(f"Erro ao consultar Google Sheets: {r_get.status_code}")
    exit(1)

current_rows = r_get.json()
print(f"Total de linhas atualmente no Google Sheets: {len(current_rows)}")

# Gera chaves para identificar o que já está na planilha
def make_key(partida, data, canal):
    p = str(partida or "").lower().replace(" ", "").replace("x", "")
    d = str(data or "")[:10].replace("/", "").replace("-", "")
    c = str(canal or "").lower().replace(" ", "")
    return f"{p}_{d}_{c}"

existing_keys = set()
for r in current_rows:
    k = make_key(r.get("partida"), r.get("data"), r.get("canal"))
    if k:
        existing_keys.add(k)

# Filtra itens que faltam enviar
pending_records = []
for r in all_sp_records:
    k = make_key(r.get("partida"), r.get("data"), r.get("canal"))
    if k not in existing_keys:
        pending_records.append(r)

print(f"Total de registros pendentes de envio: {len(pending_records)}")

if not pending_records:
    print("Todos os registros do SharePoint já estão no Google Sheets!")
    exit(0)

# Envia em lotes de 40 itens
batch_size = 40
total_batches = (len(pending_records) + batch_size - 1) // batch_size
total_enviados = 0

print(f"\nIniciando envio em {total_batches} lotes de {batch_size} itens...")
for i in range(0, len(pending_records), batch_size):
    batch = pending_records[i:i + batch_size]
    batch_idx = (i // batch_size) + 1
    t0 = time.time()
    try:
        r_post = requests.post(url, json={"events": batch}, timeout=60)
        elapsed = round(time.time() - t0, 2)
        if r_post.status_code == 200:
            res_json = r_post.json() if "{" in r_post.text else {}
            inseridos = res_json.get("inseridos", len(batch))
            total_enviados += inseridos
            print(f"Lote {batch_idx}/{total_batches} ({len(batch)} itens) -> Sucesso ({elapsed}s) | Inseridos: {inseridos}")
        else:
            print(f"Lote {batch_idx}/{total_batches} -> HTTP {r_post.status_code} ({elapsed}s)")
    except Exception as e:
        print(f"Lote {batch_idx}/{total_batches} -> Exceção: {e}")
    time.sleep(1) # pausa preventiva

print(f"\nMigração concluída com sucesso! Total enviado: {total_enviados}")
