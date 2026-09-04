"""
Script para listar e limpar duplicatas no SharePoint - Relatorios_de_Jogos.
Mantém apenas o arquivo mais recente de cada combinação Partida+Data.
"""
import os
import sys
import json
import requests
from datetime import datetime, timezone

project_root = r"e:\desenvolvimento\Monitor_Esportes"
sys.path.insert(0, project_root)

from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

def get_all_items():
    token = SharePointReporter.obter_token_graph()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Resolver Site ID
    site_url = f"https://graph.microsoft.com/v1.0/sites/{SP_CONFIG['tenant_hostname']}:{SP_CONFIG['site_path']}"
    r_site = requests.get(site_url, headers=headers, timeout=15)
    r_site.raise_for_status()
    site_id = r_site.json()["id"]

    # Localizar Drive
    drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    r_drives = requests.get(drives_url, headers=headers, timeout=15)
    r_drives.raise_for_status()

    drive_id = None
    target_names = ["Relatorios_Auditoria_Jogos", "Relatorios_de_Jogos", "Relatórios_de_Jogos"]
    for d in r_drives.json().get("value", []):
        if d.get("name") in target_names or "Relatorio" in d.get("name", ""):
            drive_id = d.get("id")
            break

    if not drive_id:
        print("ERRO: Biblioteca nao encontrada!")
        sys.exit(1)

    print(f"Drive ID: {drive_id}")

    # Listar todos os items com seus campos de metadados
    items_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children?$expand=listItem($expand=fields)&$top=100"
    r_items = requests.get(items_url, headers=headers, timeout=30)
    r_items.raise_for_status()
    items = r_items.json().get("value", [])

    return site_id, drive_id, items, headers

def delete_item(site_id, drive_id, item_id, headers):
    del_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/items/{item_id}"
    r = requests.delete(del_url, headers=headers, timeout=15)
    return r.status_code in (200, 204)

# =============================
# EXECUCAO
# =============================
print("=" * 65)
print("LIMPEZA DE DUPLICATAS - SHAREPOINT Relatorios_de_Jogos")
print("=" * 65)

site_id, drive_id, items, headers = get_all_items()

print(f"\nTotal de arquivos encontrados: {len(items)}\n")

# Mapear: chave = (partida_normalizada, data) -> lista de (modified_datetime, item_id, name)
from collections import defaultdict
groups = defaultdict(list)

for item in items:
    name = item.get("name", "")
    item_id = item.get("id", "")
    modified = item.get("lastModifiedDateTime", "1970-01-01T00:00:00Z")
    
    # Pegar metadados
    fields = {}
    li = item.get("listItem", {})
    if li:
        fields = li.get("fields", {})
    
    partida = fields.get("Partida", "") or ""
    data_hora = fields.get("Data_Partida", "") or ""
    
    # Chave de deduplicação: partida normalizada + data
    partida_norm = partida.strip().lower().replace(" ", "_")
    data_key = data_hora[:10] if data_hora else ""
    key = f"{partida_norm}__{data_key}"
    
    print(f"  [{modified[:16]}] {name}")
    print(f"    Partida={partida} | Data={data_hora[:10] if data_hora else '?'} | ID={item_id}")
    
    groups[key].append({
        "item_id": item_id,
        "name": name,
        "modified": modified,
        "partida": partida,
        "key": key
    })

print("\n" + "=" * 65)
print("ANALISE DE DUPLICATAS:")
print("=" * 65)

to_delete = []
to_keep = []

for key, group in groups.items():
    if len(group) == 1:
        to_keep.append(group[0])
        print(f"[UNICO] {group[0]['partida']} | {group[0]['name']}")
    else:
        # Ordenar por data de modificacao - mais recente primeiro
        group_sorted = sorted(group, key=lambda x: x["modified"], reverse=True)
        keep = group_sorted[0]
        delete_list = group_sorted[1:]
        
        to_keep.append(keep)
        print(f"\n[GRUPO DUPLICADO] Key: {key}")
        print(f"  MANTER: {keep['name']} ({keep['modified'][:16]})")
        for d in delete_list:
            to_delete.append(d)
            print(f"  DELETAR: {d['name']} ({d['modified'][:16]})")

# Deletar entradas com partida invalida ("Partida", "", etc.)
invalid_names = ["partida", "", "none", "n/a"]
for item_data in list(to_keep):
    partida_lower = item_data.get("partida", "").strip().lower()
    if partida_lower in invalid_names or not partida_lower:
        to_delete.append(item_data)
        to_keep.remove(item_data)
        print(f"\n[INVALIDO] Marcar para deletar: {item_data['name']} (Partida='{item_data['partida']}')")

print(f"\n{'=' * 65}")
print(f"RESUMO: {len(to_keep)} arquivos para manter | {len(to_delete)} para deletar")
print("=" * 65)

if not to_delete:
    print("Nenhuma duplicata encontrada!")
    sys.exit(0)

print("\nDeletando duplicatas...")
deleted_count = 0
failed_count = 0

for d in to_delete:
    ok = delete_item(site_id, drive_id, d["item_id"], headers)
    if ok:
        print(f"  [DELETADO] {d['name']}")
        deleted_count += 1
    else:
        print(f"  [FALHOU] {d['name']}")
        failed_count += 1

print(f"\nConcluido: {deleted_count} deletados | {failed_count} falhas")
