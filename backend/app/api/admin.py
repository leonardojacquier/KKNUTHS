"""Portal de gestão — performance do produto e dos jogadores.

Servido pela própria API (uvicorn/pm2), protegido por ADMIN_TOKEN.
Lê tudo do Supabase via service role; se o banco estiver indisponível,
renderiza com zeros em vez de quebrar.

Acesso:  GET /admin?key=<ADMIN_TOKEN>
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.db import get_repository

router = APIRouter()

# teto da varredura de eventos do painel. Existe para a página não puxar o
# banco inteiro; quando ele é atingido a página AVISA, em vez de mostrar
# número menor calado.
_TETO_EVENTOS = 5000

_ERROR_EVENTS = ("upload_failed", "error", "entrega_falha",
                 "sem_mao_na_conversa")
# Um ENVIO analisado = um evento 'upload', e só. 'print_recebido' e
# 'replay_pppoker/suprema' são o CANAL por onde a mesma mão chegou, gravados
# ao lado do upload — contar os dois dobrava o número: o Ricardo aparecia
# com 194 mãos tendo 92 no banco. (conferido no banco em 07/08)
_MAO_EVENTS = ("upload",)
# O BOT falando com a pessoa — não é a pessoa usando a ferramenta. Aparece
# no diário (é contexto), mas NÃO conta como atividade: a lição do dia de
# 07/08 marcou os 10 alunos como "ativos às 01:54", inclusive quem nunca
# mandou uma mão. Métrica que sobe sozinha quando eu aperto um botão não
# mede nada.
_SO_RECEBEU = ("daily_quiz_sent", "licao_recebida", "convite_primeira_mao",
               "reanalise_enviada")


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
                .order("created_at", desc=True)
                .limit(_TETO_EVENTOS).execute().data, []) or []
    # bater o teto não dá erro: a consulta vem ordenada do mais novo pro mais
    # velho e simplesmente CORTA o resto do mês. Os números encolheriam
    # sozinhos, sem avisar, e eu leria isso como "os alunos usaram menos".
    # Hoje são ~1.5k eventos em 14 dias com 10 alunos; o teto chega junto com
    # o crescimento, que é exatamente quando eu mais vou olhar o painel.
    truncou = len(events) >= _TETO_EVENTOS

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
            # "interações" tem que ser AÇÃO de gente: custo_llm sozinho é
            # 458 de ~1500 eventos e inflava a coluna de todo mundo. E o que
            # o bot ENVIA (quiz, lição) não é a pessoa agindo.
            agiu = ev not in _SO_SISTEMA and ev not in _SO_RECEBEU
            if agiu:
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
            if agiu and ts >= d7:
                active7.add(tg)
            day = ts[:10]
            if day and agiu:
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

    # filtra ANTES de cortar: contabilidade + cron são ~2/3 dos eventos,
    # então um [:25] cru devolvia 8 ações de gente e 17 linhas de máquina
    recent = [r for r in events if e_acao_de_gente(r)][:40]
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
        "truncou": truncou,
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
.diario{background:var(--card);border:1px solid var(--line);padding:4px 0}
.dia{background:#0d120f;color:var(--felt);font-size:11.5px;letter-spacing:.08em;
padding:6px 14px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);
text-transform:uppercase;font-weight:600;position:sticky;top:0}
.ato{display:flex;gap:10px;align-items:baseline;padding:7px 14px;font-size:13.5px;
border-bottom:1px solid rgba(40,49,43,.5)}
.ato .hora{color:var(--mut);font-family:ui-monospace,monospace;font-size:11.5px;
min-width:38px}
.ato .ico{min-width:20px}
.ato.mut{opacity:.55}
.ato.ok span:last-child{color:var(--felt)}
.ato.bad span:last-child{color:var(--red)}
.ato.mid span:last-child{color:var(--gold)}
a.kpi{display:block;border-bottom:1px solid var(--line);color:inherit}
a.kpi:hover{background:#1e2621;border-top-color:var(--gold)}
a.kpi span{color:var(--mut)}
a.kpi.sel{background:#1e2621;border-top-width:5px;padding-top:12px}
a.kpi.sel span{color:var(--ink)}
.limpa{font-size:11px;text-transform:none;letter-spacing:0;margin-left:8px}
.qa{background:var(--card);border:1px solid var(--line);
border-left:3px solid var(--felt);padding:10px 14px;margin:8px 0}
.qa .quando{color:var(--mut);font-size:11px;font-family:ui-monospace,monospace}
.qa .perg{font-weight:600;margin:4px 0 8px}
.resp{white-space:pre-wrap;font-size:13.5px;line-height:1.5;color:var(--ink)}
.resp.mut{color:var(--mut);font-style:italic}
.resp.bad{color:var(--red)}
.resp.grande{background:var(--card);border:1px solid var(--line);
border-left:3px solid var(--felt);padding:14px;font-size:14px}
pre.raw{background:var(--card);border:1px solid var(--line);padding:12px;
overflow-x:auto;font-size:12px;color:var(--mut);max-height:420px}
"""


