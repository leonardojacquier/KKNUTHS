"""O pedido em texto que anuncia o arquivo vira a legenda desse arquivo.

21/09: o alvgomes19 escreveu "analise o hand history abaixo e dê uma nota de
1 a 10" e mandou o arquivo 20 s depois. O texto foi pro coach como conversa
("não recebi nenhum histórico") e o arquivo foi analisado sem o pedido.

Mesmo mecanismo de FOTOS_RECENTES (imagem_de_propaganda): o texto fica
guardado por JANELA_S; o próximo upload do MESMO aluno o consome como
legenda. Só texto que ANUNCIA um arquivo entra — "obrigado" um minuto antes
de um print não vira relato da mão.
"""
from __future__ import annotations

import re
import time

from app.bot.memoria_do_processo import guardar_com_prazo

JANELA_S = 120
PEDIDOS: dict[int, tuple[float, str]] = {}

_ANUNCIO = re.compile(
    r"\babaixo\b|\bsegue[m]?\b|\ba\s+seguir\b|\bem\s+seguida\b|\banexo\b"
    r"|\b(?:vou|irei|j[áa]|t[ôo]|estou|to)\s+(?:te\s+|lhe\s+)?"
    r"(?:mandar|enviar|mandando|enviando|passar|mando|envio)\b",
    re.I)
_OBJETO = re.compile(
    r"hand\s*history|\bhh\b|hist[óo]ric|arquivo|\bm[ãa]os?\b|\bprint|\btxt\b"
    r"|torneio|sess[ãa]o|\bzip\b",
    re.I)

RESPOSTA_AO_ANUNCIO = (
    "👍 Pode mandar — quando o arquivo chegar eu analiso já com esse seu "
    "pedido.")


def anuncia_arquivo(texto: str) -> bool:
    """O texto avisa que um histórico/print vem em seguida."""
    t = texto or ""
    return len(t) <= 600 and bool(_ANUNCIO.search(t)) and \
        bool(_OBJETO.search(t))


def registrar(telegram_id: int, texto: str) -> None:
    guardar_com_prazo(PEDIDOS, telegram_id, (time.time(), texto.strip()),
                      JANELA_S)


def legenda_do_upload(telegram_id: int, legenda: str | None) -> str | None:
    """A legenda do upload, somada ao pedido recente (que é consumido)."""
    item = PEDIDOS.pop(telegram_id, None)
    pedido = item[1] if item and time.time() - item[0] <= JANELA_S else None
    if not pedido:
        return legenda
    if legenda and legenda.strip():
        return f"{legenda.strip()}\n{pedido}"
    return pedido
