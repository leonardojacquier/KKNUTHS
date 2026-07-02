"""Pipeline síncrono de processamento de uploads — o coração do bot.

Sem dependência do SDK do Telegram: recebe bytes, devolve o texto de resposta.
O handler async chama isto via `asyncio.to_thread`, então chamadas lentas (LLM,
banco) não bloqueiam o event loop nem os outros usuários do bot.
"""
from __future__ import annotations

import logging

from app.agent import analyze_hand, analyze_tournament
from app.agent.analyzer import select_key_hands
from app.agent.embeddings import embed_text
from app.agent.llm import coach
from app.analysis import compute_player_stats
from app.db import get_repository
from app.ingestion import ingest
from app.models.canonical import CanonicalHand
from app.quota import MAX_COACHED_HANDS, check_quota, consume_quota

log = logging.getLogger("processing")

# mãos recentes por usuário (para /treino e /stats sem banco). Cap por usuário.
RECENT_HANDS: dict[int, list[CanonicalHand]] = {}
_RECENT_CAP = 300


def remember_hands(telegram_id: int, hands: list[CanonicalHand]) -> None:
    cur = RECENT_HANDS.get(telegram_id, [])
    RECENT_HANDS[telegram_id] = (cur + hands)[-_RECENT_CAP:]


def process_upload(
    content: bytes, fmt: str, telegram_id: int, username: str | None, lang: str = "pt"
) -> str:
    """Processa um arquivo enviado e retorna a resposta (markdown do Telegram)."""
    repo = get_repository()
    user = repo.get_or_create_user(telegram_id, username) if repo.enabled else None

    # ---- cota (P0): protege o custo de LLM mesmo sem billing ----
    quota = check_quota(telegram_id, user, repo)
    if not quota.allowed:
        return (
            "🚦 Você atingiu o limite gratuito deste mês "
            f"({quota.plan}: análises esgotadas).\n"
            "Seu limite renova no próximo mês. Planos pagos chegam em breve!"
        )

    # ---- ingestão ----
    result = ingest(content, source_format=fmt)
    if not result.hands:
        return (
            "Não consegui ler esse arquivo automaticamente. "
            f"({result.note}) Em breve suporto mais formatos."
        )
    hands = result.hands
    remember_hands(telegram_id, hands)

    # ---- persistência (no-op sem Supabase) ----
    hand_row_ids: list[str | None] = []
    if user:
        upload_id = repo.save_upload(
            user["id"], None, result.source_format, result.site, result.confidence
        )
        for h in hands:
            hand_row_ids.append(repo.save_hand(user["id"], h, upload_id))

    # ---- análise determinística ----
    is_tournament = hands[0].format.value in ("tournament", "sng") and len(hands) > 1
    key_hands = None
    if is_tournament:
        structured = analyze_tournament(hands)
        key_hands = select_key_hands(hands, k=MAX_COACHED_HANDS)
    else:
        structured = analyze_hand(hands[0])

    # ---- stats cumulativas (histórico completo quando há banco) ----
    all_hands = repo.get_all_hands(user["id"]) if user else []
    stats_source = all_hands or RECENT_HANDS.get(telegram_id, hands)
    stats = compute_player_stats(stats_source, player=None)
    if user and stats.hands:
        repo.upsert_player_stats(user["id"], stats)

    # ---- coaching (Claude com tools; fallback determinístico) ----
    coaching = coach(structured, stats.__dict__, lang=lang, key_hands=key_hands)

    # ---- base de conhecimento ----
    if user and hand_row_ids and hand_row_ids[0]:
        try:
            embedding = embed_text(coaching)
            repo.save_hand_analysis(hand_row_ids[0], structured, coaching, embedding)
        except Exception as exc:
            log.warning("falha ao gravar análise/embedding: %s", exc)

    # ---- consumo de cota ----
    consume_quota(telegram_id, user, repo)
    quota_after = check_quota(telegram_id, user, repo)

    # ---- evento (visibilidade de dashboard) ----
    repo.log_event(
        telegram_id,
        username,
        "upload",
        {
            "format": result.source_format,
            "site": result.site,
            "hands": len(hands),
            "confidence": result.confidence,
            "is_tournament": is_tournament,
            "quota_remaining": quota_after.remaining,
        },
    )

    header = f"📊 *{len(hands)} mão(s)* lidas de {result.site}.\n"
    footer = ""
    if quota_after.remaining >= 0:
        footer = f"\n\n_Análises restantes no mês: {quota_after.remaining}_"
    return header + "\n" + coaching + footer


def build_drill(telegram_id: int) -> dict | None:
    """Monta um spot de treino a partir das mãos do usuário (mais recente primeiro
    com hero conhecido). Retorna None se não houver material."""
    import random

    hands = list(RECENT_HANDS.get(telegram_id, []))
    repo = get_repository()
    if not hands and repo.enabled:
        user = repo.get_or_create_user(telegram_id, None)
        if user:
            hands = repo.get_all_hands(user["id"], limit=200)
    candidates = [h for h in hands if h.hero and h.hero_cards and h.stakes.big_blind]
    if not candidates:
        return None

    h = random.choice(candidates)
    seat = h.hero_seat()
    stack_bb = round((seat.stack / h.stakes.big_blind), 1) if seat else None
    analysis = analyze_hand(h)

    # ação real do herói no preflop (primeira não-post)
    actual = "fold"
    for s in analysis["spots"]:
        if s["street"] == "preflop":
            actual = "raise" if s["decision"] == "aggression" else "call"
            break

    return {
        "hand_id": h.hand_id,
        "cards": h.hero_cards,
        "position": analysis["position"],
        "stack_bb": stack_bb,
        "blinds": f"{h.stakes.small_blind:g}/{h.stakes.big_blind:g}",
        "format": h.format.value,
        "actual": actual,
        "net_bb": analysis["net_bb"],
        "summary": analysis["summary"],
    }


def reveal_drill(drill: dict, choice: str) -> str:
    """Compara a escolha do usuário com o que aconteceu + referência push/fold."""
    lines = [
        f"Você escolheu: *{choice.upper()}*",
        f"Na mão real você fez: *{drill['actual'].upper()}* "
        f"(resultado: {drill['net_bb']:+.1f} BB)",
    ]
    stack_bb = drill.get("stack_bb")
    if stack_bb and stack_bb <= 20 and drill["format"] in ("tournament", "sng"):
        from app.analysis.pushfold import push_fold

        pf = push_fold(drill["cards"], stack_bb, drill.get("position") or "MP")
        if pf.get("applicable"):
            lines.append(
                f"📐 Referência Nash ({stack_bb}bb, {drill['position']}): "
                f"*{pf['decision'].upper()}* — sua mão está no top {pf['hand_top_pct']}%, "
                f"range de shove ≈ {pf['shove_range_pct']}%."
            )
    lines.append(f"\n_{drill['summary']}_")
    return "\n".join(lines)
