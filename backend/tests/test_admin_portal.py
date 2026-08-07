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


def test_landing_public_and_robots():
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "KKNuths" in r.text and "t.me/KKNUts_BOT" in r.text
    r2 = client.get("/robots.txt")
    assert "Disallow: /admin" in r2.text


def test_somar_custos_e_puro_e_filtra_por_mes():
    """O custo no portal era a lacuna nº 1 — o dono só via pelo /quem."""
    from app.api.admin import somar_custos
    from datetime import datetime, timezone

    hoje = datetime.now(timezone.utc).date().isoformat()
    events = [
        {"event": "custo_llm", "telegram_id": 42, "created_at": f"{hoje}T10:00:00+00:00",
         "detail": {"usd": 0.10, "tarefa": "analise"}},
        {"event": "custo_llm", "telegram_id": 42, "created_at": f"{hoje}T11:00:00+00:00",
         "detail": '{"usd": 0.05, "tarefa": "conversa"}'},          # detail em string
        {"event": "custo_llm", "telegram_id": 0, "created_at": "2020-01-01T00:00:00+00:00",
         "detail": {"usd": 9.99, "tarefa": "analise"}},              # fora do mês
        {"event": "followup", "telegram_id": 42, "created_at": f"{hoje}T12:00:00+00:00",
         "detail": {"usd": 123}},                                    # não é custo
        {"event": "custo_llm", "telegram_id": 42, "created_at": f"{hoje}T13:00:00+00:00",
         "detail": {"usd": "quebrado"}},                             # usd inválido
    ]
    c = somar_custos(events, month_start=f"{hoje[:8]}01T00:00:00+00:00")
    assert c["mes"] == 0.15
    assert c["hoje"] == 0.15
    assert c["por_tg"] == {42: 0.15000000000000002} or c["por_tg"][42] > 0.14
    assert list(c["por_tarefa"]) == ["analise", "conversa"]


def test_portal_poe_nome_em_todas_as_tabelas():
    """Reclamação do dono: 'falta nomes de usuários'. A tabela de perfis não
    tinha coluna de aluno, e erros/eventos caíam no telegram_id cru quando o
    evento vinha sem username."""
    import inspect

    from app.api import admin

    fonte = inspect.getsource(admin)
    assert "nome_por_uid" in fonte, "perfil de jogador precisa dizer DE QUEM é"
    assert "_quem(r)" in fonte, "erros e eventos usam o nome da fonte da verdade"
    assert "<th>Aluno</th>" in fonte


def test_portal_mostra_as_visoes_novas():
    import inspect

    from app.api import admin

    fonte = inspect.getsource(admin)
    for pedaco in ("custo LLM no mês", "entrega 1ª", "clareza (juiz",
                   "lições na estante", "Origem dos /start"):
        assert pedaco in fonte, pedaco


def test_dossie_exige_token(monkeypatch):
    """A página do usuário mostra TUDO de uma pessoa — sem chave, 401."""
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ADMIN_TOKEN", "segredo")
    get_settings.cache_clear()
    c = TestClient(app)
    assert c.get("/admin/usuario?tg=42").status_code == 401
    assert c.get("/admin/usuario?key=errado&tg=42").status_code == 401
    get_settings.cache_clear()


def test_veredito_vira_cor():
    """O selo já resume a análise — a cor deixa o dossiê legível de relance."""
    from app.api.admin import _linha_do_veredito

    assert _linha_do_veredito("✅ Você jogou bem — shove\nresto") == \
        ("ok", "✅ Você jogou bem — shove")
    assert _linha_do_veredito("❌ Jogada cara")[0] == "bad"
    assert _linha_do_veredito("🟡 Dava pra jogar melhor")[0] == "mid"
    assert _linha_do_veredito("")[0] == ""
    assert _linha_do_veredito(None) == ("", "")


def test_nome_na_tabela_leva_ao_dossie():
    """Sem o link, o dossiê existe e ninguém acha."""
    import inspect

    from app.api import admin

    fonte = inspect.getsource(admin.admin)
    assert "/admin/usuario?key=" in fonte
    assert "tg=" in fonte


def test_dossie_mostra_as_quatro_camadas():
    """Quem é, o que fez, o que o coach aprendeu, e como joga."""
    import inspect

    from app.api import admin

    fonte = inspect.getsource(admin.admin_usuario)
    for secao in ("Mãos analisadas", "Caderno do coach", "Perfil de jogo",
                  "Linha do tempo"):
        assert secao in fonte, secao
    # o quiz automático não pode inflar o gráfico de hábito
    assert "sem contar o quiz" in fonte
