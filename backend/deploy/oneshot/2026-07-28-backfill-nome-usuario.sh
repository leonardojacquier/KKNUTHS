#!/usr/bin/env bash
# Recupera o NOME de quem já está no banco como `username: null`.
#
# O primeiro usuário externo (8853316212) entrou, treinou e saiu gravado
# como "None" — o /start não criava a linha, e quem criava passava None no
# nome. O código novo resolve daqui pra frente; este oneshot conserta o
# passado.
#
# `getChat` do Telegram devolve first_name/username de quem JÁ conversou com
# o bot — é leitura, não é busca de gente nova.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json, os, traceback, urllib.request

TOKEN = os.environ.get("TG_TOKEN", "")
CHAT = 6452742024


def diga(t):
    print(t)
    if not TOKEN:
        return
    corpo = json.dumps({"chat_id": CHAT, "text": t[:3800]}).encode()
    r = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=corpo,
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(r, timeout=25)
    except Exception as exc:
        print(f"(envio falhou: {exc})")


def nome_no_telegram(tg_id):
    try:
        with urllib.request.urlopen(
                f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id={tg_id}",
                timeout=20) as r:
            c = json.loads(r.read()).get("result") or {}
    except Exception as exc:
        return None, str(exc)[:80]
    nome = c.get("username") or " ".join(
        x for x in (c.get("first_name"), c.get("last_name")) if x)
    return (nome or None), None


try:
    from app.db import get_repository

    repo = get_repository()
    linhas = (repo.client.table("users").select("id,telegram_id,username")
              .is_("username", "null").execute().data) or []
    partes = [f"{len(linhas)} usuário(s) sem nome no banco"]
    for u in linhas:
        tg = u.get("telegram_id")
        if not tg or tg <= 0:
            continue
        nome, erro = nome_no_telegram(tg)
        if not nome:
            partes.append(f"  {tg}: não recuperado ({erro or 'sem nome'})")
            continue
        repo.client.table("users").update({"username": nome}) \
            .eq("id", u["id"]).execute()
        partes.append(f"  {tg} -> {nome}")
    diga("[nomes]\n" + "\n".join(partes))
except Exception:
    diga("[nomes] EXCEÇÃO:\n" + traceback.format_exc()[-2000:])
PY

exit 0
