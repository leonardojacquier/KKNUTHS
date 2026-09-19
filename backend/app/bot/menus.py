"""Os botões que o aluno vê — teclados de treino, tamanhos e pós-treino.

Saiu do processing.py junto com `leitura_da_mao`. Também são funções puras:
entram pote/preço/stack, sai a lista de botões. Ficam separadas porque mudam
por motivo DIFERENTE do resto — quando a gente muda o produto, não quando
muda a matemática.
"""
from __future__ import annotations

from app.bot.leitura_da_mao import _fmt_bb


# choice do botão -> (ação base p/ a lógica, rótulo legível p/ o gabarito)
_DRILL_ACTIONS = {
    "fold": ("fold", "FOLD"),
    "call": ("call", "CALL"),
    "check": ("check", "CHECK"),
    "raise": ("raise", "RAISE"),          # legado
    "raise3x": ("raise", "RAISE 3x"),
    "raisepot": ("raise", "RAISE do tamanho do pote"),
    "allin": ("raise", "ALL-IN"),
    "bet": ("bet", "BET"),                # legado
    "bet33": ("bet", "BET ⅓ do pote"),
    "bet50": ("bet", "BET ½ do pote"),
    "betpot": ("bet", "BET do tamanho do pote"),
}


def sizing_amounts(pot_bb: float | None, to_call_bb: float | None,
                   stack_bb: float | None) -> dict[str, float | None]:
    """Tamanho REAL (em bb) de cada botão de sizing — o aluno vê o número,
    não só 'raise pote'. Convenções padrão:
    - raise 3x = aumenta PARA 3× a aposta enfrentada
    - raise pote = pote + 2× a aposta (pot_bb já inclui a aposta do vilão)
    - bet ⅓/½/pote = fração do pote atual
    - all-in = o stack do herói
    Cap no stack: nunca oferece um sizing maior que o all-in."""
    pot = pot_bb or 0
    tc = to_call_bb or 0
    stack = stack_bb or 0

    def cap(x: float) -> float | None:
        if x <= 0:
            return None
        return min(x, stack) if stack else x

    return {
        "raise3x": cap(3 * tc),
        "raisepot": cap(pot + 2 * tc),
        "bet33": cap(pot / 3),
        "bet50": cap(pot / 2),
        "betpot": cap(pot),
        "allin": stack or None,
    }


def action_menu_rows(pot_bb, to_call_bb, stack_bb, prefix: str,
                     suffix: str = "") -> list[list[dict]]:
    """Menu PRINCIPAL de ação, como numa sala de verdade: primeiro a decisão
    (Fold/Call/Raise ou Check/Bet); apertar Raise/Bet abre o menu de tamanhos
    (size_menu_rows) — feedback do admin: 'quero apertar no raise e poder
    escolher o tamanho da aposta'."""
    if to_call_bb:
        return [
            [{"text": "🚫 Fold", "callback_data": f"{prefix}:fold{suffix}"},
             {"text": f"✅ Call{_fmt_bb(to_call_bb)}",
              "callback_data": f"{prefix}:call{suffix}"}],
            [{"text": "⬆️ Raise — escolher tamanho ▸",
              "callback_data": f"{prefix}:sizes{suffix}"}],
        ]
    return [
        [{"text": "Check", "callback_data": f"{prefix}:check{suffix}"}],
        [{"text": "🎯 Bet — escolher tamanho ▸",
          "callback_data": f"{prefix}:sizes{suffix}"}],
    ]


def size_menu_rows(pot_bb, to_call_bb, stack_bb, prefix: str,
                   suffix: str = "") -> list[list[dict]]:
    """Submenu de tamanhos (abre no toque em Raise/Bet), com o valor REAL em
    bb de cada sizing e o Voltar pra trocar de ideia."""
    amt = sizing_amounts(pot_bb, to_call_bb, stack_bb)
    if to_call_bb:
        rows = [
            [{"text": f"3x{_fmt_bb(amt['raise3x'])}",
              "callback_data": f"{prefix}:raise3x{suffix}"},
             {"text": f"Pote{_fmt_bb(amt['raisepot'])}",
              "callback_data": f"{prefix}:raisepot{suffix}"},
             {"text": f"💥 All-in{_fmt_bb(amt['allin'])}",
              "callback_data": f"{prefix}:allin{suffix}"}],
        ]
    else:
        rows = [
            [{"text": f"⅓ pote{_fmt_bb(amt['bet33'])}",
              "callback_data": f"{prefix}:bet33{suffix}"},
             {"text": f"½ pote{_fmt_bb(amt['bet50'])}",
              "callback_data": f"{prefix}:bet50{suffix}"},
             {"text": f"Pote{_fmt_bb(amt['betpot'])}",
              "callback_data": f"{prefix}:betpot{suffix}"},
             {"text": f"💥 All-in{_fmt_bb(amt['allin'])}",
              "callback_data": f"{prefix}:allin{suffix}"}],
        ]
    rows.append([{"text": "↩️ Voltar",
                  "callback_data": f"{prefix}:back{suffix}"}])
    return rows


def drill_action(choice: str) -> tuple[str, str]:
    """(ação base, rótulo) de um choice de botão — normaliza os tamanhos."""
    return _DRILL_ACTIONS.get(choice, (choice, choice.upper()))


def botoes_pos_treino(precisa_da_primeira_mao: bool) -> list[list[dict]]:
    """O "e agora?" depois do gabarito. Função PURA.

    O aluno novo recebia QUATRO mensagens seguidas (gabarito, "qual é mais
    fácil pra você?", o filme da mão, "e agora?") e, no fim, quatro botões
    em que NENHUM levava à ação que importa: mandar uma mão dele. Pior:
    "Simular esta mão" e "Desafiar os amigos" agiam sobre a mão-DEMO — ele
    ia desafiar o clube com um spot que não jogou.

    Quem ainda não mandou mão vê DOIS botões, com o certo em primeiro. Quem
    já usa vê os quatro, que aí agem sobre a mão dele e fazem sentido.
    """
    if precisa_da_primeira_mao:
        return [[{"text": "📤 Mandar uma mão minha",
                  "callback_data": "go:enviar"}],
                [{"text": "🎯 Outro treino", "callback_data": "go:treino"}]]
    return [[{"text": "🔁 Simular esta mão", "callback_data": "pa:sim"},
             {"text": "🎯 Outro treino", "callback_data": "go:treino"}],
            [{"text": "📖 Range do spot", "callback_data": "pa:range"},
             {"text": "📣 Desafiar os amigos", "callback_data": "pa:share"}]]
