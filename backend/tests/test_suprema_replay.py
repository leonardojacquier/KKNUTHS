"""A derivação do endpoint da Suprema, conferida contra o código do replayer.

Não é palpite: o `main.45fc5.js` faz `token.substr(0,8)` e usa `?s=`. Dois
erros meus custaram uma rodada cada — mandar o `t` inteiro (devolve `-1`) e
usar POST (403 do CloudFront). Ambos viram teste aqui.
"""
from app.parsers.suprema_replay import (api_do_link, token_do_link,
                                        url_da_api)

# link REAL, mandado pelo admin
LINK = "https://r.supremapoker.net/?t=0s2kipvi002pt&er=5"


def test_token_sai_do_parametro_t():
    assert token_do_link(LINK) == "0s2kipvi002pt"
    assert token_do_link("https://r.supremapoker.net/") is None


def test_manda_so_os_8_primeiros():
    """O erro que devolveu `-1`: eu mandava os 13 caracteres do link."""
    assert url_da_api("0s2kipvi002pt").endswith("?s=0s2kipvi")
    assert "0s2kipvi002pt" not in url_da_api("0s2kipvi002pt")


def test_o_caractere_10_escolhe_o_ambiente():
    """substr(10,1): '0' dev, '1' homologação, qualquer outro produção."""
    assert "brazildev.zvga.me" in url_da_api("abcdefghij0xx")
    assert "braziluatcdn7.zvga.me" in url_da_api("abcdefghij1xx")
    # o link real tem '2' na posição 10 -> produção
    assert "ra.supremapoker.net" in url_da_api("0s2kipvi002pt")


def test_link_real_resolve_para_a_url_exata():
    assert api_do_link(LINK) == (
        "https://ra.supremapoker.net/supremaAPI/replayInfo.php?s=0s2kipvi")


def test_token_curto_nao_vira_chute():
    """Sem 8 caracteres não há prefixo — mandar um pedaço menor só geraria
    `-1` e pareceria 'a Suprema está fora'."""
    assert url_da_api("abc") is None
    assert url_da_api("") is None
    # token de 8 a 10 não tem posição 10: cai em produção, sem estourar
    assert "ra.supremapoker.net" in url_da_api("abcdefgh")


# pares (código, texto) tirados de uma mão REAL da Suprema — o próprio JSON
# traz as duas formas, então isto é gabarito do servidor, não meu
CARTAS_REAIS = {29: "Kd", 28: "Qd", 51: "3h", 38: "6c", 67: "3s",
                76: "Qs", 18: "2d"}


def test_decodifica_todas_as_cartas_de_uma_mao_real():
    from app.parsers.suprema_replay import _card, _cards

    for codigo, esperado in CARTAS_REAIS.items():
        assert _card(codigo) == esperado, codigo
    # board da mão: 3♥ 6♣ 3♠ Q♠ 2♦
    assert _cards([51, 38, 67, 76, 18]) == ["3h", "6c", "3s", "Qs", "2d"]


def test_naipe_segue_a_mesma_escada_da_pppoker():
    """1=♦ 2=♣ 3=♥ 4=♠ — igual à PPPoker, que usa base 256 em vez de 16."""
    from app.parsers.pppoker_replay import _SUIT as SUIT_PP
    from app.parsers.suprema_replay import _SUIT as SUIT_SU

    assert SUIT_SU == SUIT_PP


def test_carta_invalida_some_em_vez_de_virar_placeholder():
    """Mão com carta inventada é pior que mão incompleta: a análise sairia
    confiante e errada."""
    from app.parsers.suprema_replay import _card, _cards

    assert _card(0) is None and _card(15) is None      # rank fora de 2..14
    assert _card(999) is None and _card(None) is None
    assert _cards([51, 999, 38]) == ["3h", "6c"]
    assert _cards(None) == []


