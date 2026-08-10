"""/dossie em HTML: o vilão de um torneio, nas três camadas, num documento.

O /vilao responde no chat e é bom para consulta rápida. O dossiê é o formato
de ESTUDO — como o /relatorio é para o torneio — e junta num arquivo o que
hoje sai espalhado: o perfil com intervalo, as mãos que ele MOSTROU (com
cartas e linha), as apostas às escuras com os sinais, e a defesa do aluno
contra ele. Mesmo visual do relatório mão a mão; nada aqui chama modelo —
o documento inteiro é determinístico.

As regras de honestidade são as dos módulos de origem, e o HTML as repete
por escrito onde o leitor está: rótulo só com intervalo; sinais são fatos,
não veredito; taxa de blefe não existe porque showdown seleciona quem paga.
"""
from __future__ import annotations

import html as _html

from app.analysis.defesa import (
    Defesa,
    LinhaEscura,
    linhas_escuras,
    medir as medir_defesa,
    nao_vistas,
)
from app.analysis.dossie import Dossie, MaoMostrada, montar
from app.analysis.equity import pretty_cards
from app.analysis.mesa import medir as medir_mesa

_CSS = """
body{font-family:'Segoe UI',system-ui,sans-serif;font-size:13px;color:#1B211D;
margin:26px;line-height:1.5;max-width:900px}
h1{font-size:22px;margin:0 0 2px} h2{font-size:16px;color:#2E7D5B;margin:24px 0 10px}
.sub{color:#828A84;font-size:12px;margin-bottom:12px}
.kpis{display:flex;gap:10px;margin:12px 0;flex-wrap:wrap}
.kpi{border:1px solid #DDE3DE;border-top:3px solid #2E7D5B;border-radius:8px;
padding:8px 14px} .kpi b{display:block;font-size:19px}
.kpi span{font-size:10.5px;color:#828A84;text-transform:uppercase}
.mao{border:1px solid #DDE3DE;border-left:4px solid #2E7D5B;border-radius:8px;
padding:10px 14px;margin:10px 0;page-break-inside:avoid}
.mao.blefe{border-left-color:#B3502E}
.mao.escura{border-left-color:#828A84}
.cartas{font-size:17px;font-weight:800}
.linha{font-family:ui-monospace,Consolas,monospace;font-size:11px;color:#4A554E;
background:#F7F9F7;border-radius:6px;padding:6px 10px;margin:6px 0}
.papel{font-size:11px;font-weight:700;border-radius:6px;padding:1px 8px}
.papel.blefe{background:#F9E8E0;color:#B3502E}
.papel.valor{background:#E4F1E9;color:#2E7D5B}
.papel.neutro{background:#F0F4F1;color:#5A665E}
.sinais{font-size:11.5px;color:#A67E35;margin-top:4px}
.nota{border:1px solid #D2A55C;border-radius:10px;background:#FBF6EC;
padding:8px 14px;margin:14px 0;font-size:12px}
.alerta{border:1px solid #B3502E;border-radius:10px;background:#FBEDE8;
padding:8px 14px;margin:14px 0;font-size:12.5px}
.duo{display:flex;gap:10px;flex-wrap:wrap}
.duo>div{flex:1;min-width:260px;border:1px solid #DDE3DE;border-radius:8px;
padding:8px 12px;font-size:12px} .duo i{color:#828A84;font-size:10.5px}
.foot{color:#828A84;font-size:11px;margin-top:18px}
"""


def _esc(t) -> str:
    return _html.escape(str(t or ""))


def _classe_do_papel(papel: str) -> str:
    if papel == "blefe":
        return "blefe"
    return "valor" if papel.startswith("valor") else "neutro"


_RUA_CURTA = {"preflop": "pré", "flop": "flop", "turn": "turn",
              "river": "river"}


def _situacao_do_heroi(h) -> str:
    """Onde VOCÊ ficou nesta mão — uma linha, para o header da figura.

    O dossiê é do vilão; as suas cartas entram só como contexto ("você
    largou no pré com 7♥2♣"), nunca mais como as cartas grandes do header."""
    hero = getattr(h, "hero", None)
    cartas = pretty_cards(list(getattr(h, "hero_cards", None) or []))
    rua_fold = None
    for st in (getattr(h, "streets", None) or ()):
        rua = str(getattr(st.name, "value", st.name)).lower()
        if any(getattr(a, "actor", None) == hero
               and str(getattr(a.type, "value", a.type)).lower() == "fold"
               for a in (st.actions or ())):
            rua_fold = _RUA_CURTA.get(rua, rua)
            break
    fim = f"largou no {rua_fold}" if rua_fold else "foi até o fim"
    return f"você: {cartas} — {fim}" if cartas else f"você {fim}"


