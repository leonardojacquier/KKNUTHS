"""SPOT PÓS-FLOP a partir da mão real — pra parar de interrogar o aluno.

Defeito que motivou (palavras dele): "não gera a merda dos gráficos de EV,
somente de all-in". O motor pós-flop existia e funcionava; o que faltava era
a PORTA. O coach tinha uma ferramenta que exigia board, range do OOP, range
do IP, pote e stack — e, sem saber esses valores, fazia o que o modelo faz
quando falta argumento: perguntava. Duas vezes seguidas o aluno respondeu à
pergunta e mesmo assim não veio gráfico nenhum.

Aqui a mão que está na conversa vira o spot sozinha: board da street, pote
acumulado, stack efetivo, quem age primeiro (esse é o OOP, por definição da
ordem pós-flop) e o range de cada um a partir da POSIÇÃO e da ação pré-flop.

As premissas saem junto, nomeadas, porque range atribuído é suposição — e
suposição que não se declara vira alucinação.
"""
from __future__ import annotations

from app.analysis.pushfold import HAND_RANKING
from app.models.canonical import ActionType, CanonicalHand, StreetName

_ORDEM = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN,
          StreetName.RIVER]
_NOME = {StreetName.FLOP: "flop", StreetName.TURN: "turn",
         StreetName.RIVER: "river"}

# teto do solver (river_solver: 420 combos no flop/turn, 900 no river)
_CAP = {3: 300, 4: 360, 5: 700}

# quem PAGA um open fora da BB entra apertado; a BB defende muito mais largo
# (preço melhor e já tem dinheiro no pote). Referência, não lei.
FLAT_CALL_RANGE = "22+, A2s+, KTs+, QTs+, JTs, ATo+, KQo"
BB_DEFEND_RANGE = ("22+, A2s+, K2s+, Q6s+, J7s+, T7s+, 96s+, 85s+, 75s+, "
                   "64s+, 54s, A2o+, K8o+, Q9o+, J9o+, T9o, 98o")
LIMP_RANGE = "22+, A2s+, K5s+, Q8s+, J8s+, T8s+, 97s+, 87s, A7o+, KTo+, QTo+, JTo"


def _apertar(notacao: str, cap: int) -> tuple[str, int]:
    """Corta o range pelas mãos MAIS FRACAS até caber no teto do solver.

    Truncar é honesto (o range vira 'a parte forte do range'); estourar o
    teto faria o solver recusar e o gráfico simplesmente não sairia — que é
    exatamente o sintoma que o aluno reclamou."""
    from app.analysis.ranges import expand_combos, parse_range

    maos = parse_range(notacao)
    if not maos:
        return notacao, 0
    fortes = sorted(maos, key=lambda h: HAND_RANKING.index(h)
                    if h in HAND_RANKING else 999)
    while fortes and len(expand_combos(fortes)) > cap:
        fortes.pop()
    return ", ".join(fortes), len(expand_combos(fortes))


def _contribs(street) -> dict[str, float]:
    """Quanto cada jogador colocou NESTA street (raise é 'até', não '+')."""
    c: dict[str, float] = {}
    for a in street.actions:
        add = a.amount
        if a.type == ActionType.RAISE and a.to_amount:
            add = a.to_amount - c.get(a.actor, 0.0)
        c[a.actor] = c.get(a.actor, 0.0) + max(0.0, add)
    return c


def _range_de(hand: CanonicalHand, nome: str, agressor: str | None) -> str:
    from app.analysis.ranges import OPEN_RANGES

    pos = next((p.position for p in hand.players if p.name == nome), None)
    pos = (pos or "MP").upper()
    if agressor is None:                       # ninguém aumentou: pote limpado
        return LIMP_RANGE
    if nome == agressor:
        return OPEN_RANGES.get(pos) or OPEN_RANGES["MP"]
    return BB_DEFEND_RANGE if pos == "BB" else FLAT_CALL_RANGE


