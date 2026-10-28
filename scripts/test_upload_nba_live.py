import sys, os
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_nba_reporter import SharePointNBAReporter

pdf_path = r"e:\desenvolvimento\Monitor_Esportes\reports\expert_nba_outro_bkn_at_bos_20261027.pdf"
game_test = {
    "match_display": "Brooklyn Nets @ Boston Celtics",
    "platform": "Amazon Prime",
    "iso_utc": "2026-10-27T23:30:00Z",
    "score": "BKN 116 x 120 BOS",
    "away_team": "BKN",
    "home_team": "BOS",
    "away_score": "116",
    "home_score": "120"
}

print(f"Testando upload de {pdf_path} para Relatorios_de_Jogos_NBA...")
success = SharePointNBAReporter.sync_nba_report(pdf_path, game_test)
print("Resultado da Sincronização:", success)
