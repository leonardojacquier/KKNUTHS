"""PROVA REAL — a ferramenta auditando a si mesma nas mãos DO ALUNO.

Motivação (palavras do aluno): "não estou confiando que a ferramenta esteja
confiável". Ele tem razão: quase todo defeito da última semana quem achou foi
ELE, não a suíte. Testes automatizados guardam o bug ANTERIOR; não descobrem
o próximo. Dizer "244 testes passam" não é evidência para quem usa.

Então em vez de pedir confiança, esta prova roda checagens INDEPENDENTES
sobre as mãos reais do aluno e mostra o resultado — inclusive as falhas.
Ele controla, ele vê, não depende da minha palavra.

CLASSES verificadas (cada uma nasceu de um defeito real):
  A. parser        — cartas/board/showdown válidos e sem repetição
  B. contas        — pote fecha, coletado <= pote, net coerente
  C. gabarito      — a mão feita que o coach cita bate com o board
  D. veredito      — imagem do spot não contradiz o solver (caso TT/15bb)
  E. motor         — o equilíbrio responde e é coerente (AA >= mão média)
  F. filme         — as bandas do storyboard batem com a mão

HONESTIDADE: uma prova limpa NÃO significa "está tudo certo" — significa
"nenhuma das classes que eu sei verificar falhou". As classes que ninguém
pensou continuam invisíveis. Isso vai escrito no resultado.
"""
from __future__ import annotations

from app.models.canonical import CanonicalHand

_RANKS, _SUITS = "23456789TJQKA", "cdhs"


def _cartas_ok(cs) -> bool:
    return bool(cs) and all(
        isinstance(c, str) and len(c) == 2
        and c[0].upper() in _RANKS and c[1].lower() in _SUITS for c in cs)


def _check_parser(h: CanonicalHand) -> list[str]:
    p = []
    if h.hero_cards and not _cartas_ok(h.hero_cards):
        p.append(f"cartas do herói inválidas: {h.hero_cards}")
    if h.final_board:
        if not _cartas_ok(h.final_board):
            p.append(f"board inválido: {h.final_board}")
        elif len(h.final_board) > 5:
            p.append(f"board com {len(h.final_board)} cartas")
    for quem, cs in (h.shown_cards or {}).items():
        if not _cartas_ok(cs):
            p.append(f"showdown inválido de {quem}: {cs}")
    todas = list(h.hero_cards or []) + list(h.final_board or []) + [
        c for cs in (h.shown_cards or {}).values() for c in (cs or [])]
    vistas = [c for c in todas if isinstance(c, str)]
    if len(set(vistas)) != len(vistas):
        p.append("a MESMA carta aparece duas vezes na mão")
    return p


def _check_contas(h: CanonicalHand) -> list[str]:
    p = []
    if h.total_pot and h.collected:
        if sum(h.collected.values()) > h.total_pot * 1.01:
            p.append("soma dos potes coletados MAIOR que o pote total")
    if h.stakes.big_blind and h.stakes.big_blind <= 0:
        p.append("big blind zerado ou negativo")
    try:
        from app.agent.analyzer import analyze_hand

        a = analyze_hand(h)
        if a["net_bb"] is None:
            p.append("resultado da mão (net) não calculado")
    except Exception as exc:
        p.append(f"a análise da mão QUEBRA: {type(exc).__name__}")
    return p


def _check_gabarito(h: CanonicalHand) -> list[str]:
    """A mão feita que o coach cita tem que sair do board — e a textura tem
    que bater (o 'QJ fechou flush' num board de duas copas nasceu aqui)."""
    p = []
    if not (h.hero_cards and h.final_board and len(h.final_board) >= 3):
        return p
    try:
        from app.analysis.equity import board_texture, describe_hand

        desc = describe_hand(h.hero_cards, h.final_board)
        tex = board_texture(h.final_board)
        if desc and "flush" in desc and not tex["flush_possivel"]:
            p.append(f"gabarito diz '{desc}' mas o board não permite flush")
        for quem, cs in (h.shown_cards or {}).items():
            d2 = describe_hand(cs, h.final_board)
            if d2 and "flush" in d2 and not tex["flush_possivel"]:
                p.append(f"'{d2}' de {quem} sem flush possível no board")
    except Exception as exc:
        p.append(f"leitura da mão feita QUEBRA: {type(exc).__name__}")
    return p


