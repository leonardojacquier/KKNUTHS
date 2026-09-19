"""Roda o farejador NO VPS e devolve a saída inteira pelo Telegram.

Por que existe: o ambiente de desenvolvimento não alcança domínio de clube
(a política de rede nega o CONNECT), e eu não tenho SSH. O canal que existe
é o oneshot — deploy roda o script uma vez no servidor. Sem isto, cada
pergunta técnica vira um comando copiado e colado à mão pelo dono, e uma
investigação de seis passos vira seis idas e voltas.

Uso (dentro de um oneshot, ou à mão):

    python scripts/farejar_e_reportar.py "<link do replay>"

Manda a saída COMPLETA em blocos (o Telegram corta em 4096) e grava um
resumo em `bot_events` (event='farejar'), para ficar auditável por SQL
depois que a mensagem se perder no chat.

Só leitura: o link de replay é o que o próprio jogador compartilha.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import traceback
import urllib.request

ADMIN_ID = 6452742024
_LIMITE = 3800          # folga sob o teto de 4096 do Telegram


def _enviar(texto: str) -> bool:
    from app.config import get_settings

    token = get_settings().telegram_bot_token
    if not token:
        print("(sem token do Telegram — só saída local)")
        return False
    corpo = json.dumps({"chat_id": ADMIN_ID, "text": texto[:4000]}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=corpo, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=25)
        return True
    except Exception as exc:
        print(f"(falha ao enviar bloco: {exc})")
        return False


def em_blocos(texto: str, limite: int = _LIMITE) -> list[str]:
    """Quebra em mensagens, cortando em QUEBRA DE LINHA quando dá.

    Cortar no meio de uma URL é o mesmo que perder a URL — e é exatamente a
    linha que importa na saída do farejador.
    """
    blocos, atual = [], ""
    for linha in (texto or "").splitlines(keepends=True):
        # linha maior que o limite inteiro: parte na marra, sem perder nada
        while len(linha) > limite:
            if atual:
                blocos.append(atual)
                atual = ""
            blocos.append(linha[:limite])
            linha = linha[limite:]
        if len(atual) + len(linha) > limite:
            blocos.append(atual)
            atual = ""
        atual += linha
    if atual.strip():
        blocos.append(atual)
    return blocos or [""]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    url = sys.argv[1]
    sys.path.insert(0, "scripts")
    from sniff_replay import _DESPEJO, farejar

    buffer = io.StringIO()
    erro = None
    try:
        with contextlib.redirect_stdout(buffer):
            r = farejar(url, despejo=_DESPEJO)
    except Exception:
        erro, r = traceback.format_exc(), {"achados": [], "tentados": 0}

    saida = buffer.getvalue()
    if erro:
        saida += f"\n\nEXCEÇÃO:\n{erro}"
    else:
        saida += (f"\n{r['tentados']} endpoints tentados · "
                  f"{len(r['achados'])} com cara de mão\n")
        for i, a in enumerate(r["achados"][:2], 1):
            saida += (f"\n── candidato {i} ({a['pontos']} pts)\n{a['url']}\n"
                      + json.dumps(a["esqueleto"], ensure_ascii=False,
                                   indent=1)[:2500] + "\n")
    print(saida)

    blocos = em_blocos(f"🔍 Farejador — {url}\n\n{saida}")
    for i, b in enumerate(blocos, 1):
        _enviar(f"[{i}/{len(blocos)}]\n{b}")

    try:
        from app.db import get_repository

        get_repository().log_event(0, "farejar", "farejar", {
            "url": url[:300], "tentados": r.get("tentados", 0),
            "achados": [a["url"][:200] for a in r.get("achados", [])][:3],
            "erro": bool(erro), "saida": saida[:8000]})
    except Exception:
        pass
    return 0 if r.get("achados") else 1


if __name__ == "__main__":
    sys.exit(main())
