"""A mesa do torneio: quem estava nela, e quem é explorável — com prova.

O /vilao responde por UM oponente. O que faltava era a visão de mesa: num
torneio o aluno senta horas com as mesmas pessoas (medido na base: 35 vilões
e 2.270 observações num torneio só, quatro deles com 250+ mãos), e a
pergunta prática é "contra quem eu ajusto, e como".

O número que carrega o quadro é o GAP VPIP−PFR — entrar no pote sem atacar.
Ele é a medida de passividade que não sofre de comparação múltipla: é uma
proporção DENTRO do mesmo jogador (das mãos que jogou, quantas só pagando),
não um contraste dele com os outros. E "paga e não ataca" é o perfil que
paga as apostas de valor do aluno — o mais lucrativo de identificar.

As regras de honestidade, na ordem em que importam:

  * rótulo SÓ quando o intervalo de Wilson sustenta: "solto" exige o PISO
    do VPIP acima da fronteira, "fechado" exige o TETO abaixo, "passivo"
    exige o piso do gap. Média do lado certo com intervalo em cima da
    fronteira sai como números sem rótulo;
  * abaixo de 20 mãos, a linha nem aparece — vira um contador no rodapé
    ("N com amostra curta"). Entre 20 e 39, números com margem e sem
    rótulo. Rótulo pede 40+;
  * a ordem é pelo PISO do gap, não pela média — quem lidera o quadro
    lidera com evidência, não com ruído de amostra pequena.

As fronteiras (28/22% de VPIP, 10pp de gap) são convenção de poker mantida
em código revisado, como DICAS_FORMATO: o modelo narra, não arbitra.
"""
from __future__ import annotations

from typing import Any, NamedTuple

from app.analysis.defesa import _wilson_lo
from app.models.canonical import ActionType, StreetName

MINIMO_PARA_LINHA = 20
MINIMO_PARA_ROTULO = 40

# fronteiras de convenção (não medidas): VPIP para solto/fechado, gap para
# passivo. Aplicadas sempre sobre o LADO conservador do intervalo.
SOLTO_ACIMA_DE = 0.28
FECHADO_ABAIXO_DE = 0.22
PASSIVO_GAP_ACIMA_DE = 0.10

_EXPLOIT = {
    "passivo": "paga e não ataca: aposte por valor, blefe pouco",
    "solto-passivo": "aposte por valor fino; não blefe",
    "fechado-passivo": "roube os blinds; saia quando ele acordar",
    "solto": "pague mais leve; deixe-o blefar",
    "fechado": "respeite a agressão dele",
}


class Linha(NamedTuple):
    nome: str
    maos: int
    vpip: float
    vpip_margem: float          # meia-largura normal (para exibição)
    pfr: float
    gap: float                  # proporção entrou-sem-atacar
    gap_lo: float               # piso de Wilson do gap — a chave da ordem
    rotulo: str                 # "" quando o intervalo não sustenta
    exploit: str
    showdowns: int


class Mesa(NamedTuple):
    linhas: tuple[Linha, ...]   # já ordenadas: piso do gap, depois amostra
    vilaos: int                 # total que apareceu na mesa
    observacoes: int
    amostra_curta: int          # quantos ficaram fora por n < 20


def _wilson_hi(k: int, n: int) -> float:
    return 1.0 - _wilson_lo(n - k, n)


def _rotulo(vpip_n: int, gap_n: int, seen: int) -> str:
    if seen < MINIMO_PARA_ROTULO:
        return ""
    partes: list[str] = []
    if _wilson_lo(vpip_n, seen) >= SOLTO_ACIMA_DE:
        partes.append("solto")
    elif _wilson_hi(vpip_n, seen) <= FECHADO_ABAIXO_DE:
        partes.append("fechado")
    if _wilson_lo(gap_n, seen) >= PASSIVO_GAP_ACIMA_DE:
        partes.append("passivo")
    return "-".join(partes)


