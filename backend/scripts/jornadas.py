"""SONDA DE JORNADAS — o caminho do aluno entrega ARTEFATO?

Por que existe, e por que não é a sonda E2E: a e2e_probe fala com o Telegram
usando uma conta-teste que nunca foi criada. Conferi o banco — `bot_events`
não tem UM evento 'e2e' desde que ela foi escrita. Ou seja: a rede que eu
contava como proteção nunca esteve no ar.

Esta aqui roda o código de verdade EM PROCESSO: sem Telegram, sem conta, sem
LLM, sem custo. Ela não pergunta "deu erro?" — pergunta **"chegou o que o
aluno pediu?"**. É a diferença entre um teste verde e uma resposta útil.

DUAS PARTES:

  A. DADOS REAIS — percorre as conversas vivas no banco (todos os formatos
     de contexto que existem em produção) e exige que a mão resolva. Foi
     exatamente aqui que dois bugs se esconderam: quiz e simulador gravavam
     o contexto sem hand_id, e TODA ferramenta de mão morria depois deles.
     O gabarito não é meu: são as conversas que os alunos têm de fato.

  B. JORNADAS SINTÉTICAS — as contas que mais quebraram, cada uma exigindo
     número na saída: EV street a street multiway, potes paralelos, EV de
     all-in com overcall e a prova real.

Falhou -> avisa o admin no Telegram e sai com código 1 (o cron registra).
"""
from __future__ import annotations

import json
import sys
import traceback
import urllib.request

ADMIN_ID = 6452742024


def _avisar(texto: str) -> None:
    from app.config import get_settings

    token = get_settings().telegram_bot_token
    if not token:
        return
    body = json.dumps({"chat_id": ADMIN_ID, "text": texto[:3500],
                       "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


# ---------------------------------------------------------------- parte A
def jornadas_reais(repo, limite: int = 40) -> list[tuple[str, bool, str]]:
    """Cada conversa VIVA precisa resolver para uma mão (ou declarar que não
    é conversa de mão). É o detector da família de bugs de contexto."""
    from app.bot.processing import _hand_id_no_contexto

    out: list[tuple[str, bool, str]] = []
    try:
        linhas = (repo.client.table("conversation_state")
                  .select("telegram_id,state").limit(limite).execute().data
                  or [])
    except Exception as exc:
        return [("conversas: leitura do banco", False, str(exc)[:120])]
    if not linhas:
        return [("conversas: nenhuma ativa", True, "nada a conferir")]

    for row in linhas:
        st = row.get("state") or {}
        ctx = st.get("context") if isinstance(st.get("context"), dict) else {}
        nome = f"conversa {row.get('telegram_id')}"
        # conversa sem mão é legítima (coaching geral, plano, tilt)
        modo = str(ctx.get("modo") or "")
        tem_mao_esperada = bool(
            st.get("hand_row_id") or _hand_id_no_contexto(ctx)
            or ctx.get("analysis") or ctx.get("spot") or ctx.get("simulacao"))
        if not tem_mao_esperada:
            out.append((nome, True, f"sem mão por natureza ({modo[:30]})"))
            continue
        achou = bool(st.get("hand_row_id") or _hand_id_no_contexto(ctx))
        out.append((nome, achou,
                    "mão resolvida" if achou else
                    f"CONTEXTO SEM hand_id — chaves: {sorted(ctx)[:6]}"))
    return out


# ---------------------------------------------------------------- parte B
def _mao_multiway():
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)
    pre = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="Hero", type=ActionType.POST, amount=0.5, post_type="sb"),
        Action(actor="V1", type=ActionType.POST, amount=1, post_type="bb"),
        Action(actor="V2", type=ActionType.RAISE, amount=3, to_amount=3),
        Action(actor="Hero", type=ActionType.CALL, amount=2.5, to_amount=3),
        Action(actor="V1", type=ActionType.CALL, amount=2, to_amount=3)])
    flop = Street(name=StreetName.FLOP, board=["Qs", "Th", "4d"], actions=[
        Action(actor="Hero", type=ActionType.CHECK),
        Action(actor="V1", type=ActionType.CHECK),
        Action(actor="V2", type=ActionType.BET, amount=5),
        Action(actor="Hero", type=ActionType.CALL, amount=5),
        Action(actor="V1", type=ActionType.CALL, amount=5)])
    return CanonicalHand(
        site="probe", hand_id="probe-mw", hero="Hero",
        stakes=Stakes(small_blind=0.5, big_blind=1),
        players=[PlayerSeat(seat=1, name="Hero", stack=100, is_hero=True,
                            position="SB"),
                 PlayerSeat(seat=2, name="V1", stack=100, position="BB"),
                 PlayerSeat(seat=3, name="V2", stack=100, position="CO")],
        hero_cards=["Qd", "Jd"], shown_cards={"V2": ["Ah", "Qc"]},
        streets=[pre, flop], final_board=["Qs", "Th", "4d"], total_pot=24)


