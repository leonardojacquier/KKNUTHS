"""CICLO DE PROBLEMA — diagnóstico, intervenção, medição, alta.

Um erro isolado não é um problema; um PADRÃO é. E "padrão" não é impressão:
é um conjunto de portões que a observação precisa atravessar antes de virar
plano de estudo. O que este módulo protege é a diferença entre as duas.

A MÁQUINA DE ESTADOS, e por que ela tem seis estados e não três:

  observacao  erro visto, sem denominador suficiente. NÃO se fala com o aluno.
  suspeita    passou amostra e frequência, falhou custo ou recorrência.
              Vira "estou de olho", que é honesto e não gera trabalho.
  problema    passou os cinco portões. É o ÚNICO estado que gera plano.
  em_alta     critério de alta batido, em vigilância.
  resolvido   vigilância cumprida sem recaída.
  arquivado   sem oportunidade nova em 90 dias.

`arquivado` separado de `resolvido` é o que impede o sistema de FABRICAR
vitória. Quando o aluno para de jogar aquele spot — mudou de formato, de
stake, de horário — o problema não foi resolvido, ele sumiu. Um sistema com
três estados registra isso como sucesso e ensina o dono a confiar num
número que não aconteceu.

O QUE QUEBRA ESSE TIPO DE SISTEMA, e o que aqui evita:

- regressão à média: o problema é escolhido POR SER O PIOR, ou seja, por
  estar no extremo da flutuação. A próxima medição melhora sozinha. Por isso
  a linha de base NUNCA é a janela que diagnosticou (`baseline_valida`).
- comparações múltiplas: varrer 15 códigos e pegar o pior é procurar o
  extremo. Com mais de 10 códigos testados a régua vira IC99.
- declarar vitória cedo: o critério de alta é PRÉ-REGISTRADO, escrito antes
  da intervenção e imutável. Sem isso sempre se acha um jeito de fechar.
- só achar problema: teto de 1 ativo, fila visível, e o dever de mostrar
  também o que o aluno faz bem. Crítico se abandona.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

OBSERVACAO = "observacao"
SUSPEITA = "suspeita"
PROBLEMA = "problema"
EM_ALTA = "em_alta"
RESOLVIDO = "resolvido"
ARQUIVADO = "arquivado"

# --- portões de promoção. Todos têm que passar. ---------------------------
MIN_OPORTUNIDADES = 20          # abaixo disso o posterior é o prior
MIN_OPORTUNIDADES_ESTIMADO = 30  # custo estimado exige mais evidência
MIN_CUSTO_BB100 = 0.75          # leak barato não merece um ciclo de 4 semanas
MIN_SESSOES = 3                 # erro concentrado numa noite é tilt, não leak
MIN_DIAS = 10
MIN_PROCEDENCIA = 0.70          # print lido por visão não sustenta diagnóstico

MAX_ATIVOS = 1                  # o argumento é ESTATÍSTICO, não pedagógico:
                                # três problemas dividem as oportunidades e
                                # nenhum fecha
MAX_PROMOVIDOS_POR_CICLO = 2
CODIGOS_ATE_IC95 = 10           # acima disso, régua de IC99

# quem destrava quem. Não adianta trabalhar defesa de BB com um aluno que
# não calcula preço de pote: metade das mãos daquele spot ele erra pelo
# motivo errado, e a intervenção certa é a outra.
PREREQ: dict[str, tuple[str, ...]] = {
    "bb_subdefesa": ("pot_odds",),
    "call_caro": ("pot_odds",),
    "shove_perdido": ("push_fold_nash",),
    "shove_largo": ("push_fold_nash",),
}

# as quatro causas do MESMO erro. Cada uma pede intervenção diferente, e
# mandar teoria para quem já sabe a teoria é o desperdício mais comum.
CAUSAS = {
    "conhecimento": ("não sabe a regra",
                     "mini-lição + a regra em uma frase"),
    "reconhecimento": ("sabe a regra, não reconhece o spot na mesa",
                       "drill de RECONHECIMENTO: 10 spots, pergunta só "
                       "'é este spot?'"),
    "execucao": ("reconhece, decide errado sob pressão",
                 "rotina e gatilho — não é teoria"),
    "economico": ("joga acima do que a banca aguenta",
                  "conversa de bankroll, não de poker"),
}


@dataclass
class Evidencia:
    """Uma sessão que contribuiu com oportunidades desse código."""
    dia: str                 # AAAA-MM-DD
    oportunidades: int
    escorregadas: int
    fonte_exata: bool = True


@dataclass
class Veredito:
    estado: str
    por_que: str
    portoes: dict = field(default_factory=dict)


def _dias_entre(dias: list[str]) -> int:
    if len(dias) < 2:
        return 0
    try:
        d = sorted(datetime.fromisoformat(x) for x in dias)
        return (d[-1] - d[0]).days
    except Exception:
        return 0


def avaliar(diagnostico: dict, evidencias: list[Evidencia],
            codigos_testados: int = 1) -> Veredito:
    """Onde esta observação está na máquina de estados. Função PURA.

    `diagnostico` é uma linha de `taxonomia.agregar`. Devolve o estado E o
    motivo — o motivo é o que o dono lê para discordar, e é o que impede o
    sistema de virar caixa-preta.
    """
    from app.analysis.bayes import Z95, Z99, shrunk_rate

    opp = diagnostico.get("oportunidades", 0)
    miss = diagnostico.get("escorregadas", 0)
    estimado = bool(diagnostico.get("custo_e_estimado"))
    minimo = MIN_OPORTUNIDADES_ESTIMADO if estimado else MIN_OPORTUNIDADES
    tolerancia = diagnostico.get("tolerancia_pct", 25.0)

    # a régua endurece quando muitos códigos disputam o posto de "o pior"
    z = z_para_familia(codigos_testados)
    _, lo, _ = shrunk_rate(miss, opp, 20.0, 6.0, z=z)

    dias = sorted({e.dia for e in evidencias})
    exatas = sum(e.oportunidades for e in evidencias if e.fonte_exata)
    total = sum(e.oportunidades for e in evidencias) or 1
    procedencia = exatas / total

    portoes = {
        "amostra": (opp >= minimo, f"{opp}/{minimo} oportunidades"),
        "frequencia": (lo > tolerancia,
                       f"pior caso {lo:.0f}% vs tolerância {tolerancia:.0f}%"),
        "custo": (diagnostico.get("custo_bb_100", 0) >= MIN_CUSTO_BB100,
                  f"{diagnostico.get('custo_bb_100', 0):.2f}bb/100"),
        "recorrencia": (len(dias) >= MIN_SESSOES
                        and _dias_entre(dias) >= MIN_DIAS,
                        f"{len(dias)} sessão(ões) em {_dias_entre(dias)} dia(s)"),
        "procedencia": (procedencia >= MIN_PROCEDENCIA,
                        f"{procedencia:.0%} de fonte exata"),
    }
    reprovados = [k for k, (ok, _) in portoes.items() if not ok]

    if not reprovados:
        return Veredito(PROBLEMA, "passou os cinco portões", portoes)
    # amostra ou frequência reprovadas = nem suspeita é; não há o que dizer
    if "amostra" in reprovados or "frequencia" in reprovados:
        return Veredito(OBSERVACAO,
                        "sem evidência para falar com o aluno: "
                        + ", ".join(portoes[k][1] for k in reprovados), portoes)
    return Veredito(SUSPEITA,
                    "de olho, ainda não é diagnóstico: "
                    + ", ".join(f"{k} ({portoes[k][1]})" for k in reprovados),
                    portoes)


def prioridade(diagnostico: dict, oportunidades_por_semana: float,
               aluno_novo: bool = False) -> float:
    """Qual problema atacar primeiro.

    Custo manda, mas não sozinho: um leak caro que aparece 2× por semana
    leva meses para fechar, e um ciclo que nunca fecha ensina o aluno que o
    sistema não tem saída. Para ALUNO NOVO a ordem se inverte de propósito —
    a primeira alta é o que faz ele acreditar que dá para resolver.
    """
    custo = float(diagnostico.get("custo_bb_100", 0.0))
    destrava = len([c for c, p in PREREQ.items()
                    if diagnostico.get("codigo") in p])
    rapidez = min(oportunidades_por_semana / 10.0, 1.0)
    if aluno_novo:
        return rapidez * 2.0 + custo * 0.2
    return custo * 1.0 + destrava * 0.5 + rapidez * 0.4


def z_para_familia(codigos_testados: int, alfa: float = 0.05) -> float:
    """O z que segura o alfa da FAMÍLIA em `alfa`, com N códigos testados.

    O degrau anterior (`Z99 se testados > 10, senão Z95`) tinha dois
    defeitos, e o segundo anulava o primeiro:

      1. z=2,576 está calibrado para EXATAMENTE N=10. Como a regra só ligava
         a partir de N=11, ele valia apenas na faixa em que já era
         insuficiente — em N=15 o alfa familiar com 2,576 é ~7,2%.
      2. em produção `codigos_testados` é `len(CODIGOS)` = 6, e `6 > 10` é
         falso. O ramo endurecido NUNCA executava. Medido em 09/08.

    Šidák resolve os dois de uma vez e sem degrau: cada teste roda a
    `1-(1-alfa)^(1/N)`. Como o portão usa o limite INFERIOR de um IC
    bilateral, a cauda de interesse é metade disso.
    """
    import math

    n = max(1, int(codigos_testados or 1))
    por_teste = 1.0 - (1.0 - alfa) ** (1.0 / n)
    # quantil normal da cauda superior em `por_teste/2` (Acklam, erro < 1e-9
    # na faixa que nos interessa — não vale trazer scipy por isto)
    p = 1.0 - por_teste / 2.0
    if p <= 0.0 or p >= 1.0:
        return 1.96
    q = math.sqrt(-2.0 * math.log(1.0 - p)) if p > 0.5 else \
        math.sqrt(-2.0 * math.log(p))
    z = q - ((0.010328 * q + 0.802853) * q + 2.515517) / \
        (((0.001308 * q + 0.189269) * q + 1.432788) * q + 1.0)
    return abs(z)


def prereq_inertes() -> set[str]:
    """Pré-requisitos que NENHUM detector sabe produzir.

    `pot_odds` e `push_fold_nash` não estão em `taxonomia.CODIGOS`: não há
    detector que os diagnostique, logo eles nunca entram em `resolvidos` e o
    bloqueio seria eterno. Medido em 09/08: quatro dos seis códigos —
    incluindo os dois de maior sinal por amostra — estavam travados para
    sempre, e o aluno via a fila com o código interno cru ("espera
    pot_odds") sem nunca sair dela.

    Pré-requisito que não pode ser satisfeito é pior que pré-requisito
    nenhum: esconde metade do diagnóstico e parece funcionar.
    """
    from app.analysis.taxonomia import CODIGOS

    return {p for alvos in PREREQ.values() for p in alvos
            if p not in CODIGOS}


def bloqueado_por(codigo: str, resolvidos: set[str]) -> str | None:
    """O pré-requisito que ainda falta — vira o problema ativo no lugar.

    Só bloqueia por EVIDÊNCIA. Se nenhum detector sabe diagnosticar o
    pré-requisito, não há como afirmar que o aluno não o domina, e o padrão
    passa a ser "não sei" — que aqui significa deixar passar, e não travar.

    A dependência continua declarada em `PREREQ` de propósito: no dia em que
    existir um detector de `pot_odds`, o bloqueio volta a valer sozinho, sem
    ninguém precisar lembrar de reativá-lo.
    """
    inertes = prereq_inertes()
    for p in PREREQ.get(codigo, ()):
        if p in inertes:
            continue
        if p not in resolvidos:
            return p
    return None


def criterio_de_alta(diagnostico: dict, agora: datetime | None = None) -> dict:
    """O critério ESCRITO ANTES da intervenção. Imutável depois disso.

    É o antídoto do "garden of forking paths": sem pré-registro, o coach —
    humano ou modelo — sempre acha um jeito de declarar vitória olhando o
    dado depois. Com ele, a régua já estava lá.

    O alvo é redução RELATIVA de 60% porque melhora pequena (50%->40%) exige
    ~400 oportunidades por período para ser detectável, e nenhum aluno de
    clube produz isso. Alvo que a amostra não consegue medir não é alvo.
    """
    agora = agora or datetime.now(timezone.utc)
    taxa = diagnostico.get("taxa_mean", 0.0)
    return {
        "metrica": "taxa de escorregada em amostra completa",
        "codigo": diagnostico.get("codigo"),
        "taxa_na_abertura": taxa,
        "limiar": round(taxa * 0.4, 1),
        "n_minimo": 30,
        "janelas_minimas": 2,
        "dias_minimos": 14,
        "registrado_em": agora.isoformat(),
        "por_extenso": (
            f"considero resolvido quando a taxa cair de {taxa:.0f}% para "
            f"{taxa * 0.4:.0f}% ou menos, com pelo menos 30 oportunidades "
            "NOVAS de sessão inteira, em 2 janelas distintas cobrindo 14 dias"),
    }


def baseline_valida(diagnostico_dia: str, baseline_dias: list[str]) -> bool:
    """A linha de base pode ser usada?

    NÃO se ela é a mesma janela que diagnosticou. O problema foi escolhido
    por estar no extremo da flutuação, então medir a melhora contra a
    própria janela extrema mostra progresso mesmo sem intervenção nenhuma.
    Essa é a armadilha que reporta melhora falsa de forma SISTEMÁTICA — e
    seria a segunda quebra de confiança da ferramenta.
    """
    return bool(baseline_dias) and all(d > diagnostico_dia
                                       for d in baseline_dias)


def texto_do_plano(ativo: dict, fila: list[dict], acertos: list[str]) -> str:
    """O que o aluno lê. Função PURA.

    Três regras que decidem se ele continua ou abandona:

    1. A FILA APARECE. Um problema ativo por vez é decisão estatística, mas
       sem ver o resto o aluno acha que a ferramenta é míope. Ver a fila com
       o motivo da ordem resolve isso sem quebrar o foco.
    2. CONTAGEM CRUA ABAIXO DO N MÍNIMO. "4 de 14" é honesto; "29%" com n=14
       é a mesma classe de erro do VPIP 94% — percentual carrega uma promessa
       de precisão que o denominador não paga.
    3. PELO MENOS UM ACERTO, com evidência. Detector de acerto quase nunca é
       construído, e sem ele a ferramenta é só um crítico. Crítico se
       abandona.
    """
    if not ativo:
        return ""
    n = ativo.get("oportunidades", 0)
    erros = ativo.get("escorregadas", 0)
    alvo = ativo.get("alta_n_minimo", 30)
    fora = [f"🎯 *{ativo.get('nome') or ativo.get('codigo')}*",
            f"_{ativo.get('pergunta', '')}_", ""]

    if n < alvo:
        cheio = int(12 * min(n / max(alvo, 1), 1.0))
        fora += [f"Coleta: {'▓' * cheio}{'░' * (12 - cheio)}  "
                 f"{n} de ~{alvo} oportunidades",
                 f"Até aqui: {erros} escorregada(s) nessas {n}.",
                 "",
                 "*Ainda não dá para dizer se melhorou* — com essa amostra o "
                 "número balança sozinho. Eu te aviso quando souber."]
    else:
        fora += [f"{erros} de {n} oportunidades novas.",
                 ativo.get("alta_por_extenso", "")]

    if fila:
        fora += ["", f"_Na fila ({len(fila)}): "
                 + ", ".join(f.get("nome") or f.get("codigo") for f in fila[:3])
                 + ". Estamos neste primeiro porque é o mais caro._"]
    if acertos:
        fora += ["", "✅ *E o que já está de pé:* " + "; ".join(acertos[:2])]
    return "\n".join(fora)


def pode_dar_alta(medicao: dict, controle_melhorou: bool,
                  contexto_estavel: bool) -> tuple[bool, str]:
    """Os seis critérios da alta. Conjunção — todos.

    O controle é o mais barato e o mais eficaz: se uma categoria NÃO tratada
    melhorou junto, quase certamente não foi aprendizado — foi campo mais
    mole, stake menor ou mudança na amostra.
    """
    n = medicao.get("oportunidades", 0)
    if n < 30:
        return False, f"só {n} oportunidades novas; preciso de 30"
    if medicao.get("post_hi", 100.0) >= medicao.get("limiar", 0.0):
        return False, ("o intervalo ainda encosta no limiar — a melhora não "
                       "cabe inteira abaixo da linha")
    if medicao.get("janelas", 0) < 2 or medicao.get("dias", 0) < 14:
        return False, "uma sessão boa não é alta; preciso de 2 janelas/14 dias"
    if not contexto_estavel:
        return False, ("o stake ou o formato mudou no meio — não dá para "
                       "comparar os dois períodos")
    if controle_melhorou:
        return False, ("a categoria de controle melhorou junto: isso é campo "
                       "mais mole, não aprendizado")
    return True, "os seis critérios bateram"