def espec_do_vilao(h, vilao: str, titulo: str, nota: str) -> dict | None:
    """O spec da figura CENTRADO NO VILÃO — puro, testável sem PIL.

    Antes o dossiê reaproveitava `_hand_strip_img` do /relatorio, e o header
    saía com "VOCÊ" e as cartas do HERÓI — numa mão em que o aluno foldou
    7♥2♣ no pré, o dossiê do vilão estampava 7♥2♣. O dono viu e vetou.
    Aqui: cartas do VILÃO quando houve showdown, "cartas não vistas" quando
    não; posição/stack/blinds DELE; e o herói vira uma linha de contexto."""
    from app.analysis.tools import fmt_chips as _fc
    from app.bot.processing import hand_storyboard_streets

    bands = hand_storyboard_streets(h)
    if not bands:
        return None
    assento = next((p for p in (getattr(h, "players", None) or ())
                    if p.name == vilao), None)
    bb = float(getattr(getattr(h, "stakes", None), "big_blind", 0) or 0)
    sub = vilao.strip()[:18]
    if assento is not None and getattr(assento, "position", None):
        sub += f" · {assento.position}"
    if assento is not None and bb > 0 and getattr(assento, "stack", None):
        sub += f" · {round(assento.stack / bb, 1):g}bb"
    sb = getattr(getattr(h, "stakes", None), "small_blind", None)
    if sb and bb:
        sub += f" · blinds {_fc(sb)}/{_fc(bb)}"
    cartas = list((getattr(h, "shown_cards", None) or {}).get(vilao) or [])
    if len(nota) > 260:                  # mesmo teto do /relatorio
        nota = nota[:257].rstrip() + "…"
    return {
        "title": titulo,
        "subtitle": sub,
        "tagline": _situacao_do_heroi(h),
        "hero_cards": cartas,            # as do VILÃO — a figura só exibe
        "cards_note": "" if cartas else "cartas não vistas",
        "streets": bands,
        "math": {},
        "verdict": "",                   # sem selo: figura é filme, não juízo
        "verdict_text": nota,
        "correct": "",
    }


def _strip(h, vilao: str, seq: int, nota: str) -> str:
    """O storyboard da mão sob a ótica do VILÃO — PIL, custo zero de modelo.

    O try existe pela mesma regra do /relatorio: a figura nunca derruba o
    documento — falhou, sai '' e o filme em texto assume."""
    if h is None:
        return ""
    try:
        import base64

        from app.analysis.hand_figure import render_hand_strip

        spec = espec_do_vilao(h, vilao, f"Mão #{seq} — {vilao.strip()[:18]}",
                              nota)
        if spec is None:
            return ""
        b64 = base64.standard_b64encode(render_hand_strip(spec)).decode()
        return (f"<img class=strip style='width:100%;border-radius:8px;"
                f"margin:10px 0' src='data:image/png;base64,{b64}'>")
    except Exception:
        return ""


def _mao_mostrada(m: MaoMostrada, vilao: str, h=None, seq: int = 0) -> str:
    extra = "blefe" if m.papel == "blefe" else ""
    desc = f" — {_esc(m.descricao)}" if m.descricao else ""
    img = _strip(h, vilao, seq, f"{m.papel}: {m.descricao or ''}")
    return (f"<div class='mao {extra}'>"
            f"<span class='cartas'>{_esc(pretty_cards(list(m.cartas)))}</span>"
            f" <span class='papel {_classe_do_papel(m.papel)}'>{_esc(m.papel)}"
            f"</span>{desc}{img}"
            f"<div class='linha'>board {_esc(pretty_cards(list(m.board)))}"
            f" · {_esc(m.linha)}</div></div>")


