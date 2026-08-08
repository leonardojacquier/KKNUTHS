"""Estatísticas de estilo do jogador, calculadas de forma determinística.

VPIP, PFR, 3-bet%, fator de agressão (AF) e um rótulo de estilo. Recalculável
incrementalmente a cada novo lote de mãos.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.canonical import ActionType, CanonicalHand, StreetName

# Fontes que trazem a SESSÃO INTEIRA. VPIP/PFR só significam alguma coisa
# numa amostra onde as mãos foldadas TAMBÉM estão — e ninguém manda o replay
# de uma mão que largou no pré. Replay avulso e print são escolhidos a dedo:
# medir frequência neles mede o gosto do aluno, não o jogo dele.
#
# Caso real: o Ricardo tinha VPIP 94.3% no perfil, calculado sobre 53 replays
# que ele mesmo escolheu mandar. O coach disse a ele, no meio de uma análise,
# "seu VPIP tá em 93,6%, joga MUITO lixo". O VPIP de verdade dele, em 406.639
# mãos, é 26% — ele mandou o print pra ferramenta no mesmo dia.
FONTES_COMPLETAS = {"txt", "text", "csv", "phh", "pdf"}
MINIMO_PARA_PERFIL = 30
# rótulo de estilo ("LAG", "calling station") é afirmação sobre QUEM a pessoa
# é. Com 54 mãos o intervalo do VPIP é ±13 pontos — largo o bastante para o
# rótulo virar outro. Número com intervalo declarado a partir de 30; rótulo
# só com 100.
MINIMO_PARA_ROTULO = 100


def margem_de_erro_pp(n: int, p: float = 0.25) -> float:
    """Meia-largura do IC95 de uma proporção, em pontos percentuais.

    Existe para que NENHUMA taxa apareça sem ela. 'VPIP 26%' é uma promessa
    de precisão que o denominador não paga; 'VPIP 26% (n=148, ±7pp)' é o
    mesmo dado sem a promessa.
    """
    if n <= 0:
        return 50.0
    return round(200.0 * ((p * (1 - p)) / n) ** 0.5, 1)


@dataclass
class PlayerStats:
    player: str
    hands: int = 0
    vpip: float = 0.0      # % voluntariamente colocou fichas pré-flop
    pfr: float = 0.0       # % raise pré-flop
    three_bet: float = 0.0  # % 3-bet pré-flop (sobre oportunidades)
    af: float = 0.0        # fator de agressão pós-flop = (bets+raises)/calls
    label: str = "amostra insuficiente"
    detail: dict = field(default_factory=dict)

    @property
    def publicavel(self) -> bool:
        """Perfil que pode ser DITO ao aluno. Amostra escolhida a dedo não
        vira frequência — melhor não ter perfil que ter um errado."""
        return self.hands >= MINIMO_PARA_PERFIL and not self.detail.get(
            "amostra_viesada")

    @property
    def margem_pp(self) -> float:
        return margem_de_erro_pp(self.hands)


class AmostraCurada(Exception):
    """Tentaram tirar FREQUÊNCIA de mãos escolhidas a dedo.

    O incidente do VPIP 94% não foi amostra pequena — foi viés de seleção.
    Com 53 replays que o aluno escolheu mandar, o VPIP dá 94%; com 5.000
    replays que ele escolheu, TAMBÉM daria 94%. Amostra maior não conserta
    viés: o estimador converge para o valor errado.

    Por isso isto é exceção e não aviso. 'Tomar cuidado ao usar' é o que já
    existia, e o número errado foi para a tela do aluno mesmo assim.
    """


def exigir_amostra_completa(hands: list[CanonicalHand], oquê: str) -> None:
    """Portão para qualquer número MARGINAL (taxa, frequência, bb/100).

    Não vale para análise da mão nem para EV de uma decisão — ali o replay
    avulso é dado legítimo, porque a conta é sobre AQUELA mão e não sobre a
    distribuição do jogo do aluno.
    """
    curadas = [h for h in hands
               if (getattr(h, "source_format", None) or "txt")
               not in FONTES_COMPLETAS]
    if curadas:
        raise AmostraCurada(
            f"{oquê}: {len(curadas)} de {len(hands)} mãos são escolhidas a "
            "dedo (replay/print). Frequência só se calcula sobre sessão "
            "inteira — senão sai o VPIP 94% de novo.")


def amostra_completa(hands: list[CanonicalHand]) -> list[CanonicalHand]:
    """Só as mãos que vieram de export de sessão inteira."""
    return [h for h in hands if (h.source_format or "txt") in FONTES_COMPLETAS]


def compute_player_stats(hands: list[CanonicalHand], player: str | None = None,
                         somente_amostra_completa: bool = True,
                         fora_da_amostra: int = 0) -> PlayerStats:
    """Stats de `player`; com player=None usa o herói de cada mão — correto para
    histórico cumulativo, onde o nick do herói varia entre salas.

    Por padrão mede só sobre export de sessão inteira: frequência tirada de
    replay avulso/print é um artefato da escolha do aluno.

    `fora_da_amostra` são mãos JÁ descartadas antes de chegar aqui — hoje
    pelo filtro no banco (`get_hands_para_perfil`). Sem esse número, quem só
    manda replay ficava com "amostra insuficiente" em vez de "só mãos
    avulsas, que não medem frequência", que é outra coisa.
    """
    descartadas = max(0, int(fora_da_amostra or 0))
    if somente_amostra_completa:
        completas = amostra_completa(hands)
        descartadas += len(hands) - len(completas)
        hands = completas
    n = 0
    vpip_h = pfr_h = three_bet_h = 0
    three_bet_opps = 0
    post_bets = post_raises = post_calls = 0

    for h in hands:
        target = player if player is not None else h.hero
        if not target or target not in {p.name for p in h.players}:
            continue
        n += 1

        pre = h.street(StreetName.PREFLOP)
        voluntarily = raised = three_bet = False
        had_3bet_opp = False

        if pre:
            seen_raise = 0
            for a in pre.actions:
                if a.type == ActionType.POST:
                    continue
                if a.actor == target:
                    if a.type in (ActionType.CALL, ActionType.BET, ActionType.RAISE):
                        voluntarily = True
                    if a.type == ActionType.RAISE:
                        raised = True
                    # oportunidade de 3-bet: QUALQUER decisão do jogador diante
                    # de exatamente 1 raise (o open) — inclusive fold/call, senão
                    # o denominador só conta as mãos em que ele 3-betou e a
                    # estatística vira ~100%. Raise diante de 2+ é 4-bet, não 3-bet.
                    if seen_raise == 1:
                        had_3bet_opp = True
                        if a.type == ActionType.RAISE:
                            three_bet = True
                if a.type == ActionType.RAISE:
                    seen_raise += 1

            if had_3bet_opp:
                three_bet_opps += 1

        vpip_h += int(voluntarily)
        pfr_h += int(raised)
        three_bet_h += int(three_bet)

        # agressão pós-flop
        for street_name in (StreetName.FLOP, StreetName.TURN, StreetName.RIVER):
            st = h.street(street_name)
            if not st:
                continue
            for a in st.actions:
                if a.actor != target:
                    continue
                if a.type == ActionType.BET:
                    post_bets += 1
                elif a.type == ActionType.RAISE:
                    post_raises += 1
                elif a.type == ActionType.CALL:
                    post_calls += 1

    stats = PlayerStats(player=player or "hero", hands=n)
    if descartadas:
        stats.detail["maos_fora_da_amostra"] = descartadas
    if n == 0:
        if descartadas:
            stats.detail["amostra_viesada"] = True
            stats.label = ("sem amostra de sessão — só mãos avulsas, que não "
                           "medem frequência")
        return stats

    stats.vpip = round(100 * vpip_h / n, 1)
    stats.pfr = round(100 * pfr_h / n, 1)
    stats.three_bet = round(100 * three_bet_h / three_bet_opps, 1) if three_bet_opps else 0.0
    stats.af = round((post_bets + post_raises) / post_calls, 2) if post_calls else float(post_bets + post_raises)
    stats.label = _label(stats)
    # update, não atribuição: `maos_fora_da_amostra` é gravado antes daqui e
    # sobrescrevê-lo apagava justamente o rastro de que houve filtro
    stats.detail.update({
        "post_bets": post_bets,
        "post_raises": post_raises,
        "post_calls": post_calls,
        "three_bet_opps": three_bet_opps,
        "margem_pp": margem_de_erro_pp(n),
    })
    return stats


def _label(s: PlayerStats) -> str:
    """Rótulo heurístico (refinado pelo LLM com contexto na produção).

    RÓTULO É AFIRMAÇÃO SOBRE QUEM A PESSOA É — 'calling station' cola. Com
    54 mãos o VPIP tem ±13 pontos de margem, largura suficiente para o
    rótulo ser outro. Abaixo de 100 mãos o número sai (com a margem junto),
    o rótulo não.
    """
    if s.hands < MINIMO_PARA_ROTULO:
        return (f"amostra ainda curta para rótulo de estilo "
                f"({s.hands} mãos; precisa de {MINIMO_PARA_ROTULO})")
    loose = s.vpip >= 28
    aggressive = s.pfr >= 18 and s.af >= 2.0
    gap = s.vpip - s.pfr

    if loose and aggressive:
        return "LAG (loose-aggressive)"
    if not loose and aggressive:
        return "TAG (tight-aggressive)"
    if loose and not aggressive:
        return "calling station / loose-passive"
    if gap <= 6 and s.vpip < 18:
        return "nit (tight-passive)"
    return "tight-passive"


def perfil_que_pode_ser_dito(linha: dict | None) -> dict | None:
    """O perfil como ele entra na boca do coach. Função PURA.

    Este é o caminho por onde o VPIP 94,3% chegava ao aluno: a linha de
    `player_stats` era injetada crua como `perfil_do_jogador` em toda
    pergunta aberta. O cálculo já estava consertado havia semanas; a linha
    velha, não — e ninguém relê uma tabela.

    Devolve o perfil só quando a amostra o sustenta. Quando não sustenta,
    devolve o MOTIVO em vez de nada: sem isso o coach acha que o aluno é
    novo, quando na verdade ele mandou 92 mãos pelo canal errado.
    """
    if not linha:
        return None
    detail = linha.get("detail") or {}
    n = linha.get("hands") or 0
    publicavel = detail.get("publicavel")
    if publicavel is False or linha.get("vpip") is None:
        return {
            "frequencias": None,
            "maos_na_amostra": n,
            "por_que_sem_perfil": (
                "as mãos deste aluno vieram de replay avulso/print, que ele "
                "escolheu mandar — isso mede o gosto dele, não o jogo. "
                "PROIBIDO afirmar VPIP, PFR, 3-bet ou estilo. Se ele "
                "perguntar do próprio perfil, explique isso e peça um "
                "arquivo de sessão inteira (.txt do torneio)."),
        }
    return {**linha, "margem_pp": margem_de_erro_pp(n),
            "instrucao_margem": (
                f"toda frequência daqui tem ±{margem_de_erro_pp(n):g} pontos "
                f"de margem ({n} mãos) — cite a margem ou fale qualitativo")}
