"""Print com o nível em FICHAS e a mesa em BB não pode zerar a mão.

Caso real — 29/07 19:09, primeira mão do Antônio (usuário novo). A sala
mostrava '15000/30000' no cabeçalho e os stacks na mesa em bb (17.4, 66.6,
28.5...; pote 10.1). A visão transcreveu os dois literalmente. Tudo lá
embaixo divide por big_blind, então 17.4/30000 = 0.0: o coach recebeu stack
0, pote 0 e aposta 0, e respondeu pedindo ao aluno o stack efetivo — que
estava na foto que ele acabara de mandar.
"""
from app.agent import analyzer
from app.agent.llm import _coerir_unidades, _snapshot_to_canonical
from app.models.canonical import CanonicalHand, HandFormat, PlayerSeat, Stakes


def _antonio() -> dict:
    """O JSON que a visão devolveu de fato naquele print."""
    return {
        "site": "PPPoker",
        "format": "tournament",
        "hero_name": "MajorAntony",
        "hero_cards": ["9s", "9d"],
        "blinds": {"small_blind": 15000, "big_blind": 30000, "ante": 4000},
        "players": [
            {"seat": 1, "name": "Dannumber3", "stack": 66.6},
            {"seat": 2, "name": "SassyMate", "stack": 28.5},
            {"seat": 3, "name": "zorritoaguir", "stack": 16.6},
            {"seat": 4, "name": "MajorAntony", "stack": 17.4},
            {"seat": 5, "name": "Mongolona", "stack": 23.1, "position": "BTN"},
        ],
        "actions": {"preflop": [
            {"actor": "MajorAntony", "action": "bet", "amount": 0.5},
            {"actor": "zorritoaguir", "action": "bet", "amount": 1},
            {"actor": "Mongolona", "action": "raise", "amount": 6, "to_amount": 6},
        ]},
        "total_pot": 10.1,
    }


def test_o_print_do_antonio_nao_vira_uma_mesa_de_zeros():
    mao = _snapshot_to_canonical(_antonio(), fingerprint="e6ee00c6cd73")
    ctx = analyzer.analyze_hand(mao)
    assert ctx["hero_stack_bb"] == 17.4, "o stack estava no print o tempo todo"
    assert ctx["effective_bb"] == 17.4, "efetivo = min(herói, maior vilão)"
    assert ctx["pot_total"] > 0


def test_blinds_em_fichas_com_stacks_em_bb_sao_convertidos():
    stakes = Stakes(small_blind=15000, big_blind=30000, ante=4000)
    jogadores = [PlayerSeat(seat=1, name="a", stack=17.4),
                 PlayerSeat(seat=2, name="b", stack=66.6)]
    assert _coerir_unidades(stakes, jogadores) is True
    assert stakes.big_blind == 1.0
    assert stakes.small_blind == 0.5
    assert round(stakes.ante, 3) == 0.133


def test_torneio_normal_em_fichas_fica_intocado():
    """Mesma unidade dos dois lados: não há nada a consertar."""
    stakes = Stakes(small_blind=15000, big_blind=30000, ante=4000)
    jogadores = [PlayerSeat(seat=1, name="a", stack=522000)]
    assert _coerir_unidades(stakes, jogadores) is False
    assert stakes.big_blind == 30000


def test_cash_em_dolar_fica_intocado():
    """0.10/0.25 com stack 25.00 — o maior stack é maior que o bb, tudo certo."""
    stakes = Stakes(small_blind=0.10, big_blind=0.25)
    jogadores = [PlayerSeat(seat=1, name="a", stack=25.0)]
    assert _coerir_unidades(stakes, jogadores) is False
    assert stakes.big_blind == 0.25


def test_sem_jogador_ou_sem_blind_nao_tenta_adivinhar():
    s1 = Stakes(small_blind=15000, big_blind=30000)
    assert _coerir_unidades(s1, []) is False
    s2 = Stakes(small_blind=0, big_blind=0)
    assert _coerir_unidades(s2, [PlayerSeat(seat=1, name="a", stack=17.4)]) is False


def test_stack_zerado_de_verdade_nao_dispara_a_correcao():
    """Jogador eliminado com 0 fichas não é sinal de escala errada."""
    stakes = Stakes(small_blind=15000, big_blind=30000)
    jogadores = [PlayerSeat(seat=1, name="a", stack=0),
                 PlayerSeat(seat=2, name="b", stack=480000)]
    assert _coerir_unidades(stakes, jogadores) is False
    assert stakes.big_blind == 30000


