"""O farejador tem que reconhecer uma mão e recusar configuração de UI.

Testo as partes PURAS — as que decidem. A parte de rede não dá para testar
aqui (a política deste ambiente bloqueia o domínio do clube) e é justamente
por isso que ela é fina: quase toda a inteligência está nestas funções.
"""
import sys

sys.path.insert(0, "scripts")

from sniff_replay import (candidatos_da_pagina, chave_do_link,  # noqa: E402
                          esqueleto, palpites_conhecidos, parece_mao)

# esqueleto real de uma mão de PPPoker (o formato que já sabemos ler)
MAO = {"info": {"room": {"small_blind": 1, "ante": 0, "dealer_seatid": 3},
                "players": [{"user_name": "Leo", "seatid": 1,
                             "hand_chips": 100, "isSelf": True}],
                "cards": [1042, 1550]},
       "flow": {"pre_flop": {"actions": [{"seatid": 1, "chips": 3, "type": 4}]},
                "flop": {"cards": [524, 1039, 782], "actions": []},
                "winning_info": [{"seatid": 1, "chips": 12}]}}

CONFIG_UI = {"version": "3.2.1", "assets": {"lang": "pt", "theme": "dark"},
             "urls": {"help": "https://x/y"}, "id": 77}


def test_reconhece_mao_e_recusa_config():
    assert parece_mao(MAO) >= 8
    assert parece_mao(CONFIG_UI) < 5
    assert parece_mao(MAO) > parece_mao(CONFIG_UI)


def test_pontua_por_soma_e_nao_por_chave_obrigatoria():
    """Cada clube nomeia do seu jeito — exigir 'players' perderia um JSON
    que chama de 'users'."""
    outro_clube = {"seats": [{"stack": 50}], "board": ["Ah"],
                   "pot": 30, "smallBlind": 1, "showdown": True}
    assert parece_mao(outro_clube) >= 8


def test_chave_do_link_em_varios_formatos():
    uuid = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
    assert chave_do_link(f"https://x.net/#/?shareKey={uuid}") == uuid
    assert chave_do_link("https://x.net/r?handId=ABC123456789") == "ABC123456789"
    assert chave_do_link("https://x.net/review/ZZZ1234567890123") == \
        "ZZZ1234567890123"
    assert chave_do_link("https://x.net/") is None


# link REAL da Suprema, mandado pelo admin — é o gabarito deste arquivo
SUPREMA = "https://r.supremapoker.net/?t=0s2kipvi002pt&er=5"


def test_link_real_da_suprema():
    """Enumerar nomes de parâmetro não funciona: a Suprema chama de `t`.
    Com a lista de nomes, um link BOM devolvia None e o farejador rodaria
    sem gerar um palpite sequer."""
    assert chave_do_link(SUPREMA) == "0s2kipvi002pt"


def test_contador_e_timestamp_nao_viram_chave():
    """`er=5` está no mesmo link e não pode ser confundido com a mão."""
    assert chave_do_link("https://x.net/?er=5") is None
    assert chave_do_link("https://x.net/?ts=1690000000") is None   # timestamp
    assert chave_do_link("https://x.net/?v=2&debug=true") is None


def test_palpites_da_suprema_saem_do_subdominio_e_levam_os_parametros():
    from urllib.parse import urlparse

    p = urlparse(SUPREMA)
    ps = palpites_conhecidos(chave_do_link(SUPREMA), p.netloc, p.query)
    assert ps, "link com chave tem que gerar palpite"
    # a API raramente fica no subdomínio que serve a página do replay
    assert any("//supremapoker.net/" in u for u in ps)
    # e quando o replay usa 2 parâmetros, a API costuma querer os dois
    assert any(u.endswith("?t=0s2kipvi002pt&er=5") for u in ps)


def test_sem_chave_nao_inventa_palpite():
    assert palpites_conhecidos("", "r.supremapoker.net", "er=5") == []


def test_candidatos_ignoram_imagem_e_priorizam_replay():
    html = """
      <script src="/static/app.js"></script>
      <img src="https://cdn.x.net/api/logo.png">
      <script>var A="/api/config.json";var B="https://cdn.x.net/review_hand/K.json";</script>
    """
    urls = candidatos_da_pagina(html, "https://x.net/replay?k=1")
    assert not any(u.endswith(".png") for u in urls)
    # o que tem 'review_hand' vem antes do config.json genérico
    assert urls[0].endswith("review_hand/K.json")
    assert any(u.endswith("/api/config.json") for u in urls)


