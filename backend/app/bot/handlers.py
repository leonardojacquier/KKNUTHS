"""Handlers do bot Telegram — casca async fina.

Todo o trabalho pesado (LLM, banco, parsing) vive em `processing.py` (síncrono)
e roda via `asyncio.to_thread`: o event loop nunca bloqueia e o bot continua
respondendo aos demais usuários enquanto uma análise longa executa.
"""
from __future__ import annotations

import asyncio
import re

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
    "♠️ *KKNuths — seu coach de poker*\n\n"
    "Me envie suas mãos de qualquer jeito: arquivo `.txt` de hand history "
    "(GGPoker, PokerStars — inclusive Zoom —, Winamax, PartyPoker, 888poker), "
    "CSV do tracker, print/foto do replay, PDF, áudio — ou *cole o texto da "
    "mão direto aqui* (se o Telegram cortar em partes, eu junto sozinho).\n\n"
    "📊 *Análise e perfil*\n"
    "• /stats — seu perfil de estilo (e com qual pro você parece)\n"
    "• /estilo — cartão visual do seu estilo vs os grandes + plano de transição\n"
    "• /evolucao — sua linha do tempo (VPIP, PFR, resultado…) com gráficos\n"
    "• /torneio — quadro do último campeonato: curva do stack mão a mão\n\n"
    "🎮 *Treino*\n"
    "• /simular — jogue uma mão sua de novo, decisão a decisão\n"
    "• /treino — drill rápido: o que você faria neste spot?\n\n"
    "📐 *Ferramentas*\n"
    "• /range — gráficos 13×13: `/range btn` · `/range sb 10` · "
    "`/range sb 10 ev` · `/range sb 10 icm 1.5`\n"
    "• /ask <pergunta> — busque no seu histórico de mãos\n"
    "• /plano — seu plano e limites\n\n"
    "E converse comigo em texto ou áudio: discorde da análise, peça a tabela, "
    "pergunte qualquer coisa de poker. Para começar, manda uma mão! 📎"
)


async def _set_bot_menu(app: Application) -> None:
    """Menu '/' do Telegram — precisa refletir TODOS os comandos vivos."""
    from telegram import BotCommand

    try:
        await app.bot.set_my_commands([
            BotCommand("stats", "Seu perfil de estilo"),
            BotCommand("estilo", "Você vs os grandes jogadores"),
            BotCommand("evolucao", "Sua linha do tempo com gráficos"),
            BotCommand("torneio", "Quadro do último campeonato"),
            BotCommand("simular", "Rejogue uma mão sua 🎮"),
            BotCommand("treino", "Drill rápido de um spot seu"),
            BotCommand("range", "Gráficos de range 13×13"),
            BotCommand("ask", "Busque no seu histórico"),
            BotCommand("manual", "Manual do jogador em PDF 📖"),
            BotCommand("plano", "Seu plano e limites"),
            BotCommand("start", "Menu inicial"),
        ])
    except Exception:
        pass  # menu é cosmético; nunca derruba o bot


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
    from app.bot.processing import stats_report

    tg_user = update.effective_user
    msg = await asyncio.to_thread(stats_report, tg_user.id, tg_user.username)
    if not msg:
        await update.message.reply_text(
            "Ainda não tenho mãos suas. Envie um arquivo para começar."
        )
        return
    await _safe_reply(update.message, msg)


_EVO_BUTTONS = InlineKeyboardMarkup([[
    InlineKeyboardButton("VPIP", callback_data="evo:vpip"),
    InlineKeyboardButton("PFR", callback_data="evo:pfr"),
    InlineKeyboardButton("3-bet", callback_data="evo:3bet"),
    InlineKeyboardButton("AF", callback_data="evo:af"),
    InlineKeyboardButton("BB 💰", callback_data="evo:bb"),
]])


