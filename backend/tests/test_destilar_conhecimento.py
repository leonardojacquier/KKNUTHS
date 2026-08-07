"""O destilador da memória coletiva não pode vazar quem é quem.

Com 10 alunos que se conhecem do mesmo clube, "anônimo" não é opcional: um
padrão que diga "o cara que paga demais no river" é identificável na hora, e
o aluno descobre que o coach comenta o jogo dele com os outros. O prompt
PEDE anonimato; estes testes CONFEREM — que é a diferença entre as duas
coisas, e a lição que este projeto já aprendeu caro.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from destilar_conhecimento import (MIN_ALUNOS, agrupar_por_tema, cita_nome,
                                   validar)

NOMES = ["Ricardo Farah", "Leo", "dscholze1979", "Odilon Godeje"]

_BOM = {"vale": True, "titulo": "Overpair curto não folda",
        "gatilho": "SB com 10-15bb contra shove do CO",
        "texto": "Foldar overpair nessa profundidade custa cerca de 8bb de "
                 "EV; o call é obrigatório contra o range de shove.",
        "categoria": "preflop", "ev_bb": -8.0}


def test_saber_bem_formado_entra():
    ok = validar(_BOM, NOMES, alunos=3)
    assert ok and ok["alunos"] == 3
    assert ok["categoria"] == "preflop" and ok["ev_bb"] == -8.0


def test_saber_que_cita_aluno_e_descartado_nao_corrigido():
    """Descartar, não 'limpar': texto que nasceu identificável costuma ter
    mais do que o nome dentro."""
    vazado = dict(_BOM, texto=_BOM["texto"] + " Foi o caso do Ricardo Farah.")
    assert validar(vazado, NOMES, alunos=3) is None

    no_titulo = dict(_BOM, titulo="O leak do Leo")
    assert validar(no_titulo, NOMES, alunos=3) is None

    no_gatilho = dict(_BOM, gatilho="quando o dscholze1979 abre")
    assert validar(no_gatilho, NOMES, alunos=3) is None


def test_cita_nome_ignora_pedaco_curto_demais():
    """'Leo' tem 3 letras e é nome real; 'Ed' teria 2 e casaria com meio
    dicionário — o piso evita descartar saber bom por coincidência."""
    assert cita_nome("o erro do leo aqui", ["Leo"])
    assert not cita_nome("o river ficou molhado", ["Ed"])


def test_saber_sem_numero_e_opiniao():
    sem = dict(_BOM, texto="Foldar overpair curto é sempre ruim, não faça "
                           "isso nunca, é um erro grave de fundamento.")
    assert validar(sem, NOMES, alunos=3) is None


def test_recusa_do_modelo_e_respeitada():
    assert validar({"vale": False}, NOMES, 3) is None
    assert validar({}, NOMES, 3) is None
    assert validar("lixo", NOMES, 3) is None
    assert validar(None, NOMES, 3) is None


def test_frase_de_efeito_nao_e_saber():
    curto = dict(_BOM, texto="Pague sempre com 8bb.")
    assert validar(curto, NOMES, alunos=3) is None


def test_categoria_invalida_vira_nulo_em_vez_de_barrar():
    x = validar(dict(_BOM, categoria="banana"), NOMES, 3)
    assert x is not None and x["categoria"] is None


def test_so_agrupa_tema_visto_em_alunos_diferentes():
    """Duas notas do MESMO aluno não são padrão — são a mesma pessoa."""
    mesmo = [{"user_id": "a", "note": "paga demais no river"},
             {"user_id": "a", "note": "river de novo, pagou mal"}]
    assert agrupar_por_tema(mesmo) == {}

    dois = mesmo + [{"user_id": "b", "note": "erra no river também"}]
    grupos = agrupar_por_tema(dois)
    assert "river" in grupos
    assert len({n["user_id"] for n in grupos["river"]}) >= MIN_ALUNOS


def test_prompt_proibe_nome_e_exige_numero():
    from destilar_conhecimento import _PROMPT

    assert "NUNCA cite nome" in _PROMPT
    assert "número" in _PROMPT and "recuse" in _PROMPT


def test_o_modelo_nao_recebe_identidade():
    """O que ele não recebe não vaza: o corpo do prompt é só o texto das
    notas, sem user_id, sem nome, sem data."""
    import inspect

    import destilar_conhecimento as d

    fonte = inspect.getsource(d.main)
    assert "SEM user_id no prompt" in fonte
    corpo = fonte.split("corpo =")[1].split("try:")[0]
    assert "user_id" not in corpo and "username" not in corpo
