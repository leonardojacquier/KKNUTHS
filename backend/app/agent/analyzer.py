"""Agente de análise.

A camada determinística (este módulo) extrai os spots e métricas objetivas de cada
mão/torneio usando as tools de `app.analysis`. O texto final em linguagem natural pode
ser gerado por um LLM (Claude) recebendo este dicionário estruturado como contexto —
ver `llm_summary()`. Mantendo a parte cara (LLM) opcional, todo o resto roda offline.
"""
from __future__ import annotations

from app.analysis.equity import board_texture, describe_hand as _describe
from app.analysis.equity import pretty_cards as _pretty
from app.analysis.tools import fmt_chips as _fmt_chips
from app.analysis.tools import pot_odds
from app.models.canonical import ActionType, CanonicalHand, StreetName

_STREET_ORDER = [StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN, StreetName.RIVER]


def analyze_hand(hand: CanonicalHand) -> dict:
    """Análise estruturada de uma mão (sem LLM).

    Reconstrói o pote street a street, identifica as decisões do herói e calcula
    pot odds nos pontos de call. Retorna um dicionário pronto para virar texto.
    """
    hero = hand.hero
    spots: list[dict] = []
    pot = 0.0
    contributed: dict[str, float] = {}

    for sname in _STREET_ORDER:
        st = hand.street(sname)
        if not st:
            continue
        street_contrib: dict[str, float] = {}
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                # 'raises X to Y': o total da street já investido é descontado
                add = a.to_amount - street_contrib.get(a.actor, 0.0)

            # antes vão ao pote, mas NÃO contam como aposta da street (não entram
            # no street_contrib usado para o cálculo do 'raise to').
            counts_as_wager = a.type != ActionType.POST or a.post_type in ("sb", "bb")

            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET, ActionType.RAISE):
                # pot odds no momento do call do herói (antes de adicionar a ficha)
                if a.actor == hero and a.type == ActionType.CALL and add > 0:
                    req = pot_odds(pot, add)
                    spots.append(
                        {
                            "street": sname.value,
                            "decision": "call",
                            "to_call": round(add, 2),
                            "pot_before": round(pot, 2),
                            "required_equity": round(req, 3),
                        }
                    )
                if a.actor == hero and a.type in (ActionType.BET, ActionType.RAISE):
                    spots.append(
                        {
                            "street": sname.value,
                            "decision": "aggression",
                            "type": a.type.value,
                            "amount": round(add, 2),
                            "pot_before": round(pot, 2),
                            "all_in": a.all_in,
                        }
                    )
                pot += add
                if counts_as_wager:
                    street_contrib[a.actor] = street_contrib.get(a.actor, 0.0) + add
                contributed[a.actor] = contributed.get(a.actor, 0.0) + add

    # aposta não paga devolvida: sai do pote e do investimento de quem apostou
    returned = sum(hand.uncalled.values())
    pot -= returned

    won = hand.collected.get(hero or "", 0.0)
    invested = contributed.get(hero or "", 0.0) - hand.uncalled.get(hero or "", 0.0)
    net = round(won - invested, 2)
    if hand.net_won is not None:  # fonte-resumo (CSV) já traz o líquido pronto
        net = round(hand.net_won, 2)

    # `or 1` era uma bomba: print sem o nível legível saía com big_blind 0, e
    # cada stack virava o próprio número de fichas rotulado como bb (caso real:
    # 98.331 fichas viraram '98331bb'). Profundidade sem big blind não é
    # calculável — e um número inventado é pior que campo vazio, porque o
    # coach raciocina em cima dele.
    bb_conhecido = bool(hand.stakes.big_blind)
    bb = hand.stakes.big_blind or 1

    # contexto de stacks EM BB — sem isto o LLM estimava o stack do herói (caso
    # real: coach chamou push_fold com '12bb' quando o aluno tinha 58bb; o 12
    # era o valor do big blind). O que importa num all-in é o stack EFETIVO.
    hero_seat = hand.hero_seat()
    hero_stack_bb = round(hero_seat.stack / bb, 1) if hero_seat else None
    others_bb = [round(p.stack / bb, 1) for p in hand.players if not p.is_hero]
    effective_bb = (round(min(hero_stack_bb, max(others_bb)), 1)
                    if hero_stack_bb is not None and others_bb else hero_stack_bb)
    stacks_bb = {
        (p.position or p.name[:8]): round(p.stack / bb, 1) for p in hand.players
    }

    # O mais fundo da mesa com menos de 2bb é impossível na prática: quem
    # postou o blind já tem 1bb, e abaixo disso a mão nem se joga. Quando
    # aparece, a escala está furada — não é uma mesa de stacks curtos.
    # Caso real: print com blinds em fichas e stacks em bb virou tudo 0.0, e
    # o coach pediu ao aluno o stack que estava na foto.
    mais_fundo = max((p.stack or 0) for p in hand.players) if hand.players else 0
    escala_suspeita = bool(mais_fundo) and (
        not bb_conhecido or mais_fundo < 2 * bb)
    if escala_suspeita:
        # não entregar número inventado: campo vazio o coach respeita
        hero_stack_bb = effective_bb = None
        stacks_bb = {}

    # spots também em BB (o modelo raciocina em BB, não em fichas)
    for s in spots:
        for k_chips, k_bb in (("to_call", "to_call_bb"), ("pot_before", "pot_bb"),
                              ("amount", "amount_bb")):
            if k_chips in s:
                s[k_bb] = round(s[k_chips] / bb, 1)

    return {
        "hand_id": hand.hand_id,
        "site": hand.site,
        "format": hand.format.value,
        "hero": hero,
        "hero_cards": hand.hero_cards,
        "position": _hero_position(hand),
        "blinds": f"{_fmt_chips(hand.stakes.small_blind or 0)}/{_fmt_chips(bb)}"
                  + (f" ante {_fmt_chips(hand.stakes.ante)}" if hand.stakes.ante else ""),
        "players": len(hand.players),
        "hero_stack_bb": hero_stack_bb,
        "effective_bb": effective_bb,
        "stacks_bb": stacks_bb,
        **({"stacks_ilegiveis": "A profundidade NÃO pôde ser calculada: "
            + ("o big blind não foi lido na imagem." if not bb_conhecido else
               "os stacks estão numa escala inconsistente com o big blind.")
            + " Por isso hero_stack_bb/effective_bb/stacks_bb vêm vazios — não "
            "invente um valor nem trate os números de fichas como bb. Analise "
            "o que dá sem profundidade e peça ao aluno o stack efetivo em bb."}
           if escala_suspeita else {}),
        "final_board": hand.final_board,
        "pot_total": round(pot, 2),
        # Print de MEIO de mão: o pote reconstruído pela soma das ações é
        # sempre um piso, porque a foto não mostra a linha inteira. O número
        # impresso na tela é o pote de verdade, e é ele que dá o preço.
        **({"pot_na_tela": round(float(hand.total_pot), 2),
            "pot_na_tela_nota": "Pote LIDO na imagem — vale mais que "
            "pot_total (soma só das ações visíveis no print). Use este para "
            "pot odds."} if _pot_lido_manda(hand, pot) else {}),
        "net_chips": net,
        "net_bb": round(net / bb, 2),
        # showdown REAL: cartas reveladas por jogador + quem levou o pote.
        # O coach só pode afirmar cartas de vilão que estejam AQUI.
        "showdown_cards": dict(hand.shown_cards or {}),
        # cartas prontas pra citar no texto (rank + ícone do naipe) — o aluno
        # pediu os ícones nas descrições; o coach copia daqui, não translitera
        "cartas_texto": _cartas_texto(hand),
        # textura calculada do board final: flush possível ou não — âncora
        # anti-'QJ fechou flush' num board de duas copas (caso real; era
        # sequência broadway)
        "textura_do_board": (board_texture(hand.final_board)
                             if hand.final_board else None),
        "pot_winners": dict(hand.collected or {}),
        # leitura DETERMINÍSTICA da mão feita (gabarito — o coach não pode
        # recontar de cabeça: já rendeu 'trinca de J' onde havia dois pares)
        "hero_final_hand": _describe(hand.hero_cards, hand.final_board),
        "showdown_hands": {
            n: _describe(cs, hand.final_board)
            for n, cs in (hand.shown_cards or {}).items()
            if _describe(cs, hand.final_board)
        },
        # a MESMA leitura street a street: diz QUANDO cada mão ficou pronta
        # (o coach narrou 'sequência fechou no river' quando fechou no flop)
        "hand_by_street": _hands_by_street(hand),
        # registro CRONOLÓGICO oficial de TODAS as ações (herói E vilões) —
        # sem isto o coach reconstruía a sequência de memória e disse "ele
        # só pagou seu open" numa mão em que houve 3-bet pago (caso real)
        "linha_da_mao": _action_log(hand),
        # PKO/bounty: recompensas na cabeça de cada jogador — presença disto
        # OBRIGA a conta de all-in a usar pko_call (regra C7)
        "pko": any(p.bounty for p in hand.players),
        "bounties": {(p.position or p.name[:12]): p.bounty
                     for p in hand.players if p.bounty},
        "spots": spots,
        "summary": _deterministic_summary(hand, spots, net, bb),
    }


