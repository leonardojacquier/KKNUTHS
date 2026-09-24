"""'Tu que não enxergou as mãos que eu mandei' — o aluno tinha razão.

21/09, 00:36-00:52. O dono mandou 5 replays do PPPoker em 12 minutos e
perguntou por que "toda mão" o estava ferrando. O coach respondeu QUATRO
vezes que "das últimas 12 mãos de showdown, 10 foram positivas" e que "não
achei as 5 mãos — talvez sejam de outra sessão". As 5 estavam no banco. O
coach olhou para o lugar errado, e dois defeitos somados explicam por quê:

  A. `search_hands` e `find_hand` faziam `for h in reversed(hands)` com o
     comentário "mais recentes primeiro" — mas `get_all_hands` JÁ devolve do
     mais recente para o mais antigo. O reversed inverte: a tool entregava as
     12 mãos mais ANTIGAS como "últimas". As "últimas 12 de showdown" eram
     GGPoker de julho.

  B. Replay do PPPoker grava `played_at = NULL` (52 das 65 mãos sem data do
     dono são replays). Postgres põe NULL primeiro no DESC, em ordem
     arbitrária — mesmo sem o A, as 5 novas estariam perdidas num bloco de 65
     sem ordem nenhuma.

É o METODO §1 na conversa: número certo sobre a população errada. O aluno
que recebe "você ganhou 10 de 12" sobre mãos que não são as dele tem o
direito de xingar.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from app.analysis import handsearch as HS
from app.parsers import parse_text

_AMOSTRA = pathlib.Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt"


def _tres_maos(datas):
    """Três mãos reais da amostra, com played_at e hand_id controlados, na
    ORDEM em que o repositório devolve (mais recente primeiro)."""
    maos = parse_text(_AMOSTRA.read_text())[:3]
    assert len(maos) == 3
    out = []
    for i, (h, quando) in enumerate(zip(maos, datas)):
        h = h.model_copy(deep=True)
        h.played_at = quando
        h.hand_id = f"mesma-mao-{i}"
        out.append(h)
    return out


# ---- A) a busca respeita a ordem que o repositório entrega ------------------

def test_search_hands_devolve_a_mais_recente_primeiro(monkeypatch):
    monkeypatch.setattr(HS, "match_pattern", lambda *a, **k: True)
    maos = _tres_maos(["2026-09-21T00:48:00", "2026-08-09T20:25:00",
                       "2026-07-09T10:00:00"])
    achadas = HS.search_hands(maos, "showdown", limit=3)
    assert [m["hand_id"] for m in achadas] == ["mesma-mao-0", "mesma-mao-1",
                                               "mesma-mao-2"], (
        "a busca inverteu a ordem: entregou a mão mais ANTIGA como 'última'")


def test_search_hands_com_limite_pega_as_novas_e_nao_as_velhas(monkeypatch):
    """O caso real: limit=12 sobre 500 mãos pegava as 12 de julho."""
    monkeypatch.setattr(HS, "match_pattern", lambda *a, **k: True)
    maos = _tres_maos(["2026-09-21T00:48:00", "2026-08-09T20:25:00",
                       "2026-07-09T10:00:00"])
    achadas = HS.search_hands(maos, "loss", limit=1)
    assert achadas[0]["hand_id"] == "mesma-mao-0"


def test_find_hand_devolve_a_mais_recente_primeiro():
    maos = _tres_maos(["2026-09-21T00:48:00", "2026-08-09T20:25:00",
                       "2026-07-09T10:00:00"])
    achadas = HS.find_hand(maos, "mesma-mao", limit=3)
    assert [m["hand_id"] for m in achadas] == ["mesma-mao-0", "mesma-mao-1",
                                               "mesma-mao-2"]


def test_replay_sem_played_at_nao_perde_o_lugar(monkeypatch):
    """A mão que o aluno acabou de mandar vem primeiro do repositório mesmo
    sem data de jogo; a busca não pode reordenar por conta própria."""
    monkeypatch.setattr(HS, "match_pattern", lambda *a, **k: True)
    maos = _tres_maos([None, "2026-08-09T20:25:00", "2026-07-09T10:00:00"])
    assert HS.search_hands(maos, "loss", limit=1)[0]["hand_id"] == "mesma-mao-0"


# ---- B) a data nunca fica vazia, e o desempate é por chegada ----------------

class _Q:
    """Query builder falso: grava as chamadas e devolve o que mandarem."""

    def __init__(self, log, data=None):
        self.log, self.data = log, data or []

    def __getattr__(self, nome):
        def _m(*a, **k):
            self.log.append((nome, a, k))
            return self
        return _m

    def execute(self):
        class R:
            data = self.data
        return R()


def _repo(log, data=None):
    from app.db.repository import Repository

    class _Cli:
        def table(self, nome):
            log.append(("table", (nome,), {}))
            return _Q(log, data)

    r = Repository.__new__(Repository)
    r.enabled = True
    r._url = r._key = "x"
    r._client = _Cli()
    return r


def test_save_hand_preenche_played_at_quando_o_parser_nao_sabe():
    """Replay e print não trazem a hora do jogo. Gravar NULL joga a mão num
    limbo sem ordem; a hora de CHEGADA é a melhor data que existe."""
    log: list = []
    h = _tres_maos([None, None, None])[0]
    _repo(log, data=[{"id": "row-1"}]).save_hand("u-1", h)
    payload = next(a[0] for n, a, _ in log if n == "upsert")
    assert payload["played_at"], "gravou played_at vazio"
    assert re.match(r"\d{4}-\d{2}-\d{2}T", payload["played_at"])


def test_save_hand_respeita_a_data_que_o_parser_trouxe():
    log: list = []
    h = _tres_maos(["2026-08-09T20:25:00", None, None])[0]
    _repo(log, data=[{"id": "row-1"}]).save_hand("u-1", h)
    payload = next(a[0] for n, a, _ in log if n == "upsert")
    assert payload["played_at"] == "2026-08-09T20:25:00"


def test_get_all_hands_desempata_por_chegada():
    """Entre duas mãos sem played_at (as antigas, antes do backfill), a que
    chegou depois vem primeiro — não a que o Postgres quiser."""
    log: list = []
    _repo(log).get_all_hands("u-1", limit=10)
    ordens = [(a[0], k.get("desc")) for n, a, k in log if n == "order"]
    assert ("played_at", True) in ordens
    assert ("created_at", True) in ordens, "sem desempate por created_at"
    assert ordens.index(("played_at", True)) < ordens.index(("created_at", True))


def test_ha_backfill_para_as_maos_antigas_sem_data():
    """O conserto no save só vale daqui pra frente; as 65 antigas do dono
    (e as dos outros) precisam de um oneshot — o mecanismo do projeto."""
    raiz = pathlib.Path(__file__).resolve().parent.parent
    scripts = sorted((raiz / "deploy" / "oneshot").glob("*backfill-played-at*"))
    assert scripts, "não há oneshot de backfill do played_at"
    fonte = scripts[-1].read_text()
    assert "played_at" in fonte and "created_at" in fonte
    assert re.search(r'is_\(\s*"played_at"\s*,\s*"null"\s*\)', fonte), (
        "o backfill tem que mirar SÓ as mãos sem data — nunca sobrescrever "
        "uma data de jogo verdadeira")


# ---- o calque que não era ----------------------------------------------------

@pytest.mark.parametrize("frase", [
    "não teve sequência de 3 coolers seguidos aí",
    "não achei sequência de 5 mãos seguidas no vermelho",
    "é sequência normal de variância num jogo",
    "não achei sequência de 5 river beats",
])
def test_sequencia_com_numero_ou_adjetivo_no_meio_nao_e_straight(frase):
    """21/09: três acusações do juiz na mesma conversa, todas 'ordem de
    acontecimentos'. A exceção exigia a palavra logo depois de 'de'; um
    número ('de 3 coolers') ou um adjetivo ('normal de variância') quebrava."""
    from scripts.output_judge import judge_answer

    achados = [p for p in judge_answer("✅ jogou bem. " + frase) if "calque" in p]
    assert not any("'sequência'" in a for a in achados), achados


def test_straight_continua_acusado_depois_de_afrouxar():
    from scripts.output_judge import judge_answer

    for frase in ("você fechou a sequência no river", "tinha 8 outs pra sequência",
                  "o board completa a sequência até o A"):
        achados = [p for p in judge_answer("✅ ok. " + frase) if "calque" in p]
        assert any("'sequência'" in a for a in achados), frase
