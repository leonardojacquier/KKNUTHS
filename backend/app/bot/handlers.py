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
    LAST_UPLOAD_KIND,
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

# boas-vindas CURTA + 3 botões: primeiro contato não pode ser muro de comandos
# (conselho: provável causa de churn). O guia completo fica no botão.
WELCOME_SHORT = (
    "♠️ *KKNuths — seu coach de poker*\n\n"
    "Eu analiso as SUAS mãos com números calculados de verdade — equity, "
    "preço do call, Nash — e te digo o que foi decisão boa e o que custou "
    "caro.\n\n"
    "Já deixei um torneio de teste carregado pra você experimentar. "
    "Por onde quer começar?"
)

WELCOME = (
    "♠️ *KKNuths — seu coach de poker*\n\n"
    "Me envie suas mãos de qualquer jeito: arquivo `.txt` de hand history "
    "(GGPoker, PokerStars — inclusive Zoom —, Winamax, PartyPoker, 888poker), "
    "CSV do tracker, print/foto do replay, PDF, áudio — ou *cole o texto da "
    "mão direto aqui* (se o Telegram cortar em partes, eu junto sozinho).\n\n"
    "🧠 *Motor KKN* — estatística bayesiana + a ciência de 2 Prêmios Nobel: "
    "leaks precificados em bb/100, KKN Tilt Detector e leitura de vilão em "
    "odds, dentro das análises e do /stats.\n\n"
    "📊 *Análise e perfil*\n"
    "• /stats — perfil de estilo, leaks em bb/100 e KKN Tilt Detector\n"
    "• /estilo — cartão visual do seu estilo vs os grandes + plano de transição\n"
    "• /evolucao — sua linha do tempo (VPIP, PFR, resultado…) com gráficos\n"
    "• /torneio — quadro do último torneio: curva do stack mão a mão\n"
    "• /relatorio — o torneio inteiro analisado, mão por mão (HTML)\n\n"
    "🎮 *Treino*\n"
    "• /preparar — briefing pré-torneio: seus leaks, protocolo mental e metas\n"
    "• /simular — jogue uma mão sua de novo, decisão a decisão\n"
    "• /treino — drill rápido: o que você faria neste spot?\n\n"
    "📐 *Ferramentas*\n"
    "• /range — gráficos 13×13: `/range btn` · `/range sb 10` · "
    "`/range sb 10 ev` · `/range sb 10 icm 1.5`\n"
    "• /ask <pergunta> — busque no seu histórico de mãos\n"
    "• /manual — o manual do jogador em PDF\n"
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
            BotCommand("torneio", "Quadro do último torneio"),
            BotCommand("relatorio", "Relatório mão a mão 📋"),
            BotCommand("preparar", "Preparação pré-torneio 🎯"),
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


def _uname(u) -> str | None:
    """Identificação legível do usuário: @username quando existe; senão o NOME
    do perfil (o Telegram entrega, nós jogávamos fora — portal ficava cego)."""
    return u.username or (u.full_name or None)


async def _log(update: Update, event: str, **detail) -> None:
    """Registra a interação em bot_events (não bloqueia nem falha o handler)."""
    u = update.effective_user
    repo = get_repository()
    if repo.enabled and u:
        await asyncio.to_thread(repo.log_event, u.id, _uname(u), event, detail or None)


_START_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎯 Treinar agora (mão de teste)", callback_data="go:treino")],
    [InlineKeyboardButton("📤 Enviar minhas mãos", callback_data="go:enviar")],
    [InlineKeyboardButton("❓ Como funciona", callback_data="go:guia")],
])

_ENVIAR_TXT = (
    "📤 *Me mande suas mãos do jeito mais fácil pra você:*\n\n"
    "📸 *Print/foto* do replay ou da mesa — eu leio a mão inteira\n"
    "📄 *Arquivo .txt* de hand history (GGPoker: PokerCraft → download; "
    "PokerStars: pasta HandHistory)\n"
    "📋 *Texto colado* direto aqui (cortou em partes? eu junto sozinho)\n"
    "🔗 *Link de replay* do PPPoker — é só colar\n"
    "🎙️ *Áudio* contando a mão\n\n"
    "💡 Manda o torneio INTEIRO num arquivo que eu monto o relatório "
    "mão a mão completo."
)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    # t.me/BOT?start=<origem> — rastreia de qual convite/grupo o usuário veio
    ref = ctx.args[0][:60] if ctx.args else None
    await _log(update, "start", ref=ref)
    await update.message.reply_markdown(WELCOME_SHORT, reply_markup=_START_KB)


