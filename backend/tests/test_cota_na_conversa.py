"""A conversa com o coach entra na cota — com peso leve.

Diagnóstico de 06/09, item 14, ainda aberto em 25/09: só o upload passava
por check_quota. A conversa (Opus + ferramentas, o caminho mais caro por
mensagem) e o /preparar eram ilimitados por construção. "Sem isto não há
plano vendável."
"""
from __future__ import annotations

import app.quota as q


def setup_function():
    q.reset_memory()


def test_cinco_mensagens_pesam_uma_analise():
    tg = 4242
    antes = q.check_quota(tg, None).remaining
    for _ in range(q.MENSAGENS_POR_ANALISE - 1):
        q.consume_quota(tg, None, kind="conversa")
    assert q.check_quota(tg, None).remaining == antes, \
        "menos de N mensagens já custou uma análise inteira"
    q.consume_quota(tg, None, kind="conversa")
    assert q.check_quota(tg, None).remaining == antes - 1


def test_cota_esgotada_trava_a_conversa_e_diz_por_que():
    tg = 4243
    for _ in range(q.FREE_MONTHLY_ANALYSES):
        q.consume_quota(tg, None)
    txt = q.bloqueio_da_conversa(tg, None)
    assert txt and "acabaram" in txt.lower()
    assert "conversa" in txt.lower(), "o aluno tem que saber que o papo também conta"
    assert "me pergunta o que quiser" not in txt, "promessa que não vale mais"


def test_com_cota_a_conversa_segue():
    assert q.bloqueio_da_conversa(4244, None) is None


def test_admin_e_pro_nunca_travam():
    assert q.bloqueio_da_conversa(q.ADMIN_TELEGRAM_ID, None) is None
    assert q.bloqueio_da_conversa(1, {"id": "u", "plan": "pro"}) is None


def test_banco_instavel_nao_trava_a_conversa():
    """Fail-closed é do upload. Travar o papo por um soluço do banco custa
    mais que algumas respostas."""
    class _RepoSemUser:
        enabled = True

    assert q.bloqueio_da_conversa(4245, None, _RepoSemUser()) is None


def test_process_followup_e_preparar_passam_pela_cota():
    import inspect

    from app.bot import processing

    fu = inspect.getsource(processing.process_followup)
    assert "bloqueio_da_conversa" in fu and 'kind="conversa"' in fu
    # a cobrança vem DEPOIS da resposta: falha do LLM não custa ao aluno
    assert fu.index('"followup_failed"') < fu.index('kind="conversa"')
    prep = inspect.getsource(processing.prepare_report)
    assert "bloqueio_da_conversa" in prep and "consume_quota" in prep


def test_process_followup_bloqueado_nao_chama_o_modelo(monkeypatch):
    from app.agent import llm
    from app.bot import processing

    tg = 4246
    for _ in range(q.FREE_MONTHLY_ANALYSES):
        q.consume_quota(tg, None)
    chamou = []
    monkeypatch.setattr(llm, "followup",
                        lambda *a, **k: chamou.append(1) or "resposta")
    processing.LAST_ANALYSIS[tg] = {"context": {}, "history": [],
                                    "hand_row_id": None, "user_id": None}
    try:
        out = processing.process_followup(tg, "t", "e o river?")
    finally:
        processing.LAST_ANALYSIS.pop(tg, None)
    assert not chamou, "cota esgotada e o Opus rodou mesmo assim"
    assert "acabaram" in (out or "").lower()


def test_o_manual_nao_promete_conversa_de_graca():
    import pathlib

    md = (pathlib.Path(__file__).resolve().parents[2] / "MANUAL.md").read_text(
        encoding="utf-8")
    assert "não desconta da cota" not in md
    assert f"{q.MENSAGENS_POR_ANALISE} mensagens = 1 análise" in md
