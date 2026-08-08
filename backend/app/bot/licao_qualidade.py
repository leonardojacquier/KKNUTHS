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
# "aqui o resultado de -3.6bb mostra que os opponents tinham range forte
# demais" (lição 21, real): inferir estratégia de UMA amostra. É o mesmo
# vício com roupa de número — e escapava porque a frase não usa nenhuma das
# expressões acima.
_INFERE_DE_UMA_MAO = re.compile(
    r"(?:o\s+)?resultado\s+d[eo]\s*[-+−]?\d+[.,]?\d*\s*bb\s+"
    r"(?:mostra|indica|prova|sugere|revela|comprova)", re.I)
# "Raise pequeno (3bb) ... um raise padrão de 2.5x teria extraído mais valor"
# (lição 27, real): condena um tamanho por ser PEQUENO e receita um MENOR.
# O aluno que segue isso piora — e nenhum dos filtros de prosa via, porque
# cada frase, sozinha, está bem escrita.
_TAMANHO_CRITICADO = re.compile(
    r"\b(?:raise|aumento|open)\s+(?:pequen|curt|baix|frac)\w*\s*"
    r"\(?~?(\d+[.,]?\d*)\s*(?:bb|x)\b", re.I)
# o tamanho PROPOSTO precisa vir com marca de receita — "raise padrão de X"
# ou "raise de X teria extraído". Sem isso, o "faz raise de ~3bb" que só
# DESCREVE a mão no spot era lido como proposta e o par batia consigo mesmo.
_TAMANHO_PROPOSTO = re.compile(
    r"\b(?:raise|aumento|open|sizing)\s+"
    r"(?:(?:padr[ãa]o|maior|ideal|melhor)\s*(?:de\s+)?~?(\d+[.,]?\d*)"
    r"\s*(?:bb|x)\b"
    r"|de\s+~?(\d+[.,]?\d*)\s*(?:bb|x)\b"
    r"(?=[^.;\n]{0,60}\b(?:teria|seria|deveria|extrairia|renderia)\b))", re.I)

# poker não tem certeza; promessa absoluta é o que queima credibilidade
_ABSOLUTO = (
    "sempre", "nunca erra", "obrigatóri", "automátic", "garantid",
    "100% das vezes", "não tem erro", "infalível",
)


_MENTIRA_DE_POKER = "afirma dominância que a conta desmente"


def com_cartas(repo, linha: dict) -> dict:
    """A lição + as cartas da mão que a originou (hero_cards, board).

    A tabela `licoes` guarda só texto — o portão lia prosa e não tinha como
    conferir fato. As cartas estão a dois saltos (licoes.hand_analysis_id →
    hand_analysis.hand_id → hands.canonical); buscá-las na LEITURA, e não na
    escrita, é o que faz a checagem valer também para as 27 lições que já
    estão na estante. Falha silenciosa de propósito: sem cartas o portão
    volta a ser o que era, nunca pior.
    """
    if not linha or not getattr(repo, "enabled", False):
        return dict(linha or {})
    if linha.get("hero_cards"):
        return dict(linha)
    try:
        ha_id = linha.get("hand_analysis_id")
        if not ha_id:
            return dict(linha)
        ha = (repo.client.table("hand_analysis").select("hand_id")
              .eq("id", ha_id).limit(1).execute().data or [None])[0]
        can = repo.get_hand_canonical((ha or {}).get("hand_id"))
        if not can:
            return dict(linha)
        return {**linha,
                "hero_cards": list(getattr(can, "hero_cards", None) or []),
                "board": list(getattr(can, "final_board", None) or [])}
    except Exception:
        return dict(linha)


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
    m = _INFERE_DE_UMA_MAO.search(texto)
    if m:
        probs.append(f"infere estratégia de UMA mão: '{m.group(0)}' — o "
                     "resultado de uma amostra não mostra nada sobre o "
                     "range do vilão nem sobre o sizing")

    # FATO DE POKER: "só AA e QQ te viram favorito" numa lição de KK foi
    # para a estante (lição 26). QQ perde de KK em 80%. O guarda que testa
    # isso já existia e NÃO rodava aqui — só no caminho da análise, e o
    # destilador lê o summary CRU, reescrevendo o erro com autoridade de
    # material didático. Aqui ele bloqueia em vez de corrigir: lição é o
    # objeto que fala com todos, e frase que nasceu falsa costuma ter mais
    # do que a mão errada dentro.
    heroi = licao.get("hero_cards") or []
    if len(heroi) == 2:
        try:
            from app.bot.guarda_fatos import conferir_dominancia

            _, mentiras = conferir_dominancia(texto, list(heroi),
                                              licao.get("board") or [])
            if mentiras:
                probs.append(
                    f"{_MENTIRA_DE_POKER}: " + ", ".join(mentiras)
                    + " — essas mãos NÃO ganham do herói")
        except Exception:
            pass
    criticado = _TAMANHO_CRITICADO.search(texto)
    proposto = _TAMANHO_PROPOSTO.search(texto)
    if criticado and proposto:
        alvo = proposto.group(1) or proposto.group(2)
        a = float(criticado.group(1).replace(",", "."))
        b = float(alvo.replace(",", "."))
        if b < a:
            probs.append(
                f"receita um raise MENOR do que o que chamou de pequeno: "
                f"critica {criticado.group(1)} e propõe {alvo} "
                "— quem seguir isso piora o sizing")

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
