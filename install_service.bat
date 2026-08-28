@echo off
set NSSM="E:\desenvolvimento\MyMovements\nssm\nssm-2.24\win64\nssm.exe"
set SERVICE_NAME="Monitor Esporte_Web"
set PYTHON_EXE="C:\Python312\python.exe"
set SCRIPT_PATH="E:\desenvolvimento\Monitor_Esportes\headless_server.py"
set WORK_DIR="E:\desenvolvimento\Monitor_Esportes"

echo [INSTALANDO SERVICO] %SERVICE_NAME%...

%NSSM% stop %SERVICE_NAME%
%NSSM% remove %SERVICE_NAME% confirm

%NSSM% install %SERVICE_NAME% %PYTHON_EXE% %SCRIPT_PATH%
%NSSM% set %SERVICE_NAME% AppDirectory %WORK_DIR%
%NSSM% set %SERVICE_NAME% DisplayName "Monitor Esporte Web Service"
%NSSM% set %SERVICE_NAME% Description "Servico de monitoramento de eventos esportivos com painel Web"
%NSSM% set %SERVICE_NAME% Start SERVICE_AUTO_START

echo.
echo [OK] Servico instalado com sucesso.
echo Para iniciar: nssm start %SERVICE_NAME%
pause