def _pot_lido_manda(hand: CanonicalHand, pot_somado: float) -> bool:
    """O pote impresso na foto vale mais que a soma das ações transcritas.

    Só para snapshot de imagem, e só quando o lido é MAIOR: a foto de meio de
    mão nunca mostra a linha inteira, então a soma é um piso. Se o lido for
    menor, é erro de leitura e a soma manda (mão fechada não perde ficha)."""
    if hand.source_format != "image" or not hand.total_pot:
        return False
    return float(hand.total_pot) > pot_somado + 0.01


_CARTAS_ATE_A_STREET = ((StreetName.FLOP, 3), (StreetName.TURN, 4),
                        (StreetName.RIVER, 5))


def board_por_street(hand: CanonicalHand) -> dict:
    """Board CUMULATIVO de cada street: {'flop': [3 cartas], 'turn': [4], ...}.

    No canônico cada `Street.board` guarda só as cartas NOVAS dela (flop 3,
    turn 1, river 1) — o board "no turn" é a SOMA flop+turn. Quem precisa
    dessa soma pronta: o contexto do coach (`_cartas_texto`) e o guarda que
    confere as cartas citadas na linha do placar (`guarda_fatos`).

    A convenção NÃO é uniforme entre os parsers — `pppoker_replay` e `phh`
    gravam as cartas novas, `pokerstars` e `dealing_family` gravam o board já
    somado. Por isso a street que já vem com o tamanho fechado (3/4/5) manda
    como está, e só a que vem curta é somada à anterior.

    Só streets que existiram: mão que parou no flop não devolve chave de
    turn. `final_board` entra como reserva para as fontes que não trazem o
    board separado por street (CSV de tracker, imagem)."""
    fb = list(hand.final_board or [])
    out: dict = {}
    acumulado: list[str] = []
    for sname, n in _CARTAS_ATE_A_STREET:
        st = hand.street(sname)
        novas = list(st.board) if st and st.board else []
        if len(novas) == n:
            acumulado = novas          # a fonte já trouxe o board somado
        elif novas:
            acumulado = acumulado + novas
        cartas = acumulado if len(acumulado) == n else fb[:n]
        if len(cartas) != n:
            break            # street que não veio: nem ela nem as seguintes
        out[sname.value] = cartas
    return out


