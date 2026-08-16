"""GUARDA DA VOZ — a análise soa como conversa ou como formulário?

Por que existe: medido sobre a população certa (spec §9 — só análise de mão
real com selo, sem follow-up e sem torneio), o bloco depois do placar é 67%
do texto (678 chars em média, n=116), e boa parte dele repete o que o placar
já disse. O título "A conta que mais pesa" aparece em 48% (102 de 212) — e a
origem era NOSSA, escrita na instrução do coach em llm.py. A narração de
bastidor ("deixa eu conferir o EV...") sobrevive em 34% (73 de 212).

(Os números antigos deste cabeçalho — 58% / 740 / 25% / 23% — saíram de um
denominador contaminado, que engolia follow-up e torneio. A própria branch
os refez e publicou o erro: spec §9.)

Regra é pedido; conferência é garantia. O R3/R7 do prompt pedem; isto mede
e, onde é seguro, conserta.

O que CORRIGE e o que só MEDE, e o porquê de cada escolha:
  corrige  título fixo         rótulo sai sem tocar na frase (Task 2)
  corrige  narração de busca   frase inteira — MENOS quando ela leva número
  mede     bloco pós-placar    cortar prosa de LLM na marra estraga
  mede     autocorreção        3 casos em 212; conserto arrisca mais que resolve

O que NÃO é defeito, apesar de parecer:
  - "anotei no caderno" (32 análises). É voz de coach e é a regra A2
    funcionando. A primeira versão da spec mandava apagar — teria removido a
    frase mais humana da resposta.
  - número do placar repetido na prosa (`numeros_repetidos`). Continua
    medível como contador SECUNDÁRIO (spec §4/§5), mas saiu de
    `problemas_de_voz` na onda final: o R5b agora MANDA o parágrafo do
    desfecho trazer as % de cada street, que são exatamente as equities do
    placar. Executado numa análise conforme, ele devolvia
    ['número do placar repetido na prosa: 12%, 30%'] — ou seja, gravava um
    evento `voz_medida` em quase toda análise CERTA e fazia
    `com_numero_repetido` subir por causa da melhoria.
"""
from __future__ import annotations

import re

# medido: média de 678 chars depois do placar (n=116); com este teto, 14% das
# análises são marcadas — a cauda, sem acusar o caso comum. A calibragem
# nasceu da média inflada de 740 (spec §9): recalibrar espera a leitura lado
# a lado, não um palpite novo.
TETO_POS_PLACAR = 800

_SELOS = ("✅", "🟡", "❌")

# TÍTULO FIXO — os TRÊS rótulos que o R3 proíbe (llm.py, "PROIBIDO título
# fixo"). O guarda conhecia só o primeiro, e a revisão final mostrou a saída
# livre: o modelo obedece à proibição mais específica (a que tem nome
# próprio), troca para "Resumo:" e TODOS os contadores dizem sucesso com o
# formulário intacto sob cabeçalho novo.
#
# 'a conta que mais pesa' casa em qualquer posição: a frase é longa e
# específica o bastante. 'resumo' e 'o que treinar' são português comum
# ("em resumo, o que treinar aqui é..."), então só contam como TÍTULO quando
# abrem a linha — que é o que um rótulo de seção faz.
_TITULO_FIXO = re.compile(
    r"\*{0,2}\s*a\s+conta\s+que\s+mais\s+pesa\s*\*{0,2}\s*:\s*\*{0,2}\s*"
    r"|^[ \t]*\*{0,2}\s*(?:resumo|o\s+que\s+treinar)\b\s*\*{0,2}\s*:"
    r"\s*\*{0,2}\s*",
    re.I | re.M)

# bastidor de BUSCA — 91/403. NÃO inclui "anotei no caderno", que é voz de
# coach: o guarda que apaga isso piora exatamente o que viemos melhorar.
_NARRACAO = re.compile(
    r"\b(deixa\s+eu\s+(conferir|ver|puxar|checar|rodar|calcular)|"
    r"vou\s+(conferir|puxar|checar|rodar|calcular)|"
    r"me\s+deixa\s+(ver|conferir))\b", re.I)