def test_manda_cabecalho_de_navegador():
    """A MESMA URL devolve 2 bytes (`-1`) para o User-Agent padrão do curl e
    13 kB para o Chrome. Sem estes cabeçalhos o parser conclui 'token
    inválido' sobre uma mão que existe."""
    from app.parsers.suprema_replay import _UA

    assert "Chrome/" in _UA["User-Agent"]
    assert _UA["Referer"].startswith("https://r.supremapoker.net")
    for obrigatorio in ("Origin", "Sec-Fetch-Site", "Accept"):
        assert _UA.get(obrigatorio), obrigatorio


# ------------------------------------------------------------- parse real
def _mao_real():
    import json
    import pathlib

    from app.parsers.suprema_replay import parse

    p = (pathlib.Path(__file__).parent / "sample_hands"
         / "suprema_replay.json")
    return parse(json.loads(p.read_text()))


def test_mesa_e_stacks_da_mao_real():
    """Torneio 2500/5000 ante 500, 8 jogadores, herói 'Knuth' no CO."""
    h = _mao_real()
    assert h.stakes.small_blind == 2500 and h.stakes.big_blind == 5000
    assert h.stakes.ante == 500
    assert len(h.players) == 8
    assert h.hero == "Knuth"
    heroi = next(p for p in h.players if p.is_hero)
    # `players.coins` é o stack ANTES do ante — 42197, e o evento de ante
    # deixa 41697. Usar o pós-ante encolheria todo mundo em 1 ante.
    assert heroi.stack == 42197 and heroi.position == "CO"
    assert heroi.seat == 4


def test_cartas_e_board_da_mao_real():
    h = _mao_real()
    assert h.hero_cards == ["Ac", "6s"]                    # A♣6♠
    assert h.final_board == ["3h", "6c", "3s", "Qs", "2d"]
    assert h.shown_cards["Goffi Sumido"] == ["Kd", "Qd"]
    assert h.shown_cards["gop"] == ["Kh", "Qh"]


def test_streets_e_board_progressivo():
    """`nextround` nomeia a street que ACABOU: o evento 'preflop' traz o
    FLOP. Ler o nome como 'board desta street' adiantaria uma carta."""
    from app.models.canonical import StreetName

    h = _mao_real()
    por_nome = {s.name: s for s in h.streets}
    assert por_nome[StreetName.FLOP].board == ["3h", "6c", "3s"]
    assert por_nome[StreetName.TURN].board == ["3h", "6c", "3s", "Qs"]
    assert por_nome[StreetName.RIVER].board == ["3h", "6c", "3s", "Qs", "2d"]
    # todo mundo all-in no pré: nenhuma ação pós-flop
    assert not por_nome[StreetName.FLOP].actions


def test_allin_vira_raise_ou_call_conforme_o_spot():
    """`allin` não é tipo de ação: é call, raise ou aposta que gastou tudo.
    Tratar como categoria própria apaga a agressão, que é o que a análise lê.
    """
    from app.models.canonical import ActionType, StreetName

    h = _mao_real()
    pre = next(s for s in h.streets if s.name == StreetName.PREFLOP)
    por_ator = {}
    for a in pre.actions:
        por_ator.setdefault(a.actor, []).append(a)

    # herói foi de 41697 sobre um raise de 10000 -> RAISE
    heroi = por_ator["Knuth"][-1]
    assert heroi.type == ActionType.RAISE and heroi.all_in
    assert heroi.amount == 41697 and heroi.to_amount == 41697

    # MP re-shove por 113652 sobre os 41697 do herói -> RAISE
    mp = por_ator["Goffi Sumido"][-1]
    assert mp.type == ActionType.RAISE and mp.to_amount == 123652

    # HJ foi all-in por MENOS que o MP (105000 < 123652): é CALL, não raise.
    # Chamar de raise inventaria agressão que não houve.
    hj = por_ator["gop"][-1]
    assert hj.type == ActionType.CALL and hj.all_in
    assert hj.to_amount == 105000

    assert all(a.type != ActionType.POST or a.post_type for a in pre.actions)


