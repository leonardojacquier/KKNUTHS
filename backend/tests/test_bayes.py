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


def test_unreadable_image_with_caption_falls_back_to_narration(monkeypatch):
    # caso real: print ilegível + aluno narrou a mão -> resposta era
    # 'não consegui ler'; a narração tem que virar a fonte da análise
    from app.bot import processing as proc
    from app.ingestion.pipeline import IngestResult
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      Stakes, Street, StreetName)

    monkeypatch.setattr(
        "app.ingestion.pipeline.ingest",
        lambda *a, **k: IngestResult([], None, "image", 0.0, True, "ilegível"),
    )
    monkeypatch.setattr(proc, "ingest", lambda *a, **k: IngestResult(
        [], None, "image", 0.0, True, "ilegível"))

    narrated = CanonicalHand(
        site="GGPoker", hand_id="vision-abc", hero="Hero",
        source_format="txt", stakes=Stakes(small_blind=1, big_blind=2),
        hero_cards=["9h", "9s"], confidence=0.8,
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="UTG", type=ActionType.RAISE, amount=4, to_amount=4)])],
    )
    monkeypatch.setattr("app.agent.llm.extract_from_hand_text",
                        lambda text: narrated)

    captured = {}

    def fake_coach(structured, stats, **kw):
        captured["structured"] = structured
        return "análise ok"

    monkeypatch.setattr(proc, "coach", fake_coach)

    out = proc._process_upload_inner(
        b"\x89PNG...", "image", 999001, "t", "pt",
        proc.get_repository(), None,
        caption="99 no CO, 50bb, UTG abriu 2x",
    )
    assert "não consegui ler" not in out.lower()
    assert captured["structured"].get("relato_do_usuario")

    # sem legenda, print ilegível ainda retorna a mensagem de falha
    out2 = proc._process_upload_inner(
        b"\x89PNG...", "image", 999001, "t", "pt",
        proc.get_repository(), None, caption=None,
    )
    assert "não consegui ler" in out2.lower()


def test_log_event_survives_nul_bytes(monkeypatch):
    # caso real: excerpt binário de um print levava \x00 ao INSERT e o
    # Postgres derrubava o log_event inteiro (22P05) — a falha sumia do radar
    from app.db.repository import _scrub_nul

    dirty = {"excerpt": "PNG\x00\x00header", "nested": [{"a": "b\x00c"}], "n": 3}
    clean = _scrub_nul(dirty)
    assert "\x00" not in clean["excerpt"]
    assert clean["nested"][0]["a"] == "bc"
    assert clean["n"] == 3


def test_create_retries_without_temperature_when_model_rejects():
    # caso real: 'temperature is deprecated for this model' (400) derrubou a
    # leitura de prints INTEIRA no deploy da consistência — o wrapper refaz a
    # chamada sem o parâmetro e memoriza o modelo
    from app.agent import llm

    calls = []

    class FakeMessages:
        def create(self, **kw):
            calls.append(dict(kw))
            if "temperature" in kw:
                raise RuntimeError(
                    "Error code: 400 - `temperature` is deprecated for this model.")
            return "ok"

    class FakeClient:
        messages = FakeMessages()

    llm._NO_TEMP.discard("modelo-novo")
    out = llm._create(FakeClient(), model="modelo-novo", temperature=0.2,
                      max_tokens=10, messages=[])
    assert out == "ok"
    assert len(calls) == 2 and "temperature" not in calls[1]
    # memorizado: próxima chamada nem tenta com temperature
    calls.clear()
    out2 = llm._create(FakeClient(), model="modelo-novo", temperature=0.2,
                       max_tokens=10, messages=[])
    assert out2 == "ok" and len(calls) == 1 and "temperature" not in calls[0]
    llm._NO_TEMP.discard("modelo-novo")

    # erro que NÃO é de temperature propaga
    class FakeMessages2:
        def create(self, **kw):
            raise RuntimeError("overloaded")

    class FakeClient2:
        messages = FakeMessages2()

    import pytest
    with pytest.raises(RuntimeError, match="overloaded"):
        llm._create(FakeClient2(), model="outro", max_tokens=10, messages=[])


def test_shove_chart_matches_push_fold_verdict():
    # caso real: quiz de JTs UTG 8.9bb -> veredito 'fold' (shove = top 12%),
    # mas a tabela pedida saiu um range de abertura deep COM JTs —
    # o gráfico do spot de shove tem que sair do MESMO push_fold
    from app.agent.llm import charts_from_tool_call
    from app.analysis.pushfold import push_fold, shove_threshold
    from app.analysis.ranges import parse_range

    res = push_fold(["Td", "Jd"], 8.9, "UTG")
    assert res["decision"] == "fold" and res["shove_range_pct"] == 12.0

    # gancho automático: o resultado aproximado (sem 'role') gera o gráfico
    spec = charts_from_tool_call("push_fold",
                                 {"cards": ["Td", "Jd"], "stack_bb": 8.9,
                                  "position": "UTG"}, res)
    assert spec is not None and spec[0] == "range"
    assert spec[1] == "top 12%"
    assert "JTs" not in parse_range(spec[1])   # coerente: JTs fora do range

    # pedido explícito de tabela: position + stack_bb usa o mesmo limiar
    spec2 = charts_from_tool_call("send_range_chart",
                                  {"position": "UTG", "stack_bb": 8.9}, {"ok": True})
    assert spec2 is not None and spec2[1] == "top 12%"

    # acima de 20bb não existe shove aproximado
    assert shove_threshold("UTG", 35) is None


def test_chart_pipeline_coherence(monkeypatch):
    # auditoria de incoerências gráfico↔análise:
    # (a) dedupe: o mesmo range 2x vira 1 gráfico
    # (b) render que falha vira AVISO explícito (o texto prometeu o gráfico)
    # (c) gráfico órfão (TTL vencido) não gruda na resposta seguinte
    import time

    from app.bot import processing as proc

    rendered = []
    monkeypatch.setattr(
        "app.analysis.range_chart.render_spec",
        lambda spec: (b"PNG", f"ok {spec[1]}") if spec[1] != "quebra" else None,
    )

    specs = [("range", "top 12%", "Shove UTG"),
             ("range", "top 12%", "Shove UTG"),      # duplicata
             ("range", "quebra", "Range impossível")]  # render falha
    proc._stash_charts(111222, specs, None)
    charts = proc.pop_charts(111222)
    assert len(charts) == 2                      # dedupe aplicado
    assert charts[0] == (b"PNG", "ok top 12%")
    assert charts[1][0] == b"" and "Não consegui montar" in charts[1][1]

    # TTL: chart velho não é entregue
    proc.PENDING_CHARTS[111222] = (time.time() - 9999, [(b"PNG", "velho")])
    assert proc.pop_charts(111222) == []

    # docs seguem a mesma regra
    proc.PENDING_DOCS[111222] = (time.time() - 9999, [(b"X", "f.html", "c")])
    assert proc.pop_docs(111222) == []
    proc.PENDING_DOCS[111222] = (time.time(), [(b"X", "f.html", "c")])
    assert proc.pop_docs(111222) == [(b"X", "f.html", "c")]


def test_icm_chart_requires_real_bubble_factor():
    # bf chutado (default 1.5) no gráfico ICM contradiz o bubble factor do texto
    from app.agent.llm import _dispatch

    out = _dispatch("send_range_chart", {"role": "SB", "stack_bb": 10,
                                         "mode": "icm"})
    assert "error" in out and "bf" in out["error"]


def test_3bet_chart_title_names_the_opener():
    # 'Range de 3bet — CO' lia-se como range DO CO; é o range CONTRA o open de CO
    from app.agent.llm import charts_from_tool_call

    spec = charts_from_tool_call(
        "preflop_range", {"position": "CO", "action": "3bet"},
        {"range": "TT+, AJs+, KQs, A5s, A4s, AQo+"})
    assert spec is not None and "contra open de CO" in spec[2]


def test_audit_round2_sim_charts_bb_shove_and_snapshot():
    import inspect

    from app.agent import llm
    from app.bot import handlers, processing
    from app.db import repository

    # (2) simulação: gráfico do veredito 'e se' é coletado e enviado
    assert "collect_charts=chart_specs" in inspect.getsource(processing.sim_whatif)
    assert "_send_pending_charts" in inspect.getsource(handlers.on_sim_answer)

    # (5) 'Shove BB' não existe: dispatch rejeita e nenhum gráfico sai
    out = llm._dispatch("send_range_chart", {"position": "BB", "stack_bb": 9})
    assert "error" in out
    assert llm.charts_from_tool_call(
        "send_range_chart", {"position": "BB", "stack_bb": 9}, {"ok": True}) is None

    # (3) /evolucao grava os MESMOS números do /stats (bayes na flag)
    assert "bayes_stats" in inspect.getsource(
        repository.Repository.snapshot_player_stats)

    # (1) prompt manda o coach referenciar os gráficos automáticos
    assert "GRÁFICOS AUTOMÁTICOS" in llm._SYSTEM["pt"]


