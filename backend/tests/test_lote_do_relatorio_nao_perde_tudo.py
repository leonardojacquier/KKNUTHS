"""Os lotes das 150 principais: corte no teto não pode levar o lote inteiro.

Caso real de 18/08 22:25-22:33 UTC, torneio de 192 mãos, medido em
`bot_events`/`custo_llm`:

    16 chamadas seguidas de `per_hand_analysis_llm`,
    TODAS com saída = exatamente 1.800 tokens (o `max_tokens` do lote)

Todo lote cortado no meio do JSON. Como o parse era `json.loads` do bloco
inteiro, JSON truncado lançava e o `except: continue` jogava fora as SEIS
mãos do lote — as 96 mãos desses 16 lotes caíram no
`played_fallback_verdict` e o relatório das "150 principais" saiu quase todo
em texto de reserva. A feature ficou inoperante em torneio grande.

Três camadas, e cada teste abaixo prende uma:

(a) TETO — 1.800 -> 4.000. Seis mãos × ~400 tokens de nota (análise +
    analise_simples + veredito) mais o JSON não cabem em 1.800; token de
    saída só custa quando gerado.
(b) PEDIDO — a instrução manda 2-3 frases POR MÃO com alvo de tamanho.
    Teto sem pedido é convite a ensaio (docs/METODO.md).
(c) SALVAMENTO PARCIAL — cortado, o que fechou é salvo e só o que faltou
    volta, UMA vez, em lote da metade. Segunda falha: fallback + evento
    `analise_cortada` com `onde="lote_do_relatorio"`.

Fixture do corte: resposta truncada no meio do 4º objeto JSON. Os 3
completos sobrevivem; os 3 restantes vão para a re-tentativa.

Tudo determinístico: `_create` é capturado, cliente falso, zero rede e zero
LLM.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  HandFormat, PlayerSeat, Stakes, Street,
                                  StreetName)

# A medição de 18/08, como constantes, para o teste cobrar o DADO.
TETO_ANTIGO_DO_LOTE = 1800      # o teto que cortou os 16 lotes
LOTES_CORTADOS = 16             # todos, com saída = exatamente 1.800
MAOS_POR_LOTE = 6

_BB = 100.0


def _mao(hand_id: str, *, net_bb: float = 5.0) -> CanonicalHand:
    """Mão de torneio sintética — o herói abre e o vilão larga.

    Molde mínimo de propósito: o que este arquivo mede é o encanamento do
    lote (teto, pedido, salvamento parcial), não o conteúdo da análise.
    """
    aposta = 2.5 * _BB
    ganho = (net_bb + 2.5) * _BB
    return CanonicalHand(
        hand_id=hand_id, site="ggpoker", format=HandFormat.TOURNAMENT,
        tournament_id="T1",
        stakes=Stakes(small_blind=_BB / 2, big_blind=_BB),
        hero="Hero", hero_cards=["Ah", "Kd"],
        players=[
            PlayerSeat(seat=1, name="Hero", stack=5000, position="BTN",
                       is_hero=True),
            PlayerSeat(seat=2, name="Vilao", stack=5000, position="BB"),
        ],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="Vilao", type=ActionType.POST, amount=_BB,
                   post_type="bb"),
            Action(actor="Hero", type=ActionType.RAISE, amount=aposta,
                   to_amount=aposta),
            Action(actor="Vilao", type=ActionType.FOLD),
        ])],
        collected={"Hero": ganho},
        played_at="2026-08-18T22:25:00Z",
    )


_OBJ = ('{"analise": "Bem jogada, o preço fechava.", '
        '"analise_simples": "Você pagou barato para ver mais uma carta.", '
        '"veredito": "boa"}')


def _json_inteiro(ids: list[str]) -> str:
    return "{" + ", ".join(f'"{i}": {_OBJ}' for i in ids) + "}"


def _json_cortado(ids: list[str], completos: int = 3) -> str:
    """O que a API devolveu com `stop_reason='max_tokens'`.

    Os `completos` primeiros objetos FECHAM; o seguinte para no meio da
    string de `analise` — que é onde um corte por token cai de verdade.
    """
    fechados = ", ".join(f'"{i}": {_OBJ}' for i in ids[:completos])
    return ("{" + fechados + f', "{ids[completos]}": '
            '{"analise": "Aqui você pagou car')


def _resposta(texto: str, stop: str = "end_turn"):
    return SimpleNamespace(
        stop_reason=stop,
        content=[SimpleNamespace(type="text", text=texto)])


class _Repo:
    enabled = True

    def __init__(self):
        self.eventos: list[tuple[str, dict]] = []

    def log_event(self, tid, user, event, detail):
        self.eventos.append((event, detail))


@pytest.fixture
def repo(monkeypatch):
    r = _Repo()
    monkeypatch.setattr("app.db.get_repository", lambda: r)
    return r


@pytest.fixture
def lote(monkeypatch):
    """`per_hand_analysis_llm` com chave de API falsa e cliente inerte."""
    import anthropic

    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type("S", (), {"anthropic_api_key": "sk-teste",
                               "analysis_model": "m"})())
    monkeypatch.setattr(anthropic, "Anthropic",
                        lambda **k: SimpleNamespace(nome="cliente-falso"))
    from app.analysis import handreport

    return handreport


def _create_que_anota(pedidos: list[dict], respostas: list):
    """Captura o kwargs de CADA chamada e devolve as respostas na ordem."""
    fila = iter(respostas)

    def _create(client, **kw):
        pedidos.append(kw)
        return next(fila)

    return _create


def _prompt(kw: dict) -> str:
    return kw["messages"][0]["content"]


def test_o_teto_do_lote_sobe_do_que_foi_medido(lote, monkeypatch, repo):
    """Os 16 lotes de 18/08 saíram com saída = EXATAMENTE 1.800: o teto era o
    censor. Seis mãos com análise, versão simples e veredito não cabem ali."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    pedidos: list[dict] = []
    monkeypatch.setattr(
        "app.agent.llm._create",
        _create_que_anota(pedidos, [_resposta(
            _json_inteiro([h.hand_id for h in maos]))]))

    lote.per_hand_analysis_llm(maos)

    assert pedidos, "o lote nem chamou o modelo"
    assert pedidos[0]["max_tokens"] > TETO_ANTIGO_DO_LOTE, \
        f"o lote continua no teto que cortou {LOTES_CORTADOS} lotes seguidos"
    assert pedidos[0]["max_tokens"] >= 4000


