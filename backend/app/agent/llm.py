"""Integração com o Claude (Anthropic) — o LLM faz o *julgamento*, não a conta.

Arquitetura: a camada determinística (`analyze_hand`) já calculou pote, spots e
métricas. O Claude recebe isso pronto e, quando precisa de um número adicional,
chama uma *tool* determinística (equity, pot odds, EV, SPR) via function calling —
ele nunca inventa um valor. O resultado é coaching em linguagem natural ancorado
em matemática correta.

Sem `ANTHROPIC_API_KEY` (ou em qualquer falha), cai no resumo determinístico —
o produto nunca quebra por causa do LLM.
"""
from __future__ import annotations

import base64
import json

from app.analysis.equity import equity_vs_random
from app.analysis.tools import breakeven_bluff, ev_call, pot_odds, spr
from app.config import get_settings
from app.models.canonical import CanonicalHand

MAX_TOOL_ROUNDS = 5

# Ferramentas determinísticas expostas ao Claude (function calling).
TOOLS = [
    {
        "name": "equity",
        "description": "Equity (0-1) do herói por Monte Carlo contra N mãos aleatórias, "
        "dado hole cards e board. Use para ancorar a força da mão.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hero_cards": {"type": "array", "items": {"type": "string"}},
                "board": {"type": "array", "items": {"type": "string"}},
                "num_opponents": {"type": "integer", "default": 1},
            },
            "required": ["hero_cards"],
        },
    },
    {
        "name": "pot_odds",
        "description": "Equity mínima necessária para um call ser neutro em EV = "
        "to_call / (pot + to_call).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pot": {"type": "number"},
                "to_call": {"type": "number"},
            },
            "required": ["pot", "to_call"],
        },
    },
    {
        "name": "ev_call",
        "description": "EV em fichas de pagar, dada a equity. equity*pot - (1-equity)*to_call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "equity": {"type": "number"},
                "pot": {"type": "number"},
                "to_call": {"type": "number"},
            },
            "required": ["equity", "pot", "to_call"],
        },
    },
    {
        "name": "spr",
        "description": "Stack-to-pot ratio = effective_stack / pot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "effective_stack": {"type": "number"},
                "pot": {"type": "number"},
            },
            "required": ["effective_stack", "pot"],
        },
    },
    {
        "name": "breakeven_bluff",
        "description": "Frequência de fold necessária para um blefe lucrar = bet/(pot+bet).",
        "input_schema": {
            "type": "object",
            "properties": {
                "bet": {"type": "number"},
                "pot": {"type": "number"},
            },
            "required": ["bet", "pot"],
        },
    },
    {
        "name": "equity_vs_range",
        "description": "Equity do herói contra um RANGE de vilão (Monte Carlo). PREFIRA esta "
        "à 'equity' sempre que houver contexto da ação — profissional pensa em ranges. "
        "Aceita notação padrão ('TT+, AQs+, KQs') ou 'top 15%'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hero_cards": {"type": "array", "items": {"type": "string"}},
                "villain_range": {"type": "string"},
                "board": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["hero_cards", "villain_range"],
        },
    },
    {
        "name": "preflop_range",
        "description": "Range de referência pré-flop: action='open' (posições UTG/UTG+1/MP/HJ/"
        "CO/BTN/SB) ou action='3bet' (vs EP/MP/CO/BTN). Use como villain_range no "
        "equity_vs_range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "position": {"type": "string"},
                "action": {"type": "string", "enum": ["open", "3bet"]},
            },
            "required": ["position"],
        },
    },
    {
        "name": "icm",
        "description": "Equity em $ real de cada jogador (Malmuth-Harville) dado stacks e "
        "payouts. Use em decisões de mesa final / bubble.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stacks": {"type": "array", "items": {"type": "number"}},
                "payouts": {"type": "array", "items": {"type": "number"}},
            },
            "required": ["stacks", "payouts"],
        },
    },
    {
        "name": "bubble_factor",
        "description": "Pressão de ICM num all-in herói vs vilão: razão $perdido/$ganho "
        "(>1 = precisa de mais equity que chip-EV) e a equity mínima de call "
        "(threshold = bf/(1+bf)).",
        "input_schema": {
            "type": "object",
            "properties": {
                "stacks": {"type": "array", "items": {"type": "number"}},
                "payouts": {"type": "array", "items": {"type": "number"}},
                "hero_idx": {"type": "integer"},
                "villain_idx": {"type": "integer"},
            },
            "required": ["stacks", "payouts", "hero_idx", "villain_idx"],
        },
    },
    {
        "name": "push_fold",
        "description": "Decisão push/fold aproximada de Nash para stack curto (<=20bb) em "
        "torneio, por posição. Retorna decisão, range de shove e percentil da mão. Use em "
        "spots de open-shove de MTT.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cards": {"type": "array", "items": {"type": "string"}},
                "stack_bb": {"type": "number"},
                "position": {"type": "string"},
            },
            "required": ["cards", "stack_bb", "position"],
        },
    },
]