def test_ante_fica_fora_do_to_amount():
    """Ante não é aposta a igualar. Somá-lo inflaria o `to_amount` de todos
    e a MESMA mão sairia diferente conforme a sala — o parser da PPPoker
    também o exclui, e o motor de análise é um só."""
    from app.models.canonical import StreetName

    h = _mao_real()
    pre = next(s for s in h.streets if s.name == StreetName.PREFLOP)
    antes = [a for a in pre.actions if a.post_type == "ante"]
    assert len(antes) == 8 and all(a.to_amount == 0 for a in antes)
    # o raise do MP é 10000, não 10500
    mp = next(a for a in pre.actions
              if a.actor == "Goffi Sumido" and a.amount == 10000)
    assert mp.to_amount == 10000


def test_devolucao_nao_vira_jogada():
    """`return` (chips negativo) é aposta não paga voltando. Como ação, ela
    seria um 'call negativo' no meio da mão."""
    h = _mao_real()
    for s in h.streets:
        for a in s.actions:
            assert a.amount >= 0, f"{a.actor} {a.type} {a.amount}"


def test_potes_paralelos_e_vencedores():
    """Herói curto (42197) não disputa o pote paralelo. MP e HJ empataram
    com dois pares Q/3 e dividiram os dois potes."""
    h = _mao_real()
    assert h.total_pot == 263197
    assert h.collected["Goffi Sumido"] == 68296 + 63303
    assert h.collected["gop"] == 68295 + 63303
    assert "Knuth" not in h.collected          # perdeu tudo
    assert sum(h.collected.values()) == h.total_pot


def test_metadados_da_mao():
    from app.models.canonical import HandFormat

    h = _mao_real()
    assert h.source_format == "suprema_replay"
    assert h.format == HandFormat.TOURNAMENT
    assert h.hand_id == "072714625_30447128231_474109"
    assert "Suprema" in h.site and "14625" in h.site
    assert h.tournament_id == "47128231"


# ------------------------------------------------------------- ligação
def test_bot_reconhece_o_link_e_manda_para_o_parser():
    """Motor certo que ninguém chama não entrega nada — foi exatamente o que
    aconteceu com o gráfico de EV. O link tem que virar `suprema_replay`."""
    from app.bot.processing import replay_link_info

    r = replay_link_info(LINK)
    assert r["site"] == "suprema"
    # o link INTEIRO é a chave: a derivação do endpoint mora no parser
    assert r["share_key"] == LINK

    # link da Suprema sem token não vira análise (viraria `-1` mais tarde)
    assert replay_link_info("https://r.supremapoker.net/")["share_key"] is None


def test_pipeline_tem_o_ramo_suprema(monkeypatch):
    """O pipeline DESPACHA para o parser da Suprema.

    Substring no fonte de `ingest` passa mesmo se o ramo estiver morto. Aqui
    o parser é trocado por um espião: se ele não for chamado, o link cairia
    no detector de texto e viraria "não entendi".
    """
    from app.ingestion import pipeline

    chamou = []
    import app.parsers.suprema_replay as sr

    monkeypatch.setattr(sr, "fetch_and_parse",
                        lambda link: chamou.append(link) or None)
    pipeline.ingest(b"https://r.supremapoker.net/x?k=abc", "suprema_replay")
    assert chamou, "o pipeline não despachou para o parser da Suprema"


def test_handler_despacha_os_dois_clubes():
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers)
    assert '("pppoker", "suprema")' in fonte, (
        "o handler tratava só pppoker; sem os dois o link da Suprema volta "
        "para a mensagem de 'esse tipo eu não abro'")


def test_resposta_de_erro_da_aplicacao_nao_vira_mao():
    """`-1` chega com HTTP 200: quem confia no status importa lixo."""
    from app.parsers import suprema_replay as sr

    class _R:
        def read(self, _n=0):
            return b"-1"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    original = sr.urllib.request.urlopen
    sr.urllib.request.urlopen = lambda *a, **k: _R()
    try:
        assert sr.baixar(LINK) is None
    finally:
        sr.urllib.request.urlopen = original
