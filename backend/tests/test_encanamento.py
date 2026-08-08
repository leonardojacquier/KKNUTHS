"""O encanamento: memória, tráfego e porta.

1. MEMÓRIA SEM TETO. Onze mapas por telegram_id viviam no processo e nenhum
   tinha despejo — os `pop` que existiam eram de CONSUMO. Medido nesta base
   com a amostra real do PokerStars: 1 CanonicalHand ~32 KB, cap de 300 mãos
   por usuário, 100 usuários ~939 MB só de RECENT_HANDS. O bot roda em pm2:
   ele não fica lento, ele morre e reinicia perdendo o contexto de TODO
   MUNDO ao mesmo tempo.

2. HISTÓRICO INTEIRO A CADA ENVIO. `get_all_hands` baixava e validava até
   5000 mãos (14.8 MB, 2.3 s de pydantic, medido) para o perfil descartar a
   maioria logo em seguida — replay e print não medem frequência.

3. O TOKEN NA URL DE TODA PÁGINA. Cada link interno reinjetava
   `?key=<ADMIN_TOKEN>`: histórico do navegador, log de acesso e qualquer
   print da barra de endereço.
"""
from __future__ import annotations

import pytest

from app.bot.memoria_do_processo import (esquecer, guardar_com_prazo, lembrar,
                                         varrer_expirados)


# ---- 1) a memória tem teto -------------------------------------------------

def test_o_mapa_para_de_crescer():
    mapa: dict[int, str] = {}
    for tg in range(1, 501):
        lembrar(mapa, tg, f"v{tg}", teto=200)
    assert len(mapa) == 200
    assert 500 in mapa and 1 not in mapa, "despejou o novo em vez do parado"


def test_quem_volta_a_usar_nao_e_despejado():
    """LRU por escrita: reinserir joga a chave para o fim. Sem isso, quem
    treina toda noite sairia por causa de quem mandou um arquivo e sumiu."""
    mapa: dict[int, str] = {}
    for tg in range(1, 11):
        lembrar(mapa, tg, "x", teto=10)
    lembrar(mapa, 1, "de novo", teto=10)      # o mais velho volta a agir
    lembrar(mapa, 99, "novo", teto=10)        # e chega mais um
    assert 1 in mapa, "o usuário ativo foi despejado"
    assert 2 not in mapa, "o parado deveria ter saído no lugar dele"


def test_entrada_zerada_sai_do_mapa():
    mapa = {7: 0}
    esquecer(mapa, 7)
    assert mapa == {}


def test_o_que_venceu_e_varrido_mesmo_sem_ninguem_consumir():
    """Gráfico e documento tinham TTL — conferido só na hora do `pop`. O que
    nunca foi consumido (resposta falhou, aluno sumiu) nunca era olhado de
    novo, e PNG e HTML de relatório são o conteúdo mais pesado do processo."""
    mapa = {1: (100.0, b"png antigo"), 2: (900.0, b"png novo")}
    saiu = varrer_expirados(mapa, ttl=300.0, agora=1000.0)
    assert saiu == 1 and 1 not in mapa and 2 in mapa


def test_formato_estranho_nao_fica_de_lembranca():
    mapa = {1: "sem timestamp"}
    varrer_expirados(mapa, ttl=300.0, agora=1000.0)
    assert mapa == {}


def test_guardar_com_prazo_varre_e_respeita_o_teto():
    mapa = {1: (0.0, "vencido")}
    guardar_com_prazo(mapa, 2, (1000.0, "novo"), ttl=300.0, teto=5)
    assert 1 not in mapa and mapa[2][1] == "novo"


def test_mandar_mao_nao_enche_a_memoria_para_sempre():
    """O caminho de verdade: 500 usuários mandando mãos."""
    import app.bot.processing as p
    from app.bot.memoria_do_processo import TETO_USUARIOS

    p.RECENT_HANDS.clear()
    from pathlib import Path

    from app.parsers import parse_text

    maos = parse_text(
        (Path(__file__).parent / "sample_hands"
         / "pokerstars_tournament.txt").read_text())
    for tg in range(1, 501):
        p.remember_hands(tg, maos)
    assert len(p.RECENT_HANDS) == TETO_USUARIOS
    p.RECENT_HANDS.clear()


def test_despejar_nao_perde_dado_so_latencia():
    """Despejo só é seguro porque nada disso é a fonte da verdade: sem
    memória, `_user_hands` cai para o banco."""
    import inspect

    import app.bot.processing as p

    fonte = inspect.getsource(p._user_hands)
    assert "get_all_hands" in fonte


# ---- 2) o perfil não baixa o que vai jogar fora ----------------------------

class _Res:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count if count is not None else len(data)


class _Tabela:
    def __init__(self, linhas, registro):
        self._l = list(linhas)
        self._reg = registro
        self._count = False

    def select(self, cols="*", count=None):
        self._count = count == "exact"
        return self

    def eq(self, *a):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a):
        return self

    def in_(self, coluna, valores):
        self._reg.append((coluna, sorted(valores)))
        chave = coluna.split(">>")[-1]
        self._l = [r for r in self._l
                   if (r.get("canonical") or {}).get(chave) in valores]
        return self

    def execute(self):
        return _Res(self._l, len(self._l))


