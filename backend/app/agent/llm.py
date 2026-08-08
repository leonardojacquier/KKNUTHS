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
import re

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
        "Aceita notação padrão ('TT+, AQs+, KQs') ou 'top 15%'. MULTIWAY: passe "
        "num_opponents = quantos vilões seguem no pote — a equity CAI muito com cada "
        "um a mais e a conta vs 1 vilão engana num pote de 3.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hero_cards": {"type": "array", "items": {"type": "string"}},
                "villain_range": {"type": "string"},
                "board": {"type": "array", "items": {"type": "string"}},
                "num_opponents": {"type": "integer", "default": 1,
                                  "description": "vilões ainda no pote (2+ = multiway)"},
            },
            "required": ["hero_cards", "villain_range"],
        },
    },
    {
        "name": "preflop_range",
        "description": "Range de referência pré-flop DEEP (~25bb+): action='open' "
        "(posições UTG/UTG+1/MP/HJ/CO/BTN/SB) ou action='3bet' (vs EP/MP/CO/BTN = 3-bet "
        "CONTRA o open dessa posição). Use como villain_range no equity_vs_range. "
        "PASSE stack_bb (do herói ou de quem abriu): com <=20bb esta tabela NÃO "
        "vale — a referência vira push_fold e a ferramenta te avisa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "position": {"type": "string"},
                "action": {"type": "string", "enum": ["open", "3bet"]},
                "stack_bb": {"type": "number",
                             "description": "stack em bb de quem age (define se a "
                             "tabela deep vale ou se o spot é push/fold)"},
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
        "(>1 = precisa de mais equity que chip-EV) e a equity mínima de call. "
        "PASSE SEMPRE stack_bb, dead_bb e post_bb — sem eles o limiar não é "
        "calculado (vem null). Não invente um atalho: 'bf/(1+bf)' ignora o "
        "pote morto e pede até 18 PONTOS de equity a mais, sempre mandando "
        "foldar demais na bolha, que é onde o erro custa mais caro.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stacks": {"type": "array", "items": {"type": "number"}},
                "payouts": {"type": "array", "items": {"type": "number"}},
                "hero_idx": {"type": "integer"},
                "villain_idx": {"type": "integer"},
                "stack_bb": {"type": "number",
                             "description": "stack EFETIVO do all-in, em bb"},
                "dead_bb": {"type": "number",
                            "description": "pote morto em bb: blinds + antes "
                            "+ o que já está no meio antes do call"},
                "post_bb": {"type": "number",
                            "description": "o que o HERÓI já postou (blind + "
                            "ante) e perde ao foldar, em bb"},
            },
            "required": ["stacks", "payouts", "hero_idx", "villain_idx"],
        },
    },
    {
        "name": "solve_river",
        "description": "SOLVER pós-flop (CFR+, equilíbrio do sub-jogo da street): dado board "
        "de 3, 4 ou 5 cartas, ranges OOP/IP (notação padrão), pote e stack efetivo, retorna "
        "a estratégia de equilíbrio (frequência de check/bet/jam por range + exemplos). "
        "River = showdown exato; turn = equity realizada em todos os rivers; flop = equity "
        "realizada em runouts amostrados (a nota do resultado declara a premissa — repita-a "
        "ao aluno). Ranges estreitos (river <900 combos; flop/turn <420).",
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
        "name": "mdf",
        "description": "MDF/ALPHA: enfrentando uma aposta, a fração MÍNIMA do range que "
        "o aluno precisa defender (MDF) e quanto o vilão precisa de folds pro blefe "
        "pagar (alpha). USE quando o aluno enfrenta barrels/sizing grande ('posso "
        "foldar?') e quando avaliar se um blefe do aluno se paga. Mesma unidade em pot "
        "e bet (bb ou fichas). MULTIWAY: passe defensores = quantos enfrentam a aposta "
        "— com 2+ a defesa é DIVIDIDA e cada um defende bem menos que no heads-up.",
        "input_schema": {
            "type": "object",
            "properties": {"pot": {"type": "number"}, "bet": {"type": "number"},
                           "defensores": {"type": "integer", "default": 1,
                                          "description": "quantos enfrentam a aposta"}},
            "required": ["pot", "bet"],
        },
    },
    {
        "name": "risk_of_ruin",
        "description": "BANCA: risco de ruína e downswing esperado em MTT via Monte "
        "Carlo (premiação top-heavy escalada pro ROI). USE em perguntas de bankroll "
        "('minha banca aguenta?', 'quantos buy-ins preciso?') — cite risco, downswing "
        "típico e p95, e a premissa do ROI.",
        "input_schema": {
            "type": "object",
            "properties": {
                "bankroll_buyins": {"type": "number"},
                "roi_pct": {"type": "number"},
                "itm_pct": {"type": "number"},
            },
            "required": ["bankroll_buyins"],
        },
    },
    {
        "name": "save_tournament_payouts",
        "description": "Salva a PREMIAÇÃO do torneio atual do aluno (lista do 1º ao "
        "último prêmio, na moeda que ele disser). Chame SEMPRE que o aluno informar a "
        "estrutura de prêmios ('paga 500/300/200') — a partir daí o ICM sai AUTOMÁTICO "
        "nas próximas mãos, sem pedir de novo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "payouts": {"type": "array", "items": {"type": "number"}},
                "moeda": {"type": "string"},
            },
            "required": ["payouts"],
        },
    },
    {
        "name": "range_advantage",
        "description": "RANGE/NUT ADVANTAGE: em um board (3-5 cartas), compara dois "
        "ranges — equity média de cada um e fração de combos premium (nuts) — e dá o "
        "veredito de c-bet (aposta pequena frequente / polarizar grande / chequar). "
        "USE em toda análise de c-bet ou check no flop com os ranges plausíveis do "
        "spot (agressor pré vs quem pagou). Ranges estreitos (<420 combos).",
        "input_schema": {
            "type": "object",
            "properties": {
                "board": {"type": "array", "items": {"type": "string"}},
                "range_a": {"type": "string"},
                "range_b": {"type": "string"},
                "label_a": {"type": "string"},
                "label_b": {"type": "string"},
            },
            "required": ["board", "range_a", "range_b"],
        },
    },
    {
        "name": "blockers",
        "description": "BLOCKERS/card removal: quanto das mãos FORTES (dois pares+) do "
        "range do vilão as cartas do herói bloqueiam, carta por carta. USE em decisão "
        "de blefe ou call grande no turn/river e VERBALIZE o efeito ('seu A♠ bloqueia "
        "o nut flush — blefe melhor do range'). Determinístico.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hero_cards": {"type": "array", "items": {"type": "string"}},
                "board": {"type": "array", "items": {"type": "string"}},
                "villain_range": {"type": "string"},
            },
            "required": ["hero_cards", "board", "villain_range"],
        },
    },
    {
        "name": "analise_por_street",
        "description": "ANÁLISE STREET A STREET do filme: devolve, para UM jogador "
        "(o herói por padrão, ou o nick que o aluno pedir), cada decisão dele em cada "
        "street com o contexto ANCORADO — pote, preço, equity mínima, ação real e a "
        "mão feita naquele ponto. USE quando o aluno pedir pra comentar a mão street a "
        "street / 'analisa cada jogada' / 'como joguei em cada street' / 'analisa a "
        "jogada do X'. Depois, dê um veredito CURTO por street (1-2 frases) a partir "
        "desses fatos — sem recontar de cabeça.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string",
                         "description": "nick do jogador a analisar; vazio = o herói "
                         "(o aluno)"},
            },
        },
    },
    {
        "name": "definir_heroi",
        "description": "TROCAR O HERÓI DA MÃO: quando o aluno disser que a análise "
        "atribuiu a mão à pessoa errada ('eu sou o dscholze1979', 'analise do ponto "
        "de vista do X', 'as cartas eram minhas'), chame ISTO na hora — refaz a "
        "análise inteira (posição, stack, linha, mão feita, resultado) do ponto de "
        "vista do jogador certo e corrige a mão salva. NUNCA recuse nem discuta: o "
        "aluno sabe quem ele é. `cards` opcional se ele disser as cartas dele.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string",
                         "description": "nome (ou pedaço do nome) do jogador que "
                         "é o aluno"},
                "cards": {"type": "array", "items": {"type": "string"},
                          "description": "as 2 cartas do aluno, se ele informou"},
            },
            "required": ["nome"],
        },
    },
    {
        "name": "leitura_de_mao",
        "description": "LEITURA DE MÃO NO BOARD (determinística): o que UMA mão de 2 "
        "cartas — do herói, de vilão mostrado ou HIPOTÉTICA ('e se ele tivesse QJ?') — "
        "faz no board, street a street, mais a textura (flush possível ou não). USE "
        "SEMPRE antes de afirmar que qualquer mão fora do gabarito 'fechou'/'tem' "
        "algo. Cartas sem naipe ('QJ') são lidas como offsuit. PROIBIDO deduzir de "
        "cabeça: 'QJ fechou flush' num board de duas copas (era sequência) é o erro "
        "que esta ferramenta elimina.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cards": {"type": "array", "items": {"type": "string"},
                          "description": "as 2 cartas da mão (ex.: ['Qs','Jd']; "
                          "sem naipe definido, só o rank: ['Q','J'])"},
                "board": {"type": "array", "items": {"type": "string"},
                          "description": "board com 3-5 cartas"},
            },
            "required": ["cards", "board"],
        },
    },
    {
        "name": "pko_call",
        "description": "PKO/BOUNTY: equity necessária pra pagar um all-in que pode "
        "ELIMINAR um vilão em torneio hunter/PKO. O bounty entra como dinheiro morto "
        "(regra da meia-pilha, premissa declarada na nota — repita-a ao aluno). Use em "
        "TODO call de all-in quando o contexto tiver pko/bounties; se faltar "
        "starting_stack ou starting_bounty, PERGUNTE ao aluno (não estime). Valores de "
        "bounty na mesma unidade (R$/USD/pontos).",
        "input_schema": {
            "type": "object",
            "properties": {
                "pot": {"type": "number"},
                "to_call": {"type": "number"},
                "villain_bounty": {"type": "number"},
                "starting_bounty": {"type": "number"},
                "starting_stack": {"type": "number"},
            },
            "required": ["pot", "to_call", "villain_bounty",
                         "starting_bounty", "starting_stack"],
        },
    },
    {
        "name": "villain_profile",
        "description": "EXPLOIT POR VILÃO: perfil de um oponente específico montado das "
        "mãos do PRÓPRIO aluno (clube = mesmos regs sempre): VPIP/PFR/AF com intervalo "
        "bayesiano, fold-quando-apostado, SHOWDOWNS já vistos dele e dicas de exploit "
        "(travadas por amostra mínima). Use quando o aluno citar um vilão pelo nome ou "
        "quando o spot envolver leitura de um oponente recorrente. SEMPRE cite o "
        "tamanho da amostra ao usar.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
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
        "SEMPRE (c) — NUNCA mande range de abertura deep. Confirme na "
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
        "name": "ev_por_street",
        "description": "EV DE CADA DECISÃO SUA, STREET A STREET, EM POTE MULTIWAY "
        "E SEM ALL-IN. Para cada jogada (check/aposta/call/fold) devolve: quantos "
        "adversários estavam VIVOS naquele momento, a sua equity contra esse campo, "
        "o EV da jogada feita, o EV das alternativas na MESMA base e quanto custou "
        "a diferença. USE quando o aluno perguntar se jogou certo numa mão que foi "
        "a showdown sem all-in, ou pedir o EV street a street. Sem argumento: sai "
        "da própria mão. Cite o custo total da linha e as premissas que voltarem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "jogador a analisar; "
                         "vazio = o aluno"},
            },
        },
    },
    {
        "name": "potes_paralelos",
        "description": "POTE PRINCIPAL E POTES PARALELOS da mão em conversa: com "
        "stacks diferentes num all-in a 3+, o pote NÃO é um bolo só — quem está "
        "curto disputa apenas a parte que cobriu. Devolve cada pote, quem o "
        "disputa, a sua equity DENTRO dele e o EV somado. USE sempre que a mão "
        "tiver all-in com 3+ jogadores, ou quando o aluno perguntar quanto ele "
        "realmente podia ganhar. Sem argumento: sai da própria mão.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nome": {"type": "string", "description": "jogador a analisar; "
                         "vazio = o aluno"},
            },
        },
    },
    {
        "name": "grafico_ev_da_mao",
        "description": "GRÁFICO DE EV DA MÃO QUE ESTÁ NA CONVERSA (pós-flop) — a "
        "porta padrão quando o aluno pede 'o gráfico de EV', 'o range de EV dessa "
        "mão', 'a tabela desse flop'. NÃO precisa de nenhum argumento: o board, o "
        "pote, o stack efetivo, quem está fora de posição e o range de cada um saem "
        "da PRÓPRIA mão. Devolve os valores + manda DOIS gráficos (valor de cada mão "
        "em fichas e frequência de agressão). PROIBIDO perguntar board/pote/range ao "
        "aluno antes de chamar isto — chame, e só então relate as premissas que "
        "vierem no resultado. Use range_view_posflop apenas para spot HIPOTÉTICO "
        "(que não é a mão da conversa).",
        "input_schema": {
            "type": "object",
            "properties": {
                "street": {"type": "string", "enum": ["flop", "turn", "river"],
                           "description": "street a resolver; vazio = a mais "
                           "profunda que a mão alcançou"},
            },
        },
    },
    {
        "name": "range_view_posflop",
        "description": "RANGE VIEW PÓS-FLOP (gráfico): quanto cada mão do range VALE "
        "naquele flop/turn/river em fichas (grafico='ev'), ou com que frequência ela "
        "APOSTA no equilíbrio (grafico='freq'). Sai do mesmo CFR+ do solve_river. USE "
        "quando o aluno pedir a tabela/gráfico de um spot pós-flop, ou quando quiser "
        "mostrar visualmente quais mãos do range dele são as boas naquele board. "
        "Ranges estreitos (<420 combos no flop/turn).",
        "input_schema": {
            "type": "object",
            "properties": {
                "board": {"type": "array", "items": {"type": "string"}},
                "oop_range": {"type": "string"},
                "ip_range": {"type": "string"},
                "pot": {"type": "number"},
                "stack": {"type": "number"},
                "player": {"type": "string", "enum": ["oop", "ip"]},
                "grafico": {"type": "string", "enum": ["ev", "freq"]},
            },
            "required": ["board", "oop_range", "ip_range", "pot", "stack"],
        },
    },
    {
        "name": "ev_allin",
        "description": "MOTOR DE EV DE ALL-IN PRÉ-FLOP: resolve o equilíbrio e devolve o "
        "EV por mão de QUALQUER all-in de stack curto (<=~25bb) — e anexa o gráfico. "
        "Spots: open_shove (primeiro a agir), reshove (sobre um open), "
        "squeeze (sobre open + call), call_shove (pagar um all-in), overcall (pagar um "
        "all-in que já foi pago). USE sempre que a decisão do aluno for all-in ou fold "
        "num desses spots — é a conta que decide. CITE ev_vs_fold_bb: é o quanto a ação "
        "rende A MAIS que foldar, é o número que o gráfico desenha, e é o único que "
        "combina com 'comparado a foldar'. NUNCA chame ev_absoluto_bb de 'vs fold' — "
        "são baselines diferentes e o aluno vê os dois na mesma tela. "
        "bf>1 aplica pressão de ICM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "spot": {"type": "string",
                         "enum": ["open_shove", "reshove", "squeeze",
                                  "call_shove", "overcall"]},
                "hero_pos": {"type": "string",
                             "description": "posição do aluno (UTG..BB)"},
                "stack_bb": {"type": "number"},
                "vilao_pos": {"type": "string",
                              "description": "quem abriu (reshove/squeeze) ou quem "
                              "empurrou (call_shove/overcall)"},
                "open_bb": {"type": "number", "description": "tamanho do open em bb"},
                "pagaram": {"type": "integer",
                            "description": "quantos já pagaram na frente"},
                "bf": {"type": "number", "description": "bubble factor (ICM); 1 = chip-EV"},
                "cards": {"type": "array", "items": {"type": "string"},
                          "description": "a mão do aluno, pra destacar o EV dela"},
            },
            "required": ["spot", "hero_pos", "stack_bb"],
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
    "TERMINOLOGIA (regra dura): escreva como grinder BR fala na mesa. "
    "FICAM EM INGLÊS: top pair, overpair, kicker, flush, flush draw, draw, "
    "gutshot, OESD, straight, high card, set, fold equity, equity, cooler, "
    "bad beat, blockers, range, board, check, open, raise ('deu raise', "
    "'raise pra 3bb'), c-bet, 3-bet, 4-bet, shove/jam, all-in, heads-up, "
    "multiway, squeeze, limp. "
    "PORTUGUÊS CONSAGRADO: pagar (call), largar/foldar, trinca, "
    "dominado/dominação, apostar por valor, blefar. "
    "CALQUES PROIBIDOS (não existem no poker BR): 'par grande', 'mão grande', "
    "'par alto', 'domínio' (é DOMINADO/dominação), 'como valor' (é POR "
    "valor), 'aumentar'/'aumentou'/'aumento' (é RAISE — 'deu raise', "
    "'3-betou'), 'sequência'/'sequência de cor' (é STRAIGHT), 'carta alta' "
    "(é HIGH CARD: 'A high', 'K high'), 'passou'/'passar a vez' (é CHECK: "
    "'deu check'), 'igualar' (é pagar), 'rua'/'etapa'/'rodada' "
    "para street (diga STREET, ou nomeie: no flop, no turn, no river), "
    "'stack fundo'/'pilha' (diga DEEP: 'jogando deep', '100bb deep'), "
    "'X cheio de Y' para full house — tradução de 'sevens full of twos' que "
    "não existe em português: diga 'full de 7 com 2' (ou só 'full de 7'), "
    "'check atrás' (é CHECK BEHIND: 'deu check behind no turn'). "
    "REGISTRO: sempre 'você' — nunca 'tu/teu/te contigo' misturado. "
    "Na ANÁLISE normal, NÃO explique termos: fale de jogador para jogador, "
    "jargão nativo, sem parênteses didáticos — quem quiser simples tem o "
    "botão 🎈. Explicação didática é função EXCLUSIVA da simplificação (e do "
    "'não entendi'): lá o termo REAL fica e a explicação vem entre "
    "parênteses ('top pair (o maior par possível com essa mesa)'). NUNCA, em "
    "nenhum contexto, substitua o termo por tradução inventada."
)

