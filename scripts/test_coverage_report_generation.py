"""
scripts/test_coverage_report_generation.py
Testa a geração de ponta a ponta do laudo de Cobertura & Debate ao Vivo
para um evento esportivo real sem narração lance a lance (Central do Torcedor / Gaúcha).
Renderiza as páginas em PNG e valida todos os campos e requisitos.
"""

import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.narration_chronology import generate_coverage_chronology, extract_program_name, is_sports_debate_or_coverage
from modules.report_generator import ReportGenerator

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def test_coverage_pipeline():
    print("=" * 70)
    print("🚀 TESTE E2E: GERAÇÃO DE LAUDO DE COBERTURA & DEBATE ESPORTIVO AO VIVO")
    print("=" * 70)

    # 1. Testar extração de Nome do Programa
    t1 = "INTER TEM DECISÃO CONTRA O BOTAFOGO; GRÊMIO PREGA MOBILIZAÇÃO | CENTRAL DO TORCEDOR | 24/10/2026"
    prog1 = extract_program_name(t1, "Gaúcha")
    print(f"Título: {t1}")
    print(f"Nome do Programa extraído: '{prog1}'")
    assert prog1 == "Central do Torcedor", f"Esperado 'Central do Torcedor', obtido '{prog1}'"

    is_cov1, prog_name1 = is_sports_debate_or_coverage(t1)
    print(f"is_sports_debate_or_coverage: {is_cov1} (Programa: '{prog_name1}')")
    assert is_cov1 is True

    # 2. Configurar evento de teste baseado no evento real da Gaúcha
    event = {
        "video_id": "3DqzfZqIgQ4",
        "title": t1,
        "channel_name": "Gaúcha",
        "channel_url": "https://www.youtube.com/@gauchazh",
        "url": "https://www.youtube.com/watch?v=3DqzfZqIgQ4",
        "actual_start_epoch": int(datetime(2026, 10, 24, 18, 0, 0).timestamp()),
        "scheduled_epoch": int(datetime(2026, 10, 24, 18, 0, 0).timestamp()),
        "duration": 7200, # 2 horas de live
        "program_name": prog1,
        "is_coverage_debate": True,
        "event_type": "live_coverage_debate",
        "brand_mentions": [
            {
                "brand": "KTO",
                "video_time": "00:12:30",
                "real_time": "18:12:30",
                "type": "Patrocínio Máster / Testemunhal",
                "quote": "Aposte na emoção do futebol com a KTO. Faça sua fezinha no clássico!"
            },
            {
                "brand": "BANRISUL",
                "video_time": "00:35:10",
                "real_time": "18:35:10",
                "type": "Citação Comercial / Banner",
                "quote": "Banrisul: o banco dos gaúchos ao lado do esporte."
            },
            {
                "brand": "SUPERMERCADOS GUANABARA",
                "video_time": "01:05:00",
                "real_time": "19:05:00",
                "type": "Leitura de Oferta / Merchandising",
                "quote": "Confira as super ofertas do final de semana no Guanabara."
            },
            {
                "brand": "ZAPAY",
                "video_time": "01:40:20",
                "real_time": "19:40:20",
                "type": "Testemunhal",
                "quote": "Pague IPVA e multas parceladas em até 12x com o app Zapay."
            }
        ]
    }

    # 3. Gerar a estrutura de cronologia temática
    result = generate_coverage_chronology(event, api_key=None, log=print)
    
    assert result.get("report_kind") == "live_coverage"
    assert result.get("program_name") == "Central do Torcedor"
    assert len(result.get("technical_milestones", [])) >= 5
    assert len(result.get("brand_mentions", [])) >= 4

    print("\n✅ Estrutura de dados de Cobertura gerada com sucesso!")
    print(f" - Report Title: {result.get('report_title')}")
    print(f" - Programa: {result.get('program_name')}")
    print(f" - Total de Blocos: {len(result.get('technical_milestones'))}")
    for idx, b in enumerate(result.get("technical_milestones"), 1):
        print(f"   Bloco {idx}: [{b.get('clock')}] {b.get('event')} | {b.get('description')[:60]}...")

    # 4. Gerar Evidências Visuais (Frames Tarjados em BRT)
    from modules.visual_proof_service import generate_chronology_stage_proofs
    m_proofs = generate_chronology_stage_proofs(
        video_url_or_id="https://www.youtube.com/watch?v=3DqzfZqIgQ4",
        milestones=result["technical_milestones"],
        date_str="24/10/2026",
        stream_start_dt=datetime(2026, 10, 24, 18, 0, 0),
        praca="SPO",
        channel_name="GAU",
        match_display="Inter x Botafogo / Grêmio Mobilização",
        competition="Debate & Cobertura Esportiva",
        program_name="Central do Torcedor",
        is_coverage_debate=True
    )
    assert len(m_proofs) >= 5, f"Esperado >= 5 frames, obtido {len(m_proofs)}"
    result["milestone_proofs"] = m_proofs
    result["visual_proof_images"] = [p["image_path"] for p in m_proofs]
    print(f"\n📸 {len(m_proofs)} frames auditados gerados com carimbo oficial!")

    # 5. Renderizar o Relatório PDF com ReportGenerator
    reports_dir = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    reporter = ReportGenerator(reports_dir=reports_dir)
    prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
    pdf_path = reporter.write_expert_report([result], prefs=prefs, sync_sharepoint=False, name_prefix="cobertura_debate")

    print(f"\n📄 PDF Gerado: {pdf_path}")
    assert os.path.exists(pdf_path), "PDF não foi gerado!"
    sz = os.path.getsize(pdf_path)
    print(f"Tamanho do PDF: {sz / (1024*1024):.2f} MB ({sz} bytes)")
    assert sz > 200_000, f"PDF gerado é muito pequeno: {sz} bytes"

    # 6. Renderizar páginas do PDF em PNG para o Artifact do usuário
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(pdf_path)
    page_count = len(doc)
    print(f"Total de páginas renderizadas no PDF: {page_count}")

    artifact_dir = r"C:\Users\Cleber\.gemini\antigravity\brain\4349b494-c0ce-4e02-8f40-71dee7388ad6"
    os.makedirs(artifact_dir, exist_ok=True)
    
    png_paths = []
    for p_idx in range(page_count):
        page = doc[p_idx]
        image = page.render(scale=2.0).to_pil()
        out_png = os.path.join(artifact_dir, f"debate_central_torcedor_page_{p_idx + 1}.png")
        image.save(out_png)
        png_paths.append(out_png)
        print(f" - Página {p_idx + 1} salva em: {out_png}")

    print("\n🎉 TESTE CONCLUÍDO COM 100% DE SUCESSO!")
    return pdf_path, png_paths

if __name__ == "__main__":
    test_coverage_pipeline()
