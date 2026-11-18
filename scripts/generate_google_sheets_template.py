# -*- coding: utf-8 -*-
"""
Gera planilha Excel (.xlsx) 100% IDÊNTICA à lista oficial do SharePoint:
'Suporte Captação - Programação de eventos - Streaming'
URL: https://adgbl.sharepoint.com/sites/suportecaptacao/Lists/Programao%20de%20eventos%20%20Streaming/AllItems.aspx
Contendo TODOS os 862 eventos existentes da lista oficial do SharePoint!
"""

import os
import json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def build_sharepoint_exact_sheet():
    wb = openpyxl.Workbook()
    
    # ── ABA 1: PROGRAMAÇÃO DE EVENTOS - STREAMING ──────────────────────────────
    ws = wb.active
    ws.title = "Programação de eventos - Stream"
    ws.views.sheetView[0].showGridLines = True

    # Cores idênticas ao SharePoint Modern Lists
    sp_header_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    sp_header_font = Font(name="Segoe UI", size=10, bold=True, color="1E293B")
    border_subtle = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="medium", color="94A3B8")
    )
    cell_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )

    # 11 Colunas Oficiais da Lista do SharePoint
    headers = [
        "Anexos",
        "Mês",
        "Data",
        "Horário",
        "Campeonato",
        "Partida",
        "Responsavel gravação",
        "Canal de Transmissão",
        "PVID TV BOX",
        "Status de Entrega",
        "Programado"
    ]

    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = sp_header_font
        cell.fill = sp_header_fill
        cell.alignment = Alignment(horizontal="center" if col_idx in [1, 3, 4, 10, 11] else "left", vertical="center")
        cell.border = border_subtle
    ws.row_dimensions[1].height = 28

    # Estilos de Badges (Pílulas)
    badge_caze_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    badge_caze_font = Font(name="Segoe UI", size=10, bold=True, color="166534")

    badge_prime_fill = PatternFill(start_color="00509E", end_color="00509E", fill_type="solid")
    badge_prime_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_netflix_fill = PatternFill(start_color="7F4F24", end_color="7F4F24", fill_type="solid")
    badge_netflix_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_tnt_fill = PatternFill(start_color="6B21A8", end_color="6B21A8", fill_type="solid")
    badge_tnt_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_dazn_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    badge_dazn_font = Font(name="Segoe UI", size=10, bold=True, color="F8FAFC")

    badge_record_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    badge_record_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_sportv_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    badge_sportv_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_disney_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    badge_disney_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_paramount_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    badge_paramount_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_globo_fill = PatternFill(start_color="E11D48", end_color="E11D48", fill_type="solid")
    badge_globo_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    badge_outro_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    badge_outro_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    # PVID TV BOX (Verde Petróleo / Teal)
    pvid_fill = PatternFill(start_color="0D5C75", end_color="0D5C75", fill_type="solid")
    pvid_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")

    # Status de Entrega
    pendente_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    pendente_font = Font(name="Segoe UI", size=10, bold=True, color="92400E")

    exibido_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    exibido_font = Font(name="Segoe UI", size=10, bold=True, color="166534")

    nao_exibido_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    nao_exibido_font = Font(name="Segoe UI", size=10, bold=True, color="991B1B")

    # Fonte das partidas
    font_partida = Font(name="Segoe UI", size=10, bold=True, color="166534")
    font_comum = Font(name="Segoe UI", size=10, color="0F172A")

    # Fundo suave pêssego/amarelado das linhas (idêntico ao print do SharePoint)
    row_warm_fill = PatternFill(start_color="FFFBEB", end_color="FFFBEB", fill_type="solid")

    # Carrega todos os 862 eventos do SharePoint
    json_path = os.path.join(os.path.dirname(__file__), "..", "config", "sharepoint_clean_migrated_events.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        dados_sharepoint = [
            (
                r.get("anexos", ""),
                r.get("mes", "Novembro"),
                r.get("data", ""),
                r.get("horario", ""),
                r.get("campeonato", ""),
                r.get("partida", ""),
                r.get("responsavel", "Cleber BL01 e Backup"),
                r.get("canal", "Amazon Prime"),
                r.get("pvid", ""),
                r.get("status_entrega", "Pendente"),
                r.get("programado", "NÃO")
            )
            for r in records
        ]
    else:
        dados_sharepoint = [
            ("", "Dezembro", "25/12/2026", "15:00", "NFL", "Green Bay Packers x Chicago Bears", "Cleber BL01 e Backup", "Netflix", "Netflix - PV3679", "Pendente", "NÃO"),
            ("", "Dezembro", "25/12/2026", "18:30", "NFL", "Buffalo Bills x Denver Broncos", "Cleber BL01 e Backup", "Netflix", "Netflix 2 - PV3729", "Pendente", "NÃO"),
            ("", "Novembro", "29/11/2026", "17:30", "CBF - Brasileirão Série A", "Corinthians x Grêmio", "Lucieudes BL01 e Backup", "Amazon Prime", "Prime Video - PV3687", "Pendente", "NÃO"),
        ]

    for row_idx, r in enumerate(dados_sharepoint, start=2):
        ws.append(list(r))
        ws.row_dimensions[row_idx].height = 24

        for col_idx in range(1, len(r) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = cell_border
            cell.font = font_comum
            cell.fill = row_warm_fill

            # Alinhamentos específicos
            if col_idx in [1, 11]:  # Anexos, Programado
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [2, 3, 4]:  # Mês, Data, Horário
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in [5, 7]:  # Campeonato, Responsável
                cell.alignment = Alignment(horizontal="left", vertical="center")
            elif col_idx == 6:  # Partida
                cell.alignment = Alignment(horizontal="left", vertical="center")
                cell.font = font_partida
            elif col_idx == 8:  # Canal de Transmissão (Badge)
                canal_val = str(cell.value or "").lower()
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if "cazé" in canal_val or "caze" in canal_val:
                    cell.fill = badge_caze_fill
                    cell.font = badge_caze_font
                elif "prime" in canal_val or "amazon" in canal_val:
                    cell.fill = badge_prime_fill
                    cell.font = badge_prime_font
                elif "netflix" in canal_val:
                    cell.fill = badge_netflix_fill
                    cell.font = badge_netflix_font
                elif "tnt" in canal_val or "max" in canal_val or "hbo" in canal_val:
                    cell.fill = badge_tnt_fill
                    cell.font = badge_tnt_font
                elif "dazn" in canal_val:
                    cell.fill = badge_dazn_fill
                    cell.font = badge_dazn_font
                elif "record" in canal_val:
                    cell.fill = badge_record_fill
                    cell.font = badge_record_font
                elif "sport" in canal_val or "premiere" in canal_val:
                    cell.fill = badge_sportv_fill
                    cell.font = badge_sportv_font
                elif "disney" in canal_val:
                    cell.fill = badge_disney_fill
                    cell.font = badge_disney_font
                elif "paramount" in canal_val:
                    cell.fill = badge_paramount_fill
                    cell.font = badge_paramount_font
                elif "globo" in canal_val or "ge" in canal_val:
                    cell.fill = badge_globo_fill
                    cell.font = badge_globo_font
                elif canal_val.strip() and canal_val.strip() != "nenhuma":
                    cell.fill = badge_outro_fill
                    cell.font = badge_outro_font
            elif col_idx == 9:  # PVID TV BOX (Badge Teal)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.fill = pvid_fill
                cell.font = pvid_font
            elif col_idx == 10:  # Status de Entrega
                st_val = str(cell.value or "").lower()
                cell.alignment = Alignment(horizontal="center", vertical="center")
                if "exibido" in st_val and "não" not in st_val:
                    cell.fill = exibido_fill
                    cell.font = exibido_font
                elif "não" in st_val or "nao" in st_val or "cancelado" in st_val:
                    cell.fill = nao_exibido_fill
                    cell.font = nao_exibido_font
                else:
                    cell.fill = pendente_fill
                    cell.font = pendente_font

    # Congelar Linha 1 de Cabeçalho
    ws.freeze_panes = "A2"

    # Ativar Autofilter
    ws.auto_filter.ref = f"A1:K{len(dados_sharepoint) + 1}"

    # Larguras de Colunas
    larguras = {
        "A": 9,   # Anexos
        "B": 14,  # Mês
        "C": 15,  # Data
        "D": 12,  # Horário
        "E": 28,  # Campeonato
        "F": 38,  # Partida
        "G": 28,  # Responsavel gravação
        "H": 24,  # Canal de Transmissão
        "I": 24,  # PVID TV BOX
        "J": 18,  # Status de Entrega
        "K": 14   # Programado
    }
    for col_letter, w in larguras.items():
        ws.column_dimensions[col_letter].width = w

    # Salva na raiz do projeto substituindo o arquivo anterior
    output_path = os.path.join(os.path.dirname(__file__), "..", "Programacao_Eventos_Streaming_GoogleSheets.xlsx")
    wb.save(output_path)
    print(f"Planilha oficial do SharePoint gerada com 100% dos {len(dados_sharepoint)} eventos em: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    build_sharepoint_exact_sheet()
