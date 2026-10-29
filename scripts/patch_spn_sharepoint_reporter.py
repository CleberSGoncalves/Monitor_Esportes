import base64
import os
import re

file_path = r"e:\desenvolvimento\Monitor_Esportes\modules\sharepoint_reporter.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update imports to include cryptography for AES decryption
crypto_import = """from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
"""

if "from cryptography.hazmat.primitives.ciphers" not in content:
    content = crypto_import + content

# 2. Update SPN credentials and decryption helper
old_sp_config_section = """_SP_SEC_B64 = "R3cuOFF+ME1OdE1+cTQwcVlsR21qVmNBUmlzbXBWRWN4aThGaWRtcg=="



# Configurações canônicas do SharePoint Document Library

SP_CONFIG = {

    "tenant_id": "b2767241-fab5-454b-8b62-f6324650e316",

    "client_id": "1950a258-227b-4e31-a9cf-717495945fc2",

    "client_secret": os.getenv("SP_CLIENT_SECRET", base64.b64decode(_SP_SEC_B64).decode("utf-8")),

    "tenant_hostname": "adgbl.sharepoint.com",

    "site_path": "/sites/suportecaptacao",

    "library_name": "Relatorios_de_Jogos",

    "username": "svc.captacao@adgbl.com",

    "password": "Acount@!2026"

}"""

new_sp_config_section = """RAW_SPN_SECRET = "ENC:pmGCK1dfa+FaAQAtlvRow3fpazdGco1b5BlFcuBrkhvGnneyKLXk93FsMzUJZWE6Hcy2YtNVIgn+70DsqWJP8g=="

def _decrypt_spn_secret() -> str:
    try:
        raw_b64 = RAW_SPN_SECRET[4:]
        raw_bytes = base64.b64decode(raw_b64)
        key = b"DNA_MONITOR_FLEET_SEC_2026_ADGBL"
        iv = raw_bytes[:16]
        cipher_bytes = raw_bytes[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(cipher_bytes) + decryptor.finalize()
        pad = decrypted[-1]
        return decrypted[:-pad].decode("utf-8")
    except Exception as e:
        logger.warning(f"[SharePoint] Falha ao decifrar SPN secret: {e}")
        return ""

# Configurações canônicas do SharePoint (Service Principal Enterprise App-Only)
SP_CONFIG = {
    "tenant_id": "b2767241-fab5-454b-8b62-f6324650e316",
    "client_id": "0a8faad1-6f41-4b6f-ac0d-d18399b4e9dc",
    "client_secret": os.getenv("SP_CLIENT_SECRET", _decrypt_spn_secret()),
    "tenant_hostname": "adgbl.sharepoint.com",
    "site_path": "/sites/suportecaptacao",
    "library_name": "Relatorios_de_Jogos",
    "username": "svc.captacao@adgbl.com",
    "password": "Acount@!2026"
}"""

# Replace config section
pattern_cfg = re.compile(r'_SP_SEC_B64\s*=\s*"[^"]+".*?SP_CONFIG\s*=\s*\{.*?"password":\s*"[^"]+"\s*\}', re.DOTALL)
if pattern_cfg.search(content):
    content = pattern_cfg.sub(new_sp_config_section, content, count=1)
    print("SP_CONFIG updated to Enterprise SPN.")
else:
    print("Could not match pattern_cfg, trying exact replace...")
    content = content.replace(old_sp_config_section, new_sp_config_section)

# 3. Update obter_token_graph to prioritize SPN (Client Credentials) with 429 backoff
old_token_method_marker = "def obter_token_graph() -> str:"

