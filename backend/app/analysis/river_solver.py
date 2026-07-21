"""Solver pós-flop — CFR+ range-vs-range MULTI-STREET (chance amostrada).

River: showdown determinístico — equilíbrio exato do sub-jogo.
Turn: modela as APOSTAS DO RIVER de verdade — quando a street fecha
  (call sem all-in, ou check-check), uma carta de river é sorteada por
  iteração (MCCFR com chance sampling) e o jogo continua com nova rodada
  de apostas naquele river; cada river tem sua própria estratégia.
Flop: idem para o turn (apostas do flop E do turn modeladas); o river do
  flop é fechado por equity realizada (premissa declarada) — três níveis
  de chance explodiriam o custo sem mudar o veredito da street atual.
All-in antes do river: fecha por equity realizada nos runouts (correto —
  não há mais apostas por vir).

Árvore por street (uma raise por street — bet -> jam):
  OOP: check | bet(frações do pote ATUAL) | jam
  IP após check: check | bet | jam
  Contra bet: fold | call | jam        Contra jam: fold | call

Convenção de EV: fichas ganhas em relação ao início do solve (pot0 no meio).
"""
from __future__ import annotations

import itertools
import random

import numpy as np

from app.analysis.ranges import expand_combos, parse_range

_CACHE: dict[str, dict] = {}
_MAX_COMBOS = 900        # river (exato)
_MAX_COMBOS_DRAW = 420   # turn/flop (cada matchup custa runouts x avaliações)
_FLOP_RUNOUTS = 80       # amostra de turns+rivers no flop (seed fixa)

_RANKS = "23456789TJQKA"
_DECK = [r + s for r in _RANKS for s in "cdhs"]


def _strengths(combos: list[tuple[str, str]], board: list[str]) -> np.ndarray:
    from treys import Card, Evaluator

    ev = Evaluator()
    b = [Card.new(c) for c in board]
    return np.array(
        [ev.evaluate(b, [Card.new(a), Card.new(bb)]) for a, bb in combos], dtype=np.int32
    )


def _equity_matrix(oop: list[tuple[str, str]], ip: list[tuple[str, str]],
                   board: list[str]) -> np.ndarray:
    """E[i,j] = fração do pote do combo OOP i vs IP j realizada nos runouts.

    Turn (4 cartas): enumera TODOS os rivers — exato. Flop (3): amostra
    _FLOP_RUNOUTS pares turn+river com seed fixa (mesmo spot = mesmo
    resultado, requisito de consistência do coach)."""
    from treys import Card, Evaluator

    ev = Evaluator()
    dead = set(board)
    left = [c for c in _DECK if c not in dead]
    if len(board) == 4:
        runouts = [(c,) for c in left]
    else:
        pairs = list(itertools.combinations(left, 2))
        rng = random.Random(20260720)
        runouts = (rng.sample(pairs, _FLOP_RUNOUTS)
                   if len(pairs) > _FLOP_RUNOUTS else pairs)

    n_o, n_i = len(oop), len(ip)
    W = np.zeros((n_o, n_i))
    C = np.zeros((n_o, n_i))
    t_oop = [(Card.new(a), Card.new(b)) for a, b in oop]
    t_ip = [(Card.new(a), Card.new(b)) for a, b in ip]
    for ro in runouts:
        ro_set = set(ro)
        full = [Card.new(c) for c in board + list(ro)]
        v_o = np.array([not (set(c) & ro_set) for c in oop])
        v_i = np.array([not (set(c) & ro_set) for c in ip])
        s_o = np.array([ev.evaluate(full, list(t)) if ok else 0
                        for t, ok in zip(t_oop, v_o)], dtype=np.int32)
        s_i = np.array([ev.evaluate(full, list(t)) if ok else 0
                        for t, ok in zip(t_ip, v_i)], dtype=np.int32)
        R = (s_o[:, None] < s_i[None, :]) + 0.5 * (s_o[:, None] == s_i[None, :])
        V = v_o[:, None] & v_i[None, :]
        W += V * R
        C += V
    return W / np.maximum(C, 1.0)


class _Node:
    __slots__ = ("key", "actor", "n_actions", "regret", "strat_sum")

    def __init__(self, key: str, actor: int, n_actions: int, n_combos: int):
        self.key = key
        self.actor = actor
        self.n_actions = n_actions
        self.regret = np.zeros((n_combos, n_actions))
        self.strat_sum = np.zeros((n_combos, n_actions))

    def strategy(self) -> np.ndarray:
        pos = np.maximum(self.regret, 0.0)
        total = pos.sum(axis=1, keepdims=True)
        n = self.n_actions
        return np.where(total > 0, pos / np.where(total > 0, total, 1), 1.0 / n)

    def avg_strategy(self) -> np.ndarray:
        total = self.strat_sum.sum(axis=1, keepdims=True)
        n = self.n_actions
        return np.where(total > 0, self.strat_sum / np.where(total > 0, total, 1), 1.0 / n)