_AUTOCORRECAO = re.compile(r"\.{2,3}\s*digo\b", re.I)

# números que contam: 12bb, 34%, +1.49bb, -0,6bb
_NUMERO = re.compile(r"[-+]?\d+[.,]?\d*\s*(?:bb|%)")


def bloco_pos_placar(texto: str) -> str:
    """Tudo que vem DEPOIS da última linha de placar.

    É o sinal principal. A primeira versão media 'número repetido', que dá
    para contar por regex mas mira o sintoma: repetir o +1.49bb no fecho é
    ênfase legítima. O defeito é o parágrafo INTEIRO não acrescentar nada,
    e o proxy medível disso é o comprimento.
    """
    linhas = (texto or "").split("\n")
    ultimo = -1
    for i, ln in enumerate(linhas):
        if ln.lstrip().startswith(_SELOS):
            ultimo = i
    if ultimo < 0:
        return ""
    return "\n".join(linhas[ultimo + 1:]).strip()


def numeros_repetidos(texto: str) -> list[str]:
    """Números que aparecem no placar E de novo na prosa do fechamento.

    CONTADOR SECUNDÁRIO, nunca gatilho (spec §4/§5). Não entra em
    `problemas_de_voz` de propósito: desde o R3+R5b, a história do desfecho
    ("você estava atrás desde o pré: 30% no flop, 12% no river") é
    OBRIGATÓRIA, e ela repete as equities do placar por definição. Enquanto
    isto era um "defeito", uma análise conforme gravava evento de voz e
    inflava `com_numero_repetido` — o contador subia como efeito direto da
    melhoria que a branch existe para provar.
    """
    linhas = (texto or "").split("\n")
    do_placar = {m.group(0).replace(" ", "")
                 for ln in linhas if ln.lstrip().startswith(_SELOS)
                 for m in _NUMERO.finditer(ln)}
    na_prosa = {m.group(0).replace(" ", "")
                for m in _NUMERO.finditer(bloco_pos_placar(texto))}
    return sorted(do_placar & na_prosa)


def problemas_de_voz(texto: str) -> list[str]:
    """Defeitos de VOZ numa resposta do coach (lista vazia = passou).

    Função pura — é o contrato que o R3/R7 do prompt promete ao aluno.
    """
    t = (texto or "").strip()
    if not t:
        return []
    probs: list[str] = []

    bloco = bloco_pos_placar(t)
    if len(bloco) > TETO_POS_PLACAR:
        probs.append(f"bloco pós-placar longo ({len(bloco)} chars; "
                     f"teto {TETO_POS_PLACAR})")
    achado = _TITULO_FIXO.search(t)
    if achado:
        # nomeia o rótulo ENCONTRADO, não o primeiro da lista: com três
        # rótulos vigiados, "título fixo 'A conta que mais pesa'" fixo faria
        # o evento mentir sobre qual formulário o modelo usou.
        rotulo = achado.group(0).strip().strip("*").strip()
        probs.append(f"título fixo {rotulo!r}")
    if _NARRACAO.search(t):
        probs.append("bastidor de busca narrado ao aluno")
    if _AUTOCORRECAO.search(t):
        probs.append("autocorreção dentro do texto entregue")
    # `numeros_repetidos` NÃO entra aqui — ver a docstring dela: o R5b manda
    # repetir as % de cada street no parágrafo do desfecho.
    return probs


# palavras que, logo depois do rótulo, denunciam que a frase DEPENDIA dele:
# tirar o rótulo deixaria um fragmento sem sujeito.
_FRAGMENTO = re.compile(r"^(que|porque|por\s+que|e|mas|ou|então|pois|se)\b",
                        re.I)


