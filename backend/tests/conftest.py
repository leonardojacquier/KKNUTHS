"""Isolamento GLOBAL da suite: nenhum teste toca serviço externo.

Sem isto a suite dependia da ORDEM dos módulos: o singleton do repositório
era criado "disabled" por acaso (algum módulo anterior limpava o env). Rodando
um módulo isolado, o singleton nascia com as credenciais reais e os testes
batiam em Supabase/Anthropic de verdade (403 no sandbox, custo em produção).
Aqui cada teste nasce e morre offline, em qualquer ordem.
"""
from __future__ import annotations

import pytest

from app.config import get_settings
from app.db.repository import get_repository

_SECRET_VARS = [
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "VOYAGE_API_KEY",
    "SUPABASE_URL", "SUPABASE_SERVICE_KEY", "STRIPE_SECRET_KEY",
    "TELEGRAM_BOT_TOKEN", "DATABASE_URL",
]


@pytest.fixture(autouse=True)
def _hermetic_env(monkeypatch):
    for var in _SECRET_VARS:
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    get_repository.cache_clear()
    from app.quota import reset_memory

    reset_memory()
    yield
    get_settings.cache_clear()
    get_repository.cache_clear()
    reset_memory()


# ---------------------------------------------------------------------------
# HARNESS DO PIPELINE — roda a análise de ponta a ponta com LLM e banco falsos.
#
# Existe porque meia dúzia de testes afirmava que os guardas estão ligados
# assim: `assert "conferir_dominancia" in inspect.getsource(...)`. Isso confere
# que o NOME aparece no arquivo; não confere que a função é chamada, que o
# retorno dela é usado, nem que o texto entregue mudou. Provado em 09/08:
# trocando `coaching, erro = corrigir_showdown(...)` por `_ign, erro = ...`,
# a mão IMPOSSÍVEL volta ao aluno e 31 testes desses continuam verdes.
#
# Mora no conftest porque quatro arquivos precisam do mesmo aparato.
# ---------------------------------------------------------------------------

_PIPELINE_TG = 990001


class RepoDePipeline:
    """`enabled=True` de propósito: guarda só grava evento com repo ligado, e
    repo desligado faria o teste passar sem medir nada.

    Método não previsto vira registro em vez de AttributeError — assim o teste
    mostra o que o pipeline tocou em vez de morrer na primeira surpresa.
    """

    enabled = True

    def __init__(self):
        self.events: list[tuple] = []

    def log_event(self, telegram_id, username, event, detail=None):
        self.events.append((event, detail))

    def __getattr__(self, nome):
        def _qualquer(*a, **k):
            self.events.append((f"__chamou__:{nome}", None))
            return None
        return _qualquer

    def evento(self, nome):
        for ev, detalhe in self.events:
            if ev == nome:
                return detalhe or {}
        return None


@pytest.fixture
def rodar_pipeline(monkeypatch):
    """Roda `_process_upload_inner` com `ingest` e `coach` injetados.

    Devolve `(texto_entregue, repo, contexto_do_coach)`. O terceiro é o
    `structured` que o modelo recebeu — é ali que se vê se ICM, história do
    resultado e procedência chegaram ao prompt.
    """
    from app.bot import processing as proc

    def _rodar(texto_do_coach: str, hand, site: str = "PPPoker"):
        visto: dict = {}

        def _coach_falso(structured, *a, **k):
            visto["structured"] = structured
            return texto_do_coach

        from app.ingestion.pipeline import IngestResult

        monkeypatch.setattr(proc, "coach", _coach_falso)
        monkeypatch.setattr(proc, "ingest", lambda *a, **k: IngestResult(
            [hand], site, hand.source_format or "txt",
            confidence=1.0, needs_review=False))
        repo = RepoDePipeline()
        saida = proc._process_upload_inner(
            b"bruto", "txt", _PIPELINE_TG, "tester", "pt", repo, None)
        return saida, repo, visto.get("structured") or {}

    yield _rodar
    # estado global por telegram_id não pode vazar para o teste seguinte
    for mapa in (proc.RECENT_HANDS, proc.LAST_ANALYSIS, proc.LAST_UPLOAD_KIND,
                 proc.LAST_HAND_META):
        mapa.pop(_PIPELINE_TG, None)
