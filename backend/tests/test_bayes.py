"""Shrinkage bayesiano: números honestos com amostra pequena (fase 1)."""
from pathlib import Path

from app.analysis.bayes import bayes_stats, fmt_rate, shrunk_af, shrunk_rate
from app.analysis.stats import compute_player_stats
from app.parsers import parse_text


def _hands():
    return parse_text(
        (Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt").read_text()
    )


def test_small_sample_never_screams_100pct():
    # caso real que nos queimou: 2 oportunidades, 2 3-bets -> "100%" cru
    mean, lo, hi = shrunk_rate(2, 2, 7.0, 25.0)
    assert mean < 20.0            # ancorado no field, não em 100%
    assert hi - lo > 10.0         # e o intervalo confessa a incerteza


def test_large_sample_dominates_prior():
    mean, lo, hi = shrunk_rate(300, 1000, 24.0, 40.0)
    assert abs(mean - 30.0) < 1.5  # o dado manda, o prior quase some
    assert hi - lo < 7.0           # intervalo estreito = cravado


def test_af_shrinks_toward_field():
    assert 1.5 < shrunk_af(3, 0) < 3.5   # 3 bets, 0 calls: cru seria infinito
    big = shrunk_af(300, 100)
    assert abs(big - 3.0) < 0.3          # amostra grande ~ AF cru (300/100)


def test_bayes_stats_from_real_hands():
    s = compute_player_stats(_hands(), player=None)
    b = bayes_stats(s)
    for k in ("vpip", "pfr", "three_bet"):
        assert 0.0 <= b[k]["lo"] <= b[k]["mean"] <= b[k]["hi"] <= 100.0
        assert not b[k]["firm"]          # 4 mãos não cravam nada
    assert b["af"]["mean"] > 0
    txt = fmt_rate(b["vpip"], "VPIP")
    assert "entre" in txt                # frase honesta com amostra pequena


def test_stats_report_exists_and_runs_offline():
    # regressão: o `def stats_report` sumiu numa edição e /stats quebrou em
    # produção sem nenhum teste acusar — este teste trava a porta
    import app.bot.processing as proc

    tg = 313131
    proc.RECENT_HANDS[tg] = _hands()
    try:
        msg = proc.stats_report(tg, "tester")
        assert msg and "Seu perfil" in msg
        assert "100%" not in msg          # shrinkage segura o 3-bet de amostra mínima
    finally:
        proc.RECENT_HANDS.pop(tg, None)


def test_leak_detector_and_study_plan():
    from app.analysis.leaks import detect_leaks, leaks_text

    hands = _hands()
    # amostra limpa: folds padrão não viram leak (nada de acusação vazia)
    assert detect_leaks(hands * 3) == []

    # agora o herói folda AKo em pote não aberto, 4 vezes: leak de verdade
    folded = next(h for h in hands if h.hand_id == "TM6146070321")
    fakes = []
    for i in range(4):
        fk = folded.model_copy(deep=True)
        fk.hand_id = f"FAKE{i}"
        fk.hero_cards = ["Ah", "Kc"]
        fakes.append(fk)
    leaks = detect_leaks(fakes)
    assert leaks and leaks[0]["leak"] == "open_perdido"
    assert leaks[0]["escorregadas"] == 4
    assert leaks[0]["custo_bb_100maos"] > 0
    txt = leaks_text(leaks)
    assert "custando" in txt and "4 de 4" in txt

    # 1 escorregada em 2 chances NÃO crava leak crônico (shrinkage segura)
    um_so = detect_leaks([fakes[0], folded])
    assert all(lk["escorregadas"] >= 1 for lk in um_so)  # se aparecer, é honesto


def test_range_tracker_updates_toward_value_on_big_bets():
    from app.analysis.rangetracker import RangeTracker

    tr = RangeTracker("CO", "open", dead=["Ah", "Qd"])
    board = ["Kh", "7d", "2c"]
    antes = tr.shares(board)
    tr.update(board, "bet", size_pct_pot=85)
    depois = tr.shares(board)
    # bomba de 85% do pote: fatia de mão forte SOBE, ar DESCE
    assert depois["forte"] > antes["forte"]
    assert depois["ar"] < antes["ar"]


def test_range_tracker_check_shifts_to_weak():
    from app.analysis.rangetracker import RangeTracker

    tr = RangeTracker("BTN", "open")
    board = ["As", "Td", "4c"]
    antes = tr.shares(board)
    tr.update(board, "check")
    depois = tr.shares(board)
    assert depois["forte"] < antes["forte"]  # check esconde pouco valor


def test_read_villain_full_line_and_odds():
    from app.analysis.rangetracker import odds_pt, read_villain

    out = read_villain(
        "CO", "open", ["Kh", "7d", "2c", "2s"],
        [{"board_cards": 3, "action": "bet", "size_pct_pot": 33},
         {"board_cards": 4, "action": "bet", "size_pct_pot": 80}],
        hero_cards=["Ah", "Qd"],
    )
    assert out["p_valor"] > out["p_blefe_ou_draw"]
    assert "pra 1" in out["leitura"] or "equilibrado" in out["leitura"]
    assert len(out["passos"]) == 2
    assert "estimativa" in out["atencao"]      # nunca vende certeza
    assert odds_pt(0.8, 0.2).startswith("cerca de 4 pra 1")
    assert "equilibrado" in odds_pt(0.5, 0.5)


def test_read_villain_dispatch():
    from app.agent.llm import _dispatch

    r = _dispatch("read_villain", {
        "position": "BTN", "preflop": "open",
        "board": ["9h", "8h", "2d"],
        "actions": [{"board_cards": 3, "action": "bet", "size_pct_pot": 70}],
        "hero_cards": ["Ac", "Kc"],
    })
    assert "leitura" in r and "fatias" in r
    # board com draws: a fatia de draw existe e é considerada
    assert r["fatias"]["draw"] > 0


def test_parser_captures_shown_cards():
    hands = _hands()
    sd = next(h for h in hands if h.hand_id == "TM6146070388")
    assert sd.shown_cards.get("Hero") == ["3c", "Ad"]
    assert sd.shown_cards.get("609c9948") == ["Tc", "Ts"]


def test_bucket_of_combo_extremes():
    from app.analysis.calibration import bucket_of_combo

    board = ["Kh", "7d", "2c"]
    assert bucket_of_combo(["Kd", "Kc"], board) == "forte"   # trinca
    assert bucket_of_combo(["4c", "3d"], board) == "ar"      # nada, sem draw


def test_showdown_observation_and_blend():
    from app.analysis.calibration import (
        calibrated_tables, empty_counts, observe_showdowns,
    )
    from app.analysis.rangetracker import LIKELIHOOD
    from app.models.canonical import (
        Action, ActionType, CanonicalHand, Street, StreetName,
    )

    # vilão mostra trinca no showdown e tinha APOSTADO o flop: 1 observação
    # (bet | forte)
    h = CanonicalHand(
        site="GGPoker", hand_id="CAL1", hero="Hero",
        shown_cards={"Hero": ["Ah", "Ad"], "vilao": ["Kd", "Kc"]},
        streets=[
            Street(name=StreetName.PREFLOP),
            Street(name=StreetName.FLOP, board=["Kh", "7d", "2c"], actions=[
                Action(actor="vilao", type=ActionType.BET, amount=100),
                Action(actor="Hero", type=ActionType.CALL, amount=100),
            ]),
        ],
    )
    counts = observe_showdowns([h, h])  # duplicada: dedupe por (site, hand_id)
    assert counts["bet"]["forte"] == 1
    assert sum(v for by in counts.values() for v in by.values()) == 1

    # blend: sem dado nenhum, tabela == prior
    assert calibrated_tables(empty_counts()) == {
        a: {b: LIKELIHOOD[a][b] for b in LIKELIHOOD[a]} for a in LIKELIHOOD}
    # com MUITO dado de "forte aposta", bet_big|forte sobe e check|forte cai
    heavy = empty_counts()
    heavy["bet"]["forte"] = 200
    t = calibrated_tables(heavy)
    assert t["bet_big"]["forte"] > LIKELIHOOD["bet_big"]["forte"]
    assert t["check"]["forte"] < LIKELIHOOD["check"]["forte"]


def test_tracker_loads_calibration_file(tmp_path, monkeypatch):
    import json

    from app.analysis import rangetracker as rt

    tables = {a: dict(rt.LIKELIHOOD[a]) for a in rt.LIKELIHOOD}
    tables["bet_big"]["forte"] = 0.9
    f = tmp_path / "calibration.json"
    f.write_text(json.dumps({"tables": tables}))
    monkeypatch.setenv("CALIBRATION_FILE", str(f))
    rt.reset_calibration_cache()
    try:
        assert rt._likelihood()["bet_big"]["forte"] == 0.9
    finally:
        rt.reset_calibration_cache()
    # sem arquivo: cai no prior sem quebrar
    monkeypatch.setenv("CALIBRATION_FILE", str(tmp_path / "nao_existe.json"))
    rt.reset_calibration_cache()
    try:
        assert rt._likelihood() == rt.LIKELIHOOD
    finally:
        rt.reset_calibration_cache()


def test_tilt_detector_chase_pattern():
    from app.analysis.mental import mental_from_series

    # 60 mãos: base VPIP ~25%, mas nas 8 mãos depois de cada pote perdido
    # grande o jogador abre quase tudo (chase clássico)
    nets, vpips = [], []
    for bloco in range(3):
        for i in range(12):                    # jogo normal
            nets.append(-1.0 if i % 4 == 0 else 0.0)
            vpips.append(i % 4 == 0)           # 25%
        nets.append(-22.0)                     # pote grande perdido
        vpips.append(True)
        for i in range(8):                     # janela pós-perda: abre tudo
            nets.append(-2.0)
            vpips.append(i % 8 != 7)           # ~87%
    found = mental_from_series(nets, vpips)
    tipos = [f["tipo"] for f in found]
    assert "tilt_chase" in tipos
    tilt = next(f for f in found if f["tipo"] == "tilt_chase")
    assert tilt["vpip_janela"] > tilt["vpip_base"] + 8
    assert tilt["saldo_janela_bb"] < 0
    assert "perseguindo prejuízo" in tilt["frase"]


def test_tilt_detector_quiet_on_steady_play():
    from app.analysis.mental import mental_from_series

    # mesmo VPIP antes e depois dos potes grandes: nenhum diagnóstico
    nets = ([-22.0] + [0.0] * 9 + [22.0] + [0.0] * 9) * 3
    vpips = [i % 4 == 0 for i in range(len(nets))]
    assert mental_from_series(nets, vpips) == []
    # amostra pequena nunca diagnostica
    assert mental_from_series([-22.0, -2.0], [True, True]) == []


def test_detect_mental_runs_on_real_hands():
    from app.analysis.mental import detect_mental, mental_text

    out = detect_mental(_hands())          # 4 mãos: sem diagnóstico, sem crash
    assert out == []
    assert mental_text(out) == ""
    assert "Tilt Detector" in mental_text(
        [{"frase": "depois de perder um pote grande você abre 40%"}])


def test_decision_stamp_independent_of_result():
    from app.analysis.handreport import build_report_html, decision_stamp, played_facts

    hands = _hands()
    a3o = next(h for h in hands if h.hand_id == "TM6146070388")
    stamp = decision_stamp(a3o, played_facts(a3o))
    assert stamp in ("decisão ✅", "decisão ❌", None)
    html = build_report_html(hands, "leitura")
    # o relatório explica o antídoto ao viés de resultado
    assert "não o desfecho" in html and "variância" in html


def test_tournament_upload_attaches_hand_by_hand_report():
    # feedback duro do admin: "pedi a análise completa das mãos" — upload de
    # torneio TEM que sair com o relatório mão a mão anexado, sempre
    import app.bot.processing as proc

    tg = 424299
    content = (Path(__file__).parent / "sample_hands" /
               "demo_kknuths_tournament.txt").read_bytes()
    reply = proc.process_upload(content, "txt", tg, "tester")
    assert reply
    docs = proc.pop_docs(tg)
    assert docs, "upload de torneio sem relatório mão a mão anexado"
    data, fname, caption = docs[0]
    assert fname.startswith("KKNuths-MaoAMao")
    html = data.decode("utf-8")
    assert "Análise mão a mão" in html
    assert html.count("class=hand") >= 20      # TODAS as mãos jogadas viram card
    assert "decisão" in html                    # selos decisão vs resultado
    proc.RECENT_HANDS.pop(tg, None)
    proc.LAST_ANALYSIS.pop(tg, None)


def test_report_embeds_simple_version_per_hand():
    from app.analysis.handreport import build_report_html

    hands = _hands()
    html = build_report_html(hands, "leitura", per_hand_analysis={
        "TM6146070388": {"analise": "análise técnica do spot",
                         "analise_simples": "versão de iniciante com analogia",
                         "veredito": "mista"},
    })
    assert "análise técnica do spot" in html
    assert "Explica mais simples" in html
    assert "versão de iniciante com analogia" in html
    assert "decisão ⚠️" in html                 # veredito 'mista' vira selo
    # compat: valor string (formato antigo) não quebra nem cria toggle vazio
    html2 = build_report_html(hands, "leitura",
                              per_hand_analysis={"TM6146070388": "só texto"})
    assert "só texto" in html2


def test_simplify_button_flow():
    # 🎈 "explica mais simples": reexplica a última fala do coach
    import app.bot.processing as proc
    from app.agent.llm import simplify

    assert simplify("equity 31% contra pot odds de 25%") is None  # offline
    tg = 555001
    proc.LAST_ANALYSIS[tg] = {
        "context": {"coaching_anterior": "call correto: equity 31% > 25%"},
        "history": [], "hand_row_id": None, "user_id": None,
    }
    try:
        out = proc.simplify_last(tg, "t")
        assert out and "embananei" in out       # offline: fallback amigável
        assert proc.simplify_last(999998, "t") is None  # sem contexto: None
    finally:
        proc.LAST_ANALYSIS.pop(tg, None)


def test_style_report_uses_corrected_numbers():
    import app.bot.processing as proc

    tg = 323232
    # 4 mãos < mínimo de 10 -> None (sem quebrar com o caminho bayesiano)
    proc.RECENT_HANDS[tg] = _hands()
    try:
        assert proc.style_report(tg, "tester") is None
    finally:
        proc.RECENT_HANDS.pop(tg, None)


def test_snapshot_image_routes_to_spot_analysis():
    # caso real: print da mesa no meio da mão era tratado como mão completa e
    # o coach "analisava" lances que nunca viu — análise saía nada a ver
    from app.bot.processing import _augment_snapshot
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)

    h = CanonicalHand(
        site="PokerStars", hand_id="vision-snapshot", hero="Hero",
        source_format="image", stakes=Stakes(small_blind=0.5, big_blind=1),
        players=[PlayerSeat(seat=i, name=f"p{i}", stack=50) for i in range(1, 8)]
        + [PlayerSeat(seat=8, name="Hero", stack=39.2, is_hero=True)],
        hero_cards=["Qs", "Kh"], total_pot=6.7,
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="p7", type=ActionType.CALL, amount=2, to_amount=2)])],
    )
    st = {"net_bb": 0, "spots": []}
    _augment_snapshot(st, h)
    assert "FOTO DA MESA" in st["modo"]
    assert "PROIBIDO narrar" in st["instrucao_snapshot"]
    assert st["spot_atual"]["equity_vs_maos_aleatorias"] is not None

    # mão de print COM a linha do herói lida e board: análise normal (sem modo)
    h2 = h.model_copy(deep=True)
    h2.final_board = ["Kd", "7c", "2s"]
    h2.streets[0].actions.append(
        Action(actor="Hero", type=ActionType.RAISE, amount=3, to_amount=3))
    st2 = {"net_bb": 0, "spots": []}
    _augment_snapshot(st2, h2)
    assert "instrucao_snapshot" not in st2


