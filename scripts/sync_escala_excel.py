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
            print(f"📥 Planilha mais recente baixada com sucesso! ({len(r.content)} bytes)")
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
        atividades = []

        # Encontrar linha de cabeçalho dos dias 1..31
        header_row_idx = None
        day_col_map = {} # day_int -> col_idx

        for r_idx in range(1, 15):
            days_found = []
            for c_idx in range(1, 45):
                val = ws.cell(r_idx, c_idx).value
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
                break

        if not header_row_idx:
            continue

        num_dias = max(day_col_map.keys())
        current_equipe = "Monitoração"

        # Ler operadores e atividades abaixo do cabeçalho
        for r_idx in range(header_row_idx + 1, ws.max_row + 1):
            c1 = str(ws.cell(r_idx, 1).value or "").strip()
            c2 = str(ws.cell(r_idx, 2).value or "").strip()
            c3 = str(ws.cell(r_idx, 3).value or "").strip()
            c4 = str(ws.cell(r_idx, 4).value or "").strip()

            all_row_text = f"{c1} {c2} {c3} {c4}".lower()

            # Detecção de Grupo / Equipe
            if "captação" in all_row_text or "captacao" in all_row_text:
                current_equipe = "Captação"
            elif "monitoração" in all_row_text or "monitoracao" in all_row_text:
                current_equipe = "Monitoração"

            # Pular linhas de cabeçalho repetidas
            if c2.lower() == "matricula" or c3.lower() == "matricula" or "escala de trabalho" in all_row_text:
                continue

            # Detecção de Atividades Operacionais (Chamados, Incidentes, SobreAviso)
            if c2.lower().startswith("atividade") or c1.lower().startswith("atividade"):
                ativ_nome = c2 if c2.lower().startswith("atividade") else c1
                dias_ativ = {}
                for d, col in day_col_map.items():
                    val = ws.cell(r_idx, col).value
                    if val is not None and str(val).strip().upper() not in ["NONE", ""]:
                        dias_ativ[str(d)] = str(val).strip()
                atividades.append({
                    "nome": ativ_nome,
                    "dias": dias_ativ
                })
                continue

            # Mapeamento dinâmico e cirúrgico dos campos do operador
            nome = ""
            matricula = ""
            horario = ""

            if c2.isdigit():
                # Formato Outubro/Novembro/Dezembro: c2=Matrícula, c3=Horário, c4=Nome
                matricula = c2
                horario = c3
                nome = c4
            elif ":" in c2:
                # Formato Janeiro-Setembro: c2=Horário, c3=Nome
                horario = c2
                nome = c3
            elif ":" in c3:
                horario = c3
                nome = c4

            if not nome or nome.lower() in ["none", "nome", "horário", ""]:
                continue

            dias = {}
            for d, col in day_col_map.items():
                val = ws.cell(r_idx, col).value
                if val is not None and str(val).strip().upper() not in ["NONE", ""]:
                    dias[str(d)] = str(val).strip().upper()

            operadores.append({
                "nome": nome.strip(),
                "matricula": matricula.strip(),
                "horario": horario.strip() if horario else "08:00 - 17:00",
                "equipe": current_equipe,
                "dias": dias
            })

        if operadores:
            escala_data[matched_month] = {
                "num_dias": num_dias,
                "operadores": operadores,
                "atividades": atividades
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
    if not os.path.exists(excel_path):
        excel_path = os.path.join(PROJECT_ROOT, "docs", "Escala_de_trabalho_2026.xlsx")
    json_path = os.path.join(PROJECT_ROOT, "config", "escala_completa_2026.json")
    sync_from_sharepoint_if_possible(excel_path)
    if parse_escala_excel(excel_path, json_path):
        from scripts.build_portal_web import generate_portal
        generate_portal()
        print("🚀 Portal Web recompilado com os dados atualizados da Escala!")

if __name__ == "__main__":
    main()

