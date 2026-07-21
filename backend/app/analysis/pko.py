"""Matemática de torneio PKO/bounty (progressive knockout).

Num PKO, eliminar um vilão paga a recompensa (bounty) dele AGORA — isso é
dinheiro morto extra no pote que o torneio normal não tem, e muda o call
correto radicalmente (calls "loose" viram certos).

Conversão bounty -> fichas: REGRA DA MEIA-PILHA (O'Kearney/Barrese, padrão
da literatura de PKO): no início do torneio, 1 bounty inicial vale ~metade
do stack inicial em fichas. Um bounty acumulado de N bounties iniciais vale
N × (stack_inicial / 2). Premissa declarada em toda resposta — é uma
aproximação boa no meio do torneio; perto da mesa final o ICM aperta por
cima.
"""
from __future__ import annotations

from app.analysis.tools import pot_odds


def bounty_em_fichas(bounty_do_vilao: float, bounty_inicial: float,
                     stack_inicial: float) -> float:
    """Valor em FICHAS do bounty que você ganha ao eliminar o vilão.

    bounty_do_vilao e bounty_inicial na MESMA unidade (R$, USD ou pontos —
    tanto faz, só a razão importa)."""
    if bounty_inicial <= 0 or stack_inicial <= 0:
        raise ValueError("bounty_inicial e stack_inicial devem ser positivos")
    return (bounty_do_vilao / bounty_inicial) * stack_inicial / 2.0


def pko_call(pot: float, to_call: float, bounty_do_vilao: float,
             bounty_inicial: float, stack_inicial: float) -> dict:
    """Equity necessária pra pagar um all-in que pode ELIMINAR o vilão.

    O bounty entra como dinheiro morto: eq = to_call/(pot+to_call+bounty_fichas).
    Retorna também a conta SEM bounty (torneio normal) pro coach mostrar o
    desconto — é onde o aluno vê por que PKO paga mais solto."""
    if to_call <= 0:
        raise ValueError("to_call deve ser positivo")
    b_fichas = bounty_em_fichas(bounty_do_vilao, bounty_inicial, stack_inicial)
    eq_sem = pot_odds(pot, to_call)
    eq_com = to_call / (pot + to_call + b_fichas)
    return {
        "bounty_em_fichas": round(b_fichas, 1),
        "equity_necessaria_sem_bounty": round(eq_sem, 3),
        "equity_necessaria_com_bounty": round(eq_com, 3),
        "desconto_pct": round((eq_sem - eq_com) * 100, 1),
        "nota": (
            "premissa da MEIA-PILHA: 1 bounty inicial ≈ stack_inicial/2 em "
            "fichas (padrão da literatura de PKO). Vale para o miolo do "
            "torneio; na mesa final o ICM aperta a conta por cima. Só conta "
            "o bounty se o CALL cobre o vilão (elimina de verdade)."
        ),
    }
