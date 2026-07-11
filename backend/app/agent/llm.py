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
import logging

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
        "name": "solve_river",
        "description": "SOLVER de river (CFR+, equilíbrio real do sub-jogo): dado board de 5 "
        "cartas, ranges OOP/IP (notação padrão), pote e stack efetivo, retorna a estratégia "
        "de equilíbrio (frequência de check/bet/jam por range + exemplos de mãos). Use nos "
        "spots de river importantes; ranges estreitos (<900 combos).",
        "input_schema": {
            "type": "object",
            "properties": {
                "board": {"type": "array", "items": {"type": "string"}},
                "oop_range": {"type": "string"},
                "ip_range": {"type": "string"},
                "pot": {"type": "number"},
                "stack": {"type": "number"},
                "player": {"type": "string", "enum": ["oop", "ip"]},
            },
            "required": ["board", "oop_range", "ip_range", "pot", "stack"],
        },
    },
    {
        "name": "population_tendencies",
        "description": "EXPLORATIVO: frequências agregadas do field (fold/call/raise contra "
        "agressão por street) calculadas das mãos reais armazenadas, com dicas de exploit. "
        "Use para recomendar desvios lucrativos do equilíbrio. Cautela com amostra pequena.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_hands",
        "description": "BUSCA no histórico de mãos do PRÓPRIO aluno por padrão de "
        "ação: use quando ele pedir 'analise todos os meus c-bets/folds/all-ins/"
        "3-bets' ou quando você precisar de VOLUME para achar um padrão. Retorna "
        "resumos compactos (cartas, posição, stacks em BB, linha do herói, "
        "resultado). pattern: cbet|fold|call|raise|3bet|allin|bet|check|showdown|"
        "win|loss. street opcional restringe (preflop|flop|turn|river).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string",
                            "enum": ["cbet", "fold", "call", "raise", "3bet",
                                     "allin", "bet", "check", "showdown", "win", "loss"]},
                "street": {"type": "string",
                           "enum": ["preflop", "flop", "turn", "river"]},
                "limit": {"type": "integer", "default": 12},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "read_villain",
        "description": "LEITURA DO RANGE DO VILÃO: o range começa no chart da "
        "posição dele e cada ação (bet/check/call/raise, com sizing) reponderada "
        "as mãos possíveis — devolve as fatias valor/média/draw/ar por street e "
        "a leitura em odds ('cerca de 4 pra 1 que é valor'). Use SEMPRE que a "
        "decisão do aluno for pagar/largar contra apostas: narre como a linha do "
        "vilão mudou a leitura. preflop: como o vilão entrou (open|call|3bet). "
        "actions na ordem: board_cards diz a street (3=flop, 4=turn, 5=river).",
        "input_schema": {
            "type": "object",
            "properties": {
                "position": {"type": "string"},
                "preflop": {"type": "string", "enum": ["open", "call", "3bet"]},
                "board": {"type": "array", "items": {"type": "string"}},
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "board_cards": {"type": "integer"},
                            "action": {"type": "string",
                                       "enum": ["bet", "check", "call", "raise"]},
                            "size_pct_pot": {"type": "number"},
                        },
                        "required": ["board_cards", "action"],
                    },
                },
                "hero_cards": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["position", "board", "actions"],
        },
    },
    {
        "name": "get_hand",
        "description": "ABRE uma mão específica do histórico do PRÓPRIO aluno "
        "quando ele cita o Nº da mão (ex.: 'TM6146070388' — vem no relatório "
        "mão a mão e no PokerCraft) ou as cartas (ex.: 'a mão do A3o', 'meus "
        "reis', 'Ah 3c'). Retorna a história lance a lance + números calculados "
        "(pot odds, equity, sizing, stacks em BB) para você analisar EXATAMENTE "
        "aquela mão — nunca diga que não tem acesso à mão antes de tentar isto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "Nº da mão OU cartas (A3o, KK, Ah 3c)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "compare_style_to_pros",
        "description": "Classifica o ESTILO do aluno (eixos VPIP/PFR/AF/3-bet) e o "
        "compara com perfis públicos de grandes jogadores (Yuri Dzivielevski, Akkari, "
        "Rafael Moraes, Ivey, Dwan, Negreanu, Loeliger...). Se o aluno quiser MUDAR de "
        "estilo, passe desired ('tag'|'lag'|'gto'|'exploit') e receba o caminho de "
        "transição com ajustes numéricos. Use quando o aluno perguntar sobre estilo, "
        "'com quem eu pareço' ou 'como jogar mais agressivo'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "vpip": {"type": "number"},
                "pfr": {"type": "number"},
                "af": {"type": "number"},
                "three_bet": {"type": "number"},
                "desired": {"type": "string", "enum": ["tag", "lag", "gto", "exploit"]},
            },
            "required": ["vpip", "pfr", "af", "three_bet"],
        },
    },
    {
        "name": "record_student_note",
        "description": "Anota no CADERNO do aluno uma observação duradoura sobre o "
        "jogo dele: um leak identificado, um progresso visível, uma meta combinada "
        "ou um traço de estilo. Use 1x por análise quando houver algo que valha "
        "lembrar na próxima sessão. NÃO anote números de uma mão específica.",
        "input_schema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["leak", "progresso", "meta", "estilo"]},
                "note": {"type": "string", "description": "1-2 frases, específicas e acionáveis"},
            },
            "required": ["kind", "note"],
        },
    },
    {
        "name": "send_range_chart",
        "description": "ENVIA ao aluno um gráfico de range 13×13 como imagem, logo após a "
        "sua resposta. Use SEMPRE que o aluno pedir 'tabela', 'gráfico', 'range' ou 'EV "
        "das mãos'. Modos: (a) range específico — passe range_notation + title; "
        "(b) equilíbrio jam/fold — passe role (SB|BB) + stack_bb + mode "
        "('freq' | 'ev' chip | 'icm' com bf); (c) OPEN-SHOVE por posição (stack "
        "<=20bb) — passe position (UTG/MP/CO/BTN) + stack_bb: sai o range de shove "
        "aproximado de Nash (top X%), o MESMO do push_fold. Para spot de shove use "
        "SEMPRE (c) — NUNCA mande range de abertura de stack fundo. Confirme na "
        "resposta que o gráfico segue abaixo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "range_notation": {"type": "string"},
                "title": {"type": "string"},
                "role": {"type": "string", "enum": ["SB", "BB"]},
                "position": {"type": "string"},
                "stack_bb": {"type": "number"},
                "mode": {"type": "string", "enum": ["freq", "ev", "icm"]},
                "bf": {"type": "number"},
            },
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


