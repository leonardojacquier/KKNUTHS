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
                                   extrair_saberes, validar)

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


def test_o_modelo_nao_recebe_identidade(monkeypatch):
    """O que ele não recebe não vaza — medido no que SAI para a API.

    Antes isto recortava o texto-fonte de `main` entre `corpo =` e `try:` e
    procurava a palavra `user_id` lá dentro. Não vê nada montado por
    variável, nem identidade que entre pelo `tema`, pelo system prompt ou
    por outro campo da nota. Aqui o cliente é falso e grava o payload
    inteiro; a busca é pelos VALORES de identidade, não pelos nomes dos
    campos.
    """
    import destilar_conhecimento as d

    enviados: list[dict] = []

    class _Resp:
        stop_reason = "end_turn"
        content = [type("B", (), {"type": "text", "text": "[]"})()]
        usage = None

    class _Msgs:
        def create(self, **kw):
            enviados.append(kw)
            return _Resp()

    class _Cli:
        messages = _Msgs()

    # duas notas do MESMO tema e de alunos DIFERENTES: é o que faz o tema
    # sobreviver ao filtro de "2+ alunos" e chegar à chamada
    notas = [
        # as duas precisam cair no MESMO grupo: `agrupar_por_tema` agrupa por
        # palavra-chave do TEXTO da nota, não por um campo de tema
        {"user_id": "u-8f3c-SEGREDO", "kind": "bb_defense",
         "note": "folda demais o big blind contra open de 2bb",
         "created_at": "2026-08-01T20:00:00Z"},
        {"user_id": "u-99a1-SEGREDO", "kind": "bb_defense",
         "note": "defende o blind larguíssimo e paga caro no flop",
         "created_at": "2026-08-02T20:00:00Z"},
    ]

    class _T:
        def __init__(self, dados):
            self._d = dados

        def select(self, *_a, **_k):
            return self

        def order(self, *_a, **_k):
            return self

        def limit(self, *_a):
            return self

        def execute(self):
            return type("R", (), {"data": self._d})()

    class _C:
        @staticmethod
        def table(nome):
            return _T(notas if nome == "player_notes"
                      else [{"username": "ricardo_farah"},
                            {"username": "odilon"}])

    class _Repo:
        enabled = True
        client = _C()

        @staticmethod
        def listar_conhecimento(**_k):
            return []

        def __getattr__(self, _n):
            return lambda *a, **k: None

    class _Cfg:
        anthropic_api_key = "sk-teste"
        cheap_model = "modelo-barato"

        def __getattr__(self, _n):
            return None

    monkeypatch.setattr(d, "get_repository", lambda: _Repo())
    monkeypatch.setattr(d, "get_settings", lambda: _Cfg())

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda **_k: _Cli())

    d.main()

    assert enviados, (
        "o main não chegou a chamar o modelo — o teste não mediu nada")

    identidade = ["u-8f3c-SEGREDO", "u-99a1-SEGREDO", "ricardo_farah",
                  "odilon", "6921203436", "6104620007"]
    for chamada in enviados:
        texto = repr(chamada)
        for pedaco in identidade:
            assert pedaco not in texto, (
                f"identidade {pedaco!r} foi para o modelo: {texto[:400]}")
        # e a nota EM SI tem que ir, senão o teste passaria por não enviar nada
        assert "folda demais o big blind" in texto or "defende o blind" in texto, (
            "nenhuma nota chegou ao modelo — o teste não mediu nada")


# ---- as três falhas REAIS da 1ª rodada na VPS (07/08) ----
# Os seis temas morreram no parse, um a um, cada um pagando uma chamada.
# Cada teste abaixo é um dos erros que apareceram no terminal.

