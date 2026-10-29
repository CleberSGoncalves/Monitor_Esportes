import sys, json, requests, os
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG, PROJECT_ROOT

token_cache_path = os.path.join(PROJECT_ROOT, "config", "sp_token_cache.json")
with open(token_cache_path, "r", encoding="utf-8") as f:
    c_data = json.load(f)
rf_token = c_data.get("refresh_token")

token_url = f"https://login.microsoftonline.com/{SP_CONFIG['tenant_id']}/oauth2/v2.0/token"

# Try different scopes with refresh token
for scope in [
    "https://graph.microsoft.com/Sites.Manage.All offline_access",
    "https://graph.microsoft.com/Sites.FullControl.All offline_access",
    "https://graph.microsoft.com/Sites.ReadWrite.All offline_access",
    "https://graph.microsoft.com/.default"
]:
    payload = {
        "client_id": SP_CONFIG["client_id"],
        "grant_type": "refresh_token",
        "refresh_token": rf_token,
        "scope": scope
    }
    r = requests.post(token_url, data=payload)
    print(f"Scope '{scope}' -> Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   Body: {r.text[:300]}")
    if r.status_code == 200:
        tok = r.json()["access_token"]
        import base64
        parts = tok.split(".")
        p = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8"))
        print(f"   Granted scp: {p.get('scp')}")
