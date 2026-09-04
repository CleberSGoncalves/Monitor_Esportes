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

CURRENT_VERSION = "2.2.5"

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
        try:
            exe_path = sys.executable
            exe_dir = os.path.dirname(exe_path)
            new_exe_path = os.path.join(exe_dir, "Monitor_Esportes_new.exe")
            bat_path = os.path.join(exe_dir, "update_launcher.bat")

            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "application/octet-stream,application/vnd.github.v3+json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            
            print(f"[AUTO-UPDATER] Baixando atualização via requests stream de {download_url}...")
            response = requests.get(download_url, headers=headers, stream=True, verify=False, timeout=90, allow_redirects=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 1024 * 1024 # 1 MB por bloco
            
            with open(new_exe_path, "wb") as f_out:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f_out.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            if total_size > 0:
                                percent = min(100, int(downloaded * 100 / total_size))
                                progress_callback(percent)
                            else:
                                mb = downloaded / (1024 * 1024)
                                progress_callback(f"{mb:.1f} MB")

            pid = os.getpid()
            old_exe_path = os.path.join(exe_dir, "Monitor_Esportes_old.exe")
            old_exe_name = os.path.basename(old_exe_path)
            exe_name = os.path.basename(exe_path)
            
            # Script Batch ultrarrobusto com desalocação forçada, confirmação de eliminação de processo e substituição garantida no Windows
            bat_content = f"""@echo off
setlocal enabledelayedexpansion
chcp 65001 > NUL

echo [AUTO-UPDATE] Encerrando processos e aguardando liberação do sistema...
timeout /t 3 /nobreak > NUL

:: 1. Encerrar processo principal pelo PID e por nome
if not "{pid}"=="" taskkill /F /PID {pid} > NUL 2>&1
taskkill /F /T /IM "{exe_name}" > NUL 2>&1
timeout /t 2 /nobreak > NUL

:: 2. Loop de verificação se o processo encerrou no Gerenciador de Tarefas
set /a pcount=0
:CHECK_PROCESS
tasklist /FI "IMAGENAME eq {exe_name}" 2>NUL | find /I "{exe_name}" > NUL
if "%ERRORLEVEL%"=="0" (
    set /a pcount+=1
    if !pcount! LSS 10 (
        taskkill /F /T /IM "{exe_name}" > NUL 2>&1
        timeout /t 1 /nobreak > NUL
        goto CHECK_PROCESS
    )
)

:: 3. Limpar backup antigo se existir
if exist "{old_exe_path}" del /f /q /a "{old_exe_path}" > NUL 2>&1

:: 4. Loop de insistência para remover/mover o executável original
set /a count=0
:RETRY_SWAP
set /a count+=1

move /y "{exe_path}" "{old_exe_path}" > NUL 2>&1
if not exist "{exe_path}" goto DO_REPLACE

ren "{exe_path}" "{old_exe_name}" > NUL 2>&1
if not exist "{exe_path}" goto DO_REPLACE

del /f /q /a "{exe_path}" > NUL 2>&1
if not exist "{exe_path}" goto DO_REPLACE

if !count! LSS 30 (
    timeout /t 1 /nobreak > NUL
    goto RETRY_SWAP
)

:DO_REPLACE
:: 5. Mover o novo executável baixado para o lugar do em produção
if exist "{new_exe_path}" (
    move /y "{new_exe_path}" "{exe_path}" > NUL 2>&1
    if not exist "{exe_path}" (
        copy /y "{new_exe_path}" "{exe_path}" > NUL 2>&1
        del /f /q /a "{new_exe_path}" > NUL 2>&1
    )
)

:: 6. Confirmar substituição e reiniciar a aplicação
if exist "{exe_path}" (
    echo [AUTO-UPDATE] Atualização concluída com sucesso! Iniciando aplicativo...
    if exist "{new_exe_path}" del /f /q /a "{new_exe_path}" > NUL 2>&1
    if exist "{old_exe_path}" del /f /q /a "{old_exe_path}" > NUL 2>&1
    timeout /t 1 /nobreak > NUL
    start "" /D "{exe_dir}" "{exe_path}"
) else (
    echo [AUTO-UPDATE] ERRO FATAL: Falha ao substituir executável. Restaurando backup...
    if exist "{old_exe_path}" (
        copy /y "{old_exe_path}" "{exe_path}" > NUL 2>&1
        start "" /D "{exe_dir}" "{exe_path}"
    ) else if exist "{new_exe_path}" (
        copy /y "{new_exe_path}" "{exe_path}" > NUL 2>&1
        start "" /D "{exe_dir}" "{exe_path}"
    )
)

timeout /t 2 /nobreak > NUL
(goto) 2>nul & del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            # Executar script batch em background desvinculado (CREATE_NO_WINDOW | DETACHED_PROCESS)
            DETACHED_PROCESS = 0x00000008
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                f'cmd.exe /c "{bat_path}"', 
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS, 
                close_fds=True,
                shell=True
            )
            
            # Encerramento limpo para liberar totalmente o arquivo do sistema
            time.sleep(0.5)
            os._exit(0)
            return True
        except Exception as e:
            print(f"[AUTO-UPDATER] Falha ao realizar atualização: {e}")
            raise e
