with open("modules/sharepoint_reporter.py", "r", encoding="utf-8") as f:
    text = f.read()

start_marker = "    @staticmethod\n\n    def obter_token_graph() -> str:"
end_marker = "    @staticmethod\n\n    def normalizar_campeonato(comp: str) -> str:"

clean_obter_token = """    @staticmethod
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
                        if exp - now_ts > 60:
                            return cached_acc
                    except Exception:
                        pass

                # Se está para expirar, tenta renovar via Refresh Token
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
                        # Se refresh falhou temporariamente, mas access token ainda não venceu
                        try:
                            if exp - now_ts > 0:
                                return cached_acc
                        except Exception:
                            pass
            except Exception as e_rf:
                logger.warning(f"[SharePoint] Verificação de token em cache falhou: {e_rf}")

        # 2. Tentar Client Credentials
        if SP_CONFIG.get("client_secret"):
            payload_cc = {
                "client_id": SP_CONFIG["client_id"],
                "client_secret": SP_CONFIG["client_secret"],
                "grant_type": "client_credentials",
                "scope": "https://graph.microsoft.com/.default"
            }
            try:
                r = requests.post(token_url, data=payload_cc, timeout=15)
                if r.status_code == 200:
                    return r.json()["access_token"]
            except Exception as e:
                logger.warning(f"[SharePoint] Falha no login via Client Credentials: {e}")

        # 3. Fallback para Password Grant
        payload_pass = {
            "client_id": SP_CONFIG["client_id"],
            "username": SP_CONFIG["username"],
            "password": SP_CONFIG["password"],
            "grant_type": "password",
            "scope": "https://graph.microsoft.com/.default"
        }
        try:
            r = requests.post(token_url, data=payload_pass, timeout=15)
            r.raise_for_status()
            res_json = r.json()
            if "refresh_token" in res_json:
                for cp in possible_paths:
                    try:
                        os.makedirs(os.path.dirname(cp), exist_ok=True)
                        with open(cp, "w", encoding="utf-8") as f_w:
                            json.dump({
                                "access_token": res_json["access_token"],
                                "refresh_token": res_json["refresh_token"],
                                "updated_at": datetime.now().isoformat()
                            }, f_w, indent=2)
                    except Exception:
                        pass
            return res_json["access_token"]
        except requests.HTTPError as he:
            logger.error("[SharePoint Auth] O login por senha foi bloqueado pelas políticas de segurança da Microsoft (AADSTS53011). Autenticação via Device Code necessária (scripts/authenticate_sharepoint_device.py).")
            raise he

"""

idx_start = text.find(start_marker)
idx_end = text.find(end_marker)

new_text = text[:idx_start] + clean_obter_token + text[idx_end:]

with open("modules/sharepoint_reporter.py", "w", encoding="utf-8") as f:
    f.write(new_text)

print("obter_token_graph successfully replaced!")
