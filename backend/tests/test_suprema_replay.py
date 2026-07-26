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