def test_esqueleto_mostra_forma_sem_despejar_valores():
    e = esqueleto(MAO)
    assert e["info"]["room"]["small_blind"] == "int"
    assert isinstance(e["info"]["players"], list)
    # string longa vira tamanho, não conteúdo
    assert esqueleto({"t": "x" * 50})["t"] == "str(50)"
    assert esqueleto({"t": "curta"})["t"] == "'curta'"


def test_link_que_ja_e_o_json_da_mao_conta_como_achado():
    """Defeito pego no teste de fumaça: quando a própria URL devolvia JSON,
    o farejador descartava a resposta e dizia 'não achei nada' com a mão
    na mão."""
    import sniff_replay as s

    def _falso_get(url, limite_bytes=0):
        import json as _j
        return 200, _j.dumps(MAO).encode(), "application/json"

    original = s._get
    s._get = _falso_get
    try:
        r = s.farejar("https://clube.x/replay/abcdef1234567890.json")
    finally:
        s._get = original
    assert r["achados"], "o JSON da própria URL tem que virar candidato"
    assert r["achados"][0]["url"].endswith(".json")
    assert r["achados"][0]["pontos"] >= 8


def test_bundle_de_nome_generico_e_varrido():
    """A falha que o VPS expôs: 55 endpoints tentados = só os meus palpites.
    O filtro por palavra-chave descartava `/assets/index-4f3a.js`, que é
    onde o endpoint mora — o farejador dizia 'não achei' sem ter olhado."""
    from sniff_replay import scripts_da_pagina

    html = ('<script src="/assets/index-4f3a.js"></script>'
            '<script src="https://cdn.x.net/vendor.abc.js"></script>'
            '<script>var a=1</script>')
    s = scripts_da_pagina(html, "https://r.x.net/?t=k")
    assert s == ["https://r.x.net/assets/index-4f3a.js",
                 "https://cdn.x.net/vendor.abc.js"]
    # e o filtro antigo realmente os perderia
    assert not any("index-4f3a" in u
                   for u in candidatos_da_pagina(html, "https://r.x.net/"))


def test_mao_embutida_no_html_e_encontrada():
    """Página de 4 KB pode já trazer a mão dentro de um <script>."""
    import json

    from sniff_replay import _blobs_json

    html = ("<html><script>window.__D__ = "
            + json.dumps(MAO) + ";</script></html>")
    blobs = _blobs_json(html)
    assert any(parece_mao(b) >= 8 for b in blobs)


def test_caminho_completo_pagina_bundle_endpoint():
    """A LIGAÇÃO, não as peças: página → bundle de nome genérico → endpoint
    → mão. É este percurso inteiro que falhava em silêncio no VPS."""
    import json as _j

    import sniff_replay as s

    html = b'<html><script src="/assets/index-9f2.js"></script></html>'
    bundle = b'var API="https://api.clube.net/v2/hand/detail.json";'

    def _falso_get(url, limite_bytes=0):
        if url.endswith("index-9f2.js"):
            return 200, bundle, "application/javascript"
        if "hand/detail.json" in url:
            return 200, _j.dumps(MAO).encode(), "application/json"
        if url.startswith("https://r.clube.net/?t="):
            return 200, html, "text/html"
        return 404, b"", ""

    original, original_bater = s._get, s._bater
    s._get = _falso_get
    # a matriz de POST também precisa de rédea: sem isto o teste saía
    # batendo em domínio inexistente de verdade e levava 12 segundos
    s._bater = lambda url, metodo, dados, referer: (0, b"")
    try:
        r = s.farejar("https://r.clube.net/?t=abc123def456")
    finally:
        s._get, s._bater = original, original_bater

    assert r["chave"] == "abc123def456"
    assert r["achados"], "o endpoint estava escrito no bundle e tem que sair"
    assert r["achados"][0]["url"].endswith("hand/detail.json")
    assert r["achados"][0]["pontos"] >= 8