# Contabilidade por usuário: tem telegram_id de gente, mas NÃO é ação de
# gente. custo_llm sozinho é 458 de ~1500 eventos em 14 dias; junto com os
# comandos do dono (*_cmd) afoga o que os alunos realmente fizeram.
_SO_SISTEMA = {"custo_llm", "caderno_auto", "entrega_ok", "licoes_cmd",
               "termo_cmd", "quem_cmd", "planode_cmd", "daily_usage",
               "output_judge", "nota_resposta", "sonda_recebimento",
               # o par da pergunta: guarda a resposta do coach para a tela de
               # perguntas. No diário seria a mesma pergunta duas vezes.
               "followup_resposta"}


def e_acao_de_gente(e: dict) -> bool:
    """Um aluno fez isso, ou foi o sistema falando sozinho?

    Duas regras, e a segunda é a que dura: `telegram_id <= 0` é a assinatura
    de TODO cron (deploy, jornadas, anomalias, backup, coherence…). Filtrar
    por ID em vez de por nome significa que o cron que eu escrever amanhã já
    nasce fora do feed — sem eu lembrar de vir aqui pôr o nome numa lista.
    """
    tg = e.get("telegram_id")
    if not isinstance(tg, int) or tg <= 0:
        return False
    return str(e.get("event") or "") not in _SO_SISTEMA


def _repetido(texto: str, tg, ultimo: list) -> bool:
    """O clique e o efeito do clique são DOIS eventos e UM ato.

    'btn_share' + 'share_card' (e btn_range/range, btn_sim/simular) sempre
    saem em par: o feed mostrava 'Gerou o card' duas vezes seguidas e parecia
    que a pessoa fez duas coisas. Só colapsa idênticos CONSECUTIVOS do mesmo
    aluno — dois quizzes iguais em horas diferentes continuam aparecendo.
    """
    chave = (tg, texto)
    if ultimo and ultimo[0] == chave:
        return True
    ultimo[:] = [chave]
    return False


