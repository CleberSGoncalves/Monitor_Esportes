import json

d = json.load(open('config/sharepoint_real_drives_data.json', encoding='utf-8'))
for drv in d['drives']:
    name = drv['name']
    if name in ['Procedimentos', 'Metas', 'Ficha de Capacitação', 'Controle de contratos parceiros', 'Documentos Técnicos', 'Relatorios_de_Jogos_NBA', 'Relatorio Jogos Youtube']:
        print(f"\n==========================================")
        print(f"DRIVE: {name} ({len(drv['items'])} items)")
        print(f"==========================================")
        for itm in drv['items'][:15]:
            itype = itm.get('type')
            ext = itm.get('extension') or ('DIR' if itype == 'folder' else '')
            size = itm.get('size', 0)
            size_kb = f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB"
            mod = itm.get('lastModifiedDateTime', '')[:10]
            by = itm.get('lastModifiedBy', '')
            print(f"  [{ext:5}] {itm.get('name'):<45} | {size_kb:>8} | {mod} | {by}")
            if itype == 'folder' and itm.get('children'):
                for ch in itm['children'][:5]:
                    ch_ext = ch.get('extension') or ('DIR' if ch.get('type') == 'folder' else '')
                    print(f"       -> [{ch_ext:5}] {ch.get('name')}")