async def on_go(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Botões do /start: primeiro contato guiado, sem muro de comandos."""
    query = update.callback_query
    await query.answer()
    action = query.data.split(":", 1)[1]
    if action == "treino":
        await _log(update, "go_treino")
        await _send_treino(query.message, update.effective_user.id, ctx)
    elif action == "enviar":
        await query.message.reply_markdown(_ENVIAR_TXT)
    else:
        await query.message.reply_markdown(WELCOME)


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
    msg = await asyncio.to_thread(stats_report, tg_user.id, _uname(tg_user))
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
    InlineKeyboardButton("Exploit", callback_data="est:exploit"),
]])


async def cmd_estilo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Cartão visual do estilo vs grandes jogadores + botões de transição."""
    await _log(update, "estilo")
    from app.bot.processing import style_report

    tg_user = update.effective_user
    r = await asyncio.to_thread(style_report, tg_user.id, _uname(tg_user))
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
    r = await asyncio.to_thread(style_report, tg_user.id, _uname(tg_user), target)
    if not r:
        await query.message.reply_text("Preciso de mais mãos suas primeiro.")
        return
    _, text = r
    await _safe_reply(query.message, text)

    def _save_goal():
        repo = get_repository()
        if repo.enabled:
            user = repo.get_or_create_user(tg_user.id, _uname(tg_user))
            if user:
                repo.save_note(user["id"], "meta",
                               f"Aluno definiu meta de estilo: migrar para {target.upper()}.")

    await asyncio.to_thread(_save_goal)


async def cmd_relatorio(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Relatório mão a mão do último torneio, sob demanda."""
    import io as _io

    await _log(update, "relatorio_cmd")
    await update.message.reply_text("📋 Montando o relatório mão a mão do seu "
                                    "último torneio… (leva ~1 min)")
    from app.bot.processing import report_doc_for_user

    tg_user = update.effective_user
    doc = await asyncio.to_thread(report_doc_for_user, tg_user.id, _uname(tg_user))
    if not doc:
        await update.message.reply_text(
            "Ainda não tenho um torneio seu com mãos suficientes (mínimo 8). "
            "Manda o arquivo do torneio que eu preparo o relatório."
        )
        return
    data, fname, caption = doc
    await update.message.reply_document(
        document=_io.BytesIO(data), filename=fname, caption=caption[:1000]
    )


async def cmd_preparar(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Briefing pré-torneio: leaks a vigiar, protocolo mental, plano por fase
    e 2 metas da sessão (que o relatório pós-torneio vai cobrar)."""
    tg_user = update.effective_user
    await update.message.reply_text(
        "🎯 Montando sua preparação com base nas suas mãos… (~20s)")
    from app.bot.processing import prepare_report

    args_text = " ".join(ctx.args) if ctx.args else ""
    briefing = await asyncio.to_thread(
        prepare_report, tg_user.id, _uname(tg_user), args_text)
    if not briefing:
        await update.message.reply_text(
            "Preciso conhecer seu jogo primeiro — me manda um torneio ou "
            "algumas mãos e depois pede /preparar de novo."
        )
        return
    await _safe_reply(update.message, briefing, simplify_btn=True)
    await _send_pending_charts(update.message, tg_user.id)


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
            "history do torneio (arquivo ou colado) que eu monto o quadro."
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
            return None, "Não consegui buscar no seu histórico agora — tenta de novo daqui a pouco. 🙏"
        emb = embed_query(query)
        if emb is None:
            return None, "Não consegui buscar no seu histórico agora — tenta de novo daqui a pouco. 🙏"
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
        # sem argumento: BOTÕES (sintaxe de CLI assusta iniciante). O texto
        # com a sintaxe completa continua embaixo pra quem quer o avançado.
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Open UTG", callback_data="rng:utg"),
             InlineKeyboardButton("Open CO", callback_data="rng:co"),
             InlineKeyboardButton("Open BTN", callback_data="rng:btn")],
            [InlineKeyboardButton("Shove SB 10bb", callback_data="rng:sb 10"),
             InlineKeyboardButton("Call BB 10bb", callback_data="rng:bb 10")],
            [InlineKeyboardButton("EV do shove (10bb)", callback_data="rng:sb 10 ev"),
             InlineKeyboardButton("EV sob ICM", callback_data="rng:sb 10 icm")],
        ])
        await update.message.reply_markdown(
            "*Gráficos de range* 📊 — toca num botão, ou digite:\n"
            "`/range hj` `mp` `sb` · `/range sb 8` · `/range bb 12 icm 2`",
            reply_markup=kb)
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