class RiverSolver:
    def __init__(
        self,
        board: list[str],
        oop_range: str,
        ip_range: str,
        pot: float,
        stack: float,
        bet_fracs: tuple[float, ...] = (0.5, 1.0),
    ):
        dead = set(board)
        self.oop_combos = expand_combos(parse_range(oop_range), dead)
        self.ip_combos = expand_combos(parse_range(ip_range), dead)
        if not self.oop_combos or not self.ip_combos:
            raise ValueError("range vazio dado o board")
        cap = _MAX_COMBOS if len(board) == 5 else _MAX_COMBOS_DRAW
        if len(self.oop_combos) > cap or len(self.ip_combos) > cap:
            raise ValueError("range grande demais para o solver; use um range mais estreito")

        self.pot, self.stack = float(pot), float(stack)
        self.bet_fracs = bet_fracs
        self.board0 = tuple(board)
        self._R_cache: dict[tuple, np.ndarray] = {}
        self._rng = random.Random(20260721)
        # máscaras de card removal por carta: combo NÃO contém a carta
        self._free = {}
        for side, combos in ((0, self.oop_combos), (1, self.ip_combos)):
            for c in _DECK:
                self._free[(side, c)] = np.array(
                    [c not in combo for combo in combos], dtype=np.float64)
        # R do board inicial (river usa direto; turn/flop usam nos terminais
        # de all-in — equity realizada, pois não há mais apostas por vir)
        self.R = self._R(self.board0)
        # M[i,j] = 1 se os combos não colidem em cartas
        self.M = np.array(
            [[0.0 if set(ci) & set(cj) else 1.0 for cj in self.ip_combos]
             for ci in self.oop_combos]
        )
        self.nodes: dict[str, _Node] = {}
        self._n = (len(self.oop_combos), len(self.ip_combos))

    # ------------------------------------------------------------------
    def _R(self, board: tuple) -> np.ndarray:
        """Matriz de resultado do showdown PARA UM BOARD (memoizada).

        5 cartas: exato (1/0.5/0). 3-4 cartas: equity realizada nos runouts
        — usada nos terminais de all-in e no fechamento do river do flop."""
        cached = self._R_cache.get(board)
        if cached is not None:
            return cached
        if len(board) == 5:
            s_oop = _strengths(self.oop_combos, list(board))
            s_ip = _strengths(self.ip_combos, list(board))
            R = (s_oop[:, None] < s_ip[None, :]).astype(np.float64)
            R += 0.5 * (s_oop[:, None] == s_ip[None, :])
        else:
            R = _equity_matrix(self.oop_combos, self.ip_combos, list(board))
        self._R_cache[board] = R
        return R

    def _node(self, key: str, actor: int, n_actions: int) -> _Node:
        node = self.nodes.get(key)
        if node is None:
            node = _Node(key, actor, n_actions, self._n[actor])
            self.nodes[key] = node
        return node

    def _bets(self, to_call: float, cur_pot: float, invested: float) -> list[float]:
        """Tamanhos de aposta disponíveis, fração do pote ATUAL do nó."""
        out = []
        for f in self.bet_fracs:
            b = round(cur_pot * f, 2)
            if to_call == 0 and 0 < b < self.stack - invested:
                out.append(b)
        return out

    def _showdown(self, inv: float, r_opp: np.ndarray, oop_view: bool,
                  board: tuple) -> np.ndarray:
        """EV de showdown com ambos investindo `inv`: net = R*(pot+inv) - (1-R)*inv."""
        R0 = self._R(board)
        R = R0 if oop_view else (1.0 - R0.T)
        M = self.M if oop_view else self.M.T
        win = self.pot + inv
        return (M * (R * win - (1.0 - R) * inv)) @ r_opp

    def _fold_ev(self, my_inv: float, r_opp: np.ndarray, oop_view: bool) -> np.ndarray:
        M = self.M if oop_view else self.M.T
        return (M * (-my_inv)) @ r_opp

    def _win_ev(self, opp_inv: float, r_opp: np.ndarray, oop_view: bool) -> np.ndarray:
        M = self.M if oop_view else self.M.T
        return (M * (self.pot + opp_inv)) @ r_opp

    # ------------------------------------------------------------------
    def _street_end(self, matched: float,
                    reach_a: np.ndarray, r_opp: np.ndarray,
                    oop_view: bool, board: tuple):
        """Fecha a street com ambos igualados em `matched`.

        - board de 5 (ou all-in, ou flop fechando o turn): showdown/equity
        - senão: NÓ DE CHANCE — sorteia a próxima carta (MCCFR) e o jogo
          continua com nova rodada de apostas naquele runout.
        Retorna (u_me_col, u_opp_add)."""
        all_in = matched >= self.stack - 1e-9
        # o flop modela flop+turn; o river dele fecha por EQUITY (o 3º nível
        # de chance custaria caro sem mudar o veredito da street atual)
        flop_turn_done = len(self.board0) == 3 and len(board) == 4
        if len(board) == 5 or all_in or flop_turn_done:
            R0 = self._R(board)
            R = R0 if oop_view else (1.0 - R0.T)
            R_opp = (1.0 - R0.T) if oop_view else R0
            M = self.M if oop_view else self.M.T
            M_opp = self.M.T if oop_view else self.M
            win = self.pot + matched
            u_me = (M * (R * win - (1.0 - R) * matched)) @ r_opp
            u_opp = (M_opp * (R_opp * win - (1.0 - R_opp) * matched)) @ reach_a
            return u_me, u_opp

        # chance amostrada: carta nova; combos que a seguram saem da jogada
        left = [c for c in _DECK if c not in board]
        card = self._rng.choice(left)
        new_board = board + (card,)
        me_side = 0 if oop_view else 1
        free_me = self._free[(me_side, card)]
        free_opp = self._free[(1 - me_side, card)]
        if oop_view:
            new_reaches = (reach_a * free_me, r_opp * free_opp)
        else:
            new_reaches = (r_opp * free_opp, reach_a * free_me)
        # a chave carrega o pote igualado + o runout: streets alcançadas com
        # potes diferentes são sub-jogos diferentes (não podem dividir nó)
        child_key = f"|p{matched:g}" + "".join("|" + c for c in new_board)
        u_oop_c, u_ip_c = self._cfr(
            child_key, 0, 0.0, (matched, matched),
            new_reaches, True, checked=False, board=new_board)
        # combos que seguram a carta não participam deste runout
        u_oop_c = u_oop_c * self._free[(0, card)]
        u_ip_c = u_ip_c * self._free[(1, card)]
        if oop_view:
            return u_oop_c, u_ip_c
        return u_ip_c, u_oop_c

    def _cfr(self, key: str, actor: int, to_call: float, inv: tuple[float, float],
             reaches: tuple[np.ndarray, np.ndarray], can_raise: bool,
             checked: bool = False, board: tuple | None = None):
        """Retorna (u_oop, u_ip) — utilidades contrafactuais por combo."""
        board = board or self.board0
        cur_pot = self.pot + inv[0] + inv[1]
        # ações disponíveis
        acts: list[tuple[str, float]] = []
        if to_call > 0:
            acts.append(("fold", 0.0))
            acts.append(("call", to_call))
            if can_raise and inv[actor] + to_call < self.stack:
                acts.append(("jam", self.stack - inv[actor]))
        else:
            acts.append(("check", 0.0))
            acts += [("bet", b) for b in self._bets(0, cur_pot, inv[actor])]
            if self.stack - inv[actor] > 0:
                acts.append(("jam", self.stack - inv[actor]))

        node = self._node(key, actor, len(acts))
        strat = node.strategy()
        r_me, r_opp = reaches[actor], reaches[1 - actor]
        oop_view = actor == 0

        u_me = np.zeros((self._n[actor], len(acts)))
        u_opp_total = np.zeros(self._n[1 - actor])

        for a_idx, (name, amount) in enumerate(acts):
            reach_a = r_me * strat[:, a_idx]
            if name == "fold":
                u_me[:, a_idx] = self._fold_ev(inv[actor], r_opp, oop_view)
                # oponente ganha pot + o que eu investi
                M_opp = self.M.T if oop_view else self.M
                u_opp = (M_opp * (self.pot + inv[actor])) @ reach_a
                u_opp_total += u_opp
            elif name == "call" or (name == "check" and checked):
                # street fechou (call, ou check depois de check): showdown,
                # equity de all-in ou CHANCE da próxima street
                matched = inv[actor] + (to_call if name == "call" else 0.0)
                u_col, u_opp = self._street_end(matched, reach_a, r_opp,
                                               oop_view, board)
                u_me[:, a_idx] = u_col
                u_opp_total += u_opp
            else:
                # nó interno: check (primeiro), bet ou jam
                new_inv = list(inv)
                new_to_call = 0.0
                if name in ("bet", "jam"):
                    new_inv[actor] = (inv[actor] + amount if name == "bet"
                                      else self.stack)
                    new_to_call = new_inv[actor] - inv[1 - actor]
                suffix = "x" if name == "check" else ("j" if name == "jam" else f"b{amount:g}")
                child_key = key + suffix
                if actor == 0:
                    new_reaches = (reach_a, reaches[1])
                else:
                    new_reaches = (reaches[0], reach_a)
                u_oop_c, u_ip_c = self._cfr(
                    child_key, 1 - actor, new_to_call, tuple(new_inv),
                    new_reaches, can_raise and name != "jam",
                    checked=(name == "check"), board=board,
                )
                u_me[:, a_idx] = u_oop_c if oop_view else u_ip_c
                u_opp_total += u_ip_c if oop_view else u_oop_c

        ev_me = (strat * u_me).sum(axis=1)
        # CFR+: regrets nunca negativos
        node.regret = np.maximum(node.regret + (u_me - ev_me[:, None]), 0.0)
        node.strat_sum += r_me[:, None] * strat

        if oop_view:
            return ev_me, u_opp_total
        return u_opp_total, ev_me

    def solve(self, iterations: int = 400) -> "RiverSolver":
        # multi-street (chance amostrada): mais iterações pros nós fundos
        if len(self.board0) < 5:
            iterations = max(iterations, 600)
        r0 = np.ones(self._n[0])
        r1 = np.ones(self._n[1])
        for _ in range(iterations):
            self._cfr("|", 0, 0.0, (0.0, 0.0), (r0, r1), True)
        return self

    # ------------------------------------------------------------------
    def summary(self, player: str = "oop", top: int = 4) -> dict:
        """Estratégia média na raiz do jogador: frequência de cada ação no range
        + exemplos de mãos que mais tomam cada ação."""
        idx = 0 if player == "oop" else 1
        combos = self.oop_combos if idx == 0 else self.ip_combos
        # raiz do OOP = "|"; raiz do IP = após check do OOP
        key = "|" if idx == 0 else "|x"
        node = self.nodes.get(key)
        if node is None:
            raise ValueError("nó raiz não resolvido")
        strat = node.avg_strategy()

        root_bets = self._bets(0, self.pot, 0.0)
        acts = ["check"] + [f"bet {b:g}" for b in root_bets] + ["jam"]

        out = {"player": player, "pot": self.pot, "stack": self.stack, "actions": {}}
        weights = strat.mean(axis=0)
        for a_idx, name in enumerate(acts[: node.n_actions]):
            freq = float(strat[:, a_idx].mean())
            best = np.argsort(-strat[:, a_idx])[:top]
            out["actions"][name] = {
                "freq_pct": round(freq * 100, 1),
                "exemplos": ["".join(combos[i]) for i in best],
            }
        _ = weights
        return out