def _sem_titulo_fixo(texto: str) -> tuple[str, bool]:
    """Tira o rótulo e promove a frase a início de parágrafo.

    Só quando ela sobrevive sozinha: 'A conta que mais pesa: que você paga
    sempre' vira fragmento se o rótulo sair, e frase partida é o defeito que
    test_corretor_nao_estraga_portugues existe para impedir.

    Corta no início REAL do rótulo, não em m.start(): sem negrito, o trecho
    de espaço em branco opcional no começo de _TITULO_FIXO também casa a
    quebra de linha ANTES dele ('...fácil' + duas quebras + 'A conta...'
    vira o match inteiro, quebras incluídas). Cortar em m.start() comia
    essas quebras sem reemitir e colava o parágrafo anterior no texto
    promovido ('...fácilCom 12bb...') — Critical 1 da revisão de qualidade,
    que também zerava bloco_pos_placar ao juntar a linha de placar com a
    prosa seguinte. 'inicio' avança m.start() pelo tamanho do espaço em
    branco líder do match, preservando-o.

    O trecho de espaço em branco no FIM de _TITULO_FIXO é guloso e não tem
    nada depois dele no padrão: o que sobra em texto[m.end():] nunca começa
    com espaço (medido com espaço múltiplo, quebra dupla e quebra simples
    após o rótulo — sempre 0 nos três). Por isso não existe salto a
    preservar DEPOIS do rótulo, só ANTES.
    """
    saida: list[str] = []
    pos = 0
    mexeu = False
    for m in _TITULO_FIXO.finditer(texto):
        grupo = m.group(0)
        inicio = m.start() + (len(grupo) - len(grupo.lstrip()))
        cabeca = texto[m.end():].lstrip()
        if not cabeca or _FRAGMENTO.match(cabeca):
            continue
        saida.append(texto[pos:inicio])
        saida.append(cabeca[0].upper())
        pos = m.end() + 1
        mexeu = True
    saida.append(texto[pos:])
    return "".join(saida), mexeu


# fronteira real de frase: um "." só separa quando NÃO é ponto decimal.
# Medido: bb/% sempre aparecem com decimal de ponto (12.9bb, +1.49bb) — o
# separador ingênuo ([^.!?]+[.!?]*) tratava TODO ponto como fim de frase e
# cortava exatamente no meio do número, vazando o pedaço mutilado ('49bb')
# para o aluno. Critical 2 da revisão: é a classe de defeito que
# _conferir_numeros em llm.py existe para impedir, só que aqui do lado da
# limpeza de voz em vez do lado da IA.
_FRASE = re.compile(r"(?:[^.!?]|\.(?=\d))+[.!?]*")


def _sem_narracao(texto: str) -> tuple[str, bool]:
    """Remove a FRASE inteira de bastidor — menos quando ela leva um NÚMERO.

    Cortar só 'deixa eu conferir' deixaria 'o EV desse shove.' solto, que é
    pior do que a frase original. O separador de frases é _FRASE, não um
    split ingênuo por ponto: ponto decimal (12.9bb) não é fim de frase.

    A EXCEÇÃO DO NÚMERO é a correção mais importante da revisão final, e é o
    pecado capital deste repositório (METODO.md): um guarda que existe para
    MELHORAR a saída não pode apagar a conta que decide o spot. Executado
    contra o código antigo:

        '✅ Você jogou bem\\n\\nVou calcular: pedia 30%, tinha 12% → −11bb.
         Portanto foi call caro.'
      -> '✅ Você jogou bem\\n\\nPortanto foi call caro.'

    O aluno recebia um veredito com ZERO número — a forma exata que
    `guarda_fatos.conta_sem_numero` existe para detectar. E os dois
    detectores de "veredito/resposta sem número" rodam ANTES daqui nos dois
    caminhos (processing.py:532 antes de :577 na análise; :1217 antes de
    :1229 na conversa), sobre o texto que AINDA tinha o número: o defeito
    nascia depois do detector e ninguém o via. Na conversa era pior — o aluno
    pergunta "qual era o EV daquele shove?", o `guarda_saida` acha o número e
    dá entrega_ok, e a limpeza apagava a frase logo depois.

    Frase de bastidor COM número passa a ser só MEDIDA: `problemas_de_voz`
    continua apontando "bastidor de busca narrado ao aluno", o evento é
    gravado e o dono vê a taxa. Prosa feia é menos pior que conta apagada.

    De brinde isto fecha o caso da frase FUNDIDA por falta de espaço depois
    do ponto ('Vou conferir o EV.12bb é jam, e o range aperta.'): para _FRASE
    o '.' seguido de dígito é decimal, então a corrida inteira é UMA frase —
    e ela tem número, então fica. Antes, o aluno recebia só o selo.
    """
    mexeu = False
    saidas: list[str] = []
    for paragrafo in texto.split("\n"):
        frases = _FRASE.findall(paragrafo)
        mantidas = [f for f in frases
                    if not _NARRACAO.search(f) or _NUMERO.search(f)]
        if len(mantidas) != len(frases):
            mexeu = True
            paragrafo = "".join(mantidas).strip()
        saidas.append(paragrafo)
    novo = "\n".join(saidas)
    if mexeu:
        # um parágrafo que era só bastidor vira "" e soma às quebras que já
        # separavam parágrafos ('...fácil\n\n\n\nCom 12bb...') — buraco
        # visível que a guarda de 'limpar' não pega, porque só olha o texto
        # INTEIRO vazio, não o parágrafo. Important 3 da revisão.
        novo = re.sub(r"\n{3,}", "\n\n", novo)
    return novo, mexeu