_SYSTEM = {
    "pt": (
        "Você é um coach de pôquer profissional (NLHE). Analise a mão/torneio do aluno "
        "com rigor técnico e objetividade. Regras invioláveis:\n"
        "1) NUNCA invente números. Para qualquer equity, pot odds, EV ou SPR, chame a "
        "ferramenta correspondente e use o valor retornado.\n"
        "2) Pense em RANGES: use preflop_range + equity_vs_range (não equity vs aleatória) "
        "sempre que a ação der contexto do range do vilão.\n"
        "3) Aponte o(s) erro(s) concreto(s), explique a linha melhor e quantifique o impacto.\n"
        "4) Em torneio com stacks/payouts conhecidos, use icm/bubble_factor para a pressão "
        "de ICM; em stack curto, push_fold.\n"
        "5) Termine com um plano curto: 2-3 ações de estudo priorizadas.\n"
        "6) LINGUAGEM ACESSÍVEL: na primeira vez que usar um termo técnico na resposta, "
        "explique entre parênteses de forma curtíssima. Ex.: pot odds (o preço que o pote "
        "te oferece), equity (sua chance de ganhar a mão), range (conjunto de mãos que o "
        "vilão pode ter), 3-bet (re-aumento), SPR (tamanho do stack dividido pelo pote), "
        "ICM (o valor das suas fichas em dinheiro real), c-bet (aposta de continuação), "
        "all-in (apostar tudo). Depois da primeira vez, use o termo normalmente.\n"
        "Formato: é uma mensagem de Telegram — não use cabeçalhos '#'; use *negrito*, "
        "emojis com moderação e parágrafos curtos; máximo ~3000 caracteres.\n"
        "Seja direto e prático. Responda em português."
    ),
    "en": (
        "You are a professional poker coach (NLHE). Analyze the student's hand/tournament "
        "rigorously. Inviolable rules:\n"
        "1) NEVER invent numbers. For any equity, pot odds, EV or SPR, call the matching "
        "tool and use the returned value.\n"
        "2) Point out the concrete mistake(s), explain the better line, quantify the impact.\n"
        "3) Consider position, stack depth and, in MTT, ICM/bubble pressure.\n"
        "4) End with a short plan: 2-3 prioritized study actions.\n"
        "Be direct and practical. Answer in English."
    ),
}


def _dispatch(name: str, args: dict):
    if name == "push_fold":
        from app.analysis.pushfold import push_fold

        return push_fold(args["cards"], args["stack_bb"], args.get("position") or "MP")
    if name == "equity_vs_range":
        from app.analysis.ranges import equity_vs_range

        return equity_vs_range(
            args["hero_cards"], args["villain_range"], args.get("board") or [],
            iterations=4000, seed=17,
        )
    if name == "preflop_range":
        from app.analysis.ranges import preflop_range

        rng = preflop_range(args["position"], args.get("action", "open"))
        return {"range": rng} if rng else {"error": "posição/ação sem chart"}
    if name == "icm":
        from app.analysis.icm import icm_equity

        return {"equities": icm_equity(args["stacks"], args["payouts"])}
    if name == "bubble_factor":
        from app.analysis.icm import bubble_factor, icm_call_threshold

        bf = bubble_factor(args["stacks"], args["payouts"], args["hero_idx"], args["villain_idx"])
        thr = icm_call_threshold(args["stacks"], args["payouts"], args["hero_idx"], args["villain_idx"])
        return {"bubble_factor": bf, "min_call_equity": thr}
    if name == "equity":
        return equity_vs_random(
            args["hero_cards"],
            args.get("board") or [],
            int(args.get("num_opponents", 1)),
            iterations=3000,
            seed=13,
        )
    if name == "pot_odds":
        return pot_odds(args["pot"], args["to_call"])
    if name == "ev_call":
        return ev_call(args["equity"], args["pot"], args["to_call"])
    if name == "spr":
        return spr(args["effective_stack"], args["pot"])
    if name == "breakeven_bluff":
        return breakeven_bluff(args["bet"], args["pot"])
    raise ValueError(f"tool desconhecida: {name}")


