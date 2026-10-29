import sys, json, base64, requests
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG

token_url = f"https://login.microsoftonline.com/{SP_CONFIG['tenant_id']}/oauth2/v2.0/token"
payload_cc = {
    "client_id": SP_CONFIG["client_id"],
    "client_secret": SP_CONFIG["client_secret"],
    "grant_type": "client_credentials",
    "scope": "https://graph.microsoft.com/.default"
}
r = requests.post(token_url, data=payload_cc)
print("CC Status:", r.status_code)
print("CC Body:", r.text)
if r.status_code == 200:
    tok = r.json()["access_token"]
    parts = tok.split(".")
    p = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8"))
    print("CC Roles:", p.get("roles"))
    
    # Test column creation with CC token!
    site_id = "adgbl.sharepoint.com,a3e49747-9bb6-4c93-9930-dda26c8d1050,34c8fe55-2cfe-4efc-8ce0-2958fd775ee0"
    nba_list_id = "fa332a4b-5c46-433f-953d-e0534a9f5ecd"
    cc_headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    col_test = {
        "name": "Partida",
        "displayName": "Partida",
        "text": {"maxLength": 255}
    }
    r_col = requests.post(f"https://graph.microsoft.com/v1.0/sites/{site_id}/lists/{nba_list_id}/columns", headers=cc_headers, json=col_test)
    print("CC create column status:", r_col.status_code)
    print("CC create column response:", r_col.text)
