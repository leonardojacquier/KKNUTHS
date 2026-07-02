"""Handlers do bot Telegram — casca async fina.

Todo o trabalho pesado (LLM, banco, parsing) vive em `processing.py` (síncrono)
e roda via `asyncio.to_thread`: o event loop nunca bloqueia e o bot continua
respondendo aos demais usuários enquanto uma análise longa executa.
"""
from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.agent.embeddings import embed_query
from app.agent.llm import synthesize_answer
from app.analysis import compute_player_stats
from app.bot.processing import RECENT_HANDS, build_drill, process_upload, reveal_drill
from app.config import get_settings
from app.db import get_repository
from app.quota import FREE_MONTHLY_ANALYSES, MAX_UPLOAD_MB

WELCOME = (
    "♠️ *Poker Hand Analyzer*\n\n"
    "Me envie um arquivo de mãos (hand history `.txt` do PokerStars/GGPoker, PDF, "
    "print ou export do seu tracker) e eu analiso suas jogadas, o torneio inteiro "
    "e monto seu perfil de estilo.\n\n"
    "Comandos:\n"
    "• /stats — seu perfil de estilo\n"
    "• /ask <pergunta> — consulte seu histórico de mãos\n"
    "• /treino — drill com uma mão sua\n"
    "• /plano — sobre o beta gratuito\n\n"
    "Para começar, é só mandar o arquivo. 📎"
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(WELCOME)


async def cmd_plano(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(
        "🎁 *Beta gratuito*\n\n"
        f"Você tem {FREE_MONTHLY_ANALYSES} análises por mês, renovadas todo mês.\n"
        "Inclui: análise de mãos e torneios com IA, perfil de estilo, "
        "base de conhecimento (/ask) e drills (/treino).\n\n"
        "Planos pagos com análises ilimitadas chegam em breve."
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id

    def _get_stats():
        repo = get_repository()
        if repo.enabled:
            user = repo.get_or_create_user(tg_id, update.effective_user.username)
            hands = repo.get_all_hands(user["id"]) if user else []
            if hands:
                return compute_player_stats(hands, player=None)
        recent = RECENT_HANDS.get(tg_id, [])
        return compute_player_stats(recent, player=None) if recent else None

    stats = await asyncio.to_thread(_get_stats)
    if not stats or not stats.hands:
        await update.message.reply_text(
            "Ainda não tenho mãos suas. Envie um arquivo para começar."
        )
        return
    await update.message.reply_markdown(
        f"*Seu perfil* ({stats.hands} mãos)\n"
        f"• VPIP {stats.vpip}% | PFR {stats.pfr}% | 3-bet {stats.three_bet}%\n"
        f"• Agressão (AF) {stats.af}\n"
        f"• Estilo: *{stats.label}*"
    )


async def cmd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Pergunta aberta à base de conhecimento (RAG + síntese com modelo barato)."""
    query = " ".join(ctx.args) if ctx.args else ""
    if not query:
        await update.message.reply_text("Uso: /ask <sua pergunta sobre suas mãos>")
        return
    tg_id = update.effective_user.id

    def _search():
        repo = get_repository()
        if not repo.enabled:
            return None, "Base de conhecimento indisponível (persistência off)."
        emb = embed_query(query)
        if emb is None:
            return None, "Busca semântica inativa (embeddings não configurados)."
        user = repo.get_or_create_user(tg_id, update.effective_user.username)
        hits = repo.search_analysis(user["id"], emb, limit=5)
        if not hits:
            return None, "Não achei mãos relacionadas ainda. Envie mais histórico."
        snippets = [h["summary"] for h in hits if h.get("summary")]
        answer = synthesize_answer(query, snippets)
        if answer:
            return answer, None
        return "\n\n".join(f"• {s}" for s in snippets), None

    body, err = await asyncio.to_thread(_search)
    if err:
        await update.message.reply_text(err)
        return
    await _safe_reply(update.message, f"*{query}*\n\n{body}")


async def cmd_treino(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Drill: um spot real das suas mãos — o que você faria?"""
    tg_id = update.effective_user.id
    drill = await asyncio.to_thread(build_drill, tg_id)
    if not drill:
        await update.message.reply_text(
            "Preciso de mãos suas para montar um treino. Envie um arquivo primeiro."
        )
        return
    ctx.user_data["drill"] = drill
    stack = f"{drill['stack_bb']}bb" if drill.get("stack_bb") else "?"
    await update.message.reply_markdown(
        "🎯 *Treino* — o que você faz?\n\n"
        f"Suas cartas: *{' '.join(drill['cards'])}*\n"
        f"Posição: *{drill['position'] or '?'}* | Stack: *{stack}* | "
        f"Blinds: {drill['blinds']}\n"
        f"Formato: {drill['format']}",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Fold", callback_data="drill:fold"),
                    InlineKeyboardButton("Call", callback_data="drill:call"),
                    InlineKeyboardButton("Raise/All-in", callback_data="drill:raise"),
                ]
            ]
        ),
    )


async def on_drill_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    drill = ctx.user_data.get("drill")
    if not drill:
        await query.edit_message_text("Treino expirado. Use /treino para outro.")
        return
    choice = query.data.split(":", 1)[1]
    text = await asyncio.to_thread(reveal_drill, drill, choice)
    ctx.user_data.pop("drill", None)
    await query.edit_message_text(text, parse_mode="Markdown")


async def on_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    doc = update.message.document

    # limite de tamanho ANTES do download (custo e abuso)
    if doc.file_size and doc.file_size > MAX_UPLOAD_MB * 1024 * 1024:
        await update.message.reply_text(
            f"Arquivo grande demais (máx {MAX_UPLOAD_MB:g} MB). "
            "Divida o histórico em partes menores."
        )
        return

    await update.message.reply_text("✅ Recebido. Analisando suas mãos…")
    file = await ctx.bot.get_file(doc.file_id)
    content = bytes(await file.download_as_bytearray())
    fmt = _ext(doc.file_name)
    tg_user = update.effective_user

    reply = await asyncio.to_thread(
        process_upload, content, fmt, tg_user.id, tg_user.username
    )
    await _safe_reply(update.message, reply)


async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Print da mesa enviado como foto (não como arquivo)."""
    await update.message.reply_text("✅ Recebido. Lendo o print…")
    photo = update.message.photo[-1]  # maior resolução
    file = await ctx.bot.get_file(photo.file_id)
    content = bytes(await file.download_as_bytearray())
    tg_user = update.effective_user
    reply = await asyncio.to_thread(
        process_upload, content, "jpg", tg_user.id, tg_user.username
    )
    await _safe_reply(update.message, reply)


async def _safe_reply(message, text: str) -> None:
    """Envia respeitando o limite de 4096 chars do Telegram; se o Markdown do LLM
    vier malformado (entidades desbalanceadas), reenvia como texto puro."""
    from telegram.error import BadRequest

    for start in range(0, len(text), 3900):
        chunk = text[start:start + 3900]
        try:
            await message.reply_markdown(chunk)
        except BadRequest:
            await message.reply_text(chunk)


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
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("treino", cmd_treino))
    app.add_handler(CallbackQueryHandler(on_drill_answer, pattern=r"^drill:"))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    return app


def run_polling() -> None:
    """Modo desenvolvimento: long-polling (sem webhook público)."""
    build_application().run_polling()
