#!/bin/sh
# DitaAíClaude (atalhos) - inicia o servidor do PC (Linux X11)
cd "$(dirname "$0")"
python3 -c "import pynput" 2>/dev/null || pip install --user pynput || pip install --user --break-system-packages pynput
exec python3 servidor.py
