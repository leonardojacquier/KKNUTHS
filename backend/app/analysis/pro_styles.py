"""Arquétipos de estilo dos grandes nomes do poker — BR e internacional.

Classifica o jogador pelos eixos VPIP/PFR/AF/3-bet e o aproxima de perfis
PÚBLICOS e qualitativos de jogadores famosos (como a imprensa especializada os
descreve — não são stats reais deles, que não são públicas). Também entrega o
CAMINHO de transição quando o aluno quer mudar de estilo.

Fontes das caracterizações: perfis públicos em PokerNews/WPT/PokerListings/
Primedope (Ivey TAG-camaleão; Dwan/Blom LAG destemido; Negreanu leitura
exploitativa; Loeliger/Polk GTO; Yuri Dzivielevski teoria-heavy com agressão
seletiva; Akkari leitura/experiência live; Rafael Moraes agressivo de MTT).
"""
from __future__ import annotations

# centro dos eixos: (vpip, pfr, af, three_bet)
ARCHETYPES: list[dict] = [
    {
        "key": "tag",
        "nome": "TAG sólido (tight-aggressive)",
        "centro": (22, 18, 2.6, 8),
        "pros": [
            ("Yuri Dzivielevski 🇧🇷", "o brasileiro mais premiado da WSOP: teoria pesada, "
             "agressão seletiva — só entra no pote com plano"),
            ("Stephen Chidwick", "disciplina de range impecável, pressão nos spots certos"),
            ("Pedro Garagnani 🇧🇷", "MTT sólido, fundamentos de estudo modernos"),
        ],
        "descricao": "Entra em poucos potes, mas chega agredindo. É o estilo com melhor "
        "relação risco/retorno para subir de stake.",
        "caminho": "Para jogar assim: corte os opens marginais de posição inicial, "
        "3-bete mais em posição (em vez de só pagar) e dobre a c-bet em boards secos.",
    },
    {
        "key": "lag",
        "nome": "LAG (loose-aggressive)",
        "centro": (30, 24, 3.2, 11),
        "pros": [
            ("Tom Dwan", "destemor calculado: blefa qualquer textura e paga leve "
             "quando a linha do vilão não fecha"),
            ("Rafael Moraes 🇧🇷", "ex-enxadrista, pressão máxima em MTT high roller"),
            ("Michael Addamo", "hiper-agressão que quebra o equilíbrio dos oponentes"),
        ],
        "descricao": "Muitos potes, muita pressão. EV alto nas mãos boas de mesa — e "
        "variância brutal. Exige leitura pós-flop de elite e banca para os swings.",
        "caminho": "Para jogar assim: alargue opens de posição FINAL primeiro (BTN/CO), "
        "adicione 3-bets leves contra abridores frouxos e treine barrels de turn — "
        "NUNCA alargue de UTG antes de dominar o pós-flop.",
    },
    {
        "key": "gto",
        "nome": "Equilibrado/GTO (teórico)",
        "centro": (24, 19, 2.4, 9),
        "pros": [
            ("Linus Loeliger", "considerado a referência de jogo próximo do equilíbrio"),
            ("Doug Polk", "construiu carreira provando linhas com solver"),
            ("Bruno Volkmann 🇧🇷", "estudo estruturado, decisões defensáveis por teoria"),
        ],
        "descricao": "Frequências balanceadas, difícil de explorar. É o estilo que os "
        "solvers ensinam — e a base de onde qualquer desvio exploitativo deve partir.",
        "caminho": "Para jogar assim: estude ranges por posição até virar automático, "
        "revise as mãos grandes no simulador e use os equilíbrios do /range como norte.",
    },
    {
        "key": "exploit",
        "nome": "Explorador/leitor (small-ball exploitativo)",
        "centro": (27, 17, 1.9, 6),
        "pros": [
            ("Daniel Negreanu", "small ball: potes pequenos, leitura de padrões e "
             "ajuste fino contra cada perfil"),
            ("André Akkari 🇧🇷", "campeão WSOP com leitura de mesa e experiência live"),
            ("Phil Ivey", "camaleão: alterna TAG e LAG conforme o oponente"),
        ],
        "descricao": "Joga o OPONENTE, não só as cartas: potes controlados, muitos "
        "flops, decisões por leitura. Brilha em field fraco/live.",
        "caminho": "Para jogar assim: anote tendências dos regulares, use as dicas de "
        "population/exploit do coach e treine pot control fora de posição.",
    },
    {
        "key": "nit",
        "nome": "Nit/rock (tight-passivo)",
        "centro": (14, 10, 1.4, 3),
        "pros": [
            ("(sem ídolo aqui)", "até os tights vencedores, como Chidwick, agridem — "
             "o rock puro só vence field muito fraco"),
        ],
        "descricao": "Só joga o topo e joga com medo. Fácil de explorar: o field "
        "rouba seus blinds e folda quando você finalmente tem jogo.",
        "caminho": "Para sair daqui: primeiro AGRESSÃO, depois range — transforme os "
        "calls passivos em 3-bets com o topo, e roube mais o blind do BTN/SB.",
    },
    {
        "key": "station",
        "nome": "Loose-passivo (calling station)",
        "centro": (38, 10, 1.0, 3),
        "pros": [
            ("(nenhum profissional joga assim)", "é o perfil que os pros procuram na mesa"),
        ],
        "descricao": "Entra demais e só paga. É o estilo com pior EV que existe — "
        "todo o dinheiro vaza em calls sem equity.",
        "caminho": "Para sair daqui: regra dura — se a mão não vale um raise, quase "
        "nunca vale um call. Corte 1/3 dos calls pré-flop e TODOS os calls de river "
        "sem blefe-catcher real.",
    },
]