def test_post_analysis_buttons_by_context():
    # botões de pós-análise: vitrine contextual (torneio vs mão avulsa) —
    # features atrás de comando ninguém descobre (caso real: beta só usou
    # /relatorio depois de anúncio por mensagem)
    from app.bot.handlers import _post_kb

    def labels(kb):
        return [b.text for row in kb.inline_keyboard for b in row]

    t = labels(_post_kb("tournament"))
    assert any("Relatório" in x for x in t) and any("evolução" in x for x in t)
    h = labels(_post_kb("hand"))
    assert any("Simular" in x for x in h) and any("Range do spot" in x for x in h)
    # 🎈 sempre presente; nunca mais de 3 botões além dele
    assert any("simples" in x for x in t) and any("simples" in x for x in h)
    assert len(t) <= 4 and len(h) <= 4

    # o contexto vem do processing (torneio vs mão)
    import inspect

    from app.bot import processing
    assert "LAST_UPLOAD_KIND[telegram_id]" in inspect.getsource(
        processing._process_upload_inner)


def test_preparar_briefing_flow(monkeypatch):
    # /preparar fase 1: briefing das mãos do próprio aluno + metas parseadas
    from app.bot import processing as proc

    # extração de metas: só linhas META N:, no máximo 2
    metas = proc._extract_metas(
        "bla\nMETA 1: não pagar 3-bet fora de posição com par médio\n"
        "META 2: pausa de 2 min após pote grande perdido\nMETA 3: extra")
    assert len(metas) == 2 and metas[0].startswith("não pagar")
    assert proc._extract_metas("sem metas aqui") == []

    # prompt do briefing (ANTES do monkeypatch, que troca a função):
    # glossário + temperatura baixa + metas parseáveis
    import inspect

    from app.agent import llm
    src = inspect.getsource(llm.prepare_briefing)
    assert "TERMOS_REGRA" in src and "temperature=0.2" in src
    assert "META 1:" in src

    # fluxo: com mãos + LLM stubado, devolve o briefing e loga o evento
    from pathlib import Path

    from app.parsers import parse_text

    hands = parse_text((Path(__file__).parent / "sample_hands" /
                        "gg_tournament_paste.txt").read_text())
    proc.RECENT_HANDS[777001] = hands
    captured = {}

    def fake_briefing(ctx, lang="pt"):
        captured["ctx"] = ctx
        return "*Preparação*\nMETA 1: abrir os pares médios do CO\nMETA 2: pausa pós pote grande"

    monkeypatch.setattr("app.agent.llm.prepare_briefing", fake_briefing)
    out = proc.prepare_report(777001, "t", "turbo 25bb")
    assert out and "META 1" in out
    assert captured["ctx"]["torneio_de_hoje"]["descricao"] == "turbo 25bb"
    assert captured["ctx"]["torneio_de_hoje"]["formato"] == "turbo"
    assert captured["ctx"]["perfil"]["maos"] > 0
    assert "leaks" in captured["ctx"] and "tilt" in captured["ctx"]

    # sem mãos -> None (handler explica)
    proc.RECENT_HANDS.pop(777002, None)
    assert proc.prepare_report(777002, "t") is None


def test_preparacao_por_formato_de_torneio(monkeypatch):
    # a preparação se adapta ao TIPO de torneio: dicas verificadas em código
    # (não inventadas pelo LLM) + range do formato como imagem
    from app.analysis.prep import dicas_para, parse_tournament_profile

    p = parse_tournament_profile("turbo pko de $22 no GG, field mole")
    assert p["formato"] == "turbo" and p["pko"] is True
    assert p["buyin"] == 22.0 and p["field"] == "recreativo"
    d = dicas_para(p)
    assert any("push/fold" in x for x in d)        # dica de turbo
    assert any("ounty" in x for x in d)            # dica de PKO
    assert any("recreativo" in x for x in d)       # dica de field mole

    assert parse_tournament_profile("").get("formato") is None
    assert dicas_para({}) == []

    # turbo anexa o equilíbrio de shove como gráfico
    from pathlib import Path

    from app.bot import processing as proc
    from app.parsers import parse_text

    hands = parse_text((Path(__file__).parent / "sample_hands" /
                        "gg_tournament_paste.txt").read_text())
    proc.RECENT_HANDS[777003] = hands
    monkeypatch.setattr("app.agent.llm.prepare_briefing",
                        lambda ctx, lang="pt": "ok\nMETA 1: x\nMETA 2: y"
                        if ctx.get("dicas_do_formato") else None)
    stashed = []
    monkeypatch.setattr(proc, "_stash_charts",
                        lambda tg, specs, uid=None: stashed.append(specs))
    out = proc.prepare_report(777003, "t", "turbo de $11")
    assert out is not None                     # dicas chegaram ao LLM
    assert stashed and stashed[0][0][0] == "nashmode"


def test_phh_format_support():
    # caso real: admin subiu .phh (dataset do WSOP) e recebeu "formato não
    # suportado"; a mão era Seven Card Stud — a resposta deve NOMEAR o jogo
    from app.ingestion.pipeline import ingest
    from app.parsers.phh import parse_phh

    stud = """variant = 'F7S/8'
antes = [50000, 50000]
starting_stacks = [4575000, 1700000]
actions = ['d dh p1 ??????', 'd dh p2 7d2dTs', 'p1 f']
players = ['James Obst', 'Talal Shakerchi']
event = 'WSOP 2023'
"""
    hands, note = parse_phh(stud)
    assert hands == [] and "Seven Card Stud" in note

    r = ingest(stud.encode(), source_format="phh")
    assert not r.hands and "Seven Card Stud" in r.note

    # hold'em NT parseia de verdade: streets, blinds, showdown, herói
    nt = """variant = 'NT'
antes = [0, 0, 0]
blinds_or_straddles = [400, 800, 0]
min_bet = 800
starting_stacks = [20000, 30000, 25000]
actions = ['d dh p1 ????', 'd dh p2 ????', 'd dh p3 AhKd', 'p3 cbr 1600', 'p1 f', 'p2 cc', 'd db 7c2d9s', 'p2 cc', 'p3 cbr 2000', 'p2 f', 'p3 sm AhKd']
players = ['Alice', 'Bob', 'Hero']
event = 'Torneio Teste'
"""
    hands, note = parse_phh(nt)
    assert len(hands) == 1 and not note
    h = hands[0]
    assert h.hero == "Hero" and h.hero_cards == ["Ah", "Kd"]
    assert h.final_board == ["7c", "2d", "9s"]
    pre = h.streets[0]
    tipos = [(a.actor, a.type.value) for a in pre.actions if a.type.value != "post"]
    assert ("Hero", "raise") in tipos and ("Bob", "call") in tipos
    flop = h.streets[1]
    ftipos = [(a.actor, a.type.value) for a in flop.actions]
    assert ("Bob", "check") in ftipos and ("Hero", "bet") in ftipos
    assert h.shown_cards.get("Hero") == ["Ah", "Kd"]
    assert h.stakes.big_blind == 800 and h.format.value == "tournament"

    # detecção por conteúdo (colado como txt, sem extensão)
    r2 = ingest(nt, source_format="txt")
    assert r2.source_format == "phh" and len(r2.hands) == 1


def test_analise_fala_de_jogador_para_jogador():
    # feedback do admin: análise vinha "traduzindo" termo com parênteses
    # didáticos — didática é função EXCLUSIVA do 🎈; análise é poker nativo
    from app.agent.llm import TERMOS_REGRA, _SYSTEM

    pt = _SYSTEM["pt"]
    assert "LINGUAGEM ACESSÍVEL" not in pt          # regra antiga extinta
    assert "JOGADOR PARA JOGADOR" in pt
    assert "sem parênteses didáticos" in pt.lower() or \
           "sem \nparênteses" in pt or "parênteses didáticos" in pt
    assert "NÃO explique termos" in TERMOS_REGRA
    assert "EXCLUSIVA da simplificação" in TERMOS_REGRA


def test_deep_nunca_stack_fundo():
    # 'stack fundo' não existe no poker BR — é DEEP. O calque estava até
    # HARDCODED em títulos de gráfico e dicas (autoria nossa, não do LLM)
    import inspect

    from app.agent import llm
    from app.analysis import prep
    from app.bot import processing

    assert "'stack fundo'" in llm.TERMOS_REGRA          # banido no glossário
    for mod in (llm, prep, processing):
        src = inspect.getsource(mod)
        # fora da linha do glossário (que cita o calque para bani-lo),
        # nenhuma outra ocorrência
        assert src.count("stack fundo") <= (1 if mod is llm else 0), mod.__name__

    spec = llm.charts_from_tool_call(
        "preflop_range", {"position": "BTN", "action": "open"},
        {"range": "22+, A2s+"})
    assert "deep" in spec[2] and "fundo" not in spec[2]


