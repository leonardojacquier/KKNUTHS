"""Os guardas rodam DE VERDADE no caminho que fala com o aluno.

Meia dúzia de testes espalhados pela suíte diziam isto assim:

    assert "conferir_dominancia" in inspect.getsource(_process_upload_inner)

Isso confere que o NOME aparece no arquivo. Não confere que a função é
chamada, que o retorno dela é usado, nem que o texto entregue mudou. Em
09/08 esse padrão deixou passar a inversão de um portão — os 971 testes
passaram com a condição ao contrário, porque a substring continuava lá.

Aqui o pipeline roda de ponta a ponta com LLM e banco falsos, e as
asserções são sobre as duas únicas coisas que importam: o TEXTO que volta
para o aluno e os EVENTOS gravados.

O `coach` falso devolve de propósito o texto do incidente real (07/08): uma
análise que cita `77` como a mão do vilão quando o board já tem dois setes
— logo `77` é impossível — e que afirma dominância falsa.
"""
from __future__ import annotations

import pytest

from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  PlayerSeat, Stakes, Street, StreetName)

# O board tem 7c e 7h. O herói tem 7s. Sobra UM sete no baralho, então `77`
# é combinação impossível — e o vilão mostrou 2d7d, que é 72s.
TEXTO_ERRADO = ("Seu full de 7 com A só perdia pra 77 ou AA — o vilão "
                "apareceu com 77 exatos. Foi um cooler clássico.")

_TELEGRAM_ID = 990001


def _mao_do_full() -> CanonicalHand:
    """A mão do incidente, como CanonicalHand de verdade.

    A suíte tinha esses dados só como `SimpleNamespace` (duck typing), o que
    serve para testar os guardas isolados e NÃO serve para rodar o pipeline.
    """
    return CanonicalHand(
        hand_id="e2e-full", site="PPPoker", hero="KKNUThS",
        hero_cards=["As", "7s"], source_format="txt", confidence=1.0,
        stakes=Stakes(small_blind=100000, big_blind=200000),
        players=[
            PlayerSeat(seat=1, name="KKNUThS", stack=15000000, is_hero=True,
                       position="BB"),
            PlayerSeat(seat=2, name="arisn", stack=15000000, position="BTN")],
        streets=[
            Street(name=StreetName.PREFLOP, actions=[
                Action(actor="arisn", type=ActionType.RAISE, amount=15000000,
                       to_amount=15000000, all_in=True),
                Action(actor="KKNUThS", type=ActionType.CALL,
                       amount=15000000, all_in=True)]),
            Street(name=StreetName.FLOP, board=["2c", "7c", "7h"]),
            Street(name=StreetName.TURN, board=["2c", "7c", "7h", "Ac"]),
            Street(name=StreetName.RIVER,
                   board=["2c", "7c", "7h", "Ac", "Th"])],
        final_board=["2c", "7c", "7h", "Ac", "Th"],
        shown_cards={"arisn": ["2d", "7d"]},
        collected={"KKNUThS": 32132600})


def _mao_de_torneio() -> CanonicalHand:
    """Mesma estrutura, marcada como TORNEIO — é o que acorda o ramo de ICM.

    Stacks rasos e desiguais de propósito: é a situação em que ignorar ICM
    muda a decisão, não só o número.
    """
    from app.models.canonical import HandFormat

    return CanonicalHand(
        hand_id="e2e-mtt", site="PokerStars", hero="KKNUThS",
        hero_cards=["Ad", "4h"], source_format="txt", confidence=1.0,
        format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=500, big_blind=1000, ante=125),
        players=[
            PlayerSeat(seat=1, name="KKNUThS", stack=3600, is_hero=True,
                       position="SB"),
            PlayerSeat(seat=2, name="vilao", stack=42000, position="BB")],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="KKNUThS", type=ActionType.RAISE, amount=3600,
                   to_amount=3600, all_in=True),
            Action(actor="vilao", type=ActionType.CALL, amount=3600)])])


def test_a_mao_impossivel_nao_chega_ao_aluno(rodar_pipeline):
    """`77` com dois setes no board e um na mão do herói: sobra um sete no
    baralho. O vilão mostrou 2d7d, que é 72s.

    Esta é a asserção que nenhuma substring conseguia fazer: o texto que sai
    tem a mão CERTA.
    """
    saida, repo, _ = rodar_pipeline(TEXTO_ERRADO, _mao_do_full())

    assert "apareceu com 72s" in saida, (
        f"o showdown não foi corrigido no texto entregue: {saida[:300]}")
    assert "com 77 exatos" not in saida, "a mão impossível sobreviveu"

    evento = repo.evento("showdown_errado")
    assert evento, "corrigiu o texto e não registrou o evento"
    assert evento["citado"] == "77"
    assert evento["corrigido_para"] == "72s"


def test_a_dominancia_falsa_e_corrigida_no_texto_entregue(rodar_pipeline):
    """`77` não vira favorito contra o full do herói — e a frase que diz
    isso é reescrita, não só contada."""
    saida, repo, _ = rodar_pipeline(TEXTO_ERRADO, _mao_do_full())

    assert "só perdia pra AA" in saida, (
        f"a lista de mãos não foi corrigida: {saida[:300]}")
    evento = repo.evento("fato_corrigido")
    assert evento and evento["maos"] == ["77"]
    assert evento["heroi"] == ["As", "7s"]


