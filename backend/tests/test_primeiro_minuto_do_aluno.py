"""A jornada do aluno novo — onde a ferramenta falava e não entregava.

Três defeitos, todos no primeiro contato:

1. o /start dizia "já deixei um TORNEIO de teste carregado". O que existe é
   UMA mão sintética. Quem acreditava e digitava /torneio ou /relatorio
   ouvia que não havia material — a primeira coisa que a ferramenta fazia
   era falhar uma promessa dela mesma.
2. depois de responder o drill vinham QUATRO mensagens em rajada, e os
   quatro botões da última não incluíam a única ação que importa: mandar
   uma mão própria. Dois deles ("Simular esta mão", "Desafiar os amigos")
   agiam sobre a mão-DEMO — o aluno ia desafiar o clube com um spot que
   nunca jogou.
3. cota esgotada = beco sem saída. "Acabaram, renovam no próximo mês", sem
   data e sem alternativa, na tela em que ele acabou de mandar um arquivo.

Os testes de rajada CONTAM MENSAGENS de verdade em vez de ler o fonte: foi
lendo fonte que 14 testes passaram numa página em branco.
"""
from datetime import datetime, timezone

import pytest

from app.bot.processing import botoes_pos_treino


# ---- 1) o /start promete o que existe -------------------------------------

def test_start_nao_promete_torneio_que_nao_existe():
    from app.bot.handlers import WELCOME_SHORT

    assert "torneio de teste" not in WELCOME_SHORT.lower()
    assert "mão de teste" in WELCOME_SHORT.lower()


def test_o_material_de_boas_vindas_e_uma_mao_so():
    """A frase do /start só é verdade enquanto isto for uma mão."""
    from app.bot.processing import ensure_demo_material

    import app.bot.processing as proc

    proc.RECENT_HANDS.pop(-999, None)
    assert ensure_demo_material(-999) is True
    assert len(proc.RECENT_HANDS[-999]) == 1
    proc.RECENT_HANDS.pop(-999, None)


def test_a_mao_demo_nao_mente_sobre_o_proprio_formato():
    """125k/250k COM ante é forma de torneio; o modelo saía como cash (o
    default do CanonicalHand), então o metadado contradizia a mão."""
    from app.api.site_assets import _demo_hand

    h = _demo_hand()
    assert h.stakes.ante > 0
    assert h.format.value == "tournament"
    assert h.tournament_id


def test_uma_mao_so_nao_liga_o_quadro_de_torneio():
    """Marcar como torneio não pode fazer /torneio prometer de novo: o
    quadro exige 2+ mãos e continua exigindo."""
    import app.bot.processing as proc
    from app.bot.processing import (ensure_demo_material,
                                    tournament_board_report)

    proc.RECENT_HANDS.pop(-998, None)
    ensure_demo_material(-998)
    assert tournament_board_report(-998) is None
    proc.RECENT_HANDS.pop(-998, None)


# ---- 2) os botões depois do gabarito --------------------------------------

def test_aluno_novo_ve_o_botao_que_importa_primeiro():
    rows = botoes_pos_treino(True)
    primeiro = rows[0][0]
    assert primeiro["callback_data"] == "go:enviar"
    assert "mão minha" in primeiro["text"]


def test_aluno_novo_nao_e_convidado_a_desafiar_com_a_mao_demo():
    """Desafiar o clube com um spot que ele não jogou é promessa vazia."""
    tudo = [b["callback_data"] for row in botoes_pos_treino(True) for b in row]
    assert "pa:share" not in tudo
    assert "pa:sim" not in tudo, "simular a mão-DEMO não é o produto"
    assert len(tudo) == 2, "menos escolha para quem só tem uma boa"


def test_quem_ja_manda_mao_mantem_as_quatro_saidas():
    tudo = [b["callback_data"] for row in botoes_pos_treino(False) for b in row]
    assert set(tudo) == {"pa:sim", "go:treino", "pa:range", "pa:share"}


# ---- 2b) a rajada, contada de verdade -------------------------------------

class _Msg:
    """Mensagem do Telegram que registra o que foi enviado a partir dela."""

    def __init__(self, saidas, text="gabarito"):
        self.saidas = saidas
        self.text = text

    async def reply_text(self, texto, reply_markup=None, **k):
        self.saidas.append({"tipo": "texto", "texto": texto,
                            "markup": reply_markup})

    async def reply_photo(self, photo=None, caption=None, reply_markup=None,
                          **k):
        self.saidas.append({"tipo": "foto", "texto": caption,
                            "markup": reply_markup})

    async def reply_markdown(self, texto, reply_markup=None, **k):
        await self.reply_text(texto, reply_markup)

    async def edit_text(self, texto, **k):
        self.saidas.append({"tipo": "edicao", "texto": texto, "markup": None})


class _Query:
    def __init__(self, saidas, data="drill:fold"):
        self.data = data
        self.message = _Msg(saidas)

    async def answer(self):
        pass

    async def edit_message_reply_markup(self, **k):
        pass


class _Update:
    def __init__(self, saidas, data="drill:fold"):
        self.callback_query = _Query(saidas, data)
        self.effective_user = type("U", (), {
            "id": 4242, "username": "novato", "full_name": "Novato"})()


class _Ctx:
    def __init__(self):
        self.user_data = {}


