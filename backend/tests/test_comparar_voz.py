"""O comparador isola o PROMPT como variável — nada mais."""
from __future__ import annotations

import ast
import inspect
import pathlib

import pytest

import scripts.comparar_voz as comparador
from scripts.comparar_voz import montar_markdown, montar_par


def test_o_markdown_traz_os_dois_lados_e_o_modelo():
    md = montar_markdown([{
        "hand_id": "abc", "modelo": "claude-opus-4-8",
        "antes": "✅ Você jogou bem\n\nA conta que mais pesa: era jam.",
        "depois": "✅ Você jogou bem\n\nCom 12bb, jam é a única linha.",
    }])
    assert "ANTES" in md and "DEPOIS" in md
    assert "claude-opus-4-8" in md
    assert "A conta que mais pesa" in md


def test_par_sem_depois_e_marcado_e_nao_some():
    """Falha de geração tem que aparecer; sumir com o par faria a
    comparação parecer melhor do que é."""
    md = montar_markdown([{"hand_id": "x", "modelo": "m",
                           "antes": "texto", "depois": None}])
    assert "falhou" in md.lower()


def _linha(hand_id="y", modelo="m", summary="texto do antes"):
    return {"hand_id": hand_id, "modelo": modelo, "summary": summary}


def test_o_markdown_declara_o_que_o_depois_refaz_e_o_que_nao():
    """I5 — o dono vai LER este arquivo para decidir o merge. Se o cabeçalho
    não disser quais camadas rodaram no "depois", ele credita ao prompt o
    que é efeito do perfil (que é o de HOJE, não o do dia do "antes")."""
    md = montar_markdown([])
    assert "perfil" in md.lower(), "o markdown não avisa sobre o perfil"
    assert "guarda_voz.limpar()" in md, \
        "o markdown não diz que o 'depois' passou pelo guarda da voz"
    assert "de HOJE" in md, \
        "a variável que não dá para zerar tem que estar declarada"


def _chamada_de_coach() -> ast.Call:
    p = pathlib.Path(comparador.__file__).with_suffix(".py")
    for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "coach":
            return n
    raise AssertionError("coach() não é chamado no comparador")


def test_o_depois_e_gerado_com_o_perfil_do_aluno():
    """I5 — o "depois" saía com `stats=None` enquanto produção passa o
    perfil (`processing.py`, `coach(structured, perfil, ...)`). O
    experimento desenhado para ter UMA variável tinha o perfil como segunda:
    um "antes" que diz "você paga demais no river — 34% em 61 mãos" não tem
    contrapartida possível num "depois" cego, e o dono lê isso como o prompt
    novo tendo ficado menos pessoal."""
    segundo = _chamada_de_coach().args[1]
    assert not (isinstance(segundo, ast.Constant) and segundo.value is None), \
        "coach() ainda é chamado com stats=None — o perfil voltou a ser " \
        "uma segunda variável do experimento"


def test_o_depois_passa_pelo_guarda_da_voz_como_a_producao():
    """I5 — todo texto de produção passa por `conferir_e_limpar` antes de
    chegar ao aluno. Sem `limpar()` aqui, um 'A conta que mais pesa' que o
    guarda apagaria aparece cru no arquivo, e o dono julga um texto que
    nenhum aluno receberia."""
    fonte = inspect.getsource(comparador.main)
    assert "limpar(texto)" in fonte, \
        "o 'depois' voltou a ser julgado sem o guarda da voz"


def test_a_terceira_variavel_do_perfil_usa_a_funcao_da_producao():
    """Regra duplicada é regra que diverge: o perfil do comparador sai da
    MESMA função que processing.py usa."""
    from app.analysis.stats import PlayerStats, perfil_para_o_coach

    magro = PlayerStats(player="x", hands=3)
    assert perfil_para_o_coach(magro)["indisponivel"] is True
    assert "sessão inteira" in perfil_para_o_coach(magro)["por_que"]
    assert "perfil_para_o_coach" in inspect.getsource(comparador.main)


def test_falha_ao_buscar_a_mao_vira_par_marcado_e_nao_some():
    """Igual à falha de geração: uma falha de REDE ao buscar a mão em
    `hands` não pode fazer o par desaparecer do sorteio sem deixar rastro —
    tem que virar uma linha visível de falha no markdown, não um `continue`
    mudo."""
    def buscar_com_erro():
        raise RuntimeError("rede caiu")

    par = montar_par(_linha(), buscar_com_erro, lambda mao: "não deveria chamar")

    assert par is not None
    assert par["depois"] is None
    assert par["antes"] == "texto do antes"
    assert "falhou" in montar_markdown([par]).lower()


def test_mao_nao_encontrada_tambem_vira_par_marcado():
    """A mão pode ter sido apagada de `hands` sem erro de rede — mesmo
    tratamento: par visível, "depois" marcado como falha."""
    par = montar_par(_linha(), lambda: [], lambda mao: "não deveria chamar")

    assert par is not None
    assert par["depois"] is None
    assert "não encontrada" in montar_markdown([par]).lower()


def test_o_markdown_distingue_mao_sumida_de_geracao_quebrada():
    """Os dois casos pedem reações OPOSTAS do leitor e saíam idênticos —
    "_(a geração falhou)_" nos dois —, com a diferença só no print de
    console, que não é o artefato que o dono lê. Mão sumida: ignore o par.
    Geração quebrada: o prompt novo pode estar quebrando algo, e o modo de
    falha silencioso conhecido (model_validate levantando em `canonical`
    antigo) faria TODOS os pares saírem assim.
    """
    def _explode(mao):
        raise RuntimeError("model_validate: campo 'streets' ausente")

    sumida = montar_par(_linha(hand_id="sumiu"), lambda: [], _explode)
    quebrou = montar_par(_linha(hand_id="quebrou"),
                         lambda: [{"canonical": {}}], _explode)

    md = montar_markdown([sumida, quebrou])
    assert "mão não encontrada em `hands`" in md
    assert "a geração do 'depois' falhou: model_validate" in md
    assert md.count("_(") == 2, "os dois casos saíram com o mesmo texto"


def test_sucesso_chama_gerar_com_o_resultado_da_busca():
    """Caminho feliz: `gerar_depois` recebe o que `buscar_mao` devolveu e o
    texto dele vira o "depois" do par."""
    par = montar_par(_linha(), lambda: [{"canonical": "mão-x"}],
                     lambda mao: f"depois de {mao[0]['canonical']}")

    assert par["depois"] == "depois de mão-x"
    assert par["hand_id"] == "y"
    assert par["modelo"] == "m"


@pytest.mark.parametrize("modelo_bruto,esperado", [(None, "?"), ("", "?"), ("m", "m")])
def test_modelo_ausente_vira_interrogacao_no_par(modelo_bruto, esperado):
    par = montar_par(_linha(modelo=modelo_bruto), lambda: [], lambda mao: "x")
    assert par["modelo"] == esperado