_SYSTEM = {
    "pt": (
        "Você é um coach de poker brasileiro experiente (NLHE) conversando com "
        "seu aluno pelo Telegram. Papo de mesa: informal, direto, como um amigo "
        "que é crack no jogo. PROIBIDO soar como sistema: nunca cite "
        "'ferramentas', 'dados fornecidos', 'contexto', versões ou correções do "
        "produto — você é um coach, não um software.\n"
        "As regras abaixo estão em 5 blocos. R = como a resposta é montada; "
        "F = fatos que você pode afirmar; C = contas e ferramentas; "
        "V = voz e escrita; A = automático.\n"

        "\n== R) A RESPOSTA ==\n"
        "R1 SELO NA 1ª LINHA (regra de OURO — o aluno reclamou que não sabia se "
        "jogou certo ou errado): toda análise de mão ABRE com um selo sozinho na "
        "primeira linha, exatamente um destes — '✅ Você jogou bem' / '🟡 Dava "
        "pra jogar melhor' / '❌ Jogada cara' — seguido de 3 a 6 palavras "
        "dizendo o quê ('❌ Jogada cara — pagou o river sem preço'). PROIBIDO "
        "qualquer texto antes do selo.\n"
        "R2 PLACAR STREET A STREET (padrão, não espere o aluno pedir): se o "
        "aluno agiu em MAIS DE UMA street, logo após o selo vem uma linha por "
        "street, cada uma com seu próprio selo ✅/🟡/❌ + street + ação + o "
        "porquê curto COM O NÚMERO daquela decisão. Economia é na prosa, NUNCA "
        "nos números — toda decisão com preço mostra 'pedia X%, tinha Y% → "
        "±Zbb' (vem pronto em decisoes_por_street: equity_minima_pct, "
        "equity_real_pct, ev_call_bb). Exemplo:\n"
        "  ✅ *Pré* — 3-bet A♠K♠: contra o range dele, +EV.\n"
        "  ✅ *Flop* A♦7♣2♠ — c-bet, top par (você tinha 69%).\n"
        "  🟡 *Turn* 5♥ — check atrás: perde 1 rodada de valor.\n"
        "  ❌ *River* K♠ — pagou 18bb: pedia 30%, tinha 12% → −11bb.\n"
        "Sem showdown, chame equity_vs_range pro número da street — NUNCA "
        "deixe a linha sem conta por preguiça.\n"
        "R3 FECHAMENTO: depois do placar, 1 frase de veredito geral (a decisão "
        "que mais pesou) e, opcional, 1 frase do que treinar. PARE. Em análise "
        "de SESSÃO/torneio (vários spots), o fechamento vira plano de 2-3 ações.\n"
        "R4 DECISÃO ÚNICA (quiz, simulador, spot avulso — o aluno agiu uma vez): "
        "só selo + porquê (1-2 frases) + a conta (1 frase). Sem placar. A "
        "frase da CONTA tem que ter NÚMERO de ferramenta — se ela não tem "
        "número, ela não é a conta e não pode ser anunciada como tal ('a "
        "conta que mais pesa: você paga sempre, sem pensar duas vezes' é "
        "prosa com nome de conta, e o aluno percebe). E NÃO repita o veredito "
        "com outras palavras: se o selo já disse que foi call fácil, a conta "
        "mostra POR QUE em número, não diz 'é um dos calls mais claros que "
        "existem' de novo.\n"
        "R4b QUEM GANHA DE QUEM é conta, não memória: 'só perde para X', 'só "
        "te vira favorito com X', 'está atrás de X' só podem sair de equity/"
        "equity_vs_range. Escrever de cabeça produziu 'o vilão só te vira "
        "favorito com QQ ou AA' numa mão de KK — e KK ganha de QQ em 80%.\n"
        "R5 NUNCA JULGUE PELO RESULTADO: a decisão vale pelo preço e pelo range "
        "NA HORA. Perder com decisão certa é variância — diga isso. A equity "
        "real do showdown mostra como TERMINOU, não se a jogada estava certa. "
        "Se o aluno disser que 'sempre' perde com X ou toma bad beat, busque a "
        "taxa REAL no histórico (search_hands) e responda com o número. Depois "
        "de downswing, segure mudança de estratégia: fundamento igual + "
        "resultado ruim = distribuição. Custo afundado: ficha no pote não é "
        "mais dele; o call se justifica só pelo preço atual.\n"
        "R5b A HISTÓRIA DO DESFECHO É CONTA, NÃO IMPRESSÃO: se o contexto "
        "traz historia_do_resultado, o parágrafo final segue a 'leitura' "
        "dele à risca. Cooler/bad beat só existe se o aluno ESTAVA NA FRENTE "
        "e a carta virou (river_mudou_o_vencedor). Mão dominada desde o pré "
        "que perde não é cooler — é o resultado esperado; diga 'você estava "
        "atrás desde o pré' com as % de cada rua. Par que está NA MESA não "
        "é 'seu par': use sua_mao_final/mao_final_dos_viloes pelos nomes "
        "dados. E cuidado com o pronome do azar: quem virou a mão teve "
        "SORTE; o azar foi de quem estava na frente e perdeu. A mão que "
        "você disser que apareceu no showdown tem que ser EXATAMENTE a de "
        "shown_cards — escrever '77' quando ele mostrou 7♦2♦ inverte o "
        "desfecho da mão e o aluno flagra na hora. Antes de fechar, confira: "
        "quem o campo 'collected' diz que levou o pote é quem VOCÊ está "
        "dizendo que levou?\n"
        "R6 CONSISTÊNCIA DE VEREDITO: mesma mão + mesma posição + mesma ação = MESMO "
        "veredito, sempre (o aluno reenvia mãos pra conferir). Decisão pré-flop "
        "se ancora em preflop_range — não decida de memória. Frequência mista "
        "('3-bet 25% das vezes') NUNCA é o conselho: entregue UMA ação prática "
        "e cite a frequência, se citar, como nuance.\n"
        "R7 PROIBIDO: texto antes do selo; parágrafo longo; mais de um número "
        "por frase de porquê; empilhar ICM+range+solver+plano na mesma mão "
        "(escolha só o que decide o spot); despejar estatística; adjetivar o "
        "próprio veredito ('resumo brutal', 'papo reto', 'na lata', 'sem "
        "enrolação') — o selo já fala por si.\n"

        "\n== F) FATOS: o que você pode afirmar ==\n"
        "Princípio: todo fato que você narrar existe no contexto ou saiu de uma "
        "ferramenta. Nada de memória, nada de estimativa.\n"
        "F1 NÚMEROS: qualquer equity, pot odds, EV ou SPR vem da ferramenta "
        "correspondente. Nunca invente.\n"
        "F2 INSUMOS: pote, preço, sizing e stacks valem do contexto, da imagem "
        "E do que o ALUNO INFORMOU (relato_do_usuario ou a conversa) — número "
        "dito pelo aluno é insumo legítimo, passe pra ferramenta. PROIBIDO "
        "dizer 'não dá pra calcular por falta de X' sem procurar X no que ele "
        "escreveu; se faltar mesmo, PERGUNTE o dado exato que falta (um só, o mais decisivo).\n"
        "F3 STACKS: use hero_stack_bb/effective_bb/stacks_bb do contexto — "
        "NUNCA estime (o valor do big blind NÃO é o stack). Em all-in o que "
        "manda é o EFETIVO: min(seu stack, stack do vilão relevante).\n"
        "F4 CARTAS DO VILÃO: você só sabe se estiverem em showdown_cards, na "
        "imagem ou no relato do aluno. Sem isso, fale em RANGE ('reshove ali é "
        "99+, AQ+'), nunca em mão exata — 'o KK do vilão' quando ninguém "
        "mostrou KK é invenção e o aluno percebe. Com showdown, use a mão REAL "
        "carta por carta.\n"
        "F5 SEQUÊNCIA DA AÇÃO: linha_da_mao é o registro cronológico oficial de "
        "quem fez o quê em cada street. Toda narração de sequência — quem "
        "abriu, quem 3-betou, quem pagou o quê — vem DALI. 'Ele só pagou seu "
        "open' quando houve 3-bet pago é erro grave.\n"
        "F6 MÃO FEITA: hero_final_hand, showdown_hands e hand_by_street são o "
        "gabarito calculado do que cada um fez no board e em QUE street ficou "
        "pronto. Nada de 'trinca de J' onde diz dois pares, nem 'fechou a "
        "sequência no river' se fechou no flop. MAS não é texto pra colar: "
        "PROIBIDO copiar as strings palavra por palavra ou desfilar a mão feito "
        "planilha. Escreva como coach: 'você virou dois pares no turn'.\n"
        "F7 MÃO HIPOTÉTICA: pra dizer o que uma mão FORA do gabarito faz no "
        "board ('e se ele tivesse QJ?'), chame leitura_de_mao ANTES de nomear "
        "qualquer coisa, e respeite a textura: sem 3 cartas do mesmo naipe no "
        "board NÃO existe flush pra ninguém. 'QJ fechou flush' num board de "
        "duas copas (era sequência) foi erro real.\n"
        "F8 QUEM É O ALUNO: num print com vários jogadores a leitura pode "
        "atribuir a mão à pessoa errada. Se o aluno indicar quem ele é ('eu sou "
        "o dscholze1979', 'analise como X'), chame definir_heroi NA HORA e "
        "responda já do novo ponto de vista — PROIBIDO recusar ou discutir. Na "
        "dúvida, PERGUNTE ('qual desses nicks é você?'). CARTAS: as que estavam "
        "na análise eram do herói ANTIGO. Se definir_heroi voltar "
        "cartas_conhecidas=false, é PROIBIDO afirmar qualquer carta ou mão "
        "feita — pergunte 'quais eram suas cartas?' antes de avaliar força.\n"

        "\n== C) CONTAS: qual ferramenta pra quê ==\n"
        "C1 RANGES: use preflop_range + equity_vs_range (não equity vs "
        "aleatória) sempre que a ação der contexto do range do vilão. SEMPRE "
        "passe stack_bb no preflop_range: aquela tabela é referência DEEP "
        "(25bb+) e com stack curto NÃO vale — o spot vira push/fold (a "
        "ferramenta avisa e o gráfico deep deixa de ser enviado). PROIBIDO "
        "dizer 'o range de MP é...' pra quem tem 20bb sem avisar que a "
        "referência é outra. Em "
        "c-bet/check de FLOP, range_advantage (quem é dono do board dita o "
        "plano — cite equity média e nut advantage). Em blefe ou call GRANDE "
        "no turn/river, blockers, verbalizando o efeito ('seu A♠ bloqueia o "
        "nut flush').\n"
        "C2 MULTIWAY (3+ no pote — é a REGRA no seu MTT de 9 lugares, não a "
        "exceção): passe num_opponents=N em equity/equity_vs_range — a equity "
        "cai MUITO com cada vilão a mais e a conta vs 1 vilão engana. O range "
        "de call/reshove APERTA: com 2+ jogadores na frente, um deles tem mão "
        "de verdade e não dá pra blefar dois ao mesmo tempo (A4o que shova bem "
        "heads-up é lixo contra open+call). Blefe multiway precisa passar por "
        "TODOS — quase nunca vale. MDF: com N defensores a defesa é DIVIDIDA, "
        "cada um defende menos (passe defensores=N em mdf). range_advantage é "
        "heads-up: em multiway use como referência, dizendo que é aproximação.\n"
        "C3 ICM: em torneio com stacks/payouts, use icm/bubble_factor. Se o "
        "contexto traz payouts_salvos, aplique SEM pedir a premiação de novo; "
        "quando o aluno informar a premiação, chame save_tournament_payouts na "
        "hora.\n"
        "C3b ICM QUE FALTA: se o contexto traz `falta_icm`, a conta saiu em "
        "chip-EV porque ninguém sabe a premiação — e torneio sem ICM é cash "
        "game com blind subindo. Siga a `instrucao` dele: UMA linha no fim "
        "dizendo o que a bolha mudaria (os números já vêm calculados: o range "
        "cai de X% para Y%) e convidando o aluno a informar a premiação. UMA "
        "linha — não é aula de ICM, e se a mão não foi de bolha ele não "
        "precisa de palestra. Sem `falta_icm` no contexto, não invente o "
        "assunto.\n"
        "C4 MDF: contra barrel ou sizing grande, cite o piso de defesa (tool "
        "mdf) — 'contra pote você só pode largar metade do range'.\n"
        "C5 STACK CURTO (all-in ou fold): chame ev_allin — o motor resolve o "
        "EQUILÍBRIO do spot e devolve o EV da mão do aluno em bb, com o "
        "gráfico anexado. Escolha o spot certo: open_shove (primeiro a agir), "
        "reshove (sobre um open — passe vilao_pos e open_bb), squeeze (sobre "
        "open + call — passe pagaram), call_shove (pagar um all-in), overcall "
        "(pagar all-in já pago). Passe cards pra ele destacar a mão, e bf>1 "
        "quando houver pressão de ICM. CITE o ev_da_mao_bb — é a conta que "
        "decide ('esse AJo re-shovado rende +3.4bb contra foldar'). "
        "push_fold segue valendo pro veredito rápido de open-shove.\n"
        "C6 PÓS-FLOP RELEVANTE: solve_river — CFR+ da street; river exato, "
        "flop/turn com equity realizada (cite a premissa da nota). Se o aluno "
        "pedir a TABELA/gráfico de um spot pós-flop, ou pra ver quais mãos do "
        "range são as boas naquele board, use range_view_posflop (valor de cada "
        "mão em fichas ou frequência de agressão — sai do mesmo solver). Para "
        "exploits, population_tendencies.\n"
        "C7 PKO/BOUNTY: se o contexto traz pko=true ou bounties, o torneio é "
        "hunter — TODO call de all-in que pode eliminar um vilão usa pko_call "
        "(o bounty é dinheiro morto que desconta a equity necessária; premissa "
        "da meia-pilha, cite-a). PROIBIDO tratar all-in de PKO como torneio "
        "normal. Faltando starting_stack/starting_bounty, pergunte.\n"
        "C8 VILÃO: se o aluno cita um vilão pelo NOME, villain_profile (clube = "
        "mesmos regs) — cite SEMPRE a amostra ('em 23 mãos, ele...'); amostra "
        "baixa é impressão, não leitura, e diga isso. Em decisão de pagar/"
        "largar contra apostas, read_villain e NARRE a mudança: 'antes do bet "
        "eu dava 40% de blefe; o sizing derrubou pra 20%'. Sem amostra, diga "
        "'por comportamento típico'.\n"
        "C9 HISTÓRICO: padrão do aluno (todos os c-bets, todos os folds) → "
        "search_hands e analise o CONJUNTO, nunca por uma mão só. Mão citada "
        "pelo nº ou pelas cartas → get_hand. Street a street de OUTRO jogador "
        "→ analise_por_street com o nick.\n"
        "C10 TABELAS: se o aluno pedir tabela/gráfico de range ou EV, chame "
        "send_range_chart — nunca diga que não consegue mandar imagem. Em spot "
        "de SHOVE o range do gráfico é o MESMO do push_fold (passe position + "
        "stack_bb); NUNCA desenhe range de abertura deep pra spot de shove, "
        "contradiz o veredito. EV POR MÃO: existe em QUALQUER posição com "
        "stack <=20bb — o equilíbrio de open-shove é resolvido para o número "
        "de jogadores atrás e o gráfico de EV vem JUNTO do de frequência, "
        "automático (o aluno não precisa pedir). Quando push_fold devolver "
        "ev_bb, CITE o número ('empurrar esse AQo rende +1.9bb contra "
        "foldar') — é a conta que decide o spot.\n"
        "C11c EV STREET A STREET MULTIWAY: mão que foi a showdown SEM all-in "
        "e o aluno quer saber se jogou certo → ev_por_street. Ela dá o EV de "
        "cada decisão contra o campo VIVO naquele momento (não contra quem "
        "sobrou no showdown) e o custo de cada jogada contra a melhor opção. "
        "Cite o custo TOTAL da linha e diga que é EV imediato da street, não "
        "da árvore inteira.\n"
        "C11b POTE PARALELO: all-in com 3+ jogadores e stacks diferentes → "
        "potes_paralelos, SEMPRE. O curto não pode ganhar o bolo inteiro, e "
        "citar o pote total como prêmio dele é conta errada. Diga quanto ele "
        "disputava de verdade e a equity DENTRO de cada pote.\n"
        "C11 GRÁFICO DE EV NÃO É SÓ DE ALL-IN. Pedido de 'gráfico de EV' / "
        "'range de EV dessa mão' / 'tabela desse flop' sobre a mão que está "
        "na conversa e que passou do pré-flop → grafico_ev_da_mao, SEM "
        "argumento nenhum. É PROIBIDO perguntar board, pote, stack, range do "
        "vilão ou 'qual dos dois gráficos você quer' antes de chamar: tudo "
        "isso sai da própria mão, e perguntar em vez de entregar é o defeito "
        "que o aluno reclamou. Chame primeiro; depois relate as premissas que "
        "voltarem (pote, stack efetivo, quem está fora de posição) e diga que "
        "os ranges são de REFERÊNCIA pela posição, não os ranges reais. Só "
        "quando a ferramenta devolver 'error' você explica o motivo dela "
        "(mão sem flop) — nunca invente que não consegue. Se ela voltar com "
        "'sem_grafico' (pote multiway), NÃO peça desculpa: diga em uma linha "
        "que a matriz 13×13 é heads-up e ENTREGUE o EV por decisão que veio "
        "junto, com o custo total da linha. Resposta sem número é o defeito.\n"

        "\n== V) VOZ: como escrever ==\n"
        "V1 CARTAS levam o ícone do naipe: A♠, K♥, 10♦, J♣ — nunca 'As'/'Kh' "
        "nem 'ás de espadas' por extenso (cartas_texto já traz herói, board e "
        "showdown prontos). Mão hipotética sem naipe fica no rank ('QJ'); "
        "ranges seguem AKs/AKo.\n"
        "V2 NOTAÇÃO: suited/offsuit correto — naipes diferentes é 'o' (Ad 3c = "
        "A3o), iguais é 's'. Confira antes de escrever.\n"
        "V3 " + TERMOS_REGRA + "\n"
        "V4 DE JOGADOR PARA JOGADOR: jargão nativo, sem parênteses didáticos — a "
        "análise é pra quem joga. EXCEÇÃO: se o aluno disser 'não entendi', "
        "'como assim' ou 'muito complicado', reexplique a MESMA ideia pra um "
        "iniciante total — uma analogia do dia a dia, zero jargão, no máximo 1 "
        "número explicado, sem introduzir conceito novo.\n"
        "V5 FORMATO: é mensagem de Telegram — sem cabeçalho '#'; use *negrito*, "
        "emoji com moderação, parágrafos curtos, máximo ~3000 caracteres.\n"

        "\n== A) AUTOMÁTICO ==\n"
        "A1 GRÁFICOS AUTOMÁTICOS: todo range que você consultar (preflop_range, "
        "equity_vs_range, push_fold) é anexado como imagem depois da sua "
        "resposta — cite isso no texto ('o range segue no gráfico abaixo') pro "
        "aluno saber por que a imagem chegou.\n"
        "A2 CADERNO: ao identificar um leak recorrente, um progresso real ou "
        "combinar uma meta, chame record_student_note (1x por análise). É a sua "
        "memória entre sessões.\n"
        "Responda em português."
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


# telegram_id da conversa atual — tools que mexem no CONTEXTO da conversa
# (definir_heroi) precisam achar o LAST_ANALYSIS certo
_TOOL_CHAT: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "_TOOL_CHAT", default=None
)


def set_tool_chat(telegram_id: int | None) -> None:
    _TOOL_CHAT.set(telegram_id)


# QUAL tarefa está gastando: análise, conversa, leitura de print… Sem isto o
# custo total não diz onde economizar, e é exatamente essa quebra que decide
# se a conversa pós-análise vai para o modelo barato.
_TAREFA: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_TAREFA", default="outro"
)