def test_conversa_herda_teclado_contextual():
    # "nas minhas últimas conversas não tá aparecendo os botões": followup
    # agora herda o teclado do último upload (kind persiste, não é popped)
    import inspect

    from app.bot import handlers

    src = inspect.getsource(handlers)
    assert "LAST_UPLOAD_KIND.get(tg_user.id)" in src
    assert "LAST_UPLOAD_KIND.pop" not in src        # persistência, não consumo
    # followup passa kind E simplify (fallback 🎈 quando não houve upload)
    ot = inspect.getsource(handlers._route_text)
    assert "simplify_btn=True" in ot and "kind=LAST_UPLOAD_KIND.get" in ot


def test_botoes_agem_sobre_a_mao_analisada(monkeypatch):
    # "os botões deveriam ser funcionalidades referentes à análise que está
    # sendo feita": Simular mira a mão da análise; Range do spot usa o
    # stack/posição DELA (curto -> shove Nash; deep -> open da posição)
    from pathlib import Path

    from app.bot import processing as proc
    from app.parsers import parse_text

    hands = parse_text((Path(__file__).parent / "sample_hands" /
                        "gg_tournament_paste.txt").read_text())
    proc.RECENT_HANDS[888001] = hands

    # build_simulation com hand_id acha AQUELA mão (se ela tem decisão)
    from app.agent.analyzer import hand_timeline
    alvo = next(h for h in hands if h.hero and h.hero_cards and
                any(e["kind"] == "decision" for e in hand_timeline(h)))
    sim = proc.build_simulation(888001, alvo.hand_id)
    assert sim and sim["hand_id"] == alvo.hand_id

    # range do spot: curto -> top X%; deep -> open da posição
    proc.LAST_HAND_META[888002] = {"hand_id": "x", "position": "CO",
                                   "stack_bb": 9.0}
    png, cap = proc.spot_range_chart(888002)
    assert png and "Shove CO" in cap
    proc.LAST_HAND_META[888002] = {"hand_id": "x", "position": "CO",
                                   "stack_bb": 60.0}
    png2, cap2 = proc.spot_range_chart(888002)
    assert png2 and "open — CO" in cap2
    assert proc.spot_range_chart(888003) is None  # sem contexto -> aviso


def test_link_de_replay_deteccao():
    # caso real: usuário novo mandou link de replay e o coach tratou a URL
    # como pergunta. Agora é detectado (PPPoker puxa sozinho; outros pedem print)
    from app.bot.processing import replay_link_info

    assert replay_link_info("https://r.supremapoker.net/?t=ob2mfsa3002pt&er=5")
    # link comum (não replay) NÃO dispara
    assert replay_link_info("https://google.com") is None
    # url no meio de uma pergunta longa não dispara
    assert replay_link_info(
        "achei essa análise em https://replay.pppoker.net/x mas discordo "
        "totalmente do que ele falou sobre o meu 3-bet, o que você acha?"
    ) is None
    assert replay_link_info("qual o range de UTG?") is None


def _pppoker_fixture():
    # estrutura real de uma mão PPPoker (engenharia reversa da mão do Ricardo):
    # AKo, raise pré, call do CO, resto folda; flop Q34, check-fold do herói
    antes = [{"seatid": s, "chips": 50000, "hand_chips": 1_000_000, "type": 10}
             for s in (5, 7, 8, 0, 1, 2, 3, 4)]
    return {
        "share_key": "test-key", "create_time": 1,
        "info": {
            "room": {"small_blind": 200000, "ante": 50000, "dealer_seatid": 4,
                     "room_name": "Monster Stack", "gameid": "g1",
                     "mtt": {"is_ft": True}},
            "players": [
                {"user_name": "RicoFarah", "seatid": 0, "hand_chips": 21305500,
                 "uid": 1, "isSelf": True},
                {"user_name": "vilmots", "seatid": 1, "hand_chips": 6870800, "uid": 2,
                 "hunter_bonus": 150},
                {"user_name": "KKNUThS", "seatid": 2, "hand_chips": 6394900, "uid": 3},
                {"user_name": "ImperadorJuju", "seatid": 3, "hand_chips": 44596700, "uid": 4},
                {"user_name": "btn", "seatid": 4, "hand_chips": 4477000, "uid": 5},
                {"user_name": "sbp", "seatid": 5, "hand_chips": 16827800, "uid": 6},
                {"user_name": "bbp", "seatid": 7, "hand_chips": 13106900, "uid": 7},
                {"user_name": "arisn", "seatid": 8, "hand_chips": 26020400, "uid": 8},
            ],
            "cards": [269, 782],  # Kd, Ah = AKo (naipe 1=d, 3=h)
        },
        "flow": {
            "pre_flop": {"cards": [], "actions": antes + [
                {"seatid": 5, "chips": 200000, "type": 8},   # SB
                {"seatid": 7, "chips": 400000, "type": 9},   # BB
                {"seatid": 8, "chips": 0, "type": 1},        # fold
                {"seatid": 0, "chips": 1120000, "type": 4, "hand_chips": 20185500},  # raise
                {"seatid": 1, "chips": 0, "type": 1},
                {"seatid": 2, "chips": 0, "type": 1},
                {"seatid": 3, "chips": 1120000, "type": 3, "hand_chips": 43476700},  # call
                {"seatid": 4, "chips": 0, "type": 12},       # fold
                {"seatid": 5, "chips": 0, "type": 1},
                {"seatid": 7, "chips": 0, "type": 1},
            ], "pools": [{"poolid": 0, "pool": 3240000}]},
            "flop": {"cards": [268, 1027, 1028], "actions": [  # Qd 3s 4s
                {"seatid": 0, "chips": 0, "type": 2},        # check
                {"seatid": 3, "chips": 1820000, "type": 7},  # bet
                {"seatid": 0, "chips": 0, "type": 1},        # fold
            ], "chips_back": [{"seatid": 3, "chips": 1820000}]},
            "turn": {"cards": [], "actions": []},
            "river": {"cards": [], "actions": []},
            # showdown (formato real da sonda): mão completa revelada por
            # seatid em show_hands; carta única voluntária em show_cards
            "show_hands": [{"seatid": 3, "code": [520, 1032]}],   # 8c 8s
            "show_cards": [{"seatid": 1, "code": 771}],           # 3h
            "winning_info": [{"seatid": 3, "chips": 3240000, "profit": 2070000}],
        },
    }


def test_pppoker_replay_parser():
    from app.parsers.pppoker_replay import parse, share_key_from_url

    # extração do share_key do link colado
    url = ("https://replay.pppoker.net/new_game_record_publish/Frame/"
           "rls_20260624/index.html?shareKey=f48bcbb5-ef29-46d2-3a6c-5d8642064240&lan=pt")
    assert share_key_from_url(url) == "f48bcbb5-ef29-46d2-3a6c-5d8642064240"
    assert share_key_from_url("https://google.com") is None

    h = parse(_pppoker_fixture(), "f48bcbb5")
    assert h is not None
    assert h.hero == "RicoFarah"
    # naipes: 1=♦ 2=♣ 3=♥ 4=♠ (escada asiática; o vídeo do replay confirmou
    # que código 4 = espadas — o mapa antigo dava paus)
    assert set(h.hero_cards) == {"Kd", "Ah"}                 # AKo decodificado
    assert h.final_board == ["Qd", "3s", "4s"]               # flop decodificado
    assert h.stakes.big_blind == 400000 and h.stakes.small_blind == 200000
    assert h.stakes.ante == 50000
    assert h.format.value == "tournament"

    # posições: SB=seat5, BB=seat7, ordem horária → herói (seat0) é UTG+1
    pos = {p.name: p.position for p in h.players}
    assert pos["sbp"] == "SB" and pos["bbp"] == "BB"
    assert pos["btn"] == "BTN" and pos["RicoFarah"] == "UTG+1"

    # ações: pré = raise do herói + call do CO; flop = check/bet/fold
    pre = h.streets[0]
    tipos = [(a.actor, a.type.value) for a in pre.actions
             if a.type.value != "post"]
    assert ("RicoFarah", "raise") in tipos
    assert ("ImperadorJuju", "call") in tipos
    assert tipos.count(("arisn", "fold")) == 1
    flop = h.streets[1]
    ftipos = [(a.actor, a.type.value) for a in flop.actions]
    assert ftipos == [("RicoFarah", "check"), ("ImperadorJuju", "bet"),
                      ("RicoFarah", "fold")]
    assert h.total_pot == 3240000 and h.collected.get("ImperadorJuju") == 3240000

    # showdown: mão completa de flow.show_hands + carta única de show_cards
    assert h.shown_cards["ImperadorJuju"] == ["8c", "8s"]
    assert h.shown_cards["vilmots"] == ["3h"]

    # PKO: bounty capturado do hunter_bonus e exposto pro coach
    from app.agent.analyzer import analyze_hand
    vilmots = next(p for p in h.players if p.name == "vilmots")
    assert vilmots.bounty == 150
    a = analyze_hand(h)
    assert a["pko"] is True and 150 in a["bounties"].values()