def test_teste_nao_pode_escrever_no_disco_da_maquina():
    """Aconteceu de verdade: com o caminho de despejo fixo no módulo, este
    teste gravou seus fixtures em /tmp do VPS durante o portão do deploy. O
    admin abriu a pasta esperando a página da Suprema e encontrou 57 bytes
    de mentira minha. Efeito colateral só sai de main()."""
    import os

    import sniff_replay as s

    antes = set(os.listdir(s._DESPEJO)) if os.path.isdir(s._DESPEJO) else set()

    def _falso_get(url, limite_bytes=0):
        return 200, b'<html><script src="/a.js"></script></html>', "text/html"

    original, original_bater = s._get, s._bater
    s._get = _falso_get
    s._bater = lambda url, metodo, dados, referer: (0, b"")
    try:
        s.farejar("https://r.clube.net/?t=abc123def456")   # sem despejo
    finally:
        s._get, s._bater = original, original_bater

    depois = set(os.listdir(s._DESPEJO)) if os.path.isdir(s._DESPEJO) else set()
    assert depois == antes, f"o teste sujou o disco: {depois - antes}"


def test_urls_cruas_mostram_o_que_o_filtro_esconde():
    """"3 candidatos" num app inteiro é pouco demais para ser verdade. O
    filtro escolhe o que TENTAR; isto mostra o que EXISTE, para o olho
    humano ver o host de API que não tem 'api' no nome."""
    from sniff_replay import urls_cruas

    bundle = ('var B="https://gw.supremapoker.net/v2";'
              'var L="https://img.cdn.net/x/logo.png";'
              'var W="http://www.w3.org/2000/svg";'
              'fetch(B+"/hand/"+id)')
    u = urls_cruas(bundle)
    assert "https://gw.supremapoker.net/v2" in u   # o host que interessa
    assert not any("logo.png" in x for x in u)     # imagem sai
    assert not any("w3.org" in x for x in u)       # ruído de biblioteca sai
    # e o filtro de candidatos NÃO acharia esse host (não tem palavra-chave)
    assert not any("gw.supremapoker.net" in x
                   for x in candidatos_da_pagina(bundle, "https://r.x/"))


def test_php_conta_como_endpoint_e_asset_nao():
    """A Suprema serve a mão em replayInfo.php. Uma API PHP quase sempre
    quer POST — bater só com GET devolve erro e parece 'não é aqui'."""
    from sniff_replay import parece_endpoint

    assert parece_endpoint(
        "https://ra.supremapoker.net/supremaAPI/replayInfo.php")
    assert parece_endpoint("https://x.net/api/v2/hand")
    assert not parece_endpoint("https://x.net/main.45fc5.js")
    assert not parece_endpoint("https://x.net/cards/poker.png")


def test_combinacoes_comecam_pela_querystring_original():
    from sniff_replay import combinacoes_de_parametros

    c = combinacoes_de_parametros("0s2kipvi002pt", "t=0s2kipvi002pt&er=5")
    # o que a página usa de fato é o palpite com mais chance
    assert c[0] == {"t": "0s2kipvi002pt", "er": "5"}
    # e os apelidos carregam o `er` junto, porque a API pode exigir os dois
    assert {"id": "0s2kipvi002pt", "er": "5"} in c


def test_probe_acha_a_mao_via_post_e_manda_referer():
    """O Referer vai junto de propósito: API de clube recusa quem não veio
    da página do replay, e o 403 pareceria 'endpoint errado'."""
    import sniff_replay as s

    vistos = []

    def _falso_bater(url, metodo, dados, referer):
        import json as _j
        vistos.append((metodo, dict(dados), referer))
        if metodo == "POST-form" and dados.get("t") == "K1":
            return 200, _j.dumps(MAO).encode()
        return 403, b""

    original = s._bater
    s._bater = _falso_bater
    try:
        r = s.probar_endpoint("https://ra.x.net/replayInfo.php",
                              [{"t": "K1", "er": "5"}],
                              "https://r.x.net/?t=K1&er=5")
    finally:
        s._bater = original

    assert r and r[0]["pontos"] >= 8
    assert "POST-form" in r[0]["url"]
    assert all(v[2].startswith("https://r.x.net/") for v in vistos)


