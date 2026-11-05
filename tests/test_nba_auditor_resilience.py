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

if __name__ == "__main__":
    unittest.main()