def test_replay_link_detection_routes_pppoker():
    from app.bot.processing import replay_link_info

    r = replay_link_info(
        "https://replay.pppoker.net/new_game_record_publish/Frame/rls_20260624/"
        "index.html?shareKey=abc123def456aa99&lan=pt")
    assert r and r["site"] == "pppoker" and r["share_key"] == "abc123def456aa99"

    s = replay_link_info("https://r.supremapoker.net/?t=ob2mfsa3002pt&er=5")
    assert s and s["site"] == "suprema" and s["share_key"] is None

    assert replay_link_info("qual o range de UTG?") is None

    # link novo de compartilhamento (share.php em pppoker.club, shareKey UUID)
    # — antes caía no fallback genérico porque o host não batia
    p = replay_link_info(
        "https://pppoker.club/poker/api/share.php?share_type=handreview&"
        "uid=1151574&lang=pt&time=1784248958&"
        "shareKey=29e84d82-10f9-93aa-a5f1-78cd9edaf984")
    assert p and p["site"] == "pppoker"
    assert p["share_key"] == "29e84d82-10f9-93aa-a5f1-78cd9edaf984"

    # link SEM https:// (como o público copia do chat do clube) — caso real:
    # o admin colou assim e caía no coach em vez de abrir a mão
    s2 = replay_link_info(
        "replay.pppoker.net/new_game_record_publish/Frame/rls_20260624/"
        "index.html?shareKey=1027209d-560c-25ed-40c1-878cf23f0056&lan=pt")
    assert s2 and s2["site"] == "pppoker"
    assert s2["share_key"] == "1027209d-560c-25ed-40c1-878cf23f0056"
    # texto comum com ponto não vira link ("kknuths.com" citado numa frase longa)
    assert replay_link_info(
        "olha, o site kknuths.com/manual tem a explicação completa dessa "
        "jogada que a gente discutiu ontem, dá uma olhada com calma") is None


def test_drill_narracao_pre_flop_limpa():
    # feedback do admin: "a sequência das ações está confusa, precisa ser
    # contada a partir do UTG". Pré-flop cronológico (UTG-first nas mãos
    # reais), posts e folds escondidos, como um jogador conta.
    from app.bot.processing import _preflop_summary
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)

    # pote 3-bet: MP abre, herói folda, SB 3-beta, MP paga (ordem cronológica)
    pl = [
        PlayerSeat(seat=1, name="mp", stack=6000, position="MP"),
        PlayerSeat(seat=2, name="Hero", stack=3900, position="CO", is_hero=True),
        PlayerSeat(seat=3, name="sb", stack=5000, position="SB"),
        PlayerSeat(seat=4, name="bb", stack=6000, position="BB"),
        PlayerSeat(seat=5, name="utg", stack=6000, position="UTG"),
    ]
    pre = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="sb", type=ActionType.POST, amount=100, post_type="sb"),
        Action(actor="bb", type=ActionType.POST, amount=200, post_type="bb"),
        Action(actor="utg", type=ActionType.FOLD),
        Action(actor="mp", type=ActionType.RAISE, amount=400, to_amount=400),
        Action(actor="Hero", type=ActionType.FOLD),
        Action(actor="sb", type=ActionType.RAISE, amount=1100, to_amount=1200),
        Action(actor="bb", type=ActionType.FOLD),
        Action(actor="mp", type=ActionType.CALL, amount=800, to_amount=1200),
    ])
    h = CanonicalHand(site="x", hand_id="d1", hero="Hero",
                      stakes=Stakes(small_blind=100, big_blind=200),
                      players=pl, hero_cards=["5h", "4h"], streets=[pre])

    s = _preflop_summary(h)
    assert s.startswith("Pré-flop:")
    # cronológico: MP abre ANTES do SB 3-betar ANTES do MP pagar
    assert s.index("MP abre") < s.index("SB 3-beta") < s.index("MP paga")
    assert "MP paga 6bb" not in s and "MP paga" in s  # call sem valor
    assert "folda" not in s and "post" not in s.lower()  # posts/folds escondidos

    # stop_actor: para antes da ação do herói (decisão no pré) — só o open do MP
    s2 = _preflop_summary(h, stop_actor="Hero")
    assert "MP abre" in s2 and "3-beta" not in s2

    # foldou geral até o herói -> aviso curto
    pre2 = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="sb", type=ActionType.POST, amount=100, post_type="sb"),
        Action(actor="utg", type=ActionType.FOLD),
        Action(actor="mp", type=ActionType.FOLD),
    ])
    h2 = h.model_copy(update={"streets": [pre2]})
    assert _preflop_summary(h2, stop_actor="Hero") == "Pré-flop: folda até você"


def test_botoes_com_tamanho_real_em_bb():
    # feedback do admin: "só tem raise pote e coisas do tipo" — os botões de
    # sizing agora mostram o NÚMERO (bb) calculado do spot, capado no stack.
    from app.bot.processing import drill_buttons, sizing_amounts

    # enfrentando aposta: pote 9bb (já inclui a aposta), 3bb a pagar, 40bb stack
    amt = sizing_amounts(9.0, 3.0, 40.0)
    assert amt["raise3x"] == 9.0            # 3× a aposta
    assert amt["raisepot"] == 15.0          # pote + 2× aposta
    assert amt["allin"] == 40.0
    # cap no stack: sem sizing maior que o all-in
    curto = sizing_amounts(9.0, 3.0, 10.0)
    assert curto["raisepot"] == 10.0

    # fluxo em DOIS passos ("quero apertar no raise e escolher o tamanho"):
    # menu principal = ação; toque em Raise/Bet abre o submenu de tamanhos
    from app.bot.processing import drill_size_buttons

    d = {"pot_bb": 9.0, "to_call_bb": 3.0, "stack_bb": 40.0}
    main = " | ".join(b["text"] for r in drill_buttons(d) for b in r)
    assert "Fold" in main and "Call (3bb)" in main and "Raise" in main
    assert "3x" not in main                    # tamanhos só no submenu
    cbs = [b["callback_data"] for r in drill_buttons(d) for b in r]
    assert "drill:sizes" in cbs                # o toque que abre o submenu

    sub = " | ".join(b["text"] for r in drill_size_buttons(d) for b in r)
    assert "3x (9bb)" in sub and "Pote (15bb)" in sub
    assert "All-in (40bb)" in sub and "Voltar" in sub

    # sem aposta: frações do pote no submenu
    d2 = {"pot_bb": 12.0, "to_call_bb": 0, "stack_bb": 33.0}
    main2 = " | ".join(b["text"] for r in drill_buttons(d2) for b in r)
    assert "Check" in main2 and "Bet" in main2
    sub2 = " | ".join(b["text"] for r in drill_size_buttons(d2) for b in r)
    assert "⅓ pote (4bb)" in sub2 and "½ pote (6bb)" in sub2
    assert "Pote (12bb)" in sub2 and "All-in (33bb)" in sub2