def _repo_falso(linhas, registro, explode=False):
    from app.db.repository import Repository

    class _Cliente:
        def table(self, nome):
            if explode:
                raise RuntimeError("PostgREST não entendeu o filtro")
            return _Tabela(linhas, registro)

    repo = Repository.__new__(Repository)
    repo.enabled = True
    repo._url = repo._key = "x"
    repo._client = _Cliente()
    return repo


def _linha(fonte):
    return {"canonical": {"hand_id": f"h-{fonte}", "site": "X",
                          "hero": "Hero", "source_format": fonte,
                          "players": [], "streets": []}}


def test_o_filtro_de_fonte_vai_para_o_banco():
    """O que não conta para o perfil nem desce."""
    registro: list = []
    linhas = [_linha("txt")] * 3 + [_linha("pppoker_replay")] * 7
    repo = _repo_falso(linhas, registro)
    maos, fora = repo.get_hands_para_perfil("u-1")

    assert len(maos) == 3, "desceu replay que o perfil descarta"
    assert fora == 7, "perdeu a conta do que ficou de fora"
    coluna, valores = registro[0]
    assert coluna == "canonical->>source_format"
    assert "txt" in valores and "pppoker_replay" not in valores


def test_se_o_filtro_falhar_cai_no_caminho_de_sempre():
    """Número que encolhe calado é o defeito que este projeto mais combate:
    filtro quebrado não pode virar 'esse aluno não tem mão'."""
    repo = _repo_falso([], [], explode=True)
    chamou = {}

    def _todas(uid, limite):
        chamou["sim"] = True
        return ["mao"]

    repo.get_all_hands = _todas
    maos, fora = repo.get_hands_para_perfil("u-1")
    assert chamou.get("sim") and maos == ["mao"] and fora == 0


def test_quem_so_manda_replay_continua_avisado():
    """`amostra_viesada` só existe porque alguém CONTOU o que foi descartado.
    Filtrando no banco sem devolver a conta, o aluno passaria de 'só mãos
    avulsas, que não medem frequência' para 'amostra insuficiente' — que é
    outra coisa, e a errada."""
    from app.analysis import compute_player_stats

    s = compute_player_stats([], player=None, fora_da_amostra=53)
    assert s.detail.get("amostra_viesada") is True
    assert "não medem frequência" in s.label
    assert s.publicavel is False


def test_sem_descarte_nada_muda():
    from app.analysis import compute_player_stats

    s = compute_player_stats([], player=None)
    assert s.detail.get("amostra_viesada") is None


# ---- 3) o token sai da URL -------------------------------------------------

@pytest.fixture
def cliente(monkeypatch):
    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.config import get_settings

    monkeypatch.setenv("ADMIN_TOKEN", "tok-de-teste")
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()


def test_a_chave_vira_cookie_e_some_da_url(cliente):
    r = cliente.get("/admin?key=tok-de-teste", follow_redirects=False)
    assert r.status_code == 303
    assert "key=" not in r.headers["location"]
    cookie = r.headers.get("set-cookie", "")
    assert "kkn_admin=" in cookie and "HttpOnly" in cookie


def test_depois_do_cookie_a_url_limpa_abre(cliente):
    cliente.get("/admin?key=tok-de-teste")          # segue o redirect
    r = cliente.get("/admin")                        # sem segredo nenhum
    assert r.status_code == 200 and "Gestão" in r.text


def test_sem_cookie_e_sem_chave_ninguem_entra(cliente):
    from fastapi.testclient import TestClient

    from app.api.main import app

    virgem = TestClient(app)
    for url in ("/admin", "/admin?key=errado",
                "/admin/usuario?tg=1", "/admin/mao?id=abc"):
        assert virgem.get(url).status_code == 401, url


def test_cookie_errado_nao_abre(cliente):
    r = cliente.get("/admin", cookies={"kkn_admin": "chute"})
    assert r.status_code == 401


def test_nenhum_link_da_pagina_carrega_o_segredo(cliente):
    import re

    pag = cliente.get("/admin?key=tok-de-teste").text
    vazando = [h for h in re.findall(r'href=[\'"]([^\'"]+)', pag)
               if "key=" in h]
    assert not vazando, f"links ainda levam o token: {vazando[:3]}"


def test_sem_admin_token_o_portal_fica_fechado(monkeypatch):
    """Comparação em tempo constante e fail-closed: token vazio não pode
    casar com `?key=` vazio."""
    from app.api.admin import token_confere
    from app.config import get_settings

    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    get_settings.cache_clear()
    assert token_confere("") is False
    assert token_confere(None) is False
    get_settings.cache_clear()


# ---- 4) RLS ----------------------------------------------------------------

def test_toda_tabela_do_schema_liga_rls():
    """`licoes` e `glossario` nasceram FORA do schema.sql (criadas direto no
    banco) e por isso escaparam do bloco de RLS — eram as duas únicas de
    `public` sem row level security, com grant de INSERT/UPDATE/DELETE para
    `anon`. Escrever ali não é ler dado de aluno: é escrever na boca do
    coach, porque lição fala com todos e termo aprovado vira troca
    determinística no texto entregue."""
    import re
    from pathlib import Path

    sql = (Path(__file__).parent.parent / "app" / "db" / "schema.sql").read_text()
    criadas = set(re.findall(r"create table if not exists\s+(?:public\.)?(\w+)",
                             sql, re.I))
    protegidas = set(re.findall(
        r"alter table\s+(?:public\.)?(\w+)\s+enable row level security",
        sql, re.I))
    faltando = criadas - protegidas
    assert not faltando, f"tabela sem RLS no schema: {sorted(faltando)}"
