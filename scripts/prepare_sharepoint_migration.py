import json
import re
from datetime import datetime

with open('config/sharepoint_all_items_dump.json', encoding='utf-8') as f:
    items = json.load(f)

print(f"Total raw items: {len(items)}")

months_pt = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

def format_date_br(d_str):
    if not d_str:
        return ""
    # "2024-01-12T08:00:00Z" -> "12/01/2024"
    d_clean = str(d_str)[:10]
    parts = d_clean.split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return d_str

def get_month_name(d_str, mes_orig=None):
    if mes_orig and isinstance(mes_orig, str) and mes_orig.strip():
        return mes_orig.strip()
    if d_str:
        parts = str(d_str)[:10].split("-")
        if len(parts) == 3:
            try:
                m_idx = int(parts[1]) - 1
                if 0 <= m_idx < 12:
                    return months_pt[m_idx]
            except Exception:
                pass
    return "Novembro"

def map_pvid(canal, pvid_orig=None):
    if pvid_orig and isinstance(pvid_orig, str) and pvid_orig.strip():
        return pvid_orig.strip()
    c = str(canal).lower()
    if "cazé" in c or "caze" in c:
        return "CAZETV - PV3623"
    elif "prime" in c or "amazon" in c:
        return "Prime Video - PV3687"
    elif "netflix" in c:
        return "Netflix - PV3679"
    elif "sportv" in c:
        return "SporTV - PV3101"
    elif "premiere" in c:
        return "Premiere - PV3102"
    elif "tnt" in c:
        return "TNT - 316"
    return f"{canal} - PVBOX"

clean_records = []
for it in items:
    f = it.get('fields', {})
    
    # 1. Anexos
    anexos = ""
    
    # 2. Mês & 3. Data
    data_raw = f.get('Data', '')
    data_br = format_date_br(data_raw)
    mes = get_month_name(data_raw, f.get('M_x00ea_s'))
    
    # 4. Horário
    horario = str(f.get('Hor_x00e1_rio', '')).strip()
    
    # 5. Campeonato
    campeonato = str(f.get('Title', '')).strip()
    
    # 6. Partida
    partida = str(f.get('Partida', '')).strip()
    if not partida:
        continue # skip empty rows
        
    # 7. Responsavel gravação
    resp = f.get('BKP_x0020__x0028_Uso_x0020_Supor') or "Cleber BL01 e Backup"
    if isinstance(resp, list):
        resp = ", ".join(resp)
        
    # 8. Canal de Transmissão
    canais_raw = f.get('Transmiss_x00e3_o', [])
    if isinstance(canais_raw, list):
        canal = ", ".join(canais_raw) if canais_raw else "Amazon Prime"
    else:
        canal = str(canais_raw) if canais_raw else "Amazon Prime"
        
    # 9. PVID TV BOX
    pvid = map_pvid(canal, f.get('PVID'))
    
    # 10. Status de Entrega
    status = f.get('StatusdeEntrega') or "Pendente"
    
    # 11. Programado
    prog = f.get('Programado_x0020_TV_x0020_BOX_x0') or f.get('Programado_x0020_ATRIA_x0020_Pri') or "NÃO"
    
    clean_records.append({
        "id_sharepoint": it.get('id'),
        "anexos": anexos,
        "mes": mes,
        "data": data_br,
        "horario": horario,
        "campeonato": campeonato,
        "partida": partida,
        "responsavel": resp,
        "canal": canal,
        "pvid": pvid,
        "status_entrega": status,
        "programado": prog,
        "_sort_key": f"{str(data_raw)[:10]}_{horario}"
    })

# Sort chronologically by date and time
clean_records.sort(key=lambda x: x['_sort_key'])

print(f"Total clean records prepared: {len(clean_records)}")
print("\nSample first 3 (oldest):")
for r in clean_records[:3]:
    print(r)

print("\nSample last 3 (newest):")
for r in clean_records[-3:]:
    print(r)

with open('config/sharepoint_clean_migrated_events.json', 'w', encoding='utf-8') as f_out:
    json.dump(clean_records, f_out, ensure_ascii=False, indent=2)

print("\nSaved to config/sharepoint_clean_migrated_events.json")
