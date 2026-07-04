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
from app.bot.processing import (
    LAST_ANALYSIS,
    RECENT_HANDS,
    build_drill,
    build_simulation,
    process_followup,
    process_upload,
    reveal_drill,
    sim_advance,
    sim_choose,
    sim_summary,
)
from app.config import get_settings
from app.db import get_repository
from app.quota import FREE_MONTHLY_ANALYSES, MAX_UPLOAD_MB

WELCOME = (
    "♠️ *Poker Hand Analyzer*\n\n"
    "Me envie suas mãos de qualquer jeito: arquivo `.txt` de hand history "
    "(PokerStars, GGPoker, Winamax, PartyPoker, 888poker), CSV do seu tracker "
    "(HM/PT), print/foto do replay, PDF — ou *cole o texto da mão direto aqui "
    "no chat*. Eu analiso as jogadas, o torneio inteiro e monto seu perfil.\n\n"
    "Comandos:\n"
    "• /stats — seu perfil de estilo\n"
    "• /ask <pergunta> — consulte seu histórico de mãos\n"
    "• /treino — drill rápido com uma mão sua\n"
    "• /simular — jogue uma mão sua decisão a decisão 🎮\n"
    "• /range — gráficos de range 13×13 (opens e Nash) 📊\n"
    "• /plano — sobre o beta gratuito\n\n"
    "Para começar, é só mandar o arquivo. 📎"
)


async def _log(update: Update, event: str, **detail) -> None:
    """Registra a interação em bot_events (não bloqueia nem falha o handler)."""
    u = update.effective_user
    repo = get_repository()
    if repo.enabled and u:
        await asyncio.to_thread(repo.log_event, u.id, u.username, event, detail or None)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    # t.me/BOT?start=<origem> — rastreia de qual convite/grupo o usuário veio
    ref = ctx.args[0][:60] if ctx.args else None
    await _log(update, "start", ref=ref)
    await update.message.reply_markdown(WELCOME)


