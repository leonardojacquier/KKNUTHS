"""A cola entre contar, decidir e medir — e o que só ela pode garantir.

`taxonomia` sabe contar, `problemas` sabe decidir, `evolucao` sabe medir.
Nenhum dos três conhece o banco nem o aluno, e sem alguém que os ligue os
três são bibliotecas que ninguém chama.

Quatro garantias que só existem nesta camada:
  1. portão de amostra ANTES de tudo
  2. um problema ativo — se já existe, revisa em vez de abrir outro
  3. o pré-requisito na frente do sintoma
  4. o critério de alta gravado NA ABERTURA, não depois
"""
from __future__ import annotations

import pytest

from app.analysis.plano_de_estudo import revisar
from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  HandFormat, PlayerSeat, Stakes, Street,
                                  StreetName)


def _limp(hid, dia, fonte="txt", pos="CO"):
    bb = 100.0
    return CanonicalHand(
        site="GG", hand_id=hid, hero="Hero", format=HandFormat.TOURNAMENT,
        source_format=fonte, played_at=f"{dia}T20:00:00+00:00",
        stakes=Stakes(small_blind=bb / 2, big_blind=bb, ante=25),
        players=[PlayerSeat(seat=1, name="Hero", stack=30 * bb, position=pos,
                            is_hero=True),
                 PlayerSeat(seat=2, name="V", stack=30 * bb, position="BTN"),
                 PlayerSeat(seat=3, name="O", stack=30 * bb, position="SB")],
        hero_cards=["7h", "2d"],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="O", type=ActionType.POST, amount=50, post_type="sb"),
            Action(actor="V", type=ActionType.POST, amount=100, post_type="bb"),
            Action(actor="Hero", type=ActionType.CALL, amount=100,
                   to_amount=100)])])


def _muitos_limps():
    """30 limps em 3 sessões distintas cobrindo 12 dias — passa recorrência,
    amostra e frequência (a referência do limp é ZERO)."""
    dias = ["2026-07-20", "2026-07-26", "2026-08-01"]
    return [_limp(f"h{i}", dias[i % 3]) for i in range(30)]


class _Repo:
    enabled = True

    def __init__(self, abertos=None, resolvidos=()):
        self.linhas = list(abertos or [])
        self.resolvidos = list(resolvidos)
        self.gravou = []

    def problemas_do_aluno(self, uid, estados=None):
        todos = self.linhas + [{"id": f"r-{c}", "codigo": c,
                                "estado": "resolvido"}
                               for c in self.resolvidos]
        return [p for p in todos if not estados or p["estado"] in estados]

    def abrir_problema(self, uid, codigo, estado, por_que, alta=None,
                       diagnostico_ate=None):
        linha = {"id": f"p{len(self.linhas)}", "codigo": codigo,
                 "estado": estado, "por_que": por_que,
                 "alta_limiar": (alta or {}).get("limiar"),
                 "alta_n_minimo": (alta or {}).get("n_minimo"),
                 "alta_por_extenso": (alta or {}).get("por_extenso"),
                 "diagnostico_ate": diagnostico_ate}
        self.gravou.append(linha)
        self.linhas.append(linha)
        return linha


# ---- 1) o portão de amostra vem antes de tudo -----------------------------

def test_replay_avulso_nem_entra_na_varredura():
    """Uma mão escolhida a dedo no meio já envenena o denominador — e o
    denominador é a coisa toda."""
    r = _Repo()
    out = revisar(r, "u-1", [_limp(f"h{i}", "2026-08-01", fonte="pppoker_replay")
                             for i in range(30)])
    assert out["diagnosticos"] == []
    assert out["por_que"] == "sem mãos de sessão inteira"
    assert r.gravou == [], "abriu problema sobre amostra curada"


def test_so_a_parte_completa_da_amostra_e_contada():
    r = _Repo()
    mistura = _muitos_limps() + [
        _limp(f"x{i}", "2026-08-01", fonte="image") for i in range(20)]
    out = revisar(r, "u-1", mistura)
    assert out["maos_completas"] == 30


# ---- 2) um problema ativo --------------------------------------------------

def test_padrao_recorrente_e_caro_abre_problema():
    r = _Repo()
    out = revisar(r, "u-1", _muitos_limps())
    assert r.gravou, "30 limps em 3 sessões tinham que abrir"
    assert r.gravou[0]["codigo"] == "limp_de_abertura"
    assert out["ativo"]["codigo"] == "limp_de_abertura"


def test_rodar_de_novo_nao_abre_outro():
    """Idempotente por desenho: cada envio de mãos chama isto, e um problema
    novo por envio faria três ativos numa noite."""
    r = _Repo()
    revisar(r, "u-1", _muitos_limps())
    revisar(r, "u-1", _muitos_limps())
    revisar(r, "u-1", _muitos_limps())
    assert len(r.gravou) == 1


def test_com_um_ativo_o_texto_fala_dele_e_nao_do_proximo():
    r = _Repo(abertos=[{"id": "p9", "codigo": "call_caro", "estado": "problema",
                        "alta_n_minimo": 30, "alta_por_extenso": "x"}])
    out = revisar(r, "u-1", _muitos_limps())
    assert out["ativo"]["codigo"] == "call_caro"
    assert r.gravou == []


