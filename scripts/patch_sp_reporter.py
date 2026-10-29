def main():
    path = r"modules/sharepoint_reporter.py"
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()

    old_target = """        except requests.HTTPError as he:
            logger.error("[SharePoint Auth] O login por senha foi bloqueado pelas políticas de segurança da Microsoft (AADSTS53011). Autenticação via Device Code necessária (scripts/authenticate_sharepoint_device.py).")
            raise he"""

    new_target = """        except requests.HTTPError as he:
            logger.error("[SharePoint Auth] O login por senha foi bloqueado pelas políticas de segurança da Microsoft (AADSTS53011). Autenticação via Device Code necessária.")
            raise SharePointAuthRequiredError("Sessão do SharePoint expirada. É necessária a autenticação via Microsoft Device Code.") from he"""

    if old_target in c:
        c = c.replace(old_target, new_target, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print("Updated exception handling in sharepoint_reporter.py")
    else:
        print("Target not found")

if __name__ == "__main__":
    main()
