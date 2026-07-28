"""O funil parava entre o drill e a primeira mão própria.

Primeiro usuário externo, 28/07 02:01: /start, clicou em treinar em 4
segundos, respondeu dois drills na mão-DEMO, e saiu em 2min30 sem mandar
uma mão dele. Não desistiu — ninguém convidou. O drill acabava e pronto.
"""
from app.bot import processing


class _Mao:
    def __init__(self, hand_id):
        self.hand_id = hand_id


def _com_maos(maos):
    """Troca a fonte de mãos do usuário por uma lista controlada."""
    original = processing._user_hands
    processing._user_hands = lambda _tg: maos
    return original


def test_convite_diz_por_que_a_mao_DELE_importa():
    t = processing.texto_convite_primeira_mao()
    assert "mão de exemplo" in t
    assert "suas" in t and "vazamentos" in t
    # e diz COMO, com as três entradas que funcionam
    assert "print" in t and "arquivo" in t and "link" in t
    assert "PPPoker/Suprema" in t


def test_convida_quem_so_treinou_na_demo():
    original = _com_maos([])
    try:
        assert processing.merece_convite_primeira_mao(999, "demo-site")
    finally:
        processing._user_hands = original


def test_NAO_convida_quem_ja_mandou_mao():
    """Insistir com quem já usa vira ruído no fim de todo treino, e ruído a
    gente aprende a pular."""
    original = _com_maos([_Mao("PS-12345")])
    try:
        assert not processing.merece_convite_primeira_mao(999, "demo-site")
    finally:
        processing._user_hands = original


def test_NAO_convida_quando_o_drill_ja_foi_numa_mao_dele():
    original = _com_maos([])
    try:
        assert not processing.merece_convite_primeira_mao(999, "PS-999")
    finally:
        processing._user_hands = original


def test_mao_demo_no_historico_nao_conta_como_uso():
    """Quem só tem a demo salva continua sendo alguém que nunca mandou mão."""
    original = _com_maos([_Mao("demo-site"), _Mao("demo-site")])
    try:
        assert processing.merece_convite_primeira_mao(999, "demo-site")
    finally:
        processing._user_hands = original


def test_erro_ao_consultar_nao_vira_convite():
    """Na dúvida, não incomoda."""
    def _explode(_tg):
        raise RuntimeError("banco fora")

    original = processing._user_hands
    processing._user_hands = _explode
    try:
        assert not processing.merece_convite_primeira_mao(999, "demo-site")
    finally:
        processing._user_hands = original


def test_handler_mostra_convite_E_botao():
    """Instrução que exige digitar é instrução que não é seguida às 2 da
    manhã — o botão reaproveita o `go:enviar`, que já explica os formatos."""
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers.on_drill_answer)
    assert "texto_convite_primeira_mao" in fonte
    assert "merece_convite_primeira_mao" in fonte
    assert 'callback_data="go:enviar"' in fonte
    assert "convite_primeira_mao" in fonte, "o convite precisa virar evento"
    # o botão só sai junto do convite, não em todo drill
    assert "if convite:" in fonte