def solve_river(
    board: list[str], oop_range: str, ip_range: str,
    pot: float, stack: float, player: str = "oop",
    iterations: int = 400,
) -> dict:
    """Interface (e tool do agente): equilíbrio da street atual (flop, turn
    ou river). River = showdown exato; turn = equity realizada em todos os
    rivers; flop = equity realizada em runouts amostrados."""
    if len(board) not in (3, 4, 5):
        raise ValueError(
            f"solve exige board de 3, 4 ou 5 cartas (recebi {len(board)})"
        )
    key = f"{'/'.join(sorted(board))}|{oop_range}|{ip_range}|{pot}|{stack}|{player}"
    if key in _CACHE:
        return _CACHE[key]
    solver = RiverSolver(board, oop_range, ip_range, pot, stack).solve(iterations)
    result = solver.summary(player)
    notas = {
        5: "equilíbrio CFR+ do sub-jogo de river (showdown exato)",
        4: "equilíbrio CFR+ do TURN modelando as APOSTAS do river "
           "(chance amostrada — cada river tem estratégia própria)",
        3: "equilíbrio CFR+ do FLOP modelando as apostas de flop E turn; "
           "o river fecha por equity realizada (premissa declarada)",
    }
    result["nota"] = (notas[len(board)]
                      + "; sizings 50%/100%/all-in, uma raise no máximo")
    _CACHE[key] = result
    return result


# alias semântico: o mesmo solver serve flop/turn/river
solve_spot = solve_river
