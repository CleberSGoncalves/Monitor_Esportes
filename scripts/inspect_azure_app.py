import sys, requests, json
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SharePointReporter, SP_CONFIG

token = SharePointReporter.obter_token_graph()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 1. Get Application
client_id = SP_CONFIG["client_id"]
r = requests.get(f"https://graph.microsoft.com/v1.0/applications(appId='{client_id}')", headers=headers)
print("Application status:", r.status_code)
if r.status_code == 200:
    app_data = r.json()
    print("App Name:", app_data.get("displayName"))
    print("Required Resource Access:")
    for res in app_data.get("requiredResourceAccess", []):
        print("  ResourceAppId:", res.get("resourceAppId"))
        for acc in res.get("resourceAccess", []):
            print("    ID:", acc.get("id"), "Type:", acc.get("type"))
else:
    print("App query error:", r.text)

# 2. Get Service Principal
r_sp = requests.get(f"https://graph.microsoft.com/v1.0/servicePrincipals(appId='{client_id}')", headers=headers)
print("ServicePrincipal status:", r_sp.status_code)
if r_sp.status_code == 200:
    sp_data = r_sp.json()
    sp_id = sp_data.get("id")
    print("SP ID:", sp_id)
    # Check oauth2PermissionGrants
    r_grants = requests.get(f"https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/oauth2PermissionGrants", headers=headers)
    print("Grants status:", r_grants.status_code)
    for g in r_grants.json().get("value", []):
        print(f"Grant: scope={g.get('scope')} consentType={g.get('consentType')} principalId={g.get('principalId')}")