async def on_range_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Botões do /range: mesma consulta do comando, em 1 toque."""
    query = update.callback_query
    await query.answer("Montando o gráfico… 📊")
    from app.analysis.range_chart import chart_for_query

    args = query.data.split(":", 1)[1].split()
    mode = args[2] if len(args) > 2 and args[2] in ("ev", "icm") else None
    result = await asyncio.to_thread(
        chart_for_query, args[0], args[1] if len(args) > 1 else None, mode, 1.5)
    if result is None:
        await query.message.reply_text("Não consegui montar esse gráfico agora.")
        return
    import io as _io
    await query.message.reply_photo(photo=_io.BytesIO(result[0]),
                                    caption=result[1])


async def cmd_treino(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Drill: um spot real das suas mãos — o que você faria?"""
    await _log(update, "treino")
    await _send_treino(update.message, update.effective_user.id, ctx)


async def _send_treino(message, tg_id: int, ctx) -> None:
    """Monta e envia um treino (usado pelo /treino e pelo botão do /start)."""
    drill = await asyncio.to_thread(build_drill, tg_id)
    if not drill:
        await message.reply_text(
            "Preciso de mãos suas para montar um treino. Envie um arquivo primeiro."
        )
        return
    ctx.user_data["drill"] = drill
    # persiste também no banco: sobrevive a restart do auto-deploy
    await asyncio.to_thread(get_repository().set_pending_drill, tg_id, drill)
    from app.bot.processing import drill_buttons, drill_message

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(b["text"], callback_data=b["callback_data"])
         for b in row]
        for row in drill_buttons(drill)
    ])
    text = drill_message(drill, title="🎯 *Treino* — mão real sua")
    # figura da mesa: o spot lê melhor como imagem (custo zero de LLM). A
    # imagem mostra cartas/board/pote/preço; o caption fica só com a história.
    import io as _io2
    fig = None
    try:
        from app.analysis.hand_figure import render_hand_figure, spot_from_drill
        fig = await asyncio.to_thread(render_hand_figure, spot_from_drill(drill))
    except Exception:
        fig = None
    try:
        if fig:
            # MESMA lógica do quiz: história + "sua vez" com pote e preço. A
            # figura ilustra; o texto traz a pergunta completa.
            cap = "🎯 *Treino* — mão real sua"
            if drill.get("story"):
                cap += "\n\n" + drill["story"]
            cap += f"\n\n👉 *Sua vez no {(drill.get('street') or '').upper()}* — " \
                   f"pote *{drill.get('pot_bb', 0):g}bb*"
            if drill.get("to_call_bb"):
                cap += f" | pagar *{drill['to_call_bb']:g}bb*"
                if drill.get("required_eq"):
                    cap += f" (precisa ~{drill['required_eq'] * 100:.0f}%)"
            cap += "\n\n*O que você faz?*"
            await message.reply_photo(
                photo=_io2.BytesIO(fig), caption=cap[:1000],
                parse_mode="Markdown", reply_markup=markup)
        else:
            await message.reply_markdown(text, reply_markup=markup)
    except Exception:
        await message.reply_text(text, reply_markup=markup)


