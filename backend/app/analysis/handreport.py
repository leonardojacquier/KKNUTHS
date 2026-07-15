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


def played_fallback_verdict(h: CanonicalHand, facts: dict) -> str:
    """Análise determinística de mão jogada (usada quando não há texto do coach)."""
    a = facts["analysis"]
    hc = hand_class(h.hero_cards) or "?"
    bits = []
    for n in facts["numbers"][:2]:
        if "equity_minima" in n:
            eq, req = n.get("equity_vs_aleatoria"), n["equity_minima"]
            if eq is not None:
                ok = ("o preço estava bom" if eq >= req
                      else "pagou mais caro do que a mão valia")
                bits.append(
                    f"No {n['street']} você pagou {n['pagou_bb']:g}bb — para esse "
                    f"preço precisava ganhar {req*100:.0f}% das vezes, e sua mão "
                    f"ganha ~{eq*100:.0f}%: {ok}")
        elif n.get("sizing_pct_pote"):
            pct = n["sizing_pct_pote"]
            tam = ("aposta pequena" if pct < 45 else
                   "aposta média" if pct <= 80 else "aposta pesada")
            bits.append(f"No {n['street']} você apostou {n['valor_bb']:g}bb — "
                        f"{pct}% do pote, {tam}")
    stack = a.get("effective_bb")
    pre_jam = any(s.get("all_in") and s["street"] == "preflop" for s in a["spots"])
    if pre_jam and stack and stack <= 20:
        from app.analysis.pushfold import push_fold

        pf = push_fold(h.hero_cards, stack, a.get("position") or "MP")
        if pf.get("applicable"):
            bits.append(
                f"✅ shove certo: com {stack:g}bb, {hc} é all-in lucrativo"
                if pf["decision"] == "push" else
                f"❌ shove exagerado: com {stack:g}bb, {hc} ainda não vale all-in")
    res = f"Saldo da mão: {a['net_bb']:+.1f}bb"
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
        if len(note) > 260:              # limita a altura da imagem no PDF
            note = note[:257].rstrip() + "…"
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


def build_report_html(hands: list[CanonicalHand], coach_text: str = "",
                      board_png: bytes | None = None,
                      per_hand_analysis: dict[str, str] | None = None) -> str:
    """`per_hand_analysis`: hand_id -> análise do coach (mãos jogadas)."""
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
            strip_img = _hand_strip_img(h, seq, a, verdict_llm, analysis)
            story_html = "" if strip_img else f"<div class=story>{story}</div>"
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
<title>Mão a mão — Torneio #{s['tournament_id']}</title><style>{css}</style></head><body>
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
