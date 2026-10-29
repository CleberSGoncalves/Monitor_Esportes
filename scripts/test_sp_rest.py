import sys, requests, json, os
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG, PROJECT_ROOT

token_cache_path = os.path.join(PROJECT_ROOT, "config", "sp_token_cache.json")
with open(token_cache_path, "r", encoding="utf-8") as f:
    c_data = json.load(f)
rf_token = c_data.get("refresh_token")

token_url = f"https://login.microsoftonline.com/{SP_CONFIG['tenant_id']}/oauth2/v2.0/token"
payload = {
    "client_id": SP_CONFIG["client_id"],
    "grant_type": "refresh_token",
    "refresh_token": rf_token,
    "scope": "https://adgbl.sharepoint.com/.default"
}
r = requests.post(token_url, data=payload)
print("SharePoint token status:", r.status_code)
if r.status_code == 200:
    sp_token = r.json()["access_token"]
    print("Token obtido com sucesso!")
    sp_headers = {
        "Authorization": f"Bearer {sp_token}",
        "Accept": "application/json;odata=verbose",
        "Content-Type": "application/json;odata=verbose"
    }
    r_test = requests.get("https://adgbl.sharepoint.com/sites/suportecaptacao/_api/web/lists/getbytitle('Relatorios_de_Jogos_NBA')", headers=sp_headers)
    print("List test status:", r_test.status_code)
    print("List test resp:", r_test.text[:300])
else:
    print("Erro token:", r.text)
