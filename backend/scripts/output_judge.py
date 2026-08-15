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

Cron sugerido:  0 8 * * *  cd /opt/poker-bot && \
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
# calques que não existem no poker BR (regra V3/TERMOS_REGRA). Os quatro
# últimos vieram MEDIDOS das análises reais de julho: aumentou 8x, carta
# alta 7x, sequência 7x — vazavam porque 'aumentar' estava na lista de
# permitidos do prompt e ninguém vigiava os outros.
_CALQUES = ("par grande", "par alto", "mão grande", "sequência de cor",
            "stack fundo", "como valor", " rua ", " etapa ", "igualar o",
            "aumentou", "aumentar", "sequência", "carta alta", "check atrás")
# carta escrita sem ícone: rank maiúsculo + naipe minúsculo ('Kh', '10d').
# 'As' fica de fora de propósito — é artigo em português e daria falso positivo.
_CARTA_CRUA = re.compile(r"\b(?:10|[KQJT98765432])[shdc]\b|\bA[hdc]\b")
# 'sevens full of twos' traduzido ao pé da letra: '7 cheio de 2'. O certo em
# BR é 'full de 7 com 2'. Regex exige rank antes do 'cheio' para não acusar
# uso legítimo ('board cheio de draws').
_FULL_CRU = re.compile(r"\b(?:10|[AKQJT2-9])\s+chei[oa]s?\s+de\b", re.I)
_STREETS = ("flop", "turn", "river", "pré-flop", "pre-flop")


def _e_analise_de_mao(texto: str) -> bool:
    """Resposta que ANALISA uma mão (precisa de selo) vs papo geral sobre
    teoria/range (não precisa). Heurística conservadora: fala de street E
    tem valor em bb."""
    t = texto.lower()
    return any(s in t for s in _STREETS) and bool(re.search(r"\d[\d.,]*\s*bb", t))


def judge_answer(texto: str, conversa: bool = False,
                 calques_extra: tuple = ()) -> list[str]:
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
    for c in _CALQUES + tuple(calques_extra):
        if c in baixo:
            probs.append(f"calque proibido: '{c.strip()}'")
    if _FULL_CRU.search(t):
        probs.append("full house nomeado como 'X cheio de Y' "
                     "(o certo é 'full de X com Y')")
    cruas = set(_CARTA_CRUA.findall(t))
    if cruas:
        probs.append(f"carta sem ícone de naipe: {', '.join(sorted(cruas)[:4])}")
    if len(t) > 3500:
        probs.append(f"resposta longa demais ({len(t)} chars; teto ~3000)")
    if "ferramenta" in baixo or "dados fornecidos" in baixo:
        probs.append("mencionou bastidor do sistema ('ferramenta'/'dados')")
    return probs


