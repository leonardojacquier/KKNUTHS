"""GUARDA DOS TERMOS — o coach traduziu termo do poker?

Caso real (16/08, análise entregue a um aluno, mão 2f227463):

    "...você estava na frente a mão inteira — 61% no pré, 60% no flop, 66%
     no turn — e foi o RIO que virou tudo"
    "apostar de novo bate contra a fatia de AR do range dele"

`river` virou "rio", `air` virou "ar". O dono, na íntegra: "se é termo do
poker não tem que traduzir" — e disse que já tinha reclamado antes. É essa
reincidência que este arquivo existe para acabar: regra é PEDIDO,
conferência é GARANTIA (docs/METODO.md). O Conserto 1 pôs `flop/turn/river/
air` na lista de FICAM EM INGLÊS da `TERMOS_REGRA` e `'rio'`/`'ar'` nos
CALQUES PROIBIDOS; isso é o pedido. Isto aqui confere o texto que sai.

MEDIDO ANTES DE ESCREVER, no corpus real (`hand_analysis`, 45 dias, só
análise de mão: `summary not like '[Follow-up]%'` e `mistakes not null`,
n=227):

  'rio' isolado ....... 1 análise (a do caso real). 'Rio de Janeiro': 0.
  'ar' isolado ........ 3 análises — e são elas que definem o desenho:
      "é um spot de moeda ao ar"                 PORTUGUÊS -> nem toca
      "o BB tem MUITO ar que não paga a Q"       poker, mas fora de
                                                 colocação -> só EVENTO
      "bate contra a fatia de ar do range dele"  colocação -> CORRIGE
  últimos 10 dias (n=29): 'rio' 1, 'ar' 2 — e ZERO de todos os outros
  calques que a TERMOS_REGRA proíbe ('sequência', 'carta alta', 'aumentou',
  'passou', 'check atrás', 'top par', 'rua'...). Eles já são pegos pelo
  corretor mecânico de `app/agent/termos.py`. `rio` e `ar` eram os dois
  únicos que ainda escapavam — e é só neles que este guarda mexe.

POR QUE 'AR' NÃO PODE SER CORRIGIDO COMO 'RIO':
  "rio", isolado e no meio de uma análise de poker, é praticamente sempre o
  river — a única armadilha real é o topônimo, e ela é fechada por lista.
  Já "ar" é palavra comum do português ("deixou no ar", "moeda ao ar", "ar
  livre", "com ar de deboche"), e uma dessas apareceu no corpus. Corrigir
  cego estragaria texto BOM, que custa mais confiança do que o calque. Por
  isso "ar" só é trocado dentro de colocação de poker inequívoca; fora
  delas o guarda REGISTRA e não escreve.

O QUE CORRIGE E O QUE SÓ MEDE:
  corrige  'rio' isolado                     -> river, na caixa do contexto
  corrige  'ar' em colocação de poker        -> air (fatia/range/mão de ar,
                                                puro ar, só ar, com ar)
  mede     'ar' de poker fora da colocação   -> evento `termo_ambiguo`
  ignora   'ar' de português assentado       -> nem toca, nem mede: contar
           ("no ar", "ao ar", "ar livre",       "moeda ao ar" como caso
            "com ar de ...")                    ambíguo sujaria a medição
                                                que o dono vai ler depois

ONDE ELE É CHAMADO: em `guarda_voz.conferir_e_limpar`, que já é o último
portão do texto entregue nos dois caminhos (análise e conversa). Terminologia
NÃO é voz, e por isso este módulo é separado, com evento e testes próprios;
o que é compartilhado é só o CALL SITE, porque `processing.py` está a uma
linha do teto de `test_processing_nao_incha` e um segundo portão custaria
oito. Encanamento mora no guarda, não no arquivo.
"""
from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

# 'rio' como palavra inteira. A borda inclui o HÍFEN de propósito: sem ele
# "meio-rio" (a guia da calçada) viraria "meio-river". Com `\w` unicode,
# "critério"/"próprio"/"sério" já não casam — a letra anterior é palavra.
_RIO = re.compile(r"(?<![\w-])(rio)(?![\w-])", re.I)

# ...menos quando é lugar. São os únicos "Rio" que um papo de poker BR
# produz de verdade, e trocá-los é o falso positivo mais visível que existe.
_RIO_LUGAR = re.compile(r"(?<![\w-])rio(?=\s+(?:de\s+janeiro|grande|branco|"
                        r"preto|negro|claro|verde|das\s+ostras)(?![\w-]))",
                        re.I)

# COLOCAÇÃO DE POKER INEQUÍVOCA. Cada uma dessas foi escolhida porque não
# existe em português fora da mesa: ninguém diz "a fatia de ar do range" nem
# "puro ar" falando de atmosfera.
_AR_POKER = re.compile(
    r"(?P<antes>"
    r"(?:fatias?|ranges?|m[ãa]os?|peda[çc]os?|parte)\s+de\s+"
    r"|puro\s+|s[óo]\s+|com\s+"
    r")(?P<ar>ar)(?![\w-])"
    # "com ar DE deboche", "ar LIVRE", "ar CONDICIONADO": a continuação
    # prova que é o ar que se respira. Fora isso a colocação fica de pé.
    r"(?!\s+(?:de|livre|condicionado|fresco|puro|quente|frio|pesado)"
    r"(?![\w-]))",
    re.I)

