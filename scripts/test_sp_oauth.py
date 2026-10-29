import sys, requests, json, os
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG, PROJECT_ROOT

token_cache_path = os.path.join(PROJECT_ROOT, "config", "sp_token_cache.json")
with open(token_cache_path, "r", encoding="utf-8") as f:
    c_data = json.load(f)
rf_token = c_data.get("refresh_token")

token_url = f"https://login.microsoftonline.com/{SP_CONFIG['tenant_id']}/oauth2/v2.0/token"

for scp in [
    "https://adgbl.sharepoint.com/AllSites.FullControl offline_access",
    "https://adgbl.sharepoint.com/AllSites.Manage offline_access",
    "https://adgbl.sharepoint.com/AllSites.Write offline_access",
    "https://adgbl.sharepoint.com/.default"
]:
    payload = {
        "client_id": SP_CONFIG["client_id"],
        "grant_type": "refresh_token",
        "refresh_token": rf_token,
        "scope": scp
    }
    r = requests.post(token_url, data=payload)
    print(f"Scope: {scp} -> Status: {r.status_code}")
    if r.status_code == 200:
        sp_token = r.json()["access_token"]
        import base64
        parts = sp_token.split(".")
        p = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8"))
        print(f"   aud: {p.get('aud')}, scp: {p.get('scp')}")
        
        # Test request
        headers = {
            "Authorization": f"Bearer {sp_token}",
            "Accept": "application/json;odata=nometadata"
        }
        r_api = requests.get("https://adgbl.sharepoint.com/sites/suportecaptacao/_api/web/title", headers=headers)
        print(f"   API test: {r_api.status_code} {r_api.text[:100]}")
