"""TORNEIO SEM ICM É CASH GAME COM BLIND SUBINDO.

Auditoria de poker (07/08): das 25 análises de torneio mais recentes, ZERO
mencionam bolha, ICM, bubble factor ou bounty. Todo conselho saiu em chip-EV
puro — inclusive calls de all-in por 11bb, que é onde o dinheiro do MTT está.

E não é falta de motor: icm.py (Malmuth-Harville), pko.py e o parâmetro `bf`
do allin_engine existem e funcionam. O buraco é de FLUXO — `bf` só é ativado
se o aluno digitar a premiação, e o bot nunca pergunta. A regra C3 do prompt
é passiva ("se o contexto traz payouts_salvos, aplique"); nada age quando
eles faltam, então o default silencioso é bf=1.0 em 100% das análises.

Este módulo fecha o buraco sem pedir nada antes da análise — o funil já está
quebrado (8 de 10 alunos nunca mandaram uma mão; pôr formulário na frente
piora). Em vez disso ele MEDE o que a bolha mudaria, com o motor que já
existe, e entrega o número pronto para o coach citar em uma linha:

    SB paga shove do CO com 8.4bb:
        chip-EV (bf=1.0):  paga 35.5% do range
        bolha   (bf=1.6):  paga 13.6% do range
        somem 37 mãos — A8o, A7o, A6s, A5s, A4o...

"Se você estava na bolha, esse call vira fold" é conselho. "O ICM importa"
é palestra.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# bf típico de bolha de MTT de clube (field médio, 15% pagos). Serve só para
# DIMENSIONAR o efeito na frase do coach — o bf real sai do Malmuth-Harville
# assim que o aluno informa a premiação.
BF_BOLHA_TIPICO = 1.6


def _all_in_do_heroi(structured: dict) -> dict | None:
    """O spot de all-in que o aluno enfrentou, se houver."""
    for s in (structured.get("spots") or []):
        if not isinstance(s, dict):
            continue
        texto = " ".join(str(s.get(k) or "") for k in ("acao", "action",
                                                       "descricao"))
        if "all-in" in texto.lower() or s.get("all_in"):
            return s
    return None


def _stack_efetivo(structured: dict) -> float | None:
    for chave in ("effective_bb", "hero_stack_bb", "stack_bb"):
        v = structured.get(chave)
        if isinstance(v, (int, float)) and 0 < float(v) <= 200:
            return float(v)
    return None


def situacao_icm(structured: dict, payouts_salvos=None) -> dict | None:
    """O que a bolha mudaria neste spot — em número, não em aviso genérico.

    None quando não se aplica: mão de cash, sem all-in, ou quando a premiação
    JÁ é conhecida (aí o ICM sai de verdade e não há o que avisar).
    """
    if not isinstance(structured, dict):
        return None
    if str(structured.get("format") or "") != "tournament":
        return None
    if payouts_salvos:
        return None                      # ICM real disponível: nada a dizer
    spot = _all_in_do_heroi(structured)
    if not spot:
        return None
    stack = _stack_efetivo(structured)
    if not stack or stack > 25:          # acima disso não é spot de jam/fold
        return None

    try:
        from app.analysis.allin_engine import solve_spot
    except Exception:
        return None

    hero = str(structured.get("hero_pos") or spot.get("posicao") or "BB")
    vil = str(spot.get("vilao_pos") or "CO")
    try:
        chip = solve_spot("call_shove", hero, round(stack, 1), 0.125, 1.0, vil)
        bolha = solve_spot("call_shove", hero, round(stack, 1), 0.125,
                           BF_BOLHA_TIPICO, vil)
    except Exception as exc:
        log.warning("situacao_icm falhou: %s", exc)
        return None
    if not chip or not bolha:
        return None

    somem = [h for h in chip["hands"]
             if chip["acao"].get(h, 0) > 0.5 and bolha["acao"].get(h, 0) <= 0.5]
    return {
        "sabemos_a_premiacao": False,
        "range_chip_ev_pct": chip["acao_pct"],
        "range_com_bolha_pct": bolha["acao_pct"],
        "maos_que_somem": somem[:12],
        "quantas_somem": len(somem),
        "bf_usado_de_referencia": BF_BOLHA_TIPICO,
        "instrucao": (
            f"Esta conta saiu em CHIP-EV: você não sabe a premiação nem quantos "
            f"faltam para o dinheiro, então bf=1.0. Com pressão de bolha típica "
            f"o range de call deste spot cai de {chip['acao_pct']:.0f}% para "
            f"{bolha['acao_pct']:.0f}% — {len(somem)} mãos viram fold"
            + (f" (entre elas {', '.join(somem[:5])})" if somem else "")
            + ". Feche a análise com UMA linha dizendo isso e convidando o "
              "aluno a informar a premiação ('paga 500/300/200') — aí o ICM "
              "sai automático nas próximas. UMA linha, não um parágrafo: se a "
              "mão não foi de bolha, ele não precisa de aula de ICM."),
    }
