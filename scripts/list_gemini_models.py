import google.generativeai as genai
import json

with open(r"e:\desenvolvimento\Monitor_Esportes\config\google_ai.json", "r") as f:
    key = json.load(f)["api_key"]

genai.configure(api_key=key)

print("Listando modelos disponíveis:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"- {m.name}")
