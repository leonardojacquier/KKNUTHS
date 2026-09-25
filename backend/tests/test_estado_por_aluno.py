"""O estado da última chamada de IA não pode vazar de um aluno para outro.

Diagnóstico de 06/09 (item 6), ainda aberto em 25/09: `llm.py` guardava em
variável de MÓDULO a conferência do print, a do lobby, o motivo do 🎈 e os
erros de visão/followup. O bot roda cada análise num asyncio.to_thread —
threads reais. Dois alunos mandando print ao mesmo tempo, e o B podia
receber "li A♠K♦ — confere?" com as cartas do A.

E a mina ao lado: `app/repository.py`, 734 linhas, zero referências, cópia
do repositório SEM o portão `publicavel` — bastava um import errado.
"""
from __future__ import annotations

import asyncio
import inspect
import pathlib
import re
import threading


def test_llm_nao_tem_estado_global_de_ultima_chamada():
    from app.agent import llm

    fonte = inspect.getsource(llm)
    assert not re.search(r"^LAST_[A-Z_]+\s*[:=]", fonte, re.M), \
        "voltou variável LAST_* de módulo"
    assert "global LAST_" not in fonte


def test_duas_leituras_simultaneas_nao_se_misturam():
    """Aluno A grava divergência e demora; aluno B, no meio, não a vê."""
    from app.agent import llm

    gravou = threading.Event()
    b_leu = threading.Event()
    visto: dict[str, object] = {}

    def aluno_a():
        llm._VISION_CHECK.set({"divergencias": ["li A♠K♦"],
                               "conferido": False})
        gravou.set()
        b_leu.wait(5)
        visto["a"] = llm.conferencia_da_visao()

    def aluno_b():
        gravou.wait(5)
        visto["b"] = llm.conferencia_da_visao()
        b_leu.set()

    async def _rodar():
        await asyncio.gather(asyncio.to_thread(aluno_a),
                             asyncio.to_thread(aluno_b))

    asyncio.run(_rodar())
    assert visto["b"] is None, "o aluno B leu a conferência do aluno A"
    assert visto["a"]["divergencias"] == ["li A♠K♦"], \
        "o próprio aluno A perdeu a sua conferência"


def test_os_leitores_usam_o_acessor_e_nao_o_nome_antigo():
    raiz = pathlib.Path(__file__).resolve().parent.parent / "app"
    for arq in raiz.rglob("*.py"):
        txt = arq.read_text(encoding="utf-8")
        assert not re.search(
            r"LAST_(VISION_CHECK|VISION_ERROR|SIMPLIFY_REASON|FOLLOWUP_ERROR"
            r"|LOBBY_CHECK)", txt), arq


def test_a_copia_morta_do_repositorio_nao_volta():
    raiz = pathlib.Path(__file__).resolve().parent.parent / "app"
    assert not (raiz / "repository.py").exists(), (
        "app/repository.py é a cópia sem o portão `publicavel`; o "
        "repositório é app/db/repository.py")
