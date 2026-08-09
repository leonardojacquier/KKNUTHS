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

from app.bot import processing as proc
from app.ingestion.pipeline import IngestResult
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


class _RepoFalso:
    """`enabled=True` de propósito: os guardas só gravam evento com o repo
    ligado, e um repo desligado faria o teste passar sem medir nada.

    Qualquer método não previsto vira um registro `__chamou__:<nome>` em vez
    de AttributeError — assim o teste mostra o que o pipeline tocou em vez
    de morrer na primeira surpresa.
    """

    enabled = True

    def __init__(self):
        self.events: list[tuple] = []

    def log_event(self, telegram_id, username, event, detail=None):
        self.events.append((event, detail))

    def __getattr__(self, nome):
        def _qualquer(*a, **k):
            self.events.append((f"__chamou__:{nome}", None))
            return None
        return _qualquer

    def evento(self, nome):
        for ev, detalhe in self.events:
            if ev == nome:
                return detalhe or {}
        return None


@pytest.fixture
def rodar(monkeypatch):
    """Roda o pipeline com o texto de coach que o teste escolher."""
    def _rodar(texto_do_coach: str, hand: CanonicalHand | None = None):
        mao = hand or _mao_do_full()
        monkeypatch.setattr(proc, "coach", lambda *a, **k: texto_do_coach)
        monkeypatch.setattr(proc, "ingest", lambda *a, **k: IngestResult(
            [mao], "PPPoker", "txt", confidence=1.0, needs_review=False))
        repo = _RepoFalso()
        saida = proc._process_upload_inner(
            b"bruto", "txt", _TELEGRAM_ID, "tester", "pt", repo, None)
        return saida, repo

    yield _rodar
    # estado global por telegram_id não pode vazar para o próximo teste
    for mapa in (proc.RECENT_HANDS, proc.LAST_ANALYSIS, proc.LAST_UPLOAD_KIND,
                 proc.LAST_HAND_META):
        mapa.pop(_TELEGRAM_ID, None)


def test_a_mao_impossivel_nao_chega_ao_aluno(rodar):
    """`77` com dois setes no board e um na mão do herói: sobra um sete no
    baralho. O vilão mostrou 2d7d, que é 72s.

    Esta é a asserção que nenhuma substring conseguia fazer: o texto que sai
    tem a mão CERTA.
    """
    saida, repo = rodar(TEXTO_ERRADO)

    assert "apareceu com 72s" in saida, (
        f"o showdown não foi corrigido no texto entregue: {saida[:300]}")
    assert "com 77 exatos" not in saida, "a mão impossível sobreviveu"

    evento = repo.evento("showdown_errado")
    assert evento, "corrigiu o texto e não registrou o evento"
    assert evento["citado"] == "77"
    assert evento["corrigido_para"] == "72s"


def test_a_dominancia_falsa_e_corrigida_no_texto_entregue(rodar):
    """`77` não vira favorito contra o full do herói — e a frase que diz
    isso é reescrita, não só contada."""
    saida, repo = rodar(TEXTO_ERRADO)

    assert "só perdia pra AA" in saida, (
        f"a lista de mãos não foi corrigida: {saida[:300]}")
    evento = repo.evento("fato_corrigido")
    assert evento and evento["maos"] == ["77"]
    assert evento["heroi"] == ["As", "7s"]


def test_texto_correto_atravessa_intacto(rodar):
    """O outro lado do portão, e o que mais dói quando falha: guarda que
    estraga texto certo é pior que guarda ausente, porque o aluno perde
    confiança no que está certo."""
    bom = ("Seu full de 7 com A só perdia pra AA aqui. O vilão apareceu com "
           "72s e você levou o pote.")
    saida, repo = rodar(bom)

    assert "só perdia pra AA aqui" in saida
    assert "72s" in saida
    assert repo.evento("fato_corrigido") is None, "reescreveu texto correto"
    assert repo.evento("showdown_errado") is None


def test_o_evento_de_upload_registra_a_procedencia(rodar):
    """Sem isto não dá para separar depois 'analisou errado' de 'leu de uma
    fonte que não sustentava a análise'."""
    _, repo = rodar(TEXTO_ERRADO)

    upload = repo.evento("upload")
    assert upload, "o upload não foi registrado"
    assert upload["format"] == "txt" and upload["confidence"] == 1.0
    assert upload["hands"] == 1


def test_a_conta_anunciada_sem_conta_e_ao_menos_registrada(rodar):
    """CONTRATO HONESTO, e é menos do que a documentação promete.

    `conta_sem_numero` DETECTA e registra; ela não corrige. O texto sai com
    a promessa vazia mesmo. Este teste fixa o que o sistema realmente faz —
    se um dia ele passar a corrigir, o assert de baixo quebra e a mudança é
    deliberada, não acidental.
    """
    texto = ("A conta: você paga sempre nesse spot, sem pensar duas vezes. "
             "Seu full de 7 com A só perdia pra AA.")
    saida, repo = rodar(texto)

    assert repo.evento("conta_sem_numero") is not None, (
        "a conta sem número passou sem nem ser registrada")
    assert "você paga sempre nesse spot" in saida, (
        "o guarda passou a CORRIGIR — ótimo, mas atualize este teste e o "
        "METODO.md, que hoje descrevem uma conferência que só registra")
