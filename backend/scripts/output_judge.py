"""Juiz da SAÍDA — audita as respostas que o coach realmente mandou.

Os canários existentes checam a MATEMÁTICA (verdict vs solver, imagem vs
solver). Nada checava se o TEXTO saiu bom — quem descobria era o aluno
("a saída tá uma merda", "não sei se joguei certo ou errado"). Este script
lê as últimas respostas reais (conversation_state.history) e cobra o
contrato: selo de veredito, número em cada decisão, sem jargão proibido,
sem calque, cartas com ícone.

Checagem determinística (custo zero). Se houver ANTHROPIC_API_KEY, uma
segunda passada com modelo barato dá nota 0-10 de clareza — o mesmo
critério que o aluno usa.

Cron sugerido:  0 8 * * *  cd /app/backend && \
  PYTHONPATH=. ./venv/bin/python scripts/output_judge.py
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

from app.config import get_settings
from app.db import get_repository

ADMIN_ID = 6452742024

_SELOS = ("✅", "🟡", "❌")
# auto-elogio que o prompt proíbe (o selo já fala por si)
_ADJETIVOS = ("resumo brutal", "verdade honesta", "papo reto", "na lata",
              "sem enrolação", "sem rodeios")
# calques que não existem no poker BR (regra V3/TERMOS_REGRA)
_CALQUES = ("par grande", "par alto", "mão grande", "sequência de cor",
            "stack fundo", "como valor", " rua ", " etapa ", "igualar o")
# carta escrita sem ícone: rank maiúsculo + naipe minúsculo ('Kh', '10d').
# 'As' fica de fora de propósito — é artigo em português e daria falso positivo.
_CARTA_CRUA = re.compile(r"\b(?:10|[KQJT98765432])[shdc]\b|\bA[hdc]\b")
_STREETS = ("flop", "turn", "river", "pré-flop", "pre-flop")


def _e_analise_de_mao(texto: str) -> bool:
    """Resposta que ANALISA uma mão (precisa de selo) vs papo geral sobre
    teoria/range (não precisa). Heurística conservadora: fala de street E
    tem valor em bb."""
    t = texto.lower()
    return any(s in t for s in _STREETS) and bool(re.search(r"\d[\d.,]*\s*bb", t))


def judge_answer(texto: str, conversa: bool = False) -> list[str]:
    """Problemas de FORMA numa resposta do coach (lista vazia = passou).
    Função pura — é o contrato que o prompt promete ao aluno.

    `conversa=True` para turno de follow-up. O selo de veredito é o cabeçalho
    da ANÁLISE entregue, não de toda resposta: quando o aluno pergunta "não
    seria melhor o shove de 11bb?", a resposta certa explica a alternativa —
    carimbar ✅/🟡/❌ na primeira linha ali é ruído, não contrato.
    """
    t = (texto or "").strip()
    if not t:
        return ["resposta vazia"]
    probs: list[str] = []

    if _e_analise_de_mao(t) and not conversa:
        primeira = t.split("\n", 1)[0]
        if not any(primeira.startswith(s) for s in _SELOS):
            probs.append("análise de mão SEM selo de veredito na 1ª linha")
        # placar: quando há 2+ streets citadas, cada uma devia vir com selo
        streets_citadas = sum(1 for s in _STREETS if s in t.lower())
        selos_no_corpo = sum(t.count(s) for s in _SELOS)
        if streets_citadas >= 3 and selos_no_corpo < 2:
            probs.append("mão de várias streets sem placar street a street")
        # conta: 'pedia X%' sem número, ou promessa de equity sem valor
        if re.search(r"equity", t, re.I) and not re.search(r"\d+\s*%", t):
            probs.append("cita equity sem nenhum número")

    baixo = t.lower()
    for frase in _ADJETIVOS:
        if frase in baixo:
            probs.append(f"auto-elogio proibido: '{frase}'")
    for c in _CALQUES:
        if c in baixo:
            probs.append(f"calque proibido: '{c.strip()}'")
    cruas = set(_CARTA_CRUA.findall(t))
    if cruas:
        probs.append(f"carta sem ícone de naipe: {', '.join(sorted(cruas)[:4])}")
    if len(t) > 3500:
        probs.append(f"resposta longa demais ({len(t)} chars; teto ~3000)")
    if "ferramenta" in baixo or "dados fornecidos" in baixo:
        probs.append("mencionou bastidor do sistema ('ferramenta'/'dados')")
    return probs


def _nota_llm(pares: list[dict]) -> dict | None:
    """Nota 0-10 de clareza pelas respostas reais (modelo barato, sem tools).
    None se não houver chave — a checagem determinística já rodou."""
    settings = get_settings()
    if not settings.anthropic_api_key or not pares:
        return None
    try:
        import anthropic

        amostra = "\n\n---\n\n".join(
            f"PERGUNTA: {p.get('q','')[:200]}\nRESPOSTA: {str(p.get('a',''))[:1200]}"
            for p in pares[:6])
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.cheap_model, max_tokens=500, temperature=0,
            system=(
                "Você audita um coach de poker. Para o conjunto de respostas "
                "abaixo, dê uma nota 0-10 de CLAREZA no critério do aluno: "
                "(a) dá pra saber se ele jogou certo ou errado? (b) cada "
                "decisão tem um número? (c) é curta e sem enrolação? "
                "Responda SÓ JSON: {\"nota\": 8.5, \"pior\": \"o que mais "
                "atrapalha, 1 frase\", \"exemplo\": \"trecho curto\"}"),
            messages=[{"role": "user", "content": amostra}])
        # o cron também gasta: sem isto o custo total do produto fica menor
        # do que a fatura, que é o jeito clássico de se enganar sozinho
        from app.agent import custo

        custo.registrar(resp, settings.cheap_model, "cron:juiz")
        txt = "".join(b.text for b in resp.content if b.type == "text").strip()
        if txt.startswith("```"):
            txt = txt.split("```", 2)[1].removeprefix("json").strip()
        return json.loads(txt)
    except Exception:
        return None


def notify_admin(token: str, text: str) -> bool:
    body = json.dumps({"chat_id": ADMIN_ID, "text": text[:4000]}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("ok", False)
    except Exception:
        return False


def main() -> int:
    settings = get_settings()
    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase")
        return 0

    # JANELA de 24h nos dois artefatos: o texto gravado é imutável, então
    # auditar "os últimos N" faz o mesmo estoque antigo reprovar todo dia —
    # depois do conserto do preâmbulo, o juiz seguiu apontando 5 análises
    # pré-conserto como se fossem o produto corrente. O juiz é diário; cada
    # rodada mede o que foi ENTREGUE desde a anterior, não o museu.
    from datetime import datetime, timedelta, timezone

    day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    rows = (repo.client.table("conversation_state")
            .select("telegram_id,state,updated_at")
            .gte("updated_at", day_ago)
            .order("updated_at", desc=True).limit(20).execute().data) or []
    pares: list[dict] = []
    for r in rows:
        for turno in ((r.get("state") or {}).get("history") or []):
            if turno.get("a"):
                pares.append({**turno, "telegram_id": r["telegram_id"],
                              "conversa": True})
    pares = pares[:40]

    # As ANÁLISES entregues — o artefato que o contrato do selo descreve. O
    # juiz lia só o histórico de conversa, que é follow-up puro, e cobrava
    # dali um selo que nunca deveria estar lá: dois falsos positivos por dia
    # e a análise de verdade nunca auditada.
    analises = (repo.client.table("hand_analysis")
                .select("summary,created_at")
                .gte("created_at", day_ago)
                .order("created_at", desc=True).limit(25).execute().data) or []
    for a in analises:
        texto = str(a.get("summary") or "")
        if not texto or texto.startswith("[Follow-up]"):
            continue
        pares.append({"q": "(análise entregue)", "a": texto,
                      "conversa": False})

    achados: list[str] = []
    for p in pares:
        origem = "conversa" if p.get("conversa") else "análise"
        for prob in judge_answer(str(p.get("a") or ""), conversa=p["conversa"]):
            achados.append(f"[{origem}] {prob} — "
                           f"«{str(p.get('q') or '')[:50]}…»")

    # a nota de clareza também via só conversa. Mistura os dois artefatos,
    # senão a nota mede o papo e não o produto.
    amostra = ([p for p in pares if p["conversa"]][:3]
               + [p for p in pares if not p["conversa"]][:3])
    nota = _nota_llm(amostra or pares)
    repo.log_event(0, "output_judge", "output_judge", {
        "respostas": len(pares), "problemas": len(achados),
        "nota_clareza": (nota or {}).get("nota"),
        "detalhe": achados[:10]})

    ruim = len(achados) or ((nota or {}).get("nota") or 10) < 7
    if ruim and settings.telegram_bot_token:
        n_analises = sum(1 for p in pares if not p["conversa"])
        l = [f"🧪 Juiz da saída — {len(pares)} respostas das últimas 24h "
             f"({n_analises} análises)"]
        if nota:
            l.append(f"Nota de clareza: {nota.get('nota')}/10")
            if nota.get("pior"):
                l.append(f"Pior ponto: {nota['pior']}")
        if achados:
            l.append(f"\n{len(achados)} problema(s) de forma:")
            l += [f"• {a}" for a in achados[:8]]
        notify_admin(settings.telegram_bot_token, "\n".join(l))
    print(f"juiz: {len(pares)} respostas, {len(achados)} problemas, "
          f"nota {(nota or {}).get('nota')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
