import os
import csv
import re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Atualizar modules/cbf_schedule_fetcher.py
fetcher_path = os.path.join(PROJECT_ROOT, "modules", "cbf_schedule_fetcher.py")
with open(fetcher_path, "r", encoding="utf-8") as f:
    text = f.read()

# Substituir get_real_cbf_fixtures
fixtures_code = '''def get_real_cbf_fixtures() -> list:
    """
    Retorna estritamente os jogos monitorados futuros da CBF de acordo com a tabela oficial (Edição 2026):
    - Brasileirão Série A: Coluna 4 (Amazon Prime) ou Coluna 5 (CazéTV).
    - Copa do Brasil: Coluna 3/4 (Amazon Prime).
    """
    fixtures = [
        # 29/10 (qui) 20:00 - Brasileirão Série A (Coluna 4 = Amazon Prime)
        {
            "comp": "Brasileirão Série A",
            "team1": "Vasco da Gama",
            "team2": "Flamengo",
            "date": "29/10/2026",
            "time": "20:00",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Coluna 4)"
        },
        # 01/11 (dom) 15:00 - Copa do Brasil (Amazon Prime)
        {
            "comp": "Copa do Brasil",
            "team1": "Palmeiras",
            "team2": "Vasco da Gama",
            "date": "01/11/2026",
            "time": "15:00",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Copa do Brasil)"
        },
        # 01/11 (dom) 17:30 - Copa do Brasil (Amazon Prime)
        {
            "comp": "Copa do Brasil",
            "team1": "Grêmio",
            "team2": "Atlético-MG",
            "date": "01/11/2026",
            "time": "17:30",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Copa do Brasil)"
        },
        # 04/11 (qua) 19:30 - Brasileirão Série A (Coluna 5 = CazéTV)
        {
            "comp": "Brasileirão Série A",
            "team1": "Athletico-PR",
            "team2": "Vasco da Gama",
            "date": "04/11/2026",
            "time": "19:30",
            "platform": "CazéTV",
            "tag": "📺 Transmissão Exclusiva (CazéTV - Coluna 5)"
        },
        # 05/11 (qui) 21:30 - Brasileirão Série A (Coluna 4 = Amazon Prime)
        {
            "comp": "Brasileirão Série A",
            "team1": "Cruzeiro",
            "team2": "Bahia",
            "date": "05/11/2026",
            "time": "21:30",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Coluna 4)"
        },
        # 07/11 (sáb) 17:00 - Copa do Brasil (Amazon Prime)
        {
            "comp": "Copa do Brasil",
            "team1": "Atlético-MG",
            "team2": "Grêmio",
            "date": "07/11/2026",
            "time": "17:00",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Copa do Brasil)"
        },
        # 08/11 (dom) 16:00 - Copa do Brasil (Amazon Prime)
        {
            "comp": "Copa do Brasil",
            "team1": "Vasco da Gama",
            "team2": "Palmeiras",
            "date": "08/11/2026",
            "time": "16:00",
            "platform": "Amazon Prime",
            "tag": "🔥 Transmissão Exclusiva (Amazon Prime - Copa do Brasil)"
        }
    ]

    def parse_dt(g):
        try:
            return datetime.strptime(f"{g.get('date', '')} {g.get('time', '')}", "%d/%m/%Y %H:%M")
        except:
            return datetime.max

    fixtures.sort(key=parse_dt)
    return fixtures'''

text = re.sub(r'def get_real_cbf_fixtures\(\) -> list:.*?return fixtures', fixtures_code, text, flags=re.DOTALL)
with open(fetcher_path, "w", encoding="utf-8") as f:
    f.write(text)
print("[OK] modules/cbf_schedule_fetcher.py atualizado sem jogos fictícios.")

# 2. Atualizar gui/main_gui.py _load_cbf_streaming_events
main_gui_path = os.path.join(PROJECT_ROOT, "gui", "main_gui.py")
with open(main_gui_path, "r", encoding="utf-8") as f:
    gui_text = f.read()

