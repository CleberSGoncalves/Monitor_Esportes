"""
tests/test_nba_visual_proof_engine.py
Suíte de testes do Motor de Comprovação Visual e Relatórios da NBA.

Valida:
1. Siglas de canais (NBA, PRM, DIS, ESP).
2. Tarja de auditoria estampada com fuso BRT.
3. Seleção ESTRITA de vídeo: só canal oficial NBA + "FULL GAME HIGHLIGHTS" + times + data + duração.
4. Sem vídeo oficial => nenhuma imagem sintética; etapas marcadas como indisponíveis.
5. Cache só é reutilizado para o mesmo vídeo oficial.
6. PDF multi-página com frames reais e com aviso de etapa indisponível.
"""

import os
import sys
import json
import pytest
from PIL import Image
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.nba_visual_proof_service import (
    get_nba_channel_sigla,
    stamp_nba_audit_banner,
    create_nba_synthetic_frame,
    select_official_video,
    NBAVisualProofService,
)
from modules.nba_report_generator import NBAReportGenerator


GAME = {
    "away_team": "Brooklyn Nets", "home_team": "Boston Celtics",
    "away_tri": "BKN", "home_tri": "BOS",
    "date_clean": "20261027", "date_display": "27/10/2026",
    "score_display": "114 - 117", "platform": "Amazon Prime",
    "time_brt": "20:40:00", "match_display": "Brooklyn Nets @ Boston Celtics",
}
GAMEBOOK = {
    "game_duration": "2:46", "attendance": "19.156", "arena": "TD Garden, Boston, MA",
    "officials": ["Scott Foster"],
    "milestones": [
        {"period": "1º Quarto", "type": "start", "time_brt": "20:40:00", "time_local_str": "7:40 PM (Local)"},
        {"period": "1º Quarto", "type": "end", "time_brt": "21:06:00", "time_local_str": "8:06 PM (Local)"},
        {"period": "2º Quarto", "type": "start", "time_brt": "21:09:00", "time_local_str": "8:09 PM (Local)"},
        {"period": "2º Quarto", "type": "end", "time_brt": "21:40:00", "time_local_str": "8:40 PM (Local)"},
    ],
}
OFFICIAL = {
    "id": "Roz4iFs4Rto", "uploader": "NBA", "duration": 1192,
    "title": "NETS at CELTICS | FULL GAME HIGHLIGHTS | October 27, 2026",
    "url": "https://www.youtube.com/watch?v=Roz4iFs4Rto",
}


def _fake_extract(calls=None):
    def fake(cls_or_url, *args, **kwargs):
        # classmethod patched with staticmethod-like signature: (video_url, second_offset, output_raw_path)
        video_url, offset, out_path = (cls_or_url, *args)[:3]
        if calls is not None:
            calls.append((video_url, offset))
        Image.new("RGB", (1280, 720), color=(40, 90, 50)).save(out_path, "JPEG")
        return True
    return staticmethod(fake)


def test_nba_channel_siglas():
    assert get_nba_channel_sigla("Amazon Prime Video") == "PRM"
    assert get_nba_channel_sigla("Disney+") == "DIS"
    assert get_nba_channel_sigla("ESPN") == "ESP"
    assert get_nba_channel_sigla("NBA League Pass") == "NBA"


def test_stamp_nba_audit_banner(tmp_path):
    raw = str(tmp_path / "raw.jpg")
    Image.new("RGB", (1280, 720), color=(50, 60, 70)).save(raw)
    out = stamp_nba_audit_banner(raw, str(tmp_path / "s.jpg"), praca="SPO", channel_code="NBA",
                                 timestamp_brt_str="27/10/2026 20:40:00")
    im = Image.open(out)
    assert im.size == (1280, 720)
    assert sum(im.getpixel((10, 10))) < 30


def test_create_nba_synthetic_frame_still_available_but_unused(tmp_path):
    out = create_nba_synthetic_frame(str(tmp_path / "x.jpg"), channel_code="PRM",
                                     timestamp_brt_str="27/10/2026 20:40:00")
    assert os.path.exists(out)


def test_select_official_video_accepts_only_official_full_highlights():
    third_party = {"id": "AAAAAAAAAAA", "uploader": "GAMETIME HIGHLIGHTS", "duration": 564,
                   "title": "Boston Celtics vs Brooklyn Nets Full Game Highlights - October 27, 2026 | NBA Season"}
    assert select_official_video([third_party], "Brooklyn Nets", "Boston Celtics", "20261027") is None
    assert select_official_video([third_party, OFFICIAL], "Brooklyn Nets", "Boston Celtics", "20261027") == OFFICIAL


@pytest.mark.parametrize("mutation", [
    {"uploader": "NBA Highlights Fan"},                                   # canal não oficial
    {"title": "NETS at CELTICS | GAME RECAP | October 27, 2026"},         # não é Full Game Highlights
    {"title": "NETS at CELTICS | FULL GAME HIGHLIGHTS | October 26, 2026"},  # data errada
    {"title": "KNICKS at CELTICS | FULL GAME HIGHLIGHTS | October 27, 2026"},  # time errado
    {"duration": 3096},                                                    # duração implausível
    {"duration": 120},
])
def test_select_official_video_rejects_mismatches(mutation):
    cand = dict(OFFICIAL, **mutation)
    assert select_official_video([cand], "Brooklyn Nets", "Boston Celtics", "20261027") is None


