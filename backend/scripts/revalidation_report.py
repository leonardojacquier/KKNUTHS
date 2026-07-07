"""Revalidação + relatório mão a mão para um usuário — roda no VPS.

Uso: python scripts/revalidation_report.py <telegram_id> [chat_destino]

`chat_destino` (opcional): envia a CÓPIA para outro chat (ex.: admin conferindo
o que o usuário recebeu) sem notificar o usuário nem gravar evento.

1. Carrega o torneio mais recente do usuário no banco.
2. Coach analisa os PADRÕES (folds, c-bets, all-ins) com os stacks corretos.
3. Envia: mensagem de revalidação + quadro do torneio (foto) + relatório
   mão a mão (documento HTML).
"""
from __future__ import annotations

import json
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.llm import followup, set_tool_user  # noqa: E402
from app.analysis.handreport import (  # noqa: E402
    _played, build_report_html, hand_class, played_facts,
)
from app.analysis.handsearch import search_hands  # noqa: E402
from app.analysis.tournament_board import render_tournament_board  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import get_repository  # noqa: E402
from scripts.tg_send_doc import send_document  # noqa: E402


def _send_text(token: str, chat_id: int, text: str) -> None:
    body = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=20).read()


def _send_photo(token: str, chat_id: int, png: bytes, caption: str) -> None:
    import mimetypes
    import uuid

    boundary = uuid.uuid4().hex

    def field(name, value):
        return (f"--{boundary}\r\nContent-Disposition: form-data; "
                f"name=\"{name}\"\r\n\r\n{value}\r\n").encode()

    body = field("chat_id", str(chat_id)) + field("caption", caption[:1024])
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; "
             f"filename=\"board.png\"\r\nContent-Type: image/png\r\n\r\n").encode()
    body += png + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    urllib.request.urlopen(req, timeout=60).read()


