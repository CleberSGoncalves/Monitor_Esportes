import google.generativeai as genai
import json

with open(r"e:\desenvolvimento\Monitor_Esportes\config\google_ai.json", "r") as f:
    key = json.load(f)["api_key"]

genai.configure(api_key=key)

try:
    model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
    print(f"Modelo {model.model_name} carregado com sucesso.")
    # Teste de geração mínima
    response = model.generate_content("Responda apenas 'OK'")
    print(f"Resposta: {response.text}")
except Exception as e:
    print(f"Erro: {e}")