def test_no_official_video_means_no_images_and_no_synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(NBAVisualProofService, "resolve_nba_video", classmethod(lambda cls, *a, **k: None))
    proofs = NBAVisualProofService.generate_nba_visual_proofs(GAME, GAMEBOOK, output_dir=str(tmp_path))
    assert len(proofs) == 4
    for p in proofs:
        assert p["frame_available"] is False
        assert p["image_path"] is None
        assert p["clock_brt"]  # horário do Game Book preservado
    assert [f for f in os.listdir(tmp_path) if f.endswith(".jpg")] == []


def test_no_gamebook_milestones_returns_no_proofs(tmp_path):
    assert NBAVisualProofService.generate_nba_visual_proofs(GAME, {"milestones": []}, output_dir=str(tmp_path)) == []


def test_real_frames_and_cache_only_for_same_video(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(NBAVisualProofService, "resolve_nba_video", classmethod(lambda cls, *a, **k: dict(OFFICIAL)))
    monkeypatch.setattr(NBAVisualProofService, "extract_frame_at_offset", _fake_extract(calls))

    p1 = NBAVisualProofService.generate_nba_visual_proofs(GAME, GAMEBOOK, output_dir=str(tmp_path))
    assert len(calls) == 4 and all(p["frame_available"] and os.path.exists(p["image_path"]) for p in p1)
    assert all(p["source_video_id"] == OFFICIAL["id"] for p in p1)
    # offsets distintos e crescentes (cada etapa = ponto diferente do vídeo)
    offs = [c[1] for c in calls]
    assert offs == sorted(set(offs))

    # mesmo vídeo => reaproveita cache
    NBAVisualProofService.generate_nba_visual_proofs(GAME, GAMEBOOK, output_dir=str(tmp_path))
    assert len(calls) == 4

    # outro vídeo oficial => cache invalidado
    other = dict(OFFICIAL, id="ZZZZZZZZZZZ")
    monkeypatch.setattr(NBAVisualProofService, "resolve_nba_video", classmethod(lambda cls, *a, **k: dict(other)))
    NBAVisualProofService.generate_nba_visual_proofs(GAME, GAMEBOOK, output_dir=str(tmp_path))
    assert len(calls) == 8


def test_stamp_uses_gamebook_brt_time(tmp_path, monkeypatch):
    monkeypatch.setattr(NBAVisualProofService, "resolve_nba_video", classmethod(lambda cls, *a, **k: dict(OFFICIAL)))
    monkeypatch.setattr(NBAVisualProofService, "extract_frame_at_offset", _fake_extract())
    proofs = NBAVisualProofService.generate_nba_visual_proofs(GAME, GAMEBOOK, output_dir=str(tmp_path))
    assert [p["timestamp_brt_str"] for p in proofs] == [
        "27/10/2026 20:40:00", "27/10/2026 21:06:00", "27/10/2026 21:09:00", "27/10/2026 21:40:00"]


def _pdf_text(path):
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            pages = [(p.extract_text() or "") for p in pdf.pages]
        return " ".join(pages), len(pages)
    except ImportError:
        pass
    if fitz is None:
        pytest.skip("nenhum leitor de PDF disponível")
    doc = fitz.open(path)
    txt = " ".join(p.get_text() for p in doc)
    n = len(doc)
    doc.close()
    return txt, n


def test_pdf_with_real_frames(tmp_path, monkeypatch):
    monkeypatch.setattr(NBAVisualProofService, "resolve_nba_video", classmethod(lambda cls, *a, **k: dict(OFFICIAL)))
    monkeypatch.setattr(NBAVisualProofService, "extract_frame_at_offset", _fake_extract())
    proofs = NBAVisualProofService.generate_nba_visual_proofs(GAME, GAMEBOOK, output_dir=str(tmp_path / "p"))
    monkeypatch.setattr(NBAReportGenerator, "reports_dir", str(tmp_path))
    pdf = NBAReportGenerator.generate_report(GAME, GAMEBOOK, visual_proofs=proofs, auto_generate_proofs=False)
    txt, n = _pdf_text(pdf)
    assert n >= 2
    assert "COMPROVAÇÃO TÉCNICA VISUAL" in txt
    assert "posição proporcional" in txt          # transparência metodológica
    assert "Confiança IA" not in txt              # sem % de confiança inventado nos cards
    assert OFFICIAL["id"] in txt                  # fonte do frame identificada


def test_pdf_marks_unavailable_frames(tmp_path, monkeypatch):
    monkeypatch.setattr(NBAVisualProofService, "resolve_nba_video", classmethod(lambda cls, *a, **k: None))
    proofs = NBAVisualProofService.generate_nba_visual_proofs(GAME, GAMEBOOK, output_dir=str(tmp_path / "p"))
    monkeypatch.setattr(NBAReportGenerator, "reports_dir", str(tmp_path))
    pdf = NBAReportGenerator.generate_report(GAME, GAMEBOOK, visual_proofs=proofs, auto_generate_proofs=False)
    txt, _ = _pdf_text(pdf)
    assert "indisponível" in txt
