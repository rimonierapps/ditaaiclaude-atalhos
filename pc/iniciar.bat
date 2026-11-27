@echo off
rem DitaAíClaude (atalhos) - inicia o servidor do PC (Windows)
cd /d "%~dp0"
python -m pip install --quiet --disable-pip-version-check pynput
python servidor.py
pause