def test_json_cortado_no_teto_de_tokens():
    """"Unterminated string starting at: line 22 column 5" — max_tokens=600
    cortava a resposta no meio da string. Não dá erro de API: dá JSON
    quebrado, e o custo já foi pago."""
    from destilar_conhecimento import MAX_TOKENS, extrair_saberes

    cortado = '{"titulo": "Overpair curto", "gatilho": "SB 12bb", "texto": "O erro é fol'
    assert extrair_saberes(cortado) == []       # ilegível, e assumido como tal
    assert MAX_TOKENS >= 1200, "teto baixo demais volta a cortar"


def test_preambulo_antes_do_json():
    """"Extra data: line 6 column 1 (char 22)" — o modelo escreveu prosa
    antes/depois do objeto."""
    from destilar_conhecimento import extrair_saberes

    sujo = ('Claro! Aqui está o padrão destilado:\n\n'
            '{"titulo": "T", "gatilho": "G", "texto": "X", "vale": true}\n\n'
            'Espero que ajude!')
    assert extrair_saberes(sujo) == [{"titulo": "T", "gatilho": "G",
                                      "texto": "X", "vale": True}]


def test_cerca_de_codigo():
    from destilar_conhecimento import extrair_saberes

    for fence in ('```json\n{"vale": true}\n```', '```\n{"vale": true}\n```'):
        assert extrair_saberes(fence) == [{"vale": True}]


def test_lixo_total_nao_explode():
    from destilar_conhecimento import extrair_saberes

    for lixo in ("", None, "não consegui", "[1,2,3]", "{quebrado"):
        assert extrair_saberes(lixo) == []


def test_para_de_gastar_quando_a_falha_e_sistemica():
    """Na 1ª rodada, seis temas falharam em sequência e cada um pagou uma
    chamada. Dois ilegíveis seguidos não é azar — é o formato."""
    import inspect

    import destilar_conhecimento as d

    fonte = inspect.getsource(d.main)
    assert "if ilegiveis >= 2:" in fonte
    assert "ilegiveis = 0" in fonte, "o contador tem que zerar no sucesso"
    # e a resposta crua vai pro log: sem ela o diagnóstico foi adivinhação
    assert "resposta crua" in fonte
    assert "stop_reason" in fonte, "não distingue corte de tokens de lixo"


def test_array_de_padroes_e_o_formato_certo():
    """Resposta REAL da VPS (07/08): o modelo devolveu um array e minha 1ª
    versão jogou fora achando que era erro de formato. O erro era meu — o
    tema '3-bet' junta notas de 4 alunos e contém mesmo vários padrões."""
    real = ('```json\n[\n  {\n    "titulo": "Fold marginal OOP vs 3-bet",\n'
            '    "gatilho": "Mão marginal fora de posição contra 3-bet",\n'
            '    "texto": "Limp-call OOP cria spots impossíveis; 3-bet ou '
            'fold. Custa ~4bb.",\n    "categoria": "preflop",\n'
            '    "ev_bb": -4.0,\n    "vale": true\n  },\n  {\n'
            '    "titulo": "Call em vez de jam com 10bb",\n'
            '    "gatilho": "Stack ~10-12bb no SB",\n'
            '    "texto": "Pagar open com 10bb perde fold equity; jam. '
            'Custa 2bb.",\n    "categoria": "preflop",\n'
            '    "ev_bb": -2.0,\n    "vale": true\n  }\n]\n```')
    saberes = extrair_saberes(real)
    assert len(saberes) == 2
    assert saberes[0]["titulo"] == "Fold marginal OOP vs 3-bet"
    assert saberes[1]["ev_bb"] == -2.0
    # e os dois passam no validador
    for s in saberes:
        assert validar(s, ["Ricardo Farah", "Leo"], alunos=4) is not None


def test_array_cortado_aproveita_os_que_fecharam():
    """4 padrões e o 4º cortado no teto: jogar tudo fora perderia 3 bons já
    pagos."""
    cortado = ('[{"titulo": "A", "gatilho": "g", "texto": "t", "vale": true},'
               '{"titulo": "B", "gatilho": "g", "texto": "t", "vale": true},'
               '{"titulo": "C", "gatilho": "g", "texto": "inacaba')
    s = extrair_saberes(cortado)
    assert [x["titulo"] for x in s] == ["A", "B"]