# Glossário de terminologia — REGRA DURA, usado em todas as camadas de texto
# (análise, por-mão, simplificação). O modelo inventa calques se deixar.
TERMOS_REGRA = (
    "TERMINOLOGIA (regra dura): use os termos consagrados do poker BR. "
    "FICAM EM INGLÊS: top pair, overpair, kicker, flush draw, gutshot, OESD, "
    "set, fold equity, equity, cooler, bad beat, blockers, range, c-bet, "
    "3-bet, 4-bet, all-in, heads-up, multiway, squeeze, limp. "
    "PORTUGUÊS CONSAGRADO: pagar (call), largar/foldar, aumentar, trinca, "
    "dominado/dominação, apostar por valor, blefar. "
    "CALQUES PROIBIDOS (não existem no poker BR): 'par grande', 'mão grande', "
    "'par alto', 'domínio' (é DOMINADO/dominação), 'como valor' (é POR "
    "valor), 'sequência de cor', 'igualar' (é pagar), 'rua'/'etapa'/'rodada' "
    "para street (diga STREET, ou nomeie: no flop, no turn, no river). "
    "REGISTRO: sempre 'você' — nunca 'tu/teu/te contigo' misturado. "
    "Ao explicar para iniciante, o termo REAL fica e a explicação vem entre "
    "parênteses na primeira vez: 'top pair (o maior par possível com essa "
    "mesa)'. NUNCA substitua o termo por tradução inventada."
)

