"""Frequência tirada de mão avulsa mede o gosto do aluno, não o jogo dele.

Caso real — 30/07 10:18. O coach disse ao Ricardo, no meio de uma análise:
"seu VPIP tá em 93,6% (em 47 mãos), joga MUITO lixo". O perfil no banco
dizia VPIP 94.3%, PFR 50.9%, rótulo LAG.

Aquilo foi calculado sobre 53 replays que ele MESMO escolheu mandar —
ninguém manda o replay de uma mão que largou no pré. O VPIP de verdade
dele, em 406.639 mãos, é 26%: ele colou o print das próprias stats na
ferramenta no mesmo dia, às 23:37, e o número não bateu com nada.
"""
from app.analysis.stats import (FONTES_COMPLETAS, MINIMO_PARA_PERFIL,
                                amostra_completa, compute_player_stats)
from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  PlayerSeat, Stakes, Street, StreetName)


def _mao(fonte: str, jogou: bool = True) -> CanonicalHand:
    acoes = [Action(actor="hero", type=ActionType.RAISE, amount=3, to_amount=3)] \
        if jogou else [Action(actor="hero", type=ActionType.FOLD, amount=0)]
    return CanonicalHand(
        hand_id="h", site="PPPoker", stakes=Stakes(small_blind=1, big_blind=2),
        hero="hero", hero_cards=["As", "Ks"], source_format=fonte,
        players=[PlayerSeat(seat=1, name="hero", stack=100, is_hero=True),
                 PlayerSeat(seat=2, name="vilao", stack=100)],
        streets=[Street(name=StreetName.PREFLOP, board=[], actions=acoes)])


def test_replay_avulso_nao_vira_perfil():
    """53 replays escolhidos a dedo davam VPIP 94% e rótulo LAG."""
    s = compute_player_stats([_mao("pppoker_replay") for _ in range(53)])
    assert s.hands == 0
    assert s.vpip == 0.0
    assert not s.publicavel
    assert s.detail["amostra_viesada"] is True
    assert s.detail["maos_fora_da_amostra"] == 53
    assert "avulsas" in s.label


def test_print_tambem_nao_vira_perfil():
    s = compute_player_stats([_mao("image") for _ in range(40)])
    assert not s.publicavel


def test_export_de_sessao_vira_perfil():
    """No .txt as mãos foldadas ESTÃO na amostra — aí a frequência vale."""
    maos = [_mao("txt", jogou=True) for _ in range(20)] \
        + [_mao("txt", jogou=False) for _ in range(20)]
    s = compute_player_stats(maos)
    assert s.hands == 40
    assert s.vpip == 50.0, "20 de 40 jogadas"
    assert s.publicavel


def test_amostra_pequena_nao_e_publicavel_mesmo_vindo_de_export():
    s = compute_player_stats([_mao("txt") for _ in range(MINIMO_PARA_PERFIL - 1)])
    assert s.hands == MINIMO_PARA_PERFIL - 1
    assert not s.publicavel


def test_mistura_conta_so_o_export():
    """O Ricardo tem replay; o Odilon tem .txt. Quem tiver os dois, vale o
    .txt e as avulsas ficam de fora da conta — não somam nem diluem."""
    maos = [_mao("txt", jogou=False) for _ in range(30)] \
        + [_mao("pppoker_replay", jogou=True) for _ in range(30)]
    s = compute_player_stats(maos)
    assert s.hands == 30
    assert s.vpip == 0.0, "as 30 avulsas jogadas não podem inflar o VPIP"
    assert s.publicavel
    assert s.detail["maos_fora_da_amostra"] == 30


def test_da_pra_pedir_a_conta_crua_de_proposito():
    """O filtro é o padrão, não uma prisão: quem quiser medir a amostra
    inteira (ex.: perfil de VILÃO num replay) passa o flag."""
    s = compute_player_stats([_mao("pppoker_replay") for _ in range(30)],
                             somente_amostra_completa=False)
    assert s.hands == 30
    assert s.vpip == 100.0


def test_amostra_completa_separa_por_fonte():
    todas = [_mao("txt"), _mao("csv"), _mao("image"), _mao("pppoker_replay"),
             _mao("suprema_replay"), _mao("phh")]
    assert len(amostra_completa(todas)) == 3
    assert "pppoker_replay" not in FONTES_COMPLETAS
    assert "image" not in FONTES_COMPLETAS


def test_o_coach_nao_recebe_perfil_nao_publicavel():
    """A regra tem que valer no ponto onde o dado ENCONTRA o modelo — senão
    o perfil errado volta a ser dito como fato no meio da análise."""
    import inspect

    from app.bot import processing

    fonte = inspect.getsource(processing._process_upload_inner)
    assert "stats.publicavel" in fonte
    assert fonte.index("stats.publicavel") < fonte.index("coach(structured")