def _cartas_texto(hand: CanonicalHand) -> dict:
    """Cartas em texto de citação (rank + ícone ♠♥♦♣): herói, board e cada
    showdown — prontas para o coach colar na resposta."""
    out: dict = {}
    if hand.hero_cards:
        out["heroi"] = _pretty(hand.hero_cards)
    if hand.final_board:
        out["board"] = _pretty(hand.final_board)
    # o board FATIADO por street, cumulativo e já bonito. O board final numa
    # string única obrigava o coach a separar as três primeiras de cabeça
    # para escrever a linha do placar do R2 — e ele errou (16/08, mão
    # f2cd6504, board 9h Jd 2h): escreveu "*Flop* 9♥J♦2♦", inventando um
    # flush draw em que a análise inteira se apoiou. Aqui ele COPIA.
    por_street = board_por_street(hand)
    if por_street:
        out["board_por_street"] = {k: _pretty(v) for k, v in por_street.items()}
    sd = {n: _pretty(cs) for n, cs in (hand.shown_cards or {}).items()}
    if sd:
        out["showdown"] = sd
    return out


def _action_log(hand: CanonicalHand) -> dict:
    """Linha cronológica de TODAS as ações, por street, em bb — o registro
    oficial de quem fez o quê (herói marcado; raises do pré numerados:
    abre/3-beta/4-beta). É a fonte da narração do coach, nunca a memória."""
    bb = hand.stakes.big_blind or 1
    pos = {p.name: (p.position or p.name[:10]) for p in hand.players}
    out: dict = {}
    for sname in _STREET_ORDER:
        st = hand.street(sname)
        if not st:
            continue
        raise_n = 0
        lines = []
        for a in st.actions:
            if a.type == ActionType.POST:
                continue
            who = ("HERÓI" if a.actor == hand.hero else
                   f"{pos.get(a.actor, a.actor[:10])}")
            amt = round((a.to_amount or a.amount) / bb, 1)
            if a.type == ActionType.RAISE:
                raise_n += 1
                verb = ({1: "abre", 2: "3-beta", 3: "4-beta"}.get(raise_n,
                        f"{raise_n + 1}-beta") if sname == StreetName.PREFLOP
                        else "aumenta p/")
                lines.append(f"{who} {verb} {amt:g}bb"
                             + (" (all-in)" if a.all_in else ""))
            elif a.type == ActionType.BET:
                lines.append(f"{who} aposta {amt:g}bb"
                             + (" (all-in)" if a.all_in else ""))
            elif a.type == ActionType.CALL:
                lines.append(f"{who} paga {amt:g}bb"
                             + (" (all-in)" if a.all_in else ""))
            elif a.type == ActionType.CHECK:
                lines.append(f"{who} dá check")
            elif a.type == ActionType.FOLD:
                lines.append(f"{who} folda")
        if lines:
            out[sname.value] = lines
    return out