def test_texto_correto_atravessa_intacto(rodar_pipeline):
    """O outro lado do portão, e o que mais dói quando falha: guarda que
    estraga texto certo é pior que guarda ausente, porque o aluno perde
    confiança no que está certo."""
    bom = ("Seu full de 7 com A só perdia pra AA aqui. O vilão apareceu com "
           "72s e você levou o pote.")
    saida, repo, _ = rodar_pipeline(bom, _mao_do_full())

    assert "só perdia pra AA aqui" in saida
    assert "72s" in saida
    assert repo.evento("fato_corrigido") is None, "reescreveu texto correto"
    assert repo.evento("showdown_errado") is None


def test_o_evento_de_upload_registra_a_procedencia(rodar_pipeline):
    """Sem isto não dá para separar depois 'analisou errado' de 'leu de uma
    fonte que não sustentava a análise'."""
    _s, repo, _ = rodar_pipeline(TEXTO_ERRADO, _mao_do_full())

    upload = repo.evento("upload")
    assert upload, "o upload não foi registrado"
    assert upload["format"] == "txt" and upload["confidence"] == 1.0
    assert upload["hands"] == 1


def test_a_conta_anunciada_sem_conta_e_ao_menos_registrada(rodar_pipeline):
    """CONTRATO HONESTO, e é menos do que a documentação promete.

    `conta_sem_numero` DETECTA e registra; ela não corrige. O texto sai com
    a promessa vazia mesmo. Este teste fixa o que o sistema realmente faz —
    se um dia ele passar a corrigir, o assert de baixo quebra e a mudança é
    deliberada, não acidental.
    """
    texto = ("A conta: você paga sempre nesse spot, sem pensar duas vezes. "
             "Seu full de 7 com A só perdia pra AA.")
    saida, repo, _ = rodar_pipeline(texto, _mao_do_full())

    assert repo.evento("conta_sem_numero") is not None, (
        "a conta sem número passou sem nem ser registrada")
    assert "você paga sempre nesse spot" in saida, (
        "o guarda passou a CORRIGIR — ótimo, mas atualize este teste e o "
        "METODO.md, que hoje descrevem uma conferência que só registra")


@pytest.fixture
def repo_dos_guardas(monkeypatch):
    """O repo que `guarda_voz`/`guarda_termos` enxergam.

    Eles não recebem o repo por parâmetro — pegam de `app.db` na hora, como
    o resto da casa. O repo injetado em `rodar_pipeline` é outro objeto,
    então sem este patch a asserção de evento passaria por não ter nada
    para comparar, que é o pior jeito de um teste passar.
    """
    import app.db
    from tests.conftest import RepoDePipeline

    r = RepoDePipeline()
    monkeypatch.setattr(app.db, "get_repository", lambda: r)
    return r


def test_o_termo_traduzido_nao_chega_ao_aluno(rodar_pipeline,
                                              repo_dos_guardas):
    """Caso real (16/08): "e foi o rio que virou tudo" e "a fatia de ar do
    range dele" saíram numa análise entregue. O dono: "se é termo do poker
    não tem que traduzir" — e já tinha reclamado antes.

    A asserção é a única que importa: o texto que VOLTA para o aluno. Um
    `assert "guarda_termos" in inspect.getsource(...)` passaria com o
    guarda desligado — foi esse padrão que deixou um portão invertido
    passar em 09/08.
    """
    texto = ("Seu full de 7 com A só perdia pra AA. Você estava na frente a "
             "mão inteira e foi o rio que virou tudo — apostar de novo bate "
             "contra a fatia de ar do range dele.")
    saida, _repo, _ = rodar_pipeline(texto, _mao_do_full())

    assert "foi o river que virou tudo" in saida, (
        f"'rio' chegou ao aluno de novo: {saida[:400]}")
    assert "a fatia de air do range dele" in saida, (
        f"'ar' chegou ao aluno de novo: {saida[:400]}")
    evento = repo_dos_guardas.evento("termo_corrigido")
    assert evento, "corrigiu o texto e não deixou medir"
    assert evento["onde"] == "analise"


def test_o_portugues_com_ar_atravessa_o_pipeline_intacto(rodar_pipeline,
                                                         repo_dos_guardas):
    """O outro lado do portão, e a parte difícil desta tarefa: "ar" é
    palavra comum do português. "é um spot de moeda ao ar" saiu numa
    análise real (31/07) e está CERTO — guarda que estraga texto bom custa
    mais confiança do que o calque custa."""
    texto = ("Seu full de 7 com A só perdia pra AA. Largar vale 0 e é um "
             "spot de moeda ao ar; ele deixou no ar se pagava.")
    saida, _repo, _ = rodar_pipeline(texto, _mao_do_full())

    assert "moeda ao ar" in saida and "deixou no ar" in saida, (
        f"o guarda dos termos estragou português normal: {saida[:400]}")
    assert repo_dos_guardas.evento("termo_corrigido") is None
    assert repo_dos_guardas.evento("termo_ambiguo") is None, (
        "português assentado virou evento — a medição de 'ar' fica com mais "
        "português do que poker dentro e não decide nada")
