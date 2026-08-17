"""Relatório MÃO A MÃO de um torneio — o dossiê completo, em HTML.

Duas camadas, como um coach humano faria:
- MÃOS JOGADAS: um card por mão com identificação completa (ID da sala, hora,
  nível), a história lance a lance, os números e a ANÁLISE (texto do coach,
  preenchido pelo chamador; fallback determinístico sempre presente).
- FOLDS DE ROTINA: tabela compacta com veredito técnico por range em CADA
  linha — nunca "pergunte ao coach": o relatório É a análise.
"""
from __future__ import annotations

import base64
import html as _html

from app.agent.analyzer import analyze_hand
from app.analysis.handsearch import _hero_line
from app.models.canonical import ActionType, CanonicalHand, StreetName

# Teto de caracteres da nota que vai DENTRO da imagem da mão: a figura cresce
# ~30px por linha quebrada e o PDF do relatório tem uma página por mão.
NOTA_IMG_MAX = 260

_SYM = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
_RED = {"h", "d"}
_RANKS = "23456789TJQKA"


def _cards_html(cards: list[str]) -> str:
    out = []
    for c in cards or []:
        if len(c) != 2:
            continue
        color = "#C0564A" if c[1] in _RED else "#1B211D"
        out.append(f"<b style='color:{color}'>{c[0]}{_SYM.get(c[1], c[1])}</b>")
    return " ".join(out) or "—"


def hand_class(cards: list[str]) -> str | None:
    """['Ad','3c'] -> 'A3o'; ['8h','9h'] -> '98s'."""
    if not cards or len(cards) != 2 or any(len(c) != 2 for c in cards):
        return None
    (r1, s1), (r2, s2) = cards[0], cards[1]
    if r1 == r2:
        return r1 + r2
    hi, lo = (r1, r2) if _RANKS.index(r1) > _RANKS.index(r2) else (r2, r1)
    return hi + lo + ("s" if s1 == s2 else "o")


def _played(h: CanonicalHand) -> bool:
    """O herói colocou fichas voluntariamente?"""
    for st in h.streets:
        for a in st.actions:
            if (a.actor == h.hero and a.type in
                    (ActionType.CALL, ActionType.BET, ActionType.RAISE)):
                return True
    return False


def _facing_preflop(h: CanonicalHand) -> tuple[int, str]:
    """(nº de raises antes da 1ª decisão do herói, posição de quem abriu)."""
    pre = h.street(StreetName.PREFLOP)
    if not pre:
        return 0, ""
    pos = {p.name: (p.position or "?") for p in h.players}
    raises = 0
    opener = ""
    for a in pre.actions:
        if a.actor == h.hero and a.type != ActionType.POST:
            return raises, opener
        if a.type == ActionType.RAISE:
            raises += 1
            opener = pos.get(a.actor, "?")
    return raises, opener


def fold_verdict(h: CanonicalHand, a: dict) -> str:
    """Veredito técnico para fold pré-flop — baseado em range, nunca vago."""
    from app.analysis.ranges import OPEN_RANGES, parse_range

    hc = hand_class(h.hero_cards)
    pos = a.get("position") or "?"
    raises, opener = _facing_preflop(h)
    stack = a.get("hero_stack_bb")

    if raises == 0:
        rng = OPEN_RANGES.get(pos)
        if hc and rng and hc in parse_range(rng):
            return (f"⚠️ dava para abrir — {hc} de {pos} é mão de ataque; "
                    f"largar aqui é passivo demais")
        if stack and stack <= 12 and hc:
            from app.analysis.pushfold import push_fold

            pf = push_fold(h.hero_cards, stack, pos)
            if pf.get("applicable") and pf["decision"] == "push":
                return (f"⚠️ com {stack:g}bb era shove — {hc} é lucrativo aqui; "
                        f"largar deixou dinheiro na mesa")
        return f"✅ fold padrão — {hc or '?'} não vale a briga de {pos}"

    quem = f" contra o open de {opener}" if opener else " contra um raise"
    if hc and hc in parse_range("99+, AQs+, AQo+"):
        return (f"🟡 {hc} é mão forte demais para largar{quem} — "
                f"só ok se o vilão for muito apertado")
    return f"✅ fold padrão — {hc or '?'}{quem} não compensa"


