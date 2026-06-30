"""Handlers do bot Telegram.

Fluxo de UX: usuário envia arquivo -> bot responde "recebido, analisando…" na hora
-> processa (síncrono no esqueleto; vai para fila RQ na produção) -> envia resultado.

Requer `python-telegram-bot`. Mantido isolado para não afetar testes de parser/math.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.agent import analyze_hand, analyze_tournament
from app.agent.analyzer import llm_summary
from app.analysis import compute_player_stats
from app.config import get_settings
from app.db import get_repository
from app.ingestion import ingest

WELCOME = (
    "♠️ *Poker Hand Analyzer*\n\n"
    "Me envie um arquivo de mãos (hand history `.txt`, PDF, print ou export do seu "
    "tracker) e eu analiso suas jogadas, o torneio inteiro e monto seu perfil de estilo.\n\n"
    "Comandos:\n"
    "• /start — este menu\n"
    "• /stats — seu perfil de estilo\n"
    "• /plano — planos e cobrança\n\n"
    "Para começar, é só mandar o arquivo. 📎"
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(WELCOME)


async def cmd_plano(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(
        "*Planos*\n"
        "• Free — 20 mãos/mês, 1 torneio\n"
        "• Pro — análise completa, perfil de estilo, relatórios semanais\n"
        "• Premium — ilimitado, deep-dive com solver, prioridade\n\n"
        "Use /assinar para gerar seu link de pagamento."
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    repo = get_repository()
    if not repo.enabled:
        await update.message.reply_text(
            "Perfil ainda não disponível (persistência não configurada). "
            "Envie mãos e eu calculo na hora."
        )
        return
    user = repo.get_or_create_user(update.effective_user.id, update.effective_user.username)
    stats = repo.client.table("player_stats").select("*").eq("user_id", user["id"]).execute()
    if not stats.data:
        await update.message.reply_text("Ainda não tenho mãos suas. Envie um arquivo para começar.")
        return
    s = stats.data[0]
    await update.message.reply_markdown(
        f"*Seu perfil* ({s['hands']} mãos)\n"
        f"• VPIP {s['vpip']}% | PFR {s['pfr']}% | 3-bet {s['three_bet']}%\n"
        f"• Agressão (AF) {s['af']}\n"
        f"• Estilo: *{s['label']}*"
    )


async def on_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document
    await update.message.reply_text("✅ Recebido. Analisando suas mãos…")

    file = await ctx.bot.get_file(doc.file_id)
    content = bytes(await file.download_as_bytearray())
    fmt = _ext(doc.file_name)

    result = ingest(content, source_format=fmt, filename=doc.file_name or "")
    if not result.hands:
        await update.message.reply_text(
            "Não consegui ler esse arquivo automaticamente. "
            f"({result.note}) Em breve suporto mais formatos."
        )
        return

    hands = result.hands
    tg_user = update.effective_user

    # persistência (no-op se Supabase não configurado)
    repo = get_repository()
    user = repo.get_or_create_user(tg_user.id, tg_user.username) if repo.enabled else None
    upload_id = None
    if user:
        upload_id = repo.save_upload(user["id"], None, result.source_format, result.site,
                                     result.confidence)
        for h in hands:
            repo.save_hand(user["id"], h, upload_id)

    # análise + coaching (Claude se configurado; senão resumo determinístico)
    lines = [f"📊 *{len(hands)} mão(s)* lidas de {result.site}.\n"]
    if hands[0].format.value in ("tournament", "sng") and len(hands) > 1:
        structured = analyze_tournament(hands)
    else:
        structured = analyze_hand(hands[0])

    stats = compute_player_stats(hands, hands[0].hero) if hands[0].hero else None
    if user and stats:
        repo.upsert_player_stats(user["id"], stats)

    coaching = llm_summary(structured, stats.__dict__ if stats else None, lang="pt")
    lines.append(coaching)

    await update.message.reply_markdown("\n".join(lines))


def _ext(filename: str | None) -> str:
    if not filename or "." not in filename:
        return "txt"
    return filename.rsplit(".", 1)[-1].lower()


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado")
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("plano", cmd_plano))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    return app


def run_polling() -> None:
    """Modo desenvolvimento: long-polling (sem webhook público)."""
    build_application().run_polling()
