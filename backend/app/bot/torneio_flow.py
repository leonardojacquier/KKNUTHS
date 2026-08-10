"""Fluxo do /dossie — o documento HTML de um vilão num torneio.

Extraído de `processing.py` pelo teto de linhas (o guarda disparou em
3609/3600), no mesmo padrão do `lobby_flow`: tudo que os testes dublam
(`get_repository`, `torneios_do_usuario`) é resolvido VIA processing em
tempo de chamada. Reexportado lá.
"""
from __future__ import annotations


def _p():
    from app.bot import processing

    return processing


def dossie_doc(telegram_id: int, nome: str,
               escolha: int = 1) -> tuple[bytes, str, str] | str | None:
    """/dossie <vilão> [N]: o dossiê HTML de um vilão num torneio.

    (bytes, filename, caption) no sucesso; STRING quando há o que explicar
    (vilão não achado -> lista de quem estava lá; torneio N inexistente ->
    quantos existem); None sem torneio nenhum. Devolver texto em vez de
    engolir é o que separa "erro" de "porta trancada sem aviso".
    """
    ts = _p().torneios_do_usuario(telegram_id)
    if not ts:
        return None
    if not 1 <= escolha <= len(ts):
        return (f"Você tem {len(ts)} torneio(s) na base — não existe um "
                f"nº {escolha}. Manda /torneio que eu listo.")
    t = ts[escolha - 1]
    hands = t["maos"]

    from app.analysis.dossie_html import build_dossie_html

    html = build_dossie_html(nome, hands, t)
    if html is None:
        vistos = sorted({p.name for h in hands
                         for p in (h.players or [])
                         if p.name and not p.is_hero
                         and p.name.lower() not in ("hero", "você", "voce")})
        return (f"Não achei '{nome}' nesse torneio. Quem estava lá: "
                + ", ".join(vistos[:12]) if vistos
                else f"Não achei '{nome}' nesse torneio.")

    repo = _p().get_repository()
    if repo.enabled:
        repo.log_event(telegram_id, None, "dossie",
                       {"vilao": nome[:40], "escolha": escolha})
    sala = (t["site"] or "").split(" · ")[0]
    caption = (f"🔍 Dossiê de {nome} — {sala} {t['data']}\n"
               f"Mostradas, escuras com sinais, e a sua defesa. "
               f"Abre no navegador.")
    seguro = "".join(c if c.isalnum() else "-" for c in nome)[:30]
    return (html.encode("utf-8"), f"dossie-{seguro}.html", caption)


def resolver_escolha(telegram_id: int, ref: str) -> int | None:
    """'2' -> índice 2; '303773218' -> o torneio COM ESSE CÓDIGO. None = não achei.

    A regra da ambiguidade: primeiro CÓDIGO, por match EXATO (código não
    envelhece quando entra torneio novo — posição envelhece); só depois,
    dígitos viram posição, e posição fora da lista dá None. Um código
    desconhecido também dá None em vez de cair no último calado: ele pediu
    um torneio específico, e receber outro é pior que "não achei".

    (Sem guarda de comprimento: um código de 9 dígitos que não existisse
    viraria a posição 303 milhões — fora da lista, None do mesmo jeito.
    Guarda que não muda resultado é código morto.)
    """
    ref = (ref or "").strip()
    if not ref:
        return None
    ts = _p().torneios_do_usuario(telegram_id)
    for i, t in enumerate(ts, start=1):
        if t["tournament_id"] == ref:
            return i
    if ref.isdigit():
        n = int(ref)
        return n if 1 <= n <= len(ts) else None
    return None
