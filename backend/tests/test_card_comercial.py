"""O card comercial — a peça que o dono manda no WhatsApp/Telegram.

Não confundir com `site_card.png`, que é um DESAFIO de quiz (um spot para o
parceiro responder). Este vende a ferramenta, e por isso as amarras aqui são
comerciais: a tese, a prova, a credencial e o link têm que estar na imagem.

O formato é 1080x1350 porque é o que WhatsApp e Telegram exibem inteiro; um
card que o app corta perde justamente a chamada, que fica embaixo.
"""
from __future__ import annotations

from app.api.card_comercial import ALTURA, LARGURA, build_card_html


def test_o_formato_e_o_que_o_app_nao_corta():
    assert (LARGURA, ALTURA) == (1080, 1350)


def test_a_tese_e_a_chamada_estao_no_card():
    html = build_card_html()
    assert "A IA n" in html and "conta" in html      # a tese
    assert "t.me/KKNUts_BOT" in html                  # o link, sem ele o card é enfeite
    assert "Manda a primeira m" in html               # a chamada


def test_o_card_mostra_o_produto_e_nao_so_promete():
    """A prova é o placar street a street — o formato de saída real."""
    html = build_card_html()
    for rua in ("Pr&eacute;", "Flop", "Turn", "River"):
        assert rua in html, f"o placar do card perdeu a {rua}"
    assert "+1.49bb" in html, "o card ficou sem número calculado"


def test_as_credenciais_de_nobel_estao_no_card():
    html = build_card_html()
    assert html.count("NOBEL") >= 2
    assert "Kahneman" in html and "Nash" in html


def test_a_logo_vai_embutida():
    """Card é imagem: asset externo não existe no destino."""
    assert "data:image/png;base64," in build_card_html()


def test_nao_depende_de_fonte_da_rede():
    html = build_card_html()
    assert "fonts.googleapis" not in html and "@import" not in html