def test_simular_mao_foldada_pre_vira_filme():
    # caso real do Leo: colou um replay onde FOLDOU o pré-flop e clicou simular.
    # Não há decisão dele pra rejogar (1 decisão, um fold) -> a sim marca
    # dead_end e o handler mostra o FILME da mão em vez de um beco sem saída.
    from app.bot import processing as proc
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)

    pl = [
        PlayerSeat(seat=1, name="Hero", stack=30000, position="UTG",
                   is_hero=True),
        PlayerSeat(seat=2, name="vilaoA", stack=40000, position="BTN"),
        PlayerSeat(seat=3, name="vilaoB", stack=50000, position="BB"),
    ]
    pre = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="vilaoB", type=ActionType.POST, amount=200, post_type="bb"),
        Action(actor="Hero", type=ActionType.FOLD),
        Action(actor="vilaoA", type=ActionType.RAISE, amount=600, to_amount=600),
        Action(actor="vilaoB", type=ActionType.CALL, amount=400, to_amount=600),
    ])
    flop = Street(name=StreetName.FLOP, board=["Qs", "3c", "4c"], actions=[
        Action(actor="vilaoA", type=ActionType.BET, amount=500),
        Action(actor="vilaoB", type=ActionType.CALL, amount=500),
    ])
    h = CanonicalHand(site="PPPoker · clube", hand_id="pppoker-fold-pre",
                      hero="Hero", stakes=Stakes(small_blind=100, big_blind=200),
                      players=pl, hero_cards=["7s", "2d"], streets=[pre, flop],
                      final_board=["Qs", "3c", "4c"],
                      shown_cards={"vilaoA": ["Ah", "Qd"]},
                      collected={"vilaoA": 2200}, total_pot=2200)

    tid = 555001
    proc.RECENT_HANDS[tid] = [h]
    try:
        sim = proc.build_simulation(tid, "pppoker-fold-pre")
        assert sim and sim.get("dead_end") is True
        # o filme da mão inteira sai como PNG válido
        png = proc.hand_film(tid, "pppoker-fold-pre")
        assert png and png[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        proc.RECENT_HANDS.pop(tid, None)

    # o filme termina com a banda "Resultado": showdown GRÁFICO (cartas do
    # vilão desenhadas via reveals) + quem levou o pote
    bands = proc.film_bands(h)
    assert bands[-1]["name"] == "Resultado"
    rv = bands[-1]["reveals"][0]
    assert rv["who"] == "vilaoA (BTN) mostra" and rv["cards"] == ["Ah", "Qd"]
    assert rv["desc"] == "par de Q, kicker A"
    assert "leva o pote (11bb)" in " ".join(bands[-1]["lines"])
    # pós-flop identifica o vilão por NOME (posição), não só posição
    flop_blob = " ".join(bands[1]["lines"])
    assert "vilaoA (BTN) aposta" in flop_blob


def test_leitura_deterministica_da_mao_feita():
    # caso real: coach disse "trinca de J" quando o herói (K♥T♠ no
    # J♠T♦J♦7♠6♥) tinha DOIS PARES (J e 10). A leitura agora é calculada.
    from app.agent.analyzer import analyze_hand
    from app.analysis.equity import describe_hand
    from app.models.canonical import (CanonicalHand, PlayerSeat, Stakes,
                                      Street, StreetName)

    board = ["Js", "Td", "Jd", "7s", "6h"]
    assert describe_hand(["Kh", "Ts"], board) == "dois pares (J e 10), kicker K"
    assert describe_hand(["Ad", "Qc"], board) == "par de J, kicker A"
    assert describe_hand(["Jc", "2c"], board) == "trinca de J"
    assert describe_hand(["Th", "Tc"], board) == "full house (10 cheio de J)"
    assert describe_hand(["Ah", "Kd"], ["9s", "9h", "9c", "As", "3d"]) \
        == "full house (9 cheio de A)"      # o cooler TT vs AK do 999-A-3
    assert describe_hand(["Kh", "Ts"], ["Js"]) is None  # sem 5 cartas

    h = CanonicalHand(
        site="x", hand_id="t1", hero="Hero",
        stakes=Stakes(small_blind=100, big_blind=200),
        players=[PlayerSeat(seat=1, name="Hero", stack=10000, is_hero=True)],
        hero_cards=["Kh", "Ts"], final_board=board,
        shown_cards={"vilao": ["Ad", "Qc"]},
        streets=[Street(name=StreetName.PREFLOP, actions=[])])
    a = analyze_hand(h)
    assert a["hero_final_hand"] == "dois pares (J e 10), kicker K"
    assert a["showdown_hands"]["vilao"] == "par de J, kicker A"

    # QUANDO a mão ficou pronta (caso real: coach disse que o KJ 'fechou a
    # sequência no river' quando a broadway estava pronta JÁ NO FLOP T-A-Q)
    h2 = h.model_copy(update={
        "hero_cards": ["Ah", "4d"],
        "final_board": ["Tc", "Ad", "Qd", "Ts", "8c"],
        "shown_cards": {"ImperadorJuju": ["Jd", "Kh"]},
    })
    bs = analyze_hand(h2)["hand_by_street"]
    assert bs["ImperadorJuju"]["flop"] == "sequência até A"   # pronta no flop
    assert bs["ImperadorJuju"]["river"] == "sequência até A"  # e segue no river
    assert bs["heroi"]["flop"] == "par de A, kicker Q"
    assert bs["heroi"]["turn"] == "dois pares (A e 10), kicker Q"


def test_figura_da_mesa_render():
    # figura da mesa: render deterministico (custo zero de LLM). Só garante
    # que sai um PNG válido e não quebra sem board/vilões.
    from app.analysis.hand_figure import render_hand_figure, spot_from_drill

    spot = {"hero_cards": ["Ah", "Kd"], "board": ["Qs", "3c", "4c"],
            "position": "BB", "stack_bb": 52, "pot_bb": 6.5, "to_call_bb": 4.5,
            "required_eq": 0.41, "street": "flop", "blinds": "100/200",
            "villains": [{"pos": "CO", "stack_bb": 48}]}
    png = render_hand_figure(spot)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 5000

    # pré-flop sem board, sem preço (check/bet) — não quebra
    png2 = render_hand_figure({"hero_cards": ["7h", "7c"], "board": [],
                               "position": "BTN", "stack_bb": 30, "pot_bb": 1.5,
                               "street": "preflop", "villains": []})
    assert png2[:8] == b"\x89PNG\r\n\x1a\n"

    # conversão do drill preserva os campos
    d = {"cards": ["As", "Ks"], "board": [], "position": "CO", "stack_bb": 40,
         "pot_bb": 2.5, "to_call_bb": 2, "street": "preflop",
         "villains": [{"pos": "MP", "stack_bb": 50}]}
    s = spot_from_drill(d)
    assert s["hero_cards"] == ["As", "Ks"] and s["villains"][0]["pos"] == "MP"


def test_storyboard_da_mao_render():
    # storyboard: mão inteira numa imagem (custo zero de LLM). Garante PNG
    # válido, altura dinâmica, e que não quebra sem math/veredito.
    from app.analysis.hand_figure import render_hand_strip

    spot = {
        "title": "Mão teste — SB", "hero_cards": ["6c", "4c"], "position": "SB",
        "stack_bb": 39, "blinds": "35/70",
        "streets": [
            {"name": "Pré-flop", "board": [], "pot_bb": 3.6,
             "lines": ["UTG abre 2.3bb", "VOCÊ paga"], "note": "multiway"},
            {"name": "River", "board": ["7c", "9d", "Qs", "Ad", "2s"],
             "pot_bb": 7.2, "lines": ["BB aposta 2.3bb", "VOCÊ tem 6-high"]},
        ],
        "math": {"equity": 0.06, "need": 0.24, "ev_bb": -1.7,
                 "note": "call precisaria de 24%"},
        "verdict": "boa", "verdict_text": "Fold é a jogada certa e você acertou.",
        "correct": "FOLD — 6-high não paga aposta de valor.",
    }
    png = render_hand_strip(spot)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 5000

    # sem math, sem decisão certa, veredito ruim — não quebra
    png2 = render_hand_strip({
        "title": "T", "hero_cards": ["As", "Ks"], "position": "BTN",
        "streets": [{"name": "Flop", "board": ["2c", "7d", "9h"],
                     "lines": ["check"]}],
        "verdict": "ruim", "verdict_text": "Passou a mão."})
    assert png2[:8] == b"\x89PNG\r\n\x1a\n"


def _odilon_hand():
    from app.models.canonical import (CanonicalHand, Stakes, PlayerSeat,
        Street, Action, ActionType, StreetName, HandFormat)

    def A(a, t, amt=0, to=0, post=None):
        return Action(actor=a, type=t, amount=amt, to_amount=to, post_type=post)

    players = [PlayerSeat(seat=8, name="Hero", stack=2730, position="SB",
                          is_hero=True),
               PlayerSeat(seat=1, name="BB", stack=2731, position="BB"),
               PlayerSeat(seat=3, name="UTG2", stack=5729, position="UTG+1")]
    return CanonicalHand(
        site="PS", hand_id="h1", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=35, big_blind=70, ante=8), hero="Hero",
        players=players, hero_cards=["6c", "4c"], streets=[
            Street(name=StreetName.PREFLOP, actions=[
                A("Hero", ActionType.POST, 35, post="sb"),
                A("BB", ActionType.POST, 70, post="bb"),
                A("UTG2", ActionType.RAISE, 161, to=161),
                A("Hero", ActionType.CALL, 126, to=161),
                A("BB", ActionType.CALL, 91, to=161)]),
            Street(name=StreetName.FLOP, board=["7c", "9d", "Qs"], actions=[
                A("Hero", ActionType.CHECK), A("BB", ActionType.CHECK),
                A("UTG2", ActionType.CHECK)]),
            Street(name=StreetName.TURN, board=["Ad"], actions=[
                A("Hero", ActionType.CHECK), A("BB", ActionType.CHECK),
                A("UTG2", ActionType.CHECK)]),
            Street(name=StreetName.RIVER, board=["2s"], actions=[
                A("Hero", ActionType.CHECK), A("BB", ActionType.BET, 160, to=160),
                A("UTG2", ActionType.FOLD), A("Hero", ActionType.FOLD)])],
        final_board=["7c", "9d", "Qs", "Ad", "2s"])


def test_treino_tem_variedade_nao_repete():
    # /treino não pode cair sempre nas mesmas 5 mãos parecidas: memória
    # anti-repetição + pool amplo + rotação de street.
    from app.parsers import parse_text
    from app.bot import processing
    from app.bot.processing import build_drill

    hands = parse_text(
        (Path(__file__).parent / "sample_hands" /
         "demo_kknuths_tournament.txt").read_text())
    uid = 90909
    processing.RECENT_HANDS[uid] = hands
    for g in (processing.RECENT_DRILLS, processing._RECENT_DRILL_STREETS):
        g.pop(uid, None)

    seen, streets = [], set()
    for _ in range(12):
        d = build_drill(uid)
        seen.append(d["hand_id"])
        streets.add(d["street"])

    assert len(set(seen)) >= 9            # variedade de mãos (era ~5 fixas)
    assert all(seen[i] != seen[i + 1] for i in range(11))  # sem repetir seguido
    assert len(streets) >= 2              # não é só um tipo de spot
    del processing.RECENT_HANDS[uid]
    processing.RECENT_DRILLS.pop(uid, None)
    processing._RECENT_DRILL_STREETS.pop(uid, None)


