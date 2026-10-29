import requests, json, sys
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG
device_code_url = f"https://login.microsoftonline.com/{SP_CONFIG['tenant_id']}/oauth2/v2.0/devicecode"
payload = {
    "client_id": SP_CONFIG["client_id"],
    "scope": "https://graph.microsoft.com/.default offline_access"
}
r = requests.post(device_code_url, data=payload)
print("Status:", r.status_code)
d = r.json()
print("user_code:", d.get("user_code"))
print("verification_uri:", d.get("verification_uri"))
