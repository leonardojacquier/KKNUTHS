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
from app.config import get_settings
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
    lines = [f"📊 *{len(hands)} mão(s)* lidas de {result.site}.\n"]

    if hands[0].format.value in ("tournament", "sng") and len(hands) > 1:
        rep = analyze_tournament(hands)
        lines.append(rep["summary"])
        if rep.get("biggest_loss"):
            lines.append(f"\nMaior perda: {rep['biggest_loss']['net_bb']:+.1f} BB")
    else:
        a = analyze_hand(hands[0])
        lines.append(a["summary"])

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
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    return app


def run_polling() -> None:
    """Modo desenvolvimento: long-polling (sem webhook público)."""
    build_application().run_polling()