_SYSTEM = {
    "pt": (
        "Você é um coach de poker brasileiro experiente (NLHE) conversando com seu "
        "aluno pelo Telegram. VOZ: papo de mesa — informal, direto e claro, como um "
        "amigo que é crack no jogo. Fale com 'você', use a linguagem natural do poker "
        "BR (vilão, pagar, largar, shove, brigar pelo pote). PROIBIDO soar como "
        "sistema ou chatbot: nunca mencione erros/correções/versões do sistema, "
        "'ferramentas', 'dados fornecidos', 'como assistente' ou qualquer bastidor — "
        "você é um coach, não um software.\n"
        "CLAREZA (regra de ouro): comece pelo veredito em UMA frase simples ('Aqui é "
        "call tranquilo', 'Esse fold custou caro'). Depois o porquê: frases curtas, "
        "uma ideia por frase. Use no MÁXIMO 1-2 números por ponto — os que mudam a "
        "decisão — e diga o que o número significa ('o pote te dava 3 pra 1: você "
        "precisa acertar 1 vez a cada 4'). Nada de despejar estatística. "
        "PROIBIDO adjetivar o próprio veredito: nunca escreva 'resumo brutal', "
        "'verdade honesta', 'papo reto', 'na lata', 'sem enrolação' — o resumo "
        "chama-se 'Resumo' e a análise fala por si.\n"
        "Regras invioláveis:\n"
        "1) NUNCA invente números. Para qualquer equity, pot odds, EV ou SPR, chame a "
        "ferramenta correspondente e use o valor retornado.\n"
        "1b) INSUMOS da conta (pote, preço a pagar, sizing, stacks): valem os do "
        "contexto, os lidos da imagem E os que o ALUNO INFORMOU (relato_do_usuario "
        "ou a própria conversa) — número dito pelo aluno é insumo legítimo, "
        "passe-o para a ferramenta. PROIBIDO responder 'não dá para calcular por "
        "falta de X' sem antes procurar X no que o aluno escreveu; se X não "
        "estiver em lugar nenhum, PERGUNTE o dado exato que falta (um só, o mais "
        "decisivo) em vez de desistir da conta.\n"
        "2) Pense em RANGES: use preflop_range + equity_vs_range (não equity vs aleatória) "
        "sempre que a ação der contexto do range do vilão.\n"
        "2b) CONSISTÊNCIA DE VEREDITO: decisão preflop se ancora no range de "
        "referência — chame preflop_range e compare; NÃO decida de memória. "
        "Mesma mão + mesma posição + mesma ação = MESMO veredito, sempre; o "
        "aluno reenvia mãos para conferir e resposta que muda destrói a "
        "confiança. Frequência mista ('3-bet 25% das vezes') NUNCA é o "
        "conselho: entregue UMA ação prática clara ('contra abertura de CO, "
        "99 é call; o 3-bet só entra contra quem abre demais e desiste "
        "demais') e cite a frequência, se citar, como nuance — nunca como "
        "correção do que foi dito antes.\n"
        "3) Aponte o(s) erro(s) concreto(s), explique a linha melhor e quantifique o impacto.\n"
        "4) Em torneio com stacks/payouts conhecidos, use icm/bubble_factor para a pressão "
        "de ICM; em stack curto, push_fold (para SB/BB retorna EQUILÍBRIO CALCULADO — "
        "diga isso ao aluno). Em decisões de river relevantes, use solve_river (equilíbrio "
        "CFR+ do sub-jogo). Para recomendar exploits, consulte population_tendencies. "
        "Se o aluno pedir TABELA/GRÁFICO de range ou de EV, chame send_range_chart — "
        "nunca diga que não consegue enviar imagem. TABELA de spot de SHOVE (stack "
        "curto): o range do gráfico é o MESMO do push_fold — passe position + "
        "stack_bb; NUNCA desenhe range de abertura de stack fundo para spot de "
        "shove (contradiz o veredito).\n"
        "4b) STACKS: use SEMPRE hero_stack_bb/effective_bb/stacks_bb do contexto — "
        "NUNCA estime o stack (o valor do big blind NÃO é o stack!). Em all-in, "
        "o que manda é o stack EFETIVO: min(seu stack, stack do vilão relevante). "
        "Shove de stack grande contra vilão curto = jam do efetivo curto.\n"
        "4c) VOLUME: quando o aluno pedir análise de um PADRÃO (todos os c-bets/"
        "folds dele), chame search_hands e analise o CONJUNTO — não responda por "
        "uma mão só. Em lotes grandes: 3 momentos-chave + 1 leak + plano, sem "
        "narrar mão a mão.\n"
        "4d) MÃO ESPECÍFICA: se o aluno citar o Nº de uma mão (ex.: TM614607…, "
        "está no relatório mão a mão) ou as cartas ('abre a mão do A3o'), chame "
        "get_hand e analise AQUELA mão com a história e os números retornados.\n"
        "4e) LEITURA DE VILÃO: quando a decisão for pagar/largar contra apostas, "
        "chame read_villain com a linha do vilão e NARRE a mudança na voz de "
        "coach: 'antes do bet eu dava 40% de blefe; o sizing derrubou pra 20% — "
        "4 pra 1 que é valor'. Compare com o preço do call. É estimativa de "
        "field: diga 'por comportamento típico' quando a amostra do vilão for "
        "desconhecida.\n"
        "4f) NÃO ENTENDEU: se o aluno disser 'não entendi', 'como assim', "
        "'muito complicado' ou parecido, reexplique a MESMA ideia para um "
        "iniciante total — uma analogia do dia a dia, zero jargão, no máximo 1 "
        "número explicado. NÃO introduza conceito novo nem avance matéria.\n"
        "4g) PSICOLOGIA (vieses de decisão): (a) NUNCA julgue pelo resultado — "
        "avalie a decisão pelo preço na hora; perder com decisão boa é "
        "variância, diga isso. (b) Se o aluno disser 'sempre' perco com X / "
        "tomo bad beat, busque a taxa REAL no histórico dele (search_hands) e "
        "responda com o número. (c) Depois de downswing, segure mudança de "
        "estratégia: se os fundamentos não mudaram, o resultado foi "
        "distribuição — regressão à média. (d) Custo afundado: as fichas que "
        "já estão no pote não são mais do aluno; o call se justifica só pelo "
        "preço atual.\n"
        "5) Termine com um plano curto: 2-3 ações de estudo priorizadas.\n"
        "5a) CADERNO DO ALUNO: quando identificar um leak recorrente, um progresso real ou combinar uma meta, chame record_student_note (1x por análise). É a sua memória de coach entre sessões.\n"
        "5b) PRECISÃO DE NOTAÇÃO: cite as mãos com suited/offsuit correto — cartas de "
        "naipes diferentes são 'o' (ex.: Ad 3c = A3o), naipes iguais são 's'. Confira "
        "antes de escrever.\n"
        "5c) " + TERMOS_REGRA + "\n"
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
        "1b) Tool INPUTS (pot, price to call, sizing, stacks) may come from the "
        "context, the image OR the student's own words — a number the student "
        "stated is a legitimate input; pass it to the tool. Never answer 'cannot "
        "compute for lack of X' without first checking what the student wrote; "
        "if X is truly missing, ASK for that exact datum instead of giving up.\n"
        "2) Point out the concrete mistake(s), explain the better line, quantify the impact.\n"
        "3) Consider position, stack depth and, in MTT, ICM/bubble pressure.\n"
        "4) End with a short plan: 2-3 prioritized study actions.\n"
        "5) NOTATION: quote hands with correct suited/offsuit — different suits = 'o' "
        "(Ad 3c = A3o), same suit = 's'. Double-check before writing.\n"
        "Be direct and practical. Answer in English."
    ),
}