def coach(
    structured: dict,
    stats: dict | None = None,
    lang: str = "pt",
    key_hands: list[dict] | None = None,
) -> str:
    """Gera o coaching via Claude. Cai no resumo determinístico se o LLM indisponível.

    `key_hands`: análises das mãos decisivas de um torneio — o Claude narra a
    "história do torneio" em cima delas, além do agregado.
    """
    settings = get_settings()
    fallback = structured.get("summary", "")
    if not settings.anthropic_api_key:
        return fallback

    try:
        from anthropic import Anthropic
    except ImportError:
        return fallback

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        system = _SYSTEM.get(lang, _SYSTEM["pt"])
        context = {"analysis": structured, "player_stats": stats or {}}
        instruction = (
            "Analise esta mão/torneio. Dados estruturados (números já calculados, "
            "use-os; chame tools só para cálculos adicionais):\n\n"
        )
        if key_hands:
            context["key_hands"] = key_hands
            instruction = (
                "Analise este TORNEIO. Além do agregado, conte a 'história do torneio': "
                "os momentos em key_hands foram os que decidiram o resultado — analise "
                "cada um (use push_fold nos spots de stack curto) e conecte-os num "
                "diagnóstico único. Dados estruturados:\n\n"
            )
        messages = [
            {
                "role": "user",
                "content": instruction + json.dumps(context, ensure_ascii=False, indent=2),
            }
        ]

        # prompt caching: system + tools são idênticos em toda chamada -> cache
        # da Anthropic corta o custo das leituras repetidas (TTL ~5 min).
        system_blocks = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        for _ in range(MAX_TOOL_ROUNDS):
            resp = client.messages.create(
                model=settings.analysis_model,
                max_tokens=1500,
                system=system_blocks,
                tools=TOOLS,
                messages=messages,
            )
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text").strip() or fallback

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    try:
                        value = _dispatch(block.name, block.input)
                        if isinstance(value, (int, float)):
                            value = round(value, 4)
                        out = json.dumps({"result": value}, ensure_ascii=False)
                    except Exception as exc:  # erro de tool não derruba a análise
                        out = json.dumps({"error": str(exc)})
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": out}
                    )
            messages.append({"role": "user", "content": tool_results})

        return fallback
    except Exception:
        # qualquer falha de rede/SDK -> resumo determinístico
        return fallback


