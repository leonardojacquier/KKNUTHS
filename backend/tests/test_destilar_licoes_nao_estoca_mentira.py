"""O destilador é um modelo barato lendo um summary e escrevendo bonito.

Nada conferia fato de poker: a lição 26 nasceu com "Só AA e QQ te viram
favorito" numa mão de KK e ficou na estante como material aprovável. O dono
lê essa lista para decidir o que vai para TODOS os alunos — uma frase que
nasceu falsa gasta revisão e não vale nada.

Estilo (promessa absoluta, raciocínio por resultado) continua entrando com
aviso: ali o texto se conserta. Mentira, não.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from destilar_licoes import _cartas_da_mao, mentiu_sobre_poker  # noqa: E402

_LICAO_26 = {
    "titulo": "KK contra shove curto: call automático",
    "spot": "CO empurra ~8.4bb efetivo. Você paga com KK.",
    "licao": "Com KK o call rende +7.6bb de EV. Só AA e QQ te viram "
             "favorito — perder para trinca é variância, não erro.",
    "ev_bb": 7.6, "categoria": "preflop",
}


def test_dominancia_falsa_nao_vai_para_a_estante():
    analise = {"hero_cards": ["Kh", "Kd"], "board": []}
    assert mentiu_sobre_poker(_LICAO_26, analise) is True


def test_sem_cartas_o_destilador_nao_barra_no_escuro():
    """Sem as cartas não dá para provar nada — e barrar por suspeita joga
    fora lição boa. O portão do /licoes ainda pega depois."""
    assert mentiu_sobre_poker(_LICAO_26, {}) is False


def test_licao_verdadeira_entra():
    boa = {**_LICAO_26,
           "licao": "Com KK o call rende +7.6bb de EV. Só AA te vira "
                    "favorito nessa profundidade."}
    assert mentiu_sobre_poker(boa, {"hero_cards": ["Kh", "Kd"]}) is False


def test_vicio_de_estilo_nao_barra():
    """'Call automático sempre' é promessa absoluta — vira AVISO na estante,
    não bloqueio. Quem decide o texto é o dono."""
    estilo = {**_LICAO_26,
              "licao": "Com KK o call rende +7.6bb de EV. Call automático "
                       "sempre, sem pensar."}
    assert mentiu_sobre_poker(estilo, {"hero_cards": ["Kh", "Kd"]}) is False


def test_cartas_da_mao_le_o_canonical():
    class _Res:
        data = [{"canonical": {"hero_cards": ["Kh", "Kd"],
                               "final_board": ["2c", "7c", "7h"]}}]

    class _T:
        def select(self, *a, **k):
            return self

        def eq(self, *a, **k):
            return self

        def limit(self, *a, **k):
            return self

        def execute(self):
            return _Res()

    class _Repo:
        class client:
            @staticmethod
            def table(_):
                return _T()

    assert _cartas_da_mao(_Repo(), "H1") == {
        "hero_cards": ["Kh", "Kd"], "board": ["2c", "7c", "7h"]}
    assert _cartas_da_mao(_Repo(), None) == {}


def test_o_main_conta_o_que_barrou(monkeypatch):
    """Barrar em silêncio esconde o defeito: 'lições: 0 novas' parece dia
    fraco quando na verdade o destilador escreveu mentira."""
    import destilar_licoes as d

    gravados, eventos = [], []

    class _T:
        def insert(self, payload):
            gravados.append(payload)
            return self

        def execute(self):
            return type("R", (), {"data": [{"id": "L1"}]})()

    class _Repo:
        enabled = True

        class client:
            @staticmethod
            def table(_):
                return _T()

        @staticmethod
        def log_event(_tg, _u, ev, detalhe=None):
            eventos.append((ev, detalhe or {}))

    # a mão é KK; a lição afirma que o vilão tinha AA e que "sempre paga" —
    # é a #26 do caso real, que nasceu errada e foi para a estante
    verdadeira = {"id": "A1", "hero_cards": ["Kh", "Kd"],
                  "final_board": ["2c", "7c", "9h", "Ac", "Th"]}
    boa = {"titulo": "Overpair em board seco",
           "spot": "KK no BTN, flop 2-7-9 rainbow.",
           "licao": "Segue apostando um terço: ele tem poucos pares fortes."}
    mentirosa = {"titulo": "Só perde para QQ",
                 "spot": "KK contra all-in curto.",
                 "licao": "Com KK você só perde para QQ nesse spot."}

    monkeypatch.setattr(d, "get_repository", lambda: _Repo())
    monkeypatch.setattr(d, "candidatas", lambda *a, **k: [verdadeira,
                                                         dict(verdadeira,
                                                              id="A2")])
    saidas = iter([boa, mentirosa])
    monkeypatch.setattr(d, "destilar", lambda _a: next(saidas))

    assert d.main() == 0

    titulos = [g["titulo"] for g in gravados]
    assert titulos == ["Overpair em board seco"], (
        f"a lição com fato falso foi para a estante: {titulos}")

    nome, detalhe = eventos[-1]
    assert nome == "licoes_destiladas"
    assert detalhe["novas"] == 1
    assert detalhe["mentiras_barradas"] == 1, (
        "barrou em silêncio: 'lições: 0 novas' parece dia fraco quando na "
        "verdade o destilador escreveu mentira")
