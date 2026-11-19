import sys
import os
import requests

sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG

token_url = f"https://login.microsoftonline.com/{SP_CONFIG['tenant_id']}/oauth2/v2.0/token"
payload = {
    "client_id": SP_CONFIG["client_id"],
    "client_secret": SP_CONFIG["client_secret"],
    "grant_type": "client_credentials",
    "scope": "https://adgbl.sharepoint.com/.default"
}

r = requests.post(token_url, data=payload)
print("SP Token status:", r.status_code)
if r.status_code == 200:
    token = r.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json;odata=nometadata"
    }
    
    # 1. Tentar pegar o arquivo da página HomePage.aspx
    page_url = "https://adgbl.sharepoint.com/sites/suportecaptacao/_api/web/GetFileByServerRelativeUrl('/sites/suportecaptacao/SitePages/HomePage.aspx')/$value"
    r_page = requests.get(page_url, headers={"Authorization": f"Bearer {token}"})
    print("Page $value status:", r_page.status_code, "Length:", len(r_page.text))
    if r_page.status_code == 200:
        with open("config/sharepoint_homepage_raw.aspx", "w", encoding="utf-8") as f:
            f.write(r_page.text)
        print("Salvo em config/sharepoint_homepage_raw.aspx")
    
    # 2. Tentar pegar as listas do site para inspecionar
    lists_url = "https://adgbl.sharepoint.com/sites/suportecaptacao/_api/web/lists?$select=Title,ItemCount,DefaultViewUrl"
    r_lists = requests.get(lists_url, headers=headers)
    print("Lists status:", r_lists.status_code)
    if r_lists.status_code == 200:
        lists_data = r_lists.json().get("value", [])
        print("Listas encontradas:")
        for l in lists_data:
            print(f" - {l.get('Title')} (Itens: {l.get('ItemCount')}) -> {l.get('DefaultViewUrl')}")
else:
    print("Erro token SP:", r.text)
