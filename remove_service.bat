@echo off
set NSSM="E:\desenvolvimento\MyMovements\nssm\nssm-2.24\win64\nssm.exe"
set SERVICE_NAME="Monitor Esporte_Web"

echo [REMOVENDO SERVICO] %SERVICE_NAME%...
%NSSM% stop %SERVICE_NAME%
%NSSM% remove %SERVICE_NAME% confirm

echo [OK] Servico removido.
pause
