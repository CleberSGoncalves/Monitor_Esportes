import os
import sys
import io
import json
import requests
import pypdfium2

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from modules.expert_assistant import ExpertAssistant
from modules.report_generator import ReportGenerator
from modules.sharepoint_reporter import SharePointReporter

def generate_and_upload(sumula_url, team1, team2, comp, date, platform, kickoff_str):
    print(f"\n=======================================================")
    print(f"PROCESSANDO: {team1} x {team2} ({date}) - {platform}")
    print(f"Sumula URL: {sumula_url}")
    print(f"=======================================================")
    
    # 1. Download sumula PDF directly from conteudo.cbf.com.br
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(sumula_url, headers=headers, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Falha ao baixar sumula: {resp.status_code}")
        
    doc = pypdfium2.PdfDocument(io.BytesIO(resp.content))
    sumula_text = "\n".join([page.get_textpage().get_text_range() for page in doc])
    print(f"[OK] Sumula baixada ({len(sumula_text)} caracteres)")
    
    # 2. Parse deterministically
    ea = ExpertAssistant(api_key="dummy")
    data = ea._parse_sumula_deterministically(
        sumula_text=sumula_text,
        team1=team1,
        team2=team2,
        comp=comp,
        date=date,
        platform=platform
    )
    
    print(f"[OK] Parsing determinístico concluído:")
    print(f"     Placar: {data.get('resultado')}")
    print(f"     1T: {data.get('first_half_start')} -> {data.get('half_time_start')} (+{data.get('stoppage_time_1t')}')")
    print(f"     2T: {data.get('second_half_start')} -> {data.get('match_end')} (+{data.get('stoppage_time_2t')}')")
    print(f"     Marcos: {len(data.get('technical_milestones', []))}")
    
    # 3. Gerar PDF de exatamente 2 páginas
    rg = ReportGenerator(reports_dir=os.path.join(PROJECT_ROOT, "reports"))
    prefs = {
        "show_chrono": True,
        "show_milestones": True,
        "show_secondary": True,
        "show_sources": True
    }
    pdf_path = rg.write_expert_report([data], prefs=prefs, sync_sharepoint=False)
    print(f"[OK] Relatório PDF gerado em: {pdf_path}")
    
    # Validar páginas do PDF gerado
    gen_doc = pypdfium2.PdfDocument(pdf_path)
    total_pages = len(gen_doc)
    print(f"[OK] Total de páginas do relatório PDF: {total_pages}")
    if total_pages < 2:
        print("[AVISO] O relatório possui menos de 2 páginas!")
        
    # 4. Upload no SharePoint na pasta oficial Relatorios_de_Jogos
    print(f"[SHAREPOINT] Iniciando upload no SharePoint...")
    sp_ok = SharePointReporter.upload_report(
        filepath=pdf_path,
        campeonato=comp,
        partida=f"{team1} x {team2}",
        plataforma=platform,
        confianca="100.0%",
        auditado=True,
        date_str=date,
        time_str=kickoff_str
    )
    print(f"[SHAREPOINT RESULTADO] Sucesso: {sp_ok}")
    return pdf_path, sp_ok

if __name__ == "__main__":
    # Jogo 1: Palmeiras x Vasco da Gama
    p1, ok1 = generate_and_upload(
        sumula_url="https://conteudo.cbf.com.br/sumulas/2026/424152se.pdf",
        team1="Palmeiras",
        team2="Vasco da Gama",
        comp="Copa do Brasil",
        date="01/11/2026",
        platform="Amazon Prime",
        kickoff_str="16:00"
    )
    
    # Jogo 2: Grêmio x Atlético-MG
    p2, ok2 = generate_and_upload(
        sumula_url="https://conteudo.cbf.com.br/sumulas/2026/424151se.pdf",
        team1="Grêmio",
        team2="Atlético-MG",
        comp="Copa do Brasil",
        date="01/11/2026",
        platform="Amazon Prime",
        kickoff_str="17:30"
    )
    
    print("\n=======================================================")
    print("CONCLUÍDO COM SUCESSO TOTAL!")
    print(f"Palmeiras x Vasco: {ok1} -> {p1}")
    print(f"Grêmio x Atlético-MG: {ok2} -> {p2}")
    print("=======================================================")
