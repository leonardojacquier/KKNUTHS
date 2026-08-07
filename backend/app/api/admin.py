"""Portal de gestão — performance do produto e dos jogadores.

Servido pela própria API (uvicorn/pm2), protegido por ADMIN_TOKEN.
Lê tudo do Supabase via service role; se o banco estiver indisponível,
renderiza com zeros em vez de quebrar.

Acesso:  GET /admin?key=<ADMIN_TOKEN>
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.db import get_repository

router = APIRouter()

_ERROR_EVENTS = ("upload_failed", "error", "entrega_falha",
                 "sem_mao_na_conversa")
# o que conta como MÃO enviada (funil por usuário)
_MAO_EVENTS = ("upload", "print_recebido", "upload_recebido",
               "replay_pppoker", "replay_suprema")


def _q(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _detalhe(r) -> dict:
    d = r.get("detail") or {}
    if isinstance(d, str):
        try:
            d = json.loads(d)
        except Exception:
            return {}
    return d if isinstance(d, dict) else {}


def somar_custos(events: list[dict], month_start: str) -> dict:
    """Custo de LLM a partir dos eventos custo_llm (função pura).

    Devolve mes/hoje em US$, por tarefa e por telegram_id — a régua que
    decide preço, que o dono hoje só via pelo /quem no Telegram."""
    agora = datetime.now(timezone.utc)
    hoje = agora.date().isoformat()
    mes = dia = 0.0
    por_tarefa: dict[str, float] = defaultdict(float)
    por_tg: dict[int, float] = defaultdict(float)
    for r in events:
        if r.get("event") != "custo_llm":
            continue
        d = _detalhe(r)
        usd = d.get("usd")
        if not isinstance(usd, (int, float)):
            continue
        ts = str(r.get("created_at") or "")
        if ts >= month_start:
            mes += usd
            por_tarefa[str(d.get("tarefa") or "outro")] += usd
            tg = r.get("telegram_id")
            if isinstance(tg, int) and tg > 0:
                por_tg[tg] += usd
        if ts[:10] == hoje:
            dia += usd
    return {"mes": round(mes, 2), "hoje": round(dia, 2),
            "por_tarefa": dict(sorted(por_tarefa.items(),
                                      key=lambda kv: -kv[1])),
            "por_tg": dict(por_tg)}


def _collect() -> dict:
    """Métricas do produto (consultas leves; tolerantes a falha)."""
    repo = get_repository()
    if not repo.enabled:
        return {"db": False}
    c = repo.client
    now = datetime.now(timezone.utc)
    d7 = (now - timedelta(days=7)).isoformat()
    d14 = (now - timedelta(days=14)).isoformat()
    d30 = (now - timedelta(days=30)).isoformat()
    month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()

    users = _q(lambda: c.table("users")
               .select("id, telegram_id, username, plan, created_at")
               .order("created_at", desc=True).limit(200).execute().data, []) or []
    hands = _q(lambda: c.table("hands").select("id", count="exact").execute().count, 0)
    analyses30 = _q(
        lambda: c.table("hand_analysis").select("id", count="exact")
        .gte("created_at", d30).execute().count, 0)

    # eventos dos últimos 30 dias: alimentam acessos, atividade diária,
    # métricas por usuário e a seção de erros
    events = _q(lambda: c.table("bot_events")
                .select("telegram_id, username, event, detail, created_at")
                .gte("created_at", d30)
                .order("created_at", desc=True).limit(5000).execute().data, []) or []

    per_user: dict[int, dict] = defaultdict(
        lambda: {"eventos": 0, "maos": 0, "perguntas": 0, "drills": 0,
                 "erros": 0, "ultimo": "", "ref": ""})
    daily: dict[str, dict] = defaultdict(lambda: {"eventos": 0, "usuarios": set()})
    by_type: dict[str, int] = defaultdict(int)
    refs: dict[str, int] = defaultdict(int)
    entrega = {"ok": 0, "falha": 0, "remediada": 0}
    errors: list[dict] = []
    active7: set[int] = set()
    juiz: dict | None = None

    for r in events:
        tg = r.get("telegram_id")
        ev = r.get("event") or "?"
        ts = str(r.get("created_at") or "")
        by_type[ev] += 1
        if ev == "entrega_ok":
            entrega["ok"] += 1
        elif ev == "entrega_falha":
            entrega["falha"] += 1
        elif ev == "entrega_remediada":
            entrega["remediada"] += 1
        if ev == "output_judge" and juiz is None:  # events vêm desc: 1º = último
            juiz = _detalhe(r)
        if isinstance(tg, int) and tg > 0:
            u = per_user[tg]
            u["eventos"] += 1
            u["ultimo"] = max(u["ultimo"], ts)
            if ev in _MAO_EVENTS:
                u["maos"] += 1
            if ev == "followup":
                u["perguntas"] += 1
            if ev == "drill_answer":
                u["drills"] += 1
            if ev in _ERROR_EVENTS:
                u["erros"] += 1
            if ev == "start":
                origem = str(_detalhe(r).get("ref") or "") or "direto"
                u["ref"] = u["ref"] or origem
                refs[origem] += 1
            if ts >= d7:
                active7.add(tg)
            day = ts[:10]
            if day:
                daily[day]["eventos"] += 1
                daily[day]["usuarios"].add(tg)
        if ev in _ERROR_EVENTS:
            errors.append(r)

    custos = somar_custos(events, month_start)

    # análises usadas no mês por usuário (cota)
    usage = _q(lambda: c.table("usage_events").select("user_id")
               .gte("created_at", month_start).limit(5000).execute().data, []) or []
    used_by_uid: dict[str, int] = defaultdict(int)
    for r in usage:
        used_by_uid[r.get("user_id")] += 1

    recent = events[:25]
    profiles = _q(lambda: c.table("player_stats")
                  .select("user_id, hands, vpip, pfr, three_bet, af, label, updated_at")
                  .order("updated_at", desc=True).limit(20).execute().data, []) or []

    licoes = _q(lambda: c.table("licoes")
                .select("id,titulo,categoria,ev_bb,publicada")
                .order("id", desc=True).limit(50).execute().data, []) or []

    # nome em TODA linha: users é a fonte da verdade (o username do
    # bot_events falta em evento antigo/de sistema — era por isso que o
    # portal mostrava IDs crus)
    nome_por_tg = {u["telegram_id"]: (u.get("username") or str(u["telegram_id"]))
                   for u in users if u.get("telegram_id")}
    nome_por_uid = {u["id"]: (u.get("username") or str(u.get("telegram_id")))
                    for u in users}

    days = []
    for i in range(13, -1, -1):
        d = (now - timedelta(days=i)).date().isoformat()
        info = daily.get(d, {"eventos": 0, "usuarios": set()})
        days.append({"dia": d, "eventos": info["eventos"], "usuarios": len(info["usuarios"])})

    new7 = sum(1 for u in users if str(u.get("created_at") or "") >= d7)

    return {
        "db": True, "users": users, "hands": hands, "analyses30": analyses30,
        "active7": len(active7), "new7": new7, "by_type": dict(by_type),
        "per_user": dict(per_user), "used_by_uid": dict(used_by_uid),
        "errors": errors[:30], "errors30": len(errors), "days": days,
        "recent": recent, "profiles": profiles, "d14": d14,
        "custos": custos, "entrega": entrega, "refs": dict(refs),
        "juiz": juiz or {}, "licoes": licoes,
        "nome_por_tg": nome_por_tg, "nome_por_uid": nome_por_uid,
    }


_CSS = """
:root{--bg:#121714;--card:#181F1B;--ink:#E8ECE8;--mut:#96A09A;--felt:#43A97C;
--gold:#D2A55C;--red:#C0564A;--line:#28312B}
body{background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;
margin:0;padding:24px;font-size:15px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--mut);margin:0 0 24px;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:28px}
.kpi{background:var(--card);border:1px solid var(--line);border-top:3px solid var(--felt);padding:14px}
.kpi.err{border-top-color:var(--red)}
.kpi b{display:block;font-size:26px;color:var(--gold);font-variant-numeric:tabular-nums}
.kpi.err b{color:var(--red)}
.kpi span{font-size:12px;color:var(--mut)}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--felt);
margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--card)}
th{color:var(--mut);text-align:left;padding:8px 12px;font-size:11.5px;
text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--line)}
td{padding:8px 12px;border-bottom:1px solid var(--line)}
td.n{font-variant-numeric:tabular-nums;font-family:ui-monospace,monospace}
td.err{color:var(--red)}
.wrap{max-width:1080px;margin:0 auto}
.tbl{overflow-x:auto;border:1px solid var(--line)}
.warn{background:#3a2a12;border:1px solid var(--gold);padding:12px;margin-bottom:20px}
.bars{display:flex;align-items:flex-end;gap:4px;height:90px;background:var(--card);
border:1px solid var(--line);padding:12px}
.bar{flex:1;background:var(--felt);min-height:2px;position:relative}
.bar i{position:absolute;bottom:-20px;left:0;right:0;text-align:center;font-size:9px;
color:var(--mut);font-style:normal}
.bar b{position:absolute;top:-16px;left:0;right:0;text-align:center;font-size:10px;
color:var(--gold)}
.bwrap{padding-bottom:26px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:700px){.cols{grid-template-columns:1fr}}
a{color:var(--felt);text-decoration:none;border-bottom:1px dotted var(--felt)}
a:hover{color:var(--gold);border-bottom-color:var(--gold)}
.volta{display:inline-block;margin-bottom:14px;font-size:13px}
.sel{font-weight:600}
.ok{color:var(--felt)}.mid{color:var(--gold)}.bad{color:var(--red)}
.nota{background:var(--card);border-left:3px solid var(--gold);
padding:8px 12px;margin:6px 0;font-size:13px}
"""


def _linha_do_veredito(summary: str) -> tuple[str, str]:
    """(classe css, 1ª linha) — o selo já é o resumo da análise."""
    linha = (summary or "").strip().split("\n", 1)[0][:110]
    cls = ("ok" if linha.startswith("✅") else
           "bad" if linha.startswith("❌") else
           "mid" if linha.startswith("🟡") else "")
    return cls, linha


def _dossie(tg: int) -> dict:
    """Tudo que se sabe sobre UMA pessoa (tolerante a falha, como o resto)."""
    repo = get_repository()
    if not repo.enabled:
        return {"db": False}
    c = repo.client
    u = (_q(lambda: c.table("users").select("*")
            .eq("telegram_id", tg).limit(1).execute().data, []) or [None])[0]
    if not u:
        return {"db": True, "achou": False}

    eventos = _q(lambda: c.table("bot_events")
                 .select("event,detail,created_at").eq("telegram_id", tg)
                 .order("created_at", desc=True).limit(300).execute().data,
                 []) or []
    maos = _q(lambda: c.table("hands")
              .select("id,hand_id,site,format,canonical,created_at")
              .eq("user_id", u["id"])
              .order("created_at", desc=True).limit(25).execute().data,
              []) or []
    ids = [m["id"] for m in maos]
    analises = _q(lambda: c.table("hand_analysis")
                  .select("hand_id,summary,ev_loss,modelo,created_at")
                  .in_("hand_id", ids).execute().data, []) if ids else []
    por_mao = {}
    for a in (analises or []):
        por_mao.setdefault(a["hand_id"], a)
    notas = _q(lambda: repo.get_notes(u["id"], limit=10), []) or []
    perfil = (_q(lambda: c.table("player_stats").select("*")
               .eq("user_id", u["id"]).limit(1).execute().data, [])
              or [None])[0]

    agg = {"eventos": len(eventos), "maos": 0, "perguntas": 0, "drills": 0,
           "erros": 0, "custo": 0.0, "ref": "", "quiz": 0}
    dias: dict[str, int] = defaultdict(int)
    for e in eventos:
        ev = e.get("event") or ""
        ts = str(e.get("created_at") or "")
        if ev in _MAO_EVENTS:
            agg["maos"] += 1
        elif ev == "followup":
            agg["perguntas"] += 1
        elif ev == "drill_answer":
            agg["drills"] += 1
        elif ev == "daily_quiz_sent":
            agg["quiz"] += 1
        elif ev == "custo_llm":
            usd = _detalhe(e).get("usd")
            if isinstance(usd, (int, float)):
                agg["custo"] += usd
        if ev in _ERROR_EVENTS:
            agg["erros"] += 1
        if ev == "start" and not agg["ref"]:
            agg["ref"] = str(_detalhe(e).get("ref") or "direto")
        if ts and ev != "daily_quiz_sent":
            dias[ts[:10]] += 1
    return {"db": True, "achou": True, "u": u, "eventos": eventos,
            "maos": maos, "por_mao": por_mao, "notas": notas,
            "perfil": perfil, "agg": agg, "dias": dias}


@router.get("/admin/usuario", response_class=HTMLResponse)
async def admin_usuario(key: str = Query(default=""),
                        tg: int = Query(default=0)) -> str:
    settings = get_settings()
    if not settings.admin_token or key != settings.admin_token:
        raise HTTPException(status_code=401, detail="token inválido")
    esc = html.escape
    d = _dossie(tg)
    volta = f"<a class='volta' href='/admin?key={esc(key)}'>← voltar</a>"
    if not d.get("db"):
        return (f"<style>{_CSS}</style><div class='wrap'>{volta}"
                "<div class='warn'>Banco indisponível.</div></div>")
    if not d.get("achou"):
        return (f"<style>{_CSS}</style><div class='wrap'>{volta}"
                f"<div class='warn'>Não achei o usuário {tg}.</div></div>")

    u, agg = d["u"], d["agg"]
    nome = esc(str(u.get("username") or tg))

    # atividade por dia (14 dias) — o retrato do hábito
    hoje = datetime.now(timezone.utc).date()
    barras = []
    maxd = max(list(d["dias"].values()) + [1])
    for i in range(13, -1, -1):
        dia = (hoje - timedelta(days=i)).isoformat()
        n = d["dias"].get(dia, 0)
        barras.append(
            f"<div class='bar' style='height:{max(2, int(86 * n / maxd))}px'>"
            f"<b>{n or ''}</b><i>{dia[5:]}</i></div>")

    mao_rows = []
    for m in d["maos"]:
        a = d["por_mao"].get(m["id"]) or {}
        cls, linha = _linha_do_veredito(a.get("summary", ""))
        cartas = " ".join((m.get("canonical") or {}).get("hero_cards") or [])
        ev = a.get("ev_loss")
        mao_rows.append(
            f"<tr><td class='n'>{esc(str(m.get('created_at'))[:16])}</td>"
            f"<td class='n'>{esc(cartas) or '—'}</td>"
            f"<td>{esc(str(m.get('site') or ''))[:22]}</td>"
            f"<td class='n'>{f'{ev:+.1f}bb' if isinstance(ev, (int, float)) else '—'}</td>"
            f"<td class='{cls}'>{esc(linha) or '(sem análise)'}</td>"
            f"<td>{esc(str(a.get('modelo') or '').replace('claude-',''))}</td>"
            f"</tr>")
    mao_tbl = "".join(mao_rows) or \
        "<tr><td colspan=6>nenhuma mão enviada ainda</td></tr>"

    ev_rows = "".join(
        f"<tr><td class='n'>{esc(str(e.get('created_at'))[:16])}</td>"
        f"<td>{esc(str(e.get('event')))}</td>"
        f"<td>{esc(str(e.get('detail') or '')[:160])}</td></tr>"
        for e in d["eventos"][:60])

    notas_html = "".join(
        f"<div class='nota'><b>{esc(str(n.get('kind')))}</b> — "
        f"{esc(str(n.get('note')))}</div>" for n in d["notas"]) or \
        "<p class='sub'>caderno vazio — o coach ainda não destilou nada.</p>"

    p = d["perfil"]
    perfil_html = (
        f"<div class='tbl'><table><tr><th>Mãos</th><th>VPIP%</th>"
        f"<th>PFR%</th><th>3-bet%</th><th>AF</th><th>Estilo</th></tr>"
        f"<tr><td class='n'>{p.get('hands') or 0}</td>"
        f"<td class='n'>{p.get('vpip') or 0}</td>"
        f"<td class='n'>{p.get('pfr') or 0}</td>"
        f"<td class='n'>{p.get('three_bet') or 0}</td>"
        f"<td class='n'>{p.get('af') or 0}</td>"
        f"<td>{esc(str(p.get('label') or ''))}</td></tr></table></div>"
        if p else "<p class='sub'>sem perfil — precisa de export de sessão "
                  "inteira (replay avulso não mede frequência).</p>")

    return f"""<style>{_CSS}</style>
<div class="wrap">
{volta}
<h1>♠ {nome}</h1>
<p class="sub">telegram {tg} · plano <b>{esc(str(u.get('plan') or 'free'))}</b>
 · entrou {esc(str(u.get('created_at') or '')[:10])}
 · origem <b>{esc(agg['ref'] or '—')}</b></p>

<div class="grid">
  <div class="kpi"><b>{agg['maos']}</b><span>mãos enviadas</span></div>
  <div class="kpi"><b>{agg['perguntas']}</b><span>perguntas ao coach</span></div>
  <div class="kpi"><b>{agg['drills']}</b><span>quiz respondidos</span></div>
  <div class="kpi"><b>{agg['quiz']}</b><span>quiz recebidos</span></div>
  <div class="kpi"><b>US$ {agg['custo']:.2f}</b><span>custo gerado</span></div>
  <div class="kpi err"><b>{agg['erros']}</b><span>erros</span></div>
</div>

<h2>Atividade — 14 dias (sem contar o quiz automático)</h2>
<div class="bwrap"><div class="bars">{''.join(barras)}</div></div>

<h2>Mãos analisadas — as últimas {len(d['maos'])}</h2>
<div class="tbl"><table>
<tr><th>Quando</th><th>Cartas</th><th>Sala</th><th>Resultado</th>
<th>Veredito</th><th>Modelo</th></tr>
{mao_tbl}</table></div>

<h2>Caderno do coach — o que ele aprendeu sobre esta pessoa</h2>
{notas_html}

<h2>Perfil de jogo</h2>
{perfil_html}

<h2>Linha do tempo — últimos 60 eventos</h2>
<div class="tbl"><table>
<tr><th>Quando (UTC)</th><th>Evento</th><th>Detalhe</th></tr>
{ev_rows}</table></div>
</div>"""


@router.get("/admin", response_class=HTMLResponse)
async def admin(key: str = Query(default="")) -> str:
    settings = get_settings()
    if not settings.admin_token or key != settings.admin_token:
        raise HTTPException(status_code=401, detail="token inválido")

    m = _collect()
    esc = html.escape
    if not m.get("db"):
        body = "<div class='warn'>Banco indisponível — configure SUPABASE_URL/KEY.</div>"
        return f"<style>{_CSS}</style><div class='wrap'><h1>KKNuths — Gestão</h1>{body}</div>"

    # ------- tabela de usuários: quem entrou, funil, custo, erros -------
    user_rows = []
    for u in m["users"]:
        tg = u.get("telegram_id")
        pu = m["per_user"].get(tg, {})
        used = m["used_by_uid"].get(u.get("id"), 0)
        custo = m["custos"]["por_tg"].get(tg, 0.0)
        nome = u.get("username") or str(tg)
        # o nome vira porta para o dossiê: com 10 usuários, o caso
        # individual ensina mais que qualquer média (conselho, 02/08)
        link = f"<a href='/admin/usuario?key={esc(key)}&amp;tg={tg}'>" \
               f"{esc(str(nome))}</a>"
        user_rows.append(
            f"<tr><td>{link}</td>"
            f"<td>{esc(str(pu.get('ref') or '—'))}</td>"
            f"<td class='n'>{esc(str(u.get('created_at') or '')[:10])}</td>"
            f"<td>{esc(str(u.get('plan') or 'free'))}</td>"
            f"<td class='n'>{pu.get('eventos', 0)}</td>"
            f"<td class='n'>{pu.get('maos', 0)}</td>"
            f"<td class='n'>{pu.get('perguntas', 0)}</td>"
            f"<td class='n'>{pu.get('drills', 0)}</td>"
            f"<td class='n'>{used}</td>"
            f"<td class='n'>US$ {custo:.2f}</td>"
            f"<td class='n{' err' if pu.get('erros') else ''}'>{pu.get('erros', 0)}</td>"
            f"<td class='n'>{esc(str(pu.get('ultimo') or '')[:16])}</td></tr>"
        )
    users_tbl = "".join(user_rows) or "<tr><td colspan=12>nenhum usuário ainda</td></tr>"

    # ------------------- atividade diária (14 dias, barras) -------------------
    max_ev = max((d["eventos"] for d in m["days"]), default=1) or 1
    bars = "".join(
        f"<div class='bar' style='height:{max(2, int(86 * d['eventos'] / max_ev))}px'>"
        f"<b>{d['eventos'] or ''}</b><i>{d['dia'][5:]}</i></div>"
        for d in m["days"]
    )

    def _quem(r) -> str:
        """Nome SEMPRE: users é a fonte da verdade; o username do evento é
        reserva; ID cru só em último caso — era a reclamação nº 1 do dono."""
        tg = r.get("telegram_id")
        return str(m["nome_por_tg"].get(tg) or r.get("username") or tg or "?")

    # ------------------------------ erros ------------------------------
    error_rows = "".join(
        f"<tr><td class='n'>{esc(str(r.get('created_at') or '')[:16])}</td>"
        f"<td>{esc(_quem(r))}</td>"
        f"<td class='err'>{esc(str(r.get('event')))}</td>"
        f"<td>{esc(str(r.get('detail') or '')[:120])}</td></tr>"
        for r in m["errors"]
    ) or "<tr><td colspan=4>nenhum erro registrado 🎉</td></tr>"

    types_rows = "".join(
        f"<tr><td>{esc(k)}</td><td class='n'>{v}</td></tr>"
        for k, v in sorted(m["by_type"].items(), key=lambda x: -x[1])
    ) or "<tr><td colspan=2>sem eventos</td></tr>"

    profile_rows = "".join(
        f"<tr><td>{esc(str(m['nome_por_uid'].get(p.get('user_id')) or '?'))}</td>"
        f"<td class='n'>{p.get('hands') or 0}</td>"
        f"<td class='n'>{p.get('vpip') or 0}</td><td class='n'>{p.get('pfr') or 0}</td>"
        f"<td class='n'>{p.get('three_bet') or 0}</td><td class='n'>{p.get('af') or 0}</td>"
        f"<td>{esc(str(p.get('label') or ''))}</td></tr>"
        for p in m["profiles"]
    ) or "<tr><td colspan=7>sem perfis ainda</td></tr>"

    event_rows = "".join(
        f"<tr><td class='n'>{esc(str(r.get('created_at') or '')[:16])}</td>"
        f"<td>{esc(_quem(r))}</td>"
        f"<td>{esc(str(r.get('event')))}</td>"
        f"<td>{esc(str(r.get('detail') or '')[:90])}</td></tr>"
        for r in m["recent"]
    ) or "<tr><td colspan=4>sem eventos</td></tr>"

    # custo por tarefa, origem dos starts, lições
    custo_rows = "".join(
        f"<tr><td>{esc(t)}</td><td class='n'>US$ {v:.2f}</td></tr>"
        for t, v in m["custos"]["por_tarefa"].items()
    ) or "<tr><td colspan=2>sem custo no mês</td></tr>"

    ref_rows = "".join(
        f"<tr><td>{esc(o)}</td><td class='n'>{n}</td></tr>"
        for o, n in sorted(m["refs"].items(), key=lambda kv: -kv[1])
    ) or "<tr><td colspan=2>nenhum /start em 30 dias</td></tr>"

    licao_rows = "".join(
        f"<tr><td class='n'>#{x['id']}</td><td>{esc(str(x['titulo']))}</td>"
        f"<td>{esc(str(x['categoria']))}</td>"
        f"<td class='n'>{(x.get('ev_bb') or 0):+.1f}bb</td>"
        f"<td>{'📤 publicada' if x.get('publicada') else 'na estante'}</td></tr>"
        for x in m["licoes"][:12]
    ) or ("<tr><td colspan=5>biblioteca vazia — o destilador roda às "
          "9h15 UTC</td></tr>")

    ent = m["entrega"]
    pedidos = ent["ok"] + ent["falha"]
    entrega_pct = f"{round(100 * ent['ok'] / pedidos)}%" if pedidos else "—"
    juiz_nota = m["juiz"].get("nota_clareza")
    n_pub = sum(1 for x in m["licoes"] if x.get("publicada"))

    return f"""<style>{_CSS}</style>
<div class="wrap">
<h1>♠ KKNuths — Portal de Gestão</h1>
<p class="sub">Atualizado agora · dados do Supabase · north star: análises/usuário ativo/semana</p>
<div class="grid">
  <div class="kpi"><b>{len(m['users'])}</b><span>usuários totais</span></div>
  <div class="kpi"><b>{m['new7']}</b><span>novos (7 dias)</span></div>
  <div class="kpi"><b>{m['active7']}</b><span>ativos (7 dias)</span></div>
  <div class="kpi"><b>{m['hands']}</b><span>mãos no banco</span></div>
  <div class="kpi"><b>{m['analyses30']}</b><span>análises (30 dias)</span></div>
  <div class="kpi"><b>US$ {m['custos']['mes']:.2f}</b><span>custo LLM no mês · hoje US$ {m['custos']['hoje']:.2f}</span></div>
  <div class="kpi"><b>{entrega_pct}</b><span>entrega 1ª (30d) · {ent['remediada']} remediadas</span></div>
  <div class="kpi"><b>{juiz_nota if juiz_nota is not None else '—'}</b><span>clareza (juiz, última)</span></div>
  <div class="kpi"><b>{len(m['licoes'])}</b><span>lições na estante · {n_pub} publicadas</span></div>
  <div class="kpi err"><b>{m['errors30']}</b><span>erros (30 dias)</span></div>
</div>

<h2>Usuários — funil e custo por pessoa (30 dias)</h2>
<div class="tbl"><table>
<tr><th>Usuário</th><th>Origem</th><th>Entrou em</th><th>Plano</th><th>Interações</th>
<th>Mãos</th><th>Perguntas</th><th>Drills</th><th>Análises (mês)</th>
<th>Custo (mês)</th><th>Erros</th><th>Última atividade (UTC)</th></tr>
{users_tbl}</table></div>

<h2>Atividade diária — 14 dias (interações)</h2>
<div class="bwrap"><div class="bars">{bars}</div></div>

<h2>Custo de LLM por tarefa (mês) · Origem dos /start (30d)</h2>
<div class="cols">
<div class="tbl"><table><tr><th>Tarefa</th><th>US$</th></tr>{custo_rows}</table></div>
<div class="tbl"><table><tr><th>Origem</th><th>Starts</th></tr>{ref_rows}</table></div>
</div>

<h2>Biblioteca de lições (últimas)</h2>
<div class="tbl"><table>
<tr><th>#</th><th>Título</th><th>Categoria</th><th>EV</th><th>Status</th></tr>
{licao_rows}</table></div>

<h2>Erros — 30 dias (uploads rejeitados + falhas de entrega)</h2>
<div class="tbl"><table>
<tr><th>Quando (UTC)</th><th>Usuário</th><th>Tipo</th><th>Detalhe</th></tr>
{error_rows}</table></div>

<h2>Interações por tipo — 30 dias</h2>
<div class="tbl"><table><tr><th>Evento</th><th>Qtde</th></tr>{types_rows}</table></div>

<h2>Perfis de jogadores (performance)</h2>
<div class="tbl"><table>
<tr><th>Aluno</th><th>Mãos</th><th>VPIP%</th><th>PFR%</th><th>3-bet%</th><th>AF</th><th>Estilo</th></tr>
{profile_rows}</table></div>

<h2>Últimas 25 interações</h2>
<div class="tbl"><table>
<tr><th>Quando (UTC)</th><th>Usuário</th><th>Evento</th><th>Detalhe</th></tr>
{event_rows}</table></div>
</div>"""