def followup(
    context: dict,
    history: list[dict],
    question: str,
    lang: str = "pt",
    image_b64: str | None = None,
    media_type: str = "image/jpeg",
) -> str | None:
    """Continua a conversa sobre a última análise, com as mesmas tools.

    `context`: análise estruturada + coaching anterior. `history`: turnos
    anteriores do follow-up [{'q':..., 'a':...}]. Se a análise veio de um print,
    `image_b64` traz a imagem original — o modelo pode RELÊ-LA quando o aluno
    disser que algo foi mal extraído. Retorna None sem chave/erro.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        system = _SYSTEM.get(lang, _SYSTEM["pt"]) + (
            "\nVocê está numa CONVERSA DE ACOMPANHAMENTO sobre uma análise já entregue. "
            "Responda à pergunta do aluno diretamente — sem repetir a análise inteira. "
            "Use as tools para qualquer número novo. Se o aluno discordar ou trouxer "
            "informação nova (range do vilão, dinâmica da mesa), refaça o cálculo com ela."
            + (
                "\nA IMAGEM ORIGINAL do print está anexada: se o aluno disser que algo "
                "foi lido errado ou está faltando, RELEIA a imagem com atenção — nomes, "
                "stacks, posições e a linha de ação completa — e corrija a análise."
                if image_b64
                else ""
            )
        )
        system_blocks = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        ctx_text = "Contexto da análise em discussão:\n" + json.dumps(
            context, ensure_ascii=False, indent=2
        )
        first_content: list | str = ctx_text
        if image_b64:
            first_content = [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                },
                {"type": "text", "text": ctx_text},
            ]
        messages: list[dict] = [
            {"role": "user", "content": first_content},
            {"role": "assistant", "content": "Entendido. Qual a sua dúvida sobre essa mão/torneio?"},
        ]
        for turn in history[-6:]:
            messages.append({"role": "user", "content": turn["q"]})
            messages.append({"role": "assistant", "content": turn["a"]})
        messages.append({"role": "user", "content": question})

        for _ in range(MAX_TOOL_ROUNDS):
            resp = client.messages.create(
                model=settings.analysis_model,
                max_tokens=1200,
                system=system_blocks,
                tools=TOOLS,
                messages=messages,
            )
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text").strip() or None
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    try:
                        value = _dispatch(block.name, block.input)
                        if isinstance(value, (int, float)):
                            value = round(value, 4)
                        out = json.dumps({"result": value}, ensure_ascii=False)
                    except Exception as exc:
                        out = json.dumps({"error": str(exc)})
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": out}
                    )
            messages.append({"role": "user", "content": tool_results})
        return None
    except Exception:
        return None


def synthesize_answer(query: str, snippets: list[str], lang: str = "pt") -> str | None:
    """Sintetiza uma resposta ao /ask a partir dos resumos recuperados (RAG).

    Usa o modelo barato (Haiku) — tarefa simples de síntese, não de julgamento.
    Retorna None sem chave/erro (o chamador mostra os resumos crus).
    """
    settings = get_settings()
    if not settings.anthropic_api_key or not snippets:
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        joined = "\n\n".join(f"- {s}" for s in snippets)
        resp = client.messages.create(
            model=settings.cheap_model,
            max_tokens=500,
            system=(
                "Você é um coach de pôquer. Responda à pergunta do jogador usando APENAS "
                "as análises de mãos fornecidas. Seja direto, aponte o padrão comum entre "
                "as mãos e uma recomendação. Responda em português."
                if lang == "pt"
                else "You are a poker coach. Answer using ONLY the provided hand analyses. "
                "Be direct, point out the common pattern and one recommendation."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Pergunta: {query}\n\nAnálises das mãos relacionadas:\n{joined}",
                }
            ],
        )
        return "".join(b.text for b in resp.content if b.type == "text").strip() or None
    except Exception:
        return None


_VISION_PROMPT = (
    "Você recebe um print/foto de pôquer (mesa ao vivo OU replay/histórico de mão — "
    "replays do GGPoker/PokerStars mostram a ação completa: LEIA TUDO). Extraia "
    "ABSOLUTAMENTE TODO detalhe visível e retorne APENAS um JSON:\n"
    "{\n"
    '  "site": "<sala ou null>",\n'
    '  "format": "cash|tournament",\n'
    '  "hero_name": "<nome do jogador em destaque/na parte de baixo/com cartas abertas>",\n'
    '  "hero_cards": ["As","Kd"],\n'
    '  "blinds": {"small_blind":0, "big_blind":0, "ante":0, "currency":"USD"},\n'
    '  "players": [{"seat":1,"name":"...","stack":1500,"position":"BTN","cards":["..."]}],\n'
    '  "actions": {                          // TODA ação visível, na ordem\n'
    '    "preflop": [{"actor":"nome","action":"fold|check|call|bet|raise|post|allin","amount":0,"to_amount":0}],\n'
    '    "flop": [], "turn": [], "river": []\n'
    "  },\n"
    '  "board": {"flop":["Ah","7c","2d"], "turn":"9s", "river":"Kc"},\n'
    '  "total_pot": 0,\n'
    '  "winner": "<nome ou null>"\n'
    "}\n"
    "Regras: cartas em 2 caracteres (rank 23456789TJQKA, naipe cdhs; '10' vira 'T'). "
    "Posições: UTG/MP/HJ/CO/BTN/SB/BB quando visíveis (o botão do dealer indica o BTN). "
    "Em replay, transcreva a linha de ação inteira street a street com os valores exatos. "
    "Campo ilegível = null/vazio. NÃO invente valores — extraia só o que está na imagem."
)


def extract_from_image(image_bytes: bytes, media_type: str = "image/png") -> CanonicalHand | None:
    """Extrai um snapshot de mão de um print via visão do Claude.

    Retorna um `CanonicalHand` parcial com `confidence` < 1.0 (dado de visão é menos
    confiável que hand history nativa). Sem chave/lib ou em falha, retorna None.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        b64 = base64.standard_b64encode(image_bytes).decode()
        resp = client.messages.create(
            model=settings.analysis_model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": b64},
                        },
                        {"type": "text", "text": _VISION_PROMPT},
                    ],
                }
            ],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        data = json.loads(_strip_code_fence(text))
        return _snapshot_to_canonical(data)
    except Exception:
        return None


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
    return t.strip()