import contextvars

# usuário dono da conversa atual — permite tools user-scoped (search_hands)
# sem acoplar o dispatch à assinatura de cada loop
_TOOL_USER: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_TOOL_USER", default=None
)


def set_tool_user(user_id: str | None) -> None:
    _TOOL_USER.set(user_id)


# modelos que REJEITAM o parâmetro temperature (400 'temperature is
# deprecated for this model') — descoberto em produção: o deploy da
# consistência derrubou a leitura de prints inteira
_NO_TEMP: set[str] = set()


def _create(client, **kw):
    """client.messages.create com fallback: se o modelo rejeitar temperature,
    refaz sem o parâmetro e memoriza (a consistência fica por conta das
    regras de prompt nesses modelos)."""
    model = kw.get("model")
    if model in _NO_TEMP:
        kw.pop("temperature", None)
    try:
        return client.messages.create(**kw)
    except Exception as exc:
        if "temperature" in str(exc) and kw.pop("temperature", None) is not None:
            _NO_TEMP.add(model)
            logging.getLogger("llm").warning(
                "modelo %s rejeita temperature; seguindo sem", model)
            return client.messages.create(**kw)
        raise


def _coerce_args(args: dict) -> dict:
    """Normaliza argumentos vindos do modelo: cartas em string -> lista, '10h' ->
    'Th', naipe unicode -> letra, números em string ('10bb') -> float. O modelo
    erra formato com frequência — erro críptico aqui queima rounds de tool."""
    import re as _re

    args = dict(args or {})
    for key in ("cards", "hero_cards", "board"):
        v = args.get(key)
        if isinstance(v, str):
            v = [t for t in _re.split(r"[,\s]+", v.strip()) if t]
        if isinstance(v, list):
            args[key] = [(_norm_card(c) or str(c)) for c in v]
    for key in ("stack_bb", "pot", "to_call", "stack", "bet", "effective_stack",
                "equity", "bf", "num_opponents"):
        v = args.get(key)
        if isinstance(v, str):
            try:
                args[key] = float(v.lower().replace("bb", "").strip())
            except ValueError:
                pass
    return args


