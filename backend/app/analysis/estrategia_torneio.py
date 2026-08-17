"""ESTRATÉGIA DE TORNEIO — onde o EV foi perdido, por profundidade de stack.

A pergunta do dono era "etapa inicial mais tight ou mais agressivo?". A
resposta honesta começa por rejeitar a pergunta: "etapa" mistura duas
variáveis ortogonais.

  - a PROFUNDIDADE do stack determina a árvore de decisão
  - a PROFUNDIDADE do torneio determina pressão de ICM

Um jogador com 18bb no nível 3 e um com 18bb no nível 14 jogam a MESMA
estratégia de fichas e estratégias de RISCO diferentes. Segmentar por um
eixo só produz conselho errado para metade dos casos.

E a premissa "early mais tight" é de 2004, de uma era sem ante nos níveis
iniciais. Com ante, os ranges de open no early são os de cash 100bb, e o ICM
no early é ≈1 — é o momento de MÁXIMA liberdade para acumular. A variável
que de fato aperta os ranges é `ante == 0`, que é dado exato na mão. Por
isso o corte aqui é por ANTE, não por "etapa": um é medido, o outro é
palpite com nome de estratégia.

O QUE ESTE MÓDULO AFIRMA E O QUE NÃO AFIRMA:

  afirma  — EV perdido por faixa de stack, contagem de erro e DIREÇÃO do
            erro. Vale com n=1, porque cada spot auditável tem resposta
            certa: "nesses 6 spots de 15-25bb você deixou 5,3bb na mesa,
            todos na mesma direção" é demonstrável.
  não     — frequência por faixa com amostra curta. "Você joga X% das mãos
            nesta faixa" precisa de n>=60 NA FAIXA, e a mão de torneio não é
            i.i.d.: quem quebra cedo só contribui com mãos de stack fundo,
            então o n por faixa é sempre desequilibrado e tem que aparecer.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.canonical import CanonicalHand

# EIXO PRIMÁRIO: stack efetivo. Erro zero (sai da mão) e explica a maior
# parte da variação de estratégia correta. As fronteiras são onde a ÁRVORE
# muda, não números redondos por estética.
FAIXAS: tuple[tuple[str, float, float, str], ...] = (
    ("deep", 40.0, 1e9, "jogo de 3 streets; implied odds contam"),
    ("padrão", 25.0, 40.0, "3-bet ainda cabe sem comprometer o stack"),
    ("re-shove", 15.0, 25.0,
     "o re-shove domina e o 3-bet não-all-in some — a faixa que ninguém "
     "estuda"),
    ("curto", 8.0, 15.0, "push/fold, com limp-shove e iso-shove"),
    ("crítico", 0.0, 8.0, "push/fold puro"),
)

# n mínimo para FREQUÊNCIA dentro de uma faixa. Abaixo disso sai contagem
# absoluta — "você abriu 3 vezes nesta faixa" é fato; "RFI 33%" é ficção.
MINIMO_PARA_TAXA_NA_FAIXA = 60


def faixa_de(stack_bb: float | None) -> str | None:
    if not stack_bb or stack_bb <= 0:
        return None
    for nome, lo, hi, _ in FAIXAS:
        if lo < stack_bb <= hi:
            return nome
    return None


# DIREÇÃO do erro: dois códigos da mesma faixa podem apontar para lados
# opostos, e a direção é o que vira conselho. "Você errou 6 vezes" não diz o
# que fazer; "as 6 foram para o mesmo lado — passivo demais" diz.
_DIRECAO = {
    "shove_perdido": "passivo",
    "open_perdido": "passivo",
    "bb_subdefesa": "passivo",
    "limp_de_abertura": "passivo",
    "shove_largo": "solto",
    "call_caro": "solto",
}


def _proporcoes_diferem(erros_a: int, n_a: int, erros_b: int, n_b: int,
                        alfa: float = 0.05) -> bool:
    """Teste de duas proporções — A erra MAIS que B, com margem?

    Existe porque a versão anterior comparava contagens brutas. Com 40
    chances de um lado e 5 do outro, a mesma taxa real de erro produzia
    "passivo demais" em 99,5% das simulações: quem tem mais oportunidades
    acumula mais erros mesmo jogando igual.

    Aproximação normal com variância agrupada. Não vale trazer scipy para
    isto, e a aproximação é adequada porque o portão de 5 chances por lado já
    barra os casos em que ela quebraria.
    """
    import math

    if n_a < 5 or n_b < 5:
        return False
    p_a, p_b = erros_a / n_a, erros_b / n_b
    p = (erros_a + erros_b) / (n_a + n_b)
    if p <= 0.0 or p >= 1.0:
        return False
    se = math.sqrt(p * (1 - p) * (1 / n_a + 1 / n_b))
    if se <= 0:
        return False
    z = (p_a - p_b) / se
    # BILATERAL (1,96), embora a pergunta pareça dirigida. O lado testado é
    # escolhido OLHANDO O DADO (`max(self.direcao)`), e escolher o maior dos
    # dois e depois testar num rabo só é o mesmo viés de "procurar o extremo"
    # que a correção de comparações múltiplas trata em problemas.py.
    # Medido: com denominadores iguais, o limiar unilateral dava 10,4% de
    # falsa direção sob H0 — o dobro do nominal. Com 1,96 volta a ~5%.
    return z > 1.96 if alfa == 0.05 else z > 2.576


@dataclass
class LinhaDaFaixa:
    faixa: str
    o_que_muda: str
    maos: int
    spots: int
    erros: int
    ev_perdido_bb: float
    por_codigo: dict
    direcao: dict            # erros de cada lado
    chances: dict            # OPORTUNIDADES de cada lado

    @property
    def direcao_confiavel(self) -> str | None:
        """O lado dominante — só quando o OUTRO lado teve chance real de
        aparecer. Sem isto a conclusão é artefato do detector: hoje são 4
        detectores de passividade contra 2 de soltura, então "todos os erros
        foram passivos" pode significar apenas "eu só sei procurar isso".

        Uma ferramenta que sempre acha passividade empurra todo aluno para a
        agressão, e aí ela mesma cria o leak que vai diagnosticar depois.

        E COMPARAR CONTAGENS NÃO SERVE. `direcao[lado] > direcao[outro]` com
        denominadores diferentes é decidido pelo desequilíbrio, não pelo
        jogo: simulado em 09/08 com os DOIS lados na MESMA taxa real de erro,
        40 chances de um lado contra 5 do outro, o veredito saía "passivo
        demais" em 99,5% das vezes. O portão de 5 chances não corrigia nada —
        ele liberava a comparação e a comparação já estava viciada.

        Agora compara TAXAS, e só afirma quando a diferença sobrevive a um
        teste de duas proporções. O poder é baixo com amostra de clube (para
        separar 35% de 20% seriam ~200 spots por lado), e isso é a resposta
        certa: na maioria das faixas o veredito honesto é "não sei de que
        lado", não um palpite com cara de diagnóstico.
        """
        if not self.erros:
            return None
        lado = max(self.direcao, key=lambda k: self.direcao[k])
        outro = "solto" if lado == "passivo" else "passivo"
        n_a = self.chances.get(lado, 0)
        n_b = self.chances.get(outro, 0)
        if self.direcao[lado] < 2 or n_a < 5 or n_b < 5:
            return None            # o outro lado mal teve como aparecer
        p_a = self.direcao[lado] / n_a
        p_b = self.direcao.get(outro, 0) / n_b
        if p_a <= p_b:
            return None
        return lado if _proporcoes_diferem(
            self.direcao[lado], n_a, self.direcao.get(outro, 0), n_b) else None


def _stack_bb(h: CanonicalHand) -> float | None:
    try:
        bb = float(h.stakes.big_blind or 0)
        seat = h.hero_seat()
        if not bb or not seat or not seat.stack:
            return None
        return float(seat.stack) / bb
    except Exception:
        return None


def por_faixa(hands: list[CanonicalHand]) -> list[LinhaDaFaixa]:
    """Onde o EV foi perdido, por profundidade de stack.

    A leitura de topo do relatório. Não depende de saber quantos jogadores
    restam nem da premiação — dados que os apps de clube não trazem e que
    todo mundo que vende "análise de bolha" finge ter.
    """
    from app.analysis.taxonomia import observar

    maos_por_faixa: dict[str, int] = {}
    for h in hands:
        f = faixa_de(_stack_bb(h))
        if f:
            maos_por_faixa[f] = maos_por_faixa.get(f, 0) + 1

    obs_por_faixa: dict[str, list] = {}
    for o in observar(hands):
        f = faixa_de(o.stack_bb)
        if f:
            obs_por_faixa.setdefault(f, []).append(o)

    saida = []
    for nome, _lo, _hi, muda in FAIXAS:
        obs = obs_por_faixa.get(nome, [])
        n_maos = maos_por_faixa.get(nome, 0)
        if not n_maos and not obs:
            continue
        por_codigo: dict[str, dict] = {}
        direcao = {"passivo": 0, "solto": 0}
        chances = {"passivo": 0, "solto": 0}
        # DIREÇÃO CONTA DECISÃO, NÃO CÓDIGO. Um limp de 72o dispara
        # `limp_de_abertura` (passivo) E `call_caro` (solto): contar os dois
        # é a MESMA ficha alimentando os dois lados do veredito. Pior, uma
        # decisão não pode ser prova de passividade e de soltura ao mesmo
        # tempo — quando os códigos daquela decisão apontam para lados
        # opostos, a resposta honesta é não contar nenhum.
        por_decisao: dict[tuple, dict] = {}
        for o in obs:
            c = por_codigo.setdefault(o.codigo, {"spots": 0, "erros": 0,
                                                 "ev": 0.0})
            c["spots"] += 1
            if o.escorregada:
                c["erros"] += 1
                c["ev"] += o.custo_bb
            d = _DIRECAO.get(o.codigo)
            if not d:
                continue
            k = (o.hand_id, o.street)
            reg = por_decisao.setdefault(k, {"lados": set(), "erros": set()})
            reg["lados"].add(d)
            if o.escorregada:
                reg["erros"].add(d)

        for reg in por_decisao.values():
            if len(reg["lados"]) == 1:
                chances[next(iter(reg["lados"]))] += 1
            if len(reg["erros"]) == 1:
                direcao[next(iter(reg["erros"]))] += 1
        for c in por_codigo.values():
            c["ev"] = round(c["ev"], 2)
        # UMA DECISÃO, UM CUSTO. Os códigos não são mutuamente exclusivos: um
        # limp com 72o é `limp_de_abertura` E `call_caro`, porque é a mesma
        # ficha entrando no pote pelo mesmo motivo. Somar os dois inflaria o
        # "EV perdido", que é justamente o número que o aluno vai citar. O
        # detalhe por código continua inteiro — quem infla é só o TOTAL.
        pior_por_decisao: dict[tuple, float] = {}
        for o in obs:
            if not o.escorregada:
                continue
            chave = (o.hand_id, o.street)
            pior_por_decisao[chave] = max(pior_por_decisao.get(chave, 0.0),
                                          o.custo_bb)
        saida.append(LinhaDaFaixa(
            faixa=nome, o_que_muda=muda, maos=n_maos, spots=len(obs),
            erros=len(pior_por_decisao),
            ev_perdido_bb=round(sum(pior_por_decisao.values()), 2),
            por_codigo=por_codigo, direcao=direcao, chances=chances))
    return saida


def onde_doi_mais(linhas: list[LinhaDaFaixa]) -> LinhaDaFaixa | None:
    """A faixa que mais custou. É a resposta com NÚMERO para a pergunta que
    o dono fez com palavras ('early mais tight ou mais agressivo?')."""
    com_erro = [l for l in linhas if l.ev_perdido_bb > 0]
    return max(com_erro, key=lambda l: l.ev_perdido_bb) if com_erro else None


def corte_por_ante(hands: list[CanonicalHand]) -> dict:
    """Níveis SEM ante vs COM ante — o corte que substitui 'etapa inicial'.

    É dado exato (`stakes.ante`), ao contrário de nível de blind, que os
    apps de clube não numeram. Devolve `aplicavel=False` quando a amostra só
    tem um dos lados: comparar um grupo com nada é o tipo de tabela que
    parece análise e não é.
    """
    grupos = {"sem_ante": [], "com_ante": []}
    for h in hands:
        try:
            ante = float(h.stakes.ante or 0)
        except Exception:
            continue
        grupos["com_ante" if ante > 0 else "sem_ante"].append(h)
    if not grupos["sem_ante"] or not grupos["com_ante"]:
        lado = "com ante" if grupos["com_ante"] else "sem ante"
        return {"aplicavel": False,
                "por_que": (f"toda a amostra é de níveis {lado} — não há com "
                            "o que comparar"),
                "maos": {k: len(v) for k, v in grupos.items()}}
    return {"aplicavel": True,
            "maos": {k: len(v) for k, v in grupos.items()},
            "faixas": {k: por_faixa(v) for k, v in grupos.items()}}


# ---------------------------------------------------------------------------
# ETAPA DO TORNEIO — a variável que faltava, e ela É medida.
#
# O corte por ante (`corte_por_ante`) responde "os ranges de abertura apertam?"
# e é dado exato — mas nas 517 mãos de fonte completa do banco NENHUMA é sem
# ante, então ele nunca teve com o que comparar. Um eixo que não separa a
# amostra não responde pergunta nenhuma.
#
# O STACK MÉDIO DA MESA, em big blinds, separa: as blinds sobem mais rápido do
# que as fichas se concentram, então a mesa vai afundando ao longo do torneio.
# Medido no banco em 09/08: Leo tem 167 mãos com mesa acima de 40bb e 61
# abaixo de 20bb; Odilon tem 15 e 66. Há os dois lados.
#
# E o eixo é ORTOGONAL à profundidade do herói, que é a premissa do módulo
# inteiro: o stack DELE determina a árvore de decisão, a etapa do TORNEIO
# determina a pressão de ICM. Um jogador com 18bb numa mesa de 60bb de média
# está numa situação diferente de um com 18bb numa mesa de 15bb — no primeiro
# caso ele é o curto, no segundo é todo mundo.
ETAPAS: tuple[tuple[str, float, float], ...] = (
    ("inicial", 40.0, 1e9),
    ("média", 20.0, 40.0),
    ("final", 0.0, 20.0),
)

# n por CÉLULA (faixa × etapa) para a comparação valer. 30 e não 60 porque
# aqui a pergunta é comparativa (mudou entre as etapas?) e não absoluta
# (qual é a taxa?) — e o teste de duas proporções já cobra a separação.
MIN_POR_CELULA = 30
# n para AFIRMAR uma frequência ("você joga X% das mãos nesta faixa"). Bem
# maior, porque é afirmação sobre um número e não sobre uma diferença.
MIN_PARA_FREQUENCIA = 60


def _media_da_mesa_bb(h: CanonicalHand) -> float | None:
    """Stack médio da mesa em bb — o relógio do torneio que o dado tem."""
    try:
        bb = float(h.stakes.big_blind or 0)
        if not bb or not h.players:
            return None
        stacks = [float(p.stack) for p in h.players if p.stack]
        if not stacks:
            return None
        return (sum(stacks) / len(stacks)) / bb
    except Exception:
        return None


def etapa_do_torneio(h: CanonicalHand) -> str | None:
    media = _media_da_mesa_bb(h)
    if media is None:
        return None
    for nome, lo, hi in ETAPAS:
        if lo <= media < hi:
            return nome
    return None


def _entrou_no_pote(h: CanonicalHand) -> bool | None:
    """VPIP de UMA mão: o herói colocou ficha por vontade no pré?

    None quando a mão não tem decisão de pré — postar blind não é decisão, e
    contar isso como fold foi o incidente do `.txt` truncado.
    """
    from app.analysis.stats import _tem_decisao
    from app.models.canonical import ActionType, StreetName

    pre = h.street(StreetName.PREFLOP)
    if not _tem_decisao(pre):
        return None
    for a in pre.actions:
        if a.actor == h.hero and a.type in (
                ActionType.CALL, ActionType.BET, ActionType.RAISE):
            return True
    return False


def frequencia_por_faixa(hands: list[CanonicalHand]) -> list[dict]:
    """Com que frequência ele entra no pote, POR PROFUNDIDADE DE STACK.

    O que o módulo sempre se recusou a afirmar sem amostra — e agora afirma
    quando tem. Só entra mão de sessão inteira: frequência sobre replay
    escolhido a dedo é o VPIP 94% de novo.

    A mão de torneio não é i.i.d.: quem quebra cedo só contribui com mãos de
    stack fundo, então o n por faixa é sempre desequilibrado. Por isso cada
    linha carrega o próprio n e as faixas sem amostra saem com `dizivel=False`
    em vez de sumirem — faixa que some vira "ele não joga isso", que é outra
    afirmação.
    """
    from app.analysis.stats import amostra_completa, margem_de_erro_pp

    por_faixa_: dict[str, list[bool]] = {}
    for h in amostra_completa(hands):
        f = faixa_de(_stack_bb(h))
        entrou = _entrou_no_pote(h)
        if f and entrou is not None:
            por_faixa_.setdefault(f, []).append(entrou)

    saida = []
    for nome, _lo, _hi, muda in FAIXAS:
        obs = por_faixa_.get(nome, [])
        n = len(obs)
        if not n:
            continue
        entrou = sum(obs)
        saida.append({
            "faixa": nome, "o_que_muda": muda, "maos": n, "entrou": entrou,
            "vpip_pct": round(100.0 * entrou / n, 1),
            "margem_pp": margem_de_erro_pp(n, entrou / n),
            "dizivel": n >= MIN_PARA_FREQUENCIA,
            "por_que_nao": ("" if n >= MIN_PARA_FREQUENCIA else
                            f"{n} mãos nesta faixa; preciso de "
                            f"{MIN_PARA_FREQUENCIA} para dizer uma taxa"),
        })
    return saida


def inversao(hands: list[CanonicalHand]) -> dict:
    """Ele aperta no início e solta perto do dinheiro — ou o contrário?

    A pergunta original do dono ("etapa inicial mais tight ou mais
    agressivo?") só vira mensurável assim: comparando a MESMA profundidade de
    stack entre etapas diferentes do torneio. Sem fixar o stack, a diferença
    entre início e fim é só o stack encolhendo, que é a árvore mudando e não
    o jogador.

    Devolve uma linha por faixa que tenha amostra nos DOIS extremos, e o
    veredito só sai quando as proporções se separam de verdade — o mesmo
    teste que impede `direcao_confiavel` de decidir pelo denominador.
    """
    from app.analysis.stats import amostra_completa

    celulas: dict[tuple, list[bool]] = {}
    for h in amostra_completa(hands):
        f = faixa_de(_stack_bb(h))
        e = etapa_do_torneio(h)
        entrou = _entrou_no_pote(h)
        if f and e and entrou is not None:
            celulas.setdefault((f, e), []).append(entrou)

    linhas = []
    for nome, _lo, _hi, _muda in FAIXAS:
        ini = celulas.get((nome, "inicial"), [])
        fim = celulas.get((nome, "final"), [])
        if len(ini) < MIN_POR_CELULA or len(fim) < MIN_POR_CELULA:
            continue
        p_ini, p_fim = sum(ini) / len(ini), sum(fim) / len(fim)
        # o teste recebe SEMPRE o lado maior primeiro: ele é unidirecional
        # ("A > B"), e o lado é escolhido olhando o dado — daí o limiar
        # bilateral lá dentro
        if p_fim > p_ini:
            separou = _proporcoes_diferem(sum(fim), len(fim),
                                          sum(ini), len(ini))
        else:
            separou = _proporcoes_diferem(sum(ini), len(ini),
                                          sum(fim), len(fim))
        linhas.append({
            "faixa": nome,
            "inicio": {"maos": len(ini), "vpip_pct": round(100 * p_ini, 1)},
            "final": {"maos": len(fim), "vpip_pct": round(100 * p_fim, 1)},
            "veredito": (None if not separou else
                         "solta perto do dinheiro" if p_fim > p_ini
                         else "aperta perto do dinheiro"),
        })

    if not linhas:
        return {"aplicavel": False,
                "por_que": ("nenhuma faixa de stack tem "
                            f"{MIN_POR_CELULA} mãos no início E no fim do "
                            "torneio — sem os dois lados não há comparação"),
                "linhas": []}
    return {"aplicavel": True, "linhas": linhas}


def texto(linhas: list[LinhaDaFaixa]) -> str:
    """O relatório em voz de coach. Contagem absoluta quando a faixa não tem
    amostra para taxa — a regra que teria evitado o VPIP 94%."""
    if not linhas:
        return ""
    fora = [f"📊 *Onde o EV foi embora, por tamanho de stack*"]
    for l in linhas:
        cabeca = f"\n*{l.faixa}* — {l.maos} mão(s)"
        if l.maos < MINIMO_PARA_TAXA_NA_FAIXA:
            cabeca += " _(pouca amostra: números absolutos, sem percentual)_"
        fora.append(cabeca)
        if not l.spots:
            fora.append("  nenhum spot auditável aqui ainda")
            continue
        if l.erros:
            fora.append(f"  {l.erros} erro(s) em {l.spots} spot(s) — "
                        f"{l.ev_perdido_bb:.1f}bb deixados na mesa")
            lado = l.direcao_confiavel
            if lado:
                fora.append(f"  e {l.direcao[lado]} deles foram para o MESMO "
                            f"lado: {lado} demais")
        else:
            fora.append(f"  {l.spots} spot(s), nenhum erro — está de pé")
    pior = onde_doi_mais(linhas)
    if pior:
        fora.append(f"\n🎯 A faixa que mais te custou é *{pior.faixa}*: "
                    f"{pior.ev_perdido_bb:.1f}bb. {pior.o_que_muda}.")
    return "\n".join(fora)


def texto_da_frequencia(hands: list[CanonicalHand]) -> str:
    """Com que frequência ele entra no pote, por profundidade — e a inversão.

    Duas seções que o módulo se recusava a produzir por falta de amostra, e
    que agora saem quando a amostra existe. Cada taxa vai com o n e a margem;
    faixa curta aparece dizendo POR QUE não vira taxa.
    """
    freq = frequencia_por_faixa(hands)
    inv = inversao(hands)
    if not freq and not inv.get("linhas"):
        return ""

    fora = ["📈 *Com que frequência você entra, por tamanho de stack*"]
    for l in freq:
        if l["dizivel"]:
            fora.append(f"\n*{l['faixa']}* — entra em *{l['vpip_pct']:g}%* "
                        f"({l['entrou']} de {l['maos']}, ±{l['margem_pp']:g}pp)")
        else:
            fora.append(f"\n*{l['faixa']}* — {l['entrou']} de {l['maos']} "
                        f"mão(s). _{l['por_que_nao']}._")

    if inv.get("aplicavel"):
        fora.append("\n\n⏳ *E muda do início para o fim do torneio?* "
                    "_(mesma profundidade de stack nos dois lados — sem isso "
                    "a diferença seria só o stack encolhendo)_")
        for l in inv["linhas"]:
            fora.append(
                f"\n*{l['faixa']}*: {l['inicio']['vpip_pct']:g}% no início "
                f"({l['inicio']['maos']} mãos) → {l['final']['vpip_pct']:g}% "
                f"no fim ({l['final']['maos']} mãos)")
            fora.append(f"  → *{l['veredito']}*" if l["veredito"] else
                        "  → a diferença não separa: com essa amostra eu não "
                        "consigo dizer que mudou")
    elif inv.get("por_que"):
        fora.append(f"\n\n⏳ _Sobre início vs fim de torneio: {inv['por_que']}._")
    return "\n".join(fora)
