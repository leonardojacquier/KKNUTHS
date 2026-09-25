"""A sonda que teria pego a queda de verdade — e que NÃO pode gritar na
queda falsa que eu mesmo dei.

Em 2026-07-26 o banco tinha 104 eventos em 6h, todos de cron, e eu declarei
queda. Era um torneio demorando. Esta sonda precisa acertar os dois casos:
gritar quando é webhook/token, e no máximo suspeitar quando é só silêncio.
"""
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "scripts")

from sonda_recebimento import (  # noqa: E402
    HORA_ATIVA, avaliar, em_horario_ativo, texto_do_alerta)

BR = timezone(timedelta(hours=-3))


# --------------------------------------------------------------- horário
def test_janela_ativa_atravessa_a_meia_noite():
    assert em_horario_ativo(datetime(2026, 7, 27, 11, 0, tzinfo=BR))
    assert em_horario_ativo(datetime(2026, 7, 27, 23, 30, tzinfo=BR))
    assert em_horario_ativo(datetime(2026, 7, 27, 1, 0, tzinfo=BR))
    # 04h da manhã: ninguém joga, silêncio é esperado
    assert not em_horario_ativo(datetime(2026, 7, 27, 4, 0, tzinfo=BR))
    assert not em_horario_ativo(datetime(2026, 7, 27, 8, 0, tzinfo=BR))


# --------------------------------------------------------------- veredito
def test_webhook_e_CERTEZA_de_quebra():
    """A falha mais silenciosa: processo verde, log limpo, zero updates."""
    v = avaliar("https://algum.host/hook", True, 0.1, True)
    assert v["nivel"] == "quebrado"
    assert "deleteWebhook" in " ".join(v["problemas"])
    assert "NÃO ESTÁ RECEBENDO" in texto_do_alerta(v)


def test_getme_falhando_e_certeza():
    v = avaliar("", False, 0.1, True)
    assert v["nivel"] == "quebrado"
    assert "token" in " ".join(v["problemas"]).lower()


def test_silencio_longo_e_so_SUSPEITA():
    """O caso que eu errei: 2h36 de silêncio não é prova de queda. Suspeita
    não pode usar a mesma linguagem de certeza."""
    v = avaliar("", True, 5.0, True)
    assert v["nivel"] == "suspeita"
    t = texto_do_alerta(v)
    assert "Suspeita" in t and "NÃO ESTÁ RECEBENDO" not in t
    assert "período calmo" in t


def test_silencio_de_madrugada_nao_alarma():
    """Sem isto a sonda acordaria o dono toda noite."""
    assert avaliar("", True, 8.0, False)["nivel"] == "ok"
    assert texto_do_alerta(avaliar("", True, 8.0, False)) == ""


def test_tudo_certo_nao_fala_nada():
    v = avaliar("", True, 0.5, True)
    assert v["nivel"] == "ok" and texto_do_alerta(v) == ""


def test_nao_saber_o_silencio_nunca_vira_alarme():
    """Banco fora do ar não pode virar 'bot caiu' — seria trocar um
    problema por um alarme falso."""
    assert avaliar("", True, None, True)["nivel"] == "ok"


def test_webhook_grita_mesmo_de_madrugada():
    """Certeza não espera horário comercial."""
    v = avaliar("https://x/hook", True, 0.1, False)
    assert v["nivel"] == "quebrado"


def test_o_cenario_real_de_26_07_nao_dispararia_vermelho():
    """Reprodução do meu falso alarme: sem webhook, token ok, 2,6h de
    silêncio em horário ativo. A sonda pode suspeitar — não pode afirmar."""
    v = avaliar("", True, 2.6, True)
    assert v["nivel"] == "ok", "2,6h ainda está abaixo do limite de 3h"
    v2 = avaliar("", True, 3.5, True)
    assert v2["nivel"] == "suspeita"


def test_evento_de_sistema_nao_conta_como_vida():
    """104 eventos de cron enquanto o bot podia estar mudo: o filtro de
    telegram_id 0 é o coração da sonda."""
    import inspect

    import sonda_recebimento as s

    fonte = inspect.getsource(s.horas_desde_o_ultimo_humano)
    assert "_SISTEMA" in fonte and "not_" in fonte
    assert s._SISTEMA == (0,)


def test_cron_instalado_no_deploy():
    import pathlib

    sh = (pathlib.Path(__file__).resolve().parent.parent
          / "deploy/vps_deploy.sh").read_text()
    assert "sonda_recebimento.py" in sh, "sonda sem cron não roda"
    assert "poker-recebimento" in sh


def test_horario_ativo_configurado_com_folga():
    """10h–02h: cobre a madrugada de quem joga tarde sem alarmar às 5h."""
    assert HORA_ATIVA == (10, 2)