def _hands_by_street(hand: CanonicalHand) -> dict:
    """Mão feita por street (flop/turn/river) do herói e de quem mostrou.

    Gabarito de QUANDO cada mão ficou pronta — a narração do coach usa isto
    em vez de deduzir ('KJ no T-A-Q fechou a sequência NO FLOP')."""
    fb = hand.final_board or []

    def by_street(cards: list[str]) -> dict:
        out = {}
        for st, n in (("flop", 3), ("turn", 4), ("river", 5)):
            if len(fb) >= n:
                d = _describe(cards, fb[:n])
                if d:
                    out[st] = d
        return out

    result = {}
    if hand.hero_cards:
        result["heroi"] = by_street(hand.hero_cards)
    for n, cs in (hand.shown_cards or {}).items():
        b = by_street(cs)
        if b:
            result[n] = b
    return result


def analyze_tournament(hands: list[CanonicalHand]) -> dict:
    """Agrega mãos de um mesmo torneio num relatório."""
    if not hands:
        return {"hands": 0}
    hero = next((h.hero for h in hands if h.hero), None)
    per_hand = [analyze_hand(h) for h in hands]
    net_bb = round(sum(a["net_bb"] for a in per_hand), 2)
    biggest = sorted(per_hand, key=lambda a: a["net_bb"])
    all_ins = [a for a in per_hand if any(s.get("all_in") for s in a["spots"])]

    return {
        "hero": hero,
        "tournament_id": hands[0].tournament_id,
        "buyin": hands[0].stakes.buyin,
        "hands": len(hands),
        "net_bb": net_bb,
        "biggest_loss": biggest[0] if biggest else None,
        "biggest_win": biggest[-1] if biggest else None,
        "all_in_spots": len(all_ins),
        "summary": (
            f"Torneio {hands[0].tournament_id or ''}: {len(hands)} mãos, "
            f"resultado líquido {net_bb:+.1f} BB, {len(all_ins)} spot(s) de all-in."
        ),
    }


