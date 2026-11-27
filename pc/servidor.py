#!/usr/bin/env python3
"""
DitaAíClaude (atalhos) - servidor do PC (v1)

Recebe os toques do celular pela rede Wi-Fi e aperta as teclas no PC.
Funciona no Windows 11 e no Linux com X11 (EndeavourOS KDE).

Uso:
    pip install pynput
    python servidor.py

Na primeira execução cria o arquivo config.json ao lado deste script,
com o PIN de acesso e a lista de botões (dá para editar à vontade).
"""
import ipaddress
import json
import os
import random
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSAO = "1"
PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_CONFIG = os.path.join(PASTA, "config.json")
ARQ_PAGINA = os.path.join(PASTA, "index.html")

# Tempo máximo sem "sinal de vida" do celular enquanto um botão está
# segurado. Se o Wi-Fi cair no meio, a tecla é solta sozinha.
LIMITE_SEGURAR = 2.5

BOTOES_PADRAO = [
    # ---- linha de baixo (fixa) ----
    {"id": "caps", "rotulo": "Segurar para falar", "teclas": "caps_lock",
     "modo": "segurar", "lugar": "principal", "desligar_caps_depois": True},
    {"id": "ditado_ini", "rotulo": "Iniciar ditado", "teclas": "cmd+h",
     "modo": "tocar", "lugar": "ditado"},
    {"id": "ditado_fim", "rotulo": "Parar ditado", "teclas": "cmd+h",
     "modo": "tocar", "lugar": "ditado"},
    {"id": "enter", "rotulo": "Enter", "teclas": "enter",
     "modo": "tocar", "lugar": "enter"},
    # ---- atalhos do alto ----
    {"id": "abrir", "rotulo": "Abrir Claude", "teclas": "ctrl+alt+space",
     "modo": "tocar", "lugar": "topo"},
    {"id": "voz_claude", "rotulo": "Voz do Claude", "teclas": "ctrl_l+ctrl_r",
     "modo": "tocar", "lugar": "topo"},
    {"id": "esc", "rotulo": "Esc", "teclas": "esc",
     "modo": "tocar", "lugar": "topo"},
    {"id": "apagar_palavra", "rotulo": "Apagar palavra", "teclas": "ctrl+backspace",
     "modo": "tocar", "lugar": "topo"},
    {"id": "desfazer", "rotulo": "Desfazer", "teclas": "ctrl+z",
     "modo": "tocar", "lugar": "topo"},
    {"id": "nova_linha", "rotulo": "Nova linha", "teclas": "shift+enter",
     "modo": "tocar", "lugar": "topo"},
]