def _norm_card(card) -> str | None:
    """Normaliza carta da visão: '10h'->'Th', 'AS'->'As'. None se irrecuperável."""
    if not card or not isinstance(card, str):
        return None
    c = card.strip().replace("10", "T")
    if len(c) != 2:
        return None
    rank, suit = c[0].upper(), c[1].lower()
    if rank not in "23456789TJQKA" or suit not in "cdhs":
        return None
    return rank + suit


def _norm_cards(cards) -> list[str]:
    return [n for n in (_norm_card(c) for c in (cards or [])) if n]


def _snapshot_to_canonical(data: dict) -> CanonicalHand | None:
    from app.models.canonical import (
        Action,
        ActionType,
        HandFormat,
        PlayerSeat,
        Stakes,
        Street,
        StreetName,
    )

    blinds = data.get("blinds") or data.get("stakes") or {}
    stakes = Stakes(
        small_blind=float(blinds.get("small_blind") or 0),
        big_blind=float(blinds.get("big_blind") or 0),
        ante=float(blinds.get("ante") or 0),
        currency=blinds.get("currency") or "USD",
    )

    hero_name = data.get("hero_name")
    players = []
    for p in data.get("players") or []:
        if "seat" not in p or p.get("stack") is None:
            continue
        try:
            players.append(
                PlayerSeat(
                    seat=int(p["seat"]),
                    name=str(p.get("name") or f"seat{p['seat']}"),
                    stack=float(p["stack"]),
                    position=p.get("position"),
                    is_hero=bool(hero_name and p.get("name") == hero_name),
                )
            )
        except Exception:
            continue

    # boards cumulativos por street
    board_info = data.get("board") or {}
    flop = _norm_cards(board_info.get("flop"))
    turn_c = _norm_card(board_info.get("turn"))
    river_c = _norm_card(board_info.get("river"))
    final_board = _norm_cards(data.get("final_board")) or (
        flop + ([turn_c] if turn_c else []) + ([river_c] if river_c else [])
    )

    # ações por street (o coração da análise)
    _ACT = {
        "fold": ActionType.FOLD, "check": ActionType.CHECK, "call": ActionType.CALL,
        "bet": ActionType.BET, "raise": ActionType.RAISE, "post": ActionType.POST,
        "allin": ActionType.RAISE, "all-in": ActionType.RAISE, "all_in": ActionType.RAISE,
    }
    actions_in = data.get("actions") or {}
    streets: list[Street] = []
    boards = {
        StreetName.PREFLOP: [],
        StreetName.FLOP: flop,
        StreetName.TURN: flop + ([turn_c] if turn_c else []),
        StreetName.RIVER: final_board,
    }
    for sname in (StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN, StreetName.RIVER):
        raw = actions_in.get(sname.value) or []
        acts = []
        for a in raw:
            kind = _ACT.get(str(a.get("action", "")).lower())
            if not kind or not a.get("actor"):
                continue
            is_allin = str(a.get("action", "")).lower().startswith("all")
            try:
                acts.append(
                    Action(
                        actor=str(a["actor"]),
                        type=kind,
                        amount=float(a.get("amount") or 0),
                        to_amount=float(a.get("to_amount") or a.get("amount") or 0),
                        all_in=is_allin,
                    )
                )
            except Exception:
                continue
        if acts or (sname != StreetName.PREFLOP and boards[sname]):
            streets.append(Street(name=sname, board=boards[sname], actions=acts))
        elif sname == StreetName.PREFLOP and acts:
            streets.append(Street(name=sname, actions=acts))

    has_actions = any(s.actions for s in streets)
    fmt = data.get("format") or "cash"
    hand = CanonicalHand(
        hand_id="vision-snapshot",
        site=data.get("site") or "unknown",
        format=HandFormat(fmt) if fmt in ("cash", "tournament", "sng") else HandFormat.CASH,
        stakes=stakes,
        hero=hero_name,
        players=players,
        hero_cards=_norm_cards(data.get("hero_cards")),
        streets=streets,
        final_board=final_board,
        total_pot=data.get("total_pot") or data.get("pot"),
        source_format="image",
        # com a linha de ação lida, o dado é quase tão bom quanto hand history
        confidence=0.85 if has_actions else 0.7,
    )
    if data.get("winner") and hand.total_pot:
        hand.collected[str(data["winner"])] = float(hand.total_pot)
    return hand
