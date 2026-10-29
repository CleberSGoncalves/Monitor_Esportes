import os
import sys

with open("modules/sharepoint_reporter.py", "r", encoding="utf-8") as f:
    code = f.read()

target = """        # 1. Tentar Refresh Token em cache
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
            except Exception as e_rf:
                logger.warning(f"[SharePoint] Renovação por refresh_token falhou: {e_rf}")"""

replacement = """        # 1. Tentar Access Token válido em cache ou renovar por Refresh Token
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
                        if exp - now_ts > 120:  # Token válido por pelo menos mais 2 minutos
                            return cached_acc
                    except Exception:
                        pass

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
                    elif cached_acc:
                        # Se a renovação falhou por política mas o token ainda não expirou completamente
                        try:
                            if exp - now_ts > 0:
                                return cached_acc
                        except Exception:
                            pass
            except Exception as e_rf:
                logger.warning(f"[SharePoint] Verificação de token em cache falhou: {e_rf}")"""

code_n = code.replace("\r\n", "\n")
target_n = target.replace("\r\n", "\n")
replacement_n = replacement.replace("\r\n", "\n")

assert target_n in code_n, "target not found in sharepoint_reporter.py"
code_n = code_n.replace(target_n, replacement_n, 1)

with open("modules/sharepoint_reporter.py", "w", encoding="utf-8") as f:
    f.write(code_n.replace("\n", "\r\n"))

print("sharepoint_reporter.py patched successfully!")
