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

_ERROR_EVENTS = ("upload_failed", "error")


def _q(fn, default):
    try:
        return fn()
    except Exception:
        return default


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
        lambda: {"eventos": 0, "uploads": 0, "erros": 0, "ultimo": "", "ref": ""})
    daily: dict[str, dict] = defaultdict(lambda: {"eventos": 0, "usuarios": set()})
    by_type: dict[str, int] = defaultdict(int)
    errors: list[dict] = []
    active7: set[int] = set()

    for r in events:
        tg = r.get("telegram_id")
        ev = r.get("event") or "?"
        ts = str(r.get("created_at") or "")
        by_type[ev] += 1
        if tg:
            u = per_user[tg]
            u["eventos"] += 1
            u["ultimo"] = max(u["ultimo"], ts)
            if ev == "upload":
                u["uploads"] += 1
            if ev in _ERROR_EVENTS:
                u["erros"] += 1
            if ev == "start":
                try:
                    d = r.get("detail") or {}
                    d = json.loads(d) if isinstance(d, str) else d
                    u["ref"] = u["ref"] or str(d.get("ref") or "")
                except Exception:
                    pass
            if ts >= d7:
                active7.add(tg)
            day = ts[:10]
            if day:
                daily[day]["eventos"] += 1
                daily[day]["usuarios"].add(tg)
        if ev in _ERROR_EVENTS:
            errors.append(r)

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
"""


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

    # ------- tabela de usuários: quem entrou, acessos, análises, erros -------
    user_rows = []
    for u in m["users"]:
        tg = u.get("telegram_id")
        pu = m["per_user"].get(tg, {})
        used = m["used_by_uid"].get(u.get("id"), 0)
        nome = u.get("username") or str(tg)
        user_rows.append(
            f"<tr><td>{esc(str(nome))}</td>"
            f"<td>{esc(str(pu.get('ref') or '—'))}</td>"
            f"<td class='n'>{esc(str(u.get('created_at') or '')[:10])}</td>"
            f"<td>{esc(str(u.get('plan') or 'free'))}</td>"
            f"<td class='n'>{pu.get('eventos', 0)}</td>"
            f"<td class='n'>{pu.get('uploads', 0)}</td>"
            f"<td class='n'>{used}</td>"
            f"<td class='n{' err' if pu.get('erros') else ''}'>{pu.get('erros', 0)}</td>"
            f"<td class='n'>{esc(str(pu.get('ultimo') or '')[:16])}</td></tr>"
        )
    users_tbl = "".join(user_rows) or "<tr><td colspan=9>nenhum usuário ainda</td></tr>"

    # ------------------- atividade diária (14 dias, barras) -------------------
    max_ev = max((d["eventos"] for d in m["days"]), default=1) or 1
    bars = "".join(
        f"<div class='bar' style='height:{max(2, int(86 * d['eventos'] / max_ev))}px'>"
        f"<b>{d['eventos'] or ''}</b><i>{d['dia'][5:]}</i></div>"
        for d in m["days"]
    )

    # ------------------------------ erros ------------------------------
    error_rows = "".join(
        f"<tr><td class='n'>{esc(str(r.get('created_at') or '')[:16])}</td>"
        f"<td>{esc(str(r.get('username') or r.get('telegram_id') or '?'))}</td>"
        f"<td class='err'>{esc(str(r.get('event')))}</td>"
        f"<td>{esc(str(r.get('detail') or '')[:120])}</td></tr>"
        for r in m["errors"]
    ) or "<tr><td colspan=4>nenhum erro registrado 🎉</td></tr>"

    types_rows = "".join(
        f"<tr><td>{esc(k)}</td><td class='n'>{v}</td></tr>"
        for k, v in sorted(m["by_type"].items(), key=lambda x: -x[1])
    ) or "<tr><td colspan=2>sem eventos</td></tr>"

    profile_rows = "".join(
        f"<tr><td class='n'>{p.get('hands') or 0}</td>"
        f"<td class='n'>{p.get('vpip') or 0}</td><td class='n'>{p.get('pfr') or 0}</td>"
        f"<td class='n'>{p.get('three_bet') or 0}</td><td class='n'>{p.get('af') or 0}</td>"
        f"<td>{esc(str(p.get('label') or ''))}</td></tr>"
        for p in m["profiles"]
    ) or "<tr><td colspan=6>sem perfis ainda</td></tr>"

    event_rows = "".join(
        f"<tr><td class='n'>{esc(str(r.get('created_at') or '')[:16])}</td>"
        f"<td>{esc(str(r.get('username') or r.get('telegram_id') or '?'))}</td>"
        f"<td>{esc(str(r.get('event')))}</td>"
        f"<td>{esc(str(r.get('detail') or '')[:90])}</td></tr>"
        for r in m["recent"]
    ) or "<tr><td colspan=4>sem eventos</td></tr>"

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
  <div class="kpi err"><b>{m['errors30']}</b><span>erros (30 dias)</span></div>
</div>

<h2>Usuários — quem entrou e o que fez</h2>
<div class="tbl"><table>
<tr><th>Usuário</th><th>Origem</th><th>Entrou em</th><th>Plano</th><th>Interações</th>
<th>Uploads</th><th>Análises (mês)</th><th>Erros</th><th>Última atividade (UTC)</th></tr>
{users_tbl}</table></div>

<h2>Atividade diária — 14 dias (interações)</h2>
<div class="bwrap"><div class="bars">{bars}</div></div>

<h2>Erros — 30 dias (uploads rejeitados + exceções)</h2>
<div class="tbl"><table>
<tr><th>Quando (UTC)</th><th>Usuário</th><th>Tipo</th><th>Detalhe</th></tr>
{error_rows}</table></div>

<h2>Interações por tipo — 30 dias</h2>
<div class="tbl"><table><tr><th>Evento</th><th>Qtde</th></tr>{types_rows}</table></div>

<h2>Perfis de jogadores (performance)</h2>
<div class="tbl"><table>
<tr><th>Mãos</th><th>VPIP%</th><th>PFR%</th><th>3-bet%</th><th>AF</th><th>Estilo</th></tr>
{profile_rows}</table></div>

<h2>Últimas 25 interações</h2>
<div class="tbl"><table>
<tr><th>Quando (UTC)</th><th>Usuário</th><th>Evento</th><th>Detalhe</th></tr>
{event_rows}</table></div>
</div>"""