def hand_timeline(hand: CanonicalHand) -> list[dict]:
    """Linha do tempo da mão para o simulador: eventos na ordem, com o pote
    reconstruído. Decisões do herói viram eventos 'decision' (com to_call);
    ações dos vilões viram 'action' (narração)."""
    hero = hand.hero
    events: list[dict] = []
    pot = 0.0

    for sname in _STREET_ORDER:
        st = hand.street(sname)
        if not st:
            continue
        contrib: dict[str, float] = {}
        for a in st.actions:
            add = a.amount
            if a.type == ActionType.RAISE and a.to_amount:
                add = a.to_amount - contrib.get(a.actor, 0.0)
            counts = a.type != ActionType.POST or a.post_type in ("sb", "bb")
            outstanding = max(contrib.values(), default=0.0)

            if a.actor == hero and a.type != ActionType.POST:
                to_call = max(0.0, outstanding - contrib.get(hero or "", 0.0))
                events.append(
                    {
                        "kind": "decision",
                        "street": sname.value,
                        "board": list(st.board),
                        "pot": round(pot, 2),
                        "to_call": round(to_call, 2),
                        "actual": a.type.value,
                        "amount": round(add, 2),
                        "all_in": a.all_in,
                    }
                )
            elif a.type != ActionType.POST:
                label = a.type.value + (f" {add:g}" if add else "")
                events.append(
                    {
                        "kind": "action",
                        "street": sname.value,
                        "board": list(st.board),
                        "text": f"{a.actor}: {label}",
                    }
                )

            if a.type in (ActionType.POST, ActionType.CALL, ActionType.BET, ActionType.RAISE):
                pot += add
                if counts:
                    contrib[a.actor] = contrib.get(a.actor, 0.0) + add
    return events


def select_key_hands(hands: list[CanonicalHand], k: int = 5) -> list[dict]:
    """Seleciona as mãos decisivas de um torneio para coaching individual.

    Critério: todos os all-ins do herói + maiores |resultado em BB|, deduplicado,
    limitado a k — controla o custo de LLM cobrindo o que definiu o torneio.
    """
    analyses = [analyze_hand(h) for h in hands]
    allins = [a for a in analyses if any(s.get("all_in") for s in a["spots"])]
    by_swing = sorted(analyses, key=lambda a: abs(a["net_bb"]), reverse=True)

    seen: set[str] = set()
    key: list[dict] = []
    for a in allins + by_swing:
        if a["hand_id"] in seen:
            continue
        seen.add(a["hand_id"])
        key.append(a)
        if len(key) >= k:
            break
    return key


def _hero_position(hand: CanonicalHand) -> str | None:
    seat = hand.hero_seat()
    return seat.position if seat else None


def _deterministic_summary(hand: CanonicalHand, spots: list[dict], net: float, bb: float) -> str:
    """O plano C — quando a análise do coach falha, ISTO chega no aluno.

    A versão anterior era um stub de depuração ("VOCÊ (Tc Kh) em ?...") e
    foi entregue assim em produção (13/08 22:26, juiz apontou: sem selo,
    carta sem naipe). Rede de segurança também é produto: selo, naipes,
    e a honestidade de dizer que a análise completa não saiu."""
    from app.analysis.equity import pretty_cards

    cards = pretty_cards(list(hand.hero_cards)) if hand.hero_cards else "?"
    pos = _hero_position(hand)
    quem = f"{cards}" + (f" no {pos}" if pos else "")
    parts = [
        "🟡 *Análise curta — modo seguro.* A análise completa não saiu "
        "agora; ficam os números da mão. Reenvia (ou pergunta aqui) que "
        "eu detalho.",
        f"Sua mão: {quem}.",
    ]
    for s in spots:
        if s["decision"] == "call":
            parts.append(
                f"No {s['street']}: pagou {s['to_call']:.0f} num pote de "
                f"{s['pot_before']:.0f} — equity necessária {s['required_equity']*100:.1f}%."
            )
        else:
            tag = "all-in" if s.get("all_in") else s["type"]
            parts.append(
                f"No {s['street']}: {tag} de {s['amount']:.0f} "
                f"(pote {s['pot_before']:.0f})."
            )
    parts.append(f"Saldo da mão: {net/bb:+.1f} BB.")
    return "\n".join(parts)


def llm_summary(structured: dict, stats: dict | None = None, lang: str = "pt") -> str:
    """Coaching em linguagem natural via Claude (com tools determinísticas).

    Recebe a análise estruturada e as stats do jogador; o LLM julga e explica usando
    os números já calculados. Sem ANTHROPIC_API_KEY, cai no resumo determinístico.
    """
    from app.agent.llm import coach

    return coach(structured, stats, lang)