async def cmd_plano(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _log(update, "plano")
    await update.message.reply_markdown(
        "🎁 *Beta gratuito*\n\n"
        f"Você tem {FREE_MONTHLY_ANALYSES} análises por mês, renovadas todo mês.\n"
        "Inclui: análise de mãos e torneios com IA, perfil de estilo, "
        "base de conhecimento (/ask) e drills (/treino).\n\n"
        "Planos pagos com análises ilimitadas chegam em breve."
    )


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await _log(update, "stats")
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
    await _log(update, "ask", query=query)
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


async def cmd_range(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Gráfico de range 13×13: /range btn · /range sb 10 · /range bb 8."""
    args = [a.lower() for a in (ctx.args or [])]
    await _log(update, "range", query=" ".join(args))
    if not args:
        await update.message.reply_markdown(
            "*Gráficos de range* 📊\n\n"
            "• `/range utg` `mp` `hj` `co` `btn` `sb` — open-raise por posição\n"
            "• `/range sb 10` — Nash de *all-in* do SB com 10bb (frequências)\n"
            "• `/range bb 8` — Nash de *call* do BB contra shove\n"
            "• `/range sb 10 ev` — 💰 *EV de cada mão* (chip-EV)\n"
            "• `/range sb 10 icm 1.5` — 🏆 EV sob *ICM* (bubble factor 1.5)"
        )
        return

    from app.analysis.range_chart import chart_for_query

    mode = args[2] if len(args) > 2 and args[2] in ("ev", "icm") else None
    bf = 1.5
    if mode == "icm" and len(args) > 3:
        try:
            bf = float(args[3].replace(",", "."))
        except ValueError:
            pass
    result = await asyncio.to_thread(
        chart_for_query, args[0], args[1] if len(args) > 1 else None, mode, bf
    )
    if result is None:
        await update.message.reply_text(
            "Não reconheci. Exemplos: /range btn · /range sb 10 · /range bb 8"
        )
        return
    png, caption = result
    import io as _io

    await update.message.reply_photo(photo=_io.BytesIO(png), caption=caption)


async def cmd_treino(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Drill: um spot real das suas mãos — o que você faria?"""
    tg_id = update.effective_user.id
    await _log(update, "treino")
    drill = await asyncio.to_thread(build_drill, tg_id)
    if not drill:
        await update.message.reply_text(
            "Preciso de mãos suas para montar um treino. Envie um arquivo primeiro."
        )
        return
    ctx.user_data["drill"] = drill
    # persiste também no banco: sobrevive a restart do auto-deploy
    await asyncio.to_thread(
        get_repository().set_pending_drill, update.effective_user.id, drill
    )
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
        # quiz diário (enviado pelo cron) ou bot reiniciado: busca no banco
        drill = await asyncio.to_thread(
            get_repository().pop_pending_drill, update.effective_user.id
        )
    if not drill:
        await query.edit_message_text("Treino expirado. Use /treino para outro.")
        return
    choice = query.data.split(":", 1)[1]
    await _log(update, "drill_answer", choice=choice, hand_id=drill.get("hand_id"))
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
    await _send_pending_charts(update.message, tg_user.id)


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
    await _send_pending_charts(update.message, tg_user.id)


def _sim_buttons(decision: dict) -> InlineKeyboardMarkup:
    """Botões contextuais: com aposta a pagar = Fold/Call/Raise; sem = Check/Bet."""
    if decision["to_call"] > 0:
        row = [
            InlineKeyboardButton("Fold (desistir)", callback_data="sim:fold"),
            InlineKeyboardButton("Call (pagar)", callback_data="sim:call"),
            InlineKeyboardButton("Raise (aumentar)", callback_data="sim:raise"),
        ]
    else:
        row = [
            InlineKeyboardButton("Check (passar)", callback_data="sim:check"),
            InlineKeyboardButton("Bet (apostar)", callback_data="sim:bet"),
        ]
    return InlineKeyboardMarkup([row])


async def cmd_simular(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Simulação jogável: replay de uma mão real sua, decisão a decisão."""
    tg_id = update.effective_user.id
    await _log(update, "simular")
    sim = await asyncio.to_thread(build_simulation, tg_id)
    if not sim:
        await update.message.reply_text(
            "Preciso de uma mão sua com a ação completa para simular. "
            "Envie um hand history (.txt) ou um print de replay primeiro."
        )
        return
    ctx.user_data["sim"] = sim
    step = sim_advance(sim)
    intro = (
        "🎮 *Simulação* — jogue a mão como se fosse ao vivo!\n"
        f"Suas cartas: *{' '.join(sim['cards'])}* | Posição: *{sim['position'] or '?'}*\n"
        "No final eu comparo a sua linha (sequência de decisões) com a que "
        "aconteceu de verdade."
    )
    await update.message.reply_markdown(
        intro + "\n" + step["narration"],
        reply_markup=_sim_buttons(step["decision"]) if step["decision"] else None,
    )


async def on_sim_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    sim = ctx.user_data.get("sim")
    if not sim:
        await query.edit_message_text("Simulação expirada. Use /simular para outra.")
        return
    choice = query.data.split(":", 1)[1]
    sim_choose(sim, choice)
    # remove os botões da mensagem anterior e registra a escolha
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    step = sim_advance(sim)
    if step["decision"]:
        await query.message.reply_markdown(
            f"Você escolheu: *{choice}*\n" + step["narration"],
            reply_markup=_sim_buttons(step["decision"]),
        )
        return

    # fim: resumo + contexto para discutir em texto livre
    summary = sim_summary(sim)
    LAST_ANALYSIS[update.effective_user.id] = {
        "context": {
            "simulacao": sim["results"],
            "mao": {
                "cartas": sim["cards"],
                "posicao": sim["position"],
                "resultado_real_bb": sim["net_bb_real"],
            },
        },
        "history": [],
        "hand_row_id": None,
        "user_id": None,
    }
    ctx.user_data.pop("sim", None)
    await _log(update, "sim_done", decisoes=len(sim["results"]))
    await _safe_reply(query.message, summary)

    # modo "e se": o coach avalia a linha ALTERNATIVA que o usuário escolheu
    from app.bot.processing import sim_whatif

    await query.message.reply_text("🧠 Avaliando a SUA linha (modo 'e se')…")
    verdict = await asyncio.to_thread(sim_whatif, sim)
    if verdict:
        await _safe_reply(query.message, "🎓 *Veredito da sua linha:*\n\n" + verdict)
    else:
        await query.message.reply_text(
            "Não consegui gerar o veredito agora — mas o resumo acima já mostra "
            "os preços de cada decisão."
        )


async def _route_text(update: Update, text: str) -> None:
    """Roteia texto (digitado ou transcrito de voz): hand history ou follow-up."""
    tg_user = update.effective_user
    from app.parsers import detect_site

    if detect_site(text):
        await update.message.reply_text("✅ Hand history detectada! Analisando…")
        reply = await asyncio.to_thread(
            process_upload, text.encode(), "txt", tg_user.id, tg_user.username
        )
        await _safe_reply(update.message, reply)
        return

    await update.message.reply_text("🤔 Analisando sua colocação…")
    answer = await asyncio.to_thread(
        process_followup, tg_user.id, tg_user.username, text
    )
    if answer:
        await _safe_reply(update.message, answer)
        await _send_pending_charts(update.message, tg_user.id)
    else:
        await update.message.reply_text(
            "Ainda não tenho nenhuma mão sua para conversar. Envie um arquivo, "
            "print — ou cole o texto da mão aqui — que eu analiso primeiro."
        )


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Texto livre: hand history colada = análise; senão, follow-up (com memória
    recuperada do banco se o bot tiver reiniciado)."""
    await _route_text(update, update.message.text or "")


async def on_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Mensagem de voz: transcreve (Whisper) e roteia como texto."""
    from app.agent.speech import transcribe_audio

    await _log(update, "voice")
    media = update.message.voice or update.message.audio
    file = await ctx.bot.get_file(media.file_id)
    content = bytes(await file.download_as_bytearray())
    text = await asyncio.to_thread(transcribe_audio, content)
    if not text:
        await update.message.reply_text(
            "Não consegui transcrever o áudio agora — pode escrever a pergunta?"
        )
        return
    await update.message.reply_text(f"🎙️ Entendi: “{text}”")
    await _route_text(update, text)


async def on_unsupported(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Nunca deixar o usuário no vácuo, seja qual for o tipo de mensagem."""
    await update.message.reply_text(
        "Esse tipo de mensagem eu ainda não processo. 😅\n"
        "Me mande: hand history (.txt/colada), print/foto da mão, PDF, CSV do "
        "tracker, áudio com sua pergunta — ou use /simular e /treino."
    )


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


async def _send_pending_charts(message, telegram_id: int) -> None:
    """Envia os gráficos de range que o coach usou na análise (se houver)."""
    import io as _io

    from app.bot.processing import pop_charts

    for png, caption in pop_charts(telegram_id):
        try:
            await message.reply_photo(photo=_io.BytesIO(png), caption=caption[:1000])
        except Exception:
            pass


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
    app.add_handler(CommandHandler("range", cmd_range))
    app.add_handler(CommandHandler("simular", cmd_simular))
    app.add_handler(CallbackQueryHandler(on_drill_answer, pattern=r"^drill:"))
    app.add_handler(CallbackQueryHandler(on_sim_answer, pattern=r"^sim:"))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_handler(
        MessageHandler(
            ~filters.TEXT & ~filters.PHOTO & ~filters.Document.ALL
            & ~filters.VOICE & ~filters.AUDIO & ~filters.COMMAND,
            on_unsupported,
        )
    )
    return app


def run_polling() -> None:
    """Modo desenvolvimento: long-polling (sem webhook público)."""
    build_application().run_polling()