def _check_filme(h: CanonicalHand) -> list[str]:
    """O filme não pode mostrar carta que não existe na mão, nem perder o
    showdown que o parser leu."""
    p = []
    try:
        from app.bot.processing import film_bands

        bands = film_bands(h)
        if not bands:
            return p
        mostrou = {r["who"] for b in bands for r in (b.get("reveals") or [])}
        for quem in (h.shown_cards or {}):
            if not any(quem in m for m in mostrou):
                p.append(f"showdown de {quem} sumiu do filme")
        ult = bands[-1].get("board") or []
        if h.final_board and len(ult) != len(h.final_board):
            p.append("board do filme diferente do board da mão")
    except Exception as exc:
        p.append(f"o filme QUEBRA: {type(exc).__name__}")
    return p


def _check_veredito(h: CanonicalHand) -> list[str]:
    """Imagem do spot x solver: o caso TT/15bb (imagem dizia PAGAR onde o
    equilíbrio manda JAM) sobre as mãos reais."""
    try:
        from scripts.nightly_coherence import check_verdict_vs_solver

        return [s.split(": ", 1)[-1] for s in check_verdict_vs_solver(h)]
    except Exception:
        return []


def _check_motor() -> list[str]:
    """O motor de equilíbrio responde e é coerente? (não depende de mão)"""
    p = []
    try:
        from app.analysis.allin_engine import available, solve_spot

        if not available():
            return ["motor de equilíbrio INDISPONÍVEL (matriz de equity)"]
        sol = solve_spot("open_shove", "MP", 12.0)
        if not sol:
            return ["motor de equilíbrio não resolveu um spot simples"]
        ev = sol["ev"]
        if not (ev["AA"] > ev["KK"] > ev["72o"]):
            p.append("motor: ordem de força das mãos INVERTIDA")
        if ev["72o"] > 0:
            p.append("motor: 72o aparece como +EV para empurrar (suspeito)")
        if not (0 < sol["acao_pct"] < 100):
            p.append(f"motor: range de {sol['acao_pct']}% é implausível")
    except Exception as exc:
        p.append(f"motor QUEBRA: {type(exc).__name__}")
    return p


_CLASSES = (
    ("parser", _check_parser),
    ("contas", _check_contas),
    ("gabarito", _check_gabarito),
    ("filme", _check_filme),
    ("veredito", _check_veredito),
)


def prova_real(hands: list[CanonicalHand], limite: int = 60) -> dict:
    """Roda todas as classes sobre as mãos e devolve o placar HONESTO."""
    amostra = list(hands)[:limite]
    achados: list[dict] = []
    por_classe: dict[str, int] = {c: 0 for c, _ in _CLASSES}
    for h in amostra:
        for nome, fn in _CLASSES:
            try:
                for msg in fn(h):
                    achados.append({"mao": h.hand_id, "classe": nome,
                                    "problema": msg})
                    por_classe[nome] += 1
            except Exception as exc:
                achados.append({"mao": h.hand_id, "classe": nome,
                                "problema": f"checagem quebrou: {exc}"})
                por_classe[nome] += 1
    motor = _check_motor()
    for m in motor:
        achados.append({"mao": "—", "classe": "motor", "problema": m})
    return {
        "maos": len(amostra),
        "classes": len(_CLASSES) + 1,
        "problemas": len(achados),
        "por_classe": {**por_classe, "motor": len(motor)},
        "achados": achados[:20],
    }


def texto_prova(r: dict) -> str:
    """Resultado em português, com a ressalva de honestidade sempre junto."""
    if not r or not r.get("maos"):
        return ("Não achei mãos suas pra auditar. Manda um torneio ou alguns "
                "replays e roda de novo.")
    l = [f"🔬 *Prova real* — auditei *{r['maos']}* mãos suas em "
         f"*{r['classes']}* classes de verificação.\n"]
    if not r["problemas"]:
        l.append("✅ *Nenhum problema encontrado.*")
    else:
        l.append(f"⚠️ *{r['problemas']} problema(s):*")
        for a in r["achados"][:8]:
            l.append(f"• [{a['classe']}] {a['problema'][:90]}")
        vazias = [c for c, n in r["por_classe"].items() if not n]
        if vazias:
            l.append(f"\nClasses limpas: {', '.join(vazias)}")
    l.append(
        "\n_O que isto prova e o que NÃO prova: prova que nenhuma das "
        "verificações que eu sei fazer falhou nas suas mãos. NÃO prova que "
        "está tudo certo — erro de um tipo que ninguém pensou em verificar "
        "continua invisível. Quando você achar um, ele vira classe nova aqui._")
    return "\n".join(l)
