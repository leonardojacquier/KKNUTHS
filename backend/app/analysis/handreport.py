"""Relatório MÃO A MÃO de um torneio — o dossiê completo, em HTML.

Uma linha por mão (cartas, posição, stacks em BB, linha do herói, pote,
resultado) com veredito determinístico nos spots de jam/fold curtos (Nash) e
destaques nos momentos-chave. Autossuficiente (CSS inline, board embutido) —
pronto para o bot enviar como documento no Telegram.
"""
from __future__ import annotations

import base64
import html as _html

from app.agent.analyzer import analyze_hand
from app.analysis.handsearch import _hero_line
from app.models.canonical import CanonicalHand

_SYM = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
_RED = {"h", "d"}


def _cards_html(cards: list[str]) -> str:
    out = []
    for c in cards or []:
        if len(c) != 2:
            continue
        color = "#C0564A" if c[1] in _RED else "#1B211D"
        out.append(f"<b style='color:{color}'>{c[0]}{_SYM.get(c[1], c[1])}</b>")
    return " ".join(out) or "—"


def _verdict(h: CanonicalHand, a: dict) -> str:
    """Veredito determinístico quando a teoria tem resposta clara."""
    stack = a.get("effective_bb") or a.get("hero_stack_bb")
    pre_allin = any(
        s.get("all_in") and s["street"] == "preflop" for s in a["spots"]
    )
    if pre_allin and stack and stack <= 20 and a["format"] in ("tournament", "sng"):
        from app.analysis.pushfold import push_fold

        pf = push_fold(h.hero_cards, stack, a.get("position") or "MP")
        if pf.get("applicable"):
            ok = pf["decision"] == "push"
            icon = "✅" if ok else "❌"
            return (f"{icon} jam de {stack:g}bb efetivos — equilíbrio diz "
                    f"{pf['decision'].upper()} (mão no top {pf['hand_top_pct']}%, "
                    f"range ≈{pf['shove_range_pct']}%)")
    if any(s.get("all_in") for s in a["spots"]):
        return "⚔️ all-in — pergunte ao coach para abrir este spot"
    if abs(a["net_bb"]) >= 15:
        return "💥 pote decisivo"
    return ""


def build_report_html(hands: list[CanonicalHand], coach_text: str = "",
                      board_png: bytes | None = None) -> str:
    hands = sorted(hands, key=lambda h: h.played_at or "")
    from app.analysis.tournament_board import tournament_summary

    s = tournament_summary(hands)
    esc = _html.escape

    rows = []
    for i, h in enumerate(hands, 1):
        try:
            a = analyze_hand(h)
        except Exception:
            continue
        line = " → ".join(
            f"{st}: {v}" + (f" {amt:g}bb" if amt else "")
            for st, v, amt in _hero_line(h)
        ) or "fold sem ação"
        net = a["net_bb"]
        color = "#2E7D5B" if net > 0 else ("#C0564A" if net < 0 else "#828A84")
        verdict = _verdict(h, a)
        big = abs(net) >= 15 or any(sp.get("all_in") for sp in a["spots"])
        rows.append(
            f"<tr{' class=hot' if big else ''}>"
            f"<td class=n>{i}</td>"
            f"<td>{_cards_html(h.hero_cards)}</td>"
            f"<td>{esc(a.get('position') or '?')}</td>"
            f"<td class=n>{a.get('hero_stack_bb') or '?'}"
            f"<span class=mut>/{a.get('effective_bb') or '?'}ef</span></td>"
            f"<td class=line>{esc(line)}</td>"
            f"<td>{_cards_html(h.final_board)}</td>"
            f"<td class=n style='color:{color};font-weight:700'>{net:+.1f}</td>"
            f"<td class=vd>{esc(verdict)}</td></tr>"
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
    margin:26px;line-height:1.5}
    h1{font-size:22px;margin:0 0 2px} h2{font-size:15px;color:#2E7D5B;margin:20px 0 8px}
    .sub{color:#828A84;font-size:12px;margin-bottom:12px}
    .kpis{display:flex;gap:10px;margin:12px 0}
    .kpi{border:1px solid #DDE3DE;border-top:3px solid #2E7D5B;border-radius:8px;
    padding:8px 14px} .kpi b{display:block;font-size:19px}
    .kpi span{font-size:10.5px;color:#828A84;text-transform:uppercase}
    table{border-collapse:collapse;width:100%;font-size:11.5px}
    th{background:#F0F4F1;color:#5A665E;text-align:left;padding:6px 8px;font-size:10px;
    text-transform:uppercase;position:sticky;top:0}
    td{padding:5px 8px;border-bottom:1px solid #E8ECE8;vertical-align:top}
    td.n{font-variant-numeric:tabular-nums;white-space:nowrap}
    td.line{max-width:270px} td.vd{max-width:220px;font-size:11px}
    .mut{color:#9AA69F;font-size:10px} tr.hot{background:#FBF6EC}
    .coach{border:1px solid #D2A55C;border-radius:10px;background:#FBF6EC;
    padding:4px 16px 10px;margin:16px 0}
    .foot{color:#828A84;font-size:11px;margin-top:18px}
    """
    buyin = f" · buy-in ${s['buyin']:g}" if s.get("buyin") else ""
    return f"""<!doctype html><html lang=pt-BR><head><meta charset=utf-8>
<title>Mão a mão — Torneio #{s['tournament_id']}</title><style>{css}</style></head><body>
<h1>♠ Análise mão a mão — Torneio #{s['tournament_id']}</h1>
<div class=sub>{s['site']}{buyin} · níveis {esc(str(s['levels']))} · relatório KKNuths</div>
<div class=kpis>
  <div class=kpi><b>{s['hands']}</b><span>mãos</span></div>
  <div class=kpi><b>{s['net_bb']:+.1f}</b><span>resultado (BB)</span></div>
  <div class=kpi><b>{s['vpip_pct']:.0f}%</b><span>VPIP no torneio</span></div>
  <div class=kpi><b>{s['allins']}</b><span>all-ins</span></div>
</div>
{board_img}
{coach_html}
<h2>Mão a mão ({s['hands']} mãos — stacks em BB; “ef” = efetivo)</h2>
<table><tr><th>#</th><th>Cartas</th><th>Pos</th><th>Stack/ef</th>
<th>Sua linha</th><th>Board</th><th>BB</th><th>Veredito</th></tr>
{''.join(rows)}</table>
<div class=foot>Linhas destacadas = potes decisivos/all-ins. Vereditos automáticos
apenas onde a teoria é inequívoca (jam/fold curto vs equilíbrio) — para qualquer
mão, pergunte no chat: “abre a mão #N do relatório”. · KKNuths ♠ t.me/KKNUts_BOT</div>
</body></html>"""