async def cmd_evolucao(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Linha do tempo do jogador: gráfico de estilo + resultado + caderno.

    `/evolucao vpip` (ou pfr/3bet/af/bb) abre direto um indicador; sem
    argumento, manda o painel completo com botões para trocar de indicador."""
    await _log(update, "evolucao")
    from app.bot.processing import evolution_report, indicator_chart

    tg_id = update.effective_user.id
    arg = (ctx.args[0].lower() if ctx.args else "").replace("3-bet", "3bet")
    if arg:
        png = await asyncio.to_thread(indicator_chart, tg_id, arg)
        if png:
            await update.message.reply_photo(
                png, caption=f"📈 {arg.upper()} ao longo do tempo — KKNuths ♠",
                reply_markup=_EVO_BUTTONS,
            )
            return
        await update.message.reply_text(
            "Indicadores: vpip, pfr, 3bet, af, bb — ou use /evolucao sem nada "
            "para o painel completo."
        )
        return

    png, text = await asyncio.to_thread(evolution_report, tg_id)
    if png:
        try:
            await update.message.reply_photo(
                png, caption="📈 Sua evolução — toque num indicador para ampliar",
                reply_markup=_EVO_BUTTONS,
            )
        except Exception:
            pass
    await _safe_reply(update.message, text)


async def on_evo_indicator(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Botão de indicador do /evolucao: amplia o gráfico escolhido."""
    query = update.callback_query
    await query.answer()
    from app.bot.processing import indicator_chart

    ind = query.data.split(":", 1)[1]
    png = await asyncio.to_thread(indicator_chart, update.effective_user.id, ind)
    if png:
        await query.message.reply_photo(
            png, caption=f"📈 {ind.upper()} ao longo do tempo — KKNuths ♠",
            reply_markup=_EVO_BUTTONS,
        )
    else:
        await query.message.reply_text(
            "Ainda não tenho pontos suficientes para esse indicador."
        )


_STYLE_BUTTONS = InlineKeyboardMarkup([[
    InlineKeyboardButton("Virar TAG", callback_data="est:tag"),
    InlineKeyboardButton("Virar LAG", callback_data="est:lag"),
    InlineKeyboardButton("GTO", callback_data="est:gto"),
    InlineKeyboardButton("Explorador", callback_data="est:exploit"),
]])


async def cmd_estilo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Cartão visual do estilo vs grandes jogadores + botões de transição."""
    await _log(update, "estilo")
    from app.bot.processing import style_report

    tg_user = update.effective_user
    r = await asyncio.to_thread(style_report, tg_user.id, tg_user.username)
    if not r:
        await update.message.reply_text(
            "Preciso de pelo menos ~10 mãos suas para ler seu estilo. "
            "Envie uma sessão e me chame de novo!"
        )
        return
    png, text = r
    if png:
        await update.message.reply_photo(
            png, caption="♠ Seu estilo vs os grandes — toque para traçar a transição",
            reply_markup=_STYLE_BUTTONS,
        )
    await _safe_reply(update.message, text)


async def on_style_target(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Botão 'quero virar X': mostra o caminho e anota a meta no caderno."""
    query = update.callback_query
    await query.answer()
    from app.bot.processing import style_report

    target = query.data.split(":", 1)[1]
    tg_user = update.effective_user
    r = await asyncio.to_thread(style_report, tg_user.id, tg_user.username, target)
    if not r:
        await query.message.reply_text("Preciso de mais mãos suas primeiro.")
        return
    _, text = r
    await _safe_reply(query.message, text)

    def _save_goal():
        repo = get_repository()
        if repo.enabled:
            user = repo.get_or_create_user(tg_user.id, tg_user.username)
            if user:
                repo.save_note(user["id"], "meta",
                               f"Aluno definiu meta de estilo: migrar para {target.upper()}.")

    await asyncio.to_thread(_save_goal)


async def cmd_manual(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia o manual do jogador em PDF (asset gerado da página /manual)."""
    await _log(update, "manual")
    from pathlib import Path

    pdf = Path(__file__).resolve().parent.parent / "api" / "assets" / "KKNuths-Manual.pdf"
    if not pdf.exists():
        await update.message.reply_text(
            "Manual indisponível agora — use /start para ver todos os comandos."
        )
        return
    with pdf.open("rb") as f:
        await update.message.reply_document(
            f, filename="KKNuths-Manual.pdf",
            caption="♠ Manual do Jogador — tudo que o KKNuths faz, com as imagens "
                    "reais. Dúvidas? É só perguntar aqui!",
        )


async def cmd_torneio(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Quadro-resumo do último campeonato enviado (curva do stack + KPIs)."""
    await _log(update, "torneio")
    from app.bot.processing import tournament_board_report

    board = await asyncio.to_thread(tournament_board_report, update.effective_user.id)
    if not board:
        await update.message.reply_text(
            "Ainda não tenho um torneio seu com mãos suficientes. Envie o hand "
            "history do campeonato (arquivo ou colado) que eu monto o quadro."
        )
        return
    png, cap = board
    await update.message.reply_photo(png, caption=cap)


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
    from app.bot.processing import drill_buttons, drill_message

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(b["text"], callback_data=b["callback_data"])
         for b in row]
        for row in drill_buttons(drill)
    ])
    text = drill_message(drill, title="🎯 *Treino* — mão real sua")
    try:
        await update.message.reply_markdown(text, reply_markup=markup)
    except Exception:
        await update.message.reply_text(text, reply_markup=markup)


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
    # o spot vira contexto de conversa: "por que fold?" já funciona em seguida
    LAST_ANALYSIS[update.effective_user.id] = {
        "context": {
            "modo": "discussão de um spot de treino/quiz — o aluno acabou de "
            "responder e pode discordar ou pedir aprofundamento",
            "spot": {k: v for k, v in drill.items() if k != "story"},
            "historia_da_mao": drill.get("story"),
            "escolha_do_aluno": choice,
        },
        "history": [],
        "hand_row_id": None,
        "user_id": None,
    }
    try:
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception:
        # nick com _/* desbalanceia o Markdown legado — reenvia sem formatação
        await query.edit_message_text(text)


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


