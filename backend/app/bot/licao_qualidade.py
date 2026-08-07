"""Portão de qualidade da lição — antes de ela falar com TODOS os alunos.

A lição #24 chegou à véspera do primeiro broadcast com o spot dizendo
"13 outs" e a lição dizendo "12" — contradição dentro do MESMO card. E a
varredura da biblioteca mostrou que não era caso isolado: de 24 lições, 8
tinham conta com outs, raciocínio orientado a resultado ("o fold do vilão
confirmou que funciona") ou promessa absoluta ("jam é obrigatório",
"+EV automático").

Os três vícios têm a mesma origem: o destilador é um modelo barato lendo
uma análise e escrevendo bonito. Nada verificava — e diferente de uma
análise (que vai para UM aluno, que pode contestar), a lição vai para
TODOS de uma vez e leva a assinatura da ferramenta.

Checagem determinística, custo zero. Não bloqueia: SINALIZA, e o dono
decide — o mesmo desenho do linguista e do glossário.
"""
from __future__ import annotations

import re

_OUTS = re.compile(r"(\d+)\s*outs?\b", re.I)

# resultado não é argumento: o vilão foldar não prova que a linha era boa
_RESULTADISTA = (
    "confirmou que", "confirma que", "provou que", "prova que",
    "deu certo", "funcionou porque", "o resultado mostra",
)
# poker não tem certeza; promessa absoluta é o que queima credibilidade
_ABSOLUTO = (
    "sempre", "nunca erra", "obrigatóri", "automátic", "garantid",
    "100% das vezes", "não tem erro", "infalível",
)


def problemas_da_licao(licao: dict) -> list[str]:
    """Vícios de uma lição prestes a ir para todos os alunos (função pura).

    Lista vazia = passou. Cada item é legível pelo dono no /licoes.
    """
    texto = f"{licao.get('titulo', '')} {licao.get('spot', '')} " \
            f"{licao.get('licao', '')}"
    baixo = texto.lower()
    probs: list[str] = []

    # contradição de contagem DENTRO do mesmo card — o caso da #24
    contagens = {int(m) for m in _OUTS.findall(texto)}
    if len(contagens) > 1:
        probs.append("conta de outs se contradiz no mesmo card: "
                     + " vs ".join(f"{n} outs" for n in sorted(contagens)))

    for frase in _RESULTADISTA:
        if frase in baixo:
            probs.append(f"raciocínio por resultado: '{frase}' — o vilão "
                         "foldar não prova que a linha era boa")
            break
    for frase in _ABSOLUTO:
        if frase in baixo:
            probs.append(f"promessa absoluta: '{frase}' — poker não tem "
                         "certeza, e o aluno cobra quando falhar")
            break
    if not (licao.get("spot") or "").strip():
        probs.append("sem spot: o aluno não sabe do que se trata")
    if not (licao.get("licao") or "").strip():
        probs.append("sem lição: só a descrição do spot não ensina nada")
    return probs


def selo_de_qualidade(licao: dict) -> str:
    """Uma linha para a listagem do /licoes."""
    probs = problemas_da_licao(licao)
    return "✅ limpa" if not probs else f"⚠️ {len(probs)} ponto(s)"
