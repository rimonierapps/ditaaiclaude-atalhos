@echo off
rem DitaAíClaude (atalhos) - faz o servidor abrir sozinho, escondido, quando o Windows iniciar
cd /d "%~dp0"
python -m pip install --quiet --disable-pip-version-check pynput
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\DitaAiClaude.vbs"
> "%VBS%" echo CreateObject("WScript.Shell").Run "pythonw ""%~dp0servidor.py""", 0, False
echo Pronto. O servidor vai abrir sozinho no proximo login.
echo Para desfazer, apague: %VBS%
start "" pythonw "%~dp0servidor.py"
pause
