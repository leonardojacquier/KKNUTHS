"""Sonda não pode disparar o alarme que ela deveria vigiar.

`sem_mao_na_conversa` existe para avisar que a ferramenta PERDEU a mão de um
aluno. A sonda de jornadas exercita esse caminho de propósito a cada deploy,
com chat 0 — 32 registros num dia. O sinal ficou afogado no meu próprio
ruído, e um aluno de verdade perdendo o contexto passaria despercebido.
"""
from app.bot import processing


def test_chat_de_sistema_nao_gera_alarme_de_contexto():
    """telegram_id <= 0 é sistema por convenção. A sonda passa por aqui todo
    deploy; se ela registrar, o alarme vira ruído."""
    gravados = []

    class _Repo:
        enabled = True

        def log_event(self, tg, user, event, detail=None):
            gravados.append((tg, event))

    original = processing.get_repository
    processing.get_repository = lambda: _Repo()
    try:
        processing.LAST_ANALYSIS[0] = {"context": {"modo": "teste"}}
        assert processing.conversation_hand(0) is None
        assert gravados == [], f"sonda poluiu o alarme: {gravados}"

        # e o de GENTE continua registrando — o alarme não pode emudecer
        processing.LAST_ANALYSIS[6452742024] = {"context": {"modo": "teste"}}
        assert processing.conversation_hand(6452742024) is None
        assert [e for _tg, e in gravados] == ["sem_mao_na_conversa"]
    finally:
        processing.get_repository = original
        processing.LAST_ANALYSIS.pop(0, None)
        processing.LAST_ANALYSIS.pop(6452742024, None)


def test_jornadas_continua_exercitando_o_caminho():
    """O conserto é no REGISTRO, não na cobertura: a sonda tem que seguir
    testando o guarda com chat sem conversa — é justamente o caso em que a
    remediação precisa dizer que perdeu a referência."""
    from app.bot import guarda_saida as g

    texto, specs = g.remediar(0, {"grafico", "numero"}, "flop")
    assert "perdi a referência" in texto and specs == []