def played_facts(h: CanonicalHand) -> dict:
    """Fatos calculados de uma mão jogada — o insumo da análise (nada estimado)."""
    from app.analysis.equity import equity_vs_random
    from app.bot.processing import _walk_hand

    a = analyze_hand(h)
    lines, decisions = _walk_hand(h)
    key_numbers = []
    for d in decisions:
        if d["to_call_bb"] > 0 and d["actual"] != "fold":
            req = d["to_call_bb"] / (d["pot_bb"] + d["to_call_bb"])
            try:
                eq = equity_vs_random(h.hero_cards, d["board"], 1,
                                      iterations=1500, seed=5)
            except Exception:
                eq = None
            key_numbers.append({
                "street": d["street"], "pagou_bb": d["to_call_bb"],
                "pote_bb": d["pot_bb"], "equity_minima": round(req, 2),
                "equity_vs_aleatoria": round(eq, 2) if eq else None,
                # QUAL foi a ação. `!= "fold"` junta CALL e RAISE, e o preço
                # calculado acima é o de PAGAR: aplicá-lo a um raise diz
                # "pagou mais caro do que a mão vale" para quem não pagou —
                # erro de categoria, não de conta. Medido em 09/08: 24 mãos,
                # 12 delas com raise, e as 24 acusadas de call caro.
                "acao": d["actual"],
            })
        elif d["to_call_bb"] > 0 and d["actual"] == "fold":
            # O FOLD TAMBÉM É OPORTUNIDADE. Sem ele o denominador só tem as
            # mãos em que o herói pagou, e a taxa vira P(erro | pagou) em vez
            # de P(erro | teve preço na frente) — o mesmo defeito que o
            # bb_subdefesa tinha, num código marcado como custo "exato".
            key_numbers.append({
                "street": d["street"], "pagou_bb": 0.0,
                "pote_bb": d["pot_bb"],
                "equity_minima": round(
                    d["to_call_bb"] / (d["pot_bb"] + d["to_call_bb"]), 2),
                "equity_vs_aleatoria": None, "acao": "fold",
            })
        elif d["actual"] in ("bet", "raise") and d["pot_bb"]:
            key_numbers.append({
                "street": d["street"], "acao": d["actual"],
                "valor_bb": d["amount_bb"], "pote_bb": d["pot_bb"],
                "sizing_pct_pote": round(100 * d["amount_bb"] / d["pot_bb"])
                if d["pot_bb"] else None,
            })
    return {"analysis": a, "story": lines, "numbers": key_numbers}


def _termos() -> str:
    from app.agent.llm import TERMOS_REGRA

    return TERMOS_REGRA


# Quantas mãos JOGADAS recebem análise de coach (LLM) num relatório de torneio.
#
# Era 40, e acima disso NENHUMA recebia — um torneio de 90 mãos jogadas saía
# inteiro no veredito determinístico. O dono: *"se tiver torneios mais longos
# analisa as 150 principais mãos e o resto coloca algo mais simplificado e
# coloca o botão"*.
#
# CUSTO: `per_hand_analysis_llm` roda em lotes de 6, então 150 mãos = 25
# chamadas de LLM por relatório (centavos com o modelo de análise atual).
# É o preço do teto, não uma estimativa de uso: torneio com mais de 150 mãos
# jogadas é raro, e abaixo disso o número de chamadas cai proporcional.
TETO_MAOS_COACHED = 150


def _peso_da_mao(h: CanonicalHand, ordem: int) -> tuple:
    """Chave de ordenação por IMPORTÂNCIA (menor = mais importante).

    A direção do dono é "as mãos que decidiram o torneio", então o critério é,
    nesta ordem e sempre determinístico:

    1. **all-in do herói** — num torneio a mão que decide é aquela em que o
       stack foi para o meio. Um jam de 0.1bb de saldo é decisão de torneio;
       um pote gordo ganho sem risco de eliminação não é.
    2. **maior |saldo em bb|** — o tamanho do que mudou de mão. Módulo porque
       a mão que custou 60bb ensina tanto quanto a que ganhou 60bb.
    3. **maior pote** — desempate para saldo igual: saldo zero pode ser um
       pote grande devolvido (aposta não paga, split), que é decisão real, e
       o pote separa isso de um limp de 0.1bb.
    4. **ordem no torneio** — desempate final estável: o mesmo torneio sempre
       escolhe as mesmas 150 mãos, rodando quantas vezes rodar.

    `analyze_hand` pode falhar numa mão malformada; quando falha ela vai para
    o fim da fila em vez de derrubar o relatório inteiro.
    """
    from app.analysis.handsearch import match_pattern

    try:
        a = analyze_hand(h)
        saldo = abs(a.get("net_bb") or 0.0)
        pote = (a.get("pot_total") or 0.0) / (h.stakes.big_blind or 1)
    except Exception:
        return (1, 0.0, 0.0, ordem)
    jam = 0 if match_pattern(h, "allin") else 1
    return (jam, -saldo, -pote, ordem)


def maos_principais(jogadas: list[CanonicalHand],
                    teto: int = TETO_MAOS_COACHED) -> list[CanonicalHand]:
    """As `teto` mãos mais importantes do torneio, NA ORDEM em que foram jogadas.

    Acima do teto, cortar pelas primeiras seria cortar pelo começo do torneio —
    justo a parte em que nada foi decidido. Aqui o corte é por importância
    (`_peso_da_mao`) e a devolução volta para a ordem cronológica: o corte
    escolhe QUAIS mãos, nunca reordena o relatório nem o lote do coach.
    """
    if len(jogadas) <= teto:
        return list(jogadas)
    por_peso = sorted(range(len(jogadas)),
                      key=lambda i: _peso_da_mao(jogadas[i], i))
    return [jogadas[i] for i in sorted(por_peso[:teto])]