def limpar(texto: str) -> tuple[str, list[str]]:
    """Corrige o que é seguro corrigir. Devolve (texto, o que foi feito).

    Nunca degrada abaixo do que já ia sair: se a limpeza esvaziar o texto,
    a original volta. Mesma disciplina do _conferir_numeros em llm.py.
    """
    t = texto or ""
    if not t.strip():
        # devolve 't' (sempre str), não 'texto': se texto for None, devolver
        # None quebra a assinatura -> tuple[str, list[str]], e a Task 3 chama
        # 'answer, feitos = limpar(answer)' sem guarda de None antes.
        return t, []
    feitos: list[str] = []

    novo, mexeu = _sem_titulo_fixo(t)
    if mexeu:
        feitos.append("título fixo removido")
    novo, mexeu = _sem_narracao(novo)
    if mexeu:
        feitos.append("bastidor de busca removido")

    if not novo.strip():
        return texto, []
    return novo, feitos


def conferir_e_limpar(telegram_id: int, texto: str, *,
                      username: str | None = None,
                      onde: str | None = None) -> str:
    """Portão da voz: mede, corrige o que é seguro e registra o evento.

    Espelha guarda_saida.conferir_e_remediar (Rodada de correção 1, achado
    Important): antes, a análise e a conversa inlinhavam ~10 linhas cada uma
    chamando problemas_de_voz + limpar + repo.log_event direto em
    processing.py, empurrando o arquivo para o teto de 3600 linhas vigiado
    por test_processing_nao_incha.py — o teste existe para forçar extração,
    não para ser satisfeito raspando formatação. Aqui a lógica mora uma vez
    só: quem chama (análise ou conversa) vira uma linha.

    'texto' vazio/None não é medido — devolvido como veio, sem virar "" pelo
    contrato de limpar(None). 'onde' rotula o evento fora da análise (ex.:
    "conversa"); sem ele o payload fica igual ao que a análise já gravava.

    Não protege contra exceção de problemas_de_voz/limpar: essa proteção
    continua em processing.py, no try/except que envolve a chamada — uma
    exceção do guarda não pode derrubar a resposta ao aluno.
    """
    if not texto:
        return texto
    problemas = problemas_de_voz(texto)
    novo, feitos = limpar(texto)
    if not (feitos or problemas):
        return novo

    from app.db import get_repository

    repo = get_repository()
    detalhe = {"feitos": feitos, "problemas": problemas[:6]}
    if onde:
        detalhe["onde"] = onde
    try:
        repo.log_event(telegram_id, username,
                       "voz_corrigida" if feitos else "voz_medida", detalhe)
    except Exception:
        pass
    return novo
