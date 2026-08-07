"""O portal RENDERIZA conteúdo? — o teste que faltava.

Em 07/08 o dossiê foi para produção mostrando "nenhuma ação registrada" para
alunos que tinham feito sete coisas: a consulta não trazia a coluna que o
filtro lia. 557 testes passaram. Passaram porque 14 deles só conferiam se o
código-FONTE continha certas strings — e o fonte continha. Teste de fonte
passa em página em branco.

Aqui um banco falso, com dados no formato real do Supabase, atravessa as três
páginas de ponta a ponta. O que se afirma é o que o dono vê: o nome do aluno,
a ação que ele fez, o número na caixa. Se a página vier vazia, quebra —
independente do que o fonte diga.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.config import get_settings

TG = 6921203436
UID = "u-1"
# quem só RECEBEU a lição e nunca fez nada — o caso do Eder em produção, que
# aparecia como "ativo às 01:54" porque o bot mandou mensagem para ele
TG_PASSIVO = 7000000001


def _h(horas: float) -> str:
    """Timestamp relativo a AGORA. Data fixa no fixture apodrece: em uma
    semana tudo cai fora da janela de 7/14/30 dias e o teste quebra sozinho
    (ou pior, passa por vacuidade)."""
    return (datetime.now(timezone.utc)
            - timedelta(hours=horas)).isoformat(timespec="seconds")

_EVENTOS = [
    {"telegram_id": TG, "event": "licao_recebida", "detail": {"licao": 24},
     "created_at": _h(6), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "drill_verdict",
     "detail": {"cat": "river", "hand_id": "h-9", "verdict": "mista"},
     "created_at": _h(9), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "drill_answer",
     "detail": {"choice": "fold", "hand_id": "h-9"},
     "created_at": _h(9.1), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "upload",
     "detail": {"site": "PPPoker · Monster", "hands": 1,
                "quota_remaining": 75},
     "created_at": _h(18), "username": "Ricardo Farah"},
    # o MESMO envio acima também grava o canal por onde chegou. Em produção
    # sempre vem esse par; contar os dois é o bug que mostrava 194 mãos para
    # quem tinha 92. O par tem que estar no fixture, senão o teste não vê.
    {"telegram_id": TG, "event": "replay_pppoker",
     "detail": {"share_key": "abc"},
     "created_at": _h(18.01), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "custo_llm", "detail": {"usd": 0.0428},
     "created_at": _h(18.02), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "followup_resposta",
     "detail": {"q": "Check no river foi certo?",
                "r": "Foi: o range dele chega forte demais ali."},
     "created_at": _h(19), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "followup",
     "detail": {"q": "Check no river foi certo?"},
     "created_at": _h(19.01), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "upload_failed",
     "detail": {"note": "não achei mão no print"},
     "created_at": _h(19.5), "username": "Ricardo Farah"},
    {"telegram_id": TG, "event": "start", "detail": {"ref": "beta"},
     "created_at": _h(24 * 20), "username": "Ricardo Farah"},
    # SÓ recebeu: o bot empurrou a lição, ele nunca fez nada
    {"telegram_id": TG_PASSIVO, "event": "licao_recebida",
     "detail": {"licao": 24}, "created_at": _h(6), "username": "Eder"},
    # cron: telegram_id 0. NÃO pode aparecer como ação de aluno.
    {"telegram_id": 0, "event": "jornadas", "detail": {"total": 13},
     "created_at": _h(5), "username": None},
    {"telegram_id": 0, "event": "deploy", "detail": {"rev": "abc1234"},
     "created_at": _h(5.5), "username": None},
]

_USERS = [{"id": UID, "telegram_id": TG, "username": "Ricardo Farah",
           "plan": "free", "created_at": _h(24 * 20)},
          {"id": "u-2", "telegram_id": TG_PASSIVO, "username": "Eder",
           "plan": "free", "created_at": _h(24 * 2)}]
_HANDS = [{"id": "h-9", "hand_id": "pppoker-9", "site": "PPPoker · Monster",
           "format": "pppoker_replay", "created_at": _h(18),
           "played_at": None, "user_id": UID,
           "canonical": {"hero_cards": ["Kh", "Kd"]}}]
_ANALISES = [{"hand_id": "h-9", "summary": "✅ Você jogou bem — pagou certo",
              "ev_loss": -1.2, "modelo": "claude-opus-4-8",
              "mistakes": ["pagou o turn sem preço"],
              "created_at": _h(17.9)}]

_TABELAS = {"bot_events": _EVENTOS, "users": _USERS, "hands": _HANDS,
            "hand_analysis": _ANALISES, "player_stats": [],
            "usage_events": [], "licoes": []}


class _Q:
    """Imita o encadeamento do cliente Supabase: select().eq().order()...

    O select PROJETA de verdade: pediu 3 colunas, chegam 3 colunas. Sem isso
    o dublê é mais permissivo que o Supabase e o teste passa num bug que a
    produção tem — foi assim que o dossiê em branco escapou. Dublê frouxo dá
    confiança falsa, que é pior que não ter teste.
    """

    def __init__(self, linhas, count_mode=None, cols=None):
        self._l = list(linhas)
        self._count = count_mode
        self._cols = cols          # projeção pendente, aplicada no execute

    def _novo(self, linhas):
        return _Q(linhas, self._count, self._cols)

    def select(self, cols="*", count=None):
        # o PostgREST filtra na linha INTEIRA e só projeta na saída: dá para
        # .eq() numa coluna que você não pediu. Projetar aqui tornaria o
        # dublê mais estrito que o real e inventaria bug que não existe.
        return _Q(self._l, count, None if cols.strip() == "*" else cols)

    def eq(self, col, val):
        return self._novo([r for r in self._l if r.get(col) == val])

    def gte(self, col, val):
        return self._novo([r for r in self._l
                           if str(r.get(col) or "") >= str(val)])

    def in_(self, col, vals):
        return self._novo([r for r in self._l if r.get(col) in vals])

    def order(self, col, desc=False):
        return self._novo(sorted(self._l, key=lambda r: str(r.get(col) or ""),
                                 reverse=desc))

    def limit(self, n):
        return self._novo(self._l[:n])

    def execute(self):
        linhas = self._l
        if self._cols:
            nomes = [c.strip().split(":")[-1] for c in self._cols.split(",")]
            linhas = [{k: r.get(k) for k in nomes} for r in linhas]
        return type("R", (), {"data": linhas, "count": len(linhas)})()


class _Cliente:
    def table(self, nome):
        return _Q(_TABELAS.get(nome, []))


class _Repo:
    enabled = True
    client = _Cliente()

    def get_notes(self, uid, limit=10):
        return [{"kind": "leak", "note": "paga demais no river"}]


@pytest.fixture
def portal(monkeypatch):
    from app.api import admin

    monkeypatch.setenv("ADMIN_TOKEN", "tok")
    get_settings.cache_clear()
    monkeypatch.setattr(admin, "get_repository", lambda: _Repo())
    yield admin
    get_settings.cache_clear()


def _texto(html_str: str) -> str:
    import re

    t = re.sub(r"<style>.*?</style>", " ", html_str, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def test_dossie_mostra_o_que_a_pessoa_fez(portal):
    """O caso exato de 07/08: a página não pode dizer 'nenhuma ação'."""
    pag = asyncio.run(portal.admin_usuario(key="tok", tg=TG, ver=""))
    txt = _texto(pag)

    assert "nenhuma ação registrada" not in txt
    # as ações traduzidas, em português, com o conteúdo real
    assert "Perguntou" in txt and "Check no river foi certo?" in txt
    assert "Análise entregue" in txt
    assert "Respondeu o quiz: fold" in txt
    # e o cron NUNCA vira ação de aluno
    assert "jornadas" not in txt and "deploy" not in txt


def test_dossie_mostra_os_numeros_certos(portal):
    """Cada caixa com o número que os dados dão — 1 upload é 1 envio, não 2
    (o bug do canal contado em dobro), e 1 mão no banco é o banco falando."""
    pag = _texto(asyncio.run(portal.admin_usuario(key="tok", tg=TG, ver="")))
    for n, rotulo in ((1, "mãos no banco"), (1, "envios analisados"),
                      (1, "perguntas ao coach"), (1, "treinos respondidos"),
                      (1, "erros")):
        assert f"{n} {rotulo}" in pag, f"esperava '{n} {rotulo}'"


@pytest.mark.parametrize("ver,esperado", [
    ("perguntas", "Foi: o range dele chega forte demais ali."),
    ("treinos", "mista"),
    ("erros", "não achei mão no print"),
    ("quiz", "lição do dia"),
    ("maos", "PPPoker"),
])
def test_cada_caixa_abre_conteudo_de_verdade(portal, ver, esperado):
    """Clicar na caixa tem que MOSTRAR as linhas — não só existir a rota."""
    pag = _texto(asyncio.run(portal.admin_usuario(key="tok", tg=TG, ver=ver)))
    assert esperado in pag, f"ver={ver} veio sem conteúdo"


def test_pagina_da_mao_mostra_a_analise(portal):
    pag = _texto(asyncio.run(portal.admin_mao(key="tok", id="h-9", tg=TG)))
    assert "Você jogou bem" in pag
    assert "pagou o turn sem preço" in pag      # os erros apontados
    assert "K♥" in pag or "Kh" in pag           # as cartas


def test_home_lista_o_aluno_e_o_que_ele_fez(portal):
    bruto = asyncio.run(portal.admin(key="tok"))
    pag = _texto(bruto)
    assert "Ricardo Farah" in pag
    assert "Perguntou" in pag or "Análise entregue" in pag

    # o cron fica FORA DO FEED — na tabela "eventos por tipo" ele pode (e
    # deve) aparecer, que ali é diagnóstico de máquina, não ação de gente
    feed = _texto(bruto.split("O que acabou de acontecer")[1]
                  .split("<h2>")[0])
    assert "jornadas" not in feed and "deploy" not in feed
    assert "Ricardo Farah" in feed


def test_receber_licao_nao_faz_o_aluno_virar_ativo(portal):
    """O Eder só recebeu a lição — nunca mandou mão, nunca perguntou. Contar
    ele como 'ativo' faz a métrica subir quando o DONO aperta um botão."""
    pag = _texto(asyncio.run(portal.admin(key="tok")))
    assert "2 usuários totais" in pag
    assert "1 ativos (7 dias)" in pag, "o passivo entrou na conta de ativos"


def test_token_errado_nao_renderiza_nada(portal):
    from fastapi import HTTPException

    for chamada in (lambda: portal.admin(key="x"),
                    lambda: portal.admin_usuario(key="x", tg=TG),
                    lambda: portal.admin_mao(key="x", id="h-9")):
        with pytest.raises(HTTPException):
            asyncio.run(chamada())
