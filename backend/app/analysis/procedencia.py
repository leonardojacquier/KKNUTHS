"""PROCEDÊNCIA da leitura — de onde veio cada dado e com que certeza.

Endurecimento da camada de entrada. O aluno disse que não confia na
ferramenta, e a razão principal está aqui: uma análise feita a partir de um
PRINT lido por visão era apresentada com a MESMA segurança de uma lida de
replay oficial (JSON exato). Ele não tinha como saber quando duvidar.

Agora toda análise de fonte incerta abre declarando o que foi lido e de
onde veio — e, quando as duas passadas de leitura discordaram, isso aparece
para ELE, não só no contexto do coach (que podia esquecer de mencionar).

Regra: fonte EXATA (replay/hand history) não vira ruído — só a fonte
incerta (print/foto/áudio) ganha o bloco.
"""
from __future__ import annotations

# fontes com dado estruturado na origem: o que está lá é o que aconteceu
_EXATAS = {"pppoker_replay", "suprema_replay", "txt", "phh", "csv"}

_NOME_FONTE = {
    "pppoker_replay": "replay oficial da PPPoker",
    "suprema_replay": "replay oficial da Suprema",
    "txt": "hand history do site",
    "phh": "hand history",
    "csv": "exportação do tracker",
    "image": "print/foto da mesa",
    "vision": "print/foto da mesa",
    "audio": "áudio",
    "pdf": "PDF",
}


def fonte_exata(source_format: str | None) -> bool:
    return (source_format or "") in _EXATAS


def _cartas(cs) -> str:
    from app.analysis.equity import pretty_cards

    return pretty_cards(list(cs or [])) or "—"


def bloco_leitura(hand, source_format: str | None,
                  confidence: float | None = None,
                  divergencias: list[str] | None = None) -> str:
    """Bloco 'foi isto que eu li' para fonte INCERTA. String vazia quando a
    fonte é exata (não polui análise de replay/hand history)."""
    if fonte_exata(source_format) or hand is None:
        return ""
    seat = hand.hero_seat()
    bb = hand.stakes.big_blind or 0
    partes = [f"🔎 *Foi isto que eu li* — {_NOME_FONTE.get(source_format or '', 'arquivo')}:"]
    linha = f"• Você: *{_cartas(hand.hero_cards)}*"
    if seat and seat.position:
        linha += f" no *{seat.position}*"
    if seat and bb:
        linha += f" · stack *{round(seat.stack / bb, 1):g}bb*"
    partes.append(linha)
    if hand.final_board:
        partes.append(f"• Board: *{_cartas(hand.final_board)}*")
    for quem, cs in (hand.shown_cards or {}).items():
        partes.append(f"• {quem} mostrou: *{_cartas(cs)}*")

    if divergencias:
        partes.append("\n⚠️ *As duas leituras não bateram* — confira antes de "
                      "usar a conta:")
        partes += [f"  · {d}" for d in divergencias[:3]]
    elif confidence is not None and confidence < 0.8:
        partes.append(f"\n⚠️ Confiança da leitura: *{confidence*100:.0f}%* — "
                      "print difícil. Confira os dados acima.")

    partes.append("_Errei alguma coisa? Me diga (ex.: 'eu sou o Fulano', "
                  "'minhas cartas eram A♠Q♠') que eu refaço a análise._")
    return "\n".join(partes)


def selo_procedencia(source_format: str | None,
                     confidence: float | None = None) -> str:
    """Selo curto de uma linha pro rodapé: de onde veio o dado."""
    nome = _NOME_FONTE.get(source_format or "", "arquivo enviado")
    if fonte_exata(source_format):
        return f"_Fonte: {nome} — dados exatos, sem leitura por imagem._"
    conf = (f" · confiança {confidence*100:.0f}%"
            if confidence is not None else "")
    return (f"_Fonte: {nome} — leitura por imagem{conf}. "
            "Confira os dados se algum número parecer estranho._")


def checar_leitura(hand, source_format: str | None = None) -> list[str]:
    """Classe de INPUT para a prova real: o que foi lido é internamente
    possível? (cartas repetidas entre jogadores, board grande demais,
    stack/blind absurdos — sintomas clássicos de leitura ruim de print)."""
    p: list[str] = []
    if hand is None:
        return ["não consegui montar a mão a partir do arquivo"]
    vistas: dict[str, str] = {}
    for dono, cs in [("você", hand.hero_cards or []),
                     ("board", hand.final_board or [])] + [
                     (k, v) for k, v in (hand.shown_cards or {}).items()]:
        for c in cs or []:
            if c in vistas and vistas[c] != dono:
                p.append(f"a carta {c} foi lida em dois lugares "
                         f"({vistas[c]} e {dono})")
            vistas[c] = dono
    if hand.final_board and len(hand.final_board) > 5:
        p.append(f"board com {len(hand.final_board)} cartas")
    bb = hand.stakes.big_blind or 0
    if bb <= 0:
        p.append("big blind não foi lido")
    else:
        for pl in hand.players:
            if pl.stack and pl.stack / bb > 1000:
                p.append(f"stack de {pl.name} = {round(pl.stack/bb)}bb "
                         "(provável erro de leitura)")
                break
    if hand.hero_cards and len(hand.hero_cards) not in (0, 2):
        p.append(f"li {len(hand.hero_cards)} carta(s) sua(s), deveriam ser 2")
    return p
