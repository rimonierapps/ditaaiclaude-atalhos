@echo off
rem DitaAiClaude (atalhos) - inicia o servidor do PC (Windows)
cd /d "%~dp0"
netsh advfirewall firewall show rule name="DitaAiClaude" >nul 2>&1
if errorlevel 1 (
  echo Liberando o firewall para o celular achar o PC. Clique em SIM na janela do Windows.
  powershell -NoProfile -Command "Start-Process netsh -Verb RunAs -Wait -ArgumentList 'advfirewall firewall add rule name=DitaAiClaude dir=in action=allow protocol=TCP localport=8790 profile=private,domain'"
)
python -m pip install --quiet --disable-pip-version-check pynput
python servidor.py
pause
