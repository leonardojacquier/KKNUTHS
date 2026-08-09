"""Lição do dia: envio diário do que o DONO aprovou — nunca do estoque cru.

Pedido do dono (07/08): "criar um enviar diário dessa lição escolhida".
A trava é a de sempre: o destilador estoca, o dono aprova (/licoes N ok),
o cron envia UMA por dia. Lição não aprovada não sai; lição já enviada não
repete; fila vazia é silêncio pro aluno e aviso pro dono.
"""
import inspect

from scripts.licao_do_dia import main, texto_da_licao

_LICAO = {"id": 7, "titulo": "Pagar river sem preço",
          "spot": "Torneio, ~20bb. Vilão dá overbet no river.",
          "licao": "Pedia 33% e a mão tinha 18%.", "ev_bb": -9.3,
          "categoria": "river"}


def test_texto_traz_a_licao_e_termina_convidando_a_mao():
    t = texto_da_licao(_LICAO)
    assert "Lição do dia" in t and _LICAO["titulo"] in t
    import re
    # o número que prova a lição vem no TEXTO dela (exigido pelo destilador),
    # não de um sufixo colado com o resultado da mão
    assert re.search(r"\d", _LICAO["licao"]), "a fixture perdeu o número"
    assert _LICAO["licao"] in t
    assert t.rstrip().endswith("analiso na hora."), \
        "o CTA da primeira mão fecha SEMPRE — é o gargalo do funil"


def test_nao_cola_resultado_da_mao_como_custo_da_decisao():
    """Auditoria de poker (07/08): o sufixo "(custou X bb)" vinha de
    hand_analysis.ev_loss, que guarda o RESULTADO líquido da mão, não o EV
    da decisão. Saía "custou 37,4bb" numa lição de mão GANHA (+40,8bb) e
    "custou 12,5bb" num call de KK que estava certo."""
    for ev in (11.9, -9.3, None):
        t = texto_da_licao({**_LICAO, "ev_bb": ev})
        assert "custou" not in t and "rendeu" not in t


def test_ev_ausente_nao_quebra_nem_inventa():
    t = texto_da_licao({**_LICAO, "ev_bb": None})
    assert "custou" not in t and "rendeu" not in t


def test_licao_anonima_nao_vaza_aluno():
    """O texto enviado sai só do que o destilador já anonimizou."""
    t = texto_da_licao(_LICAO)
    assert "anonimizado" in t.lower()
    for campo in ("hand_analysis_id", "user", "telegram"):
        assert campo not in t


class _Tabela:
    """Duplo de PostgREST que APLICA os filtros.

    Fidelidade importa: o PostgREST filtra a linha inteira e projeta só no
    `execute()`. Um duplo que ignore `eq`/`is_` faz o teste passar com a
    query errada — que é a armadilha que este teste existe para não repetir.
    """

    def __init__(self, linhas):
        self._todas = list(linhas)
        self._f: list = []
        self._ordem = None
        self._desc = False
        self._lim = None
        self._count = False

    def select(self, *_a, count=None):
        self._count = count == "exact"
        return self

    def eq(self, col, val):
        self._f.append(lambda r: r.get(col) == val)
        return self

    def is_(self, col, val):
        alvo = None if val == "null" else val
        self._f.append(lambda r: r.get(col) is alvo)
        return self

    def order(self, col, desc=False):
        self._ordem, self._desc = col, desc
        return self

    def limit(self, n):
        self._lim = n
        return self

    def execute(self):
        out = [r for r in self._todas if all(f(r) for f in self._f)]
        if self._ordem:
            out.sort(key=lambda r: r.get(self._ordem), reverse=self._desc)
        n = len(out)
        if self._lim:
            out = out[:self._lim]
        return type("R", (), {"data": out, "count": n})()


class _RepoFalso:
    enabled = True

    def __init__(self, linhas):
        self._linhas = linhas
        tabela = _Tabela

        class _C:
            @staticmethod
            def table(_nome):
                return tabela(linhas)
        self.client = _C()


def test_so_sai_o_que_foi_aprovado_e_nunca_repete():
    """Por COMPORTAMENTO. A versão anterior conferia as substrings
    `eq("aprovada", True)` e `.order("id")` no texto-fonte — uma query
    reescrita para `eq("aprovada", False)` continuaria contendo a palavra
    "aprovada" e passaria. É o mesmo padrão que deixou passar a inversão de
    um portão em 09/08.
    """
    from app.bot.licao_envio import proxima_licao

    linhas = [
        {"id": 1, "titulo": "crua", "aprovada": False, "enviada_em": None},
        {"id": 2, "titulo": "a certa", "aprovada": True, "enviada_em": None},
        {"id": 3, "titulo": "já saiu", "aprovada": True,
         "enviada_em": "2026-08-01"},
        {"id": 4, "titulo": "mais nova", "aprovada": True, "enviada_em": None},
    ]
    escolhida = proxima_licao(_RepoFalso(linhas))
    assert escolhida is not None, "não achou lição aprovada disponível"
    assert escolhida["id"] == 2, (
        f"saiu a #{escolhida['id']} «{escolhida['titulo']}» — a fila é FIFO "
        "pela mais antiga APROVADA e ainda NÃO enviada")

    # e sem estoque aprovado disponível, não sai nada
    assert proxima_licao(_RepoFalso(
        [r for r in linhas if r["id"] in (1, 3)])) is None


def test_fila_vazia_avisa_o_dono_e_nao_incomoda_o_aluno(monkeypatch):
    """Fila vazia é SILÊNCIO para o aluno e recado para o dono.

    Antes o teste recortava o texto-fonte de `main` entre duas strings e
    procurava `ADMIN_ID` dentro. Aqui os dois efeitos são medidos: quem
    recebeu mensagem, e se `enviar_licao` chegou a ser chamado.
    """
    import scripts.licao_do_dia as m
    from app.bot.licao_envio import ADMIN_ID

    enviados: list = []
    mandou_licao: list = []

    monkeypatch.setattr(m, "_post",
                        lambda _tok, chat, texto: enviados.append((chat, texto)))
    monkeypatch.setattr(m, "enviar_licao",
                        lambda *a, **k: mandou_licao.append(1) or {})
    monkeypatch.setattr(m, "get_repository",
                        lambda: _RepoFalso([{"id": 1, "aprovada": False,
                                             "enviada_em": None}]))

    class _Cfg:
        telegram_bot_token = "tok"

    monkeypatch.setattr(m, "get_settings", lambda: _Cfg())

    assert m.main() == 0
    assert not mandou_licao, "com a fila vazia, o aluno recebeu lição"
    assert [c for c, _ in enviados] == [ADMIN_ID], (
        "a fila vazia tem que avisar o dono, e SÓ o dono")
    assert "VAZIA" in enviados[0][1]


def test_marca_como_enviada_depois_de_enviar():
    """O envio mora em app/bot/licao_envio (comando e cron compartilham)."""
    from app.bot.licao_envio import enviar_licao

    fonte = inspect.getsource(enviar_licao)
    assert "enviada_em" in fonte and "publicada" in fonte
    assert fonte.index("for u in users") < fonte.index('"enviada_em":'), \
        "marca DEPOIS do envio — falha no meio não perde a lição"


def test_comando_aprova_e_desaprova():
    from app.bot.processing import licoes_reply

    fonte = inspect.getsource(licoes_reply)
    assert '"aprovada": True' in fonte and '"aprovada": False' in fonte
    assert "já foi enviada" in fonte, "não deixa reaprovar o que já saiu"
