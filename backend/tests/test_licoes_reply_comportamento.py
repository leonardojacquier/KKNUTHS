"""O comando /licoes, rodado — não lido.

Três testes ALTO da varredura de 09/08 moravam aqui, todos assim:

    fonte = inspect.getsource(processing.licoes_reply)
    assert '"aprovada": True' in fonte
    assert "Não mandei" in fonte
    assert fonte.index("problemas_da_licao") < fonte.index("enviar_licao")

Comparar POSIÇÃO de duas strings no texto-fonte é a versão mais frágil do
padrão: passa com o portão dentro de um `if False`, com o retorno
descartado, ou com as duas linhas em ramos que nunca se encontram.

Aqui o comando roda contra um duplo de banco que aplica os filtros, e as
asserções são sobre o que mudou no banco e o que foi enviado ao aluno.
"""
from __future__ import annotations

import pytest

from app.bot import processing as proc

_LICAO_BOA = {
    "id": 7, "titulo": "Overpair em board seco",
    "spot": "KK no BTN, flop 2-7-9 rainbow, heads-up contra o BB.",
    "licao": "Segue apostando cerca de um terço do pote: o range dele "
             "tem poucos pares fortes e você nega equity barato.",
    "categoria": "postflop", "ev_bb": 1.4,
    "aprovada": False, "enviada_em": None, "hand_analysis_id": None,
}
# a lição #26 do caso real: generaliza de uma mão só e afirma dominância
_LICAO_RUIM = {
    "id": 8, "titulo": "Sempre pague",
    "spot": "Nessa mão o vilão tinha 77 e apostou o river.",
    "licao": "Contra esse tipo de jogador você sempre paga, é obrigatório.",
    "categoria": "postflop", "ev_bb": 0.9,
    "aprovada": False, "enviada_em": None, "hand_analysis_id": None,
}


class _Tabela:
    """Aplica os filtros e REGISTRA os updates.

    Um duplo que ignore `eq` faria o comando parecer certo aprovando a lição
    errada — que é o defeito que estes testes existem para pegar.
    """

    def __init__(self, estado):
        self.estado = estado
        self._f: list = []
        self._pend: dict | None = None
        self._count = False

    def select(self, *_a, count=None):
        self._count = count == "exact"
        return self

    def update(self, campos):
        self._pend = dict(campos)
        return self

    def eq(self, col, val):
        self._f.append((col, val))
        return self

    def is_(self, col, val):
        self._f.append((col, None if val == "null" else val))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def _casam(self, linha):
        return all(linha.get(c) == v for c, v in self._f)

    def execute(self):
        alvo = [l for l in self.estado["linhas"] if self._casam(l)]
        if self._pend is not None:
            for linha in alvo:
                linha.update(self._pend)
                self.estado["updates"].append((linha["id"], dict(self._pend)))
            self._pend = None
        return type("R", (), {"data": alvo, "count": len(alvo)})()


@pytest.fixture
def licoes(monkeypatch):
    """Prepara o banco falso e devolve (rodar_comando, estado)."""
    estado = {"linhas": [dict(_LICAO_BOA), dict(_LICAO_RUIM)],
              "updates": [], "enviados": []}

    class _Repo:
        enabled = True

        class client:
            @staticmethod
            def table(_nome):
                return _Tabela(estado)

        def __getattr__(self, _n):
            return lambda *a, **k: None

    monkeypatch.setattr(proc, "get_repository", lambda: _Repo())

    import app.bot.licao_envio as envio

    def _enviar(_repo, _token, linha):
        estado["enviados"].append(linha["id"])
        linha["enviada_em"] = "2026-08-09"
        return {"enviados": 3, "fila": 0}

    monkeypatch.setattr(envio, "enviar_licao", _enviar)
    monkeypatch.setattr(envio, "pode_disparar_agora", lambda _h: True)
    monkeypatch.setattr(envio, "horas_desde_o_ultimo_envio", lambda _r: 99.0)

    def _cfg():
        class _C:
            telegram_bot_token = "tok"
        return _C()

    monkeypatch.setattr(proc, "get_settings", _cfg)
    return (lambda *args: proc.licoes_reply(list(args))), estado


def _linha(estado, lid):
    return next(l for l in estado["linhas"] if l["id"] == lid)


def test_ok_aprova_e_dispara_a_licao_certa(licoes):
    rodar, estado = licoes
    saida = rodar("7", "ok")

    assert _linha(estado, 7)["aprovada"] is True
    assert estado["enviados"] == [7], (
        f"enviou {estado['enviados']} — tinha que enviar só a #7")
    assert _linha(estado, 8)["aprovada"] is False, "aprovou a lição errada"
    assert "ENVIADA agora" in saida or "enviada" in saida.lower()


def test_o_portao_de_qualidade_PARA_o_envio(licoes):
    """Sinaliza e para. A asserção que a substring não fazia: a lição com
    defeito NÃO chega a aluno nenhum."""
    rodar, estado = licoes
    saida = rodar("8", "ok")

    assert estado["enviados"] == [], "a lição com defeito foi enviada"
    assert _linha(estado, 8)["aprovada"] is False, (
        "marcou como aprovada mesmo tendo barrado o envio")
    assert "Não mandei" in saida
    assert "/licoes 8 ja" in saida, "barrou sem oferecer a saída"


def test_o_ja_fura_a_trava_e_envia(licoes):
    """Não é prisão: o dono decide com o defeito na tela."""
    rodar, estado = licoes
    saida = rodar("8", "ja")

    assert estado["enviados"] == [8]
    assert _linha(estado, 8)["aprovada"] is True
    assert "8" in saida


def test_nao_reenvia_o_que_ja_saiu(licoes):
    rodar, estado = licoes
    _linha(estado, 7)["enviada_em"] = "2026-08-01"

    saida = rodar("7", "ok")
    assert estado["enviados"] == [], "repetiu lição já enviada"
    assert "já foi enviada" in saida


def test_desaprovar_tira_da_fila(licoes):
    rodar, estado = licoes
    rodar("7", "ok")
    assert _linha(estado, 7)["aprovada"] is True

    rodar("7", "nao")
    assert _linha(estado, 7)["aprovada"] is False, (
        "desaprovar não desfez a aprovação")


def test_a_trava_anti_rajada_enfileira_em_vez_de_disparar(licoes, monkeypatch):
    """Aprovar três seguidas não pode virar três pushes no mesmo minuto."""
    import app.bot.licao_envio as envio

    monkeypatch.setattr(envio, "pode_disparar_agora", lambda _h: False)
    monkeypatch.setattr(envio, "horas_desde_o_ultimo_envio", lambda _r: 1.0)

    rodar, estado = licoes
    saida = rodar("7", "ok")

    assert _linha(estado, 7)["aprovada"] is True, "não enfileirou"
    assert estado["enviados"] == [], "disparou dentro da janela anti-rajada"
    assert "aprovada" in saida.lower()
