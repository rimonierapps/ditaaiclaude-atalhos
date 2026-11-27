# DitaAíClaude (atalhos) 🎙️

Controle remoto de atalhos do Claude no PC, pelo celular Android, no mesmo Wi-Fi.

- **Segurar para falar** (canto inferior direito): enquanto o dedo está no botão, o PC sente o **Caps Lock segurado**; ao soltar, solta a tecla e a mensagem é enviada, igual ao teclado físico.
- **Iniciar / Parar ditado** (centro): liga e desliga a digitação por voz (**Win + H**) sem apertar Enter, para conferir o texto.
- **Enter** (esquerda): envia.
- **No alto**: Abrir Claude (Ctrl + Alt + Espaço), Voz do Claude (Ctrl esq + Ctrl dir), Esc, Apagar palavra, Desfazer, Nova linha.

## Como usar

1. **No PC**: baixe a pasta `pc/` e dê dois cliques em `iniciar.bat` (Windows) ou rode `./iniciar.sh` (Linux X11). Precisa do Python 3.
2. Na primeira vez o Windows pede para liberar o firewall: clique em **Sim**.
3. **No celular**: abra o app. Ele acha o PC sozinho e conecta (o PC se anuncia na rede).
4. Se não achar, toque em ⚙ e digite o IP que aparece na janela do PC.

Sem o app, também funciona no navegador do celular: abra `http://IP-do-PC:8790`.

Para abrir sozinho com o Windows: `iniciar-com-o-windows.bat`.

## Trocar os atalhos

Edite `pc/config.json` (criado na 1ª execução) e reinicie o servidor. O celular puxa os botões do PC.

| Campo | Valores |
|---|---|
| teclas | ex. `ctrl+alt+space` |
| modo | `tocar` / `segurar` |
| lugar | `topo` / `ditado` |

**Legenda:**
- **teclas**: combinação separada por `+`. Nomes: `ctrl`, `ctrl_l`, `ctrl_r`, `alt`, `alt_gr`, `shift`, `cmd` (tecla Windows), `space`, `enter`, `esc`, `backspace`, `caps_lock`, `f1`…`f12`, ou uma letra.
- **modo**: `tocar` aperta e solta na hora; `segurar` mantém apertado enquanto o dedo estiver no botão.
- **lugar**: `topo` = grade de atalhos no alto; `ditado` = coluna do meio. Os ids `caps` e `enter` são os botões fixos de baixo.
- **desligar_caps_depois** (opcional, Windows): depois de soltar o Caps Lock, deixa o Caps desligado para o texto não sair em maiúsculas.

## Segurança

- Só aceita conexões da rede local (IPs privados). Para exigir PIN, ponha `"exigir_pin": true` e `"pin": "1234"` no `config.json`.
- Se o Wi-Fi cair com o botão segurado, o PC solta a tecla sozinho em 2,5 s.

## Compilação

Cada push na `main` compila o APK no GitHub Actions, publica em **Releases** e envia pelo Telegram (segredos `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` da organização).
