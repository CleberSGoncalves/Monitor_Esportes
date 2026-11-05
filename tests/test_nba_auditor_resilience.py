"""
tests/test_nba_auditor_resilience.py
Validação automatizada da blindagem do auditor NBA contra relatórios sem frames e governança de comprovação visual.
"""
import os
import sys
import unittest
import tempfile
from unittest.mock import MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_autonomous_auditor import NBAAutonomousAuditor
from modules.nba_visual_proof_service import select_official_video, stamp_nba_audit_banner
from PIL import Image

class TestNBAAuditorResilience(unittest.TestCase):
    def setUp(self):
        self.auditor = NBAAutonomousAuditor()
        self.auditor._audited_cache = {}

    def test_is_game_audited_rejects_missing_or_small_pdf(self):
        # 1. Entrada sem pdf_path
        self.auditor._audited_cache["101"] = {
            "audited": True,
            "pdf_path": "",
            "sp_synced": True
        }
        self.assertFalse(self.auditor.is_game_audited("101"), "Não deve considerar auditado sem PDF")

        # 2. Entrada com PDF pequeno (< 500 KB)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"PDF dummy content" * 100)
            small_pdf = f.name

        try:
            self.auditor._audited_cache["102"] = {
                "audited": True,
                "pdf_path": small_pdf,
                "sp_synced": True
            }
            self.assertFalse(self.auditor.is_game_audited("102"), "Não deve considerar auditado PDF < 500 KB")
        finally:
            if os.path.exists(small_pdf):
                os.remove(small_pdf)

    def test_is_game_audited_accepts_complete_pdf(self):
        # Cria arquivo simulado >= 500 KB
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"X" * 600_000)
            large_pdf = f.name

        try:
            self.auditor._audited_cache["103"] = {
                "audited": True,
                "has_visual_proofs": True,
                "pdf_path": large_pdf,
                "sp_synced": True
            }
            self.assertTrue(self.auditor.is_game_audited("103"), "Deve considerar auditado quando PDF >= 500 KB")
        finally:
            if os.path.exists(large_pdf):
                os.remove(large_pdf)

    def test_select_official_video_filter(self):
        candidates = [
            # Candidato de terceiro (deve rejeitar)
            {"title": "76ERS at PISTONS | FULL GAME HIGHLIGHTS | November 4, 2026", "uploader": "FanChannel", "duration": 900},
            # Candidato oficial mas sem Full Game Highlights (deve rejeitar)
            {"title": "Top 10 Plays | November 4, 2026", "uploader": "NBA", "duration": 300},
            # Candidato oficial perfeito
            {"id": "b3qMlYMESBY", "title": "76ERS at PISTONS | FULL GAME HIGHLIGHTS | November 4, 2026", "uploader": "NBA", "duration": 939}
        ]
        best = select_official_video(candidates, "Philadelphia 76ers", "Detroit Pistons", date_clean="20261104")
        self.assertIsNotNone(best)
        self.assertEqual(best["id"], "b3qMlYMESBY")

    def test_stamp_banner(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f_in, \
             tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f_out:
            img = Image.new("RGB", (640, 360), color=(50, 50, 50))
            img.save(f_in.name, "JPEG")
            in_path = f_in.name
            out_path = f_out.name

        try:
            stamped = stamp_nba_audit_banner(
                in_path,
                out_path,
                praca="SPO",
                channel_code="NBA",
                timestamp_brt_str="04/11/2026 21:13:00",
                extend_top=False
            )
            self.assertTrue(os.path.exists(stamped))
            self.assertGreater(os.path.getsize(stamped), 1000)
        finally:
            for p in (in_path, out_path):
                if os.path.exists(p):
                    os.remove(p)

    def test_streaming_audit_anchors_strictly_to_gamebook_milestones(self):
        from modules.nba_report_generator import NBAReportGenerator
        import pdfplumber

        game = {
            "id": "999001",
            "away_team": "Dallas Mavericks",
            "home_team": "San Antonio Spurs",
            "away_tri": "DAL",
            "home_tri": "SAS",
            "date_clean": "20261104",
            "date_display": "04/11/2026",
            "time_brt": "23:30",
            "platform": "Disney",
            "platforms": ["NBA League Pass", "Disney", "ESPN"],
            "score_display": "111 - 112"
        }

        parsed = {
            "game_duration": "2:38",
            "attendance": "18354",
            "arena": "Frost Bank Center, San Antonio, TX",
            "officials": ["#74 Curtis Blair"],
            "score_by_period": {},
            "milestones": [
                {"type": "start", "period": "1º Quarto", "time_brt": "23:48:00"},
                {"type": "end", "period": "1º Quarto", "time_brt": "00:19:00"},
                {"type": "start", "period": "2º Quarto", "time_brt": "00:22:00"},
                {"type": "end", "period": "2º Quarto", "time_brt": "00:59:00"},
                {"type": "start", "period": "3º Quarto", "time_brt": "01:16:00"},
                {"type": "end", "period": "3º Quarto", "time_brt": "01:52:00"},
                {"type": "start", "period": "4º Quarto", "time_brt": "01:55:00"},
                {"type": "end", "period": "4º Quarto", "time_brt": "02:26:00"}
            ]
        }

        pdf = NBAReportGenerator.generate_report(game, parsed, auto_generate_proofs=False)
        self.assertTrue(os.path.exists(pdf))

        try:
            with pdfplumber.open(pdf) as p:
                text = "\n".join(page.extract_text() or "" for page in p.pages)

            # Validar que a bola ao alto na transmissão está rigorosamente ancorada ao Game Book (23:48:00)
            self.assertIn("23:48:00", text)
            self.assertIn("Jump Ball (Ao Vivo)", text)

            # Validar que o intervalo da transmissão bate rigorosamente com o Halftime (00:59:00 a 01:16:00)
            self.assertIn("00:59:00", text)
            self.assertIn("01:16:00", text)
            self.assertIn("Halftime / Intervalo", text)

            # Validar que o pós-jogo é após o apito final (02:26:00), e NÃO às 02:00 antes do jogo acabar!
            self.assertIn("02:26:00", text)
            self.assertIn("Pós-Jogo / Encerramento", text)

            # Validar que o bloco oficial de Grounding e Cobertura Esportiva está presente
            self.assertIn("Confirmação Oficial de Horários na Transmissão & Cobertura Esportiva", text)
            self.assertIn("Grade Divulgada de Transmissão", text)

            # Garantir que estimativas sintéticas antigas e divergentes não aparecem na tabela de streaming
            self.assertNotIn("Jump Ball transmitida às 23:30", text)
            self.assertNotIn("02:00:00 Pós-Jogo", text)
        finally:
            if os.path.exists(pdf):
                os.remove(pdf)

    def test_nba_streaming_grounding_service(self):
        from modules.nba_streaming_grounding import NBAStreamingGroundingService
        res = NBAStreamingGroundingService.get_grounding_audit(
            away_team="Dallas Mavericks",
            home_team="San Antonio Spurs",
            date_str="04/11/2026",
            date_clean="20261104",
            scheduled_time_brt="23:30"
        )
        self.assertTrue(res.get("verified"), "Grounding deve certificar a transmissão")
        self.assertIn("23:30", str(res.get("broadcast_schedule_time_brt")), "Grade divulgada deve ser 23:30")
        self.assertGreater(len(res.get("reference_urls", [])), 0, "Deve conter URLs de referência")

if __name__ == "__main__":
    unittest.main()
