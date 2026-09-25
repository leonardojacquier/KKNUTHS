"""ELE MELHOROU? — a medição que se recusa a mentir.

Esta é a parte do sistema com maior chance de queimar a confiança de novo,
porque "progresso" é o número que o dono mais quer ver e o mais fácil de
fabricar sem perceber.

O QUIZ NÃO SERVE COMO MEDIDA, do jeito que está. Cinco vieses, do pior para
o menor:

1. CONTAMINAÇÃO PELO `leak_boost` (é do nosso código): o sorteio puxa mais
   das categorias em que o aluno erra. Ótimo para TREINAR, fatal para MEDIR
   — quando ele melhora, o boost cai, o mix de spots muda, e a taxa de
   acerto observada muda por mudança de AMOSTRA, não de habilidade. A série
   temporal do drill é ininterpretável por construção.
2. MEMORIZAÇÃO: o drill é sobre a mão DELE, que ele já jogou e cuja análise
   já leu. Pode estar lembrando, não aplicando.
3. CHANCE: 3-4 botões dão 25-33% de acerto no chute.
4. FORMATO: quiz é sem pressão, sem tempo, com o spot já isolado. É o
   ambiente mais fácil possível; transferência para a mesa é parcial.
5. FEEDBACK IMEDIATO ensina o item, não necessariamente o conceito.

Daí a separação treino/aferição, e o fato de que SÓ a frequência em MÃO REAL
dá alta. O quiz mede conhecimento; a mesa mede desempenho.

E o veredito tem TRÊS valores, sendo `inconclusivo` o mais frequente e
obrigatório. Um sistema que só sabe dizer "melhorou" ou "não melhorou" vai
dizer um dos dois quando a resposta certa é "ainda não sei".
"""
from __future__ import annotations

from dataclasses import dataclass

MELHOROU = "melhorou"
NAO_MELHOROU = "nao_melhorou"
INCONCLUSIVO = "inconclusivo"

# Oportunidades necessárias POR PERÍODO (antes e depois) para detectar a
# queda, bilateral, alfa 5%, poder 80%. A tabela existe para o sistema
# CONSULTAR antes de abrir a boca — e para dizer ao aluno, no dia 1, quanto
# tempo vai levar.
N_NECESSARIO = ((60, 30, 42), (50, 25, 58), (40, 20, 81), (50, 30, 93),
                (30, 15, 120))

MINIMO_ABSOLUTO = 30       # abaixo disto é INCONCLUSIVO, sem exceção
MUDANCA_DE_CONTEXTO = 0.30  # 30% de mudança no mix e a comparação é recusada


def n_necessario(taxa_antes: float, taxa_alvo: float) -> int:
    """Quantas oportunidades por período para enxergar essa queda.

    Melhoras pequenas (50%->40%) precisam de ~400 por período e simplesmente
    NÃO são detectáveis no volume de um aluno de clube. Quando a tabela não
    cobre, devolve um número grande de propósito: é a forma de o sistema
    dizer "esse alvo é imensurável" em vez de fingir que mede.
    """
    melhor, dist = 400, 1e9
    for antes, alvo, n in N_NECESSARIO:
        d = abs(antes - taxa_antes) + abs(alvo - taxa_alvo)
        if d < dist:
            dist, melhor = d, n
    reducao = (taxa_antes - taxa_alvo) / max(taxa_antes, 1e-9)
    return melhor if reducao >= 0.35 else 400


def kappa(acertos: int, total: int, opcoes: int = 4) -> float | None:
    """Acerto AJUSTADO POR CHANCE. 60% com 4 botões é 47% ajustado.

    Reportar acerto cru num quiz de múltipla escolha infla o progresso de
    graça — e o piso do chute é o número que ninguém lembra de descontar.
    """
    if total <= 0:
        return None
    chance = 1.0 / max(opcoes, 2)
    obs = acertos / total
    return round((obs - chance) / (1.0 - chance), 3)


