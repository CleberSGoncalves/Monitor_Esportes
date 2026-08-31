"""
Modulo de Atualização Automática (Auto-Updater) para o Monitor de Esportes.
Verifica novas versões disponibilizadas e realiza o auto-deploy e reinicialização.
"""

import os
import sys
import json
import time
import urllib.request
import subprocess

CURRENT_VERSION = "1.6.7"

class AutoUpdater:
    def __init__(self, version_url: str = "https://raw.githubusercontent.com/CleberSGoncalves/Monitor_Esportes/main/version.json"):
        self.version_url = version_url
        self.current_version = CURRENT_VERSION

    def check_for_update(self):
        """
        Verifica se há uma versão mais recente disponível na URL remota.
        Retorna (has_update, remote_version, download_url, changelog)
        """
        try:
            req = urllib.request.Request(self.version_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    remote_ver = data.get("version", "1.0.0")
                    download_url = data.get("download_url", "")
                    changelog = data.get("changelog", "Melhorias gerais e correções de estabilidade.")
                    
                    if self._is_newer(remote_ver, self.current_version):
                        return True, remote_ver, download_url, changelog
        except Exception as e:
            print(f"[AUTO-UPDATER] Erro ao verificar atualizações: {e}")
        return False, self.current_version, "", ""

    def _is_newer(self, remote_ver: str, local_ver: str) -> bool:
        try:
            r_parts = [int(x) for x in remote_ver.replace("v", "").split(".")]
            l_parts = [int(x) for x in local_ver.replace("v", "").split(".")]
            return r_parts > l_parts
        except:
            return False

    def perform_update_and_restart(self, download_url: str, progress_callback=None):
        """
        Baixa o novo executável, cria o script de troca rápida em background e reinicia o app.
        """
        # Descomente para testes em ambiente de desenvolvimento se necessário, mas mantemos o skip por padrão
        # if not getattr(sys, 'frozen', False):
        #     print("[AUTO-UPDATER] Atualização automática desativada em modo de código fonte (desenvolvimento).")
        #     return False

        try:
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)
            new_exe_path = os.path.join(exe_dir, "Monitor_Esportes_new.exe")
            bat_path = os.path.join(exe_dir, "update_launcher.bat")

            print(f"[AUTO-UPDATER] Baixando atualização de {download_url}...")
            
            if progress_callback:
                def reporthook(block_count, block_size, total_size):
                    if total_size > 0:
                        downloaded = block_count * block_size
                        percent = min(100, int(downloaded * 100 / total_size))
                        progress_callback(percent)
                    else:
                        downloaded_mb = (block_count * block_size) / (1024 * 1024)
                        progress_callback(f"{downloaded_mb:.1f} MB")
                urllib.request.urlretrieve(download_url, new_exe_path, reporthook)
            else:
                urllib.request.urlretrieve(download_url, new_exe_path)

            # Criar script batch para substituir e reiniciar
            bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
move /y "{new_exe_path}" "{exe_path}"
start "" "{exe_path}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            # Executar script batch em background sem janela visível
            subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=0x08000000)
            sys.exit(0)
            return True
        except Exception as e:
            print(f"[AUTO-UPDATER] Falha ao realizar atualização: {e}")
            raise e
