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

    original = s._get
    s._get = _falso_get
    try:
        r = s.farejar("https://r.clube.net/?t=abc123def456")
    finally:
        s._get = original

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

    original = s._get
    s._get = _falso_get
    try:
        s.farejar("https://r.clube.net/?t=abc123def456")   # sem despejo
    finally:
        s._get = original

    depois = set(os.listdir(s._DESPEJO)) if os.path.isdir(s._DESPEJO) else set()
    assert depois == antes, f"o teste sujou o disco: {depois - antes}"


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
