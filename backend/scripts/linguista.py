"""Linguista — a camada de IA que APRENDE termos novos, sem tocar no prompt.

O ciclo do "agente que aprende sozinho", aplicado à linguagem:
  capturar  -> textos que o coach entregou nas últimas 24h
  destilar  -> modelo barato aponta calques/traduções que soam estranhas
              a jogador BR e sugere a forma de mesa
  guardar   -> proposta entra na tabela `glossario` com aprovado=false
  aprovar   -> o dono responde /termo ok N (um toque) — o ouvido de
              jogador continua sendo o árbitro
  executar  -> corretor (troca na entrega) e juiz (vigia) leem o glossário

O que a IA NÃO faz aqui, de propósito: editar o prompt (código, protegido
pelo portão de testes) e aprovar a si mesma. Proposta errada morre com
/termo nao N e custa zero; auto-aprovação erraria em silêncio na camada
que contamina todas as análises.

Cron sugerido:  40 7 * * *  cd /opt/poker-bot && \
  PYTHONPATH=. ./venv/bin/python scripts/linguista.py
(antes do juiz das 8h: termo aprovado de manhã já vale na rodada seguinte)
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.db import get_repository

ADMIN_ID = 6452742024

_PROMPT = (
    "Você é um grinder brasileiro de poker revisando textos de um coach. "
    "Aponte APENAS termos que soam a TRADUÇÃO do inglês em vez do jargão "
    "que se fala na mesa no Brasil (ex.: '7 cheio de 2' em vez de 'full de "
    "7 com 2'). NÃO aponte: termos já em inglês (raise, straight, check "
    "behind...), português consagrado (pagar, foldar, trinca, blefar), "
    "gírias regionais válidas, nem estilo/clareza — SÓ tradução literal. "
    "Se não houver nada, devolva lista vazia. Responda SÓ JSON:\n"
    '{"achados": [{"errado": "termo como apareceu", '
    '"certo": "como o grinder fala", "exemplo": "trecho curto onde saiu"}]}'
)


def propostas_do_modelo(textos: list[str]) -> list[dict]:
    """Chama o modelo barato e valida o JSON. Lista vazia em qualquer falha."""
    settings = get_settings()
    if not settings.anthropic_api_key or not textos:
        return []
    try:
        import anthropic

        amostra = "\n\n---\n\n".join(t[:1200] for t in textos[:12])
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.cheap_model, max_tokens=700, temperature=0,
            system=_PROMPT,
            messages=[{"role": "user", "content": amostra}])
        from app.agent import custo

        custo.registrar(resp, settings.cheap_model, "cron:linguista")
        txt = "".join(b.text for b in resp.content if b.type == "text").strip()
        if txt.startswith("```"):
            txt = txt.split("```", 2)[1].removeprefix("json").strip()
        achados = (json.loads(txt) or {}).get("achados") or []
    except Exception:
        return []
    return filtrar(achados)


def filtrar(achados: list) -> list[dict]:
    """Só proposta bem formada, inédita e NA DIREÇÃO CERTA entra.

    Caso real (1ª rodada, 03/08): o modelo barato propôs traduzir top pair,
    flush draw, gutshot e nut flush PARA português — a direção exatamente
    oposta à política, e um dos 'certos' era 'par alto', que é calque
    PROIBIDO. O portão humano segurou (zero aprovadas), mas o filtro tem
    que barrar isso antes de virar notificação: a política da casa mora
    aqui em código, não na boa vontade do modelo.
    """
    from app.agent.llm import TERMOS_REGRA

    regra = TERMOS_REGRA.lower()
    ingles = regra.split("ficam em inglês:", 1)[-1].split("português", 1)[0]
    consagrado_ate_proibidos = regra.split("calques proibidos", 1)[0]
    out, vistos = [], set()
    for a in achados or []:
        errado = str((a or {}).get("errado") or "").strip().lower()
        certo = str((a or {}).get("certo") or "").strip()
        if not errado or not certo or len(errado) < 4 or len(errado) > 60:
            continue
        if errado == certo.lower() or errado in vistos:
            continue
        if f"'{errado}'" in regra:         # o prompt já proíbe este
            continue
        # direção invertida: propor trocar um termo da lista do INGLÊS (ou
        # qualquer termo já sancionado) é o modelo remando contra a política.
        # Basta UMA palavra do termo pertencer ao vocabulário inglês da regra
        # ('nut flush' não está listado inteiro, mas 'flush' está).
        palavras_ingles = set(ingles.replace(",", " ").replace("(", " ")
                              .replace(")", " ").split())
        if errado in consagrado_ate_proibidos or \
                any(p in palavras_ingles for p in errado.split()):
            continue
        # o 'certo' não pode ser um calque que a própria regra proíbe
        if any(f"'{c}'" in regra.split("calques proibidos", 1)[-1]
               for c in (certo.lower(),)) or "par alto" in certo.lower():
            continue
        vistos.add(errado)
        out.append({"errado": errado, "certo": certo[:80],
                    "exemplo": str((a or {}).get("exemplo") or "")[:160]})
    return out[:8]   # teto: proposta é pra ser rara; 50 de uma vez é ruído


def texto_do_aviso(pendentes: list[dict]) -> str:
    l = ["🗣 Linguista — termo(s) novo(s) esperando seu veredito:"]
    for p in pendentes:
        l.append(f"\n#{p['id']}  «{p['errado']}» → «{p['certo']}»")
        if p.get("exemplo"):
            l.append(f'   onde saiu: "{p["exemplo"][:100]}"')
    l.append("\nResponda:  /termo ok N  (juiz vigia) · "
             "/termo ok N corrigir  (troca automática na entrega) · "
             "/termo nao N  (descarta)")
    return "\n".join(l)


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

    day_ago = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    analises = (repo.client.table("hand_analysis").select("summary")
                .gte("created_at", day_ago).limit(25).execute().data) or []
    textos = [str(a.get("summary") or "") for a in analises
              if a.get("summary") and not str(a["summary"]).startswith("[Follow-up]")]
    if not textos:
        print("linguista: sem texto novo nas 24h")
        return 0

    ja_no_glossario = {(l.get("errado") or "").lower() for l in
                       ((repo.client.table("glossario").select("errado")
                         .execute().data) or [])}
    novas = [p for p in propostas_do_modelo(textos)
             if p["errado"] not in ja_no_glossario]

    inseridas = []
    for p in novas:
        try:
            row = (repo.client.table("glossario").insert(p).execute().data
                   or [{}])[0]
            inseridas.append({**p, "id": row.get("id", "?")})
        except Exception:
            pass  # corrida com unique(errado): outra rodada já propôs

    repo.log_event(0, "linguista", "linguista",
                   {"textos": len(textos), "propostas": len(inseridas),
                    "termos": [p["errado"] for p in inseridas]})
    if inseridas and settings.telegram_bot_token:
        notify_admin(settings.telegram_bot_token, texto_do_aviso(inseridas))
    print(f"linguista: {len(textos)} textos, {len(inseridas)} proposta(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
