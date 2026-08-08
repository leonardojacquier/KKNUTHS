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


def test_nenhuma_rota_monta_update_do_corpo_da_requisicao():
    """A defesa geral: nenhum endpoint pode transformar JSON anônimo em
    comando de bot. Pega também uma rota nova que copie o padrão antigo."""
    import inspect

    from app.api import main

    # só CÓDIGO: o comentário que explica a remoção cita os dois nomes de
    # propósito, e comentário não executa nada
    codigo = "\n".join(l for l in inspect.getsource(main).splitlines()
                       if not l.lstrip().startswith("#"))
    assert "Update.de_json" not in codigo
    assert "process_update" not in codigo


def test_o_webhook_do_stripe_continua_conferindo_assinatura():
    """O contraste que prova que não é paranoia: o do Stripe sempre validou.
    Se ele parar de validar, é o mesmo buraco em outra porta."""
    import inspect

    from app.api import main

    fonte = inspect.getsource(main.stripe_webhook)
    assert "stripe-signature" in fonte
    assert "handle_webhook(payload, sig)" in fonte


@pytest.mark.parametrize("rota", ["/telegram/webhook", "/telegram/update"])
def test_variantes_obvias_tambem_nao_respondem(rota):
    c = TestClient(app)
    assert c.post(rota, json=_forjado(1, "/quem")).status_code in (404, 405)
