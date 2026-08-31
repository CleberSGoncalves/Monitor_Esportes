from google import genai
import json
import os

config_path = r"e:\desenvolvimento\Monitor_Esportes\config\google_ai.json"
with open(config_path, "r") as f:
    key = json.load(f)["api_key"]

client = genai.Client(api_key=key)

print("Testando gemini-2.0-flash...")
try:
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents="Responda apenas 'Conectado!'"
    )
    print(f"Sucesso: {response.text}")
except Exception as e:
    print(f"Erro com 2.0: {e}")
    
print("\nTestando gemini-1.5-flash...")
try:
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents="Responda apenas 'Conectado!'"
    )
    print(f"Sucesso: {response.text}")
except Exception as e:
    print(f"Erro com 1.5: {e}")
