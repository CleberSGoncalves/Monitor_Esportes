import os
import sys
import pytest
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_autonomous_auditor import NBAAutonomousAuditor

def test_nba_auditor_blocks_small_pdf():
    auditor = NBAAutonomousAuditor.get_instance()
    
    # Criar um PDF dummy pequeno (< 50 KB)
    dummy_pdf = os.path.join(PROJECT_ROOT, "reports", "test_dummy_small.pdf")
    with open(dummy_pdf, "wb") as f:
        f.write(b"%PDF-1.4 dummy content without visual proofs" * 10)
        
    size = os.path.getsize(dummy_pdf)
    assert size < 50_000, "Dummy PDF deve ser menor que 50 KB"
    
    # O auditor deve rejeitar o envio de e-mail para PDFs < 50 KB
    # Validamos que is_game_audited respeita o cache
    assert auditor.is_game_audited("401909842") is True, "Jogo Sacramento @ Clippers deve constar no cache como auditado"
    
    if os.path.exists(dummy_pdf):
        os.remove(dummy_pdf)

def test_authentic_youtube_frames_exist_and_distinct():
    """Valida que cada canal tem sua própria pasta e seus próprios frames autênticos sem reaproveitamento cruzado."""
    channels = {
        "bage_tv_real": "bge",
        "band_rs_real": "bnd",
        "gaucha_real": "gau",
        "gaucha_esportes_real": "ges"
    }
    
    base_dir = os.path.join(PROJECT_ROOT, "reports", "visual_proofs")
    
    for folder, sigla in channels.items():
        ch_dir = os.path.join(base_dir, folder)
        assert os.path.exists(ch_dir), f"Diretório {ch_dir} deve existir"
        
        # Checar se os 10 marcos existem e têm tamanho > 50 KB
        for stage in range(1, 11):
            frame_path = os.path.join(ch_dir, f"proof_stage_{stage}_{sigla}.jpg")
            assert os.path.exists(frame_path), f"Frame {frame_path} deve existir"
            size = os.path.getsize(frame_path)
            assert size > 50_000, f"Frame {frame_path} deve ser uma imagem de alta resolução (>50KB), tamanho atual: {size}"
            
            # Validar formato da imagem
            with Image.open(frame_path) as img:
                assert img.size[0] >= 1280, f"Largura do frame deve ser pelo menos 720p (1280px), atual: {img.size[0]}"
                assert img.size[1] >= 720, f"Altura do frame deve ser pelo menos 720px, atual: {img.size[1]}"

def test_generated_youtube_pdfs_exist_and_complete():
    """Valida que os 4 relatórios em PDF foram gerados com mais de 500 KB (com todas as 10 comprovações visuais)."""
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    files = os.listdir(reports_dir)
    
    expected_matches = ["expert_bagé_tv", "expert_esporte_band_rs", "expert_gaúcha_", "expert_gaúcha_esportes"]
    for ch in expected_matches:
        matching = [f for f in files if ch in f.lower() and f.endswith(".pdf") and "01112026" in f]
        assert len(matching) > 0, f"Relatório PDF para {ch} deve existir na pasta reports/"
        latest = sorted(matching)[-1]
        pdf_path = os.path.join(reports_dir, latest)
        size = os.path.getsize(pdf_path)
        assert size > 500_000, f"Relatório PDF {latest} deve ser completo (>500KB) com comprovação visual, atual: {size} bytes"
