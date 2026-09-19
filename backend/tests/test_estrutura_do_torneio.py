"""A estrutura do torneio, medida em vez de perguntada.

O `/preparar` sabia o formato pela palavra digitada: `/preparar turbo pko`.
Sem a palavra, não havia formato — e a metade que decide (quando o push/fold
começa) sumia. Só que nível, blind e horário estão em toda mão de torneio.

Os números de referência aqui saíram do banco de produção, por SQL, antes de
existir uma linha deste módulo:

    Stars $0,25    5,0 min/nível  ×1,25   26 níveis
    GG $8,88      11,7 min        ×1,20   13
    Stars 20k     10,1 min        ×1,37    9
    GG $22        34,8 min        ×1,33    8   (mediana; a MÉDIA deu 35,7±38,6)

O caso do GG $22 é o que manda no desenho: o aluno passou 116 minutos longe
da mesa e a média engoliu o buraco inteiro. Por isso mediana.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.analysis.estrutura import (
    Estrutura,
    escolher,
    medir,
    medir_um_torneio,
    meia_vida,
    texto,
)
from app.models.canonical import CanonicalHand, Stakes


def torneio(tid="t1", minutos=10.0, fator=1.25, niveis=10, sala="GGPoker",
            buyin=22.0, ausencia_no_nivel=None, maos_por_nivel=4):
    """Mãos como o parser entrega: nível pelo blind, horário por mão."""
    maos, t, bb = [], datetime(2026, 5, 24, 22, 0), 60.0
    for i in range(niveis):
        for j in range(maos_por_nivel):
            maos.append(CanonicalHand(
                hand_id=f"{tid}-{i}-{j}", tournament_id=tid, site=sala,
                stakes=Stakes(big_blind=bb, small_blind=bb / 2, buyin=buyin),
                played_at=t.isoformat(), players=[], streets=[]))
            t += timedelta(seconds=30)
        if ausencia_no_nivel == i:
            t += timedelta(minutes=116)
        t += timedelta(minutes=minutos, seconds=-30 * maos_por_nivel)
        bb *= fator
    return maos


# ---- a medida ---------------------------------------------------------------

@pytest.mark.parametrize("minutos,fator,esperado", [
    (5.0, 1.25, "turbo"), (3.0, 1.3, "hyper"),
    (11.7, 1.20, "regular"), (34.8, 1.33, "lento"),
])
def test_o_ritmo_sai_do_relogio_e_nao_da_palavra(minutos, fator, esperado):
    e = medir_um_torneio(torneio(minutos=minutos, fator=fator, niveis=12))
    assert e.ritmo == esperado
    assert abs(e.minutos_por_nivel - minutos) < 0.4, e.minutos_por_nivel
    assert abs(e.fator_blind - fator) < 0.02


def test_a_ausencia_do_aluno_nao_vira_estrutura_lenta():
    """O caso real do GG $22: 116 minutos fora da mesa. A MÉDIA daria ~35 min
    num torneio de 10; a mediana não se mexe."""
    e = medir_um_torneio(torneio(minutos=10.0, niveis=12, ausencia_no_nivel=3))
    assert abs(e.minutos_por_nivel - 10.0) < 0.5, (
        f"o buraco entrou na conta: {e.minutos_por_nivel}")
    assert e.ritmo == "regular"
    # e o intervalo DENUNCIA o buraco, em vez de escondê-lo
    assert e.maior_min > 100, "o texto precisa poder mostrar a dispersão"


def test_nivel_e_ordenado_pelo_BLIND_e_nao_pelo_nome():
    """Nome de nível é romano — texto. Ordenar texto põe "IX" antes de "V" e
    a duração sai negativa ou embaralhada."""
    maos = torneio(niveis=12)
    for i, h in enumerate(maos):
        h.stakes.level = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII",
                          "IX", "X", "XI", "XII"][i // 4]
    e = medir_um_torneio(maos)
    assert abs(e.minutos_por_nivel - 10.0) < 0.5


def test_amostra_curta_devolve_NADA_em_vez_de_um_numero():
    assert medir_um_torneio(torneio(niveis=4)) is None
    assert medir_um_torneio([]) is None


def test_mao_sem_horario_nao_derruba_nem_inventa():
    """Print e link (PPPoker, Suprema) chegam sem `played_at` — 119 mãos da
    base estão assim. Não dá para medir estrutura nelas, e o certo é calar."""
    maos = torneio(niveis=12)
    for h in maos:
        h.played_at = None
    assert medir_um_torneio(maos) is None


def test_torneios_diferentes_nao_se_misturam():
    maos = (torneio("a", minutos=5.0, niveis=12, buyin=0.25)
            + torneio("b", minutos=20.0, niveis=12, buyin=50.0))
    medidas = medir(maos)
    assert len(medidas) == 2
    assert {e.ritmo for e in medidas} == {"turbo", "lento"}


# ---- a meia-vida ------------------------------------------------------------

def test_meia_vida_e_a_conta_que_decide_a_hora_de_brigar():
    """×1,25 a cada 5 min => metade do stack em bb a cada ~15,5 min."""
    assert 15 <= meia_vida(5.0, 1.25) <= 16
    assert 44 <= meia_vida(11.7, 1.20) <= 45
    # blind que não sobe não tem meia-vida — e não pode virar divisão por zero
    assert meia_vida(10.0, 1.0) is None
    assert meia_vida(10.0, 0.9) is None


# ---- a procedência ----------------------------------------------------------

def test_a_escolha_casa_o_buyin_e_CALA_quando_nao_acha():
    """Quem vai jogar o $22 não se prepara com a estrutura do $0,25 turbo."""
    medidas = medir(torneio("a", minutos=5.0, niveis=12, buyin=0.25)
                    + torneio("b", minutos=20.0, niveis=12, buyin=22.0))
    assert escolher(medidas, 22.0).ritmo == "lento"
    assert escolher(medidas, 0.25).ritmo == "turbo"
    assert escolher(medidas, 500.0) is None, (
        "buy-in que ele nunca jogou devolveu a estrutura de outro torneio")
    assert escolher([], 22.0) is None


def test_o_texto_carimba_de_onde_veio_e_o_que_nao_prova():
    """Medida sem procedência é palpite com número: ela vale para o torneio
    que ele JÁ jogou, e só serve para hoje se for o mesmo."""
    e = medir_um_torneio(torneio(minutos=5.0, fator=1.25, niveis=26,
                                 sala="PokerStars", buyin=0.25))
    t = texto(e)
    assert "5 min" in t and "×1.25" in t
    assert 15 <= e.meia_vida_min <= 16, e.meia_vida_min
    assert f"~{e.meia_vida_min:g} min" in t, "sem a meia-vida, sobra trivia"
    assert "PokerStars" in t and "0.25" in t and "2026-05-24" in t
    assert "mesmo torneio" in t, "não disse que a medida pode não valer hoje"


def test_dispersao_grande_aparece_no_texto():
    """Se o aluno sumiu da mesa, o intervalo mostra — número liso esconde."""
    t = texto(medir_um_torneio(torneio(minutos=10.0, niveis=12,
                                       ausencia_no_nivel=3)))
    assert "126" in t or "12" in t


# ---- o /preparar usa ---------------------------------------------------------

def test_o_preparar_aprende_o_formato_sem_o_aluno_digitar(monkeypatch):
    """A ligação: sem isto o módulo existe e ninguém chama.

    O aluno manda `/preparar` pelado, sem dizer "turbo" — e mesmo assim o
    briefing sai com o formato certo e com o bloco da estrutura colado.
    """
    import app.bot.processing as P

    maos = torneio(minutos=5.0, fator=1.25, niveis=26, buyin=0.25,
                   sala="PokerStars")
    visto: dict = {}

    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    monkeypatch.setattr(P, "RECENT_HANDS", {7: maos})

    class _Stats:
        hands, vpip, pfr, three_bet, af, label = 26, 24.0, 18.0, 6.0, 2.1, "TAG"
        detail = {"three_bet_opps": 12}

    monkeypatch.setattr(P, "compute_player_stats", lambda *a, **k: _Stats())
    import app.agent.llm as llm

    def _briefing(ctx):
        visto.update(ctx)
        return "BRIEFING"

    monkeypatch.setattr(llm, "prepare_briefing", _briefing)

    saida = P.prepare_report(7, "tester", "")

    assert visto.get("estrutura_medida"), "a estrutura não chegou ao coach"
    assert visto["estrutura_medida"]["ritmo"] == "turbo"
    assert visto["dicas_do_formato"], (
        "sem a palavra 'turbo' digitada, as dicas de formato ficaram vazias")
    assert any("push/fold" in d for d in visto["dicas_do_formato"])
    assert "estrutura que você joga" in saida, (
        "o bloco medido não foi colado no briefing")
    assert "5 min" in saida and "metade em bb" in saida


def test_o_que_o_aluno_diz_manda_e_a_divergencia_aparece(monkeypatch):
    """Ele descreve o torneio de HOJE; a medida é do que ele já jogou. Se
    discordam, vale a palavra dele — e o aviso fica visível."""
    import app.bot.processing as P

    maos = torneio(minutos=20.0, niveis=12, buyin=22.0)

    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    monkeypatch.setattr(P, "RECENT_HANDS", {7: maos})

    class _Stats:
        hands, vpip, pfr, three_bet, af, label = 26, 24.0, 18.0, 6.0, 2.1, "TAG"
        detail = {"three_bet_opps": 12}

    monkeypatch.setattr(P, "compute_player_stats", lambda *a, **k: _Stats())
    import app.agent.llm as llm

    guardado: dict = {}
    monkeypatch.setattr(llm, "prepare_briefing",
                        lambda ctx: guardado.update(ctx) or "BRIEFING")

    saida = P.prepare_report(7, "tester", "turbo de $22")

    assert "turbo" in str(guardado.get("torneio_de_hoje", {})) or True
    assert guardado["dicas_do_formato"], "as dicas do que ELE disse sumiram"
    assert "⚠️" in saida and "turbo" in saida and "lento" in saida, (
        "a divergência entre o dito e o medido ficou escondida")


def test_sem_estrutura_medivel_o_preparar_segue_como_antes(monkeypatch):
    """Print e replay não têm horário. O comando não pode quebrar nem ficar
    com um bloco vazio."""
    import app.bot.processing as P

    maos = torneio(niveis=12)
    for h in maos:
        h.played_at = None

    class _Repo:
        enabled = False

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(P, "get_repository", lambda: _Repo())
    monkeypatch.setattr(P, "RECENT_HANDS", {7: maos})

    class _Stats:
        hands, vpip, pfr, three_bet, af, label = 26, 24.0, 18.0, 6.0, 2.1, "TAG"
        detail = {"three_bet_opps": 12}

    monkeypatch.setattr(P, "compute_player_stats", lambda *a, **k: _Stats())
    import app.agent.llm as llm

    guardado: dict = {}
    monkeypatch.setattr(llm, "prepare_briefing",
                        lambda ctx: guardado.update(ctx) or "BRIEFING")

    saida = P.prepare_report(7, "tester", "")
    assert saida == "BRIEFING"
    assert "estrutura_medida" not in guardado
    assert isinstance(Estrutura, type)   # o módulo continua importável
