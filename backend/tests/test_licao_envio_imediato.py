"""Aprovar dispara na HORA — não no dia seguinte.

Pedido do dono (07/08): "seria legal disparar quando eu faço a seleção, no
mesmo instante e não só no outro dia". Ele aprovou a #24 e ficou esperando
sem ver nada acontecer.

A trava anti-rajada existe pelo outro lado: aprovar três seguidas não pode
virar três pushes no telefone do aluno — é a diferença entre um canal que
ele espera e um que ele silencia.
"""
from datetime import datetime, timedelta, timezone

from app.bot.licao_envio import (JANELA_ANTI_RAJADA_H, pode_disparar_agora,
                                 texto_da_licao)

_LICAO = {"id": 24, "titulo": "Iso contra limpers", "spot": "Isolou 2 limpers",
          "licao": "C-bet claro: 12 outs", "ev_bb": 4.2}


def test_nunca_enviou_dispara():
    assert pode_disparar_agora(None) is True


def test_dentro_da_janela_vai_pra_fila():
    assert pode_disparar_agora(0.5) is False
    assert pode_disparar_agora(JANELA_ANTI_RAJADA_H - 0.1) is False


def test_passada_a_janela_dispara():
    assert pode_disparar_agora(JANELA_ANTI_RAJADA_H) is True
    assert pode_disparar_agora(30.0) is True


def test_texto_termina_com_o_convite_a_mao():
    """O CTA é o motivo da lição existir — ataca a muralha da 1ª mão."""
    t = texto_da_licao(_LICAO)
    assert "Manda uma mão sua" in t
    assert t.index("Manda uma mão sua") > t.index("C-bet claro")
    assert "anonimizada" in t or "anonimizado" in t


def test_resultado_da_mao_nao_vira_custo_da_decisao():
    """ev_bb vem de hand_analysis.ev_loss = RESULTADO líquido da mão. Colado
    na lição como "custou/rendeu", ensina resultadismo — o pecado que R5 do
    prompt proíbe, entrando pelo encanamento (auditoria de poker, 07/08)."""
    for ev in (4.2, -9.3, None):
        t = texto_da_licao({**_LICAO, "ev_bb": ev})
        assert "custou" not in t and "rendeu" not in t


def test_horas_desde_o_ultimo_envio_le_o_banco():
    from app.bot.licao_envio import horas_desde_o_ultimo_envio

    agora = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
    ontem = (agora - timedelta(hours=25)).isoformat()

    class _Resp:
        def __init__(self, data):
            self.data = data

    class _Q:
        def __init__(self, data):
            self._d = data
            self.not_ = self

        def select(self, *a, **k):
            return self

        def is_(self, *a):
            return self

        def order(self, *a, **k):
            return self

        def limit(self, *a):
            return self

        def execute(self):
            return _Resp(self._d)

    class _Repo:
        def __init__(self, data):
            self._d = data

        @property
        def client(self):
            repo = self

            class _C:
                def table(self, _):
                    return _Q(repo._d)
            return _C()

    assert horas_desde_o_ultimo_envio(_Repo([]), agora) is None
    h = horas_desde_o_ultimo_envio(_Repo([{"enviada_em": ontem}]), agora)
    assert h is not None and 24.9 < h < 25.1


def test_comando_dispara_e_nao_so_enfileira():
    """A regra tem que valer no COMANDO — era lá que morria."""
    import inspect

    import tests.test_licoes_reply_comportamento as comportamento

    # o comando DISPARA (não só enfileira) e a trava anti-rajada segura a
    # segunda seguida — os dois medidos rodando o comando, não lendo o fonte
    for nome in ("test_ok_aprova_e_dispara_a_licao_certa",
                 "test_a_trava_anti_rajada_enfileira_em_vez_de_disparar",
                 "test_o_ja_fura_a_trava_e_envia"):
        assert hasattr(comportamento, nome), f"{nome} sumiu"


def test_cron_e_comando_usam_o_MESMO_motor():
    """Duplicar o envio é o jeito clássico de os dois divergirem."""
    import inspect

    from app.bot import processing
    from scripts import licao_do_dia

    assert "from app.bot.licao_envio import" in inspect.getsource(licao_do_dia)
    assert "from app.bot.licao_envio import" in \
        inspect.getsource(processing.licoes_reply)
