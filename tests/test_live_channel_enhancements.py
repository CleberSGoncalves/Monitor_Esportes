# tests/test_live_channel_enhancements.py
import os
import sys
sys.path.insert(0, os.getcwd())
import unittest
from modules.narration_chronology import guess_match_from_title, is_definitely_non_match

class TestLiveChannelEnhancements(unittest.TestCase):
    def test_guess_match_from_title_various_formats(self):
        # 1. Standard with X
        res1 = guess_match_from_title("AO VIVO: GRÊMIO x ATLETICO-MG | COPA DO BRASIL | JORNADA DIGITAL | 01/11/2026")
        self.assertEqual(res1["team1"].upper(), "GRÊMIO")
        self.assertIn("ATL", res1["team2"].upper())
        self.assertIn("COPA", res1["competition"].upper())

        # 2. Score embedded in title
        res2 = guess_match_from_title("JORNADA ESPORTIVA | GRÊMIO 2X0 ATLÉTICO-MG | JOGO DE IDA | SEMIFINAL | COPA DO BRASIL (01/11/2026)")
        self.assertEqual(res2["team1"].upper(), "GRÊMIO")
        self.assertIn("ATL", res2["team2"].upper())
        self.assertEqual(res2["score"], "2 x 0")
        self.assertIn("COPA", res2["competition"].upper())

        # 3. Emojis and brackets
        res3 = guess_match_from_title("🔵 AO VIVO 🔵 JORNADA DO BAGÉ 🔵 GRÊMIO X ATLÉTICO-MG [DIRETO DA ARENA DO GRÊMIO]")
        self.assertIn("GRÊMIO", res3["team1"].upper())
        self.assertIn("ATL", res3["team2"].upper())

        # 4. Standard Brasileirão match
        res4 = guess_match_from_title("AO VIVO: FLUMINENSE X INTER | BRASILEIRÃO 2026 | JORNADA DIGITAL")
        self.assertIn("FLUMINENSE", res4["team1"].upper())
        self.assertIn("INTER", res4["team2"].upper())
        self.assertIn("BRASILEIR", res4["competition"].upper())

    def test_non_match_detection(self):
        # Debates and programs must be detected as non-matches
        is_non, _ = is_definitely_non_match("SALA DE REDAÇÃO - DEBATE PÓS-JOGO")
        self.assertTrue(is_non)

        is_non, _ = is_definitely_non_match("BOM DIA GRÊMIO - NOTÍCIAS DO TRICOLOR")
        self.assertTrue(is_non)

        # Real match title should not be dismissed
        is_non, _ = is_definitely_non_match("AO VIVO: GRÊMIO x ATLETICO-MG | COPA DO BRASIL")
        self.assertFalse(is_non)

if __name__ == "__main__":
    unittest.main()
