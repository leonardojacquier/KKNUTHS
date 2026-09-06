"""O prompt ensinava os calques que ele mesmo proíbe.

TERMOS_REGRA bane "check atrás" ("é CHECK BEHIND") e manda top pair ficar
em inglês. O EXEMPLO DE OURO do R2 — a única coisa no prompt inteiro que
mostra a FORMA da resposta pronta — escrevia:

    ✅ *Flop* A♦7♣2♠ — c-bet, top par (você tinha 69%).
    🟡 *Turn* 5♥ — check atrás: perde 1 rodada de valor.

Modelo lê a regra e copia o exemplo. Foi por isso que "check atrás" saiu em
23 análises entregues com o glossário ligado o tempo todo: a regra estava
certa e a demonstração estava errada, e a demonstração ganha.

Mesma família de "sequência" no lugar de straight, em três explicações de
ferramenta ("'QJ fechou flush' num board de duas copas (era sequência)").

Este teste é a conferência do PEDIDO — lê o texto que vai para o modelo e
cobra dele a regra que ele carrega. Não substitui o corretor de saída
(app/agent/termos.py); tapa o buraco antes, na fonte.
"""
import re

import pytest

from app.agent import llm

# os calques do bloco CALQUES PROIBIDOS que dá pra procurar sem falso
# positivo. Ficam de fora os que existem em português legítimo noutro
# sentido ("aumentar" o pote, narração de "sequência" de ações), porque um
# teste que grita errado é desligado na primeira semana.
_PROIBIDOS = {
    r"\bcheck atr[áa]s\b": "é CHECK BEHIND",
    r"\btop par\b": "é TOP PAIR (não traduz pela metade)",
    r"\bpar grande\b": "é OVERPAIR",
    r"\bm[ãa]o grande\b": "não existe no poker BR",
    r"\bpar alto\b": "é OVERPAIR/top pair",
    r"\bcarta alta\b": "é HIGH CARD ('A high')",
    r"\b(?:sete|dez|dama|valete|rei|[2-9]|10)s? cheio de\b": (
        "é 'full de X com Y'"),
    r"\bsequ[êe]ncia de cor\b": "é STRAIGHT FLUSH",
    r"\b1010\b": "o dez sem naipe é T — TT, ATo, KTs",
}

def _regra_do_dez() -> str:
    """A frase do V1 que proíbe '1010' — precisa nomear o erro pra proibi-lo."""
    pt = llm._SYSTEM["pt"]
    i = pt.find("O DEZ é")
    return pt[i:pt.index("\n", i)] if i >= 0 else ""


# uma proibição PRECISA nomear o calque para proibi-lo; são os únicos
# trechos onde eles podem aparecer
_ONDE_PODE = (llm.TERMOS_REGRA, _regra_do_dez())


def _textos_do_prompt() -> dict[str, str]:
    """Tudo que sai daqui e chega ao modelo como instrução."""
    out: dict[str, str] = {}
    for idioma, texto in llm._SYSTEM.items():
        out[f"_SYSTEM[{idioma}]"] = texto
    for nome in ("_FORMA_SIMPLES", "_VISION_PROMPT", "_VISION_VERIFY_PROMPT"):
        valor = getattr(llm, nome, None)
        if isinstance(valor, str):
            out[nome] = valor
    for ferramenta in llm.TOOLS:
        out[f"TOOLS[{ferramenta['name']}].description"] = \
            ferramenta.get("description", "")
        for campo, esquema in (ferramenta.get("input_schema", {})
                               .get("properties", {}) or {}).items():
            out[f"TOOLS[{ferramenta['name']}].{campo}"] = \
                str(esquema.get("description", ""))
    return out


def _sem_a_lista_de_proibicoes(texto: str) -> str:
    for permitido in _ONDE_PODE:
        texto = texto.replace(permitido, " ")
    return texto


@pytest.mark.parametrize("padrao,motivo", sorted(_PROIBIDOS.items()))
def test_prompt_nao_usa_calque_que_ele_proibe(padrao, motivo):
    achados = []
    for onde, texto in _textos_do_prompt().items():
        limpo = _sem_a_lista_de_proibicoes(texto)
        for m in re.finditer(padrao, limpo, re.I):
            i = max(0, m.start() - 50)
            achados.append(f"{onde}: ...{limpo[i:m.end() + 50]}...")
    assert not achados, (
        f"o prompt ensina o que proíbe ({motivo}):\n"
        + "\n".join(f"  • {a}" for a in achados))


def test_o_exemplo_de_ouro_do_placar_usa_a_lingua_certa():
    """O R2 é a única DEMONSTRAÇÃO de resposta pronta no prompt — o modelo
    copia dela mais do que da regra."""
    pt = llm._SYSTEM["pt"]
    i = pt.index("R2 PLACAR STREET A STREET")
    exemplo = pt[i:pt.index("R3 FECHAMENTO", i)]
    assert "top pair" in exemplo and "top par " not in exemplo
    assert "check behind" in exemplo and "check atrás" not in exemplo


def test_a_regra_do_dez_esta_escrita():
    """'só perde pra 1010 e AA' saiu numa lição real: V1 dizia como escrever
    carta COM naipe e nada sobre o rank sozinho."""
    pt = llm._SYSTEM["pt"]
    assert "1010" in pt, "a proibição precisa nomear o erro pra ser seguida"
    assert re.search(r"TT[,.]?\s|ATo|KTs", pt), \
        "sem o exemplo certo, proibir não ensina nada"


def test_a_lista_de_proibicoes_continua_nomeando_os_calques():
    """Guarda do próprio teste: se TERMOS_REGRA parar de citar 'check
    atrás', _ONDE_PODE deixa de mascarar coisa nenhuma e o teste acima vira
    decorativo sem ninguém perceber."""
    for pedaco in ("check atrás", "carta alta", "cheio de"):
        assert pedaco in llm.TERMOS_REGRA
    assert "1010" in _regra_do_dez(), \
        "a máscara do V1 só vale se a regra do dez ainda estiver lá"