def build_dossie_html(nome: str, hands: list, torneio: dict | None = None
                      ) -> str | None:
    """O documento. None quando o vilão não aparece nessas mãos."""
    mesa = medir_mesa(hands)
    linha = next((li for li in (mesa.linhas if mesa else ())
                  if li.nome.strip().lower() == nome.strip().lower()), None)
    d: Dossie | None = montar(hands, nome)
    defesa: Defesa | None = medir_defesa(hands, nome)
    # a lista AMPLA: toda agressão pós-flop sem showdown, não só a aposta de
    # river que o herói enfrentou — com o recorte antigo a seção saía vazia
    # em torneio real (na maioria das mãos o herói já tinha foldado)
    escuras = linhas_escuras(hands, nome)
    enfrentadas = {e.hand_id: e for e in nao_vistas(hands, nome)}
    apareceu = any(
        (p.name or "").strip().lower() == nome.strip().lower()
        for h in hands for p in (getattr(h, "players", None) or ()))
    if not (apareceu or d or linha):
        return None

    t = torneio or {}
    sub = " · ".join(x for x in (
        (t.get("site") or "").split(" · ")[0] or None, t.get("data"),
        f"{len(hands)} mãos do torneio") if x)

    kpis = []
    if linha:
        kpis += [
            f"<div class='kpi'><b>{linha.maos}</b><span>mãos com ele</span></div>",
            f"<div class='kpi'><b>{round(100*linha.vpip)}% "
            f"±{round(100*linha.vpip_margem)}</b><span>vpip</span></div>",
            f"<div class='kpi'><b>{round(100*linha.pfr)}%</b><span>pfr</span></div>",
            f"<div class='kpi'><b>{round(100*linha.gap)}pp</b>"
            f"<span>gap paga-sem-atacar</span></div>"]
        if linha.rotulo:
            kpis.append(f"<div class='kpi'><b>{_esc(linha.rotulo)}</b>"
                        f"<span>rótulo (sustentado)</span></div>")
    if d:
        kpis.append(f"<div class='kpi'><b>{d.showdowns}</b>"
                    f"<span>mãos que você viu</span></div>")

    partes = [f"<h1>🔍 Dossiê — {_esc(nome)}</h1>",
              f"<div class='sub'>{_esc(sub)}</div>",
              f"<div class='kpis'>{''.join(kpis)}</div>"]
    # A SÍNTESE — "como jogar contra ele": estilo, showdowns e a defesa do
    # aluno, num plano só, cada conselho com a evidência entre parênteses
    from app.analysis.leitura_vilao import plano_contra

    plano = plano_contra(
        rotulo=(linha.rotulo if linha else ""),
        gap_pp=(round(100 * linha.gap) if linha else None),
        vpip_pct=(round(100 * linha.vpip) if linha else None),
        margem_pp=(round(100 * linha.vpip_margem) if linha else None),
        blefes_vistos=(len(d.blefes) if d else 0),
        valor_visto=(len(d.valor) if d else 0),
        overfold=bool(defesa and defesa.veredito == "overfold"),
        fold_pct=(round(100 * defesa.fold_taxa) if defesa else None),
        limiar_pct=(round(100 * defesa.limiar_fold)
                    if defesa and defesa.limiar_fold else None))
    partes.append(
        "<div class='nota'><b>🎯 Como jogar contra ele</b><br>• "
        + "<br>• ".join(_esc(c) for c in plano)
        + "<br><i>Cada conselho carrega a evidência que o sustenta — sem "
        "evidência, sem conselho.</i></div>")
    if linha and not linha.rotulo:
        partes.append("<div class='nota'>Sem rótulo: a amostra não sustenta "
                      "um — os números acima falam por si, com a margem "
                      "junto.</div>")

    # OS DOIS RETRATOS — o que ele mostrou vs o que ele fez. A divergência
    # entre eles é a conclusão que nenhum dos dois dá sozinho, e só sai
    # quando a amostra sustenta (Wilson, mesma régua de sempre).
    from app.analysis.perfil_duplo import montar as montar_duplo
    from app.analysis.perfil_duplo import texto as texto_duplo

    duplo = montar_duplo(hands, nome, d)
    if duplo.a or duplo.b:
        la, lb = texto_duplo(duplo)
        partes.append(
            "<h2>⚖️ O mesmo jogador, dois retratos</h2><div class='duo'>"
            f"<div><b>Retrato A — showdown</b><br>{_esc(la)}<br>"
            f"<i>viés declarado: só existe showdown quando alguém paga — "
            f"esta é a amostra das mãos PAGAS</i></div>"
            f"<div><b>Retrato B — linha</b><br>{_esc(lb)}<br>"
            f"<i>não precisa de carta nenhuma: cobre toda a agressão dele, "
            f"inclusive a que ninguém pagou para ver</i></div></div>")
        if duplo.divergencia:
            partes.append(f"<div class='alerta'><b>⚡ Onde os retratos "
                          f"divergem:</b> {_esc(duplo.divergencia)}</div>")

    por_id_todas = {str(getattr(h, "hand_id", "") or ""): h for h in hands}
    seq = 0
    if d:
        for titulo, grupo in (
                (f"Agrediu com mão fraca — blefe visto ({len(d.blefes)})",
                 d.blefes),
                (f"Apostou por valor ({len(d.valor)})", d.valor),
                (f"Pagou até o showdown ({len(d.pagou)})", d.pagou),
                (f"Mostrou sem agredir no fim ({len(d.outras)})", d.outras)):
            if not grupo:
                continue
            partes.append(f"<h2>{titulo}</h2>")
            for m in grupo:
                seq += 1
                partes.append(_mao_mostrada(m, nome,
                                            por_id_todas.get(m.hand_id), seq))
    else:
        partes.append("<h2>Showdowns</h2><div class='nota'>Ele não mostrou "
                      "nenhuma mão neste torneio — tudo que há são as linhas "
                      "abaixo.</div>")

    if escuras:
        from app.analysis.leitura_vilao import ler_linha, narrar_mao
        from app.bot.processing import _walk_hand

        por_id = {str(getattr(h, "hand_id", "") or ""): h for h in hands}
        levou = sum(1 for e in escuras if e.levou_o_pote)
        partes.append(f"<h2>Agrediu e ninguém viu ({len(escuras)} — "
                      f"levou o pote em {levou})</h2>")
        teto = 24
        rotulo_dele = linha.rotulo if linha else ""
        for e in escuras[:teto]:
            tam = (f" · {e.fracao_do_pote:g}× pote" if e.fracao_do_pote
                   else "")
            contra = enfrentadas.get(e.hand_id)
            fim = (f" — você: {_esc(contra.resposta)}" if contra
                   else (" — levou o pote" if e.levou_o_pote else ""))
            sin = (f"<div class='sinais'>⚑ {_esc(' · '.join(e.sinais))}</div>"
                   if e.sinais else "")

            # A MÃO INTEIRA — o storyboard do /relatorio (imagem, custo
            # zero de modelo); o filme em texto entra quando a imagem falha
            historia = ""
            h = por_id.get(e.hand_id)
            seq += 1
            img = _strip(h, nome, seq, "")
            if img:
                historia = img
            elif h is not None:
                try:
                    filme, _decs = _walk_hand(h)
                    historia = ("<div class='linha'>"
                                + "<br>".join(_esc(li) for li in filme)
                                + "</div>")
                except Exception:
                    historia = ""

            # A NARRATIVA — a mão narrada pelos números DELA: sizing em
            # fração do pote NAQUELE momento, o que cada carta do runout
            # mudou, e como a mesa reagiu. Duas mãos só saem iguais se
            # foram jogadas igual — é a análise individualizada que o dono
            # pediu para as mãos em que ele já tinha foldado.
            narrativa = ""
            if h is not None:
                frases = narrar_mao(h, nome)
                if frases:
                    narrativa = ("<div class='sinais'>📖 "
                                 + "<br>📖 ".join(_esc(f) for f in frases)
                                 + "</div>")

            # AS CARTAS PROVÁVEIS — contagem de combos do range SUPOSTO
            # (top-PFR% medido), com a suposição escrita na frase. Só nas
            # mãos em que ELE atacou o pré: quem só pagou entra com um range
            # que o PFR não descreve, e contar seria fingir precisão.
            combos_html = ""
            board_h = list(getattr(h, "final_board", None) or ()) if h else []
            if (linha is not None and linha.pfr > 0
                    and "aumenta pré" in e.linha):
                from app.analysis.combos import contar, linhas as linhas_combos

                cont = contar(
                    linha.pfr, board_h,
                    list(getattr(h, "hero_cards", None) or []),
                    f"PFR medido: {round(100 * linha.pfr)}%, "
                    f"{linha.maos} mãos")
                if cont:
                    lcs = linhas_combos(cont)
                    combos_html = (
                        "<div class='nota'>🃏 <b>Cartas prováveis</b> "
                        "<i>(contagem dado o range suposto — a suposição "
                        "está na frase)</i><br>" + _esc(lcs[0]) + "<br>• "
                        + "<br>• ".join(_esc(x.lstrip("• "))
                                        for x in lcs[1:]) + "</div>")

            # A LEITURA — recomendação de coach com as razões à mostra
            board = board_h
            lt = ler_linha(e.sinais, board, rotulo=rotulo_dele,
                           ja_mostrou_blefe=bool(d and d.blefes),
                           ja_mostrou_valor=bool(d and d.valor))
            razoes = ("<br>• " + "<br>• ".join(_esc(r) for r in lt.razoes)
                      if lt.razoes else "")
            leitura_html = (
                f"<div class='nota'>🧭 <b>Leitura: pende para "
                f"{_esc(lt.inclinacao)}</b> <i>(leitura de coach, não "
                f"medição)</i>{razoes}<br>"
                f"<b>A linha representa:</b> {_esc(lt.representa)}.<br>"
                f"<b>Recomendação:</b> {_esc(lt.conselho)}.</div>")

            if not historia:
                historia = f"<div class='linha'>{_esc(e.linha)}</div>"
            partes.append(
                f"<div class='mao escura'>"
                f"<span class='papel neutro'>{_esc(e.rua)}</span>{tam}{fim}"
                f"{historia}{narrativa}{sin}{combos_html}{leitura_html}</div>")
        if len(escuras) > teto:
            partes.append(f"<div class='sub'>…e mais "
                          f"{len(escuras) - teto} linhas.</div>")
        partes.append(
            "<div class='nota'><b>Observação:</b> nestas mãos a linha é o "
            "único fato; as cartas dele ninguém viu. A leitura 🧭 é "
            "RECOMENDAÇÃO — pesa os sinais da jogada, o perfil sustentado "
            "dele e o que ele já mostrou neste torneio — e por isso diz "
            "\"pende para\", nunca um percentual: \"blefa X%\" exigiria "
            "showdown, e o vilão só mostra quando alguém paga.</div>")

    if defesa:
        pct = round(100 * defesa.fold_taxa)
        corpo = (f"Ele apostou o river <b>{defesa.apostas}×</b> contra você; "
                 f"você largou <b>{defesa.folds} ({pct}%)</b>.")
        if defesa.fracao_mediana is not None and defesa.limiar_fold is not None:
            corpo += (f" Tamanho típico {defesa.fracao_mediana:g}× pote → o "
                      f"blefe dele lucra se você foldar mais que "
                      f"<b>{round(100*defesa.limiar_fold)}%</b>.")
        if defesa.veredito == "overfold":
            partes.append(f"<div class='alerta'><b>🛡 Sua defesa:</b> {corpo} "
                          f"<b>Você folda demais contra ele</b> (piso "
                          f"estatístico ≥{round(100*defesa.fold_lo)}%): "
                          f"qualquer duas cartas lucram te apostando.</div>")
        elif defesa.veredito == "amostra_curta":
            partes.append(f"<div class='nota'><b>🛡 Sua defesa:</b> {corpo} "
                          f"Amostra curta — números à mostra, veredito "
                          f"não.</div>")
        else:
            partes.append(f"<div class='nota'><b>🛡 Sua defesa:</b> {corpo} "
                          f"Sua frequência não abre espaço para blefe "
                          f"automático.</div>")

    from datetime import datetime, timedelta, timezone

    gerado = datetime.now(timezone(timedelta(hours=-3)))
    partes.append(f"<div class='foot'>KKNuths ♠ — dossiê determinístico: "
                  f"todo número sai das suas mãos, nenhum passa por modelo. "
                  f"Rótulo só quando o intervalo estatístico sustenta. "
                  f"<b>Gerado em {gerado:%d/%m %H:%M}</b> — se você está "
                  f"vendo outra data aqui, este é um arquivo antigo.</div>")
    return (f"<!doctype html><html lang=pt-BR><head><meta charset=utf-8>"
            f"<title>Dossiê — {_esc(nome)}</title><style>{_CSS}</style>"
            f"</head><body>{''.join(partes)}</body></html>")
