# -*- coding: utf-8 -*-
"""
Sincronizador Automático da Planilha Oficial 'Escala de trabalho 2026.xlsx'
Baixa a versão mais recente do SharePoint (se houver conexão) ou lê a planilha local,
converte todas as abas de meses para config/escala_completa_2026.json
e recompila o portal para que as edições reflitam instantaneamente na visualização.
"""

import os
import sys
import json
import logging
import openpyxl
from datetime import datetime

logger = logging.getLogger(__name__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro_Prototipo", "Plantao_Fim_Ano"
]

def sync_from_sharepoint_if_possible(excel_path: str):
    try:
        sys.path.insert(0, PROJECT_ROOT)
        from modules.sharepoint_reporter import SharePointReporter
        import requests
        token = SharePointReporter.obter_token_graph()
        if not token:
            return
        headers = {"Authorization": f"Bearer {token}"}
        drive_id = "b!R5fko7abk0yZMN2ibI0QUFX-yDT-LPxOjOApWP13XuBSDMK_ees4RrJJcQIBJdUN"
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/Escala%20de%20trabalho%202026.xlsx:/content"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            with open(excel_path, "wb") as f:
                f.write(r.content)
            print(f"📥 Planilha mais recente baixada do SharePoint com sucesso! ({len(r.content)} bytes)")
    except Exception as e:
        print(f"ℹ️ Usando planilha local existente: {e}")

def parse_escala_excel(excel_path: str, output_json: str):
    if not os.path.exists(excel_path):
        print(f"Planilha não encontrada: {excel_path}")
        return False

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    escala_data = {}

    for sheet_name in wb.sheetnames:
        clean_name = sheet_name.strip()
        matched_month = None
        for m in MONTH_NAMES:
            if m.lower() in clean_name.lower():
                matched_month = m
                break
        if not matched_month and "natal" in clean_name.lower():
            matched_month = "Plantao_Fim_Ano"
        if not matched_month:
            continue

        ws = wb[sheet_name]
        operadores = []
        num_dias = 31
        if matched_month in ["Fevereiro"]:
            num_dias = 28
        elif matched_month in ["Abril", "Junho", "Setembro", "Novembro"]:
            num_dias = 30

        # Encontrar linha de cabeçalho (dias 1..31)
        header_row_idx = None
        day_col_map = {} # day_int -> col_idx

        for r_idx in range(1, 15):
            row_vals = [ws.cell(r_idx, c).value for c in range(1, 45)]
            days_found = []
            for c_idx, val in enumerate(row_vals, 1):
                try:
                    v_int = int(str(val).strip())
                    if 1 <= v_int <= 31:
                        days_found.append((v_int, c_idx))
                except (ValueError, TypeError):
                    pass
            if len(days_found) >= 20:
                header_row_idx = r_idx
                for d_num, col_idx in days_found:
                    day_col_map[d_num] = col_idx
                num_dias = max(d[0] for d in days_found)
                break

        if not header_row_idx:
            continue

        # Ler operadores abaixo do cabeçalho
        for r_idx in range(header_row_idx + 1, header_row_idx + 35):
            nome = ws.cell(r_idx, 1).value or ws.cell(r_idx, 2).value
            if not nome or str(nome).strip().lower() in ["nome", "operador", "total", "legenda"]:
                continue
            nome_str = str(nome).strip()
            if len(nome_str) < 3:
                continue

            mat = str(ws.cell(r_idx, 2).value or "").strip()
            horario = str(ws.cell(r_idx, 3).value or "").strip()
            equipe = str(ws.cell(r_idx, 4).value or "").strip()
            if not equipe or equipe == "None":
                equipe = "Monitoração" if "06:" in horario or "10:" in horario or "14:" in horario or "22:" in horario else "Captação"

            dias = {}
            for d in range(1, num_dias + 1):
                col = day_col_map.get(d)
                if col:
                    val = ws.cell(r_idx, col).value
                    val_str = str(val).strip().upper() if val is not None else ""
                    if val_str and val_str != "NONE":
                        dias[str(d)] = val_str

            operadores.append({
                "nome": nome_str,
                "matricula": mat if mat != "None" else "",
                "horario": horario if horario != "None" else "08:00 - 17:00",
                "equipe": equipe,
                "dias": dias
            })

        if operadores:
            escala_data[matched_month] = {
                "num_dias": num_dias,
                "operadores": operadores,
                "atividades": []
            }

    if escala_data:
        # Preservar meses existentes se a planilha não continha todos
        if os.path.exists(output_json):
            try:
                with open(output_json, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                for k, v in old_data.items():
                    if k not in escala_data:
                        escala_data[k] = v
            except Exception:
                pass

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(escala_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Escala sincronizada com sucesso para {output_json} ({len(escala_data)} meses mapeados)!")
        return True
    return False

def main():
    excel_path = os.path.join(PROJECT_ROOT, "config", "Escala de trabalho 2026.xlsx")
    json_path = os.path.join(PROJECT_ROOT, "config", "escala_completa_2026.json")
    sync_from_sharepoint_if_possible(excel_path)
    if parse_escala_excel(excel_path, json_path):
        from scripts.build_portal_web import generate_portal
        generate_portal()
        print("🚀 Portal Web recompilado com os dados atualizados da Escala!")

if __name__ == "__main__":
    main()