def test_simular_esta_mao_nunca_troca_de_mao():
    # bug: "Simular esta mão" / "/simular" traziam OUTRA mão quando a pedida não
    # dava pra simular. Agora: ou simula a pedida, ou devolve sentinela — nunca
    # substitui em silêncio.
    from app.bot import processing
    from app.bot.processing import build_simulation

    h = _odilon_hand()  # tem decisões, hand_id "h1"
    processing.RECENT_HANDS[4242] = [h]

    # mão pedida inexistente -> sentinela, NÃO a h1
    out = build_simulation(4242, "NAO_EXISTE")
    assert out and out.get("unsimulable") and out.get("hand_id") == "NAO_EXISTE"

    # mão certa -> simula ELA
    assert build_simulation(4242, "h1")["hand_id"] == "h1"

    # sem hand_id (comando puro) -> pega a melhor disponível
    assert build_simulation(4242, None)["hand_id"] == "h1"

    del processing.RECENT_HANDS[4242]


def test_llm_create_retry_transitorio(monkeypatch):
    # o 'me embananei' vinha de erro transitório (overloaded/5xx) não tratado.
    # _create deve reenviar e o _is_transient classificar certo.
    from app.agent import llm

    assert llm._is_transient(type("E", (Exception,), {"status_code": 529})())
    assert llm._is_transient(Exception("Overloaded"))
    assert not llm._is_transient(type("E", (Exception,), {"status_code": 400})())

    calls = {"n": 0}

    class Boom(Exception):
        status_code = 503

    class FakeMessages:
        def create(self, **kw):
            calls["n"] += 1
            if calls["n"] < 3:
                raise Boom("temporarily overloaded")
            return "ok"

    class FakeClient:
        messages = FakeMessages()

    import time as _t
    monkeypatch.setattr(_t, "sleep", lambda *_: None)
    out = llm._create(FakeClient(), model="m", temperature=0.2, messages=[])
    assert out == "ok" and calls["n"] == 3   # 2 falhas transitórias + sucesso


def test_decision_aggressor_marca_aposta_do_vilao():
    # a figura precisa mostrar o vilão da vez + tamanho da aposta
    from app.bot.processing import _decision_aggressor

    h = _odilon_hand()
    # decisão no river: a BB apostou 160 (=2.3bb) antes do herói
    pos, bet = _decision_aggressor(
        h, {"street": "river", "board": ["7c", "9d", "Qs", "Ad", "2s"]})
    assert pos == "BB" and bet == 2.3

    # a figura desenha sem quebrar com bet_bb no vilão
    from app.analysis.hand_figure import render_hand_figure
    png = render_hand_figure({
        "hero_cards": ["6c", "4c"], "board": ["7c", "9d", "Qs", "Ad", "2s"],
        "position": "SB", "stack_bb": 39, "pot_bb": 6.9, "to_call_bb": 2.3,
        "required_eq": 0.25, "street": "river", "blinds": "35/70",
        "villains": [{"pos": "BB", "stack_bb": 39, "bet_bb": 2.3, "to_act": True}]})
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_storyboard_board_nao_duplica():
    # bug real: parser que dá o board COMPLETO por street (flop=3, turn=4,
    # river=5) fazia o storyboard acumular -> turn com 7 cartas.
    from app.models.canonical import (CanonicalHand, Stakes, PlayerSeat, Street,
        Action, ActionType, StreetName, HandFormat)
    from app.bot.processing import hand_storyboard_streets

    def A(a, t, amt=0, to=0, post=None):
        return Action(actor=a, type=t, amount=amt, to_amount=to, post_type=post)

    players = [PlayerSeat(seat=1, name="Hero", stack=2000, position="BB",
                          is_hero=True),
               PlayerSeat(seat=2, name="SB", stack=2000, position="SB")]
    # boards CUMULATIVOS (como PokerStars): flop 3, turn 4, river 5
    h = CanonicalHand(
        site="PS", hand_id="cum", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=50, big_blind=100), hero="Hero",
        players=players, hero_cards=["7d", "7s"], streets=[
            Street(name=StreetName.PREFLOP, actions=[
                A("SB", ActionType.RAISE, 230, to=230),
                A("Hero", ActionType.CALL, 130, to=230)]),
            Street(name=StreetName.FLOP, board=["6s", "Ac", "3c"], actions=[
                A("SB", ActionType.BET, 200), A("Hero", ActionType.CALL, 200)]),
            Street(name=StreetName.TURN, board=["6s", "Ac", "3c", "2h"], actions=[
                A("SB", ActionType.BET, 400), A("Hero", ActionType.CALL, 400)]),
            Street(name=StreetName.RIVER, board=["6s", "Ac", "3c", "2h", "9d"],
                   actions=[A("SB", ActionType.CHECK),
                            A("Hero", ActionType.CHECK)])])
    bands = hand_storyboard_streets(h)
    by = {b["name"]: b["board"] for b in bands}
    assert by["Flop"] == ["6s", "Ac", "3c"]
    assert by["Turn"] == ["6s", "Ac", "3c", "2h"]           # 4, não 7
    assert by["River"] == ["6s", "Ac", "3c", "2h", "9d"]    # 5, não 12


def test_hand_storyboard_streets_e_spec():
    from app.bot.processing import (hand_storyboard_streets, _walk_hand,
                                    storyboard_spot_from_drill)
    from app.analysis.tools import pot_odds

    h = _odilon_hand()
    _, decs = _walk_hand(h)
    river_di = len(decs) - 1  # a decisão de fold no river

    # reveal: mostra a mão até o river COM a ação real; não spoila futuro
    reveal = hand_storyboard_streets(h, upto_di=river_di, reveal=True)
    assert [b["name"] for b in reveal] == ["Pré-flop", "Flop", "Turn", "River"]
    assert reveal[-1]["board"] == ["7c", "9d", "Qs", "Ad", "2s"]
    assert any("folda" in ln for ln in reveal[-1]["lines"])
    # pré-flop: pote 6.9bb (35+70+161+126+91 = 483 / 70)
    assert reveal[0]["pot_bb"] == 6.9

    # pergunta (flop, sem reveal): corta na street da decisão, sem ação do herói
    q = hand_storyboard_streets(h, upto_di=1, reveal=False)
    assert q[-1]["name"] == "Flop" and q[-1]["lines"] == []

    # spec do reveal: math determinística + veredito alinhado à escolha
    drill = {"cards": ["6c", "4c"], "position": "SB", "stack_bb": 39,
             "blinds": "35/70", "board": ["7c", "9d", "Qs", "Ad", "2s"],
             "pot_bb": 6.9, "to_call_bb": 2.3,
             "required_eq": round(pot_odds(6.9, 2.3), 3), "actual": "fold",
             "storyboard": reveal}
    spec = storyboard_spot_from_drill(drill, choice="fold")
    assert spec["verdict"] == "boa"          # fold bate a matemática → acertou
    assert "FOLD" in spec["correct"]
    assert spec["math"]["equity"] < 0.2 and spec["math"]["ev_bb"] < 0
    # escolha errada (call num spot -EV) → veredito ruim
    assert storyboard_spot_from_drill(drill, choice="call")["verdict"] == "ruim"


def test_veredito_stack_curto_jam_domina_call():
    # caso real: TT com 15bb no BTN — call era +EV e a imagem dizia "PAGAR",
    # mas o JAM domina (o coach dizia shove e a imagem contradizia). O
    # veredito agora consulta o equilíbrio de jam/fold no pré curto.
    from app.bot.processing import storyboard_spot_from_drill

    drill = {
        "cards": ["Ts", "Th"], "position": "BTN", "stack_bb": 15.0,
        "blinds": "1k/2k", "street": "preflop", "format": "tournament",
        "board": [], "pot_bb": 7.0, "to_call_bb": 4.0,
        "required_eq": 0.267, "actual": "call", "net_bb": 12.0,
        "villains": [{"pos": "CO", "bet_bb": 4.0}],
        "storyboard": [{"name": "Pré-flop", "board": [],
                        "lines": ["CO abre 4bb"], "pot_bb": 7.0}],
    }
    call = storyboard_spot_from_drill(drill, choice="call")
    assert call["correct"] == "ALL-IN (jam)"
    assert call["verdict"] == "mista"            # +EV, mas não é o ótimo
    assert "jam rende MAIS" in call["verdict_text"]
    assert storyboard_spot_from_drill(drill, choice="allin")["verdict"] == "boa"
    assert storyboard_spot_from_drill(drill, choice="fold")["verdict"] == "ruim"

    # deep (60bb) o equilíbrio de shove NÃO se aplica — veredito segue a conta
    deep = dict(drill, stack_bb=60.0)
    assert storyboard_spot_from_drill(deep, choice="call")["correct"] == "PAGAR (call)"