# 'ar' inteiro, para achar o que NÃO foi corrigido e precisa ser medido.
_AR = re.compile(r"(?<![\w-])(ar)(?![\w-])", re.I)

# PORTUGUÊS ASSENTADO — nem corrige nem conta. "é um spot de moeda ao ar"
# saiu numa análise real (31/07) e está CERTO; se ele virasse evento, a
# medição de 'ar' que o dono vai ler passaria a ter mais português do que
# poker dentro e não serviria para decidir nada.
#
# São dois testes por ocorrência: o artigo/preposição ANTES ("no ar", "ao
# ar", "o ar", "pelo ar") e a continuação DEPOIS ("ar livre", "ar de
# deboche").
_AR_PT_ANTES = re.compile(r"(?:\bn?[oa]s?|\baos?|\bpel[oa]s?)\s+$", re.I)
_AR_PT_DEPOIS = re.compile(r"^\s+(?:livre|condicionado|puro|fresco|de)"
                           r"(?![\w-])", re.I)


def _na_caixa(original: str, novo: str) -> str:
    """Devolve `novo` escrito na CAIXA de `original`.

    'Rio veio K♠' abre linha de placar; devolver 'river' minúsculo ali deixa
    a frase torta de um jeito que o aluno percebe — e o guarda que conserta
    o termo não pode criar um defeito de escrita no lugar.
    """
    if original.isupper() and len(original) > 1:
        return novo.upper()
    if original[:1].isupper():
        return novo[:1].upper() + novo[1:]
    return novo


def _trocar_rio(texto: str) -> tuple[str, list[str]]:
    """'e foi o rio que virou tudo' -> '...o river que virou tudo'."""
    trocas: list[str] = []

    def _sub(m: re.Match) -> str:
        if _RIO_LUGAR.match(texto, m.start()):
            return m.group(0)                     # Rio de Janeiro fica
        novo = _na_caixa(m.group(1), "river")
        trocas.append(f"{m.group(1)} -> {novo}")
        return novo

    return _RIO.sub(_sub, texto), trocas


def _trocar_ar(texto: str) -> tuple[str, list[str]]:
    """'a fatia de ar do range dele' -> '...a fatia de air do range dele'."""
    trocas: list[str] = []

    def _sub(m: re.Match) -> str:
        novo = _na_caixa(m.group("ar"), "air")
        trocas.append(f"{m.group('antes').strip()} {m.group('ar')} -> {novo}")
        return m.group("antes") + novo

    return _AR_POKER.sub(_sub, texto), trocas


def _ar_ambiguo(texto: str) -> list[str]:
    """Os 'ar' que sobraram: nem colocação de poker, nem português assentado.

    Real (14/08): "o BB tem MUITO ar que não paga a Q" — é air de poker, e
    mesmo assim não se corrige. Inventar uma regra nova só para caber esta
    frase é o caminho curto para estragar a próxima frase boa. Ela vira
    número, e o número decide se vale mexer.
    """
    achados: list[str] = []
    for m in _AR.finditer(texto):
        if _AR_PT_ANTES.search(texto[:m.start()]) \
                or _AR_PT_DEPOIS.match(texto[m.end():]):
            continue
        i = max(0, m.start() - 45)
        achados.append(texto[i:m.end() + 45].replace("\n", " ").strip())
    return achados


def conferir(texto: str) -> tuple[str, list[str], list[str]]:
    """Devolve (texto, trocas feitas, trechos ambíguos que só foram medidos).

    Nunca degrada abaixo do que já ia sair: mesma disciplina de
    `guarda_voz.limpar` — o guarda só troca termo, nunca reescreve prosa.
    """
    if not texto:
        return texto, [], []
    novo, trocas = _trocar_rio(texto)
    novo, trocas_ar = _trocar_ar(novo)
    return novo, trocas + trocas_ar, _ar_ambiguo(novo)


def conferir_e_registrar(telegram_id: int, texto: str, *,
                         username: str | None = None,
                         onde: str | None = None) -> str:
    """Portão da terminologia: corrige o inequívoco, registra o resto.

    Espelha `guarda_voz.conferir_e_limpar` — inclusive o rótulo `onde`, que
    carimba a POPULAÇÃO do evento na origem. Sem ele o juiz soma conversa,
    torneio e análise no mesmo numerador e divide por um denominador que só
    conta análise de mão; foi assim que a taxa 🗣 chegou a dar 225%.

    Uma exceção daqui não pode derrubar a resposta ao aluno: quem chama
    (`guarda_voz`) envolve a chamada em try/except, e o texto original segue.
    """
    if not texto:
        return texto
    novo, trocas, ambiguos = conferir(texto)
    if not (trocas or ambiguos):
        return novo

    from app.db import get_repository

    repo = get_repository()
    detalhe = {"trocas": trocas[:8], "ambiguos": [a[:160] for a in ambiguos[:4]],
               "onde": onde or "analise"}
    if trocas:
        log.info("termo de poker traduzido corrigido na entrega: %s", trocas)
    try:
        if getattr(repo, "enabled", False):
            repo.log_event(telegram_id, username,
                           "termo_corrigido" if trocas else "termo_ambiguo",
                           detalhe)
    except Exception:
        pass
    return novo