# Substituir official_schedule_2026
official_code = '''    official_schedule_2026 = [
        {"comp": "Brasileirão Série A", "partida": "Vasco da Gama x Flamengo", "team1": "Vasco da Gama", "team2": "Flamengo", "date": "29/10/2026", "time": "20:00", "platform": "Amazon Prime"},
        {"comp": "Copa do Brasil", "partida": "Palmeiras x Vasco da Gama", "team1": "Palmeiras", "team2": "Vasco da Gama", "date": "01/11/2026", "time": "15:00", "platform": "Amazon Prime"},
        {"comp": "Copa do Brasil", "partida": "Grêmio x Atlético-MG", "team1": "Grêmio", "team2": "Atlético-MG", "date": "01/11/2026", "time": "17:30", "platform": "Amazon Prime"},
        {"comp": "Brasileirão Série A", "partida": "Athletico-PR x Vasco da Gama", "team1": "Athletico-PR", "team2": "Vasco da Gama", "date": "04/11/2026", "time": "19:30", "platform": "CazéTV"},
        {"comp": "Brasileirão Série A", "partida": "Cruzeiro x Bahia", "team1": "Cruzeiro", "team2": "Bahia", "date": "05/11/2026", "time": "21:30", "platform": "Amazon Prime"},
        {"comp": "Copa do Brasil", "partida": "Atlético-MG x Grêmio", "team1": "Atlético-MG", "team2": "Grêmio", "date": "07/11/2026", "time": "17:00", "platform": "Amazon Prime"},
        {"comp": "Copa do Brasil", "partida": "Vasco da Gama x Palmeiras", "team1": "Vasco da Gama", "team2": "Palmeiras", "date": "08/11/2026", "time": "16:00", "platform": "Amazon Prime"}
    ]'''

gui_text = re.sub(r'official_schedule_2026 = \[.*?\]', official_code.strip(), gui_text, flags=re.DOTALL)
with open(main_gui_path, "w", encoding="utf-8") as f:
    f.write(gui_text)
print("[OK] gui/main_gui.py atualizado.")

# 3. Atualizar config/streaming_data.csv e Streaming_Scheduler/data.csv
exact_csv_rows = [
    ["CBF - Brasileirão Série A", "Vasco da Gama x Flamengo", "29/10/2026", "20:00", "Esquerda", "15", "Amazon Prime", "https://www.primevideo.com"],
    ["CBF - Copa do Brasil", "Palmeiras x Vasco da Gama", "01/11/2026", "15:00", "Esquerda", "15", "Amazon Prime", "https://www.primevideo.com"],
    ["CBF - Copa do Brasil", "Grêmio x Atlético-MG", "01/11/2026", "17:30", "Esquerda", "15", "Amazon Prime", "https://www.primevideo.com"],
    ["CBF - Brasileirão Série A", "Athletico-PR x Vasco da Gama", "04/11/2026", "19:30", "Direita", "15", "Cazé TV", "https://www.youtube.com/@CazeTV/streams"],
    ["CBF - Brasileirão Série A", "Cruzeiro x Bahia", "05/11/2026", "21:30", "Esquerda", "15", "Amazon Prime", "https://www.primevideo.com"],
    ["CBF - Copa do Brasil", "Atlético-MG x Grêmio", "07/11/2026", "17:00", "Esquerda", "15", "Amazon Prime", "https://www.primevideo.com"],
    ["CBF - Copa do Brasil", "Vasco da Gama x Palmeiras", "08/11/2026", "16:00", "Esquerda", "15", "Amazon Prime", "https://www.primevideo.com"],
]

fallback_csv = os.path.join(PROJECT_ROOT, "config", "streaming_data.csv")
with open(fallback_csv, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Campeonato", "Partida", "Data", "Horário", "Navegador", "Min antes para ação", "Canal de Transmissão", "Url"])
    w.writerows(exact_csv_rows)

sched_csv = r"E:\desenvolvimento\Streaming_Scheduler\data.csv"
if os.path.exists(sched_csv):
    # Filtrar linhas antigas que continham Flamengo x Corinthians 31/10
    lines_keep = []
    with open(sched_csv, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            row_str = " ".join(row)
            if "Flamengo x Corinthians" in row_str and "31/10/2026" in row_str:
                continue
            if "São Paulo x Corinthians" in row_str and "04/11/2026" in row_str:
                continue
            lines_keep.append(row)
    
    # Adicionar as novas linhas oficiais se não existirem
    existing_keys = {f"{r[1]}_{r[2]}" for r in lines_keep if len(r) > 2}
    for r in exact_csv_rows:
        k = f"{r[1]}_{r[2]}"
        if k not in existing_keys:
            lines_keep.append(r)

    with open(sched_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows(lines_keep)
    print("[OK] Streaming_Scheduler/data.csv expurgado e sincronizado.")
