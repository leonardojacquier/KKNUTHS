"""Nenhuma rota executa comando de bot a partir de identidade não verificada.

Achado da auditoria de 07/08: POST /telegram/webhook aceitava qualquer JSON
anônimo, montava um Update com `Update.de_json(body)` e chamava
process_update. Como TODA autorização de admin é `tg_id != ADMIN_TELEGRAM_ID`
e esse tg_id vem do corpo da requisição, um curl sem credencial nenhuma
executava comando de dono — e disparava análise na conta de qualquer aluno,
gastando cota e crédito da Anthropic.

A rota nem estava em uso: o bot roda run_polling(). Era superfície pura,
servida no mesmo app FastAPI que responde poker.vortex369.com.br.

Este teste é a memória disso. Se alguém reabrir o webhook, tem que ser com
segredo conferido — não com a identidade vindo do payload.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app


def _forjado(tg_id: int, texto: str) -> dict:
    """Um update do Telegram como o atacante escreveria."""
    return {
        "update_id": 1,
        "message": {
            "message_id": 1,
            "date": 0,
            "chat": {"id": tg_id, "type": "private"},
            "from": {"id": tg_id, "is_bot": False, "first_name": "quemquer"},
            "text": texto,
        },
    }


def test_webhook_do_telegram_nao_existe_mais():
    """404/405 — nunca 200. O bot é polling; esta rota só dava poder."""
    from app.quota import ADMIN_TELEGRAM_ID

    c = TestClient(app)
    r = c.post("/telegram/webhook",
               json=_forjado(ADMIN_TELEGRAM_ID, "/planode 111111 premium"))
    assert r.status_code in (404, 405), (
        f"a rota respondeu {r.status_code}: identidade de admin voltou a "
        "poder ser forjada pelo corpo da requisição")


def _rotas_que_aceitam_post() -> list[str]:
    """Descobertas do app REAL, não de uma lista escrita à mão.

    É o ponto todo: uma rota nova nasce coberta, sem ninguém lembrar de vir
    aqui acrescentá-la.
    """
    achadas = []
    for r in app.routes:
        metodos = getattr(r, "methods", None) or set()
        if "POST" in metodos:
            achadas.append(getattr(r, "path", ""))
    return [p for p in achadas if p]


def test_nenhuma_rota_executa_comando_de_bot_com_json_anonimo(monkeypatch):
    """A defesa geral, por COMPORTAMENTO.

    A versão anterior varria o texto-fonte atrás de `Update.de_json` e
    `process_update`. Isso só pega uma rota que repita esses dois nomes
    literais — um helper com outro nome, ou o dict repassado para outro
    módulo, passava batido. E foi assim que o padrão de teste por substring
    deixou passar a inversão de um portão em 09/08.

    Aqui as rotas são descobertas do app real e cada uma leva o payload
    forjado. O critério é duplo: nenhuma responde 200, e nenhuma chega a
    tocar o despachante do bot.
    """
    tocou: list = []

    # se qualquer rota tentar despachar um update, isto registra
    import app.bot.handlers as handlers

    for nome in ("process_update", "build_application"):
        if hasattr(handlers, nome):
            monkeypatch.setattr(handlers, nome,
                                lambda *a, **k: tocou.append(nome) or None,
                                raising=False)

    from app.quota import ADMIN_TELEGRAM_ID

    c = TestClient(app)
    forjado = _forjado(ADMIN_TELEGRAM_ID, "/planode 111111 premium")
    rotas = _rotas_que_aceitam_post()
    assert rotas, "não achei nenhuma rota POST — o teste ficaria vazio"

    # Rota que responde 200 a um update do Telegram precisa estar aqui, com
    # o motivo. Uma rota NOVA que responda 200 quebra o teste — que é o
    # ponto: a lista é a decisão consciente, não a descoberta automática.
    aceitam_200 = {
        "/stripe/webhook": "billing desligado: responde {'ignored'} sem ler "
                           "nada do corpo e sem tocar em usuário nenhum",
    }
    for path in rotas:
        r = c.post(path, json=forjado)
        if r.status_code == 200:
            assert path in aceitam_200, (
                f"{path} respondeu 200 a um update do Telegram forjado com "
                f"identidade de admin — se for inofensivo, declare o motivo "
                f"em `aceitam_200`. Corpo: {r.text[:200]}")
            assert "planode" not in r.text and "premium" not in r.text, (
                f"{path} devolveu eco do comando forjado")
    assert not tocou, (
        f"uma rota despachou o update forjado para o bot: {tocou}")


def test_o_webhook_do_stripe_nunca_aplica_evento_sem_assinatura(monkeypatch):
    """O contraste que prova que não é paranoia: o do Stripe sempre validou.
    Se ele parar de validar, é o mesmo buraco em outra porta.

    Por COMPORTAMENTO, e nos dois estados do produto:

    - billing DESLIGADO (hoje): responde `{"ignored"}` e não chama o handler.
      200 aqui é inofensivo — nada é lido do corpo.
    - billing LIGADO: sem `stripe-signature` o handler tem que RECUSAR, e a
      rota devolver não-2xx. 200 com {"error"} marcaria o evento como
      entregue e o Stripe não reenviaria.
    """
    import app.billing as billing

    vistos: list = []

    def _handler(payload, sig):
        vistos.append(sig)
        if not sig:
            raise ValueError("sem assinatura")
        return {"ok": True}

    monkeypatch.setattr(billing, "handle_webhook", _handler)

    c = TestClient(app)
    r = c.post("/stripe/webhook",
               json={"type": "checkout.session.completed"})

    if not vistos:                      # billing desligado, curto-circuito
        assert r.status_code == 200 and "ignored" in r.text, (
            "billing desligado tem que ignorar sem processar")
        return

    assert vistos == [None], "chegou ao handler com assinatura inventada"
    assert r.status_code == 400, (
        f"evento sem assinatura respondeu {r.status_code}; 2xx faria o "
        "Stripe marcar como entregue e não reenviar")


@pytest.mark.parametrize("rota", ["/telegram/webhook", "/telegram/update"])
def test_variantes_obvias_tambem_nao_respondem(rota):
    c = TestClient(app)
    assert c.post(rota, json=_forjado(1, "/quem")).status_code in (404, 405)