def medir(hands: list) -> Mesa | None:
    """A mesa de UM conjunto de mãos (o chamador decide qual torneio)."""
    import math

    contagem: dict[str, dict] = {}
    for h in (hands or []):
        pre = next((s for s in (getattr(h, "streets", None) or ())
                    if s.name == StreetName.PREFLOP), None)
        mostradas = getattr(h, "shown_cards", None) or {}
        for p in (getattr(h, "players", None) or ()):
            nome = (p.name or "").strip()
            if not nome or getattr(p, "is_hero", False) \
                    or nome.lower() in ("hero", "você", "voce"):
                continue
            c = contagem.setdefault(nome, {"seen": 0, "vpip": 0, "pfr": 0,
                                           "sd": 0})
            c["seen"] += 1
            voluntaria = atacou = False
            for a in (pre.actions if pre else ()):
                # POST não precisa de guarda próprio: a whitelist abaixo só
                # tem CALL/BET/RAISE — blind postado nunca vira voluntária
                # (test_blind_postado_nao_conta_como_vpip prende isso)
                if a.actor != nome:
                    continue
                if a.type in (ActionType.CALL, ActionType.BET,
                              ActionType.RAISE):
                    voluntaria = True
                if a.type in (ActionType.BET, ActionType.RAISE):
                    atacou = True
            c["vpip"] += voluntaria
            c["pfr"] += atacou
            c["sd"] += bool(mostradas.get(nome))

    if not contagem:
        return None

    linhas: list[Linha] = []
    curtos = 0
    for nome, c in contagem.items():
        n = c["seen"]
        if n < MINIMO_PARA_LINHA:
            curtos += 1
            continue
        gap_n = c["vpip"] - c["pfr"]
        p = c["vpip"] / n
        rot = _rotulo(c["vpip"], gap_n, n)
        linhas.append(Linha(
            nome=nome, maos=n,
            vpip=round(p, 3),
            vpip_margem=round(1.96 * math.sqrt(p * (1 - p) / n), 3),
            pfr=round(c["pfr"] / n, 3),
            gap=round(gap_n / n, 3),
            gap_lo=round(_wilson_lo(gap_n, n), 3),
            rotulo=rot, exploit=_EXPLOIT.get(rot, ""),
            showdowns=c["sd"]))

    linhas.sort(key=lambda li: (li.gap_lo, li.maos), reverse=True)
    return Mesa(linhas=tuple(linhas), vilaos=len(contagem),
                observacoes=sum(c["seen"] for c in contagem.values()),
                amostra_curta=curtos)


def texto(m: Mesa | None, limite: int = 6) -> str:
    """Bloco determinístico da mesa. '' quando não há linha que se sustente."""
    if m is None or not m.linhas:
        return ""
    out = [f"👥 *A mesa deste torneio* — {m.vilaos} vilões, "
           f"{m.observacoes} observações",
           "_Mais exploráveis primeiro (entra no pote e não ataca):_"]
    for li in m.linhas[:limite]:
        um = (f"• *{li.nome}* — {li.maos} mãos · VPIP "
              f"{round(100 * li.vpip)}% ±{round(100 * li.vpip_margem)} · "
              f"PFR {round(100 * li.pfr)}% · gap {round(100 * li.gap)}pp")
        if li.rotulo:
            um += f"\n  → *{li.rotulo}*: {li.exploit}" if li.exploit \
                else f"\n  → *{li.rotulo}*"
        if li.showdowns:
            um += f"\n  🔍 mostrou {li.showdowns}× — `/vilao {li.nome}`"
        out.append(um)
    if len(m.linhas) > limite:
        out.append(f"_…e mais {len(m.linhas) - limite} com 20+ mãos._")
    if m.amostra_curta:
        quem = (f"{m.amostra_curta} vilões ficam"
                if m.amostra_curta > 1 else "1 vilão fica")
        out.append(f"_{quem} de fora por ter menos de {MINIMO_PARA_LINHA} "
                   f"mãos — amostra curta não vira rótulo._")
    return "\n".join(out)