# ---------------------------------------------------------------- config
def carregar_config():
    if os.path.exists(ARQ_CONFIG):
        with open(ARQ_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {}
    alterou = False
    if "pin" not in cfg:
        cfg["pin"] = "%06d" % random.SystemRandom().randint(0, 999999)
        alterou = True
    if "porta" not in cfg:
        cfg["porta"] = 8790
        alterou = True
    if "botoes" not in cfg:
        cfg["botoes"] = BOTOES_PADRAO
        alterou = True
    if alterou:
        with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    return cfg


# ---------------------------------------------------------------- teclado
class Teclado:
    """Aperta e solta combinações como 'ctrl+alt+space' ou 'caps_lock'."""

    def __init__(self, falso=False):
        self.falso = falso
        self.registro = []  # usado nos testes
        if not falso:
            from pynput.keyboard import Controller, Key
            self.ctrl = Controller()
            self.Key = Key

    def _tecla(self, nome):
        nome = nome.strip().lower()
        apelidos = {"win": "cmd", "super": "cmd", "control": "ctrl",
                    "escape": "esc", "espaco": "space", "espaço": "space",
                    "capslock": "caps_lock", "altgr": "alt_gr",
                    "return": "enter"}
        nome = apelidos.get(nome, nome)
        if self.falso:
            return nome
        if len(nome) == 1:
            return nome
        return getattr(self.Key, nome)

    def teclas(self, combo):
        return [self._tecla(p) for p in combo.split("+") if p.strip()]

    def apertar(self, combo):
        for t in self.teclas(combo):
            self._press(t)

    def soltar(self, combo):
        for t in reversed(self.teclas(combo)):
            self._release(t)

    def tocar(self, combo):
        self.apertar(combo)
        time.sleep(0.03)
        self.soltar(combo)

    def _press(self, t):
        self.registro.append(("down", str(t)))
        if not self.falso:
            self.ctrl.press(t)

    def _release(self, t):
        self.registro.append(("up", str(t)))
        if not self.falso:
            self.ctrl.release(t)

    def desligar_caps(self):
        """Depois de segurar o Caps Lock, deixa o Caps desligado
        (senão o texto passaria a sair em MAIÚSCULAS)."""
        if self.falso:
            self.registro.append(("caps_off", ""))
            return
        if sys.platform != "win32":
            return  # no Linux o próprio sistema cuida (ou o usuário remapeia)
        import ctypes
        time.sleep(0.05)
        if ctypes.windll.user32.GetKeyState(0x14) & 1:
            self.ctrl.press(self.Key.caps_lock)
            self.ctrl.release(self.Key.caps_lock)


# ---------------------------------------------------------------- estado
class Estado:
    def __init__(self, cfg, teclado):
        self.cfg = cfg
        self.teclado = teclado
        self.segurando = {}  # id -> último sinal de vida
        self.trava = threading.Lock()

    def botao(self, bid):
        for b in self.cfg["botoes"]:
            if b["id"] == bid:
                return b
        return None

    def acao(self, bid, tipo):
        b = self.botao(bid)
        if not b:
            return False, "botão desconhecido"
        with self.trava:
            if tipo == "tocar":
                self.teclado.tocar(b["teclas"])
            elif tipo == "apertar":
                if bid not in self.segurando:
                    self.teclado.apertar(b["teclas"])
                self.segurando[bid] = time.monotonic()
            elif tipo == "vivo":
                if bid in self.segurando:
                    self.segurando[bid] = time.monotonic()
            elif tipo == "soltar":
                if bid in self.segurando:
                    del self.segurando[bid]
                    self.teclado.soltar(b["teclas"])
                    if b.get("desligar_caps_depois"):
                        self.teclado.desligar_caps()
            else:
                return False, "tipo inválido"
        return True, "ok"

    def vigiar(self):
        """Solta teclas 'esquecidas' se o celular sumir da rede."""
        while True:
            time.sleep(0.5)
            agora = time.monotonic()
            with self.trava:
                vencidos = [k for k, t in self.segurando.items()
                            if agora - t > LIMITE_SEGURAR]
            for bid in vencidos:
                print("[aviso] sem sinal do celular, soltando:", bid)
                self.acao(bid, "soltar")


# ---------------------------------------------------------------- rede
def ip_permitido(ip):
    try:
        e = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return e.is_private or e.is_loopback


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.0.1", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def criar_handler(estado):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _enviar(self, codigo, dados, tipo="application/json"):
            corpo = dados if isinstance(dados, bytes) else json.dumps(
                dados, ensure_ascii=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", tipo + "; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def _bloqueado(self):
            if not ip_permitido(self.client_address[0]):
                self._enviar(403, {"erro": "só na rede local"})
                return True
            return False

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            if self._bloqueado():
                return
            if self.path == "/ping":
                self._enviar(200, {"app": "ditaaiclaude", "versao": VERSAO,
                                   "pc": socket.gethostname()})
            elif self.path in ("/", "/index.html"):
                try:
                    with open(ARQ_PAGINA, "rb") as f:
                        self._enviar(200, f.read(), "text/html")
                except OSError:
                    self._enviar(404, {"erro": "index.html não encontrado"})
            else:
                self._enviar(404, {"erro": "não encontrado"})

        def do_POST(self):
            if self._bloqueado():
                return
            try:
                n = int(self.headers.get("Content-Length", 0))
                dados = json.loads(self.rfile.read(n) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._enviar(400, {"erro": "json inválido"})
                return
            if str(dados.get("pin")) != str(estado.cfg["pin"]):
                self._enviar(401, {"erro": "PIN errado"})
                return
            if self.path == "/config":
                botoes = [{k: b[k] for k in ("id", "rotulo", "modo", "lugar", "teclas")}
                          for b in estado.cfg["botoes"]]
                self._enviar(200, {"pc": socket.gethostname(), "botoes": botoes})
            elif self.path == "/acao":
                ok, msg = estado.acao(str(dados.get("id")), str(dados.get("tipo")))
                self._enviar(200 if ok else 400, {"ok": ok, "msg": msg})
            else:
                self._enviar(404, {"erro": "não encontrado"})

    return Handler


def main():
    cfg = carregar_config()
    falso = "--teste" in sys.argv
    estado = Estado(cfg, Teclado(falso=falso))
    threading.Thread(target=estado.vigiar, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", cfg["porta"]), criar_handler(estado))
    print("=" * 52)
    print(" DitaAíClaude (atalhos) v%s - servidor do PC" % VERSAO)
    print(" Endereço : %s:%d" % (ip_local(), cfg["porta"]))
    print(" PIN      : %s" % cfg["pin"])
    print(" (celular e PC precisam estar no mesmo Wi-Fi)")
    print("=" * 52)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
