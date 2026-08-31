from google import genai
import json
import os

config_path = r"e:\desenvolvimento\Monitor_Esportes\config\google_ai.json"
with open(config_path, "r") as f:
    key = json.load(f)["api_key"]

client = genai.Client(api_key=key)

print("Listando modelos FLASH disponíveis:")
try:
    models = list(client.models.list())
    for m in models:
        name = getattr(m, 'name', 'N/A')
        if "flash" in name.lower():
            print(f"ID: {name} | Display: {getattr(m, 'display_name', 'N/A')} | Actions: {getattr(m, 'supported_actions', [])}")
except Exception as e:
    print(f"Erro ao listar modelos: {e}")