async def _show_reveal(query, text: str) -> None:
    """Mostra o gabarito. Se a mensagem do quiz tem texto (quiz diário), edita.
    Se foi enviada como FOTO (a figura da mesa do /treino), não dá pra editar
    texto — então tira os botões e manda o gabarito como mensagem nova."""
    msg = query.message
    if getattr(msg, "text", None):
        for kw in ({"parse_mode": "Markdown"}, {}):
            try:
                await msg.edit_text(text, **kw)
                return
            except Exception:
                continue
    try:
        await msg.edit_reply_markup(reply_markup=None)  # trava re-resposta
    except Exception:
        pass
    for kw in ({"parse_mode": "Markdown"}, {}):
        try:
            await msg.reply_text(text, **kw)
            return
        except Exception:
            continue


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
        await _show_reveal(query, "Treino expirado. Use /treino para outro.")
        return
    choice = query.data.split(":", 1)[1]
    # navegação do menu (Raise ▸ tamanhos / Voltar): troca só o teclado da
    # mensagem, nada de reveal. O drill volta pro estado (ctx + banco) — o
    # pop lá em cima não pode engolir o quiz num mero toque de menu.
    if choice in ("sizes", "back"):
        from app.bot.processing import drill_buttons, drill_size_buttons

        rows = (drill_size_buttons if choice == "sizes" else drill_buttons)(drill)
        try:
            await query.edit_message_reply_markup(reply_markup=_kb(rows))
        except Exception:
            pass
        ctx.user_data["drill"] = drill
        await asyncio.to_thread(
            get_repository().set_pending_drill, update.effective_user.id, drill)
        return
    await _log(update, "drill_answer", choice=choice, hand_id=drill.get("hand_id"))
    # os botões pós-reveal agem sobre ESTA mão. Quando o quiz veio do banco
    # (quiz diário do cron), o LAST_HAND_META deste processo está vazio — e o
    # "Simular esta mão" caía noutra mão. Grava a referência aqui, SEMPRE.
    from app.bot.processing import LAST_HAND_META as _LHM
    _LHM[update.effective_user.id] = {
        "hand_id": drill.get("hand_id"),
        "position": drill.get("position"),
        "stack_bb": drill.get("stack_bb"),
    }
    text = await asyncio.to_thread(reveal_drill, drill, choice)
    # streak: razão de voltar amanhã (o push das 19h traz; o 🔥 segura)
    try:
        streak = await asyncio.to_thread(
            get_repository().quiz_streak_days, update.effective_user.id)
        if streak >= 2:
            text += f"\n\n🔥 *{streak} dias seguidos de treino!* Não quebra a corrente."
        elif streak == 1:
            text += "\n\n🔥 Treino de hoje feito — volta amanhã pra começar a sequência."
    except Exception:
        pass
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
    await _show_reveal(query, text)

    # storyboard da revelação: o filme da mão até a decisão, com a matemática e
    # o veredito. Determinístico (custo zero de LLM); só some se algo falhar.
    try:
        from app.analysis.hand_figure import render_hand_strip
        from app.bot.processing import storyboard_spot_from_drill

        spec = await asyncio.to_thread(storyboard_spot_from_drill, drill, choice)
        if spec:
            # placar semanal: registra o veredito da resposta (boa/ruim/mista)
            await _log(update, "drill_verdict",
                       verdict=spec.get("verdict"),
                       hand_id=drill.get("hand_id"))
            png = await asyncio.to_thread(render_hand_strip, spec)
            import io as _io3
            await query.message.reply_photo(
                photo=_io3.BytesIO(png),
                caption="🎬 *O filme da mão* — do pré à sua decisão.",
                parse_mode="Markdown")
    except Exception:
        pass

    # próximos passos em UM TOQUE (pedir pra digitar comando é fricção)
    try:
        from app.analysis.hand_figure import spot_from_drill
        ctx.user_data["share_spot"] = spot_from_drill(drill)
    except Exception:
        pass
    try:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔁 Simular esta mão", callback_data="pa:sim"),
            InlineKeyboardButton("🎯 Outro treino", callback_data="go:treino"),
        ], [
            InlineKeyboardButton("📖 Range do spot", callback_data="pa:range"),
            InlineKeyboardButton("📣 Desafiar os amigos", callback_data="pa:share"),
        ]])
        await query.message.reply_text("E agora?", reply_markup=kb)
    except Exception:
        pass


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
        process_upload, content, fmt, tg_user.id, _uname(tg_user), "pt",
        update.message.caption,
    )
    await _safe_reply(update.message, reply,
                      kind=LAST_UPLOAD_KIND.get(tg_user.id))
    await _send_pending_charts(update.message, tg_user.id)


async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Print da mesa enviado como foto (não como arquivo)."""
    await update.message.reply_text("✅ Recebido. Lendo o print…")
    photo = update.message.photo[-1]  # maior resolução
    file = await ctx.bot.get_file(photo.file_id)
    content = bytes(await file.download_as_bytearray())
    tg_user = update.effective_user
    reply = await asyncio.to_thread(
        process_upload, content, "jpg", tg_user.id, _uname(tg_user), "pt",
        update.message.caption,
    )
    await _safe_reply(update.message, reply,
                      kind=LAST_UPLOAD_KIND.get(tg_user.id))
    await _send_pending_charts(update.message, tg_user.id)


def _kb(rows: list[list[dict]]) -> InlineKeyboardMarkup:
    """Converte linhas de botões-dict (processing) em InlineKeyboardMarkup."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(b["text"], callback_data=b["callback_data"])
         for b in row]
        for row in rows
    ])


def _sim_menu_args(sim: dict, decision: dict, pos: int) -> tuple:
    """(pot_bb, to_call_bb, stack_bb) da decisão atual — régua dos menus."""
    bb = sim.get("bb") or 1
    fig = (sim.get("figures") or {}).get(str(pos)) or {}
    return (round(decision["pot"] / bb, 1),
            round(decision["to_call"] / bb, 1),
            fig.get("stack_bb"))


def _sim_buttons(sim: dict, decision: dict, pos: int) -> InlineKeyboardMarkup:
    """Menu principal da simulação (Fold/Call + Raise ▸ ou Check + Bet ▸).
    Apertar Raise/Bet abre o submenu de tamanhos (dois toques, como numa sala).

    O índice da decisão vai no callback_data: um duplo-clique no celular não
    pode responder a decisão SEGUINTE (que o usuário nem viu)."""
    from app.bot.processing import action_menu_rows

    pot_bb, tc_bb, stack_bb = _sim_menu_args(sim, decision, pos)
    return _kb(action_menu_rows(pot_bb, tc_bb, stack_bb, "sim", f":{pos}"))