def test_timing_tells_snap_bet_forte():
    # 7 mãos: vilão aposta RÁPIDO (2s) e mostra valor no showdown — o sinal
    # "snap-bet = força" sai; com poucas ações com tempo, nada sai
    from app.analysis.villains import timing_tells
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)

    def mao(i):
        riv = Street(name=StreetName.RIVER,
                     board=["Ks", "9h", "4d", "2c", "9s"], actions=[
            Action(actor="Snap", type=ActionType.BET, amount=100, time_raw=2.0),
            Action(actor="Snap", type=ActionType.CHECK, time_raw=3.0),
        ])
        return CanonicalHand(
            site="x", hand_id=f"t{i}", hero="Hero",
            stakes=Stakes(small_blind=1, big_blind=2),
            players=[PlayerSeat(seat=1, name="Hero", stack=100, is_hero=True),
                     PlayerSeat(seat=2, name="Snap", stack=100)],
            hero_cards=["Ah", "Qd"],
            final_board=["Ks", "9h", "4d", "2c", "9s"],
            shown_cards={"Snap": ["9c", "9d"]},   # quadra: forte
            streets=[riv])

    hands = [mao(i) for i in range(7)]
    tt = timing_tells(hands, "snap")
    assert tt and tt["acoes_com_tempo"] == 14
    assert tt["mediana_agressao_s"] == 2.0
    assert any("força" in s for s in tt["sinais"])
    assert timing_tells(hands[:2], "snap") is None      # amostra curta


def test_risk_of_ruin_banca():
    import pytest as _pytest

    from app.analysis.bankroll import risk_of_ruin

    # 100 BI em MTT NÃO é ultra-seguro (literatura: é o mínimo) — ~5% de
    # ruína é o realismo do modelo; 250 BI derruba pra quase zero
    folgado = risk_of_ruin(250, roi_pct=20)
    assert folgado["risco_de_ruina_pct"] < 2
    medio = risk_of_ruin(100, roi_pct=20)
    apertado = risk_of_ruin(5, roi_pct=-20)
    assert apertado["risco_de_ruina_pct"] > 60
    assert (folgado["risco_de_ruina_pct"] < medio["risco_de_ruina_pct"]
            < apertado["risco_de_ruina_pct"])
    # determinístico: mesma pergunta, mesma resposta
    assert risk_of_ruin(30, 10) == risk_of_ruin(30, 10)
    assert "Monte Carlo" in folgado["nota"]
    with _pytest.raises(ValueError):
        risk_of_ruin(0.5)


def test_treino_de_leitura_de_maos():
    from app.bot import processing as proc
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)

    pre = Street(name=StreetName.PREFLOP, actions=[
        Action(actor="vilaoX", type=ActionType.RAISE, amount=6, to_amount=6),
        Action(actor="Hero", type=ActionType.CALL, amount=6, to_amount=6),
    ])
    h = CanonicalHand(
        site="x", hand_id="hr1", hero="Hero",
        stakes=Stakes(small_blind=1, big_blind=2),
        players=[PlayerSeat(seat=1, name="Hero", stack=100, is_hero=True),
                 PlayerSeat(seat=2, name="vilaoX", stack=100)],
        hero_cards=["Ah", "Qd"], streets=[pre],
        final_board=["Ks", "9h", "4d", "2c", "7s"],
        shown_cards={"vilaoX": ["Kd", "Jc"]})
    tid = 555777
    proc.RECENT_HANDS[tid] = [h]
    try:
        hr = proc.build_hand_reading(tid)
    finally:
        proc.RECENT_HANDS.pop(tid, None)
    assert hr and len(hr["options"]) == 4
    assert hr["options"][hr["correct"]] == ["Kd", "Jc"]
    assert hr["vilao"] == "vilaoX" and hr["story"]
    assert "par de K" in hr["leitura"]
    # iscas não colidem com board/herói/resposta
    usadas = set(h.final_board) | {"Ah", "Qd", "Kd", "Jc"}
    for i, o in enumerate(hr["options"]):
        if i != hr["correct"]:
            assert not set(o) & usadas


def test_mdf_e_alpha():
    # gabarito clássico: aposta de POTE -> MDF 50% / alpha 50%;
    # meia-pote -> MDF 66.7% / alpha 33.3%
    import pytest as _pytest

    from app.analysis.tools import mdf

    r = mdf(pot=100, bet=100)
    assert r["mdf_pct"] == 50.0 and r["alpha_pct"] == 50.0
    r2 = mdf(pot=100, bet=50)
    assert r2["mdf_pct"] == 66.7 and r2["alpha_pct"] == 33.3
    assert "defender" in r2["leitura"]
    with _pytest.raises(ValueError):
        mdf(0, 10)


def test_range_advantage_no_flop():
    from app.analysis.range_advantage import range_advantage

    # A72 rainbow: range do agressor (pares altos + AK) esmaga quem defendeu
    # com conectores baixos — c-bet pequeno e frequente
    r = range_advantage(["Ah", "7d", "2c"], "AA, KK, QQ, AK", "76s, 65s")
    assert r["equity_media"]["agressor"] > 60
    assert "PEQUENO" in r["veredito"] or "pequeno" in r["veredito"]

    # 765 two-tone: sets e duas pontas do defensor dominam overcards soltas
    r2 = range_advantage(["7h", "6h", "5c"], "AK, AQ", "77, 66, 55",
                         label_a="agressor", label_b="defensor")
    assert r2["equity_media"]["defensor"] > 60
    assert "chequar" in r2["veredito"] or "defensor" in r2["veredito"]

    import pytest as _pytest
    with _pytest.raises(ValueError):
        range_advantage(["Ah", "7d"], "AA", "KK")   # board curto


def test_blockers_no_river():
    from app.analysis.blockers import blocker_effects

    # board K♠9♠4♠2♥7♦; vilão com AQ/99/88: fortes = 3 sets de 9 (sem o 9♠
    # do board) + o flush A♠Q♠ = 4 combos. Herói com 9♦ bloqueia 2 (50%).
    r = blocker_effects(["9d", "Th"], ["Ks", "9s", "4s", "2h", "7d"],
                        "AQ, 99, 88")
    assert r["combos_fortes"] == 4
    assert r["por_carta"]["9d"]["combos_fortes_bloqueados"] == 2
    assert r["fortes_bloqueados_pct"] == 50.0
    assert "blefe" in r["leitura"]

    # sem bloqueio relevante
    r2 = blocker_effects(["Th", "8h"], ["Ks", "9s", "4s", "2h", "7d"],
                         "AQ, 99")
    assert r2["por_carta"]["Th"]["combos_fortes_bloqueados"] == 0


def test_pko_bounty_desconta_equity():
    # regra da meia-pilha: bounty de 2 bounties iniciais com stack inicial
    # 10k = 10k fichas de dinheiro morto extra no call
    import pytest as _pytest

    from app.analysis.pko import bounty_em_fichas, pko_call

    assert bounty_em_fichas(100, 50, 10_000) == 10_000
    r = pko_call(12_000, 8_000, 100, 50, 10_000)
    assert r["equity_necessaria_sem_bounty"] == 0.4      # 8k/(12k+8k)
    assert r["equity_necessaria_com_bounty"] == round(8_000 / 30_000, 3)
    assert r["desconto_pct"] > 10                        # o bounty muda a conta
    assert "meia-pilha" in r["nota"].lower() or "MEIA-PILHA" in r["nota"]
    with _pytest.raises(ValueError):
        pko_call(10, 0, 1, 1, 100)


def test_villain_profile_exploit_por_vilao():
    from app.analysis.villains import villain_profile
    from app.models.canonical import (Action, ActionType, CanonicalHand,
                                      PlayerSeat, Stakes, Street, StreetName)

    def mao(i, acao_vilao):
        pre = Street(name=StreetName.PREFLOP, actions=[
            Action(actor="Nit77", type=ActionType.POST, amount=2,
                   post_type="bb"),
            acao_vilao,
            Action(actor="Hero", type=ActionType.RAISE, amount=6, to_amount=6),
        ])
        return CanonicalHand(
            site="x", hand_id=f"m{i}", hero="Hero",
            stakes=Stakes(small_blind=1, big_blind=2),
            players=[PlayerSeat(seat=1, name="Hero", stack=200, is_hero=True),
                     PlayerSeat(seat=2, name="Nit77", stack=200)],
            hero_cards=["As", "Kd"], streets=[pre],
            shown_cards={"Nit77": ["Qh", "Qd"]} if i == 0 else {})

    # 20 mãos: vilão só joga 2 (call) e folda 18 -> nit
    hands = ([mao(i, Action(actor="Nit77", type=ActionType.CALL, amount=2))
              for i in range(2)]
             + [mao(i + 2, Action(actor="Nit77", type=ActionType.FOLD))
                for i in range(18)])
    prof = villain_profile(hands, "nit77")          # case-insensitive
    assert prof and prof["maos_na_base"] == 20
    assert prof["vpip"]["media"] < 20               # shrinkage puxa mas é nit
    assert prof["amostra"] == "média"
    assert any("nit" in e for e in prof["exploits"])
    assert prof["showdowns_vistos"][0]["cartas"] == ["Qh", "Qd"]
    # vilão inexistente
    assert villain_profile(hands, "fantasma") is None
    # amostra pequena: SEM dicas (ruído não vira conselho)
    poucos = villain_profile(hands[:5], "Nit77")
    assert poucos["exploits"] == [] and "aviso" in poucos


