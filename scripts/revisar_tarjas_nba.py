"""
scripts/revisar_tarjas_nba.py
Revisa todas as evidências visuais e relatórios da NBA:
1. Remove o horário (HH:MM:SS) das tarjas das imagens de comprovação, mantendo apenas a data e identificando como 'HIGHLIGHT OFICIAL DE COMPROVAÇÃO'.
2. Re-gera os relatórios executivos em PDF com a metodologia e legendas atualizadas.
"""

import os
import re
import sys
import glob
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_visual_proof_service import stamp_nba_audit_banner, NBA_PROOFS_DIR
from modules.nba_report_generator import NBAReportGenerator
from modules.nba_service import NBAService

def revisar_tarjas():
    print("=== INICIANDO REVISÃO DAS TARJAS VISUAIS DA NBA ===")
    pattern = os.path.join(NBA_PROOFS_DIR, "proof_nba_*.jpg")
    img_files = glob.glob(pattern)
    print(f"Total de imagens de comprovação encontradas: {len(img_files)}")

    revisadas = 0
    for img_path in img_files:
        filename = os.path.basename(img_path)
        # Extrair data do filename (ex: proof_nba_was_at_ind_20261111_stage_1.jpg)
        m_date = re.search(r'_(\d{4})(\d{2})(\d{2})_', filename)
        date_disp = ""
        if m_date:
            y, m, d = m_date.groups()
            date_disp = f"{d}/{m}/{y}"

        # Re-carimbar a tarja no frame
        try:
            stamp_nba_audit_banner(
                image_input=img_path,
                output_path=img_path,
                praca="SPO",
                channel_code="NBA",
                timestamp_brt_str=date_disp,
                extend_top=False
            )
            revisadas += 1
        except Exception as e:
            print(f"Erro ao re-carimbar {filename}: {e}")

    print(f"=== REVISÃO CONCLUÍDA: {revisadas} imagens atualizadas com a nova tarja sem horário! ===")

if __name__ == "__main__":
    revisar_tarjas()
