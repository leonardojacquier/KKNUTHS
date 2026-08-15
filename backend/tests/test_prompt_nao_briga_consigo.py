"""O prompt é coerente consigo mesmo?

São ~2.900 palavras de instrução em 33 regras, mais ~2.900 nas descrições
das 33 ferramentas. Ninguém relê isso inteiro a cada mudança, então as
incoerências se acumulam caladas — e o modelo obedece à que estiver mais
perto do exemplo.

Duas achadas ao medir (08/08):

1. R7 proibia "mais de um número por frase de porquê" e R2 MANDA escrever
   'pedia 30%, tinha 12% → −11bb' — três números — com um exemplo de ouro
   que mostra quatro. Regra que briga com a demonstração ao lado perde, e
   ainda arrisca calar número em outro lugar.
2. o bloco C mandava ler C10, depois C11c, C11b e só então C11: sub-regras
   de uma regra que ainda não tinha aparecido. Eram três regras distintas
   empilhadas dentro do C10 com rótulo errado.

O que NÃO foi achado, e vale registrar: nenhuma regra morta. Toda ferramenta
citada existe e toda chave de contexto citada é produzida por alguém. A
"gordura" que uma auditoria estimou em ~800 palavras não sobreviveu à
medição — o que existe é ~400 palavras de eco das descrições das ferramentas,
onde a regra ainda acrescenta o COMO FALAR sobre o que a ferramenta faz.
Cortar isso no escuro, sem poder medir o efeito numa mão real, seria trocar
um defeito conhecido por um desconhecido.
"""
from __future__ import annotations

import re

import pytest

from app.agent import llm

PT = llm._SYSTEM["pt"]
_CABECA = r"(?:(?<=^)|(?<=[.:;] ))([RFCVA]\d+[a-z]?) "


def _rotulos(texto: str) -> list[str]:
    return re.findall(_CABECA, texto, re.M)


def _blocos() -> dict[str, str]:
    return {b[0]: b for b in re.split(r"\n== ", PT)[1:]}


def test_cada_regra_aparece_uma_vez_so():
    from collections import Counter

    repetidas = [r for r, n in Counter(_rotulos(PT)).items() if n > 1]
    assert not repetidas, f"rótulo duplicado: {repetidas}"


@pytest.mark.parametrize("letra", ["R", "F", "C", "V", "A"])
def test_as_regras_estao_no_bloco_certo_e_em_ordem(letra):
    """O modelo lia C11c e C11b ANTES de C11 — sub-regra de uma regra que
    ainda não apareceu. Não é preciosismo: a ordem é o único índice que ele
    tem para achar a regra que vale."""
    bloco = _blocos()[letra]
    achados = _rotulos(bloco)
    fora = [a for a in achados if not a.startswith(letra)]
    assert not fora, f"regra {fora} mora no bloco {letra}"

    def _chave(r):
        m = re.match(r"[A-Z](\d+)([a-z]?)", r)
        return int(m.group(1)), m.group(2)

    assert achados == sorted(achados, key=_chave), \
        f"bloco {letra} fora de ordem: {achados}"


def test_o_placar_nao_e_proibido_pela_regra_do_lado():
    """R7 proibia o que R2 manda. Quem vence uma contradição é o exemplo, e
    o exemplo do R2 tem QUATRO números — ou seja, a proibição era letra
    morta que ainda podia calar número em outro lugar."""
    r7 = re.search(r"R7 .*?(?=\n== )", PT, re.S).group(0)
    assert "mais de um número" in r7
    assert "PROSA" in r7 and "R2" in r7, \
        "a proibição precisa dizer que vale para a prosa, e abrir o placar"


def test_o_exemplo_de_ouro_continua_com_a_conta_inteira():
    """Se um dia alguém 'consertar' a contradição pelo outro lado — tirando
    os números do exemplo — o placar perde o que ele existe para mostrar."""
    i = PT.index("R2 PLACAR")
    exemplo = PT[i:PT.index("R3 FECHAMENTO", i)]
    assert "pedia 30%, tinha 12%" in exemplo and "−11bb" in exemplo


def test_todo_nome_tecnico_do_prompt_existe_de_verdade():
    """Cada `snake_case` do prompt é OU uma ferramenta OU um campo que
    alguém produz. Não há terceira opção honesta.

    Regra apontando para ferramenta removida é instrução que o modelo tenta
    seguir e não consegue. Regra falando de um campo que ninguém preenche é
    pior: ele preenche o vazio de imaginação, que é a doença que este
    projeto inteiro combate.

    Sem lista de exceção de propósito — lista de exceção é onde o nome morto
    se esconde.
    """
    from pathlib import Path

    raiz = Path(__file__).parent.parent
    fonte = "".join(
        p.read_text() for p in sorted((raiz / "app").rglob("*.py")))
    ferramentas = {t["name"] for t in llm.TOOLS}
    citados = {n for n in re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b", PT)}

    orfaos = sorted(
        n for n in citados
        if n not in ferramentas
        and f'"{n}"' not in fonte and f"'{n}'" not in fonte
        and f"{n} =" not in fonte and f"def {n}" not in fonte)
    assert not orfaos, (
        f"o prompt cita {orfaos} — nem ferramenta, nem campo que alguém "
        "produz. O modelo vai tentar usar isso.")


# teto medido em 08/08 (2.901 palavras) com folga para uma regra nova. Não é
# meta de emagrecimento: é freio. O prompt cresce um parágrafo por vez, e
# cada acréscimo parece pequeno na hora em que é escrito.
#
# 15/08 (voz-do-coach): o freio pegou, como devia. R3 reescrito, R7 com duas
# proibições novas e V4 inteiro pela voz nova custaram +211 palavras (2.945 →
# 3.155, +7% de uma vez). Conferido o que o freio manda conferir: nenhuma das
# palavras novas é eco de descrição de ferramenta — são regra de VOZ, que não
# existe em ferramenta nenhuma. Teto subido de propósito, não por acidente. Se
# alguém quiser pagar essa conta, o lugar óbvio é o R4, que ainda gasta 20
# palavras num exemplo do título fixo que o R3 agora proíbe por inteiro.
_TETO_PALAVRAS = 3200


def test_o_prompt_nao_cresce_calado():
    n = len(PT.split())
    assert n <= _TETO_PALAVRAS, (
        f"o system prompt está com {n} palavras (teto {_TETO_PALAVRAS}). "
        "Antes de subir o teto: alguma regra virou eco da descrição de uma "
        "ferramenta?")


def test_as_ferramentas_tambem_tem_freio():
    n = sum(len(str(t).split()) for t in llm.TOOLS)
    assert n <= 3300, f"as descrições de ferramenta estão com {n} palavras"