def _dispatch(name: str, args: dict):
    args = _coerce_args(args)
    if name == "search_hands":
        from app.analysis.handsearch import search_hands
        from app.db import get_repository

        user_id = _TOOL_USER.get()
        repo = get_repository()
        if not user_id or not repo.enabled:
            return {"error": "histórico indisponível nesta conversa"}
        hands = repo.get_all_hands(user_id, limit=500)
        found = search_hands(hands, str(args.get("pattern") or ""),
                             args.get("street"),
                             int(args.get("limit") or 12))
        return {"total_no_filtro": len(found), "maos": found} if found else {
            "total_no_filtro": 0,
            "info": "nenhuma mão do aluno casa com esse filtro"}
    if name == "read_villain":
        from app.analysis.rangetracker import read_villain

        return read_villain(
            str(args.get("position") or "MP"),
            str(args.get("preflop") or "open"),
            list(args.get("board") or []),
            list(args.get("actions") or []),
            list(args.get("hero_cards") or []),
        )
    if name == "get_hand":
        from app.analysis.handsearch import find_hand
        from app.db import get_repository

        user_id = _TOOL_USER.get()
        repo = get_repository()
        if not user_id or not repo.enabled:
            return {"error": "histórico indisponível nesta conversa"}
        hands = repo.get_all_hands(user_id, limit=500)
        found = find_hand(hands, str(args.get("query") or ""))
        return {"encontradas": len(found), "maos": found} if found else {
            "encontradas": 0,
            "info": "nenhuma mão do aluno casa com esse Nº/cartas — peça o Nº "
                    "da mão (está no relatório) ou as cartas exatas"}
    if name == "compare_style_to_pros":
        from app.analysis.pro_styles import match_pro_style

        return match_pro_style(
            float(args.get("vpip") or 0), float(args.get("pfr") or 0),
            float(args.get("af") or 0), float(args.get("three_bet") or 0),
            args.get("desired"),
        )
    if name == "record_student_note":
        # a nota é coletada por charts_from_tool_call e persistida pelo caller
        if not (args.get("note") or "").strip():
            return {"error": "note vazia"}
        return {"ok": True, "info": "anotado no caderno do aluno"}
    if name == "send_range_chart":
        # valida JÁ: confirmar "gráfico agendado" e não entregar destrói a
        # confiança do aluno — erro aqui deixa o modelo se corrigir
        if args.get("range_notation"):
            from app.analysis.ranges import parse_range

            try:
                parse_range(str(args["range_notation"]))
            except ValueError as exc:
                return {"error": f"notação de range inválida: {exc}"}
            return {"ok": True, "info": "gráfico agendado — será enviado após a resposta"}
        role = str(args.get("role") or "").upper()
        stack = args.get("stack_bb")
        if role in ("SB", "BB") and isinstance(stack, (int, float)) and stack > 0:
            if args.get("mode") in ("ev", "icm"):
                from app.analysis.jam_fold_solver import available as _solver_ok

                if not _solver_ok():
                    return {"error": "solver de EV indisponível — use mode='freq'"}
            else:
                from app.analysis.nash_pushfold import available as _nash_ok

                if not _nash_ok():
                    return {"error": "tabela Nash indisponível"}
            return {"ok": True, "info": "gráfico agendado — será enviado após a resposta"}
        pos = str(args.get("position") or "").upper()
        if pos and isinstance(stack, (int, float)) and stack > 0:
            from app.analysis.pushfold import shove_threshold

            if shove_threshold(pos, float(stack)) is None:
                return {"error": "stack acima de 20bb: não é spot de open-shove — "
                                 "use range_notation com o range de abertura"}
            return {"ok": True, "info": "gráfico agendado — será enviado após a resposta"}
        return {"error": "parâmetros insuficientes: passe range_notation OU "
                         "role ('SB'/'BB') + stack_bb OU position + stack_bb (<=20)"}
    if name == "push_fold":
        from app.analysis.nash_pushfold import nash_jam_fold
        from app.analysis.pushfold import push_fold

        pos = (args.get("position") or "MP").upper()
        if pos in ("SB", "BB"):
            exact = nash_jam_fold(args["cards"], args["stack_bb"], pos)
            if exact:
                return exact
        return push_fold(args["cards"], args["stack_bb"], pos)
    if name == "solve_river":
        from app.analysis.river_solver import solve_river

        return solve_river(
            args["board"], args["oop_range"], args["ip_range"],
            args["pot"], args["stack"], args.get("player", "oop"),
        )
    if name == "population_tendencies":
        from app.analysis.population import exploit_hints, population_tendencies
        from app.db import get_repository

        repo = get_repository()
        hands = repo.get_population_hands(limit=2000) if repo.enabled else []
        if not hands:
            return {"error": "sem dados de população ainda"}
        t = population_tendencies(hands)
        t["exploits"] = exploit_hints(t)
        return t
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
        if not args.get("to_call") or args["to_call"] <= 0:
            return {"error": "to_call deve ser > 0 (sem aposta a pagar não há pot odds)"}
        return pot_odds(args["pot"], args["to_call"])
    if name == "ev_call":
        return ev_call(args["equity"], args["pot"], args["to_call"])
    if name == "spr":
        if not args.get("pot") or args["pot"] <= 0:
            return {"error": "pot deve ser > 0 para calcular SPR"}
        return spr(args["effective_stack"], args["pot"])
    if name == "breakeven_bluff":
        return breakeven_bluff(args["bet"], args["pot"])
    raise ValueError(f"tool desconhecida: {name}")


