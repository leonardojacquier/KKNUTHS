"""Motor único de EV para QUALQUER all-in pré-flop.

Com stack curto (<=~20bb) toda decisão de torneio colapsa em all-in ou fold —
e todo all-in pré-flop é a MESMA conta: dinheiro morto no pote, quem ainda
pode pagar, e a equity contra o range de quem paga. Antes isso estava em dois
solvers de caso especial (SB vs BB, e open-shove); aqui é um nó só, com os
seis spots reais que aparecem numa mesa de 9:

  EMPURRAR                             PAGAR
  - open_shove : primeiro a agir       - call_shove : alguém empurrou
  - reshove    : sobre um open         - overcall   : empurrou e já pagaram
  - squeeze    : sobre open + call(s)

Fictitious play sobre a matriz de equity 169×169 (a mesma do jam/fold), com
uma estratégia por GRUPO de oponente (quem abriu, quem pagou na frente, quem
está atrás) — todos se ajustam até o equilíbrio.

PREMISSAS (vão na figura):
  - o primeiro que paga fecha a ação (sem overcall depois) — overcall é raro
    e a simplificação é o padrão em solvers de push/fold;
  - stacks efetivos iguais (o herói está curto e é coberto);
  - quem abriu paga o all-in com um subconjunto do próprio range de abertura;
  - ICM entra como bubble factor simétrico (perdas valem bf vezes mais).
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from app.analysis.jam_fold_solver import _matrix

_ITERS = 1500

_ORDEM = ["UTG", "UTG+1", "MP", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
_ALIAS = {"UTG+2": "MP", "MP+1": "LJ"}
_BLIND = {"SB": 0.5, "BB": 1.0}

# spots que o motor resolve
SPOTS = ("open_shove", "reshove", "squeeze", "call_shove", "overcall")


def available() -> bool:
    return _matrix() is not None


def _pos(p: str) -> str:
    p = _ALIAS.get((p or "").upper(), (p or "").upper())
    return p if p in _ORDEM else "MP"


def _atras_de(position: str) -> list[str]:
    return _ORDEM[_ORDEM.index(_pos(position)) + 1:]


def _post(p: str, ante: float) -> float:
    return ante + _BLIND.get(p, 0.0)


@lru_cache(maxsize=128)
def solve_spot(spot: str, hero_pos: str, stack_bb: float,
               ante_bb: float = 0.125, bf: float = 1.0,
               vilao_pos: str | None = None, open_bb: float = 2.2,
               pagaram: int = 0) -> dict | None:
    """Resolve o spot e ANEXA o EV contra foldar.

    ev_vs_fold sai daqui, num lugar só, porque o solver tem mais de um
    caminho de saída (o nó de pagar devolve antes do de empurrar) e a versão
    que só marcava um deles deixava o outro — justamente o call_shove do
    print — sem o campo. Derivar no fim vale para todos.
    """
    sol = _solve_spot(spot, hero_pos, stack_bb, ante_bb, bf, vilao_pos,
                      open_bb, pagaram)
    if sol is None:
        return None
    f = sol["fold_ev"]
    sol["ev_vs_fold"] = {h: round(v - f, 3) for h, v in sol["ev"].items()}
    return sol


def _solve_spot(spot: str, hero_pos: str, stack_bb: float,
                ante_bb: float = 0.125, bf: float = 1.0,
                vilao_pos: str | None = None, open_bb: float = 2.2,
                pagaram: int = 0) -> dict | None:
    """Equilíbrio e EV por mão de um all-in pré-flop.

    spot: open_shove | reshove | squeeze | call_shove | overcall
    hero_pos: posição do herói. vilao_pos: quem abriu (reshove/squeeze) ou
    quem empurrou (call_shove/overcall). open_bb: tamanho da abertura.
    pagaram: quantos já pagaram na frente (squeeze/overcall).

    Retorna {hands, acao (freq por mão), ev, fold_ev, acao_pct, atras,
    dead, premissas} ou None sem a matriz.
    """
    data = _matrix()
    if data is None or spot not in SPOTS:
        return None
    hands, E, W = data
    n = len(hands)

    hero = _pos(hero_pos)
    s = float(stack_bb)
    a = max(0.0, float(ante_bb))
    hero_post = _post(hero, a)
    antes_mesa = 9 * a
    peso = np.maximum(W.sum(axis=1), 1e-12)

    paga_node = spot in ("call_shove", "overcall")
    vil = _pos(vilao_pos) if vilao_pos else None

    # ---- quem ainda pode agir depois do herói ----
    if paga_node:
        # herói paga: só quem está atrás DELE pode entrar (overcall é
        # ignorado por premissa, então não há mais ninguém a temer)
        atras: list[str] = []
    else:
        atras = _atras_de(hero)
        if vil and vil in atras:          # quem abriu já agiu: sai da lista
            atras = [p for p in atras if p != vil]

    # ---- dinheiro morto no pote quando a decisão chega ----
    dead = 1.5 + antes_mesa - hero_post   # blinds+antes dos outros
    if spot in ("reshove", "squeeze"):
        dead += float(open_bb) - (_post(vil, a) if vil else 0.0)
    if spot in ("squeeze", "overcall"):
        dead += max(0, int(pagaram)) * float(open_bb)
    if paga_node:
        # o all-in de quem empurrou JÁ CONTÉM o blind/ante dele — somar o
        # post separadamente contava o mesmo dinheiro duas vezes (a validação
        # contra o solver heads-up acusou 0.42bb de erro por mão)
        dead += s - (_post(vil, a) if vil else 0.0)
        if spot == "overcall":
            dead += max(0, int(pagaram)) * (s - a)

    fold_ev = -hero_post * bf

    def _eq(freq: np.ndarray) -> np.ndarray:
        """Equity de cada mão (linha) vs a distribuição `freq` — ponderada por
        card removal. NUNCA transpor E (bug conhecido do jam/fold)."""
        reach = W * freq[None, :]
        return (reach * E).sum(axis=1) / np.maximum(reach.sum(axis=1), 1e-12)

    def _freq_por_mao(freq: np.ndarray) -> np.ndarray:
        """P(um oponente com essa estratégia entra), por mão do herói."""
        reach = W * freq[None, :]
        return np.clip(reach.sum(axis=1) / peso, 0.0, 1.0)

    def _ev_showdown(eq: np.ndarray, pote_extra: float) -> np.ndarray:
        return eq * (s + pote_extra) - (1 - eq) * s * bf

    # ---------------- nó de PAGAR (não há mais decisões) ----------------
    if paga_node:
        # o range de quem empurrou vem do próprio motor (auto-referência):
        # o shove dele é resolvido no spot dele, com o stack e a mesa iguais
        empurrador = None
        if vil:
            empurrador = solve_spot("open_shove", vil, s, a, bf)
        r_shove = (np.array([empurrador["acao"][h] for h in hands])
                   if empurrador else np.ones(n))
        # `pagaram` só faz sentido no OVERCALL (as fichas de quem pagou estão
        # no pote e eles seguem vivos). Em call_shove a ação ainda está aberta
        # e o `dead` não contém essas fichas: contar os jogadores sem contar o
        # dinheiro deles apertaria o range por um motivo falso.
        n_pag = max(0, int(pagaram)) if spot == "overcall" else 0
        if n_pag:
            # QUEM JÁ PAGOU É ADVERSÁRIO VIVO, não dinheiro morto. O código
            # somava as fichas deles ao pote e mandava o herói bater só o
            # shover: dava "overcall com 100% das mãos" e 72o +3,4bb. Aqui a
            # equity é a chance de bater TODOS, por Monte Carlo multiway
            # (multiplicar as equities heads-up foi medido e reprovado:
            # erra até 14 pontos nas mãos fracas).
            from app.analysis.multiway_equity import equity_table

            pagador = solve_spot("call_shove", hero, s, a, bf, vilao_pos=vil)
            r_call = (np.array([pagador["acao"][h] for h in hands])
                      if pagador else r_shove)
            eq = equity_table(list(hands), [r_shove] + [r_call] * n_pag,
                              iters=6000)
        else:
            eq = _eq(r_shove)
        ev = _ev_showdown(eq, dead - s)     # dead já inclui o all-in dele
        acao = (ev > fold_ev).astype(float)
        pct = round(100 * float((acao * peso).sum() / peso.sum()), 1)
        return {
            "hands": list(hands), "spot": spot, "hero_pos": hero,
            "vilao_pos": vil, "stack": s, "ante": a, "bf": bf,
            "acao": {h: round(float(f), 3) for h, f in zip(hands, acao)},
            "ev": {h: round(float(e), 3) for h, e in zip(hands, ev)},
            "fold_ev": round(fold_ev, 3), "acao_pct": pct, "atras": 0,
            "dead": round(dead, 2),
            "premissas": (
                f"premissas: paga all-in de {vil or 'vilão'} · stack {s:g}bb · "
                f"ante {a*100:g}% do bb · range de shove dele resolvido no "
                f"mesmo motor · bubble factor {bf:g}"
                + (f" · {n_pag} que já pagou(aram) entra(m) como ADVERSÁRIO "
                   f"vivo (equity multiway por simulação, precisa bater "
                   f"todos)" if n_pag else "")),
        }

    # ---------------- nó de EMPURRAR (fictitious play) ----------------
    # grupos que podem pagar: quem abriu (se houver) + cada um atrás
    tem_opener = spot in ("reshove", "squeeze") and vil is not None
    dead_opener = dead - (float(open_bb) - _post(vil, a)) if tem_opener else dead

    # RANGE DE QUEM ABRIU: ele não tem mão aleatória — já abriu, então a
    # distribuição dele é o range de abertura da posição. Sem condicionar
    # nisso, a chance de ele pagar saía diluída sobre as 169 mãos e o
    # re-shove aparecia como +EV com 87% do range (absurdo flagrado no teste).
    r_open = np.ones(n)
    if tem_opener:
        from app.analysis.ranges import OPEN_RANGES, parse_range

        notacao = OPEN_RANGES.get(vil) or OPEN_RANGES.get("MP")
        abre = set(parse_range(notacao))
        r_open = np.array([1.0 if h in abre else 0.0 for h in hands])
        if r_open.sum() == 0:
            r_open = np.ones(n)
    # quem PAGOU o open na frente (squeeze) entra com range de flat call
    r_flat = np.ones(n)
    if spot == "squeeze" and pagaram > 0:
        from app.analysis.ranges import parse_range as _pr

        chama = set(_pr("22+, A2s+, KTs+, QTs+, JTs, ATo+, KQo"))
        r_flat = np.array([1.0 if h in chama else 0.0 for h in hands])

    heroi = np.ones(n)
    call_op = np.zeros(n)      # range de call de quem abriu
    call_atras = np.zeros(n)   # range de call de quem está atrás
    call_flat = np.zeros(n)    # range de call de quem PAGOU o open (squeeze)
    avg_h, avg_op, avg_at = heroi.copy(), call_op.copy(), call_atras.copy()
    avg_fl = call_flat.copy()

    tem_flat = spot == "squeeze" and int(pagaram) > 0
    _frac_open = float((r_open * peso).sum() / peso.sum()) if tem_opener else 1.0
    _frac_flat = float((r_flat * peso).sum() / peso.sum()) if tem_flat else 1.0
    posts_atras = [_post(p, a) for p in atras] or [a]
    dead_medio_atras = dead - float(np.mean(posts_atras))

    def _ev_heroi(op: np.ndarray, at: np.ndarray,
                  fl: np.ndarray | None = None) -> np.ndarray:
        # quem abriu só tem as mãos do range de abertura: a frequência de
        # call é medida DENTRO dele (condicionada), não sobre as 169 mãos
        op_eff = op * r_open
        p_op = (_freq_por_mao(op_eff) / max(_frac_open, 1e-9)
                if tem_opener else np.zeros(n))
        p_op = np.clip(p_op, 0.0, 1.0)
        p_at = _freq_por_mao(at)
        p_todos_largam = (1 - p_op) * (1 - p_at) ** len(atras)
        ev = p_todos_largam * dead
        if tem_opener:
            eq_op = _eq(op_eff) if op_eff.sum() > 1e-9 else np.full(n, 0.5)
            ev += p_op * _ev_showdown(eq_op, dead_opener)
        # quem já pagou o open também pode pagar o squeeze
        p_fl = np.zeros(n)
        if tem_flat and fl is not None:
            fl_eff = fl * r_flat
            p_um = np.clip(_freq_por_mao(fl_eff) / max(_frac_flat, 1e-9), 0, 1)
            # N pagantes na frente: cada um pode pagar o squeeze
            p_fl = 1 - (1 - p_um) ** max(1, int(pagaram))
            eq_fl = _eq(fl_eff) if fl_eff.sum() > 1e-9 else np.full(n, 0.5)
            ev += (1 - p_op) * p_fl * _ev_showdown(eq_fl, dead_opener)
        eq_at = _eq(at) if at.sum() > 1e-9 else np.full(n, 0.5)
        ev += (1 - p_op) * (1 - p_fl) * (1 - (1 - p_at) ** len(atras)) * \
            _ev_showdown(eq_at, dead_medio_atras)
        # ninguém entra: só quando o opener, o flat E todos atrás largam
        ev -= (p_todos_largam - (1 - p_op) * (1 - p_fl)
               * (1 - p_at) ** len(atras)) * dead
        return ev

    for t in range(1, _ITERS + 1):
        eq_vs_heroi = _eq(avg_h)
        # quem abriu paga: o open dele já é dinheiro afundado. Ele adiciona
        # (s − open) e, ganhando, leva tudo que NÃO é dele. Fold vale 0
        # (o open já era perdido de qualquer jeito).
        if tem_opener:
            custo_op = max(s - float(open_bb), 0.0)
            ganho_op = (1.5 + antes_mesa - hero_post - _post(vil, a)) + s
            ev_op = (eq_vs_heroi * ganho_op
                     - (1 - eq_vs_heroi) * custo_op * bf)
            br_op = ((ev_op > 0).astype(float)) * r_open
        else:
            br_op = np.zeros(n)
        # quem está atrás paga o all-in cheio
        br_at = np.zeros(n)
        for post_i in posts_atras:
            pote = dead - post_i + s
            ev_at = eq_vs_heroi * pote - (1 - eq_vs_heroi) * s * bf
            br_at += (ev_at > -post_i * bf).astype(float)
        br_at /= len(posts_atras)

        # melhor resposta de quem pagou o open (custo: s − open já investido)
        if tem_flat:
            custo_fl = max(s - float(open_bb), 0.0)
            ganho_fl = (1.5 + antes_mesa - hero_post - a) + s
            ev_fl = eq_vs_heroi * ganho_fl - (1 - eq_vs_heroi) * custo_fl * bf
            br_fl = ((ev_fl > 0).astype(float)) * r_flat
        else:
            br_fl = np.zeros(n)

        br_h = (_ev_heroi(avg_op, avg_at, avg_fl) > fold_ev).astype(float)

        avg_h += (br_h - avg_h) / t
        avg_op += (br_op - avg_op) / t
        avg_at += (br_at - avg_at) / t
        avg_fl += (br_fl - avg_fl) / t

    ev = _ev_heroi(avg_op, avg_at, avg_fl)
    pct = round(100 * float((avg_h * peso).sum() / peso.sum()), 1)
    nome = {"open_shove": "abre de all-in", "reshove": "empurra sobre o open",
            "squeeze": "empurra sobre open + call"}[spot]
    return {
        "hands": list(hands), "spot": spot, "hero_pos": hero, "vilao_pos": vil,
        "stack": s, "ante": a, "bf": bf,
        "acao": {h: round(float(f), 3) for h, f in zip(hands, avg_h)},
        # 'ev' é o EV ABSOLUTO da ação (referência: início da mão). Quase
        # ninguém quer esse número sozinho: a decisão é ação vs FOLD, e é a
        # diferença que o gráfico desenha. Deixar só o absoluto aqui fez o
        # coach escrever "+7.6bb comparado a foldar" ao lado de um gráfico
        # marcando +8.2 na mesma mão — os dois certos, baselines diferentes.
        # Quem MOSTRA número usa ev_vs_fold (anexado por solve_spot).
        "ev": {h: round(float(e), 3) for h, e in zip(hands, ev)},
        "call_opener": {h: round(float(f), 3) for h, f in zip(hands, avg_op)},
        "call_atras": {h: round(float(f), 3) for h, f in zip(hands, avg_at)},
        "fold_ev": round(fold_ev, 3), "acao_pct": pct, "atras": len(atras),
        "dead": round(dead, 2),
        "premissas": (
            f"premissas: {nome} · {len(atras)} atrás"
            + (f" + quem abriu ({vil} {open_bb:g}bb)" if tem_opener else "")
            + (f" + {pagaram} que pagou(aram)" if pagaram else "")
            + f" · equilíbrio resolvido · primeiro que paga fecha a ação · "
              f"stacks iguais {s:g}bb · ante {a*100:g}% do bb · "
              f"bubble factor {bf:g}"),
    }
