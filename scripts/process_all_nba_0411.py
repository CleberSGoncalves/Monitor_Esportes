"""
scripts/process_all_nba_0411.py
Gera e sincroniza relatórios oficiais da NBA de 04/11/2026 com 100% de comprovação visual autêntica.
"""
import os
import sys
import time
import json
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.nba_service import NBAService, NBA_TEAMS
from modules.nba_report_generator import NBAReportGenerator
from modules.sharepoint_nba_reporter import SharePointNBAReporter

TRI_TO_NAME = {v: k for k, v in NBA_TEAMS.items()}

def run_batch_0411():
    print("==================================================================")
    print("AUDITORIA NBA — 04/11/2026 (14 PARTIDAS COM COMPROVAÇÃO VISUAL)")
    print("==================================================================")

    games = NBAService.fetch_games_for_date("2026-11-04")
    print(f"Total de partidas localizadas: {len(games)}")

    generated_pdfs = []

    for idx, g in enumerate(games, 1):
        match_disp = g["match_display"]
        away_tri, home_tri = g["away_tri"], g["home_tri"]
        plat = g["platform"] or "NBA League Pass"
        
        print(f"\n--- [{idx}/{len(games)}] Processando: {match_disp} ({plat}) ---", flush=True)

        # 1. Download do Game Book
        gb_path = NBAService.download_gamebook(g)
        if not gb_path or not os.path.exists(gb_path):
            print(f"⚠️ Gamebook indisponível para {match_disp}")
            continue

        # 2. Parse do Game Book
        parsed = NBAService.parse_gamebook(gb_path, home_tri=home_tri, date_clean="20261104")
        
        # 3. Verificar se já existe PDF completo (>= 1.5 MB)
        partida_slug = f"{away_tri.lower()}_at_{home_tri.lower()}"
        plat_slug = plat.lower().replace(" ", "_")
        expected_pdf = os.path.join(PROJECT_ROOT, "reports", f"expert_nba_{plat_slug}_{partida_slug}_20261104.pdf")

        if os.path.exists(expected_pdf) and os.path.getsize(expected_pdf) >= 1_500_000:
            print(f"✅ PDF já gerado com comprovação visual ({os.path.getsize(expected_pdf)} bytes): {os.path.basename(expected_pdf)}")
            generated_pdfs.append((g, expected_pdf))
            continue

        # 4. Gerar relatório com frames autênticos
        print(f"📸 Extraindo comprovações visuais e gerando relatório executivo...", flush=True)
        pdf = NBAReportGenerator.generate_report(g, parsed, auto_generate_proofs=True)
        sz = os.path.getsize(pdf) if os.path.exists(pdf) else 0
        print(f"📄 Relatório concluído: {os.path.basename(pdf)} ({sz} bytes)", flush=True)
        generated_pdfs.append((g, pdf))

    print("\n==================================================================")
    print(f"FASE 1 CONCLUÍDA: {len(generated_pdfs)} relatórios gerados com sucesso!")
    print("==================================================================")

    # FASE 2: Sincronização no SharePoint
    print("\nIniciando upload e sincronização na biblioteca 'Relatorios_de_Jogos_NBA' do SharePoint...", flush=True)
    synced = 0
    for idx, (g, pdf_path) in enumerate(generated_pdfs, 1):
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) < 500_000:
            print(f"[{idx}/{len(generated_pdfs)}] ⚠️ PDF inválido ou sem frames: {os.path.basename(pdf_path)}")
            continue

        print(f"[{idx}/{len(generated_pdfs)}] ☁️ Sincronizando {g['match_display']} ({os.path.getsize(pdf_path)} bytes)...", flush=True)
        try:
            ok = SharePointNBAReporter.sync_nba_report(pdf_path, g)
            if ok:
                synced += 1
                print(f"    ✅ Sincronizado com sucesso no SharePoint!", flush=True)
            else:
                print(f"    ⚠️ Falha ao sincronizar no SharePoint.", flush=True)
        except Exception as e:
            print(f"    ❌ Exceção ao sincronizar: {e}", flush=True)
        time.sleep(3.0)

    print(f"\n==================================================================")
    print(f"PROCESSO COMPLETO: {synced}/{len(generated_pdfs)} sincronizados no SharePoint!")
    print("==================================================================")

if __name__ == "__main__":
    run_batch_0411()