def contexto_mudou(antes: dict, depois: dict) -> bool:
    """O aluno trocou de stake/formato entre as janelas?

    Se trocou, os dois períodos não são comparáveis e a medição é RECUSADA.
    "Você melhorou" quando na verdade ele desceu de $22 para $5 é uma mentira
    que o próprio aluno vai desmentir sozinho.
    """
    chaves = set(antes) | set(depois)
    for k in chaves:
        a, d = float(antes.get(k, 0)), float(depois.get(k, 0))
        base = max(a, d, 1.0)
        if abs(a - d) / base > MUDANCA_DE_CONTEXTO:
            return True
    return False


@dataclass
class Medicao:
    veredito: str
    por_que: str
    n_pos: int
    faltam: int = 0


def medir(baseline: dict, pos: dict, limiar: float,
          controle_antes: dict | None = None,
          controle_depois: dict | None = None,
          contexto_antes: dict | None = None,
          contexto_depois: dict | None = None) -> Medicao:
    """Melhorou? Função PURA, e conservadora por desenho.

    A afirmação de melhora exige o limite SUPERIOR do intervalo abaixo do
    limiar: o sistema só fala quando a incerteza inteira cabe embaixo da
    linha. É deliberadamente duro — depois de um incidente de confiança, o
    custo de dizer "ainda não sei" é muito menor que o de errar de novo.
    """
    from app.analysis.bayes import shrunk_rate

    n = int(pos.get("oportunidades", 0))
    if n < MINIMO_ABSOLUTO:
        return Medicao(INCONCLUSIVO,
                       f"{n} oportunidades novas; preciso de "
                       f"{MINIMO_ABSOLUTO}", n, MINIMO_ABSOLUTO - n)

    if contexto_antes and contexto_depois and \
            contexto_mudou(contexto_antes, contexto_depois):
        return Medicao(INCONCLUSIVO,
                       "o stake ou o formato mudou entre os dois períodos — "
                       "não dá para comparar; reiniciei a linha de base", n)

    _, lo, hi = shrunk_rate(pos.get("escorregadas", 0), n, 20.0, 6.0)

    # CONTROLE: uma categoria que ninguém tratou. Se ela melhorou junto, o
    # campo ficou mais mole ou a amostra mudou — não foi aprendizado. É a
    # linha de código de maior retorno desta lista inteira.
    if controle_antes and controle_depois:
        antes_c = controle_antes.get("taxa", 0.0)
        depois_c = controle_depois.get("taxa", 0.0)
        if antes_c and (antes_c - depois_c) / antes_c > 0.3:
            return Medicao(INCONCLUSIVO,
                           "uma categoria que eu NÃO estava tratando melhorou "
                           "junto — isso costuma ser campo mais mole, não "
                           "aprendizado", n)

    if hi < limiar:
        return Medicao(MELHOROU,
                       f"a faixa inteira ({lo:.0f}-{hi:.0f}%) ficou abaixo "
                       f"do alvo de {limiar:.0f}%", n)
    if lo > baseline.get("taxa", 100.0):
        return Medicao(NAO_MELHOROU,
                       f"a taxa subiu: era {baseline.get('taxa', 0):.0f}%, "
                       f"agora o melhor caso é {lo:.0f}%", n)
    return Medicao(INCONCLUSIVO,
                   f"a faixa ({lo:.0f}-{hi:.0f}%) ainda encosta no alvo de "
                   f"{limiar:.0f}% — com mais mãos eu separo", n)


def texto_da_medicao(m: Medicao, nome_do_problema: str) -> str:
    """O que o aluno lê. `inconclusivo` precisa soar como TRABALHO EM CURSO,
    não como falha da ferramenta."""
    if m.veredito == MELHOROU:
        return (f"✅ *Resolvido: {nome_do_problema}*\n{m.por_que}.\n"
                "Fica sob vigilância por 60 dias — se voltar eu aviso, sem "
                "drama.")
    if m.veredito == NAO_MELHOROU:
        return (f"🔁 *{nome_do_problema}* — {m.por_que}.\n"
                "A hipótese de causa estava errada; vou trocar a abordagem, "
                "não repetir a mesma lição mais alto.")
    faltam = (f" Faltam ~{m.faltam} oportunidades." if m.faltam else "")
    return (f"⏳ *{nome_do_problema}* — ainda não sei.\n{m.por_que}.{faltam}\n"
            "_Prefiro te dizer isso a chutar._")