def per_hand_analysis_llm(hands_played: list[CanonicalHand],
                          batch: int = 6) -> dict[str, str]:
    """Análise de coach (2-3 frases) POR MÃO jogada, em lotes — usa APENAS os
    números calculados. Sem chave de API, devolve {} e o relatório cai no
    veredito determinístico."""
    import json

    from app.config import get_settings

    settings = get_settings()
    if not settings.anthropic_api_key:
        return {}
    import anthropic

    from app.agent.llm import _create

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    out: dict[str, str] = {}
    for i in range(0, len(hands_played), batch):
        chunk = hands_played[i:i + batch]
        payload = []
        for h in chunk:
            f = played_facts(h)
            a = f["analysis"]
            payload.append({
                "hand_id": h.hand_id,
                "mao": hand_class(h.hero_cards),
                "posicao": a.get("position"),
                "stack_bb": a.get("hero_stack_bb"),
                "efetivo_bb": a.get("effective_bb"),
                "blinds": a.get("blinds"),
                "historia": f["story"],
                "numeros_calculados": f["numbers"],
                "resultado_bb": a.get("net_bb"),
            })
        prompt = (
            "Você é um coach de poker brasileiro, informal e claro, falando com "
            "seu aluno. Para CADA mão abaixo, escreva 2-3 frases em português: "
            "comece pelo veredito em uma frase simples ('Bem jogada', 'Aqui você "
            "pagou caro'), depois o porquê com NO MÁXIMO 1-2 números — use APENAS "
            "os numeros_calculados fornecidos e os stacks dados, nunca invente nem "
            "estime. Fale com 'você', como papo de mesa — nada de soar robótico, "
            "nada de mencionar sistema/dados/análises anteriores e nada de "
            "adjetivar o veredito ('brutal', 'honesto', 'papo reto'). Além do "
            "texto, entregue TAMBÉM: (a) analise_simples — a MESMA ideia para "
            "quem nunca estudou poker: 1-2 frases, uma analogia do dia a dia, "
            "no máximo 1 número explicado; " + _termos() + " (b) o veredito da DECISÃO (independente do resultado!): "
            "'boa' se as decisões foram corretas, 'ruim' se teve erro claro, "
            "'mista' se teve acerto e erro. Responda SOMENTE um JSON "
            '{hand_id: {"analise": str, "analise_simples": str, '
            '"veredito": "boa"|"ruim"|"mista"}}.\n\n'
            + json.dumps(payload, ensure_ascii=False)
        )
        try:
            resp = _create(client,
                model=settings.analysis_model, max_tokens=1800,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = "".join(b.text for b in resp.content if b.type == "text").strip()
            out.update(json.loads(raw[raw.index("{"):raw.rindex("}") + 1]))
        except Exception:
            continue  # lote falhou -> veredito determinístico cobre
    return out


def decision_stamp(h: CanonicalHand, facts: dict) -> str | None:
    """Selo de DECISÃO, independente do resultado — antídoto ao viés de
    resultado (Kahneman): ganhar com decisão ruim continua decisão ruim."""
    a = facts["analysis"]
    measured = bad = False
    for n in facts["numbers"]:
        if "equity_minima" in n and n.get("equity_vs_aleatoria") is not None:
            measured = True
            if n["equity_minima"] - n["equity_vs_aleatoria"] > 0.05:
                bad = True
    stack = a.get("effective_bb")
    if stack and stack <= 20 and any(
            s.get("all_in") and s["street"] == "preflop" for s in a["spots"]):
        from app.analysis.pushfold import push_fold

        pf = push_fold(h.hero_cards, stack, a.get("position") or "MP")
        if pf.get("applicable"):
            measured = True
            if pf["decision"] == "fold":
                bad = True
    if not measured:
        return None
    return "decisão ❌" if bad else "decisão ✅"


def _frase_da_decisao(n: dict) -> str | None:
    """Uma frase para UMA decisão do herói — o verbo vem de `n['acao']`.

    Três regras que o texto antigo quebrava, todas vistas no relatório do
    torneio #303773218:

    - **fold é decisão**: `played_facts` grava a street em que o herói largou
      (com `equity_vs_aleatoria: None` de propósito), e o texto só escrevia a
      linha quando havia equity — a street sumia do relatório. Aqui ela sai com
      o preço que estava na frente e o pote, e SEM veredito: sem equity medida
      não se afirma se largar foi certo (docs/METODO.md).
    - **raise não é call**: `pagou_bb` é o preço de PAGAR. Colado num raise ele
      vira "você pagou 1bb" para quem abriu 2.5bb (a #10 Q♥J♥ do CO) e o
      veredito de preço acusa de call caro quem nem pagou.
    - o veredito de preço ("o preço estava bom") só vale para quem pagou.
    """
    street = n["street"]
    if "equity_minima" not in n:                 # aposta de iniciativa
        pct = n.get("sizing_pct_pote")
        if not pct:
            return None
        tam = ("aposta pequena" if pct < 45 else
               "aposta média" if pct <= 80 else "aposta pesada")
        verbo = "aumentou para" if n.get("acao") == "raise" else "apostou"
        return (f"No {street} você {verbo} {n['valor_bb']:g}bb — "
                f"{pct}% do pote, {tam}")
    req, acao = n["equity_minima"], n.get("acao")
    eq = n.get("equity_vs_aleatoria")
    if acao == "fold":
        return (f"No {street} você largou — na frente tinha um preço que pedia "
                f"{req*100:.0f}% de vitória, com {n['pote_bb']:g}bb no pote; "
                f"sem equity medida, sem veredito")
    if acao != "call":                           # raise sobre a aposta do vilão
        mede = (f"sua mão ganha ~{eq*100:.0f}% contra uma aleatória; "
                if eq is not None else "")
        return (f"No {street} você aumentou (não pagou) — {mede}"
                f"o preço de {req*100:.0f}% julga call, não raise")
    if eq is None:
        return (f"No {street} você pagou {n['pagou_bb']:g}bb — o preço pedia "
                f"{req*100:.0f}% de vitória; sem equity medida, sem veredito")
    ok = ("o preço estava bom" if eq >= req
          else "pagou mais caro do que a mão valia")
    return (f"No {street} você pagou {n['pagou_bb']:g}bb — para esse preço "
            f"precisava ganhar {req*100:.0f}% das vezes, e sua mão ganha "
            f"~{eq*100:.0f}%: {ok}")


def _sob_o_teto(decisoes: list[tuple[float, str]], extras: list[str],
                fecho: str, teto: int) -> list[str]:
    """Corta pela decisão MAIS BARATA até o texto caber em `teto` caracteres.

    Só a imagem tem teto (altura da figura no PDF). Cortar a decisão de menor
    pote é o contrário de cortar por posição: a mão da #7 perdia o preflop
    porque ele era o primeiro, não porque era o menos importante.
    """
    escolhidas = list(decisoes)
    while escolhidas:
        if len(". ".join([f for _, f in escolhidas] + extras + [fecho])) <= teto:
            break
        escolhidas.pop(min(range(len(escolhidas)),
                           key=lambda i: escolhidas[i][0]))
    return [f for _, f in escolhidas] + extras


def played_fallback_verdict(h: CanonicalHand, facts: dict,
                            max_chars: int | None = None) -> str:
    """Análise determinística de mão jogada (usada quando não há texto do coach).

    Cobre TODAS as streets com decisão. O teto antigo era `numbers[:2]`, e nas
    fixtures de `tests/sample_hands` ele jogava fora 23 das 81 decisões (28%),
    em 14 das 41 mãos jogadas — foi a reclamação do dono no torneio
    #303773218: *"analisa só o pre-flop"*.

    `max_chars` (só a imagem usa, com `NOTA_IMG_MAX`): devolve a versão curta,
    com as decisões de maior pote que couberem. O HTML recebe sempre a inteira.
    """
    a = facts["analysis"]
    hc = hand_class(h.hero_cards) or "?"
    decisoes: list[tuple[float, str]] = []
    for n in facts["numbers"]:
        frase = _frase_da_decisao(n)
        if frase:
            decisoes.append((n.get("pote_bb") or 0.0, frase))
    extras: list[str] = []
    stack = a.get("effective_bb")
    pre_jam = any(s.get("all_in") and s["street"] == "preflop" for s in a["spots"])
    if pre_jam and stack and stack <= 20:
        from app.analysis.pushfold import push_fold

        pf = push_fold(h.hero_cards, stack, a.get("position") or "MP")
        if pf.get("applicable"):
            extras.append(
                f"✅ shove certo: com {stack:g}bb, {hc} é all-in lucrativo"
                if pf["decision"] == "push" else
                f"❌ shove exagerado: com {stack:g}bb, {hc} ainda não vale all-in")
    res = f"Saldo da mão: {a['net_bb']:+.1f}bb"
    # o veredito de shove nunca é cortado: é o julgamento da mão inteira
    bits = ([f for _, f in decisoes] + extras if max_chars is None
            else _sob_o_teto(decisoes, extras, res, max_chars))
    return ". ".join(bits + [res]) if bits else f"{hc} — {res.lower()}"


def _hand_strip_img(h: CanonicalHand, seq: int, a: dict,
                    verdict_llm: str | None, analysis: str) -> str:
    """<img> data-URI do storyboard da mão completa. '' se falhar (nunca quebra
    o relatório). Footer = veredito da análise já computada (sem custo novo)."""
    try:
        from app.analysis.hand_figure import render_hand_strip
        from app.bot.processing import hand_storyboard_streets

        bands = hand_storyboard_streets(h)
        if not bands:
            return ""
        note = (analysis or "").strip()
        if len(note) > NOTA_IMG_MAX:     # limita a altura da imagem no PDF
            note = note[:NOTA_IMG_MAX - 3].rstrip() + "…"
        spec = {
            "title": f"Mão #{seq} — {a.get('position') or '?'}",
            "hero_cards": h.hero_cards,
            "position": a.get("position"),
            "stack_bb": a.get("hero_stack_bb"),
            "blinds": a.get("blinds"),
            "streets": bands,
            "math": {},                  # sem decisão única no relatório
            "verdict": verdict_llm or "mista",
            "verdict_text": note,
            "correct": "",
        }
        png = render_hand_strip(spec)
        b64 = base64.standard_b64encode(png).decode()
        return (f"<img class=strip style='width:100%;border-radius:8px;"
                f"margin:10px 0' src='data:image/png;base64,{b64}'>")
    except Exception:
        return ""


def _tabela_auditoria(auditoria: list[dict]) -> str:
    """Seção de AUDITORIA DE ALL-INS: cada decisão de stack curto contra o
    equilíbrio, com o EV em bb. É a conta que o relatório não tinha."""
    if not auditoria:
        return ""
    _NOME = {"open_shove": "abriu de all-in", "reshove": "re-shove sobre open",
             "squeeze": "squeeze", "call_shove": "pagar all-in",
             "overcall": "overcall"}
    linhas = []
    for l in auditoria:
        ok = l["acertou"]
        cor = "#1f7a4d" if ok else "#a8382e"
        marca = "✔" if ok else "✘"
        custo = "" if ok else f" · custou {l['custo_bb']:g}bb"
        vs = f" vs {l['vilao']}" if l.get("vilao") else ""
        linhas.append(
            f"<tr><td><b>{_html.escape(l['mao'])}</b></td>"
            f"<td>{_html.escape(l['posicao'])} · {l['stack_bb']:g}bb</td>"
            f"<td>{_NOME.get(l['spot'], l['spot'])}{_html.escape(vs)}</td>"
            f"<td>{l['voce_fez']}</td>"
            f"<td>{l['equilibrio']} ({l['range_pct']:g}% do range)</td>"
            f"<td style='color:{cor};font-weight:700'>{marca} "
            f"{(l['ev_bb'] or 0):+.2f}bb{custo}</td></tr>")
    erros = [l for l in auditoria if not l["acertou"]]
    total_custo = sum(l["custo_bb"] for l in erros)
    return (
        "<h2>Auditoria de all-ins</h2>"
        "<p class='sub'>Cada decisão de all-in ou fold com stack curto, "
        "resolvida no equilíbrio (mesa de 9, com ante e a ação que veio na "
        "frente). EV em bb contra foldar — cálculo determinístico.</p>"
        f"<p class='sub'><b>{len(auditoria)} decisões · "
        f"{len(auditoria)-len(erros)} no equilíbrio · {len(erros)} fora"
        + (f", custando {total_custo:.1f}bb" if erros else "") + "</b></p>"
        "<table class='audit'><tr><th>Mão</th><th>Spot</th><th>Situação</th>"
        "<th>Você</th><th>Equilíbrio</th><th>EV</th></tr>"
        + "".join(linhas) + "</table>")


def _tabela_pre_deep(linhas: list[dict]) -> str:
    """Pré-flop de stack deep contra o range de REFERÊNCIA (não é solver — o
    rótulo diz, pra não vender tabela como equilíbrio)."""
    if not linhas:
        return ""
    rows = []
    for l in linhas:
        cor = "#1f7a4d" if l["acertou"] else "#a8382e"
        rows.append(
            f"<tr><td><b>{_html.escape(l['mao'])}</b></td>"
            f"<td>{_html.escape(l['posicao'])} · {l['stack_bb']:g}bb</td>"
            f"<td>{_html.escape(l['spot'])}</td><td>{l['voce_fez']}</td>"
            f"<td style='color:{cor};font-weight:700'>"
            f"{'✔' if l['acertou'] else '✘'} referência: {l['referencia']}"
            f"</td></tr>")
    fora = sum(1 for l in linhas if not l["acertou"])
    return ("<h2>Pré-flop de stack deep</h2>"
            "<p class='sub'>Comparado ao range de <b>referência</b> da posição "
            "— não é equilíbrio resolvido; é a tabela padrão, que serve de "
            "régua e não de lei.</p>"
            f"<p class='sub'><b>{len(linhas)} decisões · {len(linhas)-fora} "
            f"dentro da referência</b></p>"
            "<table class='audit'><tr><th>Mão</th><th>Spot</th>"
            "<th>Situação</th><th>Você</th><th>Referência</th></tr>"
            + "".join(rows) + "</table>")


def _tabela_posflop(linhas: list[dict]) -> str:
    """Pós-flop resolvido no CFR+ (só os maiores potes — custo de CPU)."""
    if not linhas:
        return ""
    rows = []
    for l in linhas:
        cor = "#1f7a4d" if l["acertou"] else "#a8382e"
        rows.append(
            f"<tr><td><b>{_html.escape(l['mao'])}</b></td>"
            f"<td>{_html.escape(l['street'])} · {_html.escape(l['board'])}</td>"
            f"<td>{l['pot_bb']:g}bb</td><td>{l['voce_fez']}</td>"
            f"<td>{_html.escape(l['equilibrio'])} "
            f"({l['freq_equilibrio_pct']}% aposta)</td>"
            f"<td style='color:{cor};font-weight:700'>"
            f"{'✔' if l['acertou'] else '✘'}</td></tr>")
    return ("<h2>Pós-flop — equilíbrio dos potes maiores</h2>"
            "<p class='sub'>CFR+ range vs range nas decisões de "
            "<b>iniciativa</b> (apostar ou dar check) dos maiores potes. "
            "Entre 30% e 70% o equilíbrio joga MISTO — as duas ações estão "
            "certas. Ranges do vilão estimados; cada spot custa segundos de "
            "CPU, por isso só os maiores.</p>"
            "<table class='audit'><tr><th>Mão</th><th>Street</th>"
            "<th>Pote</th><th>Você</th><th>Equilíbrio</th><th></th></tr>"
            + "".join(rows) + "</table>")



def _tabela_faixas(hands: list) -> str:
    """ONDE O EV FOI EMBORA, por profundidade de stack.

    Vem antes das auditorias de propósito: as tabelas de all-in e pós-flop
    listam spots, e o aluno se perde na lista sem saber por onde começar.
    Esta responde "por onde começar" com número.
    """
    try:
        from app.analysis.estrategia_torneio import onde_doi_mais, por_faixa

        linhas = por_faixa(hands)
    except Exception:
        return ""
    if not linhas:
        return ""
    esc = _html.escape
    tr = []
    for l in linhas:
        lado = l.direcao_confiavel
        obs = (f"{l.direcao[lado]} para o mesmo lado: {lado} demais"
               if lado else ("—" if l.erros else "nenhum erro"))
        tr.append(
            f"<tr><td><b>{esc(l.faixa)}</b><br>"
            f"<span style='color:#828A84;font-size:11px'>{esc(l.o_que_muda)}"
            f"</span></td>"
            f"<td class=n>{l.maos}</td><td class=n>{l.spots}</td>"
            f"<td class=n>{l.erros}</td>"
            f"<td class=n>{l.ev_perdido_bb:.1f}</td>"
            f"<td>{esc(obs)}</td></tr>")
    pior = onde_doi_mais(linhas)
    remate = (f"<p style='margin:6px 0 0'>A faixa que mais custou foi "
              f"<b>{esc(pior.faixa)}</b>: {pior.ev_perdido_bb:.1f}bb.</p>"
              if pior else "")
    return ("<h2>Onde o EV foi embora — por profundidade de stack</h2>"
            "<p style='color:#828A84;font-size:11.5px;margin:2px 0 8px'>"
            "Cada spot auditável tem resposta certa, então a conta de EV vale "
            "mesmo com poucas mãos na faixa. O que NÃO sai daqui é frequência "
            "(&ldquo;você joga X% nesta faixa&rdquo;) — isso precisaria de 60+ "
            "mãos <i>na faixa</i>.</p>"
            "<table class=audit><tr><th>Faixa (stack efetivo)</th><th>Mãos</th>"
            "<th>Spots</th><th>Erros</th><th>EV perdido (bb)</th>"
            "<th>Direção</th></tr>"
            + "".join(tr) + "</table>" + remate)


def build_report_html(hands: list[CanonicalHand], coach_text: str = "",
                      board_png: bytes | None = None,
                      per_hand_analysis: dict[str, str] | None = None,
                      auditoria: list[dict] | None = None,
                      pre_deep: list[dict] | None = None,
                      posflop: list[dict] | None = None) -> str:
    """`per_hand_analysis`: hand_id -> análise do coach (mãos jogadas).
    `auditoria`: saída de allin_audit.auditar_allins (seção de all-ins)."""
    hands = sorted(hands, key=lambda h: h.played_at or "")
    per_hand_analysis = per_hand_analysis or {}
    from app.analysis.tournament_board import tournament_summary

    s = tournament_summary(hands)
    esc = _html.escape

    def ident(i: int, h: CanonicalHand, a: dict) -> tuple[str, str, str]:
        hora = (h.played_at or "")[11:16]
        return (f"#{i}", f"{h.hand_id}", f"{hora} · blinds {a['blinds']}")

    played_cards, fold_rows = [], []
    seq = 0
    for h in hands:
        seq += 1
        try:
            a = analyze_hand(h)
        except Exception:
            continue
        n_lab, hid, meta = ident(seq, h, a)
        if _played(h):
            facts = played_facts(h)
            entry = per_hand_analysis.get(h.hand_id)
            verdict_llm = simple = None
            if isinstance(entry, dict):
                verdict_llm = entry.get("veredito")
                simple = (entry.get("analise_simples") or "").strip()
                entry = entry.get("analise")
            analysis = entry or played_fallback_verdict(h, facts)
            story = "<br>".join(esc(x) for x in facts["story"])
            net = a["net_bb"]
            color = "#2E7D5B" if net > 0 else ("#C0564A" if net < 0 else "#828A84")
            # selo vem do MESMO veredito que assina a análise — nunca mais
            # "decisão ✅" em cima e "jogou passivo demais" embaixo
            stamp = {"boa": "decisão ✅", "ruim": "decisão ❌",
                     "mista": "decisão ⚠️"}.get(verdict_llm or "") or \
                decision_stamp(h, facts)
            dec_html = f"<span class=dec>{esc(stamp)}</span>" if stamp else ""
            # storyboard da mão completa (o filme) — determinístico, custo zero
            # de LLM. Reaproveita o veredito da análise já computada no rodapé.
            # Só para mãos JOGADAS (as foldadas ficam na tabela): PDF não incha.
            # A imagem tem altura limitada (NOTA_IMG_MAX) e o texto agora vai
            # street por street: sem uma versão curta, quase toda mão viraria
            # "…" na figura. O HTML fica com a mão inteira; a figura, com as
            # decisões de maior pote que cabem.
            nota_img = entry or played_fallback_verdict(
                h, facts, max_chars=NOTA_IMG_MAX)
            strip_img = _hand_strip_img(h, seq, a, verdict_llm, nota_img)
            story_html = "" if strip_img else f"<div class=story>{story}</div>"
            # HONESTIDADE ENTRE DUAS CLASSES DE TEXTO. Acima de
            # TETO_MAOS_COACHED mãos jogadas, só as principais recebem o texto
            # do coach; as outras ficam no veredito determinístico, que é um
            # resumo mecânico das contas. Sem esta linha o aluno lê os dois
            # como se fossem a mesma coisa — e o resumo, que nunca julga a
            # jogada, passa por análise de coach que decidiu não julgar.
            auto_html = "" if entry else (
                "<div class=auto>📝 resumo automático (só as contas da mão) — "
                "para a análise completa desta, me manda o Nº dela no "
                "chat.</div>")
            played_cards.append(f"""
<div class=hand>
  <div class=hh><span class=seq>{n_lab}</span> {_cards_html(h.hero_cards)}
  <span class=pos>{esc(a.get('position') or '?')}</span>
  <span class=meta>mão {esc(hid)} · {esc(meta)} · stack {a.get('hero_stack_bb') or '?'}bb
  (efetivo {a.get('effective_bb') or '?'}bb)</span>
  {dec_html}<span class=net style='color:{color}'>{net:+.1f} BB</span></div>
  {strip_img}{story_html}
  <div class=an><b>Análise:</b> {esc(analysis)}</div>
  {f'<details class=simple><summary>🎈 Explica mais simples</summary><p>{esc(simple)}</p></details>' if simple else ''}
  {auto_html}
</div>""")
        else:
            verdict = fold_verdict(h, a)
            fold_rows.append(
                f"<tr><td class=n>{n_lab}</td>"
                f"<td class=n>{esc(hid)}</td>"
                f"<td class=n>{esc((h.played_at or '')[11:16])}</td>"
                f"<td>{_cards_html(h.hero_cards)}</td>"
                f"<td>{esc(a.get('position') or '?')}</td>"
                f"<td class=n>{a.get('hero_stack_bb') or '?'}</td>"
                f"<td>{esc(verdict)}</td></tr>"
            )

    board_img = ""
    if board_png:
        b64 = base64.standard_b64encode(board_png).decode()
        board_img = (f"<img style='width:100%;border-radius:10px;margin:14px 0' "
                     f"src='data:image/png;base64,{b64}'>")
    coach_html = ""
    if coach_text:
        coach_html = ("<div class=coach><h2>🎓 Leitura do coach — seus padrões</h2>"
                      f"<p>{esc(coach_text).replace(chr(10), '<br>')}</p></div>")

    css = """
    body{font-family:'Segoe UI',system-ui,sans-serif;font-size:13px;color:#1B211D;
    margin:26px;line-height:1.5;max-width:980px}
    h1{font-size:22px;margin:0 0 2px} h2{font-size:16px;color:#2E7D5B;margin:24px 0 10px}
    .sub{color:#828A84;font-size:12px;margin-bottom:12px}
    .kpis{display:flex;gap:10px;margin:12px 0;flex-wrap:wrap}
    .kpi{border:1px solid #DDE3DE;border-top:3px solid #2E7D5B;border-radius:8px;
    padding:8px 14px} .kpi b{display:block;font-size:19px}
    .kpi span{font-size:10.5px;color:#828A84;text-transform:uppercase}
    .coach{border:1px solid #D2A55C;border-radius:10px;background:#FBF6EC;
    padding:4px 16px 10px;margin:16px 0}
    .hand{border:1px solid #DDE3DE;border-left:4px solid #2E7D5B;border-radius:8px;
    padding:10px 14px;margin:10px 0;page-break-inside:avoid}
    .hh{font-size:14px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
    .seq{font-weight:800;color:#A67E35}
    .pos{background:#F0F4F1;border-radius:6px;padding:1px 8px;font-size:11px;font-weight:700}
    .meta{color:#828A84;font-size:11px}
    .net{margin-left:auto;font-weight:800;font-size:14px}
    .dec{font-size:11px;font-weight:700;background:#F0F4F1;border-radius:6px;
    padding:1px 8px}
    .story{font-family:ui-monospace,Consolas,monospace;font-size:11px;color:#4A554E;
    background:#F7F9F7;border-radius:6px;padding:8px 10px;margin:8px 0}
    .an{font-size:12.5px}
    .auto{font-size:10.5px;color:#828A84;margin-top:6px;font-style:italic}
    .simple{margin-top:6px}
    .simple summary{cursor:pointer;font-size:11.5px;font-weight:700;color:#2E7D5B}
    .simple p{font-size:12.5px;background:#F0F7F2;border-radius:6px;
    padding:8px 10px;margin:6px 0 0}
    table{border-collapse:collapse;width:100%;font-size:11.5px}
    th{background:#F0F4F1;color:#5A665E;text-align:left;padding:6px 8px;font-size:10px;
    text-transform:uppercase}
    td{padding:5px 8px;border-bottom:1px solid #E8ECE8;vertical-align:top}
    td.n{font-variant-numeric:tabular-nums;white-space:nowrap;color:#5A665E}
    .foot{color:#828A84;font-size:11px;margin-top:18px}
    """
    buyin = f" · buy-in ${s['buyin']:g}" if s.get("buyin") else ""
    return f"""<!doctype html><html lang=pt-BR><head><meta charset=utf-8>
<title>Mão a mão — Torneio #{s['tournament_id']}</title><style>{css}table.audit td,table.audit th{{font-size:12px;padding:5px 8px}}table.audit th{{background:#16211A;color:#D0A85C}}table.audit tr:nth-child(even){{background:#F7F9F7}}</style></head><body>
<h1>♠ Análise mão a mão — Torneio #{s['tournament_id']}</h1>
<div class=sub>{s['site']}{buyin} · níveis {esc(str(s['levels']))} ·
{s['hands']} mãos · cada mão identificada pelo Nº da sala (confira no PokerCraft/HM)</div>
<div class=kpis>
  <div class=kpi><b>{s['hands']}</b><span>mãos</span></div>
  <div class=kpi><b>{s['net_bb']:+.1f}</b><span>resultado (BB)</span></div>
  <div class=kpi><b>{s['vpip_pct']:.0f}%</b><span>VPIP no torneio</span></div>
  <div class=kpi><b>{s['allins']}</b><span>all-ins</span></div>
  <div class=kpi><b>{len(played_cards)}</b><span>mãos jogadas</span></div>
</div>
{board_img}
{coach_html}
{_tabela_faixas(hands)}
{_tabela_auditoria(auditoria or [])}
{_tabela_pre_deep(pre_deep or [])}
{_tabela_posflop(posflop or [])}
<h2>🃏 Mãos jogadas — análise completa ({len(played_cards)})</h2>
<p style='color:#828A84;font-size:11.5px;margin:2px 0 8px'>O selo de
<b>decisão</b> julga o preço na hora, não o desfecho — ganhar com decisão
ruim continua ruim, e perder com decisão boa é só variância.</p>
{''.join(played_cards) or '<p>nenhuma mão jogada voluntariamente neste lote.</p>'}
<h2>🚫 Mãos que você largou no pré-flop ({len(fold_rows)})</h2>
<table><tr><th>#</th><th>Nº da mão</th><th>Hora</th><th>Cartas</th><th>Pos</th>
<th>Stack (bb)</th><th>Veredito</th></tr>
{''.join(fold_rows)}</table>
<div class=foot>Quer abrir qualquer mão dessas? Me manda o Nº dela (ou as cartas)
no chat que a gente destrincha juntos. · KKNuths ♠ t.me/KKNUts_BOT</div>
</body></html>"""
