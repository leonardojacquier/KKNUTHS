"""Diagnóstico de saúde do bot — roda no servidor e testa cada integração.

Uso:  cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/diagnose.py

Não imprime segredos (só presença e prefixo mascarado).
"""
from __future__ import annotations

import json
import urllib.request

from app.config import get_settings

OK, FAIL, SKIP = "✅", "❌", "⏭️"


def mask(v: str) -> str:
    return f"{v[:8]}…({len(v)} chars)" if v else "(vazio)"


def main() -> None:
    s = get_settings()
    print("== 1. Variáveis do .env ==")
    for name, val in [
        ("TELEGRAM_BOT_TOKEN", s.telegram_bot_token),
        ("ANTHROPIC_API_KEY", s.anthropic_api_key),
        ("OPENAI_API_KEY", s.openai_api_key),
        ("SUPABASE_URL", s.supabase_url),
        ("SUPABASE_SERVICE_KEY", s.supabase_service_key),
    ]:
        print(f"  {OK if val else FAIL} {name}: {mask(val)}")
    print(f"  modelo de análise: {s.analysis_model} | barato: {s.cheap_model}")

    print("\n== 2. Telegram (getMe) ==")
    if not s.telegram_bot_token:
        print(f"  {SKIP} sem token")
    else:
        try:
            with urllib.request.urlopen(
                f"https://api.telegram.org/bot{s.telegram_bot_token}/getMe", timeout=15
            ) as r:
                me = json.load(r)
            print(f"  {OK} bot @{me['result'].get('username')}")
        except Exception as exc:
            print(f"  {FAIL} {type(exc).__name__}: {exc}")

    print("\n== 3. Anthropic (Claude) ==")
    if not s.anthropic_api_key:
        print(f"  {FAIL} ANTHROPIC_API_KEY ausente no .env")
    else:
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=s.anthropic_api_key)
            try:
                models = [m.id for m in client.models.list(limit=20).data]
                print(f"  {OK} chave válida. Modelos disponíveis: {', '.join(models[:8])}")
                for label, mid in [("análise", s.analysis_model), ("barato", s.cheap_model)]:
                    mark = OK if mid in models else FAIL
                    print(f"  {mark} modelo de {label} '{mid}' "
                          f"{'disponível' if mid in models else 'NÃO está na lista!'}")
            except Exception as exc:
                print(f"  {FAIL} chave rejeitada/erro: {type(exc).__name__}: {exc}")
            # chamada mínima de verdade (usa o modelo barato, ~10 tokens)
            try:
                resp = client.messages.create(
                    model=s.cheap_model, max_tokens=10,
                    messages=[{"role": "user", "content": "responda apenas: ok"}],
                )
                print(f"  {OK} chamada de teste ({s.cheap_model}): "
                      f"{resp.content[0].text.strip()!r}")
            except Exception as exc:
                print(f"  {FAIL} chamada de teste falhou: {type(exc).__name__}: {exc}")
        except ImportError:
            print(f"  {FAIL} pacote 'anthropic' não instalado no venv")

    print("\n== 4. OpenAI (embeddings do /ask) ==")
    if not s.openai_api_key:
        print(f"  {SKIP} sem chave (busca semântica fica inativa)")
    else:
        try:
            from openai import OpenAI

            r = OpenAI(api_key=s.openai_api_key).embeddings.create(
                model="text-embedding-3-small", input="teste"
            )
            print(f"  {OK} embedding ok ({len(r.data[0].embedding)} dims)")
        except Exception as exc:
            print(f"  {FAIL} {type(exc).__name__}: {exc}")

    print("\n== 5. Supabase (memória) ==")
    from app.db import get_repository

    repo = get_repository()
    if not repo.enabled:
        print(f"  {SKIP} não configurado (bot funciona sem memória persistente)")
    else:
        try:
            res = repo.client.table("users").select("id", count="exact").execute()
            print(f"  {OK} conectado — {res.count or 0} usuário(s) na base")
        except Exception as exc:
            print(f"  {FAIL} {type(exc).__name__}: {exc}")

    print("\nDiagnóstico concluído.")


if __name__ == "__main__":
    main()
