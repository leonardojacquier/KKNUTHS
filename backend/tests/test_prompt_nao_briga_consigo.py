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


# frases que PROÍBEM explicar termo. Viveram no TERMOS_REGRA até 15/08, na
# linha imediatamente acima do V4, que manda o contrário.
_PROIBE_EXPLICAR = (
    "não explique termos",
    "sem parênteses didáticos",
    "sem parêntese didático",
    "proibido explicar termo",
    "nunca explique termo",
    "exclusiva da simplificação",
)
# e as que MANDAM — o teto do V4 é escrito assim
_MANDA_EXPLICAR = ("primeira aparição", "primeira vez")


def _textos_que_chegam_ao_modelo() -> dict[str, str]:
    """As constantes de prompt MAIS os blocos de sistema montados dentro das
    funções — a contradição de 15/08 morava entre duas constantes, mas a
    próxima pode morar num literal solto dentro de simplify()."""
    import inspect

    out = {f"_SYSTEM[{k}]": v for k, v in llm._SYSTEM.items()}
    for nome in ("TERMOS_REGRA", "_FORMA_SIMPLES"):
        valor = getattr(llm, nome, None)
        if isinstance(valor, str):
            out[nome] = valor
    for nome in ("coach", "followup", "prepare_briefing", "sintese_do_dossie",
                 "simplify"):
        fn = getattr(llm, nome, None)
        if fn is not None:
            # comentário de código não é instrução: o histórico pode citar a
            # frase antiga sem que o modelo leia. (Corta a linha no '#', então
            # erra para o lado de deixar passar, nunca de gritar errado.)
            out[f"{nome}()"] = re.sub(r"#.*", "", inspect.getsource(fn))
    return out


def test_o_prompt_nao_proibe_e_manda_explicar():
    """A 3ª contradição, achada em 15/08 — e a única que nenhum teste pegava.

    O V4 novo MANDA explicar o termo (parêntese curto na primeira aparição,
    no máximo 2) e o V3, na linha IMEDIATAMENTE acima, dizia 'NÃO explique
    termos ... sem parênteses didáticos ... função EXCLUSIVA da
    simplificação'. Rótulo, ordem, calque e tamanho — tudo que os outros
    testes deste arquivo leem — passava nos dois lados ao mesmo tempo.

    O modelo obedece à regra que estiver mais perto do exemplo, então com as
    duas no ar ninguém sabe qual valeu. Enquanto o prompt MANDAR explicar,
    nenhuma camada de texto pode proibir.
    """
    textos = _textos_que_chegam_ao_modelo()
    manda = [onde for onde, s in textos.items()
             if any(p in s.lower() for p in _MANDA_EXPLICAR)]
    assert manda, (
        "nenhum texto manda explicar o termo. Se a política voltou a ser "
        "'jargão cru e ponto', este teste sai junto com o V4 que ele guarda "
        "— mas não fica passando à toa.")
    proibe = [f"{onde}: {frase!r}" for onde, s in textos.items()
              for frase in _PROIBE_EXPLICAR if frase in s.lower()]
    assert not proibe, (
        "o prompt manda explicar o termo em " + ", ".join(manda)
        + " e proíbe em:\n" + "\n".join(f"  • {p}" for p in proibe))


def test_o_fechamento_nao_cala_a_historia_do_desfecho():
    """4ª contradição (15/08), mesma família da do R7 × R2: o R3 novo proíbe
    repetir número que o placar já deu, e o R5b MANDA o parágrafo do desfecho
    trazer 'as % de cada rua' — que são as equities do placar. Sem a exceção
    ESCRITA, uma regra apaga a outra, e a que ganha é a que tiver exemplo do
    lado.

    O que dá para conferir aqui é o PEDIDO: as duas regras têm que se citar.
    Quem confere a SAÍDA é o guarda determinístico (app/bot/guarda_voz.py) —
    a diferença entre RECITAR a conta e CONTAR a história é semântica e não
    sobrevive a uma regex, então um teste de texto aqui seria decorativo.
    """
    r3 = re.search(r"R3 .*?(?=R4 )", PT, re.S).group(0)
    assert "RECITAR" in r3, \
        "o R3 tem que proibir a recitação, não o número em si"
    assert "R5b" in r3, \
        "o R3 proíbe repetir número sem abrir a exceção do R5b"
    r5b = re.search(r"R5b .*?(?=R6 )", PT, re.S).group(0)
    # sem pinar a palavra que o R5b usa para street: ele ainda diz o calque
    # "rua", e um teste não pode ser o motivo de o calque continuar lá
    assert "% de cada" in r5b, \
        "se o R5b parou de pedir as %, a exceção do R3 ficou órfã"


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