CLOUDFRONT_403 = (
    b"<HTML><H1>403 ERROR</H1>This distribution is not configured to allow "
    b"the HTTP request method that was used for this request. The "
    b"distribution supports only cachable requests.</HTML>")


def test_403_do_cloudfront_e_confirmacao_nao_recusa():
    """Aconteceu com a Suprema: o POST levou 403, e o corpo dizia que só
    entra requisição cacheável — ou seja, a URL está CERTA e o método é que
    estava errado. Descartar isso como 'falhou' quase matou o endpoint."""
    from sniff_replay import pista_do_erro

    pista = pista_do_erro(CLOUDFRONT_403)
    assert pista and "EXISTE" in pista
    assert pista_do_erro(b"<html>404 not found</html>") is None


def test_corpo_que_e_so_um_numero_e_erro_da_aplicacao():
    """A Suprema devolveu literalmente `-1` com HTTP 200 quando o método já
    estava certo. Isso não é 'vazio': é o endpoint respondendo que o
    PARÂMETRO está errado."""
    from sniff_replay import pista_do_erro

    p = pista_do_erro(b"-1")
    assert p and "RESPONDE" in p and "parâmetro" in p
    assert pista_do_erro(b"0")
    # JSON de verdade não pode ser confundido com código de erro
    assert pista_do_erro(b'{"pot": 30}') is None


def test_get_vem_antes_do_post():
    """API de clube fica atrás de CDN, e CDN só deixa passar cacheável."""
    import sniff_replay as s

    ordem = []
    original = s._bater
    s._bater = lambda u, m, d, r: (ordem.append(m), (403, CLOUDFRONT_403))[1]
    try:
        s.probar_endpoint("https://ra.x.net/replayInfo.php", [{"t": "K"}],
                          "https://r.x.net/", relatar=lambda _t: None)
    finally:
        s._bater = original
    assert ordem[0] == "GET"


def test_pista_do_erro_e_relatada_uma_vez_so():
    import sniff_replay as s

    ditas = []
    original = s._bater
    s._bater = lambda u, m, d, r: (403, CLOUDFRONT_403)
    try:
        s.probar_endpoint("https://ra.x.net/r.php",
                          [{"t": "K"}, {"id": "K"}, {"key": "K"}],
                          "https://r.x.net/", relatar=ditas.append)
    finally:
        s._bater = original
    # 3 métodos × 3 combos = 9 respostas iguais, mas o humano lê UMA linha
    assert len(ditas) == 1 and "EXISTE" in ditas[0]


def test_encurtador_e_resolvido_antes_de_tudo():
    """`gg.gl/fovbb` não tem chave nenhuma: derivar dele é trabalhar no
    endereço errado. Cobre redirecionamento HTTP e meta-refresh/JS."""
    import sniff_replay as s

    class _R:
        def __init__(self, url, corpo=b""):
            self._u, self._c = url, corpo

        def geturl(self):
            return self._u

        def read(self, _n=0):
            return self._c

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    alvo = "https://replay.ggpoker.com/hand?id=ABC123XYZ"
    original = s.urllib.request.urlopen

    s.urllib.request.urlopen = lambda *a, **k: _R(alvo)
    try:
        assert s.resolver_encurtador("https://gg.gl/fovbb") == alvo
    finally:
        s.urllib.request.urlopen = original

    # redirecionamento por meta-refresh (o urlopen não segue)
    html = (b'<meta http-equiv="refresh" content="0; url='
            + alvo.encode() + b'">')
    s.urllib.request.urlopen = lambda *a, **k: _R("https://gg.gl/fovbb", html)
    try:
        assert s.resolver_encurtador("https://gg.gl/fovbb") == alvo
    finally:
        s.urllib.request.urlopen = original


def test_blobs_ignoram_objeto_pequeno_de_config():
    from sniff_replay import _blobs_json

    assert _blobs_json('<script>var c={"a":1};</script>') == []


def test_esqueleto_nao_entra_em_recursao_infinita():
    fundo = {}
    no = fundo
    for _ in range(30):
        no["n"] = {}
        no = no["n"]
    assert esqueleto(fundo)          # não estoura
    assert parece_mao(fundo) == 0
