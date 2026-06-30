"""Testes offline (sem chaves) de embeddings e billing — garantem degradação graciosa."""
from app.agent.embeddings import embed_query, embed_text
from app.billing import create_checkout_session, handle_webhook, is_enabled


def test_embeddings_none_without_provider():
    assert embed_text("alguma análise de mão") is None
    assert embed_query("river ruim") is None
    assert embed_text("") is None


def test_billing_disabled_without_stripe_key():
    assert is_enabled() is False
    assert create_checkout_session("user-123", "pro") is None


def test_webhook_ignored_when_disabled():
    res = handle_webhook(b"{}", None)
    assert "ignored" in res