# ---- 3) o critério de alta é gravado NA ABERTURA --------------------------

def test_o_criterio_vai_na_mesma_gravacao():
    """Gravar depois abriria a porta para escrever a régua já sabendo o
    resultado — que é exatamente o viés que o pré-registro impede."""
    r = _Repo()
    revisar(r, "u-1", _muitos_limps())
    linha = r.gravou[0]
    assert linha["alta_limiar"] is not None
    assert linha["alta_n_minimo"] == 30
    assert "considero resolvido quando" in linha["alta_por_extenso"]
    assert linha["diagnostico_ate"], "sem a data do diagnóstico não dá para " \
        "recusar essa janela como linha de base depois"


# ---- 4) o pré-requisito na frente do sintoma ------------------------------

def test_o_que_depende_de_prerequisito_espera_na_fila():
    """Não adianta abrir 'defesa de BB' para quem não calcula preço de pote:
    metade daquelas mãos ele erra pelo motivo errado."""
    from app.analysis.problemas import bloqueado_por

    assert bloqueado_por("bb_subdefesa", set()) == "pot_odds"
    r = _Repo()
    out = revisar(r, "u-1", _muitos_limps())
    # limp não tem pré-requisito, então é ele que abre
    assert out["ativo"]["codigo"] == "limp_de_abertura"


# ---- o que o aluno lê ------------------------------------------------------

def test_o_texto_sai_pronto_e_com_a_pergunta():
    r = _Repo()
    out = revisar(r, "u-1", _muitos_limps())
    assert "vale entrar" in out["texto"] or "vale abrir" in out["texto"]
    assert "Coleta:" in out["texto"]


def test_a_coleta_comeca_em_zero_e_nao_nas_maos_que_diagnosticaram():
    """No instante em que o problema abre, ZERO mãos novas foram coletadas.
    Contar as 30 do diagnóstico diria "30 de 30" — "você já chegou" antes de
    coletar uma única mão nova. É a mesma confusão entre a janela que
    DIAGNOSTICA e a que MEDE que faz a regressão à média virar melhora
    falsa."""
    r = _Repo()
    out = revisar(r, "u-1", _muitos_limps())
    assert out["ativo"]["oportunidades"] == 0
    assert out["ativo"]["diagnosticado_com"] == 30
    assert "0 de ~30" in out["texto"]


def test_maos_novas_depois_do_diagnostico_enchem_a_barra():
    aberto = [{"id": "p0", "codigo": "limp_de_abertura", "estado": "problema",
               "diagnostico_ate": "2026-08-01", "alta_n_minimo": 30,
               "alta_por_extenso": "x"}]
    r = _Repo(abertos=aberto)
    novas = [_limp(f"n{i}", "2026-08-10") for i in range(9)]
    out = revisar(r, "u-1", _muitos_limps() + novas)
    assert out["ativo"]["oportunidades"] == 9, \
        "só as mãos POSTERIORES ao diagnóstico contam"


def test_o_que_esta_de_pe_aparece():
    """Sem detector de acerto a ferramenta é um crítico, e crítico se
    abandona."""
    r = _Repo()
    out = revisar(r, "u-1", _muitos_limps())
    assert out["acertos"], "nenhum acerto listado num aluno com 30 mãos"


def test_sem_padrao_o_silencio_e_explicado():
    """'Não achei problema' e 'não tenho dados' são coisas diferentes, e o
    aluno merece saber qual das duas é."""
    r = _Repo()
    boas = [
        CanonicalHand(
            site="GG", hand_id=f"b{i}", hero="Hero",
            format=HandFormat.TOURNAMENT, source_format="txt",
            played_at="2026-08-01T20:00:00+00:00",
            stakes=Stakes(small_blind=50, big_blind=100, ante=25),
            players=[PlayerSeat(seat=1, name="Hero", stack=3000,
                                position="CO", is_hero=True),
                     PlayerSeat(seat=2, name="V", stack=3000, position="BTN")],
            hero_cards=["Ah", "Kd"],
            streets=[Street(name=StreetName.PREFLOP, actions=[
                Action(actor="V", type=ActionType.POST, amount=100,
                       post_type="bb"),
                Action(actor="Hero", type=ActionType.RAISE, amount=250,
                       to_amount=250)])]) for i in range(30)]
    out = revisar(r, "u-1", boas)
    assert out["texto"] == "" and r.gravou == []


# ---- o comando existe e chega ao aluno ------------------------------------

def test_o_comando_foco_existe_e_esta_registrado():
    """Módulo que ninguém chama não existe — e esta camada inteira só vale
    se o aluno puder abrir."""
    import inspect

    from app.bot import handlers, processing

    assert hasattr(processing, "foco_reply")
    fonte = inspect.getsource(handlers)
    assert 'CommandHandler("foco", cmd_foco)' in fonte
    assert 'BotCommand("foco"' in fonte


def test_o_foco_separa_sem_dado_de_sem_problema():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing.foco_reply)
    assert "sessão inteira" in fonte
    assert "não achei padrão" in fonte