def test_student_numbers_are_valid_tool_inputs():
    # caso real: aluno narrou pote e sizings na legenda e o coach respondeu
    # "não consegui calcular o EV porque faltam os sizings" — número dito
    # pelo aluno é INSUMO legítimo; se faltar de verdade, pergunta o dado
    from app.agent.llm import _SYSTEM

    pt = _SYSTEM["pt"]
    assert "INSUMOS" in pt
    assert "ALUNO INFORMOU" in pt
    assert "PERGUNTE o dado exato" in pt
    en = _SYSTEM["en"]
    assert "student's own words" in en

    # e a instrução que acompanha o relato do usuário diz o mesmo
    import inspect

    from app.bot import processing

    src = inspect.getsource(processing._process_upload_inner)
    assert "INSUMOS válidos" in src
    assert "pergunte esse dado" in src


def test_coach_calls_are_low_temperature():
    # caso real: mesma mão (99) recebeu '3-beta' num dia e '3-bet só 25%'
    # no outro — temperature default (1.0) sorteava o conselho. Análise e
    # conversa rodam frias; extração de mão/imagem roda determinística.
    import inspect

    from app.agent import llm
    from app.analysis import handreport

    for fn in (llm.coach, llm.followup, llm.evaluate_line, llm.simplify,
               llm.synthesize_answer):
        assert "temperature=0.2" in inspect.getsource(fn), fn.__name__
    for fn in (llm.extract_from_hand_text, llm.extract_from_image):
        assert "temperature=0.0" in inspect.getsource(fn), fn.__name__
    assert "temperature=0.2" in inspect.getsource(
        handreport.per_hand_analysis_llm)

    # e o prompt exige veredito ancorado + coerência entre mensagens
    pt = llm._SYSTEM["pt"]
    assert "CONSISTÊNCIA DE VEREDITO" in pt
    assert "MESMO veredito" in pt
    src = inspect.getsource(llm.followup)
    assert "COERÊNCIA" in src


def test_each_print_gets_own_hand_id():
    # caso real: todo print virava hand_id 'vision-snapshot' e o upsert por
    # (user, site, hand_id) fazia cada foto SOBRESCREVER a anterior no banco —
    # 4 análises do dia apontavam para a mão de uma semana atrás
    from app.agent.llm import _fingerprint, _snapshot_to_canonical

    data = {"hero_cards": ["9h", "9s"], "site": "GGPoker",
            "blinds": {"small_blind": 1, "big_blind": 2}}
    a = _snapshot_to_canonical(data, fingerprint=_fingerprint(b"foto-A"))
    b = _snapshot_to_canonical(data, fingerprint=_fingerprint(b"foto-B"))
    assert a.hand_id != b.hand_id            # prints diferentes, linhas diferentes
    assert a.hand_id.startswith("vision-")
    # MESMO print reenviado -> mesmo id (dedupe continua funcionando)
    assert _fingerprint(b"foto-A") == _fingerprint(b"foto-A")