def test_o_pedido_do_lote_cobra_tamanho_por_mao(lote, monkeypatch, repo):
    """Teto maior sem pedido é ensaio de 4.000 tokens. O lote pede 2-3 frases
    POR MÃO, com alvo de tamanho — a nota do card do relatório é curta."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    pedidos: list[dict] = []
    monkeypatch.setattr(
        "app.agent.llm._create",
        _create_que_anota(pedidos, [_resposta(
            _json_inteiro([h.hand_id for h in maos]))]))

    lote.per_hand_analysis_llm(maos)

    texto = _prompt(pedidos[0])
    assert "2-3 frases" in texto, "o lote parou de pedir 2-3 frases por mão"
    assert "TAMANHO" in texto, "o pedido do lote não fala de tamanho"


def test_lote_cortado_salva_as_maos_cujo_json_fechou(lote, monkeypatch, repo):
    """O defeito de 18/08: `json.loads` do bloco truncado lançava e o
    `except: continue` levava as SEIS mãos. Agora o que fechou fica."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    ids = [h.hand_id for h in maos]
    pedidos: list[dict] = []
    monkeypatch.setattr(
        "app.agent.llm._create",
        _create_que_anota(pedidos, [
            _resposta(_json_cortado(ids), stop="max_tokens"),
            _resposta(_json_inteiro(ids[3:])),
        ]))

    out = lote.per_hand_analysis_llm(maos)

    assert {"H0", "H1", "H2"} <= set(out), \
        "as mãos cujo JSON veio completo foram jogadas fora com o lote"
    assert out["H0"]["veredito"] == "boa"


