"""Destilador de lições — popula a biblioteca em silêncio; publicar é humano.

Veredicto do conselho: a lição anônima é o objeto de AQUISIÇÃO (o erro caro
de um aluno vira conteúdo que o público exato — os companheiros de clube —
quer discutir). Mas com 6 alunos que se conhecem, "anônimo" só é anônimo se
a GENERALIZAÇÃO for parte da escrita, não um filtro depois. E uma lição
errada publicada no grupo destrói a credibilidade com esse público — por
isso o destilador NUNCA publica: ele estoca, o dono escolhe (/licoes).

Roda diário no modelo barato; só olha decisões com |EV| relevante (lição
sem número é opinião).

Cron sugerido:  15 9 * * *  cd /app/backend && \
  PYTHONPATH=. ./venv/bin/python scripts/destilar_licoes.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.db import get_repository

EV_MINIMO_BB = 3.0     # decisão que custou/rendeu menos que isso não é lição
_CATEGORIAS = ("preflop", "flop", "turn", "river", "icm")

_PROMPT = (
    "Você escreve LIÇÕES DE POKER anônimas a partir da análise de uma mão "
    "real de um aluno. A lição vai para OUTROS alunos e pode virar conteúdo "
    "público — então a anonimização faz parte da escrita:\n"
    "- NUNCA cite nomes, apelidos, clube, sala, data ou horário\n"
    "- arredonde stacks e pote ('~20bb', 'pote de uns 8bb')\n"
    "- generalize o que não muda a conta (posições podem ficar)\n"
    "- a lição PRECISA do número que a prova (EV em bb, preço em %)\n"
    "- jargão de mesa BR (raise, straight, check behind, high card...)\n"
    "Responda SÓ JSON:\n"
    '{"titulo": "curto e concreto", "spot": "a situação em 2-3 frases", '
    '"licao": "o ensinamento com o número, 2-4 frases", '
    '"ev_bb": -9.3, "categoria": "preflop|flop|turn|river|icm", '
    '"vale": true}\n'
    'Se a análise não render lição clara com número, {"vale": false}.'
)


def validar(bruto: object) -> dict | None:
    """Só lição bem formada entra na biblioteca (função pura)."""
    if not isinstance(bruto, dict) or bruto.get("vale") is not True:
        return None
    titulo = str(bruto.get("titulo") or "").strip()
    spot = str(bruto.get("spot") or "").strip()
    licao = str(bruto.get("licao") or "").strip()
    cat = str(bruto.get("categoria") or "").strip().lower()
    try:
        ev = float(bruto.get("ev_bb"))
    except (TypeError, ValueError):
        return None
    if not titulo or not spot or not licao or cat not in _CATEGORIAS:
        return None
    if abs(ev) < EV_MINIMO_BB:
        return None
    if len(titulo) > 80 or len(spot) > 600 or len(licao) > 800:
        return None
    texto = f"{titulo} {spot} {licao}".lower()
    # anonimização é parte da escrita — se vazou marcador óbvio, descarta
    for proibido in ("pppoker", "suprema", "clubgg", "ggpoker", "clube "):
        if proibido in texto:
            return None
    return {"titulo": titulo, "spot": spot, "licao": licao,
            "ev_bb": round(ev, 1), "categoria": cat}


def candidatas(repo, desde_iso: str, limite: int = 10) -> list[dict]:
    """Análises recentes com erro/acerto caro o bastante pra virar lição."""
    linhas = (repo.client.table("hand_analysis")
              .select("id,summary,ev_loss,mistakes,created_at")
              .gte("created_at", desde_iso)
              .order("created_at", desc=True).limit(60).execute().data) or []
    ja = {l.get("hand_analysis_id") for l in
          ((repo.client.table("licoes").select("hand_analysis_id")
            .execute().data) or [])}
    out = []
    for a in linhas:
        if a["id"] in ja or not a.get("summary"):
            continue
        if str(a["summary"]).startswith("[Follow-up]"):
            continue
        tem_erro = bool(a.get("mistakes"))
        ev = abs(a.get("ev_loss") or 0)
        if tem_erro or ev >= EV_MINIMO_BB:
            out.append(a)
        if len(out) == limite:
            break
    return out


def destilar(analise: dict) -> dict | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.cheap_model, max_tokens=600, temperature=0,
            system=_PROMPT,
            messages=[{"role": "user",
                       "content": str(analise.get("summary"))[:4000]}])
        from app.agent import custo

        custo.registrar(resp, settings.cheap_model, "cron:licoes")
        txt = "".join(b.text for b in resp.content if b.type == "text").strip()
        if txt.startswith("```"):
            txt = txt.split("```", 2)[1].removeprefix("json").strip()
        return validar(json.loads(txt))
    except Exception:
        return None


def main() -> int:
    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase")
        return 0
    desde = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    novas = 0
    for analise in candidatas(repo, desde):
        licao = destilar(analise)
        if not licao:
            continue
        try:
            repo.client.table("licoes").insert(
                {**licao, "hand_analysis_id": analise["id"]}).execute()
            novas += 1
        except Exception:
            pass
    repo.log_event(0, "licoes", "licoes_destiladas", {"novas": novas})
    print(f"lições: {novas} nova(s) na biblioteca")
    return 0


if __name__ == "__main__":
    sys.exit(main())
