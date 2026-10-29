import sys, requests, json
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

client_id = SP_CONFIG["client_id"]
r = requests.get(f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{client_id}'", headers=headers)
print("SP query status:", r.status_code)
if r.status_code == 200:
    vals = r.json().get("value", [])
    if vals:
        sp = vals[0]
        print("SP found! ID:", sp.get("id"), "DisplayName:", sp.get("displayName"))
    else:
        print("SP not found in tenant.")
else:
    print("SP query error:", r.text)
