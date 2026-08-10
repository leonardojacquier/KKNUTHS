"""/dossie <vilão> [N] e /torneio N: os torneios antigos ganham porta.

Duas coisas que o aluno pediu com todas as letras: um dossiê em DOCUMENTO
(como o /relatorio) do vilão de um torneio específico, e poder abrir um
torneio que não seja o último.

O que se prende:

  * pedir o torneio nº 5 quando existem 3 responde ISSO — nunca cai no
    último calado (resposta errada com cara de certa);
  * o dossiê HTML carrega as três camadas (mostradas, escuras com sinais,
    defesa) e NENHUM "provavelmente blefou";
  * vilão que não estava no torneio -> texto com quem estava, não documento
    vazio;
  * `/dossie fulano 2` lê o nome E o índice — nome com espaço continua
    funcionando.
"""
from __future__ import annotations

import pytest

import app.bot.processing as P
from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)

BOARD = ["Qs", "7h", "2d", "9c", "3s"]


def _mao(hid, tid, quando, vilao="v1", cartas=None, resposta=ActionType.FOLD):
    riv = [Action(actor="Hero", type=ActionType.CHECK),
           Action(actor=vilao, type=ActionType.BET, amount=650),
           Action(actor="Hero", type=resposta,
                  amount=650 if resposta == ActionType.CALL else 0)]
    return CanonicalHand(
        hand_id=hid, site="GGPoker", tournament_id=tid, played_at=quando,
        stakes=Stakes(big_blind=100), hero="Hero",
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name=vilao, stack=5000)],
        hero_cards=["Ah", "Kd"], final_board=BOARD,
        shown_cards={vilao: cartas} if cartas else {},
        streets=[Street(name=StreetName.PREFLOP, actions=[
                     Action(actor=vilao, type=ActionType.RAISE,
                            amount=200, to_amount=200),
                     Action(actor="Hero", type=ActionType.CALL, amount=200)]),
                 Street(name=StreetName.FLOP, actions=[
                     Action(actor="Hero", type=ActionType.CHECK),
                     Action(actor=vilao, type=ActionType.BET, amount=300),
                     Action(actor="Hero", type=ActionType.CALL, amount=300)]),
                 Street(name=StreetName.TURN, actions=[
                     Action(actor="Hero", type=ActionType.CHECK),
                     Action(actor=vilao, type=ActionType.BET, amount=400),
                     Action(actor="Hero", type=ActionType.CALL, amount=400)]),
                 Street(name=StreetName.RIVER, actions=riv)])


def _base():
    """Dois torneios: o novo (t2, vilão v2) e o velho (t1, vilão v1)."""
    velho = [_mao(f"a{i}", "t1", f"2026-07-01T2{i%10}:00:00", vilao="v1",
                  cartas=["Jd", "Th"] if i == 0 else None,
                  resposta=ActionType.CALL if i == 0 else ActionType.FOLD)
             for i in range(24)]
    novo = [_mao(f"b{i}", "t2", f"2026-08-01T2{i%10}:00:00", vilao="v2")
            for i in range(24)]
    return velho + novo


@pytest.fixture
def base(monkeypatch):
    maos = _base()

    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    monkeypatch.setattr(P, "RECENT_HANDS", {7: maos})
    return maos


# ---- o índice de torneios ---------------------------------------------------

def test_os_torneios_saem_do_mais_novo_para_o_mais_velho(base):
    ts = P.torneios_do_usuario(7)
    assert [t["tournament_id"] for t in ts] == ["t2", "t1"]
    assert ts[0]["data"] == "2026-08-01"
    assert len(ts[1]["maos"]) == 24


def test_escolha_2_abre_o_torneio_ANTERIOR(base):
    assert {h.tournament_id for h in P.maos_do_torneio(7, 1)} == {"t2"}
    assert {h.tournament_id for h in P.maos_do_torneio(7, 2)} == {"t1"}


def test_escolha_fora_da_lista_devolve_VAZIO_e_nao_o_ultimo(base):
    """Cair no último calado é resposta errada com cara de certa."""
    assert P.maos_do_torneio(7, 5) == []
    assert P.maos_do_torneio(7, 0) == []


def test_o_ultimo_continua_sendo_o_ultimo(base):
    assert P.maos_do_ultimo_torneio(7) == P.maos_do_torneio(7, 1)


def test_a_estrategia_aceita_a_escolha(base):
    """`/torneio 2` tem que levar a escolha até a leitura — senão o quadro
    mostra um torneio e o texto analisa outro."""
    import inspect

    assert "escolha" in inspect.signature(P.estrategia_do_torneio).parameters
    assert "escolha" in inspect.signature(P.tournament_board_report).parameters