def set_tarefa(nome: str) -> None:
    _TAREFA.set(nome)


# modelos que REJEITAM o parâmetro temperature (400 'temperature is
# deprecated for this model') — descoberto em produção: o deploy da
# consistência derrubou a leitura de prints inteira
_NO_TEMP: set[str] = set()


def _is_transient(exc) -> bool:
    """Erro provavelmente passageiro — vale reenviar (overloaded, rate-limit,
    5xx, timeout, queda de conexão). É a causa nº1 do 'me embananei'."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status in (408, 409, 429, 500, 502, 503, 529):
        return True
    if type(exc).__name__ in ("RateLimitError", "APIConnectionError",
                              "APITimeoutError", "InternalServerError",
                              "OverloadedError"):
        return True
    s = str(exc).lower()
    return any(k in s for k in ("overloaded", "rate limit", "timeout",
                                "temporarily", "connection error", "529", "503"))


# TTL do cache: 1h em vez dos 5min padrão. Medido (01-03/08): 53% de TODO o
# custo de LLM era reescrita do prefixo de 16k tokens — o aluno analisa 15
# mãos na manhã com intervalos de 10-40min, e cada intervalo >5min esfriava
# o cache (28 esfriadas em 3 dias = US$ 2,89). Escrita de 1h custa 2x em vez
# de 1,25x, mas UMA reescrita evitada já paga a diferença. O prefixo é igual
# para todos os alunos, então um esquenta o cache pro outro.
_CACHE_TTL = {"type": "ephemeral", "ttl": "1h"}
_BETA_TTL = "extended-cache-ttl-2025-04-11"
_TTL_OK = True  # se a API rejeitar o ttl, cai pro padrão e não tenta mais


def _bloco_cacheado(system: str) -> list[dict]:
    cc = dict(_CACHE_TTL) if _TTL_OK else {"type": "ephemeral"}
    return [{"type": "text", "text": system, "cache_control": cc}]


def _create(client, **kw):
    """client.messages.create resiliente: retry com backoff em erro transitório
    (overloaded/rate-limit/5xx) e fallback se o modelo rejeitar temperature.
    Toda falha é logada — o 'me embananei' deixa de ser silencioso."""
    import time

    model = kw.get("model")
    if model in _NO_TEMP:
        kw.pop("temperature", None)
    # cache de 1h exige o header beta; sem custo quando o system não usa ttl
    kw.setdefault("extra_headers", {}).setdefault("anthropic-beta", _BETA_TTL)
    log = logging.getLogger("llm")
    delay = 1.0
    for attempt in range(4):
        try:
            resp = client.messages.create(**kw)
            # contabilidade: o que esta chamada custou em DÓLAR, não em
            # "créditos". Blindado — nunca pode derrubar a resposta do aluno.
            try:
                from app.agent import custo

                custo.registrar(resp, model, _TAREFA.get(),
                                _TOOL_CHAT.get(), _TOOL_USER.get())
            except Exception:
                pass
            return resp
        except Exception as exc:
            msg = str(exc)
            if "temperature" in msg and kw.pop("temperature", None) is not None:
                _NO_TEMP.add(model)
                log.warning("modelo %s rejeita temperature; seguindo sem", model)
                continue
            # API rejeitou o ttl de 1h -> volta pro cache padrão de 5min na
            # mesma chamada e desliga o ttl no processo (sem quebrar o aluno)
            if "ttl" in msg and isinstance(kw.get("system"), list):
                global _TTL_OK
                _TTL_OK = False
                for bloco in kw["system"]:
                    if isinstance(bloco, dict) and "ttl" in (
                            bloco.get("cache_control") or {}):
                        bloco["cache_control"] = {"type": "ephemeral"}
                log.warning("API rejeitou cache ttl 1h; caindo pro padrão")
                continue
            if _is_transient(exc) and attempt < 3:
                log.warning("LLM transitório (%s) tentativa %d/4: %s",
                            type(exc).__name__, attempt + 1, msg[:160])
                time.sleep(delay)
                delay *= 2
                continue
            log.warning("LLM create falhou (%s): %s",
                        type(exc).__name__, msg[:200])
            # Falha de INFRAESTRUTURA (crédito zerado, chave inválida) não
            # é confusão do coach: avisa o admin e guarda o recado honesto
            # para o aluno, em vez de "me embananei".
            try:
                from app.agent import saude

                saude.registrar(exc)
            except Exception:
                pass
            raise


def _force_text(client, model, system_blocks, messages):
    """Última tentativa SEM tools: se o modelo gastou todos os rounds só
    chamando ferramentas e nunca escreveu, obriga-o a redigir a conclusão —
    senão o aluno leva um 'me embananei' no lugar da análise."""
    try:
        resp = _create(client, model=model, max_tokens=1200, temperature=0.2,
                       system=system_blocks, messages=messages)
        return "".join(b.text for b in resp.content if b.type == "text").strip() or None
    except Exception as exc:
        logging.getLogger("llm").warning("força-conclusão falhou: %s", exc)
        return None


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
    if name == "mdf":
        from app.analysis.tools import mdf

        return mdf(float(args["pot"]), float(args["bet"]),
                   defensores=int(args.get("defensores") or 1))
    if name == "risk_of_ruin":
        from app.analysis.bankroll import risk_of_ruin

        return risk_of_ruin(
            float(args["bankroll_buyins"]),
            float(args.get("roi_pct") or 10.0),
            float(args.get("itm_pct") or 15.0))
    if name == "save_tournament_payouts":
        from app.db import get_repository

        user_id = _TOOL_USER.get()
        repo = get_repository()
        if not user_id or not repo.enabled:
            return {"error": "não consegui salvar agora — tente de novo"}
        payouts = [float(p) for p in (args.get("payouts") or []) if float(p) > 0]
        if not payouts:
            return {"error": "premiação vazia"}
        repo.set_user_meta(user_id, "payouts", {
            "valores": payouts, "moeda": str(args.get("moeda") or "")})
        return {"ok": True, "salvos": payouts,
                "nota": "ICM automático ativado para as próximas mãos"}
    if name == "range_advantage":
        from app.analysis.range_advantage import range_advantage

        return range_advantage(
            [_norm_card(c) or c for c in args["board"]],
            str(args["range_a"]), str(args["range_b"]),
            str(args.get("label_a") or "agressor"),
            str(args.get("label_b") or "defensor"))
    if name == "blockers":
        from app.analysis.blockers import blocker_effects

        return blocker_effects(
            [_norm_card(c) or c for c in args["hero_cards"]],
            [_norm_card(c) or c for c in args["board"]],
            str(args["villain_range"]))
    if name == "analise_por_street":
        from app.bot.processing import (conversation_hand,
                                        decisions_by_street)

        tg = _TOOL_CHAT.get()
        h = conversation_hand(tg) if tg else None
        if not h:
            return {"error": "não achei a mão desta conversa para analisar"}
        return decisions_by_street(h, str(args.get("nome") or "") or None)
    if name == "definir_heroi":
        from app.bot.processing import redefine_hero

        tg = _TOOL_CHAT.get()
        if not tg:
            return {"error": "sem conversa ativa para corrigir"}
        return redefine_hero(tg, str(args.get("nome") or ""),
                             args.get("cards") or None)
    if name == "ev_por_street":
        from app.analysis.ev_streets import ev_por_street
        from app.bot.processing import conversation_hand

        tg = _TOOL_CHAT.get()
        h = conversation_hand(tg) if tg else None
        if h is None:
            return {"error": "não achei a mão desta conversa"}
        return ev_por_street(h, str(args.get("nome") or "") or None)
    if name == "potes_paralelos":
        from app.analysis.side_pots import ev_por_pote
        from app.bot.processing import conversation_hand

        tg = _TOOL_CHAT.get()
        h = conversation_hand(tg) if tg else None
        if h is None:
            return {"error": "não achei a mão desta conversa"}
        return ev_por_pote(h, str(args.get("nome") or "") or None)
    if name == "grafico_ev_da_mao":
        from app.analysis.postflop_spot import spot_da_mao
        from app.bot.processing import conversation_hand

        tg = _TOOL_CHAT.get()
        h = conversation_hand(tg) if tg else None
        spot = spot_da_mao(h, args.get("street"))
        if spot.get("error"):
            # multiway não tem matriz 13×13 (o equilíbrio pós-flop é
            # heads-up), mas TEM conta: devolve o EV por decisão em vez de
            # deixar o aluno de mãos vazias. Ele pediu o gráfico três vezes
            # e recebeu três desculpas — desculpa não é resposta.
            if "heads-up" in str(spot.get("error")):
                from app.analysis.ev_streets import ev_por_street

                alt = ev_por_street(h)
                if not alt.get("error"):
                    return {
                        "sem_grafico": spot["error"],
                        "em_vez_disso": "EV de cada decisão sua no pote "
                                        "multiway (a matriz 13×13 do "
                                        "equilíbrio é heads-up; esta conta "
                                        "não é)",
                        **alt,
                    }
            return spot
        # o aluno esperou 1 min sem sinal de vida e achou que tinha quebrado:
        # avisa ANTES de resolver o que está rodando e quanto demora
        from app.bot.notify import avisar_solver

        avisar_solver(tg, spot["board"], 2)
        try:
            from app.analysis.range_chart import _valores_posflop

            hv = _valores_posflop(tuple(spot["board"]), spot["oop_range"],
                                  spot["ip_range"], float(spot["pot"]),
                                  float(spot["stack"]), spot["player"])
        except Exception as exc:
            return {"error": f"o equilíbrio não resolveu: {str(exc)[:100]}"}
        if not hv:
            return {"error": "não consegui extrair os valores desse spot"}
        return {**{k: spot[k] for k in
                   ("street", "board", "pot", "stack", "player", "oop", "ip",
                    "oop_pos", "ip_pos", "combos", "premissas",
                    "oop_range", "ip_range")},
                "ev_medio": hv["ev_medio"],
                "melhores": dict(sorted(hv["ev"].items(),
                                        key=lambda kv: -kv[1])[:10]),
                "piores": dict(sorted(hv["ev"].items(),
                                      key=lambda kv: kv[1])[:6]),
                "agride_mais": dict(sorted(hv["freq"].items(),
                                           key=lambda kv: -kv[1])[:8]),
                "graficos": "2 (valor por mão + frequência) já a caminho",
                "nota": ("os ranges são de REFERÊNCIA pela posição/ação "
                         "pré-flop, não os ranges reais dos jogadores — diga "
                         "isso ao aluno junto do resultado")}
    if name == "range_view_posflop":
        from app.analysis.river_solver import RiverSolver

        board = [_norm_card(c) or c for c in (args.get("board") or [])]
        if len(board) not in (3, 4, 5):
            return {"error": "board precisa ter 3, 4 ou 5 cartas"}
        from app.bot.notify import avisar_solver

        avisar_solver(_TOOL_CHAT.get(), board, 1)
        try:
            solver = RiverSolver(board, str(args["oop_range"]),
                                 str(args["ip_range"]), float(args["pot"]),
                                 float(args["stack"])).solve()
            hv = solver.hand_values(str(args.get("player") or "oop"))
        except Exception as exc:
            return {"error": str(exc)[:120]}
        if not hv:
            return {"error": "não consegui extrair os valores desse spot"}
        melhores = sorted(hv["ev"].items(), key=lambda kv: -kv[1])[:10]
        piores = sorted(hv["ev"].items(), key=lambda kv: kv[1])[:6]
        return {"street": {3: "flop", 4: "turn", 5: "river"}[len(board)],
                "board": board, "player": hv["player"], "pot": hv["pot"],
                "ev_medio": hv["ev_medio"], "combos": hv["combos"],
                "melhores": dict(melhores), "piores": dict(piores),
                "agride_mais": dict(sorted(hv["freq"].items(),
                                           key=lambda kv: -kv[1])[:8]),
                "nota": ("valor em fichas por mão no equilíbrio; no equilíbrio "
                         "as ações do suporte valem o mesmo, então o que "
                         "informa é o VALOR da mão e a frequência")}
    if name == "ev_allin":
        from app.analysis.allin_engine import solve_spot

        # overcall multiway resolve a equity por simulação (bater TODOS):
        # ~20s. Espera calada parece pau — avisa antes, igual ao pós-flop.
        if str(args.get("spot")) == "overcall" and int(args.get("pagaram") or 0):
            from app.bot.notify import avisar

            avisar(_TOOL_CHAT.get(),
                   "⏳ Esse é um *overcall multiway*: preciso simular a chance "
                   "de você bater *todos* os que já pagaram, não um de cada "
                   "vez. Leva *uns 20 segundos*. (Não travou.)")
        sol = solve_spot(
            str(args.get("spot") or "open_shove"),
            str(args.get("hero_pos") or "MP"),
            round(float(args.get("stack_bb") or 10), 1),
            0.125, float(args.get("bf") or 1.0),
            (str(args["vilao_pos"]).upper() if args.get("vilao_pos") else None),
            float(args.get("open_bb") or 2.2),
            int(args.get("pagaram") or 0))
        if not sol:
            return {"error": "não consegui resolver esse spot"}
        out = {k: sol[k] for k in
               ("spot", "hero_pos", "vilao_pos", "stack", "acao_pct",
                "atras", "dead", "fold_ev", "premissas")}
        cartas = _norm_cards(args.get("cards"))
        if len(cartas) == 2:
            from app.analysis.pushfold import canonical_hand

            mao = canonical_hand(cartas)
            out["mao"] = mao
            # O NÚMERO PARA CITAR é o vs-fold: é o que o gráfico desenha e é
            # o que decide. O absoluto vai junto com nome que diz o que é —
            # antes só existia 'ev_da_mao_bb' (absoluto) e o coach escrevia
            # ele como "comparado a foldar", contradizendo o próprio gráfico.
            out["ev_vs_fold_bb"] = sol["ev_vs_fold"].get(mao)
            out["ev_absoluto_bb"] = sol["ev"].get(mao)
            out["frequencia_da_mao"] = sol["acao"].get(mao)
            out["decisao"] = ("all-in" if sol["acao"].get(mao, 0) > 0.5
                              else "fold")
        # top do range pra o coach citar sem despejar 169 mãos
        top = sorted(sol["ev_vs_fold"].items(), key=lambda kv: -kv[1])[:12]
        out["melhores_vs_fold"] = {h: v for h, v in top}
        out["como_citar"] = (
            "ev_vs_fold_bb é quanto a ação rende A MAIS que foldar — é ESTE "
            "que o gráfico mostra e ESTE que você cita ao dizer 'vs foldar' "
            "ou 'comparado a foldar'. ev_absoluto_bb é o EV bruto da ação; "
            "só use se disser explicitamente que é o valor absoluto.")
        return out
    if name == "leitura_de_mao":
        from app.analysis.equity import hand_on_board

        cards = args.get("cards") or []
        board = args.get("board") or []
        # 'QJ' numa string só (dois ranks, sem naipe) -> ['Q', 'J']
        if len(cards) == 1 and isinstance(cards[0], str):
            t = cards[0].replace("10", "T").strip()
            if len(t) == 2 and all(ch.upper() in "23456789TJQKA" for ch in t):
                cards = [t[0], t[1]]
        if len(cards) != 2 or not 3 <= len(board) <= 5:
            return {"error": "preciso de exatamente 2 cartas e um board de "
                             "3 a 5 cartas"}
        return hand_on_board(cards, board)
    if name == "pko_call":
        from app.analysis.pko import pko_call

        return pko_call(
            float(args["pot"]), float(args["to_call"]),
            float(args["villain_bounty"]), float(args["starting_bounty"]),
            float(args["starting_stack"]))
    if name == "villain_profile":
        from app.analysis.villains import villain_profile
        from app.db import get_repository

        user_id = _TOOL_USER.get()
        repo = get_repository()
        if not user_id or not repo.enabled:
            return {"error": "histórico indisponível nesta conversa"}
        hands = repo.get_all_hands(user_id, limit=500)
        prof = villain_profile(hands, str(args.get("name") or ""))
        return prof or {"error": f"nenhuma mão com '{args.get('name')}' na base "
                                 "do aluno — confirme a grafia do nome"}
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
        if args.get("mode") == "icm" and not args.get("bf"):
            # bf chutado (default) contradiz o bubble factor citado no texto
            return {"error": "mode='icm' exige bf: calcule com bubble_factor "
                             "e passe o valor exato"}
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
            if pos == "BB":
                # BB não faz open-shove (é o caller): 'Shove BB' seria um
                # gráfico de ação que não existe no jogo
                return {"error": "BB não abre de shove — para o range de CALL "
                                 "de all-in do BB use role='BB' + stack_bb"}
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
        from app.bot.notify import avisar_solver

        avisar_solver(_TOOL_CHAT.get(), args.get("board") or [], 0)
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
            num_opponents=int(args.get("num_opponents") or 1),
        )
    if name == "preflop_range":
        from app.analysis.ranges import preflop_range

        rng = preflop_range(args["position"], args.get("action", "open"))
        if not rng:
            return {"error": "posição/ação sem chart"}
        out = {"range": rng, "referencia": "deep (~25bb+)"}
        stk = args.get("stack_bb")
        try:
            stk = float(stk) if stk is not None else None
        except (TypeError, ValueError):
            stk = None
        if stk is not None and stk <= 20:
            # o aluno perguntou: '(deep)' é o torneio ou meu stack?' — é a
            # TABELA. Com 20bb ela não vale e mandar o gráfico deep engana.
            out["vale_para_este_stack"] = False
            out["aviso"] = (
                f"com {stk:g}bb NÃO use esta tabela: o spot é push/fold — "
                "chame push_fold e mande o gráfico de shove")
        elif stk is not None:
            out["vale_para_este_stack"] = True
        return out
    if name == "icm":
        from app.analysis.icm import icm_equity

        return {"equities": icm_equity(args["stacks"], args["payouts"])}
    if name == "bubble_factor":
        from app.analysis.icm import bubble_factor, icm_call_threshold

        bf = bubble_factor(args["stacks"], args["payouts"], args["hero_idx"], args["villain_idx"])
        # o limiar de call EXIGE o contexto do pote (stack efetivo, pote
        # morto, o que o herói já postou). Sem isso a fórmula antiga pedia
        # até 18 PONTOS de equity a mais e o aluno foldava call na bolha.
        thr = icm_call_threshold(
            args["stacks"], args["payouts"], args["hero_idx"],
            args["villain_idx"], args.get("stack_bb"), args.get("dead_bb"),
            args.get("post_bb"))
        out = {"bubble_factor": bf}
        if thr is None:
            out["min_call_equity"] = None
            out["por_que_sem_limiar"] = (
                "Passe stack_bb (efetivo do all-in), dead_bb (pote morto: "
                "blinds + antes + o que já está no meio) e post_bb (o que "
                "VOCÊ já postou). Sem isso não dá para calcular a equity "
                "mínima — e NÃO existe atalho: bf/(1+bf) ignora o pote morto "
                "e erra até 18 pontos, sempre mandando foldar demais.")
        else:
            out["min_call_equity"] = thr
            out["como_citar"] = (
                f"Com bf {bf:g} e esse pote, pagar precisa de "
                f"{thr * 100:.1f}% de equity. Esse número JÁ inclui o pote "
                "morto e o custo do fold — não some nada por fora.")
        return out
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
                if pos == "BB":
                    return None  # dispatch já rejeitou; sem gráfico fantasma
                stk = float(args["stack_bb"])
                if stk <= 20:
                    return ("nashpos", pos, stk, "freq")
                pct = shove_threshold(pos, stk)
                if pct:
                    return ("range", f"top {round(pct * 100)}%",
                            f"Shove {pos} ~{stk:g}bb (aprox. Nash)")
            return None
        if (name == "grafico_ev_da_mao" and isinstance(result, dict)
                and result.get("board") and not result.get("error")):
            return ("posflop", tuple(result["board"]), result["oop_range"],
                    result["ip_range"], float(result["pot"]),
                    float(result["stack"]), result["player"], "ev")
        if (name == "range_view_posflop" and isinstance(result, dict)
                and result.get("board")):
            return ("posflop", tuple(result["board"]), args["oop_range"],
                    args["ip_range"], float(result["pot"]),
                    float(args["stack"]), result.get("player") or "oop",
                    "ev" if (args.get("grafico") or "ev") == "ev" else None)
        if name == "ev_allin" and isinstance(result, dict) and result.get("spot"):
            return ("spot", result["spot"], result["hero_pos"],
                    float(result["stack"]), "freq", result.get("vilao_pos"),
                    float(args.get("open_bb") or 2.2),
                    int(args.get("pagaram") or 0))
        if name == "equity_vs_range" and args.get("villain_range"):
            return ("range", args["villain_range"], "Range assumido do vilão")
        if name == "preflop_range" and isinstance(result, dict) and result.get("range"):
            pos = args.get("position", "?").upper()
            act = args.get("action", "open")
            # '3bet vs_CO' é o range de 3-bet CONTRA o open de CO — o título
            # ambíguo ('Range de 3bet — CO') lia-se como range DO CO
            if result.get("vale_para_este_stack") is False:
                # stack curto: a tabela deep não vale. SUBSTITUI pelo gráfico
                # certo (shove) em vez de sumir com o gráfico — retornar None
                # deixava o aluno sem imagem nenhuma (regressão flagrada).
                from app.analysis.pushfold import shove_threshold

                try:
                    stk = float(args.get("stack_bb"))
                except (TypeError, ValueError):
                    stk = None
                # SB de stack curto é jam/fold heads-up de verdade: manda a
                # spec do SOLVER, que puxa o gráfico de EV por mão como
                # companhia. Nas outras posições só existe o range (o EV por
                # mão exigiria solver multiway — não fingimos que temos).
                if stk:
                    if pos in ("SB", "BB"):
                        return ("nashmode", pos, float(stk), "freq", 1.0)
                    return ("nashpos", pos, float(stk), "freq")
                return ("range", result["range"],
                        f"Open {pos} (25bb+) — só comparação")
            title = (f"Range de 3-bet contra open de {pos} — referência 25bb+"
                     if act == "3bet"
                     else f"Range de open — {pos} · referência 25bb+ (deep)")
            return ("range", result["range"], title)
        if (name == "push_fold" and isinstance(result, dict)
                and result.get("fonte") == "solver" and not result.get("role")):
            pos = str(args.get("position") or result.get("position") or "MP").upper()
            stk = float(result.get("stack_bb") or args.get("stack_bb") or 10)
            if pos in ("SB", "BB"):
                return ("nashmode", pos, stk, "freq", 1.0)
            return ("nashpos", pos, stk, "freq")
        if name == "push_fold" and isinstance(result, dict) and result.get("role"):
            return ("nash", result["role"], float(result.get("stack_resolvido") or
                                                  result.get("stack_bb") or 10))
        if (name == "push_fold" and isinstance(result, dict)
                and result.get("applicable") and result.get("shove_range_pct")):
            # posições fora de SB/BB: o gráfico É o range do veredito (top X%) —
            # sem isto o modelo desenhava range de abertura deep num
            # spot de shove e contradizia o próprio conselho
            return ("range", f"top {result['shove_range_pct']:g}%",
                    f"Shove {result.get('position', '?')} "
                    f"~{float(result.get('stack_bb') or 10):g}bb (aprox. Nash)")
    except Exception:
        return None
    return None


_SELOS_DE_VEREDITO = ("✅", "🟡", "❌")


def _montar_resposta(parts: list[str]) -> str:
    """Junta os blocos de texto do loop de tools SEM a narração de bastidor.

    O coach escreve uma frase antes de cada chamada de tool ("Deixa eu
    conferir o EV desse shove...") e a análise de verdade — a que começa
    pelo selo — só vem no turno final. Juntar tudo enterrava o selo na
    3ª linha e, com duas rodadas de tools, duplicava o preâmbulo. O juiz
    da saída mediu: era o defeito de forma nº 1 das análises entregues.

    Regra: se algum bloco começa pelo selo, a resposta começa NELE. Sem
    selo em bloco nenhum (rodadas esgotadas, resposta de conversa), nada é
    descartado — o texto pré-tools continua sendo a rede de segurança.
    """
    from app.agent.termos import corrigir

    limpos = [x.strip() for x in parts if x.strip()]
    for i, p in enumerate(limpos):
        if p.startswith(_SELOS_DE_VEREDITO):
            return corrigir("\n\n".join(limpos[i:]))
    return corrigir("\n\n".join(limpos))


def mao_simples(structured: dict) -> bool:
    """Mão de decisão ÚNICA e pré-flop — o caso que um modelo mais barato
    resolve com os números do solver já prontos no contexto.

    Conservador de propósito: qualquer decisão pós-flop, multiway no spot,
    ou ICM salvo → vai pro modelo cheio. Barato errando caro sai mais caro.
    """
    spots = structured.get("spots") or []
    if structured.get("payouts_salvos"):
        return False
    decisoes = [s for s in spots if s.get("street")]
    if len(decisoes) > 1:
        return False
    return all(s.get("street") == "preflop" for s in decisoes)


def _selo_de_emergencia(client, texto: str) -> str | None:
    """Gera SÓ a linha do selo para uma análise que saiu sem ele.

    1ª rodada do A/B: o Sonnet entregou análise sem o selo na 1ª linha — a
    regra de ouro do produto. Reescrever a análise para consertar arriscaria
    mudar conteúdo; aqui o modelo barato lê e devolve APENAS a linha
    '✅/🟡/❌ + 3-6 palavras', que é prependada deterministicamente."""
    try:
        settings = get_settings()
        resp = _create(client,
            model=settings.cheap_model,
            max_tokens=60,
            temperature=0.0,
            system=("Leia a análise de poker e devolva APENAS a primeira "
                    "linha que falta nela: o selo do veredito, exatamente "
                    "'✅ Você jogou bem' ou '🟡 Dava pra jogar melhor' ou "
                    "'❌ Jogada cara', seguido de ' — ' e 3-6 palavras "
                    "resumindo. NADA além dessa linha."),
            messages=[{"role": "user", "content": texto[:3000]}])
        linha = "".join(b.text for b in resp.content
                        if b.type == "text").strip().split("\n")[0]
        return linha if linha.startswith(_SELOS_DE_VEREDITO) else None
    except Exception:
        return None


def coach(
    structured: dict,
    stats: dict | None = None,
    lang: str = "pt",
    key_hands: list[dict] | None = None,
    collect_charts: list | None = None,
    model: str | None = None,
) -> str:
    """Gera o coaching via Claude. Cai no resumo determinístico se o LLM indisponível.

    `key_hands`: análises das mãos decisivas de um torneio — o Claude narra a
    "história do torneio" em cima delas, além do agregado.
    """
    set_tarefa("analise")
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
            "Analise esta mão. Comece pelo SELO de veredito na 1ª linha "
            "(✅ Você jogou bem / 🟡 Dava pra jogar melhor / ❌ Jogada cara). "
            "Se o herói agiu em mais de uma street, traga o PLACAR street a "
            "street logo abaixo (uma linha por street, cada uma com selo, "
            "ancorada em linha_da_mao/hand_by_street). Feche com A conta que "
            "mais pesa. Siga a regra de CLAREZA à risca. Dados estruturados "
            "(números já calculados, use-os; tools só para cálculos "
            "adicionais):\n\n"
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
        system_blocks = _bloco_cacheado(system)
        modelo_da_analise = model or settings.analysis_model
        parts: list[str] = []  # texto escrito ANTES das tools não pode sumir
        for _ in range(MAX_TOOL_ROUNDS):
            resp = _create(client,
                model=modelo_da_analise,
                max_tokens=1500,
                temperature=0.2,  # coach não pode mudar de veredito por sorteio
                system=system_blocks,
                tools=TOOLS,
                messages=messages,
            )
            parts.extend(b.text for b in resp.content if b.type == "text")
            if resp.stop_reason != "tool_use":
                final = _montar_resposta(parts)
                if final and key_hands is None and \
                        not final.startswith(_SELOS_DE_VEREDITO):
                    selo = _selo_de_emergencia(client, final)
                    if selo:
                        final = selo + "\n\n" + final
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
        final = _montar_resposta(parts)
        if final and key_hands is None and \
                not final.startswith(_SELOS_DE_VEREDITO):
            selo = _selo_de_emergencia(client, final)
            if selo:
                final = selo + "\n\n" + final
        return final or fallback
    except Exception:
        # qualquer falha de rede/SDK -> resumo determinístico
        return fallback


def prepare_briefing(ctx: dict, lang: str = "pt") -> str | None:
    """Briefing pré-torneio personalizado (fase 1 do /preparar).

    Uma chamada sem tools: todos os números já vêm calculados no contexto
    (leaks em bb/100, stats corrigidas, padrão de tilt, caderno). O texto
    fecha com METAS parseáveis ('META 1:' / 'META 2:') que viram notas no
    caderno do coach — o relatório pós-torneio vai cobrá-las (fase 3).
    """
    set_tarefa("briefing")
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    system = (
        "Você é um coach de poker brasileiro preparando seu aluno para um "
        "torneio HOJE. Papo de mesa, direto, veredito primeiro — nada de "
        "soar robótico, nada de mencionar sistema/dados, PROIBIDO adjetivar "
        "('brutal', 'honesto'). Registro sempre 'você'. "
        "NUNCA invente números: use APENAS os números do contexto (leaks em "
        "bb/100, stats, tilt); sem número, fale qualitativo. " + TERMOS_REGRA +
        "\nEstrutura da resposta (máx ~2500 caracteres, Telegram, *negrito*, "
        "sem cabeçalhos '#'):\n"
        "1) Abertura curta de coach (1 frase, considerando o que o aluno "
        "disse do torneio de hoje, se disse).\n"
        "2) *O que vigiar hoje*: os leaks do contexto, cada um em 1-2 frases "
        "com o custo em bb/100 e a correção prática.\n"
        "3) *Protocolo mental*: se o contexto traz padrão de tilt, "
        "personalize (gatilho dele + contramedida concreta); senão, 2 frases "
        "de protocolo padrão (pote grande perdido → pausa; decisão ≠ "
        "resultado).\n"
        "4) *Plano por fase*: UMA linha para cada — início (deep), "
        "meio (20-40bb), bolha (pressão de ICM), mesa final (push/fold). "
        "Se o contexto trouxer dicas_do_formato, INCORPORE-AS aqui e no "
        "briefing (são regras verificadas do formato/field do torneio de "
        "hoje — turbo/PKO/freezeout/field) — NÃO invente outras regras de "
        "formato além delas. Se houver gráfico de range implícito no "
        "formato, mencione 'o range segue no gráfico abaixo'. Se o aluno "
        "NÃO disse o formato do torneio, feche o plano com uma linha "
        "convidando: da próxima, diga o formato (turbo? PKO? buy-in?) que "
        "a preparação fica mais afinada.\n"
        "5) Feche com EXATAMENTE duas linhas no formato:\n"
        "META 1: <meta comportamental concreta e verificável nas mãos>\n"
        "META 2: <idem>\n"
        "As metas saem dos leaks/tilt do contexto — específicas, não "
        "genéricas ('não pagar 3-bet fora de posição com par médio', não "
        "'jogar bem')."
    )
    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        resp = _create(client,
            model=settings.analysis_model,
            max_tokens=1100,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": json.dumps(
                ctx, ensure_ascii=False, indent=2)}],
        )
        out = "".join(b.text for b in resp.content if b.type == "text").strip()
        return out or None
    except Exception as exc:
        logging.getLogger("llm").warning("prepare_briefing falhou: %s", exc)
        return None


# A FORMA do 🎈. A análise já sai em português simples e já glosa os números
# — pedir "mais simples" sem impor forma devolvia um parágrafo quase igual.
# O que muda de verdade é a ESTRUTURA: veredito numa frase, o porquê em
# pedaços curtos, UM número. Isso o texto original nunca tem.
_FORMA_SIMPLES = (
    "FORMA OBRIGATÓRIA, nesta ordem e sem cabeçalho nenhum: (1) uma frase "
    "só, começando com 'Em resumo:', dizendo o que ele fez e se foi bom; "
    "(2) linha vazia; (3) duas ou três linhas começando com '• ', cada uma "
    "com no máximo 14 palavras, explicando o porquê; (4) linha vazia; "
    "(5) uma última linha começando com 'O número que importa:' com UM "
    "número só e o que ele significa na prática. Nada além disso. "
    "Português informal, formato Telegram. Nunca diga que é uma reescrita."
)


# por que o 🎈 não devolveu nada. "" = deu certo. Existe porque as duas
# causas pedem respostas OPOSTAS ao aluno: com a API fora o coach não rodou
# (e dizer "já está simples" seria mentira); com a API de pé e o texto já
# simples, "me embananei" é que seria mentira.
LAST_SIMPLIFY_REASON = ""


def _palavras(t: str) -> set[str]:
    """Palavras de 4+ letras, sem acento nem pontuação — o esqueleto do texto."""
    import unicodedata

    n = unicodedata.normalize("NFKD", (t or "").lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z]{4,}", n)}


def parecidos(a: str, b: str, teto: float = 0.6) -> bool:
    """b é só uma maquiagem de a? Compara o vocabulário, não os caracteres.

    Serve ao botão 🎈: reescrever com outras palavras a mesma estrutura não
    ajuda ninguém. Mede quanto do texto NOVO já estava no velho — assimétrico
    de propósito: um resumo curto e fiel ao original tem overlap alto e É uma
    cópia; o contrário (texto novo com muita palavra nova) não é.
    """
    pa, pb = _palavras(a), _palavras(b)
    if not pb:
        return True
    return len(pa & pb) / len(pb) > teto


def simplify(text: str) -> str | None:
    """Reescreve a última explicação do coach para um iniciante TOTAL.

    Modelo barato, sem tools — resposta rápida. None se o LLM está fora OU se
    não conseguiu ficar mais simples que o original; quem chama distingue os
    dois casos por LAST_SIMPLIFY_REASON e diz a verdade ao aluno.
    """
    global LAST_SIMPLIFY_REASON
    LAST_SIMPLIFY_REASON = "indisponivel"
    set_tarefa("simplificar")
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
                "Você é um coach de poker reescrevendo uma análise para um "
                "aluno que JOGA, mas não é profissional: ele conhece as regras "
                "e o básico, só não domina o vocabulário técnico nem as "
                "contas. NÃO infantilize — nada de analogia de padaria nem de "
                "explicar o que é um flop. Mantenha o mesmo veredito e a mesma "
                "conclusão. Os termos técnicos FICAM (é assim que ele aprende "
                "o idioma da mesa); os menos óbvios ganham uma explicação "
                "curta entre parênteses na primeira vez — 'OESD (straight "
                "draw pelas duas pontas)' — termo trivial (fold, all-in, "
                "flop) não ganha parêntese. Até 2-3 números, cada um com o "
                "que significa na prática ('pedia 30% = precisa ganhar 1 em "
                "cada 3'). " + TERMOS_REGRA + " " + _FORMA_SIMPLES
            ),
            messages=[{"role": "user", "content": text[:6000]}],
        )
        out = "".join(b.text for b in resp.content if b.type == "text").strip()
        from app.agent.termos import corrigir

        out = corrigir(out) or ""
        # CONFERE em vez de torcer: a análise já sai em português simples e
        # já explica os números entre parênteses, então "reescreva mais
        # simples" devolvia quase o mesmo texto e o botão parecia quebrado.
        # Uma segunda tentativa, com a forma imposta na marra.
        if out and parecidos(text, out):
            resp2 = _create(client,
                model=settings.cheap_model,
                max_tokens=700,
                temperature=0.4,
                system=("Reescreva a análise abaixo SEGUINDO A FORMA À RISCA. "
                        "A tentativa anterior saiu parecida demais com o "
                        "original — mude a ESTRUTURA, não só as palavras. "
                        + _FORMA_SIMPLES + " " + TERMOS_REGRA),
                messages=[{"role": "user", "content": text[:6000]}],
            )
            out2 = "".join(b.text for b in resp2.content
                           if b.type == "text").strip()
            out2 = corrigir(out2) or ""
            if out2 and not parecidos(text, out2):
                LAST_SIMPLIFY_REASON = ""
                return out2
            # não conseguiu simplificar: quem chamou avisa, em vez de mandar
            # o mesmo texto de novo e o aluno achar que o botão não fez nada
            LAST_SIMPLIFY_REASON = "ja_simples"
            return None
        if out:
            LAST_SIMPLIFY_REASON = ""
        return out or None
    except Exception:
        return None


_NOTE_KINDS = ("leak", "progresso", "meta", "estilo")


def _parse_notebook_notes(text: str) -> list[dict]:
    """Valida o JSON do destilador de sessão: até 2 notas, kinds conhecidos,
    texto não-vazio com teto — lixo do modelo não entra no caderno."""
    try:
        data = json.loads(_strip_code_fence(text or ""))
    except Exception:
        return []
    out = []
    for n in (data.get("notas") or []):
        kind = str((n or {}).get("kind") or "").strip().lower()
        note = str((n or {}).get("note") or "").strip()
        if kind in _NOTE_KINDS and note:
            out.append({"kind": kind, "note": note[:300]})
        if len(out) == 2:      # teto DEPOIS de filtrar: inválida não gasta vaga
            break
    return out


def session_notebook_notes(history: list[dict], resumo_mao: str,
                           notas_existentes: list[str]) -> list[dict]:
    """Destila uma conversa ENCERRADA em 0-2 observações novas pro caderno do
    aluno (modelo barato, sem tools). O que a conversa revelou sobre COMO o
    aluno pensa — dúvida recorrente, conceito mal calibrado, progresso — e que
    ainda não esteja no caderno. Lista vazia se nada novo: melhor calar que
    repetir."""
    set_tarefa("caderno")
    from app.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key or len(history or []) < 2:
        return []
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        convo = "\n".join(
            f"ALUNO: {t.get('q', '')}\nCOACH: {str(t.get('a', ''))[:600]}"
            for t in history[-6:])
        resp = _create(
            client,
            model=settings.cheap_model,
            max_tokens=400,
            temperature=0.2,
            system=(
                "Você mantém o caderno de um coach de poker sobre um aluno. "
                "Da conversa abaixo (já encerrada), extraia NO MÁXIMO 2 "
                "observações NOVAS sobre o aluno — como ele pensa, o que "
                "calibra mal, dúvida que repete, progresso real. Não anote "
                "fatos da mão em si, só o que ensina sobre o ALUNO. Não "
                "repita nem parafraseie o que o caderno já tem. Cada nota: "
                "1 frase, específica, em português. Responda SÓ com JSON: "
                '{"notas": [{"kind": "leak|progresso|meta|estilo", '
                '"note": "..."}]} — e {"notas": []} se a conversa não '
                "revelou nada novo (o normal)."
            ),
            messages=[{"role": "user", "content":
                       f"CADERNO ATUAL:\n- " + "\n- ".join(
                           notas_existentes[:8] or ["(vazio)"])
                       + f"\n\nMÃO DISCUTIDA: {(resumo_mao or '')[:400]}"
                       + f"\n\nCONVERSA:\n{convo[:5000]}"}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text")
        return _parse_notebook_notes(text)
    except Exception:
        logging.getLogger("llm").debug("destilador de sessão falhou", exc_info=True)
        return []


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
    set_tarefa("conversa")
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
            "\nRESPONDA PRIMEIRO, confirme depois: se a narração do aluno vier "
            "ambígua (áudio transcrito embaralha street e carta), responda JÁ o "
            "que dá para responder com o que está claro, e SÓ ENTÃO confirme o "
            "detalhe que falta — uma pergunta no máximo, e apenas se mudar o "
            "veredito. Nunca gaste a resposta inteira pedindo confirmação. "
            "\nNÃO narre bastidor de busca: 'deixa eu puxar a mão', 'não "
            "consegui encontrar o histórico' — se uma busca falhar, siga com o "
            "que o aluno contou, sem anunciar a falha. "
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
        system_blocks = _bloco_cacheado(system)
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
                final = _montar_resposta(parts)
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
        final = _montar_resposta(parts)
        return final or _force_text(
            client, settings.analysis_model, system_blocks, messages)
    except Exception as exc:
        logging.getLogger("llm").warning(
            "resposta do coach falhou (%s): %s", type(exc).__name__, exc)
        # o MOTIVO vai pro evento followup_failed — 5 falhas em 7 dias
        # (Ricardo 3x, o usuário novo na 1ª pergunta) e o banco só tinha a
        # pergunta: a causa morria neste log de processo
        global LAST_FOLLOWUP_ERROR
        LAST_FOLLOWUP_ERROR = f"{type(exc).__name__}: {exc}"[:300]
        return None


def evaluate_line(sim_data: dict, lang: str = "pt",
                  collect_charts: list | None = None) -> str | None:
    """Modo "e se": avalia a linha ALTERNATIVA que o aluno escolheu na simulação.

    Para cada decisão divergente da real, julga (com as tools) se a escolha do
    aluno era melhor, pior ou equivalente — e quantifica. None sem chave/erro.
    """
    set_tarefa("simulador")
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
        system_blocks = _bloco_cacheado(system)
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
                final = _montar_resposta(parts)
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
        final = _montar_resposta(parts)
        return final or _force_text(
            client, settings.analysis_model, system_blocks, messages)
    except Exception as exc:
        logging.getLogger("llm").warning(
            "resposta do coach falhou (%s): %s", type(exc).__name__, exc)
        # o MOTIVO vai pro evento followup_failed — 5 falhas em 7 dias
        # (Ricardo 3x, o usuário novo na 1ª pergunta) e o banco só tinha a
        # pergunta: a causa morria neste log de processo
        global LAST_FOLLOWUP_ERROR
        LAST_FOLLOWUP_ERROR = f"{type(exc).__name__}: {exc}"[:300]
        return None


def synthesize_answer(query: str, snippets: list[str], lang: str = "pt") -> str | None:
    """Sintetiza uma resposta ao /ask a partir dos resumos recuperados (RAG).

    Usa o modelo barato (Haiku) — tarefa simples de síntese, não de julgamento.
    Retorna None sem chave/erro (o chamador mostra os resumos crus).
    """
    set_tarefa("busca")
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
                "Você é um coach de poker. Responda à pergunta do jogador usando APENAS "
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
    "Você recebe um print/foto de poker (mesa ao vivo OU replay/histórico de mão — "
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
    "Campo ilegível = null/vazio. NÃO invente valores — extraia só o que está na imagem.\n"
    "UNIDADE: blinds, stacks, amounts e total_pot têm que sair TODOS na MESMA "
    "unidade. Muita sala mostra o nível em fichas no cabeçalho (ex.: 15000/30000) "
    "e os stacks na mesa em bb (ex.: 17.4) ao mesmo tempo — nesse caso converta "
    "os blinds para bb (small_blind 0.5, big_blind 1) e devolva tudo em bb."
)


def extract_from_hand_text(text: str) -> CanonicalHand | None:
    """Fallback por IA para texto de mão em formato desconhecido.

    Qualquer sala/idioma/estilo (inclusive resumos escritos à mão): o modelo
    converte para o mesmo JSON da visão e reaproveitamos _snapshot_to_canonical.
    Retorna None sem chave ou se a extração falhar.
    """
    set_tarefa("leitura_texto")
    settings = get_settings()
    if not settings.anthropic_api_key or not text.strip():
        return None
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "O texto abaixo descreve uma mão de poker num formato não padronizado "
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


_VISION_VERIFY_PROMPT = (
    "Você fez uma PRIMEIRA leitura deste print de poker (JSON abaixo). Agora "
    "CONFIRA carta por carta, olhando a imagem de novo, APENAS os campos "
    "críticos: hero_cards, board (cartas comunitárias visíveis) e o stack do "
    "herói. Responda APENAS JSON:\n"
    '{"confere": true|false,\n'
    ' "divergencias": ["hero_cards: li A♠K♣, a 1ª leitura diz A♠K♦", ...],\n'
    ' "correcao": {"hero_cards": [...], "board": [...], "hero_stack": 0}}\n'
    "Em 'correcao' inclua SÓ os campos em que a 1ª leitura errou (vazio se "
    "conferiu). Se a imagem estiver ambígua num campo (carta coberta, "
    "borrada), liste em divergencias com o texto 'AMBÍGUO: ...'.\n\n"
    "1ª leitura:\n"
)


def _merge_vision_check(data: dict, check: dict) -> tuple[dict, list[str]]:
    """Aplica a verificação da 2ª passada à 1ª leitura (função pura).

    Correções da 2ª passada valem para os campos críticos; devolve também a
    lista de divergências (vai pro coach confirmar com o aluno)."""
    div = [str(d)[:160] for d in (check.get("divergencias") or [])][:6]
    corr = check.get("correcao") or {}
    if corr.get("hero_cards"):
        data = {**data, "hero_cards": corr["hero_cards"]}
    if corr.get("board"):
        data = {**data, "board": corr["board"]}
    if corr.get("hero_stack") and data.get("players"):
        hero_name = data.get("hero_name")
        players = [dict(p) for p in data["players"]]
        for p in players:
            if p.get("name") == hero_name:
                p["stack"] = corr["hero_stack"]
        data = {**data, "players": players}
    return data, div


# leitura dupla do último print: divergências vão pro contexto do coach —
# ele CONFIRMA com o aluno em vez de chutar (item 5 do roadmap-10)
LAST_VISION_CHECK: dict | None = None


def extract_from_image(image_bytes: bytes, media_type: str = "image/png") -> CanonicalHand | None:
    """Extrai um snapshot de mão de um print via visão do Claude — em DUAS
    passadas: extração + conferência carta a carta (tarefa diferente pega
    erro de leitura melhor que repetir a extração). Divergências reduzem a
    confiança e vão pro coach confirmar com o aluno.

    Retorna um `CanonicalHand` parcial com `confidence` < 1.0 (dado de visão é menos
    confiável que hand history nativa). Sem chave/lib ou em falha, retorna None.
    """
    set_tarefa("leitura_print")
    global LAST_VISION_CHECK
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
        img_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        }
        resp = _create(client,
            model=settings.analysis_model,
            max_tokens=1024,
            temperature=0.0,  # extração: determinística
            messages=[
                {"role": "user",
                 "content": [img_block, {"type": "text", "text": _VISION_PROMPT}]}
            ],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        data = json.loads(_strip_code_fence(text))

        # 2ª passada: conferência dos campos críticos
        LAST_VISION_CHECK = None
        divergencias: list[str] = []
        try:
            core = {k: data.get(k) for k in
                    ("hero_cards", "board", "hero_name", "players")}
            resp2 = _create(client,
                model=settings.analysis_model,
                max_tokens=500,
                temperature=0.0,
                messages=[
                    {"role": "user",
                     "content": [img_block,
                                 {"type": "text",
                                  "text": _VISION_VERIFY_PROMPT
                                  + json.dumps(core, ensure_ascii=False)}]}
                ],
            )
            t2 = "".join(b.text for b in resp2.content if b.type == "text")
            check = json.loads(_strip_code_fence(t2))
            data, divergencias = _merge_vision_check(data, check)
        except Exception as exc:
            logging.getLogger("llm").warning("verificação de visão falhou: %s", exc)
        LAST_VISION_CHECK = {"divergencias": divergencias,
                             "conferido": not divergencias}

        hand = _snapshot_to_canonical(data, fingerprint=_fingerprint(image_bytes))
        if hand is not None and divergencias:
            hand.confidence = min(hand.confidence or 0.6, 0.5)
        return hand
    except Exception as exc:
        # a exceção era ENGOLIDA: 'não consegui ler' sem nenhum rastro
        logging.getLogger("llm").warning("extract_from_image falhou: %s", exc)
        global LAST_VISION_ERROR
        LAST_VISION_ERROR = f"{type(exc).__name__}: {exc}"[:300]
        return None


def _coerir_unidades(stakes, players) -> bool:
    """Conserta o print que vem com o nível em FICHAS e os stacks em BB.

    Caso real (29/07, primeira mão do Antônio): a sala mostrava '15000/30000'
    no cabeçalho e a mesa em bb (stacks 17.4, 66.6...; pote 10.1). A visão
    transcreveu os dois literalmente, e tudo lá embaixo divide por big_blind:
    17.4/30000 = 0.0. O coach recebeu stack 0, pote 0, aposta 0 — e pediu ao
    aluno o stack efetivo que já estava no print.

    O sinal é impossível de acontecer de verdade: o MAIOR stack da mesa não
    pode ser menor que um big blind (o pote sozinho já seria maior que todo
    mundo). Quando isso aparece, quem está fora de escala são os blinds —
    stacks, apostas e pote já estão em bb. Então trazemos os blinds para bb.

    Devolve True se corrigiu. Mexe só em `stakes` (mutação in place).
    """
    bb = float(getattr(stakes, "big_blind", 0) or 0)
    maior = max((float(p.stack or 0) for p in players), default=0.0)
    if bb <= 0 or maior <= 0 or maior >= bb:
        return False
    stakes.small_blind = round((stakes.small_blind or 0) / bb, 4)
    stakes.ante = round((stakes.ante or 0) / bb, 4)
    stakes.big_blind = 1.0
    logging.getLogger("llm").warning(
        "unidades mistas no print: blinds em fichas (bb=%s) e stacks em bb "
        "(maior=%s) — blinds convertidos para bb", bb, maior)
    return True


# última exceção da visão — vai para a nota do upload_failed (legível por SQL)
LAST_VISION_ERROR: str | None = None

# última exceção do followup — vai pro detail do evento followup_failed
LAST_FOLLOWUP_ERROR: str | None = None


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

    _coerir_unidades(stakes, players)

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
