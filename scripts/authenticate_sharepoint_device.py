import os
import sys
import requests
import json
import time
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")

from modules.sharepoint_reporter import SP_CONFIG

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

print("\n" + "="*70)
print("🔑 AUTENTICAÇÃO DO SHAREPOINT VIA DEVICE CODE")
print("="*70)
print(f"1. Abra o navegador e acesse: {verification_uri}")
print(f"2. Digite o código de acesso: {user_code}")
print(f"3. Faça login com a conta oficial: {SP_CONFIG['username']}")
print("="*70)
print(f"Aguardando confirmação do login (expira em {expires_in // 60} minutos)...")

payload_poll = {
    "client_id": client_id,
    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    "device_code": device_code
}

start_time = time.time()
while time.time() - start_time < expires_in:
    time.sleep(interval)
    r_poll = requests.post(token_url, data=payload_poll)
    poll_res = r_poll.json()
    
    if r_poll.status_code == 200:
        access_token = poll_res.get("access_token")
        refresh_token = poll_res.get("refresh_token")
        
        cache_path = os.path.join(r"e:\desenvolvimento\Monitor_Esportes", "config", "sp_token_cache.json")
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        
        with open(cache_path, "w", encoding="utf-8") as f_out:
            json.dump({
                "access_token": access_token,
                "refresh_token": refresh_token,
                "updated_at": datetime.now().isoformat()
            }, f_out, indent=2)
            
        print("\n🎉 AUTENTICAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"Token de atualização (refresh_token) salvo em: {cache_path}")
        print("O Monitor de Esportes agora publicará relatórios no SharePoint automaticamente!")
        sys.exit(0)
    
    err = poll_res.get("error")
    if err == "authorization_pending":
        print(".", end="", flush=True)
        continue
    elif err == "slow_down":
        interval += 5
        continue
    elif err == "expired_token":
        print("\n❌ Tempo limite expirado. Execute o script novamente.")
        sys.exit(1)
    else:
        print(f"\n❌ Erro ao aguardar autenticação: {err} - {poll_res.get('error_description')}")
        sys.exit(1)
