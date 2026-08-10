"""O elo que faltava: a foto do lobby chega, é guardada, e o /preparar usa.

Sem isto, o `lobby.py` e o extrator de visão são dois módulos que ninguém
chama — a forma mais comum de trabalho que parece pronto e não existe.

Três coisas prendem aqui:

  1. foto do lobby NÃO pode cair no leitor de mão. A tela de estrutura não
     tem carta nem stack; o aluno receberia "não consegui ler" e teria
     gastado uma análise da cota para ouvir nada;
  2. a estrutura tem que ser GUARDADA, senão ele fotografa antes de todo
     torneio — o mesmo que não guardar;
  3. o /preparar tem que PREFERIR o lobby à medida do histórico: o lobby
     descreve o torneio que vai começar, a medida descreve o que já passou.
"""
from __future__ import annotations

import pytest

import app.bot.handlers as H
import app.bot.processing as P
from app.analysis.lobby import Lobby, Nivel
from app.models.canonical import CanonicalHand, Stakes

ESCADA = ((1, 25, 50, 0), (2, 50, 100, 0), (3, 100, 200, 25),
          (4, 200, 400, 50), (5, 300, 600, 75), (6, 400, 800, 100),
          (7, 500, 1000, 100), (8, 700, 1400, 200), (9, 1000, 2000, 300),
          (10, 1500, 3000, 400), (11, 2000, 4000, 500), (12, 3000, 6000, 800))

LOBBY = Lobby(niveis=tuple(Nivel(*n) for n in ESCADA),
              nome="MonsterStackHyperTur", buyin=85.0, taxa=15.0,
              fichas_iniciais=100_000, minutos_por_nivel=15,
              late_reg_nivel=5, pausa_min=5, pausa_cada_min=55,
              rebuy="3 Vezes/1×", addon="Não")


class _Repo:
    enabled = True

    def __init__(self):
        self.meta: dict = {}
        self.eventos: list = []

    def get_or_create_user(self, *a, **k):
        return {"id": "u-1"}

    def set_user_meta(self, user_id, key, value):
        self.meta[key] = value

    def get_user_meta(self, user_id, key):
        return self.meta.get(key)

    def get_hands_para_perfil(self, *a, **k):
        return [], 0

    def get_notes(self, *a, **k):
        return []

    def log_event(self, tg, user, evento, detail=None):
        self.eventos.append((evento, detail))

    def __getattr__(self, _n):
        return lambda *a, **k: None


# ---- 1) a foto do lobby não vai para o leitor de mão ------------------------

@pytest.mark.parametrize("legenda,esperado", [
    ("estrutura do torneio", True), ("/preparar", True),
    ("Estrut. de blinds", True), ("lobby", True), ("níveis", True),
    ("olha essa mão que absurdo", False), ("", False), (None, False),
])
def test_a_legenda_separa_a_tela_do_lobby_da_tela_da_mesa(legenda, esperado):
    """Distinguir as duas telas sem LER a imagem é impossível, e ler duas
    vezes custa duas análises da cota. Por isso a legenda decide."""
    assert H._pede_leitura_de_lobby(legenda) is esperado


def test_o_desvio_do_lobby_acontece_ANTES_do_leitor_de_mao():
    """A ordem no `on_photo` é o que importa: replay, depois lobby, depois
    mão. Invertida, a foto da estrutura vira análise de mão."""
    import inspect

    fonte = inspect.getsource(H.on_photo)
    assert fonte.index("_pede_leitura_de_lobby") < fonte.index("process_upload")


# ---- 2) a estrutura é lida, conferida e guardada ----------------------------

@pytest.fixture
def lobby_lido(monkeypatch):
    repo = _Repo()
    monkeypatch.setattr(P, "get_repository", lambda: repo)

    import app.agent.llm as llm

    monkeypatch.setattr(llm, "extract_lobby_from_image",
                        lambda *a, **k: LOBBY)
    monkeypatch.setattr(llm, "LAST_LOBBY_CHECK",
                        {"divergencias": [], "conferido": True})
    return repo


