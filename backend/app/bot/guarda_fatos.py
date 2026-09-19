"""GUARDA DOS FATOS — a análise afirma coisa que não é verdade?

Caso real (07/08, print do dono): numa análise de KK pagando all-in, o coach
escreveu "o vilão só te vira favorito com QQ ou AA". KK ganha de QQ em 80%
das vezes. O aluno que acredita nisso passa a foldar KK contra 4-bet.

Isso é da mesma família do guarda da saída: o prompt JÁ proíbe (F1 "nunca
invente números", F4 "sem showdown fale em range"), e mesmo assim saiu. Regra
é pedido; isto é conferência — e esta dá pra fazer com a conta na mão, porque
"X é favorito contra Y" é uma pergunta fechada que o motor de equity responde.

Só mexe no que consegue PROVAR errado: acha a frase, testa cada mão citada,
e corrige a lista para as mãos que realmente ganham do herói. Sem frase do
tipo, não toca em nada.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

# "só te vira favorito com QQ ou AA", "só perde para AA", "só está atrás de AA"
_DOMINANCIA = re.compile(
    # o VERBO em qualquer tempo: "só perde para AA" pegava, mas o texto real
    # entregue em 07/08 dizia "só PERDIA pra 77 ou AA/1010" — imperfeito — e
    # passou batido. Mesma armadilha em "perdeu", "perdem", "perderia".
    r"(?P<abre>só\s+(?:te\s+)?(?:vira\s+favorito\s+(?:com|contra)|"
    r"perd(?:e|ia|eu|em|iam|eria|eriam)\s+(?:para|pra|pro)|"
    r"est[aá]\s+atr[áa]s\s+d[eo]|estava\s+atr[áa]s\s+d[eo]|"
    r"fica\s+atr[áa]s\s+d[eo]|ficava\s+atr[áa]s\s+d[eo]|"
    r"apanha(?:va)?\s+(?:para|pra|de)))"
    # A LISTA ACEITA VÍRGULA, e é `_so_a_lista` quem a corta.
    #
    # Excluir a vírgula na regex parecia seguro e escondia o pior defeito do
    # guarda: "Você só perde para AA, QQ ou JJ" capturava só `AA`. Como AA é
    # verdade, o guarda devolvia `erros=[]` — declarava a frase LIMPA com
    # duas mentiras dentro, e o evento `fato_corrigido` não disparava. Medido
    # em 09/08; pior que não checar, porque o portal registra a análise como
    # conferida.
    #
    # O travessão e o ponto seguem fora: "só perdia pra 77 ou AA — o vilão
    # apareceu com 72s" não pode virar uma lista só.
    r"\s+(?P<maos>[^.;\n—–]{1,80})", re.I)

# A MESMA mentira com a ordem trocada: "Só AA e QQ te viram favorito" (lição
# 26, real, com KK na mão). O verbo vem DEPOIS das mãos, então o padrão de
# cima não via nada — e essa é justamente a forma que o destilador escreve,
# porque copia o título ("Só X te vira favorito") em vez da frase corrida.
_DOMINANCIA_INVERTIDA = re.compile(
    r"(?P<abre>\bs[óo]|\bapenas|\bsomente)\s+"
    r"(?P<maos>[^.;\n—–]{1,80}?)\s+"
    r"(?P<fecha>(?:te\s+)?(?:vira(?:m|ram|va|vam)?\s+favorito|"
    r"ganha(?:m|va|vam)?\s+de\s+(?:voc[êe]|vc|ti|si)|"
    r"te\s+bate(?:m|ria|riam)?|"
    r"est[áa](?:o)?\s+na\s+frente|estava(?:m)?\s+na\s+frente))", re.I)

# AA, KK, AKs, AKo, QQ+ — o vocabulário de mão que aparece nessas frases
_MAO = re.compile(r"\b([AKQJT2-9])\1\b|\b([AKQJT2-9])([AKQJT2-9])([so])\b",
                  re.I)

_NAIPES = ("h", "d", "c", "s")


def _combos(nota: str) -> list[list[str]] | None:
    """'QQ' -> [['Qh','Qd']]; 'AKo' -> [['Ah','Kd']]; 'AKs' -> [['Ah','Kh']].

    Um combo representativo basta: a equity pré-flop de QQ contra KK é a
    mesma para qualquer par de naipes (a menos de bloqueio irrelevante aqui).
    """
    n = nota.strip().upper().replace("10", "T")
    if len(n) == 2 and n[0] == n[1]:
        return [[n[0] + "h", n[1] + "d"]]
    if len(n) == 3 and n[2] in ("S", "O"):
        a, b = n[0], n[1]
        if a == b:
            return None
        return [[a + "h", b + "h"]] if n[2] == "S" else [[a + "h", b + "d"]]
    return None


def maos_citadas(trecho: str) -> list[str]:
    """As mãos nomeadas num pedaço de frase, na ordem em que aparecem."""
    achadas = []
    for m in _MAO.finditer(trecho or ""):
        if m.group(1):
            nota = (m.group(1) * 2).upper()
        else:
            nota = (m.group(2) + m.group(3) + m.group(4)).upper()
            nota = nota[:2] + nota[2].lower()
        if nota not in achadas:
            achadas.append(nota)
    return achadas


def quem_ganha_do_heroi(hero: list[str], candidatas: list[str],
                        board: list[str] | None = None) -> list[str]:
    """Das mãos citadas, quais REALMENTE ganham do herói.

    COM board, a conta é sobre a mão FEITA — que é outra pergunta. "seu full
    de 7 com A só perdia pra 77" é uma frase de river, e comparar equity
    pré-flop ali responde a pergunta errada: pré-flop 77 é favorito contra
    A7s, mas NAQUELE board o herói tem full de 7 com A e 77 seria quadra
    impossível. Sem board (frase de pré-flop), segue a equity de mão vs mão.
    """
    from app.analysis.equity import equity_vs_hand, equity_vs_hands

    b = [c for c in (board or []) if isinstance(c, str) and c]
    mortas = {(c[0].upper() + c[1:].lower()) for c in list(hero) + b}
    vencem = []
    for nota in candidatas:
        combos = _combos(nota)
        if not combos:
            continue
        vil = combos[0]
        # mão que usa carta já visível não é combo possível — pula em vez de
        # devolver equity de um baralho impossível
        if {(c[0].upper() + c[1:].lower()) for c in vil} & mortas:
            continue
        try:
            eq = (equity_vs_hands(list(hero), [vil], b) if len(b) >= 3
                  else equity_vs_hand(list(hero), vil))
        except Exception:
            continue
        if eq is None:
            continue
        if eq < 0.5:                      # o herói perde => a citada ganha
            vencem.append(nota)
    return vencem


def conferir_dominancia(texto: str, hero: list[str],
                        board: list[str] | None = None) -> tuple[str, list[str]]:
    """Corrige frases de 'só perde para X'. Devolve (texto, erros_achados).

    Conservador: se NENHUMA das mãos citadas ganha do herói, a frase inteira
    é falsa e vira o nome da mão que realmente ganha; se alguma ganha e outra
    não, ficam só as verdadeiras. Sem mão citada, não mexe.

    `board` muda a PERGUNTA: com mesa, a conta é sobre a mão feita. Sem ele,
    uma frase de river era conferida com equity pré-flop — resposta certa
    para a pergunta errada.
    """
    if not texto or not hero or len(hero) != 2:
        return texto, []

    erros: list[str] = []

    def _e_sobre_o_heroi(inicio: int, frase: str = "") -> bool:
        """A afirmação é sobre a mão do ALUNO?

        `conferir_dominancia` sempre conferiu contra `hero_cards` sem olhar de
        quem a frase fala. "O vilão só perde para AA e KK" com o herói de KK
        virava "O vilão só perde para AA" — o guarda apagando informação
        CERTA sobre o oponente. Medido em 09/08.

        Mas SUJEITO não basta, e a primeira versão desta função quebrou o caso
        que criou o módulo: "O vilão só te vira favorito com QQ ou AA" tem
        sujeito de terceira pessoa E é sobre o herói, porque o objeto é o
        "te". O que decide é a referência ao aluno DENTRO da própria frase;
        o sujeito só desempata quando ela não existe.
        """
        if re.search(r"\b(te|voc[êe]|vc|ti|contigo)\b", frase or "", re.I):
            return True
        antes = texto[max(0, inicio - 60):inicio].lower()
        # corta na fronteira de oração anterior: sujeito de outra frase não
        # governa esta
        for corte in (".", ";", "\n", "—", "–"):
            if corte in antes:
                antes = antes.rsplit(corte, 1)[1]
        if re.search(r"\b(voc[êe]|vc|seu|sua|teu|tua)\b", antes):
            return True
        return not re.search(
            r"\b(o\s+vil[ãa]o|o\s+oponente|o\s+advers[áa]rio|ele|ela|"
            r"o\s+outro|o\s+cara)\b", antes)

    def _verdade(citadas: list[str]) -> tuple[list[str], str] | None:
        """(mentiras, lista_certa) — None quando a frase já está correta."""
        vencem = quem_ganha_do_heroi(hero, citadas, board)
        mentiras = [x for x in citadas if x not in vencem]
        if not mentiras:
            return None
        if vencem:
            return mentiras, " ou ".join(vencem)
        # nenhuma das citadas ganha: procura a verdade entre os pares
        # altos, que é de onde essa frase sempre fala
        return mentiras, " ou ".join(_pares_que_ganham(hero, board)) or "nada"

    def _corrige(m: re.Match) -> str:
        if not _e_sobre_o_heroi(m.start(), m.group(0)):
            return m.group(0)
        lista, cauda = _so_a_lista(m.group("maos"))
        citadas = maos_citadas(lista)
        if not citadas:
            return m.group(0)
        achado = _verdade(citadas)
        if not achado:
            return m.group(0)
        mentiras, certo = achado
        erros.extend(mentiras)
        # preserva o resto da frase depois das mãos (", e isso é raro")
        return f"{m.group('abre')} {certo}{cauda}"

    def _corrige_invertida(m: re.Match) -> str:
        if not _e_sobre_o_heroi(m.start(), m.group(0)):
            return m.group(0)
        citadas = maos_citadas(m.group("maos"))
        if not citadas:
            return m.group(0)
        achado = _verdade(citadas)
        if not achado:
            return m.group(0)
        mentiras, certo = achado
        erros.extend(mentiras)
        return f"{m.group('abre')} {certo} {m.group('fecha')}"

    novo = _DOMINANCIA.sub(_corrige, texto)
    novo = _DOMINANCIA_INVERTIDA.sub(_corrige_invertida, novo)
    if erros:
        log.warning("guarda de fatos: mão citada como favorita sem ser: %s",
                    ", ".join(erros))
    return novo, erros


_LIGA = re.compile(r"^[\s,]*(?:e|ou|nem)?[\s,]*$", re.I)


def _so_a_lista(trecho: str) -> tuple[str, str]:
    """Corta o trecho no ponto em que ele deixa de ser enumeração de mãos.

    Aceitar vírgula na regex é o que permite ver "AA, QQ ou JJ" inteiro — mas
    também deixaria entrar "AA, e por isso você paga". A diferença é
    verificável: entre duas mãos de uma lista só cabem vírgula, espaço e
    conector ("e", "ou", "nem"). Qualquer outra palavra fecha a lista.

    Devolve (lista, cauda).
    """
    achadas = list(_MAO.finditer(trecho or ""))
    if not achadas:
        return trecho, ""
    fim = achadas[0].end()
    for anterior, seguinte in zip(achadas, achadas[1:]):
        if not _LIGA.match(trecho[anterior.end():seguinte.start()]):
            break
        fim = seguinte.end()
    return trecho[:fim], trecho[fim:]


def _cauda(trecho: str, citadas: list[str]) -> str:
    """O que vem depois da última mão citada — vírgula, 'e isso é raro', etc."""
    fim = 0
    for m in _MAO.finditer(trecho):
        fim = m.end()
    resto = trecho[fim:]
    if resto.strip():
        return resto
    # só espaço em branco: devolve UM espaço, não string vazia — sem isso
    # "pra AA — o vilão" saía colado ("pra AA— o vilão")
    return " " if resto else ""


# "A conta que mais pesa:", "a conta:", "fazendo a conta" — o coach ANUNCIA
# que vai mostrar a matemática
_ANUNCIA_CONTA = re.compile(
    r"^[^\n]{0,40}\ba\s+conta\b[^\n]{0,40}:", re.I | re.M)
# O que conta como CONTA. Exigir sufixo bb/%/fichas reprovava as duas formas
# mais básicas da matemática de poker, e o falso positivo aqui é caro: o
# evento diz que a análise enrolou quando ela mostrou a conta certinha.
#
#   "o pote paga 2.5 para 1 e você tem 1 em 3"   <- pot odds, em razão
#   "você tem 9 outs, 4 e 2 no turn"             <- outs
#
# Não é afrouxar até `\d`: número solto continua NÃO sendo conta. "paga esse
# all-in 2 vezes" e "na 3ª street" seguem reprovados, que é o caso do print
# de 07/08 e o motivo de o guarda existir.
_TEM_NUMERO = re.compile(
    r"""[-+−]?\d+[.,]?\d*\s*(?:bb|%|fichas|bb/100)   # 12bb, 30%, 5000 fichas
      | [-+−]\d+[.,]\d                               # +8.2, -1,5
      | \d+%                                         # 30%
      | \d+[.,]?\d*\s*(?:para|:)\s*\d                # 2.5 para 1, 3:1
      | \d+\s*(?:vez(?:es)?\s+)?em\s*(?:cada\s+)?\d  # 1 em 3, 2 vezes em cada 10
      | \d+\s*outs?\b                                # 9 outs
    """, re.I | re.X)


def conta_sem_numero(texto: str) -> list[str]:
    """Parágrafos que se anunciam como 'a conta' e não trazem número nenhum.

    No print de 07/08: "A conta que mais pesa: com KK e stack curto você paga
    esse all-in sempre, sem pensar duas vezes." Prosa com nome de conta — e
    era a TERCEIRA vez que o texto dizia a mesma coisa, o que faz o aluno
    achar que o coach está enrolando.

    Só DETECTA (vira evento). Reescrever prosa de LLM na marra estraga mais
    do que conserta; o que isto dá é a taxa — se for alta, o prompt está
    errado e eu conserto lá, com número na mão em vez de impressão.
    """
    achados = []
    for m in _ANUNCIA_CONTA.finditer(texto or ""):
        # o parágrafo inteiro a partir do anúncio
        fim = (texto or "").find("\n\n", m.start())
        trecho = (texto or "")[m.start():fim if fim > 0 else len(texto or "")]
        if not _TEM_NUMERO.search(trecho):
            achados.append(trecho[:120].strip())
    return achados


def _pares_que_ganham(hero: list[str],
                      board: list[str] | None = None) -> list[str]:
    """Os pares que ganham do herói (a resposta que a frase queria dar).
    Só pares: é o caso que aparece nessas frases."""
    ordem = "AKQJT98765432"
    return quem_ganha_do_heroi(hero, [r * 2 for r in ordem], board)


# ---------------------------------------------------------------------------
# GUARDA DO BOARD — a carta citada no placar é a carta que veio na mesa?
#
# Caso real de 16/08, mão f2cd6504-9faa-48d5-87f7-1adfa6770ad2, board 9h Jd
# 2h: a linha do placar saiu "*Flop* 9♥J♦2♦". O 2♦ inventa um flush draw que
# não existia, e a análise inteira se apoiou nele ("c-bet com K high + flush
# draw", "o turn 5♦ que completa seu flush draw"). Numa segunda passagem saiu
# "2♠" — poker idêntico, board diferente do replay que o aluno vai abrir.
#
# Nenhum guarda pegava isso: `conferir_dominancia` cuida de "só perde para
# X", `corrigir_showdown` cuida das cartas do showdown, `conferir_analise`
# confere NÚMEROS contra lastro — e naipe não é número.
#
# ONDE ELE CORRIGE, E POR QUE SÓ ALI. Corrigir carta em prosa livre é
# perigoso: o coach legitimamente escreve hipótese ("se viesse o 2♦ você
# fechava") e trocar a carta ali estragaria a frase — o pecado que METODO.md
# nomeia (guarda que reescreve texto certo é pior que guarda ausente). Então
# a correção mora dentro da CITAÇÃO da linha do placar do R2 (o trecho entre
# o rótulo da street e o travessão), que é onde mora o fato de board e onde o
# erro real aconteceu. Fora dali: evento, nunca correção.
#
# E só corrige quando é INEQUÍVOCO: a carta citada não é carta de verdade
# desta mão, tem rank que existe no board daquela street e esse rank aparece
# UMA única vez. Rank repetido ou ausente é chute — vira evento.

_ICONE_DO_NAIPE = {"♠": "s", "♥": "h", "♦": "d", "♣": "c"}
_NAIPE_DO_ICONE = {v: k for k, v in _ICONE_DO_NAIPE.items()}

# "9♥", "10♦", "K♠" — o formato que `pretty_card` produz e que o coach copia
_CARTA_CITADA = re.compile(r"(10|[AKQJT98765432])([♠♥♦♣])")

# a linha do placar do R2: selo + *Street* + citação + travessão + porquê
_ROTULO_DA_STREET = re.compile(r"\*\s*(Pr[éeÉE]|Flop|Turn|River)\s*\*", re.I)
_STREET_DO_ROTULO = {"pre": "preflop", "pré": "preflop", "flop": "flop",
                     "turn": "turn", "river": "river"}
# fim da CITAÇÃO e começo do porquê. O travessão é o separador do R2; os
# outros entram porque o modelo às vezes troca de sinal, nunca de estrutura.
_FIM_DA_CITACAO = re.compile(r"[—–:]|\s-\s")


def _carta_do_texto(m: re.Match) -> str:
    """'10♦' -> 'Td' — a notação canônica da carta citada."""
    rank = "T" if m.group(1) == "10" else m.group(1).upper()
    return rank + _ICONE_DO_NAIPE[m.group(2)]


def _bonita(carta: str) -> str:
    rank = "10" if carta[0].upper() == "T" else carta[0].upper()
    return rank + _NAIPE_DO_ICONE.get(carta[1].lower(), carta[1])


def conferir_board(texto: str, hand) -> tuple[str, list[dict]]:
    """Confere as cartas do board citadas no texto contra o board real.

    Devolve (texto, achados). Cada achado traz `citada`, `onde`
    ('placar'/'prosa'), `street`, `motivo` e `corrigido_para` — None quando o
    guarda só mediu. Quem chama grava os eventos `board_corrigido` e
    `board_nao_conferido` (a taxa dos dois é o que diz se o contexto novo
    resolveu o erro de 16/08).
    """
    if not texto or hand is None:
        return texto, []
    from app.agent.analyzer import board_por_street

    por_street = board_por_street(hand)
    if not por_street:
        return texto, []

    # cartas de VERDADE desta mão: board inteiro, mão do herói e o que foi
    # mostrado. Citar qualquer uma delas nunca é erro provável — e esta é a
    # trava que impede o pior falso positivo possível: a linha do placar que
    # cita a mão do aluno ("*Flop* K♥J♦2♥ com K♦ na mão") teria o K♦ dele
    # trocado pelo K♥ do board.
    reais = {c for c in (getattr(hand, "final_board", None) or [])}
    reais |= {c for c in (getattr(hand, "hero_cards", None) or [])}
    for cs in (getattr(hand, "shown_cards", None) or {}).values():
        reais |= set(cs or [])
    ranks_reais = {c[0].upper() for c in reais}

    achados: list[dict] = []

    def _medir(trecho: str, street: str | None) -> None:
        """Fora da citação do placar o guarda NÃO toca — só conta."""
        for m in _CARTA_CITADA.finditer(trecho):
            carta = _carta_do_texto(m)
            if carta in reais or carta[0].upper() not in ranks_reais:
                continue      # carta da mão, ou rank que o board nem tem
            achados.append({"citada": m.group(0), "onde": "prosa",
                            "street": street, "corrigido_para": None,
                            "motivo": "fora_da_linha_do_placar",
                            "trecho": trecho.strip()[:120]})

    def _conferir_citacao(trecho: str, board: list[str], street: str) -> str:
        saida, pos = [], 0
        for m in _CARTA_CITADA.finditer(trecho):
            carta = _carta_do_texto(m)
            if carta in board or carta in reais:
                continue
            iguais = [c for c in board if c[0].upper() == carta[0].upper()]
            if len(iguais) != 1:
                if carta[0].upper() in ranks_reais:
                    achados.append({
                        "citada": m.group(0), "onde": "placar",
                        "street": street, "corrigido_para": None,
                        "motivo": ("rank_repetido_no_board" if iguais
                                   else "rank_ausente_do_board"),
                        "trecho": trecho.strip()[:120]})
                continue
            certa = _bonita(iguais[0])
            achados.append({"citada": m.group(0), "onde": "placar",
                            "street": street, "corrigido_para": certa,
                            "motivo": "naipe_errado",
                            "trecho": trecho.strip()[:120]})
            saida.append(trecho[pos:m.start()])
            saida.append(certa)
            pos = m.end()
        saida.append(trecho[pos:])
        return "".join(saida)

    linhas = (texto or "").split("\n")
    for i, linha in enumerate(linhas):
        rotulo = _ROTULO_DA_STREET.search(linha)
        if not rotulo:
            _medir(linha, None)
            continue
        street = _STREET_DO_ROTULO[rotulo.group(1).lower()]
        board = por_street.get(street, [])   # *Pré* não tem board: fica vazio
        resto = linha[rotulo.end():]
        corte = _FIM_DA_CITACAO.search(resto)
        citacao = resto[:corte.start()] if corte else resto
        porque = resto[len(citacao):]
        _medir(porque, street)
        linhas[i] = (linha[:rotulo.end()]
                     + _conferir_citacao(citacao, board, street) + porque)

    return "\n".join(linhas), achados


def conferir_board_e_registrar(texto: str, hand, repo, telegram_id: int,
                               username: str | None = None) -> str:
    """`conferir_board` + os dois eventos, para o pipeline chamar em uma linha.

    O encanamento do evento mora AQUI, não em `processing.py`: aquele arquivo
    tem teto de tamanho medido (test_processing_nao_incha) justamente porque
    cresce um parágrafo por vez, e separar corrigidos de medidos é assunto
    deste guarda, não do pipeline.

    `board_corrigido` conta o que foi consertado; `board_nao_conferido` conta
    o que o guarda VIU e decidiu não tocar (hipótese em prosa, rank repetido,
    carta que não está no board da street). A razão entre os dois é a medida
    de se o contexto novo (`board_por_street`) resolveu o erro de 16/08.
    """
    texto, achados = conferir_board(texto, hand)
    if not achados or not getattr(repo, "enabled", False):
        return texto
    board = list(getattr(hand, "final_board", None) or [])
    for evento, lote in (
            ("board_corrigido", [a for a in achados if a["corrigido_para"]]),
            ("board_nao_conferido",
             [a for a in achados if not a["corrigido_para"]])):
        if lote:
            repo.log_event(telegram_id, username, evento,
                           {"achados": lote[:4], "board": board})
    return texto