def narrar_evento(e: dict) -> dict | None:
    """Traduz UM evento para o que a pessoa fez, em português.

    Devolve {icone, texto, classe} ou None se não for ação de gente. É esta
    função que transforma 'followup {"q":"..."}' em «💬 Perguntou: "..."» —
    sem ela o portal mostra nome de evento e JSON, que não é legível.
    """
    ev = str(e.get("event") or "")
    if ev in _SO_SISTEMA:
        return None
    d = _detalhe(e)

    def _t(txt, icone="•", classe=""):
        return {"icone": icone, "texto": txt, "classe": classe}

    if ev == "start":
        origem = d.get("ref") or "direto"
        return _t(f"Abriu o bot (origem: <b>{html.escape(str(origem))}</b>)",
                  "🚪")
    if ev == "upload":
        site = str(d.get("site") or "?")
        n = d.get("hands") or 1
        resta = d.get("quota_remaining")
        extra = f" · restam {resta} análises" if resta is not None else ""
        return _t(f"Análise entregue: {n} mão(s) — {html.escape(site)}{extra}",
                  "✅", "ok")
    if ev in ("replay_pppoker", "replay_suprema"):
        sala = "PPPoker" if "pppoker" in ev else "Suprema"
        return _t(f"Mandou link de replay do {sala}", "🔗")
    if ev == "replay_link":
        return _t(f"Mandou link que eu não abro sozinho "
                  f"({html.escape(str(d.get('site') or '?'))})", "🔗", "mid")
    if ev == "print_recebido":
        return _t("Mandou um print da mesa", "📸")
    if ev == "upload_recebido":
        return _t("Mandou um arquivo de mãos", "📎")
    if ev == "voice":
        return _t("Mandou áudio", "🎤")
    if ev == "followup":
        q = str(d.get("q") or "")[:150]
        return _t(f"Perguntou: <i>“{html.escape(q)}”</i>", "💬")
    if ev == "followup_failed":
        q = str(d.get("q") or "")[:90]
        motivo = str(d.get("motivo") or "sem motivo registrado")[:70]
        return _t(f"Pergunta FALHOU: <i>“{html.escape(q)}”</i> — "
                  f"{html.escape(motivo)}", "🚨", "bad")
    if ev == "daily_quiz_sent":
        return _t("Recebeu o quiz do dia", "🎯", "mut")
    if ev == "drill_answer":
        return _t(f"Respondeu o quiz: <b>"
                  f"{html.escape(str(d.get('choice') or '?'))}</b>", "🎯")
    if ev == "drill_verdict":
        v = str(d.get("verdict") or "?")
        cls = "ok" if v == "boa" else "bad" if v == "ruim" else "mid"
        return _t(f"Resultado do quiz: <b>{html.escape(v)}</b> "
                  f"({html.escape(str(d.get('cat') or ''))})", "🎯", cls)
    if ev == "licao_recebida":
        return _t(f"Recebeu a lição #{d.get('licao')}", "📖")
    if ev == "convite_primeira_mao":
        return _t("Recebeu o convite à primeira mão", "👋", "mid")
    if ev == "simplify":
        return _t("Pediu a versão simples da análise 🎈", "🎈")
    if ev in ("simular", "btn_sim"):
        return _t("Abriu o simulador", "🎮")
    if ev == "sim_done":
        return _t(f"Terminou a simulação ({d.get('decisoes')} decisões)", "🎮")
    if ev in ("range", "btn_range"):
        return _t("Abriu o range do spot", "📊")
    if ev in ("share_card", "btn_share"):
        return _t("Gerou o card para compartilhar", "📣", "ok")
    if ev == "go_treino":
        return _t("Clicou em treinar", "🎓")
    if ev == "plano":
        return _t("Consultou o próprio plano", "💳")
    if ev == "preparar":
        return _t("Pediu o briefing pré-torneio", "🧠")
    if ev == "spot_cmd":
        return _t("Pediu um spot para treinar", "🎯")
    if ev == "upload_failed":
        return _t(f"Envio FALHOU: "
                  f"{html.escape(str(d.get('note') or '')[:110])}", "🚨", "bad")
    if ev == "error":
        return _t(f"Erro: {html.escape(str(d.get('error') or '')[:110])}",
                  "🚨", "bad")
    if ev == "sem_mao_na_conversa":
        return _t("Conversou sem mão aberta (contexto perdido)", "⚠️", "mid")
    if ev == "entrega_falha":
        return _t(f"Resposta veio incompleta (faltou "
                  f"{html.escape(str(d.get('faltou') or ''))})", "⚠️", "mid")
    if ev == "entrega_remediada":
        return _t("Resposta incompleta — o guarda consertou", "🔧", "mid")
    if ev == "reanalise_enviada":
        return _t("Recebeu uma reanálise (correção nossa)", "🔄", "mid")
    # evento novo que ainda não traduzi: mostra cru, mas não some
    return _t(html.escape(ev), "•", "mut")


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

    # telegram_id VAI no select mesmo já filtrando por ele: e_acao_de_gente()
    # lê essa coluna, e sem ela o dossiê inteiro dizia "nenhuma ação
    # registrada" para gente que tinha feito coisas. Coluna que a regra usa
    # tem que vir na consulta.
    eventos = _q(lambda: c.table("bot_events")
                 .select("telegram_id,event,detail,created_at")
                 .eq("telegram_id", tg)
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
    # quantas mãos ESTA pessoa tem de verdade. Contar evento não serve: um
    # export de sessão é 1 envio e 159 mãos (caso do Odilon), e reenviar o
    # mesmo arquivo soma evento sem criar mão. Só o banco sabe. count exact
    # não traz linha nenhuma — é barato.
    n_maos = _q(lambda: c.table("hands").select("id", count="exact")
                .eq("user_id", u["id"]).execute().count, 0) or 0
    notas = _q(lambda: repo.get_notes(u["id"], limit=10), []) or []
    perfil = (_q(lambda: c.table("player_stats").select("*")
               .eq("user_id", u["id"]).limit(1).execute().data, [])
              or [None])[0]

    agg = {"eventos": len(eventos), "maos": 0, "perguntas": 0, "drills": 0,
           "erros": 0, "custo": 0.0, "ref": "", "quiz": 0, "treino_btn": 0}
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
        elif ev == "go_treino":
            # o botão "treinar" serve um treino na hora. Sem contar isso, o
            # painel mostrava "1 respondido / 0 recebidos" e parecia bug —
            # era o treino do onboarding, que não vem do quiz das 19h.
            agg["treino_btn"] += 1
        elif ev == "custo_llm":
            usd = _detalhe(e).get("usd")
            if isinstance(usd, (int, float)):
                agg["custo"] += usd
        if ev in _ERROR_EVENTS:
            agg["erros"] += 1
        if ev == "start" and not agg["ref"]:
            agg["ref"] = str(_detalhe(e).get("ref") or "direto")
        # o gráfico de hábito mede o que a PESSOA fez: quiz e lição que o bot
        # empurrou desenhariam uma barra por dia mesmo com ela sumida
        if ts and ev not in _SO_RECEBEU and ev not in _SO_SISTEMA:
            dias[ts[:10]] += 1
    agg["maos_banco"] = n_maos
    return {"db": True, "achou": True, "u": u, "eventos": eventos,
            "maos": maos, "por_mao": por_mao, "notas": notas,
            "perfil": perfil, "agg": agg, "dias": dias}


def _perguntas_com_resposta(eventos: list) -> list[dict]:
    """Casa cada pergunta do aluno com a resposta que o coach deu.

    A pergunta é gravada ANTES de chamar o LLM (para não sumir se ele cair) e
    a resposta depois, em 'followup_resposta' — então elas são dois eventos e
    é aqui que viram uma conversa. Casa pelo texto da pergunta: as duas
    pontas gravam o mesmo `q`.
    """
    respostas: dict[str, str] = {}
    for e in eventos:
        if (e.get("event") or "") == "followup_resposta":
            det = _detalhe(e)
            q = str(det.get("q") or "")[:120]
            if q:
                respostas.setdefault(q, str(det.get("r") or ""))
    saida = []
    for e in eventos:
        ev = e.get("event") or ""
        if ev not in ("followup", "followup_failed"):
            continue
        det = _detalhe(e)
        q = str(det.get("q") or "")
        saida.append({
            "quando": str(e.get("created_at") or ""),
            "q": q,
            "r": respostas.get(q[:120], ""),
            "falhou": ev == "followup_failed",
            "motivo": str(det.get("motivo") or ""),
        })
    return saida


def _treinos(eventos: list) -> list[dict]:
    """Junta a resposta do treino com o veredito que veio depois.

    'drill_answer' (o que a pessoa escolheu) e 'drill_verdict' (se acertou)
    são eventos separados, ligados pelo hand_id. Separados, a tela mostrava
    'respondeu: call' sem dizer se call estava certo — que é a única coisa
    que interessa saber.
    """
    veredito: dict[str, dict] = {}
    for e in eventos:
        if (e.get("event") or "") == "drill_verdict":
            det = _detalhe(e)
            hid = str(det.get("hand_id") or "")
            veredito.setdefault(hid, det)
    saida = []
    for e in eventos:
        if (e.get("event") or "") != "drill_answer":
            continue
        det = _detalhe(e)
        v = veredito.get(str(det.get("hand_id") or "")) or {}
        saida.append({
            "quando": str(e.get("created_at") or ""),
            "escolha": str(det.get("choice") or "—"),
            "veredito": str(v.get("verdict") or ""),
            "cat": str(v.get("cat") or det.get("cat") or ""),
            "mao": str(det.get("hand_id") or ""),
        })
    return saida


# as caixas que abrem lista. Cada uma promete um número — clicar tem que
# mostrar exatamente as linhas que formam aquele número, senão o painel
# obriga a confiar nele.
_FOCOS = ("maos", "perguntas", "treinos", "quiz", "erros")


def _bloco_foco(ver: str, d: dict, key: str, tg: int) -> str:
    """A lista da caixa clicada. Zero consulta nova: tudo já veio no dossiê.

    O filtro é de memória de propósito — clicar numa caixa não pode custar
    uma ida ao banco, senão o portal fica lento na mão de quem está usando.
    """
    esc = html.escape
    if ver not in _FOCOS:
        return ""
    eventos = d["eventos"]

    if ver == "perguntas":
        itens = _perguntas_com_resposta(eventos)
        if not itens:
            return "<p class='sub'>nenhuma pergunta ao coach ainda.</p>"
        out = []
        for it in itens[:60]:
            if it["falhou"]:
                corpo = (f"<div class='resp bad'>falhou — "
                         f"{esc(it['motivo'] or 'motivo não gravado')}</div>")
            elif it["r"]:
                corpo = f"<div class='resp'>{esc(it['r'])}</div>"
            else:
                corpo = ("<div class='resp mut'>resposta não gravada — só "
                         "guardo a partir de 07/08.</div>")
            out.append(
                f"<div class='qa'><div class='quando'>"
                f"{esc(it['quando'][:16].replace('T', ' '))}</div>"
                f"<div class='perg'>{esc(it['q'])}</div>{corpo}</div>")
        return "".join(out)

    if ver == "treinos":
        itens = _treinos(eventos)
        if not itens:
            return "<p class='sub'>nenhum treino respondido ainda.</p>"
        cor = {"boa": "ok", "ruim": "bad", "mista": "mid"}
        linhas = "".join(
            f"<tr><td class='n'>{esc(it['quando'][:16].replace('T', ' '))}</td>"
            f"<td>{esc(it['cat'] or '—')}</td>"
            f"<td class='n'>{esc(it['escolha'])}</td>"
            f"<td class='{cor.get(it['veredito'], '')}'>"
            f"{esc(it['veredito'] or '(sem veredito)')}</td>"
            f"<td class='n'>{esc(it['mao'][:24] or '—')}</td></tr>"
            for it in itens[:60])
        return ("<div class='tbl'><table><tr><th>Quando</th><th>Rua</th>"
                "<th>Escolheu</th><th>Veredito</th><th>Mão</th></tr>"
                f"{linhas}</table></div>")

    if ver == "erros":
        itens = [e for e in eventos if (e.get("event") or "") in _ERROR_EVENTS]
        if not itens:
            return "<p class='sub'>nenhum erro — esta pessoa nunca bateu " \
                   "numa falha.</p>"
        linhas = []
        for e in itens[:60]:
            det = _detalhe(e)
            # as chaves que cada falha REALMENTE grava (conferido no banco):
            # upload_failed→note, error→error, entrega_falha→faltou,
            # sem_mao_na_conversa→chaves. Chutar nome de chave aqui rende
            # uma coluna "motivo" vazia, que é pior que não ter a coluna.
            motivo = next(
                (str(det[k]) for k in
                 ("note", "error", "motivo", "faltou", "chaves")
                 if det.get(k)), "")
            if (e.get("event") or "") == "entrega_falha" and det.get("pediu"):
                motivo = f"pediu {det['pediu']}, faltou {motivo}"
            linhas.append(
                f"<tr><td class='n'>"
                f"{esc(str(e.get('created_at'))[:16].replace('T', ' '))}</td>"
                f"<td class='err'>{esc(str(e.get('event')))}</td>"
                f"<td>{esc(str(motivo)[:300] or '(motivo não gravado)')}</td>"
                f"</tr>")
        return ("<div class='tbl'><table><tr><th>Quando</th><th>Falha</th>"
                f"<th>Motivo</th></tr>{''.join(linhas)}</table></div>")

    if ver == "quiz":
        itens = [e for e in eventos
                 if (e.get("event") or "") in ("daily_quiz_sent",
                                               "licao_recebida", "go_treino")]
        if not itens:
            return "<p class='sub'>o bot ainda não empurrou nada para esta " \
                   "pessoa.</p>"
        rotulo = {"daily_quiz_sent": "quiz do dia (19h)",
                  "licao_recebida": "lição do dia",
                  "go_treino": "abriu treino pelo botão"}
        linhas = "".join(
            f"<tr><td class='n'>"
            f"{esc(str(e.get('created_at'))[:16].replace('T', ' '))}</td>"
            f"<td>{esc(rotulo.get(str(e.get('event')), str(e.get('event'))))}</td>"
            f"<td class='n'>{esc(str(_detalhe(e).get('licao') or ''))}</td></tr>"
            for e in itens[:60])
        return ("<div class='tbl'><table><tr><th>Quando</th><th>O quê</th>"
                f"<th>Lição nº</th></tr>{linhas}</table></div>")

    # ver == "maos": a tabela já existe embaixo; aqui ela vira o foco e cada
    # linha abre a mão inteira
    if not d["maos"]:
        return "<p class='sub'>nenhuma mão enviada ainda.</p>"
    linhas = []
    for m in d["maos"]:
        a = d["por_mao"].get(m["id"]) or {}
        cls, linha = _linha_do_veredito(a.get("summary", ""))
        cartas = " ".join((m.get("canonical") or {}).get("hero_cards") or [])
        ev = a.get("ev_loss")
        linhas.append(
            f"<tr><td class='n'><a href='/admin/mao?key={esc(key)}"
            f"&id={esc(str(m['id']))}&tg={tg}'>"
            f"{esc(str(m.get('created_at'))[:16].replace('T', ' '))}</a></td>"
            f"<td class='n'>{esc(cartas) or '—'}</td>"
            f"<td>{esc(str(m.get('site') or ''))[:22]}</td>"
            f"<td class='n'>"
            f"{f'{ev:+.1f}bb' if isinstance(ev, (int, float)) else '—'}</td>"
            f"<td class='{cls}'>{esc(linha) or '(sem análise)'}</td></tr>")
    return ("<div class='tbl'><table><tr><th>Quando (clique para abrir)</th>"
            "<th>Cartas</th><th>Sala</th><th>Resultado</th><th>Veredito</th>"
            f"</tr>{''.join(linhas)}</table></div>")


@router.get("/admin/mao", response_class=HTMLResponse)
async def admin_mao(key: str = Query(default=""),
                    id: str = Query(default=""),
                    tg: int = Query(default=0)) -> str:
    """A mão inteira: o que o coach respondeu, e o que aconteceu na mesa."""
    settings = get_settings()
    if not settings.admin_token or key != settings.admin_token:
        raise HTTPException(status_code=401, detail="token inválido")
    esc = html.escape
    volta = (f"<a class='volta' href='/admin/usuario?key={esc(key)}&tg={tg}"
             f"&ver=maos'>← voltar para as mãos</a>")
    repo = get_repository()
    if not repo.enabled:
        return (f"<style>{_CSS}</style><div class='wrap'>{volta}"
                "<div class='warn'>Banco indisponível.</div></div>")
    c = repo.client
    m = (_q(lambda: c.table("hands")
            .select("id,hand_id,site,format,canonical,created_at,played_at")
            .eq("id", id).limit(1).execute().data, []) or [None])[0]
    if not m:
        return (f"<style>{_CSS}</style><div class='wrap'>{volta}"
                "<div class='warn'>Mão não encontrada.</div></div>")
    # 'embedding' NUNCA entra no select: é um vetor de 1536 números que não
    # serve para nada nesta tela e engorda a resposta à toa
    a = (_q(lambda: c.table("hand_analysis")
           .select("summary,ev_loss,mistakes,modelo,created_at")
           .eq("hand_id", id).order("created_at", desc=True)
           .limit(1).execute().data, []) or [None])[0] or {}

    can = m.get("canonical") or {}
    cartas = " ".join(can.get("hero_cards") or []) or "—"
    ev = a.get("ev_loss")
    erros = a.get("mistakes")
    erros_html = ""
    if isinstance(erros, list) and erros:
        erros_html = "<h2>Erros apontados</h2>" + "".join(
            f"<div class='nota'>{esc(str(x))}</div>" for x in erros)
    # o resumo é o texto que o aluno recebeu no Telegram, com *negrito*
    resumo = esc(str(a.get("summary") or "")) or \
        "(esta mão não tem análise gravada)"
    resumo = re.sub(r"\*([^*]+)\*", r"<b>\1</b>", resumo)

    ruas = ""
    if isinstance(can.get("streets"), (list, dict)):
        ruas = (f"<h2>Como a mão foi</h2><pre class='raw'>"
                f"{esc(json.dumps(can.get('streets'), ensure_ascii=False, indent=2))[:4000]}"
                f"</pre>")

    return f"""<style>{_CSS}</style>
<div class="wrap">
{volta}
<h1>♠ {esc(cartas)}</h1>
<p class="sub">{esc(str(m.get('site') or ''))} ·
 {esc(str(m.get('format') or ''))} ·
 {esc(str(m.get('created_at') or '')[:16].replace('T', ' '))} ·
 resultado <b>{f'{ev:+.1f}bb' if isinstance(ev, (int, float)) else '—'}</b> ·
 modelo {esc(str(a.get('modelo') or '—').replace('claude-', ''))}</p>

<h2>O que o coach respondeu</h2>
<div class="resp grande">{resumo}</div>
{erros_html}
{ruas}
</div>"""


@router.get("/admin/usuario", response_class=HTMLResponse)
async def admin_usuario(key: str = Query(default=""),
                        tg: int = Query(default=0),
                        ver: str = Query(default="")) -> str:
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

    # DIÁRIO: o que a pessoa fez, em português, agrupado por dia. O dump de
    # nome-de-evento + JSON não dizia nada ("não fica claro como estão as
    # ações dos usuários" — dono, 07/08).
    linhas_diario, dia_atual, mostrados, ultimo = [], None, 0, []
    for e in d["eventos"]:
        n = narrar_evento(e) if e_acao_de_gente(e) else None
        if not n or mostrados >= 80:
            continue
        if _repetido(n["texto"], tg, ultimo):
            continue
        ts = str(e.get("created_at") or "")
        dia = ts[:10]
        if dia != dia_atual:
            dia_atual = dia
            linhas_diario.append(
                f"<div class='dia'>{esc(dia[8:10])}/{esc(dia[5:7])}</div>")
        linhas_diario.append(
            f"<div class='ato {n['classe']}'>"
            f"<span class='hora'>{esc(ts[11:16])}</span>"
            f"<span class='ico'>{n['icone']}</span>"
            f"<span>{n['texto']}</span></div>")
        mostrados += 1
    diario = "".join(linhas_diario) or \
        "<p class='sub'>nenhuma ação registrada.</p>"

    notas_html = "".join(
        f"<div class='nota'><b>{esc(str(n.get('kind')))}</b> — "
        f"{esc(str(n.get('note')))}</div>" for n in d["notas"]) or \
        "<p class='sub'>caderno vazio — o coach ainda não destilou nada.</p>"

    # CAIXAS CLICÁVEIS: cada número abre exatamente as linhas que o formam.
    # Rótulos precisos porque "quiz respondidos: 1 / quiz recebidos: 0"
    # parecia impossível — eram coisas diferentes com o mesmo nome: o treino
    # veio do botão "treinar", não do quiz das 19h.
    ver = ver if ver in _FOCOS else ""
    base = f"/admin/usuario?key={esc(key)}&tg={tg}"
    caixas_def = [
        ("maos", agg.get("maos_banco", 0), "mãos no banco", ""),
        (None, agg["maos"], "envios analisados", ""),
        ("perguntas", agg["perguntas"], "perguntas ao coach", ""),
        ("treinos", agg["drills"], "treinos respondidos", ""),
        ("quiz", agg["quiz"] + agg["treino_btn"], "treinos que o bot serviu",
         ""),
        (None, f"US$ {agg['custo']:.2f}", "custo gerado", ""),
        ("erros", agg["erros"], "erros", "err"),
    ]
    caixas = []
    for alvo, valor, rotulo, extra in caixas_def:
        cls = f"kpi {extra}".strip()
        if not alvo:
            caixas.append(f"<div class='{cls}'><b>{valor}</b>"
                          f"<span>{rotulo}</span></div>")
            continue
        sel = " sel" if ver == alvo else ""
        href = base if ver == alvo else f"{base}&ver={alvo}"
        caixas.append(f"<a class='{cls}{sel}' href='{href}'><b>{valor}</b>"
                      f"<span>{rotulo} ›</span></a>")
    caixas = "".join(caixas)

    titulo_foco = {"maos": "As mãos, uma a uma",
                   "perguntas": "As perguntas — e o que o coach respondeu",
                   "treinos": "Os treinos respondidos",
                   "quiz": "O que o bot serviu para esta pessoa",
                   "erros": "As falhas que esta pessoa encontrou"}
    foco_html = ""
    if ver:
        foco_html = (f"<h2>{titulo_foco[ver]} "
                     f"<a class='limpa' href='{base}'>× limpar</a></h2>"
                     f"{_bloco_foco(ver, d, key, tg)}")

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

<div class="grid">{caixas}</div>
{foco_html}
<h2>Atividade — 14 dias (só o que a pessoa fez; sem contar o quiz
 automático e a lição que o bot empurra)</h2>
<div class="bwrap"><div class="bars">{''.join(barras)}</div></div>

<h2>O que esta pessoa fez — em ordem</h2>
<div class="diario">{diario}</div>

<h2>Mãos analisadas — as últimas {len(d['maos'])}</h2>
<div class="tbl"><table>
<tr><th>Quando</th><th>Cartas</th><th>Sala</th><th>Resultado</th>
<th>Veredito</th><th>Modelo</th></tr>
{mao_tbl}</table></div>

<h2>Caderno do coach — o que ele aprendeu sobre esta pessoa</h2>
{notas_html}

<h2>Perfil de jogo</h2>
{perfil_html}
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

    # A mesma narração do dossiê, aqui com o NOME na frente: a home vira
    # "quem fez o quê agora", e não um dump de nome-de-evento + JSON.
    atos, ultimo = [], []
    for r in m["recent"]:
        n = narrar_evento(r) if e_acao_de_gente(r) else None
        if not n or len(atos) >= 40:
            continue
        tg = r.get("telegram_id")
        if _repetido(n["texto"], tg, ultimo):
            continue
        ts = str(r.get("created_at") or "")
        quem = esc(_quem(r))
        if isinstance(tg, int) and tg > 0:
            quem = f"<a href='/admin/usuario?key={esc(key)}&amp;tg={tg}'>" \
                   f"{quem}</a>"
        atos.append(
            f"<div class='ato {n['classe']}'>"
            f"<span class='hora'>{esc(ts[5:16].replace('T', ' '))}</span>"
            f"<span class='ico'>{n['icone']}</span>"
            f"<span><b>{quem}</b> · {n['texto']}</span></div>")
    feed = "".join(atos) or "<p class='sub'>sem ações registradas.</p>"

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

    aviso_teto = ("<div class='warn'>⚠️ Bati o teto de "
                  f"{_TETO_EVENTOS} eventos na varredura de 30 dias: os "
                  "números abaixo estão <b>incompletos</b> (falta a parte "
                  "mais antiga do mês). Hora de somar no banco em vez de "
                  "contar linha por linha aqui.</div>") if m.get("truncou") \
        else ""

    return f"""<style>{_CSS}</style>
<div class="wrap">
<h1>♠ KKNuths — Portal de Gestão</h1>
<p class="sub">Atualizado agora · dados do Supabase · north star: análises/usuário ativo/semana</p>
{aviso_teto}
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

<h2>O que acabou de acontecer</h2>
<div class="diario">{feed}</div>

<h2>Usuários — funil e custo por pessoa (30 dias)</h2>
<div class="tbl"><table>
<tr><th>Usuário</th><th>Origem</th><th>Entrou em</th><th>Plano</th><th>Interações</th>
<th>Envios</th><th>Perguntas</th><th>Treinos</th><th>Análises (mês)</th>
<th>Custo (mês)</th><th>Erros</th><th>Última ação (UTC)</th></tr>
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

</div>"""
