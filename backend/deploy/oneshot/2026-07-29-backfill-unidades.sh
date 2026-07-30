#!/usr/bin/env bash
# Backfill das unidades nas mãos antigas de VISÃO + reanálise das afetadas.
#
# A varredura das 17 mãos de visão achou três com a escala furada, todas do
# dono:
#   vision-87dab199478b (19/07) bb 4000 com stacks 181.5 -> CORRIGÍVEL
#   vision-4c718b0a064f (09/07) bb 200  com stacks 244.3 -> ambígua
#   vision-7148abd71930 (09/07) bb 0    com stacks 98331 -> bb ilegível
#
# Só a primeira dá pra consertar com prova: o maior stack menor que um big
# blind é impossível. Nas outras duas eu NÃO invento número — elas passam a
# sair com a profundidade vazia e o coach pedindo o dado.
#
# O backfill varre TODAS as mãos de imagem, não só essas três: se o mesmo
# defeito estiver em alguma que a varredura por SQL não pegou, aqui pega.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json, os, traceback, urllib.request

TOKEN = os.environ.get("TG_TOKEN", "")
DONO = 6452742024
REANALISAR = ["vision-87dab199478b", "vision-4c718b0a064f",
              "vision-7148abd71930"]


def mandar(texto, markdown=False):
    if not TOKEN:
        return
    for i in range(0, len(texto), 3800):
        corpo = {"chat_id": DONO, "text": texto[i:i + 3800]}
        if markdown:
            corpo["parse_mode"] = "Markdown"
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data=json.dumps(corpo).encode(),
            headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=30)
        except Exception as exc:
            print(f"envio falhou: {exc}")


try:
    from app.agent import analyzer
    from app.agent.llm import _coerir_unidades, coach
    from app.db import get_repository
    from app.models.canonical import CanonicalHand

    repo = get_repository()
    # paginado e filtrado em Python de propósito: filtro JSON do PostgREST
    # que não casa devolve lista VAZIA, e "0 mãos" lê-se como sucesso. Aqui,
    # se a leitura falhar, falha alto.
    todas, passo = [], 500
    for pagina in range(20):
        lote = (repo.client.table("hands").select("id,hand_id,canonical")
                .order("created_at")
                .range(pagina * passo, pagina * passo + passo - 1)
                .execute().data) or []
        todas += lote
        if len(lote) < passo:
            break
    linhas = [h for h in todas
              if (h.get("canonical") or {}).get("source_format") == "image"]

    corrigidas, relatorio = [], [f"{len(todas)} mão(s) no banco, "
                                 f"{len(linhas)} de visão"]
    if not linhas:
        raise RuntimeError("nenhuma mão de visão encontrada — leitura suspeita")
    for linha in linhas:
        try:
            mao = CanonicalHand.model_validate(linha["canonical"])
        except Exception as exc:
            relatorio.append(f"  {linha['hand_id']}: não abriu ({exc})"[:120])
            continue
        if not _coerir_unidades(mao.stakes, mao.players):
            continue
        repo.client.table("hands").update(
            {"canonical": json.loads(mao.model_dump_json())}) \
            .eq("id", linha["id"]).execute()
        corrigidas.append(linha["hand_id"])
        ctx = analyzer.analyze_hand(mao)
        relatorio.append(f"  ✅ {linha['hand_id']}: herói agora "
                         f"{ctx['hero_stack_bb']}bb, efetivo "
                         f"{ctx['effective_bb']}bb")

    relatorio.append(f"\n{len(corrigidas)} corrigida(s) no banco")
    mandar("[backfill unidades]\n" + "\n".join(relatorio))

    # reanálise: mostra o que o coach diz AGORA em cada uma das três
    for hid in REANALISAR:
        try:
            linha = (repo.client.table("hands").select("canonical")
                     .eq("hand_id", hid).limit(1).execute().data)
            if not linha:
                mandar(f"[{hid}] não achei no banco")
                continue
            mao = CanonicalHand.model_validate(linha[0]["canonical"])
            ctx = analyzer.analyze_hand(mao)
            cab = (f"[{hid}]\nstack {ctx.get('hero_stack_bb')} · efetivo "
                   f"{ctx.get('effective_bb')} · blinds {ctx.get('blinds')}\n"
                   + ("⚠️ " + ctx["stacks_ilegiveis"][:200] + "\n"
                      if ctx.get("stacks_ilegiveis") else "")
                   + "--- análise nova ---\n")
            mandar(cab + coach(ctx, None, lang="pt"))
        except Exception as exc:
            mandar(f"[{hid}] falhou na reanálise: {type(exc).__name__}: {exc}")
except Exception:
    mandar("[backfill unidades] EXCEÇÃO:\n" + traceback.format_exc()[-2000:])
PY

exit 0