def charts_from_tool_call(name: str, args: dict, result) -> tuple | None:
    """Se a tool usada implica um range visualizável, retorna a spec do gráfico.

    Specs: ("range", notacao, titulo) | ("nash", role, stack_bb)
         | ("nashmode", role, stack_bb, mode, bf)
    """
    try:
        if isinstance(result, dict) and result.get("error"):
            return None  # tool falhou — não prometer gráfico que não sai
        if name == "record_student_note":
            kind = args.get("kind") or "leak"
            note = (args.get("note") or "").strip()
            return ("note", kind, note) if note else None
        if name == "send_range_chart":
            args = _coerce_args(args)
            if args.get("range_notation"):
                return ("range", args["range_notation"],
                        args.get("title") or "Range")
            if args.get("role") and args.get("stack_bb"):
                return ("nashmode", str(args["role"]).upper(), float(args["stack_bb"]),
                        args.get("mode") or "freq", float(args.get("bf") or 1.5))
            if args.get("position") and args.get("stack_bb"):
                from app.analysis.pushfold import shove_threshold

                pos = str(args["position"]).upper()
                stk = float(args["stack_bb"])
                pct = shove_threshold(pos, stk)
                if pct:
                    return ("range", f"top {round(pct * 100)}%",
                            f"Shove {pos} ~{stk:g}bb (aprox. Nash)")
            return None
        if name == "equity_vs_range" and args.get("villain_range"):
            return ("range", args["villain_range"], "Range assumido do vilão")
        if name == "preflop_range" and isinstance(result, dict) and result.get("range"):
            pos = args.get("position", "?").upper()
            act = args.get("action", "open")
            return ("range", result["range"], f"Range de {act} — {pos}")
        if name == "push_fold" and isinstance(result, dict) and result.get("role"):
            return ("nash", result["role"], float(result.get("stack_resolvido") or
                                                  result.get("stack_bb") or 10))
        if (name == "push_fold" and isinstance(result, dict)
                and result.get("applicable") and result.get("shove_range_pct")):
            # posições fora de SB/BB: o gráfico É o range do veredito (top X%) —
            # sem isto o modelo desenhava range de abertura de stack fundo num
            # spot de shove e contradizia o próprio conselho
            return ("range", f"top {result['shove_range_pct']:g}%",
                    f"Shove {result.get('position', '?')} "
                    f"~{float(result.get('stack_bb') or 10):g}bb (aprox. Nash)")
    except Exception:
        return None
    return None


def coach(
    structured: dict,
    stats: dict | None = None,
    lang: str = "pt",
    key_hands: list[dict] | None = None,
    collect_charts: list | None = None,
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
        parts: list[str] = []  # texto escrito ANTES das tools não pode sumir
        for _ in range(MAX_TOOL_ROUNDS):
            resp = _create(client,
                model=settings.analysis_model,
                max_tokens=1500,
                temperature=0.2,  # coach não pode mudar de veredito por sorteio
                system=system_blocks,
                tools=TOOLS,
                messages=messages,
            )
            parts.extend(b.text for b in resp.content if b.type == "text")
            if resp.stop_reason != "tool_use":
                final = "\n\n".join(x.strip() for x in parts if x.strip())
                return final or fallback

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    try:
                        value = _dispatch(block.name, block.input)
                        if collect_charts is not None:
                            spec = charts_from_tool_call(block.name, block.input, value)
                            if spec and spec not in collect_charts:
                                collect_charts.append(spec)
                        if isinstance(value, (int, float)):
                            value = round(value, 4)
                        out = json.dumps({"result": value}, ensure_ascii=False)
                    except Exception as exc:  # erro de tool não derruba a análise
                        out = json.dumps({"error": str(exc)})
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": out}
                    )
            messages.append({"role": "user", "content": tool_results})

        # rodadas esgotadas: entrega o que já foi escrito em vez de jogar fora
        final = "\n\n".join(x.strip() for x in parts if x.strip())
        return final or fallback
    except Exception:
        # qualquer falha de rede/SDK -> resumo determinístico
        return fallback


def simplify(text: str) -> str | None:
    """Reescreve a última explicação do coach para um iniciante TOTAL.

    Modelo barato, sem tools — resposta rápida. None se o LLM está fora.
    """
    from app.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key or not (text or "").strip():
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        resp = _create(client,
            model=settings.cheap_model,
            max_tokens=700,
            temperature=0.2,
            system=(
                "Você é um coach de poker explicando para alguém que NUNCA "
                "estudou o jogo. Reescreva a explicação abaixo mantendo o mesmo "
                "veredito e a mesma ideia: frases curtas, UMA analogia do dia a "
                "dia, no máximo 1 número — e diga o que ele significa. "
                + TERMOS_REGRA + " "
                "Português informal, até ~120 palavras, formato Telegram (sem "
                "cabeçalhos). Nunca mencione que isto é uma reescrita."
            ),
            messages=[{"role": "user", "content": text[:6000]}],
        )
        out = "".join(b.text for b in resp.content if b.type == "text").strip()
        return out or None
    except Exception:
        return None


