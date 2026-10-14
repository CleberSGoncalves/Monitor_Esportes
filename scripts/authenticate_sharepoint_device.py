import os
import sys
import requests
import json
import time
import subprocess
import webbrowser
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = r"e:\desenvolvimento\Monitor_Esportes"
sys.path.insert(0, PROJECT_ROOT)

from modules.sharepoint_reporter import SP_CONFIG, SharePointReporter

tenant_id = SP_CONFIG["tenant_id"]
client_id = SP_CONFIG["client_id"]

device_code_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

payload_device = {
    "client_id": client_id,
    "scope": "https://graph.microsoft.com/.default offline_access"
}

r_device = requests.post(device_code_url, data=payload_device)
if r_device.status_code != 200:
    print(f"❌ Erro ao solicitar Device Code ({r_device.status_code}): {r_device.text}")
    sys.exit(1)

dev_data = r_device.json()
user_code = dev_data.get("user_code")
device_code = dev_data.get("device_code")
verification_uri = dev_data.get("verification_uri", "https://login.microsoft.com/device")
interval = dev_data.get("interval", 5)
expires_in = dev_data.get("expires_in", 900)

# Copiar código para a área de transferência do Windows via PowerShell
try:
    subprocess.run(f'powershell -command "Set-Clipboard -Value \'{user_code}\'"', shell=True)
    clip_msg = "(Código copiado para a área de transferência! Pressione Ctrl+V no navegador)"
except Exception:
    clip_msg = ""

print("\n" + "="*75)
print("🔑 AUTENTICAÇÃO DO SHAREPOINT VIA DEVICE CODE")
print("="*75)
print(f"1. Acessando no navegador: {verification_uri}")
print(f"2. Código de Acesso: {user_code} {clip_msg}")
print(f"3. Conta de Login: {SP_CONFIG['username']}")
print("="*75)
print(f"Aguardando confirmação do login no navegador (expira em {expires_in // 60} minutos)...")

# Abrir automaticamente o navegador no link oficial de dispositivo
try:
    webbrowser.open(verification_uri)
except Exception:
    pass

payload_poll = {
    "client_id": client_id,
    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    "device_code": device_code
}

start_time = time.time()
authenticated = False
tokens_data = None

while time.time() - start_time < expires_in:
    time.sleep(interval)
    r_poll = requests.post(token_url, data=payload_poll)
    poll_res = r_poll.json()
    
    if r_poll.status_code == 200:
        access_token = poll_res.get("access_token")
        refresh_token = poll_res.get("refresh_token")
        tokens_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "updated_at": datetime.now().isoformat()
        }
        authenticated = True
        break
    else:
        err = poll_res.get("error", "")
        if err not in ("authorization_pending", "slow_down"):
            print(f"\n❌ Erro na autenticação: {poll_res.get('error_description', err)}")
            sys.exit(1)
        print(".", end="", flush=True)

if not authenticated or not tokens_data:
    print("\n❌ Tempo limite expirado. Execute o script novamente.")
    sys.exit(1)

# Salvar token em múltiplos locais de cache para redundância
cache_paths = [
    os.path.join(PROJECT_ROOT, "config", "sp_token_cache.json"),
    os.path.expandvars(r"%APPDATA%\Monitor_Esportes\config\sp_token_cache.json")
]

for cp in cache_paths:
    try:
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        with open(cp, "w", encoding="utf-8") as f:
            json.dump(tokens_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Token armazenado em cache: {cp}")
    except Exception as e_w:
        print(f"⚠️ Erro ao salvar cache em {cp}: {e_w}")

print("\n🎉 Autenticação do SharePoint concluída com sucesso!")
print("🚀 Sincronizando relatórios pendentes para a Document Library 'Relatorios_de_Jogos'...\n")

# Disparar envio automático de relatórios PDF locais para o SharePoint
reports_dir = os.path.join(PROJECT_ROOT, "reports")
if os.path.exists(reports_dir):
    pdf_files = [os.path.join(reports_dir, f) for f in os.listdir(reports_dir) if f.endswith(".pdf")]
    uploaded_count = 0
    for pdf in pdf_files:
        filename = os.path.basename(pdf)
        print(f"📤 Enviando {filename}...")
        try:
            # Tentar ler metadados do JSON correspondente se existir
            json_path = pdf.replace(".pdf", ".json")
            match_name = "Relatório Auditoria"
            comp_name = "Brasileiro Serie A"
            plat_name = "Amazon Prime"
            date_iso = None
            
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f_j:
                    jdata = json.load(f_j)
                    res_list = jdata.get("expert_results", [])
                    if res_list:
                        first = res_list[0]
                        match_name = first.get("match_display", match_name)
                        comp_name = first.get("competition", comp_name)
                        plat_name = first.get("platform", plat_name)
                        d_str = first.get("date")
                        t_str = first.get("time")
                        if d_str:
                            date_iso = SharePointReporter.format_iso_datetime(d_str, t_str)

            ok = SharePointReporter.sync_pdf_to_sharepoint(
                pdf_path=pdf,
                partida=match_name,
                campeonato=comp_name,
                plataforma=plat_name,
                data_hora_iso=date_iso,
                confianca="99.0%"
            )
            if ok:
                uploaded_count += 1
                print(f"   ✅ {filename} publicado com sucesso!")
            else:
                print(f"   ⚠️ Falha ao publicar {filename}")
        except Exception as ex_up:
            print(f"   ❌ Erro ao enviar {filename}: {ex_up}")
    
    print(f"\n🎉 {uploaded_count}/{len(pdf_files)} relatórios publicados no SharePoint com sucesso!")