def test_chave_dentro_de_texto_nao_quebra_a_varredura():
    """Texto de poker pode conter '{' — a contagem tem que ignorar o que
    está dentro de string, senão parte os objetos no lugar errado."""
    tricky = ('[{"titulo": "A", "gatilho": "g", "texto": "use {x} assim", '
              '"vale": true}, {"titulo": "B", "gatilho": "g", '
              '"texto": "aspas \\" no meio", "vale": true}, {"cortado')
    s = extrair_saberes(tricky)
    assert [x["titulo"] for x in s] == ["A", "B"]
    assert s[0]["texto"] == "use {x} assim"


def test_um_tema_fertil_nao_enche_a_memoria_sozinho():
    import inspect

    import destilar_conhecimento as d

    assert d.MAX_POR_TEMA <= 3
    assert "brutos[:MAX_POR_TEMA]" in inspect.getsource(d.main)


def test_prompt_pede_array():
    from destilar_conhecimento import _PROMPT

    assert "array JSON" in _PROMPT and "MAIS DE UM padrão" in _PROMPT
    assert "Sem padrão claro: []" in _PROMPT


def test_estatistica_de_jogador_nao_vira_padrao_coletivo():
    """Achado da 1ª rodada boa (07/08): entrou "VPIP extremo (~90%+)" como
    saber global. Dois defeitos num só:

    (a) erro de CATEGORIA — VPIP descreve uma pessoa, não uma situação; o
        gatilho tem que ser um spot reconhecível na mão à frente;
    (b) o número era LIXO conhecido — as notas gravaram "VPIP 93%" de
        amostras de replay/print escolhidas a dedo, exatamente o que o
        produto se recusa a mostrar ao aluno ("VPIP 94% pra quem joga 26%").
    """
    from destilar_conhecimento import sobre_perfil_individual

    ruim = {"vale": True,
            "titulo": "VPIP extremo (~90%+) com seleção invertida",
            "gatilho": "Sessão com VPIP >90% em amostra >40 mãos",
            "texto": "Entra em quase tudo (VPIP 93%+) mas folda premium. "
                     "Reduzir VPIP para ~25-30%. Economiza ~3-4bb por órbita.",
            "categoria": "preflop", "ev_bb": -3.5}
    assert validar(ruim, NOMES, alunos=5) is None

    for t, g in (("VPIP alto", "qualquer"), ("X", "jogador com PFR 19%"),
                 ("AF baixo demais", "pós-flop"), ("X", "3-bet 6% em 48 opps")):
        assert sobre_perfil_individual(t, g), f"{t} / {g}"


def test_padrao_de_spot_continua_passando():
    """O filtro não pode comer os bons: citar a estatística como CONTEXTO no
    texto é legítimo — o que não pode é ela ser o gatilho."""
    from destilar_conhecimento import sobre_perfil_individual

    bom = {"vale": True,
           "titulo": "Flat de mãos fortes em vez de 3-bet com stack médio",
           "gatilho": "ATs, AJ, KQ com ~28bb flatando opens",
           "texto": "Flatar ATs com 28bb (perfil tight-passive, 3-bet só 7%) "
                    "deixa dinheiro na mesa. 3-betar ganha ~1bb/100.",
           "categoria": "preflop", "ev_bb": -0.9}
    assert validar(bom, NOMES, alunos=5) is not None
    assert not sobre_perfil_individual(bom["titulo"], bom["gatilho"])

    # e o gatilho de spot puro segue passando
    assert not sobre_perfil_individual("Call OOP com especulativas",
                                       "SB/BB pagando 3-bet com QJs")


def test_prompt_proibe_padrao_de_estatistica():
    from destilar_conhecimento import _PROMPT

    assert "VPIP" in _PROMPT and "descreve uma PESSOA" in _PROMPT
