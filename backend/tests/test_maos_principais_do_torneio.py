"""As 150 principais mãos do torneio — o pedido do dono, na íntegra:

    "se tiver torneios mais longos analisa as 150 principais mãos e o resto
     coloca algo mais simplificado e coloca o botão"

O teto de mãos que recebem análise de COACH era 40, e acima dele NENHUMA
recebia: um torneio de 90 mãos jogadas saía inteiro no veredito
determinístico. Agora o teto é 150 — e quando o torneio passa disso, o corte
deixa de ser "as 150 primeiras" (o começo do torneio, quando nada foi
decidido) e passa a ser as 150 mais importantes.

As que ficam de fora seguem no `played_fallback_verdict`, e o relatório DIZ
isso na mão: sem o aviso o aluno lê um resumo mecânico achando que o coach o
escreveu.

Tudo aqui é determinístico — o ranking é função pura e o coach entra mockado.
Nenhuma chamada de rede ou de LLM.
"""
from __future__ import annotations

from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  HandFormat, PlayerSeat, Stakes, Street,
                                  StreetName)

_BB = 100.0


def _mao(hand_id: str, *, net_bb: float = 0.0, aposta_bb: float = 1.0,
         allin: bool = False) -> CanonicalHand:
    """Mão de torneio sintética: o herói investe `aposta_bb` e sai com `net_bb`.

    Molde mínimo de propósito — o ranking olha all-in, |saldo em bb| e pote, e
    é exatamente o que estes três parâmetros controlam. Pote da mão = 1bb (o
    big blind postado) + `aposta_bb`.
    """
    aposta = aposta_bb * _BB
    ganho = (net_bb + aposta_bb) * _BB        # net = ganho - investido
    return CanonicalHand(
        hand_id=hand_id, site="ggpoker", format=HandFormat.TOURNAMENT,
        tournament_id="T1",
        stakes=Stakes(small_blind=_BB / 2, big_blind=_BB),
        hero="Hero", hero_cards=["Ah", "Kd"],
        players=[
            PlayerSeat(seat=1, name="Hero", stack=5000, position="BTN",
                       is_hero=True),
            PlayerSeat(seat=2, name="Vilao", stack=5000, position="BB"),
        ],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="Vilao", type=ActionType.POST, amount=_BB,
                   post_type="bb"),
            Action(actor="Hero", type=ActionType.RAISE, amount=aposta,
                   to_amount=aposta, all_in=allin),
            Action(actor="Vilao", type=ActionType.FOLD),
        ])],
        collected={"Hero": ganho} if ganho else {},
        played_at="2026-08-15T20:00:00Z",
    )


def test_ate_150_maos_ninguem_fica_de_fora_e_a_151a_entra_no_corte():
    """O teto de coach é 150 (era 40). Abaixo dele nada é descartado; acima,
    a mão mais irrelevante do torneio é a que sai."""
    from app.analysis.handreport import maos_principais

    maos = [_mao(f"H{i}", net_bb=float(i + 1)) for i in range(150)]
    assert len(maos_principais(maos)) == 150

    maos.append(_mao("MIUDA", net_bb=0.0, aposta_bb=0.1))
    escolhidas = maos_principais(maos)
    assert len(escolhidas) == 150
    assert "MIUDA" not in {h.hand_id for h in escolhidas}


def test_torneio_de_200_maos_manda_ao_coach_as_que_decidiram_o_torneio():
    """Fixture do pedido: 200 mãos jogadas, 150 coachadas. Todo all-in entra
    (mesmo com saldo miúdo) e as mãos de saldo zero e pote mínimo ficam fora."""
    from app.analysis.handreport import maos_principais

    allins = [_mao(f"JAM{i}", net_bb=0.1, aposta_bb=0.5, allin=True)
              for i in range(3)]
    swings = [_mao(f"SW{i}", net_bb=float(i + 1)) for i in range(147)]
    miudas = [_mao(f"MIUDA{i}", net_bb=0.0, aposta_bb=0.1) for i in range(50)]
    # os all-ins no MEIO do torneio: se o corte fosse "as 150 primeiras",
    # metade das miúdas entrava e os jams do fim ficavam de fora
    torneio = miudas[:25] + swings + allins + miudas[25:]

    escolhidas = {h.hand_id for h in maos_principais(torneio)}
    assert len(escolhidas) == 150
    assert {"JAM0", "JAM1", "JAM2"} <= escolhidas
    assert all(f"SW{i}" in escolhidas for i in range(147))
    assert not any(f"MIUDA{i}" in escolhidas for i in range(50))