def per_hand_llm(hands_played) -> dict[str, str]:
    """Análise 2-3 frases POR MÃO (lotes de 6) — só com os números calculados."""
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        return {}
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    out: dict[str, str] = {}
    batch = 6
    for i in range(0, len(hands_played), batch):
        chunk = hands_played[i:i + batch]
        payload = []
        for h in chunk:
            f = played_facts(h)
            a = f["analysis"]
            payload.append({
                "hand_id": h.hand_id,
                "mao": hand_class(h.hero_cards),
                "posicao": a.get("position"),
                "stack_bb": a.get("hero_stack_bb"),
                "efetivo_bb": a.get("effective_bb"),
                "blinds": a.get("blinds"),
                "historia": f["story"],
                "numeros_calculados": f["numbers"],
                "resultado_bb": a.get("net_bb"),
            })
        prompt = (
            "Você é um coach profissional de MTT. Para CADA mão abaixo, escreva "
            "uma análise de 2-3 frases em português: julgue as decisões do herói "
            "usando APENAS os numeros_calculados fornecidos (equity, pot odds, "
            "sizing) e os stacks dados — NUNCA invente números nem estime stacks. "
            "Seja específico e direto (estilo coach). Responda SOMENTE um JSON "
            "{hand_id: analise}.\n\n" + json.dumps(payload, ensure_ascii=False)
        )
        try:
            resp = client.messages.create(
                model=settings.analysis_model, max_tokens=1800,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = "".join(b.text for b in resp.content if b.type == "text").strip()
            if raw.startswith("```"):
                raw = raw.strip("`\n")
                raw = raw[raw.index("{"):]
            out.update(json.loads(raw[raw.index("{"):raw.rindex("}") + 1]))
        except Exception as exc:
            print(f"lote {i//batch}: LLM falhou ({exc}) — fallback determinístico")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    update_mode = "--update" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tg_id = int(args[0])
    dest = int(args[1]) if len(args) > 1 else tg_id
    admin_copy = dest != tg_id
    settings = get_settings()
    repo = get_repository()
    if not settings.telegram_bot_token or not repo.enabled:
        print("precisa de TELEGRAM_BOT_TOKEN e Supabase")
        return 1

    user = repo.get_or_create_user(tg_id, None)
    all_hands = repo.get_all_hands(user["id"]) if user else []
    tourneys = [h for h in all_hands if h.tournament_id]
    if len(tourneys) < 3:
        print("sem torneio suficiente no banco")
        return 1
    latest = max(tourneys, key=lambda h: h.played_at or "")
    hands = sorted((h for h in tourneys if h.tournament_id == latest.tournament_id),
                   key=lambda h: h.played_at or "")
    print(f"torneio #{latest.tournament_id}: {len(hands)} mãos")

    # ---- coach: análise dos padrões com stacks corretos ----
    set_tool_user(user["id"])
    folds = search_hands(hands, "fold", limit=30)
    cbets = search_hands(hands, "cbet", limit=15)
    allins = search_hands(hands, "allin", limit=10)
    coach_text = followup(
        {
            "modo": "REVALIDAÇÃO pós-correção de stacks: a equipe corrigiu um bug "
            "em que o stack do herói era estimado errado (ex.: '12bb' quando era "
            "58bb). Reanalise os PADRÕES deste torneio com os dados corretos "
            "abaixo (tudo em BB, com stack efetivo). Seja específico e cite mãos.",
            "instrucao": "3 blocos curtos: (1) seus FOLDS — algum fold caro/errado? "
            "(2) seus C-BETS — padrão de sizing; (3) seus ALL-INS — vs equilíbrio "
            "com o stack EFETIVO. Feche com 1 leak principal e 1 ponto forte.",
            "folds_do_torneio": folds,
            "cbets_do_torneio": cbets,
            "allins_do_torneio": allins,
        },
        [], "Revalide meus padrões deste torneio, mão a mão nos momentos-chave.",
    ) or ""
    print(f"coach: {len(coach_text)} chars")

    # ---- análise POR MÃO (as jogadas) ----
    played = [h for h in hands if _played(h)]
    per_hand = per_hand_llm(played)
    print(f"análises por mão: {len(per_hand)}/{len(played)}")

    # ---- monta e envia ----
    board_png, board_cap = render_tournament_board(hands)
    html = build_report_html(hands, coach_text, board_png,
                             per_hand_analysis=per_hand)
    tmp = Path(tempfile.gettempdir()) / f"KKNuths-MaoAMao-{latest.tournament_id}.html"
    tmp.write_text(html, encoding="utf-8")

    token = settings.telegram_bot_token
    if update_mode:
        _send_text(
            token, dest,
            ("👁 Cópia de admin — versão 2 do relatório:" if admin_copy else
             "📋 Relatório mão a mão ATUALIZADO — agora com análise em TODAS "
             "as mãos e o Nº de cada mão da sala, para você conferir no "
             "PokerCraft/HM. Obrigado pelo feedback! 🙏"),
        )
        out = send_document(str(dest), tmp,
                            "Versão 2 — análise completa mão a mão.")
        print("documento:", out.get("ok"))
        return 0
    if admin_copy:
        _send_text(token, dest,
                   f"👁 Cópia de admin — o que o usuário {tg_id} recebeu:")
    _send_text(
        token, dest,
        "🔎 Revalidação concluída!\n\n"
        "Encontramos e corrigimos um erro que afetava análises anteriores: o "
        "coach às vezes usava o VALOR DO BIG BLIND como se fosse o seu stack "
        "(ex.: dizia \"12bb\" quando você tinha 58bb). Agora ele recebe os "
        "stacks reais de toda a mesa — inclusive o stack EFETIVO, que é o que "
        "manda num all-in.\n\n"
        "Reanalisei seu torneio inteiro com os dados corretos. Está chegando:\n"
        "1️⃣ o quadro do campeonato (curva do seu stack)\n"
        "2️⃣ o RELATÓRIO MÃO A MÃO — as 54 mãos, uma a uma, com sua linha, "
        "stacks e veredito nos spots de all-in\n"
        "3️⃣ a leitura dos seus padrões (folds, c-bets, all-ins) vai dentro do "
        "relatório\n\n"
        "Para abrir qualquer mão: me diga as cartas ou o momento (ex.: \"abre a "
        "mão do A3o no BB\"). "
        "E se tiver o arquivo daquela MESA FINAL (blinds 6k/12k), me manda — "
        "refaço o 98o e o BTN com os stacks efetivos certos. 🃏",
    )
    _send_photo(token, dest, board_png, board_cap)
    out = send_document(str(dest), tmp,
                        "📋 Relatório mão a mão — abra no navegador. Para discutir "
                        "uma mão, me diga as cartas aqui no chat.")
    print("documento:", out.get("ok"))
    if not admin_copy:
        repo.log_event(tg_id, None, "revalidation_sent",
                       {"tournament": latest.tournament_id, "hands": len(hands)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
