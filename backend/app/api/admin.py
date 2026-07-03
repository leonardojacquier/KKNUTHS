"""Portal de gestão — performance do produto e dos jogadores.

Servido pela própria API (uvicorn/pm2), protegido por ADMIN_TOKEN.
Lê tudo do Supabase via service role; se o banco estiver indisponível,
renderiza com zeros em vez de quebrar.

Acesso:  GET /admin?key=<ADMIN_TOKEN>
"""
from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.db import get_repository

router = APIRouter()


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

    users = _q(lambda: c.table("users").select("id", count="exact").execute().count, 0)
    hands = _q(lambda: c.table("hands").select("id", count="exact").execute().count, 0)
    analyses30 = _q(
        lambda: c.table("hand_analysis").select("id", count="exact")
        .gte("created_at", d30).execute().count, 0)
    events7 = _q(
        lambda: c.table("bot_events").select("id", count="exact")
        .gte("created_at", d7).execute().count, 0)
    active7 = _q(
        lambda: len({r["telegram_id"] for r in (
            c.table("bot_events").select("telegram_id").gte("created_at", d7)
            .execute().data or []) if r.get("telegram_id")}), 0)

    by_type = {}
    for r in _q(lambda: c.table("bot_events").select("event")
                .gte("created_at", d14).execute().data, []) or []:
        by_type[r["event"]] = by_type.get(r["event"], 0) + 1

    recent = _q(lambda: c.table("bot_events")
                .select("telegram_id, username, event, detail, created_at")
                .order("created_at", desc=True).limit(25).execute().data, []) or []

    profiles = _q(lambda: c.table("player_stats")
                  .select("user_id, hands, vpip, pfr, three_bet, af, label, updated_at")
                  .order("updated_at", desc=True).limit(20).execute().data, []) or []

    uploads = {}
    for r in _q(lambda: c.table("uploads").select("format")
                .gte("created_at", d30).execute().data, []) or []:
        uploads[r["format"]] = uploads.get(r["format"], 0) + 1

    return {
        "db": True, "users": users, "hands": hands, "analyses30": analyses30,
        "events7": events7, "active7": active7, "by_type": by_type,
        "recent": recent, "profiles": profiles, "uploads": uploads,
    }


_CSS = """
:root{--bg:#121714;--card:#181F1B;--ink:#E8ECE8;--mut:#96A09A;--felt:#43A97C;
--gold:#D2A55C;--line:#28312B}
body{background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;
margin:0;padding:24px;font-size:15px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--mut);margin:0 0 24px;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:28px}
.kpi{background:var(--card);border:1px solid var(--line);border-top:3px solid var(--felt);padding:14px}
.kpi b{display:block;font-size:26px;color:var(--gold);font-variant-numeric:tabular-nums}
.kpi span{font-size:12px;color:var(--mut)}
h2{font-size:15px;text-transform:uppercase;letter-spacing:.08em;color:var(--felt);
margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:var(--card)}
th{color:var(--mut);text-align:left;padding:8px 12px;font-size:11.5px;
text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--line)}
td{padding:8px 12px;border-bottom:1px solid var(--line)}
td.n{font-variant-numeric:tabular-nums;font-family:ui-monospace,monospace}
.wrap{max-width:1000px;margin:0 auto}
.tbl{overflow-x:auto;border:1px solid var(--line)}
.warn{background:#3a2a12;border:1px solid var(--gold);padding:12px;margin-bottom:20px}
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

    types_rows = "".join(
        f"<tr><td>{esc(k)}</td><td class='n'>{v}</td></tr>"
        for k, v in sorted(m["by_type"].items(), key=lambda x: -x[1])
    ) or "<tr><td colspan=2>sem eventos</td></tr>"

    upload_rows = "".join(
        f"<tr><td>{esc(k)}</td><td class='n'>{v}</td></tr>"
        for k, v in sorted(m["uploads"].items(), key=lambda x: -x[1])
    ) or "<tr><td colspan=2>sem uploads</td></tr>"

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
  <div class="kpi"><b>{m['users']}</b><span>usuários totais</span></div>
  <div class="kpi"><b>{m['active7']}</b><span>ativos (7 dias)</span></div>
  <div class="kpi"><b>{m['hands']}</b><span>mãos no banco</span></div>
  <div class="kpi"><b>{m['analyses30']}</b><span>análises (30 dias)</span></div>
  <div class="kpi"><b>{m['events7']}</b><span>interações (7 dias)</span></div>
</div>
<h2>Interações por tipo — 14 dias</h2>
<div class="tbl"><table><tr><th>Evento</th><th>Qtde</th></tr>{types_rows}</table></div>
<h2>Uploads por formato — 30 dias</h2>
<div class="tbl"><table><tr><th>Formato</th><th>Qtde</th></tr>{upload_rows}</table></div>
<h2>Perfis de jogadores (performance)</h2>
<div class="tbl"><table>
<tr><th>Mãos</th><th>VPIP%</th><th>PFR%</th><th>3-bet%</th><th>AF</th><th>Estilo</th></tr>
{profile_rows}</table></div>
<h2>Últimas 25 interações</h2>
<div class="tbl"><table>
<tr><th>Quando (UTC)</th><th>Usuário</th><th>Evento</th><th>Detalhe</th></tr>
{event_rows}</table></div>
</div>"""
