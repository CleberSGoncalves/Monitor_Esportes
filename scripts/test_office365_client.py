import sys
sys.path.insert(0, r"e:\desenvolvimento\Monitor_Esportes")
from modules.sharepoint_reporter import SP_CONFIG
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.user_credential import UserCredential

site_url = "https://adgbl.sharepoint.com/sites/suportecaptacao"
user = SP_CONFIG["username"]
pwd = SP_CONFIG["password"]

try:
    ctx = ClientContext(site_url).with_user_credentials(user, pwd)
    web = ctx.web
    ctx.load(web)
    ctx.execute_query()
    print("Sucesso ao conectar com UserCredential! Site title:", web.properties.get("Title"))
except Exception as e:
    print("Falha UserCredential:", e)