def test_a_estrutura_lida_e_guardada_para_o_proximo_torneio(lobby_lido):
    texto = P.processar_lobby(b"png", "image/jpeg", 7, "tester")

    assert P.CHAVE_ATUAL in lobby_lido.meta, (
        "leu e não guardou — o aluno teria que fotografar antes de cada "
        "torneio")
    assert "lobby:monsterstackhypertur" in lobby_lido.meta, (
        "sem a chave nomeada não há acervo de estruturas")
    guardado = lobby_lido.meta[P.CHAVE_ATUAL]
    assert guardado["fichas_iniciais"] == 100_000
    assert len(guardado["niveis"]) == len(ESCADA)

    assert "push/fold no nível 12" in texto
    assert "2000 bb" in texto
    assert "/preparar" in texto, "não ensinou o próximo passo"
    assert any(e == "lobby_lido" for e, _ in lobby_lido.eventos)


def test_duvida_da_leitura_vai_PARA_O_ALUNO(lobby_lido, monkeypatch):
    """Divergência entre as duas passadas não pode morrer no log: quem sabe
    se o nível 12 é 3.000/6.000 é ele, olhando a tela."""
    import app.agent.llm as llm

    monkeypatch.setattr(llm, "LAST_LOBBY_CHECK", {
        "divergencias": ["AMBÍGUO: nível 12 cortado na tela"],
        "conferido": False})
    texto = P.processar_lobby(b"png", "image/jpeg", 7, "tester")
    assert "Li com dúvida" in texto and "nível 12" in texto
    assert "me corrige" in texto


def test_print_ilegivel_explica_qual_tela_mandar(lobby_lido, monkeypatch):
    import app.agent.llm as llm

    monkeypatch.setattr(llm, "extract_lobby_from_image", lambda *a, **k: None)
    texto = P.processar_lobby(b"png", "image/jpeg", 7, "tester")
    assert "Informações do jogo" in texto
    assert P.CHAVE_ATUAL not in lobby_lido.meta, "guardou um nada"


def test_banco_fora_do_ar_nao_derruba_a_leitura(lobby_lido, monkeypatch):
    """O aluno recebe a estrutura mesmo sem conseguir guardar."""
    def _explode(*a, **k):
        raise RuntimeError("supabase fora")

    monkeypatch.setattr(lobby_lido, "set_user_meta", _explode)
    assert "push/fold" in P.processar_lobby(b"png", "image/jpeg", 7, "tester")


# ---- 3) o /preparar prefere o lobby ao histórico ----------------------------

@pytest.fixture
def preparar(monkeypatch):
    repo = _Repo()
    monkeypatch.setattr(P, "get_repository", lambda: repo)
    uma_mao = CanonicalHand(hand_id="h1", site="PPPoker · MonsterStack",
                            stakes=Stakes(big_blind=800.0), players=[],
                            streets=[])
    monkeypatch.setattr(P, "RECENT_HANDS", {7: [uma_mao]})

    class _Stats:
        hands, vpip, pfr, three_bet, af, label = 30, 24.0, 18.0, 6.0, 2.1, "TAG"
        detail = {"three_bet_opps": 12}

    monkeypatch.setattr(P, "compute_player_stats", lambda *a, **k: _Stats())

    import app.agent.llm as llm

    visto: dict = {}
    monkeypatch.setattr(llm, "prepare_briefing",
                        lambda ctx: visto.update(ctx) or "BRIEFING")
    return repo, visto


def test_o_preparar_usa_a_estrutura_fotografada(preparar):
    repo, visto = preparar
    repo.meta[P.CHAVE_ATUAL] = {
        k: (list(v) if isinstance(v, tuple) else v)
        for k, v in LOBBY._asdict().items()}

    saida = P.prepare_report(7, "tester", "")

    assert visto.get("estrutura_do_lobby"), "a estrutura guardada não chegou"
    assert visto["estrutura_do_lobby"]["push_fold_nivel"] == 12
    assert "MonsterStackHyperTur" in saida
    assert "push/fold no nível 12" in saida
    assert visto["dicas_do_formato"], (
        "sem digitar formato nenhum, as dicas ficaram vazias")


def test_sem_foto_guardada_o_preparar_segue_como_antes(preparar):
    _repo, visto = preparar
    saida = P.prepare_report(7, "tester", "")
    assert saida == "BRIEFING"
    assert "estrutura_do_lobby" not in visto


def test_estrutura_guardada_ilegivel_nao_derruba_o_comando(preparar):
    """Formato antigo no banco depois de um deploy é o caso comum. Cair aqui
    tiraria o /preparar do ar inteiro."""
    repo, visto = preparar
    repo.meta[P.CHAVE_ATUAL] = {"niveis": "isto não é uma lista de níveis"}
    assert P.prepare_report(7, "tester", "") == "BRIEFING"
    assert "estrutura_do_lobby" not in visto