def _sim_size_buttons(sim: dict, decision: dict, pos: int) -> InlineKeyboardMarkup:
    """Submenu de tamanhos da simulação (abre no toque em Raise/Bet)."""
    from app.bot.processing import size_menu_rows

    pot_bb, tc_bb, stack_bb = _sim_menu_args(sim, decision, pos)
    return _kb(size_menu_rows(pot_bb, tc_bb, stack_bb, "sim", f":{pos}"))


async def _send_sim_step(msg, sim: dict, step: dict, prefix: str = "") -> None:
    """Envia um passo da simulação: a FIGURA da mesa daquela decisão (o gráfico
    que o aluno quer ver) + a narração como legenda + botões. Cai pra texto se
    não houver figura ou o render falhar. A narração de cada passo é curta (só
    o que rolou desde a última decisão), então cabe na legenda."""
    text = prefix + step["narration"]
    kb = _sim_buttons(sim, step["decision"], sim["pos"]) if step["decision"] else None
    fig = None
    if step["decision"]:
        spot = (sim.get("figures") or {}).get(str(sim["pos"]))
        if spot:
            try:
                from app.analysis.hand_figure import render_hand_figure
                fig = await asyncio.to_thread(render_hand_figure, spot)
            except Exception:
                fig = None
    if fig:
        import io as _io
        try:
            await msg.reply_photo(photo=_io.BytesIO(fig), caption=text[:1000],
                                  parse_mode="Markdown", reply_markup=kb)
            return
        except Exception:
            pass
    try:
        await msg.reply_markdown(text, reply_markup=kb)
    except Exception:
        await msg.reply_text(text, reply_markup=kb)


async def _send_hand_film(msg, telegram_id: int, hand_id, lead: str) -> None:
    """Mostra o FILME da mão inteira (fallback pra mão sem decisão jogável, ex.:
    herói foldou o pré). Cai pra texto se não der pra renderizar."""
    from app.bot.processing import hand_film

    png = await asyncio.to_thread(hand_film, telegram_id, hand_id)
    if not png:
        await msg.reply_text(lead)
        return
    import io as _io
    try:
        await msg.reply_photo(photo=_io.BytesIO(png), caption=lead[:1000],
                              parse_mode="Markdown")
    except Exception:
        try:
            await msg.reply_markdown(lead)
        except Exception:
            await msg.reply_text(lead)