def spot_da_mao(hand: CanonicalHand, street: str | None = None) -> dict:
    """Monta o spot pós-flop da mão em contexto. Devolve os argumentos do
    solver JÁ preenchidos + as premissas em português, ou {'error': ...}."""
    if hand is None:
        return {"error": "não achei a mão desta conversa"}
    bb = hand.stakes.big_blind or 0
    if bb <= 0:
        return {"error": "a mão não tem big blind lido — sem bb não dá conta"}

    alvo = None
    if street:
        s = str(street).strip().lower()
        alvo = next((k for k, v in _NOME.items() if v == s), None)
    posflop = [s for s in _ORDEM[1:]
               if hand.street(s) and hand.street(s).actions]
    if not posflop:
        return {"error": "esta mão não chegou ao flop — não há spot pós-flop"}
    if alvo and alvo not in posflop:
        return {"error": f"a mão não teve ação no {_NOME[alvo]}"}
    alvo = alvo or posflop[-1]

    # pote no INÍCIO da street + o que cada um já tinha investido
    pot_chips, investido = 0.0, {}
    for s in _ORDEM:
        if s == alvo:
            break
        st = hand.street(s)
        if not st:
            continue
        for nome, v in _contribs(st).items():
            investido[nome] = investido.get(nome, 0.0) + v
            pot_chips += v

    st = hand.street(alvo)
    board = list(st.board)
    if len(board) not in (3, 4, 5):
        # a street guarda só a carta nova em alguns parsers: remonta o board
        board = []
        for s in _ORDEM[1:]:
            b = hand.street(s).board if hand.street(s) else []
            for c in b or []:
                if c not in board:
                    board.append(c)
            if s == alvo:
                break
    if len(board) not in (3, 4, 5):
        return {"error": f"não consegui montar o board do {_NOME[alvo]}"}

    atores: list[str] = []
    for a in st.actions:
        if a.actor not in atores:
            atores.append(a.actor)
    if len(atores) != 2:
        return {"error": f"o {_NOME[alvo]} foi com {len(atores)} jogadores; "
                         "o solver de equilíbrio pós-flop é heads-up"}

    # ordem pós-flop: quem age primeiro está fora de posição. Por definição.
    oop, ip = atores[0], atores[1]
    if not hand.hero or hand.hero not in (oop, ip):
        return {"error": "o herói não está entre os dois jogadores da street"}
    lado = "oop" if hand.hero == oop else "ip"

    pre = hand.street(StreetName.PREFLOP)
    agressor = None
    for a in (pre.actions if pre else []):
        if a.type == ActionType.RAISE:
            agressor = a.actor
    if agressor not in (oop, ip):
        agressor = None

    cap = _CAP[len(board)]
    r_oop, n_oop = _apertar(_range_de(hand, oop, agressor), cap)
    r_ip, n_ip = _apertar(_range_de(hand, ip, agressor), cap)
    if not n_oop or not n_ip:
        return {"error": "não consegui montar os ranges deste spot"}

    stacks = {}
    for nome in (oop, ip):
        p = next((p for p in hand.players if p.name == nome), None)
        stacks[nome] = max(0.0, (p.stack if p else 0.0)
                           - investido.get(nome, 0.0))
    stack_bb = round(min(stacks.values()) / bb, 1)
    pot_bb = round(pot_chips / bb, 1)
    if stack_bb <= 0 or pot_bb <= 0:
        return {"error": "pote ou stack zerado nesta street — leitura da mão "
                         "incompleta pra rodar o equilíbrio"}

    def _pos(nome):
        return next((p.position for p in hand.players if p.name == nome), "?")

    return {
        "street": _NOME[alvo], "board": board,
        "oop_range": r_oop, "ip_range": r_ip,
        "pot": pot_bb, "stack": stack_bb, "player": lado,
        "oop": oop, "ip": ip, "oop_pos": _pos(oop), "ip_pos": _pos(ip),
        "combos": {"oop": n_oop, "ip": n_ip},
        "agressor_preflop": agressor,
        "premissas": [
            f"pote no início do {_NOME[alvo]}: {pot_bb:g}bb · stack efetivo "
            f"{stack_bb:g}bb",
            f"{oop} ({_pos(oop)}) age primeiro = fora de posição; "
            f"{ip} ({_pos(ip)}) em posição",
            (f"ranges de referência pela posição e pela ação pré-flop "
             f"({'quem abriu: ' + agressor if agressor else 'pote limpado'}) — "
             f"{n_oop} x {n_ip} combos, cortados nas mãos mais fracas pra "
             f"caber no solver"),
        ],
    }
