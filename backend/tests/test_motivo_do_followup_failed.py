"""followup_failed sem motivo é um evento cego.

Caso real — 5 falhas em 7 dias: o Ricardo teve a MESMA pergunta falhando às
10:28 e às 12:39 (e o "pode me avisar quando resolver?" também falhou no
meio), e o primeiro followup da vida do usuário novo falhou às 16:38. O
banco só guardava a pergunta; a causa morria no log de processo da VPS.
"""
from app.agent import llm
from app.bot import processing


def test_falha_do_followup_guarda_o_motivo():
    llm.LAST_FOLLOWUP_ERROR = None

    class _Settings:
        anthropic_api_key = "chave-de-teste"
        analysis_model = "claude-opus-4-8"

    class _Exploso:
        def __init__(self, **kw):
            raise RuntimeError("overloaded_error: try later")

    import anthropic

    orig_cls = anthropic.Anthropic
    orig_settings = llm.get_settings
    anthropic.Anthropic = _Exploso
    llm.get_settings = lambda: _Settings()
    try:
        out = llm.followup({"analysis": {}}, [], "O fold não tem equidade?")
        assert out is None
        assert "overloaded_error" in (llm.LAST_FOLLOWUP_ERROR or "")
    finally:
        anthropic.Anthropic = orig_cls
        llm.get_settings = orig_settings


def test_o_evento_leva_o_motivo_junto():
    import inspect

    fonte = inspect.getsource(processing)
    trecho = fonte.split('"followup_failed"', 1)[1][:200]
    assert "motivo" in trecho, "o evento tem que carregar a causa"