def _sim_buttons(decision: dict, pos: int) -> InlineKeyboardMarkup:
    """Botões contextuais: com aposta a pagar = Fold/Call/Raise; sem = Check/Bet.

    O índice da decisão vai no callback_data: um duplo-clique no celular não
    pode responder a decisão SEGUINTE (que o usuário nem viu)."""
    if decision["to_call"] > 0:
        row = [
            InlineKeyboardButton("Fold (desistir)", callback_data=f"sim:fold:{pos}"),
            InlineKeyboardButton("Call (pagar)", callback_data=f"sim:call:{pos}"),
            InlineKeyboardButton("Raise (aumentar)", callback_data=f"sim:raise:{pos}"),
        ]
    else:
        row = [
            InlineKeyboardButton("Check (passar)", callback_data=f"sim:check:{pos}"),
            InlineKeyboardButton("Bet (apostar)", callback_data=f"sim:bet:{pos}"),
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
    try:
        await update.message.reply_markdown(
            intro + "\n" + step["narration"],
            reply_markup=_sim_buttons(step["decision"], sim["pos"])
            if step["decision"] else None,
        )
    except Exception:
        # nick com _/* quebra o Markdown legado do Telegram — manda sem formatação
        await update.message.reply_text(
            intro + "\n" + step["narration"],
            reply_markup=_sim_buttons(step["decision"], sim["pos"])
            if step["decision"] else None,
        )


async def on_sim_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    sim = ctx.user_data.get("sim")
    if not sim:
        await query.edit_message_text("Simulação expirada. Use /simular para outra.")
        return
    parts = query.data.split(":")
    choice = parts[1]
    # callback velho (duplo-clique / retoque em mensagem antiga): ignora em vez
    # de registrar resposta numa decisão que o usuário nem viu
    if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) != sim["pos"]:
        return
    if sim["pos"] >= len(sim["events"]):
        return
    sim_choose(sim, choice)
    # remove os botões da mensagem anterior e registra a escolha
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    step = sim_advance(sim)
    if step["decision"]:
        try:
            await query.message.reply_markdown(
                f"Você escolheu: *{choice}*\n" + step["narration"],
                reply_markup=_sim_buttons(step["decision"], sim["pos"]),
            )
        except Exception:
            await query.message.reply_text(
                f"Você escolheu: {choice}\n" + step["narration"],
                reply_markup=_sim_buttons(step["decision"], sim["pos"]),
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


# linhas inconfundíveis de hand history — usadas para distinguir "continuação de
# paste cortado" de "pergunta ao coach" (palavras-chave soltas não bastam: uma
# pergunta como "devo dar fold no river?" também fala de poker)
_HH_LINE = re.compile(
    r"^(?:Poker Hand #|PokerStars |Winamax |Seat \d+: |Dealt to |Board \[|"
    r"Total pot |Uncalled bet \(|"
    r"\*{1,3} (?:HOLE CARDS|FLOP|TURN|RIVER|SHOW ?DOWN|SUMMARY)|"
    r"\S[^\n]*?: (?:folds|checks|calls|bets|raises|posts|shows)\b|"
    r"\S+ collected [\d,.]+ from)",
    re.MULTILINE,
)


# subconjunto INCONFUNDÍVEL: uma pergunta nunca começa assim ("Seat 3: ..."),
# mas pode casar com o formato de ação ("meu oponente: calls tudo, como ajusto?")
_HH_STRICT = re.compile(
    r"^(?:Poker Hand #|PokerStars |Winamax |Seat \d+: |Dealt to |Board \[|"
    r"Total pot |Uncalled bet \(|"
    r"\*{1,3} (?:HOLE CARDS|FLOP|TURN|RIVER|SHOW ?DOWN|SUMMARY)|"
    r"\S+ collected [\d,.]+ from)",
    re.MULTILINE,
)


def _hh_fragment(text: str) -> bool:
    """True se o texto PARECE pedaço de hand history — não pergunta ao coach.

    Multi-linha com formato de HH = continuação. Linha ÚNICA só conta se for de
    formato inconfundível: o formato de ação também casa com pergunta."""
    hits = _HH_LINE.findall(text)
    if len(hits) >= 2 or (hits and "\n" in text.strip()):
        return True
    return bool(_HH_STRICT.search(text))


def _join_paste(pending: str, part: str) -> str:
    """Emenda partes de um paste cortado pelo Telegram.

    O corte acontece no limite de 4096 chars, muitas vezes NO MEIO de uma linha
    (até no meio de um número: 'calls 1,' + '500') — e o resto da linha cortada
    pode ele mesmo parecer uma linha válida ('ro: raises 300' do meio de
    'Hero: raises 300'). O teste decisivo é a COSTURA: se o fim da parte antiga
    + o começo da nova formam uma linha de HH válida, o corte foi no meio da
    linha e a emenda é direta. (Validado por varredura de todos os pontos de
    corte possíveis nos formatos suportados: zero corrupção.)"""
    if pending.endswith("\n") or part.startswith("\n"):
        return pending + part
    last = pending.rsplit("\n", 1)[-1]
    first = part.split("\n", 1)[0]
    if _HH_LINE.match(last + first):
        return pending + part
    if _HH_LINE.match(first) and not _HH_LINE.match(last):
        return pending + "\n" + part
    return pending + part


def _normalize_force_word(text: str) -> str:
    """'Analisar!' / 'análise.' -> 'analisar' / 'analise' (acentos e pontuação)."""
    import unicodedata

    t = text.strip().lower().strip("!?.…,;: ")
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn")


_FORCE_WORDS = {"analisar", "analise", "pronto"}


async def _route_text(update: Update, text: str) -> None:
    """Roteia texto (digitado ou transcrito de voz): hand history ou follow-up.

    Pastes longos chegam cortados pelo Telegram (limite 4096): as partes são
    remontadas via stash/take_paste antes de analisar."""
    tg_user = update.effective_user
    from app.bot.processing import stash_paste, take_paste
    from app.parsers import detect_site

    raw_len = len(text)
    pending, parts = take_paste(tg_user.id)
    is_force_word = _normalize_force_word(text) in _FORCE_WORDS
    if is_force_word and not pending:
        await update.message.reply_text(
            "Não tenho nenhum paste pendente seu (ou ele expirou). Cole o "
            "histórico de novo que eu analiso."
        )
        return
    force = bool(pending) and is_force_word
    continuation = False
    if force:
        text = pending
    elif pending and (detect_site(text) or _hh_fragment(text)):
        text = _join_paste(pending, text)  # continuação do paste cortado
        continuation = True
    elif pending:
        stash_paste(tg_user.id, pending, parts)  # não era continuação; preserva

    if detect_site(text):
        if raw_len >= 3800 and not force:
            # mensagem no limite do Telegram = quase certo que falta o resto
            stash_paste(tg_user.id, text, parts + 1)
            if not continuation:
                await update.message.reply_text(
                    "📄 Recebi a primeira parte — o Telegram corta textos longos, "
                    "então continue colando o resto que eu junto tudo. Se a última "
                    "parte for curta eu percebo sozinho e analiso na hora; se não, "
                    "responda “analisar” quando terminar."
                )
            elif parts + 1 == 2 or (parts + 1) % 5 == 0:
                await update.message.reply_text(
                    f"📄 {parts + 1} partes recebidas — sigo juntando. Responda "
                    "“analisar” quando terminar de colar."
                )
            return
        await update.message.reply_text("✅ Hand history detectada! Analisando…")
        reply = await asyncio.to_thread(
            process_upload, text.encode(), "txt", tg_user.id, tg_user.username
        )
        await _safe_reply(update.message, reply)
        await _send_pending_charts(update.message, tg_user.id)
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
    app = (Application.builder().token(settings.telegram_bot_token)
           .post_init(_set_bot_menu).build())
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("plano", cmd_plano))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("evolucao", cmd_evolucao))
    app.add_handler(CommandHandler("torneio", cmd_torneio))
    app.add_handler(CommandHandler("estilo", cmd_estilo))
    app.add_handler(CommandHandler("manual", cmd_manual))
    app.add_handler(CallbackQueryHandler(on_evo_indicator, pattern=r"^evo:"))
    app.add_handler(CallbackQueryHandler(on_style_target, pattern=r"^est:"))
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
    app.add_error_handler(_on_error)
    return app


async def _on_error(update: object, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Exceção não tratada em handler: loga (arquivo + banco, para o portal de
    gestão) e avisa o usuário — nunca silêncio depois de um 'Analisando…'."""
    import logging

    logging.getLogger("bot").exception("erro não tratado", exc_info=ctx.error)
    tg_id, username = None, None
    if isinstance(update, Update) and update.effective_user:
        tg_id = update.effective_user.id
        username = update.effective_user.username
    try:
        await asyncio.to_thread(
            get_repository().log_event, tg_id or 0, username, "error",
            {"error": str(ctx.error)[:300]},
        )
    except Exception:
        pass
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "😵 Algo deu errado do meu lado agora. Tente de novo em instantes "
                "— se persistir, me mande a mão novamente."
            )
    except Exception:
        pass


def run_polling() -> None:
    """Modo desenvolvimento: long-polling (sem webhook público)."""
    build_application().run_polling()
