import sys
import os
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.report_generator import ReportGenerator

rg = ReportGenerator(PROJECT_ROOT)

m = {
    "match_display": "Fluminense x Internacional",
    "team1": "Fluminense",
    "team2": "Internacional",
    "competition": "Brasileirão Série A",
    "platform": "CazéTV",
    "date": "28/10/2026",
    "time": "18:30",
    "live_start_time": "18:15:00",
    "live_end_time": "20:50:00",
    "first_half_start": "18:30:00",
    "half_time_start": "19:17:00",
    "second_half_start": "19:32:00",
    "match_end": "20:27:00",
    "post_game_end": "20:50:00",
    "stoppage_time_1t": 2,
    "stoppage_time_2t": 7,
    "confidence_score": 0.99,
    "duration": 9000,
    "technical_milestones": [
        {"time": "18:15:00", "type": "Abertura do Sinal", "event": "Início da cobertura ao vivo na CazéTV.", "confidence": 0.99},
        {"time": "18:25:00", "type": "Hino Nacional", "event": "Execução do hino nacional no Maracanã.", "confidence": 0.99},
        {"time": "18:30:00", "minute": 0, "type": "APITO INICIAL (1T)", "event": "Início do jogo no Maracanã.", "confidence": 0.99},
        {"time": "19:17:00", "minute": 47, "type": "FIM DO 1º TEMPO", "event": "Fim do primeiro tempo sem abertura de placar (+2' de acréscimo) - 0 x 0.", "confidence": 0.99},
        {"time": "19:32:00", "minute": 45, "type": "APITO INICIAL (2T)", "event": "Início da segunda etapa.", "confidence": 0.99},
        {"time": "19:33:00", "minute": 46, "type": "GOL", "event": "Gol do Internacional! Alan Patrick marca logo no primeiro minuto (0 x 1).", "confidence": 0.99},
        {"time": "20:05:00", "minute": 78, "type": "GOL", "event": "Gol do Fluminense! Hércules empata aos 33' do 2T (1 x 1).", "confidence": 0.99},
        {"time": "20:23:00", "minute": 96, "type": "GOL", "event": "Gol do Fluminense! Lucho Acosta decreta a virada heroica aos 51' do 2T (2 x 1).", "confidence": 0.99},
        {"time": "20:27:00", "minute": 97, "type": "APITO FINAL", "event": "Encerramento no Maracanã (+7' de acréscimo). Fluminense 2 x 1 Internacional.", "confidence": 0.99},
        {"time": "20:38:00", "type": "Pós-Jogo", "event": "Entrevistas com Lucho Acosta e análise da virada tricolor.", "confidence": 0.99},
        {"time": "20:50:00", "type": "ENCERRAMENTO", "event": "Encerramento com transmissão 100% nominal.", "confidence": 0.99}
    ],
    "grounding_verdict": {
        "verdict_text": (
            "A confirmação do horário de início da partida foi verificada em múltiplos portais oficiais e veículos esportivos de grande relevância, "
            "como a tabela detalhada da CBF (Confederação Brasileira de Futebol), o Globo Esporte (ge), a ESPN Brasil e o Lance!.\n\n"
            "Todos esses canais confirmam os dados abaixo para o jogo da 33ª rodada do Campeonato Brasileiro:\n\n"
            "• Horário de Início: 18h30 (Horário de Brasília)\n"
            "• Horário de Término: O apito final da partida foi registrado nos veículos de transmissão às 20h27.\n\n"
            "O confronto terminou com a vitória do Fluminense por 2 a 1 sobre o Internacional no Estádio do Maracanã. A transmissão oficial exclusiva em streaming aberto foi realizada pela CazéTV."
        ),
        "references": [
            {"title": "Súmula Oficial Eletrônica - CBF", "url": "https://www.cbf.com.br/futebol-brasileiro/competicoes/campeonato-brasileiro-serie-a/2026/328"},
            {"title": "Globo Esporte (ge) - Pós-Jogo e Tempo Real", "url": "https://ge.globo.com/futebol/brasileirao-serie-a/"},
            {"title": "Lance! - Ficha Técnica e Relógio Final", "url": "https://www.lance.com.br/futebol-nacional/"},
            {"title": "CazéTV (YouTube) - Live Stream Oficial", "url": "https://www.youtube.com/@CazeTV/streams"}
        ]
    },
    "sources": [
        {"title": "Súmula Oficial Eletrônica - CBF", "url": "https://www.cbf.com.br", "snippet": "Registro oficial do quarteto de arbitragem e cronologia da partida."},
        {"title": "Globo Esporte (ge)", "url": "https://ge.globo.com", "snippet": "Cobertura minuto a minuto e cronômetro em tempo real do confronto no Maracanã."}
    ]
}

pdf = rg.write_expert_report([m], sync_sharepoint=False, name_prefix="test_expert")
print("PDF generated successfully:", pdf)

import pypdfium2 as pdfium
doc = pdfium.PdfDocument(pdf)
print(f"Total pages: {len(doc)}")
for i, page in enumerate(doc):
    text = page.get_textpage().get_text_range()
    print(f"--- PAGE {i+1} ---")
    print(text[-300:] if len(text) > 300 else text)