def match_pro_style(vpip: float, pfr: float, af: float, three_bet: float,
                    desired: str | None = None) -> dict:
    """Classifica o estilo e aproxima dos pros; opcionalmente traça a transição.

    `desired`: key ou nome de arquétipo-alvo ('lag', 'gto'...) quando o aluno
    quer mudar de jogo — retorna o caminho do estilo atual para o alvo.
    """
    def dist(a: dict) -> float:
        cv, cp, ca, c3 = a["centro"]
        # eixos normalizados pela escala típica de cada stat
        return (((vpip - cv) / 10) ** 2 + ((pfr - cp) / 8) ** 2
                + ((af - ca) / 1.2) ** 2 + ((three_bet - c3) / 4) ** 2)

    ranked = sorted(ARCHETYPES, key=dist)
    best = ranked[0]
    result = {
        "estilo": best["nome"],
        "descricao": best["descricao"],
        "jogadores_parecidos": [
            {"nome": n, "por_que": d} for n, d in best["pros"][:3]
        ],
        "segundo_estilo_mais_proximo": ranked[1]["nome"],
        "nota": "comparação pelos eixos VPIP/PFR/AF/3-bet com os perfis públicos "
        "desses jogadores — qualitativa, não são as stats reais deles",
    }

    if desired:
        want = desired.strip().lower()
        target = next(
            (a for a in ARCHETYPES
             if a["key"] == want or want in a["nome"].lower()),
            None,
        )
        if target:
            result["transicao_para"] = target["nome"]
            result["caminho"] = target["caminho"]
            deltas = []
            cv, cp, ca, c3 = target["centro"]
            for atual, alvo, nome in ((vpip, cv, "VPIP"), (pfr, cp, "PFR"),
                                      (three_bet, c3, "3-bet")):
                d = alvo - atual
                if abs(d) >= 2:
                    deltas.append(f"{nome} {'↑' if d > 0 else '↓'} ~{abs(d):.0f}pp")
            if abs(af - ca) >= 0.4:
                deltas.append(f"AF {'↑' if ca > af else '↓'} para ~{ca:.1f}")
            result["ajustes_numericos"] = deltas or ["você já está perto do alvo"]
    return result
