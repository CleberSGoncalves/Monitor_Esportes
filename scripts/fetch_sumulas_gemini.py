"""
Busca dados das sumulas CBF via Gemini com Google Search grounding
para os 4 jogos auditados pelo Arthur.
"""
import sys, json, os, re
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")

with open(r"e:\desenvolvimento\Monitor_Esportes\config\google_ai.json", encoding="utf-8") as f:
    cfg = json.load(f)
api_key = cfg.get("api_key", "")

import google.genai as genai
from google.genai import types

client = genai.Client(api_key=api_key)

prompt = (
    "Busque na internet os dados oficiais das sumulas da CBF para os seguintes jogos da Copa do Brasil 2026. "
    "Para cada jogo, preciso exatamente: horario oficial de inicio (apito inicial 1o tempo), "
    "horario fim do 1o tempo, horario inicio do 2o tempo, horario fim da partida (apito final), "
    "acrescimos de cada tempo, e o resultado do jogo.\n\n"
    "Jogos:\n"
    "1. Chapecoense x Sao Paulo - 23/08/2026 - Copa do Brasil\n"
    "2. Cruzeiro x Flamengo - 22/08/2026 - Copa do Brasil\n"
    "3. Vasco x Vitoria - 26/08/2026 - Copa do Brasil\n"
    "4. Palmeiras x Santos - 26/08/2026 - Copa do Brasil\n\n"
    "Responda SOMENTE em formato JSON valido com esta estrutura exata:\n"
    '{"Chapecoense_x_Sao_Paulo": {"data": "23/08/2026", "resultado": "X x X", '
    '"horario_inicio_jogo": "HH:MM", "horario_fim_1t": "HH:MM", '
    '"horario_inicio_2t": "HH:MM", "horario_fim_jogo": "HH:MM", '
    '"acrescimos_1t": 0, "acrescimos_2t": 0, "fonte": "url"}, '
    '"Cruzeiro_x_Flamengo": {...}, "Vasco_x_Vitoria": {...}, "Palmeiras_x_Santos": {...}}'
)

print("Consultando Gemini com Google Search grounding...")
result = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.1,
    )
)

text = result.text
print("\nRESPOSTA GEMINI:")
print(text)

# Tentar extrair JSON
json_match = re.search(r"\{.*\}", text, re.DOTALL)
if json_match:
    try:
        data = json.loads(json_match.group())
        print("\nJSON EXTRAIDO:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        out_path = r"e:\desenvolvimento\Monitor_Esportes\scratch\sumulas_cbf_official.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("\nSalvo em: " + out_path)
    except Exception as e:
        print("Erro ao parsear JSON: " + str(e))
else:
    print("Nenhum JSON encontrado na resposta.")