def _mao_allin_desigual():
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)
    pre = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="Curto", type=ActionType.RAISE, amount=10, to_amount=10,
               all_in=True),
        Action(actor="Medio", type=ActionType.RAISE, amount=25, to_amount=25,
               all_in=True),
        Action(actor="Grande", type=ActionType.CALL, amount=25, to_amount=25)])
    return CanonicalHand(
        site="probe", hand_id="probe-sp", hero="Curto",
        stakes=Stakes(small_blind=0.5, big_blind=1),
        players=[PlayerSeat(seat=1, name="Curto", stack=10, is_hero=True,
                            position="BTN"),
                 PlayerSeat(seat=2, name="Medio", stack=25, position="SB"),
                 PlayerSeat(seat=3, name="Grande", stack=40, position="BB")],
        hero_cards=["As", "Kd"],
        shown_cards={"Medio": ["Qh", "Qc"], "Grande": ["7s", "7d"]},
        streets=[pre, Street(name=StreetName.RIVER,
                             board=["Ah", "9c", "4d", "2s", "Jh"])],
        final_board=["Ah", "9c", "4d", "2s", "Jh"], total_pot=60)


def jornadas_sinteticas() -> list[tuple[str, bool, str]]:
    """Cada uma exige NÚMERO na saída — não basta 'não deu erro'."""
    out: list[tuple[str, bool, str]] = []

    def passo(nome, fn):
        try:
            ok, det = fn()
        except Exception as exc:
            ok, det = False, f"{type(exc).__name__}: {exc}"[:140]
        out.append((nome, ok, det))

    def ev_streets():
        from app.analysis.ev_streets import ev_por_street

        r = ev_por_street(_mao_multiway())
        com_ev = [d for d in r.get("decisoes", []) if d.get("ev_bb") is not None]
        return (bool(com_ev) and r.get("multiway") is True,
                f"{len(com_ev)} decisões com EV · custo "
                f"{r.get('custo_total_bb')}bb")

    def potes():
        from app.analysis.side_pots import ev_por_pote

        r = ev_por_pote(_mao_allin_desigual())
        # o curto NÃO pode disputar o pote paralelo
        paralelo = [p for p in r.get("potes", []) if not p.get("voce_disputa")]
        return (r.get("multiway") is True and bool(paralelo)
                and r.get("ev_liquido_bb") is not None,
                f"EV líquido {r.get('ev_liquido_bb')}bb · "
                f"{len(paralelo)} pote(s) fora do alcance")

    def guarda():
        from app.bot import guarda_saida as g

        pedido = g.pedido_do_aluno("Manda o gráfico de EV do flop")
        falhas = g.faltou(pedido, "não consigo montar isso", False)
        # chat 0 não tem conversa: a remediação tem que dizer isso com todas
        # as letras, nunca ficar em silêncio nem inventar conta
        texto, _specs = g.remediar(0, falhas, "flop")
        return (pedido == {"grafico", "numero"} and falhas == pedido
                and "perdi a referência" in texto,
                f"pedido={sorted(pedido)} faltou={sorted(falhas)}")

    def overcall():
        from app.analysis.allin_engine import available, solve_spot

        if not available():
            return True, "motor sem matriz (ambiente sem dados) — pulado"
        s = solve_spot("overcall", "BB", 12.0, vilao_pos="CO", pagaram=1)
        # o defeito clássico: pagar com 100% das mãos e 72o lucrativo
        return (s["acao_pct"] < 90 and s["ev"]["72o"] < 0,
                f"range {s['acao_pct']}% · 72o {s['ev']['72o']:+.2f}bb")

    def prova():
        from app.analysis.selfcheck import prova_real
        from app.api.site_assets import _demo_hand

        r = prova_real([_demo_hand()])
        return (r["problemas"] == 0 and r["classes"] >= 8,
                f"{r['classes']} classes · {r['problemas']} problemas")

    passo("EV street a street (multiway, sem all-in)", ev_streets)
    passo("potes paralelos (all-in com stacks diferentes)", potes)
    passo("guarda da saída (pedido vs entrega)", guarda)
    passo("motor de overcall multiway", overcall)
    passo("prova real (8 classes)", prova)
    return out


def main() -> int:
    from app.db import get_repository

    repo = get_repository()
    resultados = jornadas_sinteticas()
    if repo.enabled:
        resultados = jornadas_reais(repo) + resultados

    falhas = [r for r in resultados if not r[1]]
    for nome, ok, det in resultados:
        print(f"{'OK  ' if ok else 'FALHA'} {nome}: {det}")
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} jornadas OK")

    if repo.enabled:
        try:
            repo.log_event(0, "jornadas", "jornadas",
                           {"total": len(resultados), "falhas": len(falhas),
                            "quais": [f[0] for f in falhas][:6]})
        except Exception:
            pass
    if falhas:
        _avisar("🚨 *Sonda de jornadas: "
                f"{len(falhas)} de {len(resultados)} falharam*\n"
                + "\n".join(f"• {n}: {d}" for n, _o, d in falhas[:6]))
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        _avisar("🚨 *Sonda de jornadas QUEBROU* — ver /var/log/poker-jornadas.log")
        sys.exit(1)