def followup(
    context: dict,
    history: list[dict],
    question: str,
    lang: str = "pt",
    image_b64: str | None = None,
    media_type: str = "image/jpeg",
    collect_charts: list | None = None,
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
            "\nVocê está numa CONVERSA com o aluno. Se o contexto trouxer uma análise, "
            "é acompanhamento dela: responda direto, sem repetir a análise inteira. "
            "Se o contexto indicar 'coaching geral', responda a pergunta como coach de "
            "poker (bad beats/tilt, estratégia, bankroll, ranges, mental game) — use o "
            "perfil_do_jogador para personalizar quando existir. Use as tools para "
            "qualquer número. Se o aluno discordar ou trouxer informação nova (range do "
            "vilão, dinâmica da mesa), refaça o cálculo com ela."
            "\nCOERÊNCIA: o contexto traz o veredito já dado. Sem informação NOVA, "
            "o veredito é o MESMO — proibido mudar de conselho entre mensagens por "
            "conta própria. Se um dado novo mudar a leitura, diga explicitamente: "
            "'isso muda o que eu disse, porque X'. Nunca apresente uma frequência "
            "de solver como se contradissesse o conselho anterior."
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

        parts: list[str] = []  # texto escrito ANTES das tools não pode sumir
        for _ in range(MAX_TOOL_ROUNDS):
            resp = _create(client,
                model=settings.analysis_model,
                max_tokens=1200,
                temperature=0.2,  # mesma pergunta, mesma resposta
                system=system_blocks,
                tools=TOOLS,
                messages=messages,
            )
            parts.extend(b.text for b in resp.content if b.type == "text")
            if resp.stop_reason != "tool_use":
                final = "\n\n".join(x.strip() for x in parts if x.strip())
                return final or None
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    try:
                        value = _dispatch(block.name, block.input)
                        if collect_charts is not None:
                            spec = charts_from_tool_call(block.name, block.input, value)
                            if spec and spec not in collect_charts:
                                collect_charts.append(spec)
                        if isinstance(value, (int, float)):
                            value = round(value, 4)
                        out = json.dumps({"result": value}, ensure_ascii=False)
                    except Exception as exc:
                        out = json.dumps({"error": str(exc)})
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": out}
                    )
            messages.append({"role": "user", "content": tool_results})
        final = "\n\n".join(x.strip() for x in parts if x.strip())
        return final or None
    except Exception:
        return None


