"""A memória do coach: ele lê o que já viu, ou só escreve?

Auditoria de 07/08: 385 análises com embedding, 100% indexadas, e o único
código que lia era o comando /ask — usado ZERO vezes desde 02/07. Embedding
escrito e nunca consultado é custo puro. Pior: tudo era por aluno (a busca
trava em user_id), então as 194 mãos do Ricardo eram invisíveis na 4ª mão do
Antonio — a ferramenta não aprendia com os usuários, aprendia sobre cada um
em separado.

Aqui se testa o que dá para provar sem LLM: que a memória é LIDA, que ela
degrada sem derrubar a análise, e que o anonimato da memória coletiva é
conferido em vez de pedido.
"""
from __future__ import annotations

import pytest

from app.agent.memoria import montar, resumo_para_busca

_STRUCT = {
    "formato": "tournament",
    "effective_bb": 11.9,
    "spots": [{"street": "preflop", "posicao": "SB", "acao": "call all-in",
               "board": ""}],
}


class _RepoFake:
    enabled = True

    def __init__(self, minhas=None, coletivo=None, explode=None):
        self._minhas = minhas or []
        self._coletivo = coletivo or []
        self._explode = explode or set()
        self.marcados: list[str] = []

    def search_analysis(self, user_id, emb, limit=8):
        if "minhas" in self._explode:
            raise RuntimeError("banco caiu")
        return self._minhas[:limit]

    def buscar_conhecimento(self, emb, limit=3, min_alunos=1):
        if "coletivo" in self._explode:
            raise RuntimeError("rpc falhou")
        return self._coletivo[:limit]


def _emb(_texto):
    return [0.1] * 1536


def test_resumo_pega_o_que_define_o_spot():
    r = resumo_para_busca(_STRUCT)
    assert "preflop" in r and "SB" in r and "12bb" in r
    assert resumo_para_busca({}) == ""
    assert resumo_para_busca(None) == ""


def test_le_as_maos_parecidas_do_proprio_aluno():
    """O caminho que não existia: 385 análises indexadas e nada consultava."""
    repo = _RepoFake(minhas=[{"summary": "✅ Pagou certo com KK no SB"},
                             {"summary": "❌ Foldou AQ barato demais"}])
    bloco, usados = montar(_STRUCT, repo, "u-1", _emb)
    assert bloco["suas_maos_parecidas"] == [
        "✅ Pagou certo com KK no SB", "❌ Foldou AQ barato demais"]
    assert "continuidade" in bloco["instrucao_maos_parecidas"]
    assert usados == []          # nenhum saber coletivo foi usado


def test_le_o_que_aprendeu_com_os_outros_alunos():
    repo = _RepoFake(coletivo=[{
        "id": "k-1", "kind": "padrao", "titulo": "Call curto com par alto",
        "gatilho": "SB com 10-15bb contra shove do CO",
        "texto": "Foldar aqui custa 8bb de EV.", "alunos": 4, "ev_bb": -8.0}])
    bloco, usados = montar(_STRUCT, repo, "u-1", _emb)
    linha = bloco["aprendido_com_outros_alunos"][0]
    assert "Call curto com par alto" in linha
    assert "QUANDO: SB com 10-15bb" in linha
    assert "visto em 4 alunos" in linha, "a força da evidência tem que ir junto"
    assert "8.0bb" in linha
    assert usados == ["k-1"]


def test_saber_de_um_aluno_so_vai_marcado_como_pista():
    """1 aluno é anedota. O coach precisa saber a diferença — senão trata
    coincidência como regra e ensina errado com convicção."""
    repo = _RepoFake(coletivo=[{
        "id": "k-2", "kind": "padrao", "titulo": "X", "gatilho": "Y",
        "texto": "Z", "alunos": 1}])
    bloco, _ = montar(_STRUCT, repo, "u-1", _emb)
    assert "pista, não como regra" in bloco["aprendido_com_outros_alunos"][0]


def test_o_aluno_nunca_pode_saber_que_existem_outros():
    repo = _RepoFake(coletivo=[{"id": "k", "kind": "padrao", "titulo": "T",
                                "gatilho": "G", "texto": "X", "alunos": 3}])
    bloco, _ = montar(_STRUCT, repo, "u-1", _emb)
    ins = bloco["instrucao_coletiva"]
    assert "NUNCA diga" in ins and "outro aluno" in ins
    # e a mesa ganha do prior: padrão não pode virar fato da mão
    assert "a mesa ganha" in ins


@pytest.mark.parametrize("falha", ["minhas", "coletivo"])
def test_memoria_quebrada_nao_derruba_a_analise(falha):
    """Memória é bônus. Se o banco cair, a análise sai igual a antes."""
    repo = _RepoFake(minhas=[{"summary": "s"}],
                     coletivo=[{"id": "k", "kind": "padrao", "titulo": "T",
                                "gatilho": "G", "texto": "X", "alunos": 2}],
                     explode={falha})
    bloco, usados = montar(_STRUCT, repo, "u-1", _emb)
    assert isinstance(bloco, dict)      # não levantou
    if falha == "coletivo":
        assert "suas_maos_parecidas" in bloco and usados == []
    else:
        assert "aprendido_com_outros_alunos" in bloco


def test_sem_provedor_de_embedding_segue_sem_memoria():
    repo = _RepoFake(minhas=[{"summary": "s"}])
    assert montar(_STRUCT, repo, "u-1", lambda _t: None) == ({}, [])
    # e se o próprio embed explodir
    def _boom(_t):
        raise RuntimeError("voyage fora")
    assert montar(_STRUCT, repo, "u-1", _boom) == ({}, [])


def test_sem_banco_nao_tenta_nada():
    class _Off:
        enabled = False
    assert montar(_STRUCT, _Off(), "u-1", _emb) == ({}, [])
    assert montar(_STRUCT, None, "u-1", _emb) == ({}, [])


def test_esta_ligado_na_analise_e_conta_o_uso():
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "montar_memoria" in fonte, "a memória não é lida na análise"
    assert "structured.update(bloco)" in fonte
    # sem contador não dá para saber se serviu — foi o erro do /ask
    assert "marcar_uso_conhecimento" in fonte
