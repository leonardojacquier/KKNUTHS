"""O folder tem três restrições que não se veem olhando o HTML.

Elas estão no docstring de folder_page.py e já custaram retrabalho:

1. DUAS PÁGINAS A4 EXATAS — o arquivo vira PDF. Conteúdo a mais não rola:
   some no overflow:hidden, e ninguém percebe até o folder já estar impresso.
2. SEM LINK DO BOT — decisão de produto do piloto (acesso a dedo). Folder
   com link circulando vira cadastro aleatório e o piloto perde a amostra.
3. FONTES DO SISTEMA — o gerador de PDF roda sem rede; @import de Google
   Fonts cai em silêncio e o layout medido em mm quebra.
"""
from __future__ import annotations

from app.api.folder_page import build_folder_html


def test_sao_exatamente_duas_paginas_a4():
    html = build_folder_html()
    assert html.count('class="page"') == 2
    assert "size:A4" in html.replace(" ", "")
    assert "296mm" in html, "altura de página perdida — o PDF vai cortar"


def test_o_folder_leva_o_link_do_bot():
    """22/08 o dono ABRIU o acesso: o folder passa a levar o link.

    O teste inverteu junto com o docstring — antes ele proibia o link. Se um
    dia fechar de novo, os três mudam juntos (folder, docstring, teste),
    senão o material e o teste contam versões diferentes da decisão.
    """
    html = build_folder_html()
    assert "t.me/" in html, "o folder ficou sem link depois da abertura"
    assert html.count("t.me/") >= 2, "o link tem que estar nas duas páginas"
    assert "https://t.me/" in html, "o botão precisa de href absoluto"


def test_a_restricao_de_imagem_com_link_saiu_com_o_piloto_fechado():
    """Enquanto o piloto era fechado, imagem com link/QR era proibida.

    O link podia estar DENTRO do png e o teste de texto passava verde —
    site_card.png entrou assim. Com o acesso aberto (22/08) a proibição
    perdeu o motivo, e este teste guarda a REMOÇÃO dela: se alguém
    reintroduzir a lista sem reabrir a discussão, aqui acusa.
    """
    import inspect

    from app.api import folder_page

    fonte = inspect.getsource(folder_page)
    corpo = fonte.split("def build_folder_html")[1]
    assert not hasattr(folder_page, "_COM_LINK_DO_BOT"), (
        "a lista de assets proibidos só fazia sentido no piloto fechado; "
        "com o acesso aberto ela saiu junto com a restrição")


def test_nao_depende_de_fonte_da_rede():
    html = build_folder_html()
    assert "fonts.googleapis" not in html
    assert "@import" not in html


def test_a_ciencia_e_a_logo_continuam_no_folder():
    """Conteúdo comercial que já custou caro para existir."""
    html = build_folder_html()
    assert "NOBEL" in html
    assert "Kahneman" in html and "Nash" in html
    assert html.count("data:image/png;base64") >= 2, "logo/prints sumiram"


def test_a_tese_e_o_placar_de_exemplo_estao_na_primeira_pagina():
    html = build_folder_html()
    pagina1 = html.split('class="page"')[1]
    assert "não faz a" in pagina1, "a tese saiu da capa"
    for rua in ("Pré", "Flop", "Turn", "River"):
        assert rua in pagina1, f"o placar de exemplo perdeu a {rua}"


def test_todo_bloco_colorido_pede_cor_no_pdf():
    """Sem print-color-adjust o PDF sai com os blocos brancos."""
    html = build_folder_html()
    assert html.count("print-color-adjust:exact") >= 8
