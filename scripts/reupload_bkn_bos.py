import os, sys
sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_nba_reporter import SharePointNBAReporter

game = {
    "away_team": "Brooklyn Nets", "home_team": "Boston Celtics",
    "away_tri": "BKN", "home_tri": "BOS",
    "match_display": "Brooklyn Nets @ Boston Celtics",
    "date_clean": "20261027", "date_display": "27/10/2026",
    "time_brt": "20:40", "platform": "NBA League Pass",
    "score_display": "Finalizado", "is_finished": True,
}
pdf = os.path.join(PROJECT_ROOT, "reports", "expert_nba_nba_league_pass_bkn_at_bos_20261027.pdf")
print("PDF local:", os.path.getsize(pdf), "bytes")
print("Upload BKN@BOS:", SharePointNBAReporter.sync_nba_report(pdf, game))
