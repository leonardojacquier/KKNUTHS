"""Draws — flush draw e draw de sequência, CONTADOS, não opinados.

24/09: vilão com A♦7♦ no flop 5♠4♦Q♦ (quatro ouros, flush draw de livro, 9
outs). O coach disse três vezes seguidas que não havia draw — uma delas
depois de ter acertado no parágrafo anterior. O gabarito da conversa trazia
mão feita street a street e textura do board, e não trazia draw: o modelo
contava naipe de cabeça. Contagem é conta; aqui ela sai de código.

Definições (as da mesa, não as de manual de solver):
  · flush draw — 4 cartas do mesmo naipe entre mão + board, usando PELO
    MENOS UMA carta da mão, e o flush ainda não feito. Quatro no board e
    nenhuma na mão é draw do board, não do jogador.
  · OESD — dois valores de carta completam a sequência (8 outs).
  · gutshot — um valor completa (4 outs).
Draw de sequência também exige uma carta da mão na sequência completada.
No river não existe draw: só mão feita.
"""
from __future__ import annotations

_VALORES = "23456789TJQKA"
_NAIPE_ICONE = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}


def _valor(carta: str) -> int:
    r = carta[0].upper()
    return 10 if r in ("1",) else _VALORES.index(r) + 2   # '10x' -> T


def _norm(carta: str) -> str:
    c = carta.strip()
    return ("T" + c[2:]) if c.startswith("10") else c


def _sequencias_completas(valores: set[int]) -> list[set[int]]:
    """Janelas de 5 valores consecutivos (com a roda A-2-3-4-5)."""
    v = set(valores)
    if 14 in v:
        v.add(1)                      # ás baixo
    out = []
    for inicio in range(1, 11):
        janela = set(range(inicio, inicio + 5))
        if janela <= v:
            out.append(janela)
    return out


def _com_as(valores: set[int]) -> set[int]:
    return valores | ({1} if 14 in valores else set())


def draws(cartas: list[str], board: list[str]) -> dict:
    """Draws de um jogador num board de 3 ou 4 cartas."""
    cartas = [_norm(c) for c in cartas]
    board = [_norm(c) for c in board]
    vazio = {"flush_draw": False, "flush_feito": False, "naipe": None,
             "outs_flush": 0, "sequencia": None, "outs_sequencia": 0,
             "sequencia_feita": False}
    if len(cartas) != 2 or len(board) not in (3, 4):
        return vazio
    out = dict(vazio)

    # --- flush -------------------------------------------------------------
    todas = cartas + board
    for naipe in "shdc":
        na_mao = sum(1 for c in cartas if c[1].lower() == naipe)
        total = sum(1 for c in todas if c[1].lower() == naipe)
        if na_mao and total >= 5:
            out.update(flush_feito=True, naipe=naipe)
        elif na_mao and total == 4:
            out.update(flush_draw=True, naipe=naipe, outs_flush=13 - 4)

    # --- sequência ---------------------------------------------------------
    mao = {_valor(c) for c in cartas}
    vistos = mao | {_valor(c) for c in board}
    if _sequencias_completas(vistos):
        out["sequencia_feita"] = True
    else:
        completam = set()
        for novo in range(2, 15):
            if novo in vistos:
                continue
            for janela in _sequencias_completas(vistos | {novo}):
                if janela & _com_as(mao):            # usa carta da mão
                    completam.add(novo)
        if len(completam) >= 2:
            out.update(sequencia="oesd", outs_sequencia=8)
        elif len(completam) == 1:
            out.update(sequencia="gutshot", outs_sequencia=4)
    return out


def texto_do_draw(d: dict) -> str | None:
    """Frase pronta para o coach citar (e para o guarda corrigir)."""
    partes = []
    if d.get("flush_draw"):
        icone = _NAIPE_ICONE.get(d["naipe"], d["naipe"])
        partes.append(f"flush draw de {icone} ({d['outs_flush']} outs)")
    if d.get("sequencia") == "oesd":
        partes.append("draw de sequência aberto (8 outs)")
    elif d.get("sequencia") == "gutshot":
        partes.append("gutshot (4 outs)")
    return " + ".join(partes) or None


def draws_por_street(cartas: list[str], final_board: list[str]) -> dict:
    """{flop: {...}, turn: {...}} — QUANDO o draw existia. River não entra."""
    out = {}
    fb = list(final_board or [])
    for street, n in (("flop", 3), ("turn", 4)):
        if len(fb) >= n:
            d = draws(cartas, fb[:n])
            d["texto"] = texto_do_draw(d) or "sem draw"
            out[street] = d
    return out


def tem_draw(d: dict) -> bool:
    return bool(d.get("flush_draw") or d.get("sequencia"))
