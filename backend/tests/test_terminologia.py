"""O coach fala grinder, não tradutor — e a simplificação ensina o idioma.

Pedido do dono (02/08): "ainda está saindo traduzido... quero linguagem
técnica de poker na análise principal; na simplificada aí sim explicar com
mais didática, mas também não precisa ser tão básico".

Medido nas análises reais de julho antes do ajuste: 'aumentou' 8x, 'carta
alta' 7x, 'sequência' 7x, 'passou' 3x. O 'aumentar' vazava porque estava na
lista de PERMITIDOS do prompt — chamávamos de consagrado um termo que
grinder não usa.
"""
import inspect

from app.agent.llm import TERMOS_REGRA, simplify
from scripts.output_judge import judge_answer


def _depois_de_proibidos(termo: str) -> bool:
    return TERMOS_REGRA.index(termo) > TERMOS_REGRA.index("CALQUES PROIBIDOS")


def test_aumentar_saiu_dos_permitidos_e_virou_calque():
    assert "'aumentar'" in TERMOS_REGRA
    assert _depois_de_proibidos("'aumentar'")
    permitidos = TERMOS_REGRA[:TERMOS_REGRA.index("CALQUES PROIBIDOS")]
    assert "aumentar" not in permitidos
    assert "raise" in permitidos, "o termo do grinder entra no lugar"


def test_os_calques_medidos_estao_proibidos():
    for termo in ("'sequência'", "'carta alta'", "'passou'"):
        assert termo in TERMOS_REGRA, termo
        assert _depois_de_proibidos(termo), termo


def test_o_juiz_vigia_os_calques_medidos():
    """Sem vigia, a regressão volta em silêncio — como vazou até aqui."""
    t = "No turn ele aumentou pra 6bb e você tinha uma sequência feita."
    probs = judge_answer(t, conversa=False)
    assert any("aumentou" in p for p in probs)
    assert any("sequência" in p for p in probs)
    assert any("carta alta" in p
               for p in judge_answer("Você só tinha carta alta no river."))


def test_termos_legitimos_nao_disparam_o_juiz():
    t = ("✅ Você jogou bem — 3-bet padrão\n\nDeu raise pra 7bb, o straight "
         "draw não completou e o A high ganhou no showdown.")
    assert not any("calque" in p for p in judge_answer(t))


def test_simplificacao_e_para_quem_joga_nao_para_leigo():
    """'Para alguém que NUNCA estudou o jogo' era o 'básico demais': analogia
    de padaria e 1 número só. O alvo agora é quem joga sem ser profissional:
    termo técnico FICA, explicação curta em parêntese, 2-3 números com
    significado."""
    fonte = inspect.getsource(simplify)
    assert "NUNCA estudou" not in fonte
    assert "não é profissional" in fonte
    assert "NÃO infantilize" in fonte


def test_o_glossario_chega_ao_modelo_em_TODA_tentativa(monkeypatch):
    """O que importa é o `system` que SAI, não o identificador no fonte.

    A versão anterior fazia `assert "TERMOS_REGRA" in inspect.getsource(...)`.
    Como `simplify` tem DUAS chamadas ao modelo — a primeira e a retentativa
    quando o texto saiu parecido demais — bastava o nome aparecer numa delas.
    Medido em 09/08: removendo o glossário do prompt da PRIMEIRA chamada (a
    que responde o botão 🎈 quase sempre), 355 testes passavam.

    Aqui o cliente é falso e grava o que foi enviado. Se o glossário sumir de
    qualquer uma das tentativas, isto quebra.
    """
    from app.agent import llm

    enviados: list[str] = []

    class _Bloco:
        type = "text"

        def __init__(self, t):
            self.text = t

    class _Resp:
        # devolve o MESMO texto de entrada, o que força `parecidos()` a
        # disparar a segunda tentativa — é assim que as duas são exercitadas
        content = [_Bloco("O vilão apostou no flop e você pagou com top pair.")]
        usage = None

    def _falso(client, **kw):
        enviados.append(kw.get("system") or "")
        return _Resp()

    monkeypatch.setattr(llm, "_create", _falso)

    # `simplify` faz `from app.config import get_settings` DENTRO da função,
    # então o patch tem que ser no módulo de origem
    import app.config as cfg

    real = cfg.get_settings()

    class _Cfg:
        anthropic_api_key = "sk-teste"
        cheap_model = getattr(real, "cheap_model", None) or "modelo-barato"

        def __getattr__(self, nome):
            return getattr(real, nome)

    monkeypatch.setattr(cfg, "get_settings", lambda: _Cfg())
    llm.simplify("O vilão apostou no flop e você pagou com top pair.")

    assert len(enviados) >= 2, (
        "a retentativa não foi exercitada — o teste não cobriria as duas")
    marca = "TERMINOLOGIA (regra dura)"
    for i, system in enumerate(enviados, 1):
        assert marca in system, (
            f"o glossário não foi para o modelo na tentativa {i} de "
            f"{len(enviados)} — o calque volta por esse caminho")


def test_full_house_nao_e_cheio_de_nada():
    """Caso real (02/08): '7 cheio de 2' numa análise — tradução literal de
    'sevens full of twos'. Em BR é 'full de 7 com 2'."""
    assert "'X cheio de Y'" in TERMOS_REGRA
    assert _depois_de_proibidos("'X cheio de Y'")
    probs = judge_answer("Ele tinha 7 cheio de 2, o full máximo ali.")
    assert any("cheio de" in p for p in probs)
    # 'A cheia de' e plural também são o mesmo calque
    assert any("cheio de" in p for p in judge_answer(
        "Você mostrou A cheia de K no showdown."))


def test_cheio_de_legitimo_nao_dispara():
    """'board cheio de draws' é português normal — só rank antes acusa."""
    assert not any("cheio de" in p for p in judge_answer(
        "O board estava cheio de draws e o pote cheio de fichas."))


def test_check_atras_e_check_behind():
    """Dono (02/08): 'check atrás normalmente se fala check behind'."""
    assert "'check atrás'" in TERMOS_REGRA
    assert _depois_de_proibidos("'check atrás'")
    probs = judge_answer("🟡 Deu check atrás no turn com o full.")
    assert any("check atrás" in p for p in probs)
    assert not any("calque" in p for p in judge_answer(
        "✅ Deu check behind no turn — linha padrão."))