def test_o_allin_passa_na_frente_do_saldo_maior():
    """A direção do dono: o que decidiu o torneio. Um jam de 0.1bb é uma
    decisão de torneio; um pote grande ganho sem risco de eliminação, não."""
    from app.analysis.handreport import maos_principais

    maos = [_mao("SWING", net_bb=80.0), _mao("JAM", net_bb=0.1, allin=True)]
    assert [h.hand_id for h in maos_principais(maos, teto=1)] == ["JAM"]


def test_com_saldo_igual_o_pote_maior_e_que_desempata():
    """Saldo zero pode ser pote grande devolvido — decisão real. O desempate
    por pote separa isso de um limp de 0.1bb."""
    from app.analysis.handreport import maos_principais

    maos = [_mao("PEQUENA", net_bb=0.0, aposta_bb=0.2),
            _mao("GRANDE", net_bb=0.0, aposta_bb=9.0)]
    assert [h.hand_id for h in maos_principais(maos, teto=1)] == ["GRANDE"]


def test_as_escolhidas_saem_na_ordem_do_torneio():
    """O corte escolhe QUAIS, não reordena: o lote do coach e o relatório
    continuam seguindo a linha do tempo da mesa."""
    from app.analysis.handreport import maos_principais

    maos = [_mao("PRIMEIRA", net_bb=1.0), _mao("MIUDA", net_bb=0.0,
                                               aposta_bb=0.1),
            _mao("ULTIMA", net_bb=90.0)]
    assert [h.hand_id for h in maos_principais(maos, teto=2)] == \
        ["PRIMEIRA", "ULTIMA"]


def test_o_relatorio_de_torneio_longo_pede_coach_para_as_150_principais(
        monkeypatch):
    """O seam que importa em produção: com 200 mãos jogadas o relatório
    mandava ZERO ao coach (o teto antigo de 40 era um corte seco). Agora manda
    as 150 principais — e o corte é o mesmo `maos_principais`, não uma segunda
    regra escondida no `processing`."""
    from app.analysis import allin_audit, handreport, tournament_board
    from app.bot import processing as proc

    allins = [_mao(f"JAM{i}", net_bb=0.1, aposta_bb=0.5, allin=True)
              for i in range(3)]
    swings = [_mao(f"SW{i}", net_bb=float(i + 1)) for i in range(147)]
    miudas = [_mao(f"MIUDA{i}", net_bb=0.0, aposta_bb=0.1) for i in range(50)]
    torneio = miudas[:25] + swings + allins + miudas[25:]

    class _Repo:
        enabled = True

        def get_or_create_user(self, *a, **k):
            return {"id": "u1"}

        def get_all_hands(self, user_id, limit=5000):
            return torneio

        def log_event(self, *a, **k):
            return None

    pedidas: dict = {}
    monkeypatch.setattr(proc, "get_repository", lambda: _Repo())
    monkeypatch.setattr(tournament_board, "render_tournament_board",
                        lambda *a, **k: (b"", ""))
    for nome in ("auditar_allins", "auditar_preflop_deep", "auditar_posflop"):
        monkeypatch.setattr(allin_audit, nome, lambda *a, **k: [])
    monkeypatch.setattr(allin_audit, "resumo_auditoria", lambda *a, **k: {})
    monkeypatch.setattr(handreport, "build_report_html",
                        lambda *a, **k: "<html></html>")
    monkeypatch.setattr(
        handreport, "per_hand_analysis_llm",
        lambda maos, **k: pedidas.setdefault("ids", [h.hand_id for h in maos])
        and {})

    assert proc.report_doc_for_user(111, "leo") is not None
    ids = set(pedidas["ids"])
    assert len(ids) == 150
    assert {"JAM0", "JAM1", "JAM2"} <= ids
    assert not any(f"MIUDA{i}" in ids for i in range(50))


def test_a_mao_fora_do_corte_avisa_que_o_texto_e_resumo_automatico():
    """Duas classes de texto no mesmo relatório sem aviso é o aluno achando
    que o coach escreveu o resumo mecânico. A mão sem análise de coach diz."""
    from app.analysis.handreport import build_report_html

    com, sem = _mao("COMCOACH", net_bb=5.0), _mao("SEMCOACH", net_bb=5.0)
    html = build_report_html([com, sem], per_hand_analysis={
        "COMCOACH": {"analise": "Bem jogada, o preço fechava.",
                     "veredito": "boa"}})
    cartoes = html.split("<div class=hand>")
    card_com = next(c for c in cartoes if "COMCOACH" in c)
    card_sem = next(c for c in cartoes if "SEMCOACH" in c)
    assert "resumo automático" in card_sem
    assert "resumo automático" not in card_com
