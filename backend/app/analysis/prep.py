"""Preparação pré-torneio: perfil do torneio + dicas VERIFICADAS por formato.

As dicas são conhecimento de estratégia consolidado, mantido AQUI (código
revisado) e entregue ao LLM como contexto — o coach narra e personaliza,
nunca inventa regra de formato. Mesmo princípio do TERMOS_REGRA.
"""
from __future__ import annotations

import re

# dicas por característica do torneio — curtas, acionáveis, sem número inventado
DICAS_FORMATO: dict[str, list[str]] = {
    "turbo": [
        "Blinds sobem rápido: a média de stack despenca — o jogo vira "
        "pré-flop cedo. Entre em modo push/fold já com ~15bb (não espere 10).",
        "Roubo de blinds vale mais desde o meio do torneio; brigar por potes "
        "pequenos sem showdown é onde o stack se sustenta.",
        "Menos pós-flop: evite call especulativo que só floppa bem às vezes — "
        "não haverá jogo deep por muito tempo para pagar o implied.",
    ],
    "hyper": [
        "Estrutura extrema: quase tudo é push/fold — os ranges de shove/call "
        "de Nash SÃO o jogo. Desvio do equilíbrio aqui custa caro e rápido.",
        "Variância altíssima é normal: avalie a sessão pelas decisões, nunca "
        "pelo resultado de um torneio.",
    ],
    "regular": [
        "Estrutura lenta favorece paciência: early é para observar o field e "
        "jogar pós-flop com posição, não para acumular a qualquer custo.",
        "Mãos especulativas (pares baixos, suited connectors) ganham valor "
        "quando você está deep — o implied existe de verdade aqui.",
    ],
    "pko": [
        "Bounty muda a conta do call: contra shove de um stack que você "
        "COBRE, o prêmio na cabeça dele paga parte do risco — pague mais "
        "largo que o normal nesses spots.",
        "Manter stack que cubra a mesa vale ouro: quem cobre, caça; quem é "
        "coberto, vira alvo.",
        "No early do PKO o field atira mais atrás de bounty — seus valores "
        "fortes pagam melhor; blefe grande perde valor.",
    ],
    "freezeout": [
        "Sem re-entry o field joga mais cauteloso (e você também deve): "
        "early tight, sem flip desnecessário — não há segunda bala.",
    ],
    "reentry": [
        "Com re-entry o early vira campo de tiro: gente atirando com a "
        "mentalidade de 'se perder, recompro'. Pague mais largo POR VALOR "
        "e blefe menos nessa fase.",
    ],
    "field_mole": [
        "Field recreativo (buy-in baixo): aposte SEU valor mais caro (eles "
        "pagam), blefe menos (eles não largam) e não nivele — ninguém está "
        "lendo sua linha.",
    ],
}


def parse_tournament_profile(text: str) -> dict:
    """Extrai o perfil do torneio do texto livre do aluno.

    '/preparar turbo pko de $22 no GG' -> formato, caracteristicas, buy-in.
    O que não for dito fica de fora (o coach pede na próxima)."""
    t = (text or "").lower()
    profile: dict = {"descricao": text.strip() or None}

    if re.search(r"\bhyper|hiper\b", t):
        profile["formato"] = "hyper"
    elif "turbo" in t:
        profile["formato"] = "turbo"
    elif re.search(r"\bregular|deep|lento|estrutura boa\b", t):
        profile["formato"] = "regular"

    if re.search(r"\bpko|bounty|recompensa|progressive\b", t):
        profile["pko"] = True
    if re.search(r"\bfreez|congelado|sem re-?entr", t):
        profile["freezeout"] = True
    elif re.search(r"\bre-?entr|recompra|reentrada\b", t):
        profile["reentry"] = True

    m = re.search(r"[\$r]\$?\s*(\d+[.,]?\d*)", t)
    if m:
        try:
            profile["buyin"] = float(m.group(1).replace(",", "."))
        except ValueError:
            pass

    if re.search(r"field (mole|fraco|recreativo)|muito peixe", t):
        profile["field"] = "recreativo"
    elif re.search(r"field (duro|forte|reg)", t):
        profile["field"] = "forte"

    return profile


def dicas_para(profile: dict) -> list[str]:
    """Seleciona as dicas verificadas que se aplicam ao torneio descrito."""
    out: list[str] = []
    fmt = profile.get("formato")
    if fmt in DICAS_FORMATO:
        out += DICAS_FORMATO[fmt]
    if profile.get("pko"):
        out += DICAS_FORMATO["pko"]
    if profile.get("freezeout"):
        out += DICAS_FORMATO["freezeout"]
    elif profile.get("reentry"):
        out += DICAS_FORMATO["reentry"]
    buyin = profile.get("buyin")
    if profile.get("field") == "recreativo" or (buyin is not None and buyin <= 33):
        out += DICAS_FORMATO["field_mole"]
    return out
