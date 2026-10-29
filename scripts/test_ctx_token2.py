import sys, json, os, requests
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG, PROJECT_ROOT
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.token_response import TokenResponse

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
if r.status_code == 200:
    data = r.json()
    tok_res = TokenResponse(access_token=data.get("access_token"), token_type=data.get("token_type", "Bearer"))
    site_url = "https://adgbl.sharepoint.com/sites/suportecaptacao"
    try:
        ctx = ClientContext(site_url).with_access_token(lambda: tok_res)
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()
        print("Sucesso! Site title:", web.properties.get("Title"))
    except Exception as e:
        print("Falha:", e)