def _nota_uma(par: dict) -> dict | None:
    """Nota 0-10 de UMA resposta (modelo barato). None sem chave/falha.

    Por resposta, não por janela: a nota individual acumula em histórico e
    a 'nota geral' vira média móvel de 7 dias — o 3.5 de 05/08 era UMA
    conversa ruim pesando a janela inteira de n=2 e soando como colapso."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.cheap_model, max_tokens=200, temperature=0,
            system=(
                "Você audita UMA resposta de um coach de poker. Nota 0-10 de "
                "CLAREZA no critério do aluno: (a) dá pra saber se jogou "
                "certo ou errado? (b) cada decisão tem um número? (c) curta "
                "e sem enrolação? Responda SÓ JSON: "
                "{\"nota\": 8.5, \"pior\": \"1 frase ou null\"}"),
            messages=[{"role": "user", "content":
                       f"PERGUNTA: {par.get('q', '')[:200]}\n"
                       f"RESPOSTA: {str(par.get('a', ''))[:1500]}"}])
        # o cron também gasta: sem isto o custo total do produto fica menor
        # do que a fatura, que é o jeito clássico de se enganar sozinho
        from app.agent import custo

        custo.registrar(resp, settings.cheap_model, "cron:juiz")
        txt = "".join(b.text for b in resp.content if b.type == "text").strip()
        if txt.startswith("```"):
            txt = txt.split("```", 2)[1].removeprefix("json").strip()
        d = json.loads(txt)
        return {"nota": round(float(d.get("nota")), 1),
                "pior": d.get("pior")}
    except Exception:
        return None


def agregar_notas(avaliadas: list[dict]) -> dict:
    """Média da janela, média por modelo (análises) e a pior resposta.
    Função pura — as três leituras saem das MESMAS notas individuais."""
    com_nota = [a for a in avaliadas if a.get("nota") is not None]
    if not com_nota:
        return {"media": None, "n": 0, "por_modelo": {}, "pior": None}
    media = round(sum(a["nota"] for a in com_nota) / len(com_nota), 1)
    grupos: dict[str, list[float]] = {}
    for a in com_nota:
        if not a.get("conversa"):
            grupos.setdefault(a.get("modelo", "?"), []).append(a["nota"])
    por_modelo = {m: {"media": round(sum(v) / len(v), 1), "n": len(v)}
                  for m, v in grupos.items()}
    pior = min(com_nota, key=lambda a: a["nota"])
    return {"media": media, "n": len(com_nota),
            "por_modelo": por_modelo, "pior": pior}


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


def resumo_de_voz(textos: list[str]) -> dict:
    """Contadores de VOZ — separados da nota, de propósito.

    A nota 0-10 e seus critérios ficam intocados: mudar o texto e a régua
    no mesmo dia faz a média móvel de 7 dias mudar de significado no meio
    da série. Função pura para dar teste sem rede.
    """
    from app.bot.guarda_voz import bloco_pos_placar, problemas_de_voz

    com = {"titulo_fixo": 0, "bastidor": 0, "bloco_longo": 0,
           "autocorrecao": 0, "numero_repetido": 0}
    blocos: list[int] = []
    for t in textos:
        blocos.append(len(bloco_pos_placar(t)))
        for p in problemas_de_voz(t):
            if "título fixo" in p:
                com["titulo_fixo"] += 1
            elif "bastidor" in p:
                com["bastidor"] += 1
            elif "bloco pós-placar" in p:
                com["bloco_longo"] += 1
            elif "autocorreção" in p:
                com["autocorrecao"] += 1
            elif "repetido" in p:
                com["numero_repetido"] += 1
    medios = round(sum(blocos) / len(blocos)) if blocos else 0
    return {"analisadas": len(textos),
            "com_titulo_fixo": com["titulo_fixo"],
            "com_bastidor": com["bastidor"],
            "com_bloco_longo": com["bloco_longo"],
            "com_autocorrecao": com["autocorrecao"],
            "com_numero_repetido": com["numero_repetido"],
            "chars_pos_placar_medio": medios}


def main() -> int:
    settings = get_settings()
    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase")
        return 0

    # VOZ: importa problemas_de_voz que resumo_de_voz() usará para contar
    # defeitos separados da nota (a régua 0-10 não muda).
    from app.bot.guarda_voz import problemas_de_voz  # noqa: F401

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
                .select("summary,created_at,modelo")
                .gte("created_at", day_ago)
                .order("created_at", desc=True).limit(25).execute().data) or []
    for a in analises:
        texto = str(a.get("summary") or "")
        if not texto or texto.startswith("[Follow-up]"):
            continue
        pares.append({"q": "(análise entregue)", "a": texto,
                      "conversa": False,
                      "modelo": (a.get("modelo") or "?").replace(
                          "claude-", "")})

    # glossário vivo: termos que o dono aprovou como 'vigiar' via /termo
    try:
        from app.agent.termos import vigiados

        extra = tuple(vigiados())
    except Exception:
        extra = ()

    achados: list[str] = []
    for p in pares:
        origem = ("conversa" if p.get("conversa")
                  else f"análise·{p.get('modelo', '?')}")
        for prob in judge_answer(str(p.get("a") or ""), conversa=p["conversa"],
                                 calques_extra=extra):
            achados.append(f"[{origem}] {prob} — "
                           f"«{str(p.get('q') or '')[:50]}…»")

    # VOZ: contadores novos, fora da nota. Linha de base de 15/08 (403
    # análises): título fixo 25%, bastidor 23%, bloco pós-placar médio 740.
    voz = resumo_de_voz([str(p.get("a") or "") for p in pares
                         if not p.get("conversa")])
    repo.log_event(0, "output_judge", "voz_do_dia", voz)
    linha_voz = (
        f"\n🗣 VOZ (contadores, fora da nota) — {voz['analisadas']} análises: "
        f"título fixo {voz['com_titulo_fixo']} · bastidor {voz['com_bastidor']} "
        f"· bloco longo {voz['com_bloco_longo']} · pós-placar médio "
        f"{voz['chars_pos_placar_medio']} chars (base 15/08: 740)")

    # nota POR RESPOSTA (teto de 15 por rodada, custo Haiku): cada nota vira
    # evento `nota_resposta` — o histórico que dá a média móvel de 7 dias e
    # o A/B por modelo, tudo das mesmas notas individuais.
    avaliadas: list[dict] = []
    for p in pares[:15]:
        n = _nota_uma(p)
        avaliadas.append({**p, "nota": (n or {}).get("nota"),
                          "pior": (n or {}).get("pior")})
        if n:
            repo.log_event(0, "output_judge", "nota_resposta", {
                "tipo": "conversa" if p.get("conversa") else "análise",
                "modelo": p.get("modelo"), "nota": n["nota"],
                "pior": str(n.get("pior") or "")[:160]})
    agr = agregar_notas(avaliadas)
    notas_por_modelo = (agr["por_modelo"]
                        if len(agr["por_modelo"]) >= 2 else {})

    # média móvel: as notas individuais dos últimos 7 dias
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    hist = (repo.client.table("bot_events").select("detail")
            .eq("event", "nota_resposta").gte("created_at", week_ago)
            .limit(500).execute().data) or []
    notas7 = []
    for h in hist:
        d = h.get("detail") or {}
        d = json.loads(d) if isinstance(d, str) else d
        if isinstance(d.get("nota"), (int, float)):
            notas7.append(float(d["nota"]))
    media7 = round(sum(notas7) / len(notas7), 1) if notas7 else None

    repo.log_event(0, "output_judge", "output_judge", {
        "respostas": len(pares), "problemas": len(achados),
        "nota_clareza": agr["media"], "media_7d": media7,
        "nota_por_modelo": notas_por_modelo or None,
        "detalhe": achados[:10]})

    # com A/B rodando, o juiz SEMPRE fala — comparação silenciosa não decide
    ruim = len(achados) or (agr["media"] or 10) < 7 \
        or bool(notas_por_modelo)
    if ruim and settings.telegram_bot_token:
        n_analises = sum(1 for p in pares if not p["conversa"])
        l = [f"🧪 Juiz da saída — {len(pares)} respostas das últimas 24h "
             f"({n_analises} análises)"]
        if agr["media"] is not None:
            # duas leituras: a janela (o dia) e a média móvel (o produto).
            # Janela de n<4 é anedota — o 3.5 de 05/08 era UMA conversa ruim
            sal = (" ⚠️ amostra pequena — leia com sal"
                   if len(pares) < 4 else "")
            l.append(f"Nota do dia: {agr['media']}/10 "
                     f"(n={agr['n']}){sal}"
                     + (f" · média 7 dias: {media7}/10 "
                        f"(n={len(notas7)})" if media7 is not None else ""))
            pior = agr["pior"]
            if pior and pior["nota"] < 7:
                quem = ("conversa" if pior.get("conversa")
                        else f"análise·{pior.get('modelo', '?')}")
                l.append(f"Pior resposta ({pior['nota']}/10, {quem}): "
                         f"{pior.get('pior') or 'sem detalhe'}")
        if notas_por_modelo:
            l.append("⚖️ A/B por modelo: " + " · ".join(
                f"{m}: {v['media']}/10 ({v['n']} análises)"
                for m, v in sorted(notas_por_modelo.items())))
        if achados:
            l.append(f"\n{len(achados)} problema(s) de forma:")
            l += [f"• {a}" for a in achados[:8]]
        l.append(linha_voz)
        notify_admin(settings.telegram_bot_token, "\n".join(l))
    print(f"juiz: {len(pares)} respostas, {len(achados)} problemas, "
          f"nota {agr['media']} (7d: {media7})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