async def cmd_simular(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Simulação jogável: replay de uma mão real sua, decisão a decisão."""
    tg_id = update.effective_user.id
    await _log(update, "simular")
    # /simular cai na MÃO QUE VOCÊ ESTÁ VENDO (último quiz/treino/análise), não
    # numa mão qualquer. Só usa a "melhor" quando não há mão recente.
    from app.bot.processing import LAST_HAND_META

    preferred = (LAST_HAND_META.get(tg_id) or {}).get("hand_id")
    swapped = False
    sim = await asyncio.to_thread(build_simulation, tg_id, preferred)
    # /simular = A MESMA mão do treino/quiz. NUNCA troca por outra só porque é
    # curta — o aluno quer jogar A MÃO QUE ele viu. Só cai na melhor se a mão
    # atual não dá mesmo pra simular (print/histórico sem ação).
    if sim and sim.get("unsimulable"):
        swapped = True
        sim = await asyncio.to_thread(build_simulation, tg_id, None)
    if not sim or sim.get("unsimulable"):
        await update.message.reply_text(
            "Preciso de uma mão sua com a ação completa para simular. "
            "Envie um hand history (.txt) ou um print de replay primeiro."
        )
        return
    if sim.get("dead_end"):
        # herói foldou o pré (ou teve só uma decisão de fold): não há jogada pra
        # rejogar. Em vez do beco sem saída, mostra o filme de como a mão terminou.
        await _send_hand_film(
            update.message, tg_id, sim.get("hand_id"),
            "🃏 Nessa mão você *foldou o pré-flop*, então não tem decisão sua "
            "pra rejogar. Mas aqui está o *filme* de como ela terminou 👇")
        return
    ctx.user_data["sim"] = sim
    step = sim_advance(sim)
    intro = (
        "🎮 *Simulação* — jogue a mão como se fosse ao vivo!\n"
        + ("_Essa mão específica não tinha a ação completa; peguei uma sua "
           "jogável._\n" if swapped else "")
        + "No final eu comparo a sua linha com a que aconteceu de verdade."
    )
    await _send_sim_step(update.message, sim, step, prefix=intro + "\n")


async def on_sim_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    sim = ctx.user_data.get("sim")
    if not sim:
        # a pergunta da simulação agora é FOTO: não dá pra editar texto. Tira
        # os botões e responde — senão o clique morre em silêncio (bug real).
        await _show_reveal(query, "Simulação expirada. Use /simular para outra.")
        return
    parts = query.data.split(":")
    raw = parts[1]
    # callback velho (duplo-clique / retoque em mensagem antiga): ignora em vez
    # de registrar resposta numa decisão que o usuário nem viu
    if len(parts) > 2 and parts[2].isdigit() and int(parts[2]) != sim["pos"]:
        return
    if sim["pos"] >= len(sim["events"]):
        return
    # navegação do menu (Raise ▸ tamanhos / Voltar): só troca o teclado da
    # MESMA mensagem — nada é registrado como resposta
    if raw in ("sizes", "back"):
        e = sim["events"][sim["pos"]]
        kb = (_sim_size_buttons if raw == "sizes" else _sim_buttons)(
            sim, e, sim["pos"])
        try:
            await query.edit_message_reply_markup(reply_markup=kb)
        except Exception:
            pass
        return
    # botões com sizing (raise3x/betpot/...): registra a ação-base + o tamanho
    # legível — o resumo compara pelo verbo ("raise" vs "raise") e o aluno vê
    # o sizing que escolheu ("raise 3x", "bet ½ pote")
    _SIZES = {"raise3x": "raise 3x", "raisepot": "raise pote",
              "bet33": "bet ⅓ pote", "bet50": "bet ½ pote",
              "betpot": "bet pote"}
    if raw == "allin":
        # all-in enfrentando aposta = raise; sem aposta = bet (o verbo certo
        # é o que o resumo compara com a ação real)
        e = sim["events"][sim["pos"]]
        choice = "raise all-in" if e["to_call"] > 0 else "bet all-in"
    else:
        choice = _SIZES.get(raw, raw)
    sim_choose(sim, choice)
    # remove os botões da mensagem anterior e registra a escolha
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    # FOLD encerra a mão: você saiu, não há mais decisão sua. Sem isto o
    # simulador seguia pedindo as próximas jogadas (bug que irritou o Leo).
    if choice == "fold":
        await query.message.reply_text(
            "🚪 Você *foldou* — encerrou a mão aqui.", parse_mode="Markdown")
    else:
        step = sim_advance(sim)
        if step["decision"]:
            await _send_sim_step(query.message, sim, step,
                                 prefix=f"Você escolheu: *{choice}*\n")
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
                # gabarito calculado — a conversa pós-sim não redescobre a
                # mão de cabeça (board, showdown, mão feita por street)
                **(sim.get("gabarito") or {}),
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
    verdict = await asyncio.to_thread(sim_whatif, sim, update.effective_user.id)
    if verdict:
        await _safe_reply(query.message, "🎓 *Veredito da sua linha:*\n\n" + verdict)
        await _send_pending_charts(query.message, update.effective_user.id)
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
    from app.bot.processing import (
        LAST_UPLOAD_KIND, replay_fallback_text, replay_link_info, stash_paste,
        take_paste,
    )
    from app.parsers import detect_site

    # link de replay de clube: o público BR compartilha LINK, não arquivo.
    # PPPoker: puxa a mão sozinho (JSON no CDN) e analisa. Outros: instrução.
    rl = replay_link_info(text)
    if rl:
        if rl["site"] == "pppoker" and rl["share_key"]:
            await update.message.reply_text(
                "🔗 Achei o link do replay! Puxando a mão e analisando… 🃏")
            reply = await asyncio.to_thread(
                process_upload, rl["share_key"], "pppoker_replay",
                tg_user.id, _uname(tg_user), "pt", None)
            # share_key no evento: sondas/diagnóstico acham a mão certa (o
            # fluxo antigo só deixava rastro quando caía no followup)
            await _log(update, "replay_pppoker", share_key=rl["share_key"])
            await _safe_reply(update.message, reply,
                              kind=LAST_UPLOAD_KIND.get(tg_user.id))
            await _send_pending_charts(update.message, tg_user.id)
            return
        await _log(update, "replay_link", site=rl["site"])
        await update.message.reply_markdown(replay_fallback_text())
        return

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
            process_upload, text.encode(), "txt", tg_user.id, _uname(tg_user)
        )
        await _safe_reply(update.message, reply,
                          kind=LAST_UPLOAD_KIND.get(tg_user.id))
        await _send_pending_charts(update.message, tg_user.id)
        return

    await update.message.reply_text("🤔 Analisando sua colocação…")
    answer = await asyncio.to_thread(
        process_followup, tg_user.id, _uname(tg_user), text
    )
    if answer:
        await _safe_reply(update.message, answer, simplify_btn=True,
                          kind=LAST_UPLOAD_KIND.get(tg_user.id))
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


_SIMPLIFY_KB = InlineKeyboardMarkup(
    [[InlineKeyboardButton("🎈 Explica mais simples", callback_data="simp")]]
)


def _post_kb(kind: str | None) -> InlineKeyboardMarkup:
    """Botões de pós-análise: o momento de maior atenção vira vitrine do
    resto do produto (features escondidas atrás de comando ninguém acha)."""
    rows = [[InlineKeyboardButton("🎈 Explica mais simples", callback_data="simp")]]
    if kind == "tournament":
        rows.append([
            InlineKeyboardButton("📋 Relatório mão a mão", callback_data="pa:rel"),
            InlineKeyboardButton("📈 Minha evolução", callback_data="pa:evo"),
        ])
    elif kind == "hand":
        rows.append([
            InlineKeyboardButton("🔁 Simular esta mão", callback_data="pa:sim"),
            InlineKeyboardButton("📖 Range do spot", callback_data="pa:range"),
        ])
    return InlineKeyboardMarkup(rows)


async def _safe_reply(message, text: str, simplify_btn: bool = False,
                      kind: str | None = None) -> None:
    """Envia respeitando o limite de 4096 chars do Telegram; se o Markdown do LLM
    vier malformado (entidades desbalanceadas), reenvia como texto puro.
    `simplify_btn`: anexa o botão 🎈 ao último pedaço (respostas do coach).
    `kind`: adiciona os botões contextuais de pós-análise ('tournament'|'hand')."""
    from telegram.error import BadRequest

    chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)] or [text]
    for i, chunk in enumerate(chunks):
        last = i == len(chunks) - 1
        kb = None
        if last and kind:
            kb = _post_kb(kind)
        elif last and simplify_btn:
            kb = _SIMPLIFY_KB
        try:
            await message.reply_markdown(chunk, reply_markup=kb)
        except BadRequest:
            await message.reply_text(chunk, reply_markup=kb)


async def on_post_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Botões contextuais de pós-análise (pa:rel / pa:evo / pa:sim / pa:stats).

    Cada clique vira evento no banco — o funil pós-análise deixa de ser
    invisível e passa a dizer onde investir."""
    import io as _io

    query = update.callback_query
    action = query.data.split(":", 1)[1]
    tg_user = update.effective_user
    await _log(update, f"btn_{action}")

    if action == "rel":
        await query.answer("Montando o relatório… 📋")
        from app.bot.processing import report_doc_for_user

        doc = await asyncio.to_thread(report_doc_for_user, tg_user.id,
                                      _uname(tg_user))
        if not doc:
            await query.message.reply_text(
                "Ainda não tenho um torneio seu com mãos suficientes (mínimo 8).")
            return
        data, fname, caption = doc
        await query.message.reply_document(
            document=_io.BytesIO(data), filename=fname, caption=caption[:1000])
        return

    if action == "evo":
        await query.answer("Buscando sua evolução… 📈")
        from app.bot.processing import evolution_report

        png, text = await asyncio.to_thread(evolution_report, tg_user.id)
        if png:
            try:
                await query.message.reply_photo(png, caption=text[:1000],
                                                reply_markup=_EVO_BUTTONS)
            except Exception:
                await query.message.reply_text(text)
        else:
            await query.message.reply_text(
                text or "Preciso de mais uploads para desenhar sua evolução.")
        return

    if action == "sim":
        await query.answer("Preparando a simulação… 🎮")
        from app.bot.processing import LAST_HAND_META

        hand_id = (LAST_HAND_META.get(tg_user.id) or {}).get("hand_id")
        sim = await asyncio.to_thread(build_simulation, tg_user.id, hand_id)
        if sim and sim.get("unsimulable"):
            # ESTA mão não tem a sequência de ações jogável — NÃO simula outra
            await query.message.reply_text(
                "Essa mão eu não consigo simular — não tenho a sequência "
                "completa de ações dela (o print/histórico só pegou parte). "
                "Manda /simular que eu pego a sua mão mais recente com a mão "
                "inteira, ou envie o hand history dessa mão.")
            return
        if not sim:
            await query.message.reply_text(
                "Preciso de uma mão sua com a ação completa para simular.")
            return
        if sim.get("dead_end"):
            await _send_hand_film(
                query.message, tg_user.id, sim.get("hand_id"),
                "🃏 Nessa mão você *foldou o pré-flop*, então não tem decisão "
                "sua pra rejogar. Mas aqui está o *filme* de como ela terminou 👇")
            return
        ctx.user_data["sim"] = sim
        step = sim_advance(sim)
        intro = (
            "🎮 *Simulação* — jogue a mão como se fosse ao vivo!\n"
            "No final eu comparo a sua linha com a que aconteceu de verdade."
        )
        # MESMO caminho do /simular: figura da mesa em cada decisão (o botão
        # usava um envio próprio só-texto — as imagens "sumiam" por aqui)
        await _send_sim_step(query.message, sim, step, prefix=intro + "\n")
        return

    if action == "share":
        await query.answer("Montando o card… 📣")
        spot = ctx.user_data.get("share_spot")
        if not spot:
            await query.message.reply_text(
                "Responde um /treino primeiro que eu monto o card do spot.")
            return
        try:
            from app.analysis.hand_figure import render_share_card
            png = await asyncio.to_thread(render_share_card, spot)
            import io as _ioS
            await _log(update, "share_card")
            await query.message.reply_photo(
                photo=_ioS.BytesIO(png),
                caption="📣 Encaminha pro grupo e vê quem acerta o spot. "
                        "Cada um responde no t.me/KKNUts_BOT 😉")
        except Exception:
            await query.message.reply_text("Não consegui montar o card agora.")
        return

    if action == "range":
        await query.answer("Montando o range do spot… 📖")
        from app.bot.processing import spot_range_chart

        import io as _io2
        chart = await asyncio.to_thread(spot_range_chart, tg_user.id)
        if chart:
            png, caption = chart
            await query.message.reply_photo(photo=_io2.BytesIO(png),
                                            caption=caption[:1000])
        else:
            await query.message.reply_text(
                "Perdi o contexto da última mão — me manda ela de novo que "
                "eu trago o range do spot.")
        return

    if action == "stats":
        await query.answer("Calculando seu perfil… 📊")
        from app.bot.processing import stats_report

        msg = await asyncio.to_thread(stats_report, tg_user.id, _uname(tg_user))
        if msg:
            await _safe_reply(query.message, msg)
        else:
            await query.message.reply_text(
                "Ainda não tenho mãos suas o bastante — manda mais uploads.")
        return

    await query.answer()


async def on_simplify(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Botão 🎈: reexplica a última resposta do coach para iniciante total."""
    from app.bot.processing import simplify_last

    query = update.callback_query
    await query.answer("Simplificando… 🎈")
    tg_user = update.effective_user
    simple = await asyncio.to_thread(simplify_last, tg_user.id, _uname(tg_user))
    if simple:
        await _safe_reply(query.message, simple, simplify_btn=True)
    else:
        await query.message.reply_text(
            "Não achei uma análise recente pra simplificar — me manda uma mão "
            "ou pergunta algo que eu explico do zero. 🙂"
        )


async def _send_pending_charts(message, telegram_id: int) -> None:
    """Envia os gráficos de range que o coach usou na análise (se houver)."""
    import io as _io

    from app.bot.processing import pop_charts

    for png, caption in pop_charts(telegram_id):
        try:
            if png:
                await message.reply_photo(photo=_io.BytesIO(png),
                                          caption=caption[:1000])
            else:
                # render falhou: o texto prometeu o gráfico — avisar é melhor
                # que sumir com ele (incoerência silenciosa)
                await message.reply_text(caption[:1000])
        except Exception:
            pass
    from app.bot.processing import pop_docs

    for data, fname, caption in pop_docs(telegram_id):
        try:
            await message.reply_document(
                document=_io.BytesIO(data), filename=fname, caption=caption[:1000]
            )
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
    app.add_handler(CommandHandler("relatorio", cmd_relatorio))
    app.add_handler(CommandHandler("preparar", cmd_preparar))
    app.add_handler(CallbackQueryHandler(on_evo_indicator, pattern=r"^evo:"))
    app.add_handler(CallbackQueryHandler(on_style_target, pattern=r"^est:"))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("treino", cmd_treino))
    app.add_handler(CommandHandler("range", cmd_range))
    app.add_handler(CommandHandler("simular", cmd_simular))
    app.add_handler(CallbackQueryHandler(on_drill_answer, pattern=r"^drill:"))
    app.add_handler(CallbackQueryHandler(on_go, pattern=r"^go:"))
    app.add_handler(CallbackQueryHandler(on_range_button, pattern=r"^rng:"))
    app.add_handler(CallbackQueryHandler(on_simplify, pattern=r"^simp$"))
    app.add_handler(CallbackQueryHandler(on_post_action, pattern=r"^pa:"))
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