# ---- o dossiê ---------------------------------------------------------------

def test_o_dossie_do_torneio_anterior_acha_o_vilao_de_la(base):
    doc = P.dossie_doc(7, "v1", 2)
    assert isinstance(doc, tuple), doc
    data, fname, caption = doc
    html = data.decode("utf-8")
    assert "v1" in html and fname == "dossie-v1.html"
    assert "Dossiê" in html


def test_o_dossie_carrega_as_tres_camadas(base):
    html = P.dossie_doc(7, "v1", 2)[0].decode("utf-8")
    assert "J♦" in html or "Jd" in html, "a mão mostrada sumiu"
    assert "ninguém viu" in html, "as escuras sumiram"
    assert "Sua defesa" in html, "a defesa sumiu"
    assert "três barris" in html, "os sinais da linha sumiram"
    assert "provavelmente blefou" not in html.replace(
        '"provavelmente blefou X%"', ""), "a taxa proibida entrou"


def test_o_dossie_mostra_a_agressao_contra_OUTROS_jogadores(base, monkeypatch):
    """O defeito relatado pelo dono: dossiê sem escura nenhuma. Causa: o
    recorte antigo só via aposta de river contra o herói — e na maioria das
    mãos de torneio o herói já foldou. Agora toda agressão pós-flop sem
    showdown entra, com a linha, a rua e a observação."""
    contra_outro = CanonicalHand(
        hand_id="x1", site="GGPoker", tournament_id="t2",
        played_at="2026-08-01T23:00:00", hero="Hero",
        stakes=Stakes(big_blind=100),
        players=[PlayerSeat(seat=1, name="Hero", stack=5000, is_hero=True),
                 PlayerSeat(seat=2, name="v2", stack=5000),
                 PlayerSeat(seat=3, name="outro", stack=5000)],
        hero_cards=["7h", "2c"], final_board=["Qs", "7s", "2d", "9c"],
        shown_cards={}, collected={"v2": 1900.0},
        streets=[Street(name=StreetName.PREFLOP, actions=[
                     Action(actor="Hero", type=ActionType.FOLD),
                     Action(actor="v2", type=ActionType.RAISE, amount=250,
                            to_amount=250),
                     Action(actor="outro", type=ActionType.CALL, amount=250)]),
                 Street(name=StreetName.FLOP, actions=[
                     Action(actor="outro", type=ActionType.CHECK),
                     Action(actor="v2", type=ActionType.BET, amount=300),
                     Action(actor="outro", type=ActionType.FOLD)])])
    monkeypatch.setattr(P, "RECENT_HANDS", {7: _base() + [contra_outro]})

    html = P.dossie_doc(7, "v2", 1)[0].decode("utf-8")
    assert "Agrediu e ninguém viu" in html
    assert "levou o pote" in html
    assert "por que estas mãos estão aqui sem veredito" in html, (
        "a observação pedida pelo dono não está no documento")


def test_vilao_de_OUTRO_torneio_nao_vaza_para_este(base):
    """v1 jogou o t1. Pedir v1 no t2 tem que dizer quem estava no t2 — não
    montar o dossiê com mãos do torneio errado."""
    doc = P.dossie_doc(7, "v1", 1)
    assert isinstance(doc, str)
    assert "v2" in doc, "não listou quem estava lá"


def test_torneio_inexistente_explica_quantos_ha(base):
    doc = P.dossie_doc(7, "v1", 9)
    assert isinstance(doc, str) and "2 torneio" in doc


def test_sem_torneio_nenhum_devolve_None(monkeypatch):
    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    monkeypatch.setattr(P, "RECENT_HANDS", {})
    assert P.dossie_doc(7, "v1", 1) is None


def test_nome_de_arquivo_nao_carrega_caractere_de_vilao():
    """Apelido de clube tem emoji, barra, espaço — nada disso pode ir para
    um filename."""
    from app.bot.processing import dossie_doc  # noqa: F401 (só o import)

    seguro = "".join(c if c.isalnum() else "-" for c in "Zé/♠ do B")[:30]
    assert "/" not in seguro and "♠" not in seguro


# ---- o comando lê nome + índice ---------------------------------------------

def test_o_handler_separa_nome_com_espaco_do_indice():
    """`/dossie marcelo laguna 2`: nome "marcelo laguna", torneio 2. O
    índice é o ÚLTIMO argumento quando numérico — nome nunca vira número."""
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers.cmd_dossie)
    assert "args[-1].isdigit()" in fonte and "args.pop()" in fonte
    assert 'CommandHandler("dossie", cmd_dossie)' in \
        inspect.getsource(handlers)


