import os
import sys
import hashlib
import pytest
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_youtube_reporter import SharePointYouTubeReporter
from modules.visual_proof_service import get_channel_sigla, stamp_audit_banner
from modules.auto_updater import CURRENT_VERSION, AutoUpdater

def get_file_md5(file_path):
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

def test_distinct_channel_frames_exist_and_unique():
    channels = ["gaúcha", "gaucha_esportes", "bage_tv", "esporte_band_rs"]
    channel_frames = {}

    for ch in channels:
        folder = os.path.join(PROJECT_ROOT, "reports", "visual_proofs", ch)
        assert os.path.exists(folder), f"Pasta de frames para {ch} não existe: {folder}"
        
        frames = [os.path.join(folder, f) for f in os.listdir(folder) if f.startswith("proof_etapa_") and f.endswith(".jpg")]
        assert len(frames) >= 10, f"Canal {ch} tem menos de 10 frames: {len(frames)}"
        
        # Verificar integridade de cada imagem
        for fp in frames:
            assert os.path.getsize(fp) > 20000, f"Frame {fp} é muito pequeno ou corrompido"
            with Image.open(fp) as img:
                w, h = img.size
                assert w >= 640 and h >= 360, f"Resolução inválida em {fp}: {w}x{h}"

        channel_frames[ch] = frames

    # Validação rigorosa: NENHUM frame da etapa 4 (gol) pode ter o mesmo hash entre canais!
    etapa4_hashes = set()
    for ch in channels:
        fp_etapa4 = os.path.join(PROJECT_ROOT, "reports", "visual_proofs", ch, "proof_etapa_4.jpg")
        assert os.path.exists(fp_etapa4), f"Frame etapa 4 não encontrado para {ch}"
        h = get_file_md5(fp_etapa4)
        assert h not in etapa4_hashes, f"DUPLICAÇÃO DETECTADA: O frame da etapa 4 de {ch} é idêntico a outro canal!"
        etapa4_hashes.add(h)

    assert len(etapa4_hashes) == len(channels), "Cada canal DEVE ter seu próprio frame distinto e autêntico!"

def test_channel_siglas():
    assert get_channel_sigla("Bagé TV") == "BGE"
    assert get_channel_sigla("Esporte Band RS") == "BND"
    assert get_channel_sigla("Gaúcha") == "GAU"
    assert get_channel_sigla("Gaúcha Esportes") == "GAU"
    assert get_channel_sigla("Baldasso TV") == "BLD"
    assert get_channel_sigla("Atlantida TV") == "ATL"

def test_sharepoint_normalizar_canal():
    assert SharePointYouTubeReporter.normalizar_canal("bage tv") == "Bagé TV"
    assert SharePointYouTubeReporter.normalizar_canal("esporte band rs") == "Esporte Band RS"
    assert SharePointYouTubeReporter.normalizar_canal("gaúcha") == "Gaúcha"
    assert SharePointYouTubeReporter.normalizar_canal("gaucha esportes") == "Gaucha Esportes"
    assert SharePointYouTubeReporter.normalizar_canal("baldasso tv") == "Baldasso TV"
    assert SharePointYouTubeReporter.normalizar_canal("atlantida tv") == "Atlantida TV"

def test_auto_updater_version_bump():
    assert CURRENT_VERSION == "2.4.35", f"Versão deve ser 2.4.35, atual: {CURRENT_VERSION}"
