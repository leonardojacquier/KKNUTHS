"""O aluno tem que VER o relógio andando, não uma promessa parada.

Palavras dele sobre a espera do solver: *"foi isso que me lascou"* — pediu o
gráfico, ficou olhando uma mensagem estática por um minuto e concluiu, com
razão, que tinha quebrado.

Existia meio caminho: o `avisar_solver` mandava UMA mensagem dizendo "leva
cerca de 1 minuto". Mas era uma estimativa parada — nada se mexia depois
dela, que é exatamente o sintoma de travamento. E o contador de verdade
(`progresso.acompanhar`, que edita a mensagem com o tempo decorrido) só
estava ligado nos caminhos de UPLOAD; na conversa — que é onde o solver roda
— não havia contador nenhum.

Subir o orçamento do solver sem consertar isso seria piorar o problema de
propósito.
"""
from __future__ import annotations

import inspect

from app.analysis import river_solver as R
from app.bot import progresso

_OOP = "AA,KK,77,22,99,AK,AQ,AJ,KQ,QJ,JT,T9,98,87,76,65"
_IP = "AK,AQ,AJ,ATs,KQ,KJs,QJs,JTs,T9s,99,77,22,A5s,A4s"
_RIVER = ["Ah", "Kd", "7c", "2s", "9h"]


# ---- 1) o solver conta o próprio progresso ---------------------------------

def test_o_solver_avisa_o_progresso_enquanto_roda():
    vistos: list[float] = []
    R._CACHE.clear()
    R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop", iterations=400,
                  ao_progredir=lambda f: vistos.append(f))
    assert len(vistos) >= 5, (
        f"só {len(vistos)} avisos numa solve inteira — o aluno fica no escuro")
    assert vistos == sorted(vistos), "o progresso andou pra trás"
    assert 0.0 < vistos[0] <= 1.0 and vistos[-1] <= 1.0
    assert vistos[-1] >= 0.9, "nunca chegou perto do fim"


def test_o_solver_roda_igual_sem_ninguem_escutando():
    """O contador é enfeite do ponto de vista da conta: sem callback, a
    resposta tem que ser a mesma."""
    R._CACHE.clear()
    com = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop", iterations=300,
                        ao_progredir=lambda f: None)
    R._CACHE.clear()
    sem = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop", iterations=300)
    assert com["actions"] == sem["actions"]


def test_callback_que_explode_nao_derruba_a_analise():
    """Aviso que derruba o trabalho é pior que silêncio (regra do notify)."""
    def _explode(_f):
        raise RuntimeError("telegram fora do ar")

    R._CACHE.clear()
    r = R.solve_river(_RIVER, _OOP, _IP, 20.0, 60.0, "oop", iterations=300,
                      ao_progredir=_explode)
    assert r["actions"], "o contador derrubou a conta"


# ---- 2) o texto que o aluno lê ---------------------------------------------

def test_o_texto_do_solver_diz_a_street_e_a_porcentagem():
    t = R.texto_do_progresso(["Ah", "Kd", "7c"], 0.42)
    assert "flop" in t.lower()
    assert "42" in t
    assert R.texto_do_progresso(["Ah", "Kd", "7c", "2s"], 0.5).lower() \
        .count("turn") == 1
    assert "river" in R.texto_do_progresso(_RIVER, 0.1).lower()


def test_o_contador_mostra_tempo_decorrido_de_verdade():
    """Peça que já existia — aqui só se prende que o solver a usa: minuto e
    segundo, não uma promessa."""
    assert "1min 05s" in progresso.texto_do_contador("Resolvendo o flop", 65.0)
    assert "9s" in progresso.texto_do_contador("Resolvendo o river", 9.0)


def test_a_espera_longa_nao_fala_de_torneio_no_meio_de_um_solver():
    """A linha de espera longa era escrita só para torneio. Ela passou a
    aparecer no solver pós-flop, onde não há torneio nenhum — e frase que não
    bate com a etapa mina justamente o aviso que existe para tranquilizar."""
    longo = progresso.texto_do_contador("Resolvendo o equilíbrio do flop", 70.0)
    assert "torneio" not in longo.lower()
    assert "alguns minutos" in longo, "a espera longa deixou de ser explicada"


# ---- 3) o contador está LIGADO onde o solver roda --------------------------

def test_a_conversa_tambem_liga_o_contador():
    """Era só nos caminhos de upload. O solver roda na CONVERSA."""
    from app.bot import handlers

    fonte = inspect.getsource(handlers._route_text)
    assert "acompanhar" in fonte, (
        "o caminho da conversa chama o solver sem contador nenhum")
    assert "encerrar" in fonte, "contador ligado e nunca desligado vaza task"


def test_a_tool_do_solver_liga_o_progresso_no_chat():
    from app.agent import llm

    fonte = inspect.getsource(llm)
    # o BLOCO inteiro da tool: até o próximo `if name ==`, não uma janela de
    # N caracteres (que já deu falso vermelho quando o bloco cresceu)
    inicio = fonte.index('if name == "solve_river"')
    resto = fonte[inicio + 10:]
    trecho = fonte[inicio:inicio + 10 + resto.index('if name == "')]
    assert "ao_progredir" in trecho, (
        "a tool resolve sem repassar o progresso pro chat do aluno")
    assert "marcar" in trecho, "o progresso não chega no contador do chat"


def test_a_estimativa_do_aviso_nao_promete_numero_de_outra_maquina():
    """A estimativa fixa era medida numa máquina só. Com teto de relógio dá
    para prometer o TETO, que vale em qualquer uma."""
    from app.bot import notify

    for chaves in (3, 4, 5):
        assert chaves in notify.ESPERA
    fonte = inspect.getsource(notify.avisar_solver)
    assert "no máximo" in fonte or "até" in fonte, (
        "o aviso ainda promete um tempo médio em vez do teto")
