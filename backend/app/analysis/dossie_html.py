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
.foot{color:#828A84;font-size:11px;margin-top:18px}
"""


def _esc(t) -> str:
    return _html.escape(str(t or ""))


def _classe_do_papel(papel: str) -> str:
    if papel == "blefe":
        return "blefe"
    return "valor" if papel.startswith("valor") else "neutro"


def _mao_mostrada(m: MaoMostrada) -> str:
    extra = "blefe" if m.papel == "blefe" else ""
    desc = f" — {_esc(m.descricao)}" if m.descricao else ""
    return (f"<div class='mao {extra}'>"
            f"<span class='cartas'>{_esc(pretty_cards(list(m.cartas)))}</span>"
            f" <span class='papel {_classe_do_papel(m.papel)}'>{_esc(m.papel)}"
            f"</span>{desc}"
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
    if linha and linha.exploit:
        partes.append(f"<div class='nota'><b>Como explorar:</b> "
                      f"{_esc(linha.exploit)}</div>")
    if linha and not linha.rotulo:
        partes.append("<div class='nota'>Sem rótulo: a amostra não sustenta "
                      "um — os números acima falam por si, com a margem "
                      "junto.</div>")

    if d:
        if d.blefes:
            partes.append(f"<h2>Agrediu com mão fraca — blefe visto "
                          f"({len(d.blefes)})</h2>")
            partes += [_mao_mostrada(m) for m in d.blefes]
        if d.valor:
            partes.append(f"<h2>Apostou por valor ({len(d.valor)})</h2>")
            partes += [_mao_mostrada(m) for m in d.valor]
        if d.pagou:
            partes.append(f"<h2>Pagou até o showdown ({len(d.pagou)})</h2>")
            partes += [_mao_mostrada(m) for m in d.pagou]
        if d.outras:
            partes.append(f"<h2>Mostrou sem agredir no fim "
                          f"({len(d.outras)})</h2>")
            partes += [_mao_mostrada(m) for m in d.outras]
    else:
        partes.append("<h2>Showdowns</h2><div class='nota'>Ele não mostrou "
                      "nenhuma mão neste torneio — tudo que há são as linhas "
                      "abaixo.</div>")

    if escuras:
        levou = sum(1 for e in escuras if e.levou_o_pote)
        partes.append(f"<h2>Agrediu e ninguém viu ({len(escuras)} — "
                      f"levou o pote em {levou})</h2>")
        teto = 24
        for e in escuras[:teto]:
            tam = (f" · {e.fracao_do_pote:g}× pote" if e.fracao_do_pote
                   else "")
            contra = enfrentadas.get(e.hand_id)
            fim = (f" — você: {_esc(contra.resposta)}" if contra
                   else (" — levou o pote" if e.levou_o_pote else ""))
            sin = (f"<div class='sinais'>⚑ {_esc(' · '.join(e.sinais))}</div>"
                   if e.sinais else "")
            partes.append(
                f"<div class='mao escura'>"
                f"<span class='papel neutro'>{_esc(e.rua)}</span>"
                f"<div class='linha'>{_esc(e.linha)}{tam}{fim}</div>"
                f"{sin}</div>")
        if len(escuras) > teto:
            partes.append(f"<div class='sub'>…e mais "
                          f"{len(escuras) - teto} linhas.</div>")
        partes.append(
            "<div class='nota'><b>Observação — por que estas mãos estão "
            "aqui sem veredito:</b> a linha é o único fato que existe delas. "
            "⚑ marca traços da jogada (três barris, overbet, draw que não "
            "bateu) que cabem tanto num blefe quanto num valor polarizado. "
            "Não existe \"provavelmente blefou X%\": o vilão só mostra "
            "quando alguém paga, e uma taxa tirada dos showdowns mediria "
            "quem pagou, não ele. \"Levou o pote\" é registro, não "
            "leitura.</div>")

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

    partes.append("<div class='foot'>KKNuths ♠ — dossiê determinístico: "
                  "todo número sai das suas mãos, nenhum passa por modelo. "
                  "Rótulo só quando o intervalo estatístico sustenta.</div>")
    return (f"<!doctype html><html lang=pt-BR><head><meta charset=utf-8>"
            f"<title>Dossiê — {_esc(nome)}</title><style>{_CSS}</style>"
            f"</head><body>{''.join(partes)}</body></html>")