def test_graficos_sem_duplicata_e_com_ev_de_companhia():
    # feedback do admin: (1) o mesmo range saía DUAS vezes (push_fold +
    # send_range_chart geravam specs diferentes do mesmo conteúdo);
    # (2) o range Nash agora vem com o EV por mão como SEGUNDO gráfico
    import pytest as _pytest

    from app.bot import processing as proc

    solver = _pytest.importorskip("app.analysis.jam_fold_solver")
    if not solver.available():
        _pytest.skip("matriz não gerada")

    tid = 999321
    proc._stash_charts(tid, [
        ("nash", "SB", 10.0),                       # push_fold
        ("nashmode", "SB", 10.0, "freq", 1.5),      # send_range_chart (igual!)
        ("range", "AA, KK", "titulo A"),
        ("range", "AA, KK", "titulo B"),            # mesmo range, outro título
    ])
    charts = proc.pop_charts(tid)
    captions = [c for _, c in charts]
    # 3 gráficos: nash-freq (1x), o EV de companhia, e o range (1x)
    assert len(charts) == 3, captions
    assert any("EV" in c or "chip" in c for c in captions), captions


def test_usuario_zero_ganha_mao_demo():
    # item 6 do roadmap-10: quem chega sem mãos recebe uma mão-DEMO sintética
    # na memória (nunca no banco) — /treino e /simular funcionam no 1º minuto
    from app.bot import processing as proc

    tid = 888123
    proc.RECENT_HANDS.pop(tid, None)
    try:
        assert proc.ensure_demo_material(tid) is True
        drill = proc.build_drill(tid)
        assert drill and str(drill["hand_id"]).startswith("demo")
        sim = proc.build_simulation(tid, None)
        assert sim and sim.get("cards") and not sim.get("dead_end")
        # já tem material -> NÃO injeta de novo
        assert proc.ensure_demo_material(tid) is False
    finally:
        proc.RECENT_HANDS.pop(tid, None)


def test_leitura_dupla_de_print_aplica_correcao():
    # item 5 do roadmap-10: 2ª passada confere carta a carta; correções dos
    # campos críticos valem e as divergências viajam pro coach confirmar
    from app.agent.llm import _merge_vision_check

    data = {"hero_name": "H", "hero_cards": ["As", "Kd"],
            "board": ["Qs", "3c"], "players": [{"name": "H", "stack": 1000}]}
    check = {"confere": False,
             "divergencias": ["hero_cards: li A♠K♣, a 1ª leitura diz A♠K♦"],
             "correcao": {"hero_cards": ["As", "Kc"], "hero_stack": 1200}}
    merged, div = _merge_vision_check(data, check)
    assert merged["hero_cards"] == ["As", "Kc"]          # correção aplicada
    assert merged["players"][0]["stack"] == 1200
    assert merged["board"] == ["Qs", "3c"]               # sem correção: mantém
    assert div and "K♣" in div[0]

    # conferiu tudo: nada muda, sem divergências
    ok, div2 = _merge_vision_check(data, {"confere": True, "correcao": {}})
    assert ok == data and div2 == []


def test_conversa_persistida_sem_imagem_e_com_cap():
    # item 4 do roadmap-10: a conversa sobrevive a restart. Persiste SEM a
    # imagem (pesada) e com o histórico limitado; restaura no followup.
    from app.bot import processing as proc

    tid = 777001
    proc.LAST_ANALYSIS[tid] = {
        "context": {"analysis": {"hero_cards": ["As", "Kd"]}},
        "history": [{"q": f"q{i}", "a": f"a{i}"} for i in range(30)],
        "hand_row_id": None, "user_id": None,
        "image_b64": "x" * 100_000, "media": "image/jpeg",
    }
    saved = {}

    class _FakeRepo:
        enabled = True

        def set_conversation(self, t, state):
            saved[t] = state

    real = proc.get_repository
    proc.get_repository = lambda: _FakeRepo()
    try:
        proc.persist_conversation(tid)
    finally:
        proc.get_repository = real
        proc.LAST_ANALYSIS.pop(tid, None)
    st = saved[tid]
    assert "image_b64" not in st and "media" not in st
    assert len(st["history"]) <= proc._HISTORY_CAP
    assert st["context"]["analysis"]["hero_cards"] == ["As", "Kd"]


def test_auditor_noturno_pega_mao_quebrada_e_contradicao():
    # o "Leo automático": sanidade estrutural + classe TT/15bb em mãos reais
    import scripts.nightly_coherence as nc
    from app.models.canonical import (CanonicalHand, PlayerSeat, Stakes,
                                      Street, StreetName)

    ok = CanonicalHand(
        site="x", hand_id="ok1", hero="H",
        stakes=Stakes(small_blind=1, big_blind=2),
        players=[PlayerSeat(seat=1, name="H", stack=100, is_hero=True)],
        hero_cards=["As", "Kd"], final_board=["2h", "7c", "9d"],
        streets=[Street(name=StreetName.PREFLOP, actions=[])])
    assert nc.check_hand(ok) == []

    ruim = ok.model_copy(update={
        "hand_id": "bad1",
        "final_board": ["2h", "2h", "9d"],          # carta duplicada
        "shown_cards": {"vilao": ["Zz", "9d"]},     # carta inválida
    })
    probs = nc.check_hand(ruim)
    assert any("board" in p for p in probs)
    assert any("showdown" in p for p in probs)


def test_canario_imagem_nunca_contradiz_solver():
    # CANÁRIO anti-contradição (lição do TT/15bb): varre uma bateria de spots
    # curtos e PROÍBE a imagem dizer "PAGAR" onde o equilíbrio manda JAM.
    # Não testa um caso — testa a CLASSE do bug, antes de todo deploy.
    from app.analysis.pushfold import push_fold
    from app.bot.processing import storyboard_spot_from_drill

    hands = [["Ts", "Th"], ["As", "Kd"], ["9c", "9d"], ["Ah", "Qs"],
             ["Kh", "Js"], ["7s", "7d"], ["As", "5s"], ["Qd", "Jd"]]
    contradicoes = []
    for cards in hands:
        for stack in (8.0, 12.0, 15.0, 18.0):
            for pos in ("BTN", "CO", "SB"):
                drill = {
                    "cards": cards, "position": pos, "stack_bb": stack,
                    "blinds": "1k/2k", "street": "preflop",
                    "format": "tournament", "board": [],
                    "pot_bb": 7.0, "to_call_bb": 4.0, "required_eq": 0.267,
                    "actual": "call", "net_bb": 0.0,
                    "villains": [{"pos": "MP", "bet_bb": 4.0}],
                    "storyboard": [{"name": "Pré-flop", "board": [],
                                    "lines": ["MP abre 4bb"], "pot_bb": 7.0}],
                }
                spec = storyboard_spot_from_drill(drill, choice="call")
                pf = push_fold(cards, stack, pos)
                if (pf.get("applicable") and pf.get("decision") == "push"
                        and spec["correct"] == "PAGAR (call)"):
                    contradicoes.append(f"{cards} {stack}bb {pos}")
    assert not contradicoes, f"imagem diz PAGAR onde o solver manda JAM: {contradicoes}"


def test_show_reveal_foto_vs_texto():
    # regressão: quiz enviado como FOTO não tem texto pra editar — o gabarito
    # não pode usar edit_text (Telegram: "no text in the message to edit").
    import asyncio

    from app.bot.handlers import _show_reveal

    class Msg:
        def __init__(self, text=None):
            self.text = text
            self.calls = []

        async def edit_text(self, t, **kw):
            self.calls.append(("edit_text", t))

        async def edit_reply_markup(self, reply_markup=None):
            self.calls.append(("clear_markup", reply_markup))

        async def reply_text(self, t, **kw):
            self.calls.append(("reply_text", t))

    class Q:
        def __init__(self, msg):
            self.message = msg

    # mensagem de TEXTO (quiz diário): edita no lugar
    tm = Msg(text="pergunta")
    asyncio.run(_show_reveal(Q(tm), "gabarito"))
    assert [c[0] for c in tm.calls] == ["edit_text"]

    # mensagem de FOTO (/treino, sem .text): tira botões e manda msg nova
    pm = Msg(text=None)
    asyncio.run(_show_reveal(Q(pm), "gabarito"))
    assert [c[0] for c in pm.calls] == ["clear_markup", "reply_text"]