def test_as_maos_que_faltaram_voltam_num_lote_da_metade(lote, monkeypatch,
                                                        repo):
    """A re-tentativa é só das que faltaram, e em lote menor — mandar as seis
    de novo repetiria o corte com o mesmo tamanho de resposta."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    ids = [h.hand_id for h in maos]
    pedidos: list[dict] = []
    monkeypatch.setattr(
        "app.agent.llm._create",
        _create_que_anota(pedidos, [
            _resposta(_json_cortado(ids), stop="max_tokens"),
            _resposta(_json_inteiro(ids[3:])),
        ]))

    out = lote.per_hand_analysis_llm(maos)

    assert len(pedidos) == 2, "a re-tentativa não saiu"
    segundo = _prompt(pedidos[1])
    for perdida in ("H3", "H4", "H5"):
        assert f'"hand_id": "{perdida}"' in segundo
    for salva in ("H0", "H1", "H2"):
        assert f'"hand_id": "{salva}"' not in segundo, \
            "a re-tentativa está re-analisando (e re-pagando) o que já veio"
    assert set(out) == set(ids), "a re-tentativa não recuperou as que faltaram"


def test_a_re_tentativa_e_uma_so_e_o_resto_cai_no_fallback(lote, monkeypatch,
                                                            repo):
    """Segunda falha encerra: essas mãos ficam no veredito determinístico e o
    corte vira evento — sem terceira chamada, sem laço infinito."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    ids = [h.hand_id for h in maos]
    pedidos: list[dict] = []
    monkeypatch.setattr(
        "app.agent.llm._create",
        _create_que_anota(pedidos, [
            _resposta(_json_cortado(ids), stop="max_tokens"),
            _resposta('{"H3": {"analise": "Aqui você pagou car',
                      stop="max_tokens"),
        ]))

    out = lote.per_hand_analysis_llm(maos)

    assert len(pedidos) == 2, "houve uma terceira tentativa"
    assert set(out) == {"H0", "H1", "H2"}
    assert not ({"H3", "H4", "H5"} & set(out)), \
        "mão sem JSON completo não pode entrar no relatório"


def test_o_corte_do_lote_vira_evento_com_lugar_proprio(lote, monkeypatch,
                                                        repo):
    """Sem evento, um relatório inteiro em texto de reserva é invisível — foi
    exatamente o que aconteceu nos 16 lotes de 18/08."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    ids = [h.hand_id for h in maos]
    monkeypatch.setattr(
        "app.agent.llm._create",
        _create_que_anota([], [
            _resposta(_json_cortado(ids), stop="max_tokens"),
            _resposta('{"H3": {"analise": "Aqui você pagou car',
                      stop="max_tokens"),
        ]))

    lote.per_hand_analysis_llm(maos)

    cortes = [d for e, d in repo.eventos if e == "analise_cortada"]
    assert cortes, "o corte do lote não é contável"
    assert all(d["onde"] == "lote_do_relatorio" for d in cortes)
    assert all(d["stop_reason"] == "max_tokens" for d in cortes)
    perdidas = [d for d in cortes if d.get("tentativa") == 2]
    assert perdidas, "a segunda falha (a que joga no fallback) não foi anotada"


def test_o_lote_inteiro_nao_paga_pedagio_nenhum(lote, monkeypatch, repo):
    """Caminho bom: JSON completo, uma chamada só, nenhuma re-tentativa e
    nenhum evento. O conserto não pode encarecer o que já funcionava."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    ids = [h.hand_id for h in maos]
    pedidos: list[dict] = []
    monkeypatch.setattr(
        "app.agent.llm._create",
        _create_que_anota(pedidos, [_resposta(_json_inteiro(ids))]))

    out = lote.per_hand_analysis_llm(maos)

    assert len(pedidos) == 1
    assert set(out) == set(ids)
    assert repo.eventos == []


def test_falha_de_rede_no_lote_nao_vira_re_tentativa(lote, monkeypatch, repo):
    """`stop_reason='max_tokens'` é o gatilho — e só ele. Erro de rede já
    tinha o seu caminho (as mãos caem no fallback) e não ganha rodada extra:
    re-tentar rede aqui duplicaria o retry que `_create` já faz sozinho."""
    maos = [_mao(f"H{i}") for i in range(MAOS_POR_LOTE)]
    chamadas: list[int] = []

    def _explode(client, **kw):
        chamadas.append(1)
        raise RuntimeError("overloaded")

    monkeypatch.setattr("app.agent.llm._create", _explode)

    assert lote.per_hand_analysis_llm(maos) == {}
    assert len(chamadas) == 1
