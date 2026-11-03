import os
import sys
import unittest
import pypdfium2

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.expert_assistant import ExpertAssistant
from modules.cbf_schedule_fetcher import CBFScheduleFetcher

class TestSumulaAndSchedulerResilience(unittest.TestCase):

    def test_team_map_normalization(self):
        """Valida que slugs com variações como atletico-mg mapeiam corretamente para os links da CBF."""
        slug_mg = "atletico-mg"
        from modules.cbf_schedule_fetcher import load_broadcaster_rules
        # Testa a disponibilidade do link oficial de Grêmio x Atlético-MG
        ea = ExpertAssistant(api_key="dummy")
        is_avail = ea.is_cbf_sumula_available("Grêmio", "Atlético-MG", "01/11/2026", "Copa do Brasil")
        self.assertTrue(is_avail, "Súmula oficial de Grêmio x Atlético-MG deve ser detectada como disponível no site da CBF.")

    def test_deterministic_sumula_parsing_gremio(self):
        """Valida o parser determinístico da súmula de Grêmio x Atlético-MG sem tocar na API do Gemini."""
        sample_sumula = """
        Início 1º Tempo: 18:30 Término 1º Tempo: 19:20 Acréscimo: 5 min
        Início 2º Tempo: 19:38 Término 2º Tempo: 20:29 Acréscimo: 6 min
        Resultado Final: 2 X 0
        Gols
        Tempo 1T/2T Nº Tipo Nome do Jogador Equipe
        10:00 1T 95 NR Carlos Vinicius Alves Morais Grêmio/RS
        01:00 2T 8 NR Erick Carlos Noriega Loret de Mola Grêmio/RS
        Cartões Amarelos
        Tempo 1T/2T Nº Nome do Jogador Equipe
        30:00 1T 28 Tomas Esteban Cuello Atlético Mineiro/MG
        +01:00 2T 6 Gustavo Martins de Souza Santos Grêmio/RS
        """
        ea = ExpertAssistant(api_key="dummy")
        parsed = ea._parse_sumula_deterministically(
            sumula_text=sample_sumula,
            team1="Grêmio",
            team2="Atlético-MG",
            comp="Copa do Brasil",
            date="01/11/2026",
            platform="Amazon Prime"
        )
        self.assertEqual(parsed["resultado"], "2 x 0")
        self.assertEqual(parsed["first_half_start"], "18:30:00")
        self.assertEqual(parsed["half_time_start"], "19:20:00")
        self.assertEqual(parsed["second_half_start"], "19:38:00")
        self.assertEqual(parsed["match_end"], "20:29:00")
        self.assertEqual(parsed["stoppage_time_1t"], 5)
        self.assertEqual(parsed["stoppage_time_2t"], 6)
        self.assertTrue(parsed["is_deterministic_sumula"])
        
        milestones = parsed.get("technical_milestones", [])
        self.assertEqual(len(milestones), 4)
        
        # Gol 1
        self.assertEqual(milestones[0]["minute"], 10)
        self.assertEqual(milestones[0]["time"], "18:40:00")
        self.assertIn("Carlos Vinicius", milestones[0]["event"])
        
        # Gol 2
        self.assertEqual(milestones[1]["minute"], 46)
        self.assertEqual(milestones[1]["time"], "19:39:00")
        self.assertIn("Erick Carlos", milestones[1]["event"])
        
        # Cartão 1
        self.assertEqual(milestones[2]["minute"], 30)
        self.assertEqual(milestones[2]["time"], "19:00:00")
        
        # Grounding Page 2
        self.assertIn("grounding_verdict", parsed)
        self.assertIn("2 x 0", parsed["grounding_verdict"]["verdict_text"])

    def test_pdf_reports_integrity_and_page2(self):
        """Valida se os relatórios gerados do dia 01/11 possuem exatamente 2 páginas e a seção oficial."""
        import glob
        p_vasco = glob.glob(os.path.join(PROJECT_ROOT, "reports", "*palmeiras*vasco*01112026*.pdf"))
        g_atletico = glob.glob(os.path.join(PROJECT_ROOT, "reports", "*amazon*grêmio*atlético*01112026*.pdf"))
        
        self.assertTrue(len(p_vasco) > 0, "PDF de Palmeiras x Vasco deve existir em reports.")
        self.assertTrue(len(g_atletico) > 0, "PDF de Grêmio x Atlético-MG deve existir em reports.")
        
        doc1 = pypdfium2.PdfDocument(p_vasco[-1])
        doc2 = pypdfium2.PdfDocument(g_atletico[-1])
        
        self.assertEqual(len(doc1), 2, "Relatório Palmeiras x Vasco deve ter 2 páginas.")
        self.assertEqual(len(doc2), 2, "Relatório Grêmio x Atlético-MG deve ter 2 páginas.")
        
        p2_text_1 = doc1[1].get_textpage().get_text_range()
        p2_text_2 = doc2[1].get_textpage().get_text_range()
        
        self.assertIn("CONFIRMAÇÃO DE HORÁRIOS", p2_text_1)
        self.assertIn("CONFIRMAÇÃO DE HORÁRIOS", p2_text_2)

if __name__ == "__main__":
    unittest.main()