def _rodar_gabarito(monkeypatch, *, convite: bool, filme: bool):
    """Executa on_drill_answer com o mundo externo desligado; devolve o que
    o aluno recebeu, em ordem."""
    import asyncio

    from app.bot import handlers
    import app.bot.processing as proc

    saidas: list[dict] = []
    drill = {"hand_id": "demo-site", "street": "flop", "pot_bb": 8,
             "to_call_bb": 3, "actual": "call", "position": "BB",
             "stack_bb": 30, "story": "história"}

    class _Repo:
        enabled = False

        def pop_pending_drill(self, *a):
            return None

        def set_pending_drill(self, *a):
            return None

        def quiz_streak_days(self, *a):
            return 0

        def log_event(self, *a, **k):
            return None

    monkeypatch.setattr(handlers, "get_repository", lambda: _Repo())
    monkeypatch.setattr(handlers, "reveal_drill", lambda d, c: "GABARITO")
    monkeypatch.setattr(proc, "merece_convite_primeira_mao",
                        lambda *a, **k: convite)
    monkeypatch.setattr(proc, "abrir_conversa", lambda *a, **k: None)
    monkeypatch.setattr(proc, "persist_conversation", lambda *a, **k: None)
    monkeypatch.setattr(proc, "storyboard_spot_from_drill",
                        lambda *a, **k: ({"x": 1} if filme else None))

    from app.analysis import hand_figure

    monkeypatch.setattr(hand_figure, "render_hand_strip",
                        lambda spec: b"PNG" if filme else None)
    monkeypatch.setattr(hand_figure, "spot_from_drill", lambda d: {"s": 1})

    update, ctx = _Update(saidas), _Ctx()
    ctx.user_data["drill"] = drill
    asyncio.run(handlers.on_drill_answer(update, ctx))
    return saidas


def test_aluno_novo_recebe_duas_mensagens_e_nao_quatro(monkeypatch):
    """Eram quatro em rajada; a terceira de quatro ninguém lê."""
    saidas = _rodar_gabarito(monkeypatch, convite=True, filme=True)
    assert len(saidas) == 2, [s["texto"] for s in saidas]
    assert saidas[0]["texto"].startswith("GABARITO")
    assert saidas[1]["tipo"] == "foto"


def test_o_botao_de_mandar_mao_vem_junto_do_filme(monkeypatch):
    """Sem markup no filme, a última coisa que o aluno vê é um beco."""
    saidas = _rodar_gabarito(monkeypatch, convite=True, filme=True)
    markup = saidas[-1]["markup"]
    assert markup is not None
    dados = [b.callback_data for linha in markup.inline_keyboard for b in linha]
    assert dados[0] == "go:enviar"


def test_sem_filme_os_botoes_ainda_chegam(monkeypatch):
    """Se o desenho falhar, o próximo passo não pode sumir junto."""
    saidas = _rodar_gabarito(monkeypatch, convite=True, filme=False)
    assert saidas[-1]["markup"] is not None
    assert saidas[-1]["texto"] == "E agora?"


def test_veterano_nao_recebe_convite(monkeypatch):
    saidas = _rodar_gabarito(monkeypatch, convite=False, filme=True)
    markup = saidas[-1]["markup"]
    dados = [b.callback_data for linha in markup.inline_keyboard for b in linha]
    assert "go:enviar" not in dados
    assert "pa:sim" in dados


# ---- 3) a cota esgotada ---------------------------------------------------

def test_cota_esgotada_diz_a_data_e_o_que_sobrou():
    from app.quota import texto_cota_esgotada

    txt = texto_cota_esgotada("free", datetime(2026, 8, 8, 12, tzinfo=timezone.utc))
    assert "01/09" in txt
    assert "/treino" in txt and "/range" in txt
    assert "próximo mês" not in txt, "sem data é o mesmo beco de antes"


def test_a_data_prometida_e_a_que_o_contador_usa():
    """`_count_used` conta a partir do dia 1 às 00:00 UTC. Se a mensagem
    disser outra data, o aluno volta um dia antes e apanha de novo."""
    from app.quota import dias_ate_renovar

    for agora, esperado in (
        (datetime(2026, 8, 8, 12, tzinfo=timezone.utc), "01/09"),
        (datetime(2026, 12, 31, 23, tzinfo=timezone.utc), "01/01"),
        (datetime(2026, 1, 31, 0, tzinfo=timezone.utc), "01/02"),
    ):
        assert dias_ate_renovar(agora)[1] == esperado


def test_o_teto_citado_e_o_do_plano_do_aluno():
    """Dizer '50' para quem tem 100 é errar na cara do testador convidado."""
    from app.quota import texto_cota_esgotada

    agora = datetime(2026, 8, 8, 12, tzinfo=timezone.utc)
    assert "50 análises" in texto_cota_esgotada("free", agora)
    assert "100 análises" in texto_cota_esgotada("piloto", agora)


@pytest.mark.parametrize("plano", ["free", "piloto"])
def test_o_caminho_do_upload_usa_esse_texto(monkeypatch, plano):
    """O texto bonito não vale nada se o upload continuar respondendo o
    beco antigo."""
    import app.bot.processing as proc
    from app.quota import QuotaResult

    monkeypatch.setattr(proc, "check_quota",
                        lambda *a, **k: QuotaResult(False, 0, plano))
    out = proc.process_upload(b"x", "txt", 4242, "novato")
    assert "01/" in out or "renova" in out
    assert "/treino" in out
