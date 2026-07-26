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
