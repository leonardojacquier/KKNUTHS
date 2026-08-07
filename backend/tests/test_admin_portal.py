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
                  "em ordem"):
        assert secao in fonte, secao
    # o quiz automático não pode inflar o gráfico de hábito
    assert "sem contar o quiz" in fonte


def test_o_bot_empurrar_nao_conta_como_o_aluno_estar_ativo():
    """A lição de 07/08 marcou os 10 alunos como 'ativos às 01:54' — até quem
    nunca mandou uma mão. Métrica que sobe quando EU aperto um botão mente."""
    import inspect

    from app.api import admin

    assert "licao_recebida" in admin._SO_RECEBEU
    assert "daily_quiz_sent" in admin._SO_RECEBEU
    fonte = inspect.getsource(admin._collect)
    # 'ativos (7 dias)', 'última atividade' e a barra diária usam o mesmo
    # filtro — se um deles escapar, o painel volta a mentir
    assert "agiu = ev not in _SO_SISTEMA and ev not in _SO_RECEBEU" in fonte
    assert "if agiu and ts >= d7" in fonte
    assert "if day and agiu" in fonte
    # e o gráfico do dossiê segue a mesma regra
    assert "ev not in _SO_RECEBEU" in inspect.getsource(admin._dossie)


def test_diario_esconde_ruido_de_sistema():
    """'custo_llm' sozinho era 346 dos ~500 eventos de 14 dias. Deixar isso na
    linha do tempo é o motivo de 'não fica claro como estão as ações'."""
    from app.api.admin import narrar_evento

    for ruido in ("custo_llm", "entrega_ok", "caderno_auto", "nota_resposta",
                  "output_judge", "daily_usage", "sonda_recebimento"):
        assert narrar_evento({"event": ruido, "detail": {"usd": 0.1}}) is None


def test_cron_nunca_aparece_como_acao_de_aluno():
    """A regra que dura é telegram_id<=0, não uma lista de nomes: 'deploy',
    'jornadas', 'anomalias', 'backup_db' e o cron que eu escrever amanhã
    entram todos por essa porta. Lista de nomes eu esqueço de atualizar."""
    from app.api.admin import e_acao_de_gente

    for cron in ("deploy", "jornadas", "anomalias", "backup_db", "coherence",
                 "linguista", "licao_do_dia", "cron_que_ainda_nao_inventei"):
        assert not e_acao_de_gente({"event": cron, "telegram_id": 0}), cron
    assert not e_acao_de_gente({"event": "start", "telegram_id": None})
    # contabilidade tem tg de gente mas não é ação de gente
    assert not e_acao_de_gente({"event": "custo_llm", "telegram_id": 42})
    # e a ação de verdade passa
    assert e_acao_de_gente({"event": "upload", "telegram_id": 42})


def test_diario_mostra_o_conteudo_da_acao():
    """Não basta traduzir o nome do evento: a pergunta que a pessoa fez, a
    resposta que ela deu no quiz e o motivo da falha são A informação."""
    from app.api.admin import narrar_evento

    n = narrar_evento({"event": "followup", "detail": {"q": "vale 3-bet aqui?"}})
    assert "vale 3-bet aqui?" in n["texto"] and n["icone"] == "💬"

    n = narrar_evento({"event": "upload",
                       "detail": '{"site": "PPPoker", "hands": 1,'
                                 ' "quota_remaining": 48}'})   # detail string
    assert "PPPoker" in n["texto"] and "48" in n["texto"]
    assert n["classe"] == "ok"

    n = narrar_evento({"event": "followup_failed",
                       "detail": {"q": "o fold tem equity?",
                                  "motivo": "overloaded"}})
    assert "o fold tem equity?" in n["texto"] and "overloaded" in n["texto"]
    assert n["classe"] == "bad"

    n = narrar_evento({"event": "drill_verdict",
                       "detail": {"verdict": "ruim", "cat": "turn"}})
    assert n["classe"] == "bad" and "turn" in n["texto"]
    assert narrar_evento({"event": "drill_verdict",
                          "detail": {"verdict": "boa"}})["classe"] == "ok"


def test_clique_e_efeito_do_clique_viram_uma_linha_so():
    """btn_share + share_card é UM ato logado duas vezes — o feed mostrava
    'Gerou o card' em duplicata e parecia atividade que não houve."""
    from app.api.admin import _repetido

    ultimo = []
    assert not _repetido("Gerou o card", 42, ultimo)
    assert _repetido("Gerou o card", 42, ultimo)          # o par
    assert not _repetido("Gerou o card", 99, ultimo)      # outra pessoa
    assert not _repetido("Abriu o range", 99, ultimo)
    # mesmo ato de novo, mas NÃO consecutivo: continua aparecendo
    assert not _repetido("Gerou o card", 99, ultimo)


def test_diario_nao_engole_evento_desconhecido():
    """Evento novo que eu ainda não traduzi tem que APARECER, cru — senão a
    ação some do dossiê e ninguém descobre que ela existe."""
    from app.api.admin import narrar_evento

    n = narrar_evento({"event": "recurso_que_ainda_nao_existe", "detail": {}})
    assert n is not None and "recurso_que_ainda_nao_existe" in n["texto"]
    assert n["classe"] == "mut"


def test_diario_escapa_texto_do_usuario():
    """A pergunta é texto de terceiro entrando num HTML sem template."""
    from app.api.admin import narrar_evento

    n = narrar_evento({"event": "followup",
                       "detail": {"q": "<script>alert(1)</script>"}})
    assert "<script>" not in n["texto"] and "&lt;script&gt;" in n["texto"]


def test_interacoes_da_tabela_nao_contam_ruido():
    """A coluna 'Interações' contava custo_llm — todo mundo parecia ativo."""
    import inspect

    from app.api import admin

    fonte = inspect.getsource(admin._collect)
    assert "if agiu:" in fonte
    assert "custo_llm" in admin._SO_SISTEMA
    # e o feed da home tem que filtrar ANTES de cortar, senão as 25 linhas
    # viram 7 ações de gente e 18 de contabilidade
    assert "if e_acao_de_gente(r)][:40]" in fonte


def test_home_mostra_feed_narrado_e_nao_dump():
    """A home era a mesma tabela crua de evento+JSON. O dono clica no portal
    para saber o que está acontecendo, não para ler nome de função."""
    import inspect

    from app.api import admin

    fonte = inspect.getsource(admin.admin)
    assert "narrar_evento(r) if e_acao_de_gente(r)" in fonte
    assert "O que acabou de acontecer" in fonte
    # o dump antigo saiu de cena
    assert "<th>Evento</th><th>Detalhe</th>" not in fonte
    # e cada linha do feed leva ao dossiê da pessoa
    assert "/admin/usuario?key=" in fonte