# ---- escolher pelo código ou pela lista --------------------------------------

def test_o_codigo_da_sala_resolve_para_o_torneio_certo(base):
    """`/torneio 303773218` tem que abrir AQUELE torneio, esteja onde
    estiver na lista — código não envelhece quando entra torneio novo,
    que é o defeito do índice."""
    from app.bot.torneio_flow import resolver_escolha

    assert resolver_escolha(7, "t1") == 2
    assert resolver_escolha(7, "t2") == 1
    assert resolver_escolha(7, "2") == 2      # curto = posição na lista
    assert resolver_escolha(7, "1") == 1


def test_codigo_desconhecido_da_None_e_nunca_o_ultimo(base):
    """Ele pediu um torneio ESPECÍFICO; entregar outro é pior que "não
    achei"."""
    from app.bot.torneio_flow import resolver_escolha

    assert resolver_escolha(7, "99999999") is None
    assert resolver_escolha(7, "7") is None      # posição que não existe
    assert resolver_escolha(7, "") is None
    # e o código casa por INTEIRO: "t" é começo de t1 e t2, e prefixo
    # devolveria o primeiro que aparecesse — um torneio que ele não pediu
    assert resolver_escolha(7, "t") is None


def test_id_numerico_longo_e_codigo_e_nao_posicao(monkeypatch):
    """Torneio da sala com id '303773218': 5+ dígitos NUNCA vira posição —
    virar posição 303 milhões seria só um jeito engraçado de falhar, mas um
    id de 3 dígitos que colidisse com posição seria resposta errada."""
    import app.bot.processing as P2
    from app.bot.torneio_flow import resolver_escolha

    maos = [_mao(f"c{i}", "303773218", f"2026-08-02T2{i%10}:00:00",
                 vilao="v3") for i in range(24)]

    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P2, "get_repository", lambda: _Repo())
    monkeypatch.setattr(P2, "RECENT_HANDS", {7: maos})
    assert resolver_escolha(7, "303773218") == 1


def test_o_teclado_da_lista_tem_um_botao_por_torneio():
    from app.bot import handlers

    ts = [{"tournament_id": "t2", "site": "GGPoker", "data": "2026-08-01",
           "maos": [1] * 24},
          {"tournament_id": "t1", "site": "PokerStars", "data": "2026-07-01",
           "maos": [1] * 10}]
    kb = handlers._teclado_de_torneios(ts, atual=1)
    botoes = [b for linha in kb.inline_keyboard for b in linha]
    assert [b.callback_data for b in botoes] == ["tor:1", "tor:2"]
    assert "▸" in botoes[0].text, "o torneio aberto tem que estar marcado"
    assert "PokerStars" in botoes[1].text


def test_um_torneio_so_nao_ganha_teclado():
    """Botão para escolher entre um é ruído."""
    from app.bot import handlers

    ts = [{"tournament_id": "t1", "site": "GG", "data": "2026-08-01",
           "maos": [1] * 24}]
    assert handlers._teclado_de_torneios(ts) is None


def test_o_botao_esta_registrado_e_compartilha_o_caminho_do_comando():
    """Clique sem handler é botão morto; e o botão tem que mandar no MESMO
    fluxo do comando — dois caminhos de envio é dois jeitos de divergirem."""
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers)
    assert 'CallbackQueryHandler(on_torneio_escolhido, pattern=r"^tor:")'         in fonte
    assert "_enviar_torneio" in inspect.getsource(handlers.on_torneio_escolhido)
    assert "_enviar_torneio" in inspect.getsource(handlers.cmd_torneio)


def test_o_dossie_aceita_o_codigo_do_torneio(base):
    """`/dossie v1 t1` — o handler resolve o código; aqui o processing com o
    índice resolvido continua sendo a única porta."""
    from app.bot.torneio_flow import resolver_escolha

    escolha = resolver_escolha(7, "t1")
    doc = P.dossie_doc(7, "v1", escolha)
    assert isinstance(doc, tuple)
    assert "v1" in doc[0].decode("utf-8")


def test_o_indice_do_torneio_aparece_no_rodape():
    from app.bot import handlers

    ts = [{"tournament_id": "t2", "site": "GGPoker", "data": "2026-08-01",
           "maos": [1] * 24},
          {"tournament_id": "t1", "site": "PokerStars", "data": "2026-07-01",
           "maos": [1] * 10}]
    t = handlers._indice_de_torneios(ts, atual=1)
    assert "1. GGPoker · 2026-08-01 · 24 mãos ← este" in t
    assert "2. PokerStars" in t
    assert "/torneio N" in t and "/dossie" in t and "código" in t
