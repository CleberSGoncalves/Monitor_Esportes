import json

d = json.load(open('config/sharepoint_real_lists_data.json', encoding='utf-8'))
print(f"TOTAL LISTAS MAPEADAS: {d['total_lists']}")
print("=" * 70)
for k, v in sorted(d['summary'].items()):
    hidden_str = " [HIDDEN]" if v.get('hidden') else ""
    print(f"- {k:<42} | {v['items_count']:>4} itens | {v['columns_count']:>2} colunas{hidden_str}")
