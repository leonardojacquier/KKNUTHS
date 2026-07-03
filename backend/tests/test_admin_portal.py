"""Testes do portal de gestão (/admin): auth por token e render sem banco."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.config import get_settings


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for var in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ADMIN_TOKEN", "tok-de-teste")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_admin_requires_token():
    client = TestClient(app)
    assert client.get("/admin").status_code == 401
    assert client.get("/admin?key=errado").status_code == 401


def test_admin_renders_without_db():
    client = TestClient(app)
    r = client.get("/admin?key=tok-de-teste")
    assert r.status_code == 200
    assert "Gestão" in r.text
    assert "Banco indisponível" in r.text


def test_admin_denied_when_token_unset(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    get_settings.cache_clear()
    client = TestClient(app)
    # sem token configurado, portal fica fechado (nunca aberto por default)
    assert client.get("/admin?key=").status_code == 401