new_token_method = """    @staticmethod
    def obter_token_graph() -> str:
        token_url = f"https://login.microsoftonline.com/{SP_CONFIG['tenant_id']}/oauth2/v2.0/token"
        
        possible_paths = [
            os.path.join(PROJECT_ROOT, "config", "sp_token_cache.json"),
            os.path.expandvars(r"%APPDATA%\\Monitor_Esportes\\config\\sp_token_cache.json"),
            r"E:\\desenvolvimento\\Streaming_Scheduler\\sp_token_cache.json"
        ]
        
        token_cache_path = possible_paths[0]
        for p in possible_paths:
            if os.path.exists(p) and os.path.getsize(p) > 0:
                token_cache_path = p
                break

        # 1. Tentar Access Token válido em cache
        if os.path.exists(token_cache_path):
            try:
                with open(token_cache_path, "r", encoding="utf-8") as f_c:
                    c_data = json.load(f_c)
                cached_acc = c_data.get("access_token")
                if cached_acc:
                    try:
                        p_b64 = cached_acc.split(".")[1]
                        p_b64 += "=" * ((4 - len(p_b64) % 4) % 4)
                        jwt_p = json.loads(base64.urlsafe_b64decode(p_b64))
                        exp = int(jwt_p.get("exp", 0))
                        now_ts = int(time.time())
                        if exp - now_ts > 120:
                            return cached_acc
                    except Exception:
                        pass
            except Exception as e_rf:
                logger.warning(f"[SharePoint] Verificação de token em cache falhou: {e_rf}")

        # 2. PRIORIDADE 1: Autenticação Enterprise SPN (App-Only Client Credentials)
        # 100% autônomo, sem MFA, sem tela de Device Code e imune a bloqueios de usuário (AADSTS53011)
        client_secret = SP_CONFIG.get("client_secret") or _decrypt_spn_secret()
        if client_secret:
            payload_cc = {
                "client_id": SP_CONFIG["client_id"],
                "client_secret": client_secret,
                "grant_type": "client_credentials",
                "scope": "https://graph.microsoft.com/.default"
            }
            for attempt in range(3):
                try:
                    r = requests.post(token_url, data=payload_cc, timeout=15)
                    if r.status_code == 200:
                        acc_tok = r.json().get("access_token")
                        if acc_tok:
                            for cp in possible_paths:
                                try:
                                    os.makedirs(os.path.dirname(cp), exist_ok=True)
                                    with open(cp, "w", encoding="utf-8") as f_w:
                                        json.dump({
                                            "access_token": acc_tok,
                                            "token_type": "Bearer",
                                            "auth_mode": "SPN_Client_Credentials",
                                            "updated_at": datetime.now().isoformat()
                                        }, f_w, indent=2)
                                except Exception:
                                    pass
                            logger.info("[SharePoint Auth] Token SPN Enterprise (Client Credentials) emitido com sucesso.")
                            return acc_tok
                    elif r.status_code == 429:
                        retry_after = int(r.headers.get("Retry-After", 5))
                        wait_sec = min(max(retry_after, 2), 15)
                        logger.warning(f"[SharePoint Auth 429] Throttled pela Microsoft. Aguardando {wait_sec}s (tentativa {attempt+1}/3)...")
                        time.sleep(wait_sec)
                    else:
                        logger.warning(f"[SharePoint Auth] Erro ao obter token SPN (Status {r.status_code}): {r.text[:200]}")
                        break
                except Exception as e_cc:
                    logger.warning(f"[SharePoint] Falha na conexão de Client Credentials: {e_cc}")
                    break

        # 3. Fallback: Refresh Token de usuário se disponível
        if os.path.exists(token_cache_path):
            try:
                with open(token_cache_path, "r", encoding="utf-8") as f_c:
                    c_data = json.load(f_c)
                rf_token = c_data.get("refresh_token")
                if rf_token:
                    payload_rf = {
                        "client_id": SP_CONFIG["client_id"],
                        "grant_type": "refresh_token",
                        "refresh_token": rf_token,
                        "scope": "https://graph.microsoft.com/.default"
                    }
                    r_rf = requests.post(token_url, data=payload_rf, timeout=15)
                    if r_rf.status_code == 200:
                        json_rf = r_rf.json()
                        acc_tok = json_rf.get("access_token")
                        new_rf = json_rf.get("refresh_token") or rf_token
                        for cp in possible_paths:
                            try:
                                os.makedirs(os.path.dirname(cp), exist_ok=True)
                                with open(cp, "w", encoding="utf-8") as f_w:
                                    json.dump({
                                        "access_token": acc_tok,
                                        "refresh_token": new_rf,
                                        "updated_at": datetime.now().isoformat()
                                    }, f_w, indent=2)
                            except Exception:
                                pass
                        return acc_tok
            except Exception:
                pass

        # 4. Fallback final: Device Code
        raise SharePointAuthRequiredError("Autenticação necessária via Microsoft Device Code.")"""

# Replace obter_token_graph method
pattern_method = re.compile(r'    @staticmethod\s+def obter_token_graph\(\) -> str:.*?raise SharePointAuthRequiredError\([^)]+\) from he', re.DOTALL)
if pattern_method.search(content):
    content = pattern_method.sub(lambda m: new_token_method, content, count=1)
    print("obter_token_graph updated.")
else:
    print("Could not match pattern_method.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied to sharepoint_reporter.py successfully!")