def test_escala_furada_avisa_o_coach_em_vez_de_entregar_0ponto0():
    """Segunda linha de defesa, para fonte que não passa pela visão: 0.0bb
    com ficha na mesa é escala errada, e o coach precisa saber disso — senão
    raciocina sobre um spot de stack zero que não existe."""
    mao = CanonicalHand(
        hand_id="x", site="PPPoker", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=15000, big_blind=30000),
        hero="h", hero_cards=["9s", "9d"],
        players=[PlayerSeat(seat=1, name="h", stack=17.4, is_hero=True),
                 PlayerSeat(seat=2, name="v", stack=66.6)],
    )
    ctx = analyzer.analyze_hand(mao)
    assert "stacks_ilegiveis" in ctx
    assert "peça ao aluno" in ctx["stacks_ilegiveis"]


def test_mao_saudavel_nao_carrega_o_aviso():
    mao = CanonicalHand(
        hand_id="x", site="PPPoker", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=15000, big_blind=30000),
        hero="h", hero_cards=["9s", "9d"],
        players=[PlayerSeat(seat=1, name="h", stack=522000, is_hero=True),
                 PlayerSeat(seat=2, name="v", stack=998000)],
    )
    assert "stacks_ilegiveis" not in analyzer.analyze_hand(mao)


def test_a_visao_e_instruida_a_devolver_uma_unidade_so():
    """A guarda conserta o estrago; o prompt evita que ele aconteça."""
    from app.agent.llm import _VISION_PROMPT

    assert "UNIDADE" in _VISION_PROMPT
    assert "MESMA unidade" in _VISION_PROMPT


def test_pote_lido_na_tela_vale_mais_que_a_soma_das_acoes():
    """Print de meio de mão não mostra a linha inteira: a soma das ações é um
    piso. No print do Antônio a tela dizia 10.1 e a soma dava 7.5 — e é o
    pote que define o preço da decisão."""
    mao = _snapshot_to_canonical(_antonio(), fingerprint="e6ee00c6cd73")
    ctx = analyzer.analyze_hand(mao)
    assert ctx["pot_total"] < 10.1, "a soma das ações visíveis é menor"
    assert ctx["pot_na_tela"] == 10.1
    assert "pot odds" in ctx["pot_na_tela_nota"]


def test_mao_fechada_de_hand_history_nao_ganha_pote_paralelo():
    """Só snapshot de imagem — .txt tem a linha toda, a soma é a verdade."""
    mao = _snapshot_to_canonical(_antonio(), fingerprint="x")
    mao.source_format = "text"
    assert "pot_na_tela" not in analyzer.analyze_hand(mao)


def test_pote_lido_menor_que_a_soma_e_erro_de_leitura_e_e_ignorado():
    dados = _antonio()
    dados["total_pot"] = 2.0
    ctx = analyzer.analyze_hand(_snapshot_to_canonical(dados, fingerprint="y"))
    assert "pot_na_tela" not in ctx, "mão não perde ficha; a soma manda"


def _mesa(bb, stacks, **kw):
    return CanonicalHand(
        hand_id="x", site="PPPoker", format=HandFormat.TOURNAMENT,
        stakes=Stakes(small_blind=bb / 2 if bb else 0, big_blind=bb),
        hero="h", hero_cards=["9s", "9d"],
        players=[PlayerSeat(seat=i + 1, name=f"p{i}", stack=s, is_hero=(i == 0))
                 for i, s in enumerate(stacks)], **kw)


def test_big_blind_zero_nao_vira_stack_de_98mil_bb():
    """Caso real (09/07, print de GGPoker): o nível não foi lido, big_blind
    saiu 0, e `bb = big_blind or 1` fez 98.331 fichas virarem '98331bb'. Um
    número inventado é pior que campo vazio — o coach raciocina em cima."""
    ctx = analyzer.analyze_hand(_mesa(0, [98331, 54000, 31000]))
    assert ctx["hero_stack_bb"] is None
    assert ctx["effective_bb"] is None
    assert ctx["stacks_bb"] == {}
    assert "big blind não foi lido" in ctx["stacks_ilegiveis"]


def test_mesa_com_o_mais_fundo_abaixo_de_2bb_e_escala_furada():
    """Caso real (09/07, cash): bb 200 com stacks 244.3 e 95.7 — 1.2bb no
    mais fundo. Impossível: quem postou o blind já tem 1bb."""
    ctx = analyzer.analyze_hand(_mesa(200, [95.7, 244.3]))
    assert "stacks_ilegiveis" in ctx
    assert "escala inconsistente" in ctx["stacks_ilegiveis"]
    assert ctx["hero_stack_bb"] is None


def test_mesa_de_stack_curto_de_verdade_passa():
    """4bb no mais fundo é hyper turbo real, não defeito de leitura."""
    ctx = analyzer.analyze_hand(_mesa(1000, [2500, 4000, 3100]))
    assert "stacks_ilegiveis" not in ctx
    assert ctx["hero_stack_bb"] == 2.5


def test_mesa_saudavel_mantem_os_numeros():
    ctx = analyzer.analyze_hand(_mesa(2400, [188467, 90000, 42000]))
    assert "stacks_ilegiveis" not in ctx
    assert ctx["hero_stack_bb"] == 78.5
    assert ctx["stacks_bb"]