def evaluate_line(sim_data: dict, lang: str = "pt",
                  collect_charts: list | None = None) -> str | None:
    """Modo "e se": avalia a linha ALTERNATIVA que o aluno escolheu na simulação.

    Para cada decisão divergente da real, julga (com as tools) se a escolha do
    aluno era melhor, pior ou equivalente — e quantifica. None sem chave/erro.
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
            "\nMODO 'E SE': o aluno acabou de jogar uma SIMULAÇÃO de uma mão real dele. "
            "Compare a linha que ELE escolheu com a linha real, decisão a decisão:\n"
            "- Onde coincidiu: valide em 1 frase.\n"
            "- Onde divergiu: julgue qual era melhor (use equity_vs_range/pot_odds/"
            "push_fold para os números) e estime o impacto.\n"
            "- Feche com o veredito: a linha do aluno era melhor, pior ou equivalente "
            "à real — e a lição principal.\n"
            "Seja curto (max ~1500 caracteres) e use a linguagem acessível da regra 6."
        )
        system_blocks = [
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
        ]
        messages = [
            {
                "role": "user",
                "content": "Dados da simulação (linha do aluno vs linha real):\n"
                + json.dumps(sim_data, ensure_ascii=False, indent=2),
            }
        ]
        parts: list[str] = []  # texto escrito ANTES das tools não pode sumir
        for _ in range(MAX_TOOL_ROUNDS):
            resp = _create(client,
                model=settings.analysis_model,
                max_tokens=900,
                temperature=0.2,
                system=system_blocks,
                tools=TOOLS,
                messages=messages,
            )
            parts.extend(b.text for b in resp.content if b.type == "text")
            if resp.stop_reason != "tool_use":
                final = "\n\n".join(x.strip() for x in parts if x.strip())
                return final or None
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    try:
                        value = _dispatch(block.name, block.input)
                        if collect_charts is not None:
                            spec = charts_from_tool_call(block.name, block.input, value)
                            if spec and spec not in collect_charts:
                                collect_charts.append(spec)
                        if isinstance(value, (int, float)):
                            value = round(value, 4)
                        out = json.dumps({"result": value}, ensure_ascii=False)
                    except Exception as exc:
                        out = json.dumps({"error": str(exc)})
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": out}
                    )
            messages.append({"role": "user", "content": tool_results})
        final = "\n\n".join(x.strip() for x in parts if x.strip())
        return final or None
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
        resp = _create(client,
            model=settings.cheap_model,
            max_tokens=500,
            temperature=0.2,
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


def extract_from_hand_text(text: str) -> CanonicalHand | None:
    """Fallback por IA para texto de mão em formato desconhecido.

    Qualquer sala/idioma/estilo (inclusive resumos escritos à mão): o modelo
    converte para o mesmo JSON da visão e reaproveitamos _snapshot_to_canonical.
    Retorna None sem chave ou se a extração falhar.
    """
    settings = get_settings()
    if not settings.anthropic_api_key or not text.strip():
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "O texto abaixo descreve uma mão de pôquer num formato não padronizado "
            "(pode ser de qualquer sala, idioma ou até descrição livre). Extraia a "
            "PRIMEIRA mão completa no MESMO formato JSON a seguir — apenas o JSON:\n"
            + _VISION_PROMPT.split("{", 1)[1].rsplit("}", 1)[0].join(["{", "}"])
            + "\n\nTEXTO:\n" + text[:6000]
        )
        resp = _create(client,
            model=settings.analysis_model,
            max_tokens=1500,
            temperature=0.0,  # extração: determinística
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in resp.content if b.type == "text").strip()
        data = json.loads(_strip_code_fence(raw))
        hand = _snapshot_to_canonical(data, fingerprint=_fingerprint(text.encode()))
        # guarda anti-alucinação: sem cartas do herói E sem AÇÃO, não é mão
        # (board sozinho não basta — street sem ação pode ser fabricada)
        if hand is None or (
            not hand.hero_cards and not any(st.actions for st in hand.streets)
        ):
            return None
        hand.source_format = "txt"
        hand.confidence = min(hand.confidence, 0.8)
        return hand
    except Exception as exc:
        logging.getLogger("llm").warning("extract_from_hand_text falhou: %s", exc)
        return None


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
        resp = _create(client,
            model=settings.analysis_model,
            max_tokens=1024,
            temperature=0.0,  # extração: determinística
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
        return _snapshot_to_canonical(data, fingerprint=_fingerprint(image_bytes))
    except Exception as exc:
        # a exceção era ENGOLIDA: 'não consegui ler' sem nenhum rastro
        logging.getLogger("llm").warning("extract_from_image falhou: %s", exc)
        global LAST_VISION_ERROR
        LAST_VISION_ERROR = f"{type(exc).__name__}: {exc}"[:300]
        return None


# última exceção da visão — vai para a nota do upload_failed (legível por SQL)
LAST_VISION_ERROR: str | None = None


def _fingerprint(content: bytes) -> str:
    """Id determinístico por conteúdo: reenvio do MESMO print/texto deduplica,
    print DIFERENTE ganha linha própria (antes tudo era 'vision-snapshot' e o
    upsert por hand_id fazia cada foto SOBRESCREVER a anterior no banco)."""
    import hashlib

    return hashlib.sha1(content).hexdigest()[:12]


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.startswith("json"):
            t = t[4:]
    return t.strip()


def _norm_card(card) -> str | None:
    """Normaliza carta: '10h'->'Th', 'AS'->'As', 'A♥'->'Ah'. None se irrecuperável."""
    if not card or not isinstance(card, str):
        return None
    c = card.strip().replace("10", "T")
    for sym, letter in (("♠", "s"), ("♥", "h"), ("♦", "d"), ("♣", "c")):
        c = c.replace(sym, letter)
    if len(c) != 2:
        return None
    rank, suit = c[0].upper(), c[1].lower()
    if rank not in "23456789TJQKA" or suit not in "cdhs":
        return None
    return rank + suit


def _norm_cards(cards) -> list[str]:
    return [n for n in (_norm_card(c) for c in (cards or [])) if n]


def _snapshot_to_canonical(data: dict, fingerprint: str | None = None) -> CanonicalHand | None:
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
        # a street só existe se tem ação OU se a carta DELA foi vista —
        # turn/river não podem ser fabricadas a partir do board do flop
        card_seen = {
            StreetName.PREFLOP: False,
            StreetName.FLOP: bool(flop),
            StreetName.TURN: bool(turn_c),
            StreetName.RIVER: bool(river_c),
        }[sname]
        if acts or card_seen:
            streets.append(Street(name=sname, board=boards[sname], actions=acts))

    has_actions = any(s.actions for s in streets)
    fmt = data.get("format") or "cash"
    hand = CanonicalHand(
        hand_id=f"vision-{fingerprint}" if fingerprint else "vision-snapshot",
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
