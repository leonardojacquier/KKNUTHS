"""Link de replay de clube: reconhecer, extrair a chave, ou explicar.

Saiu do `processing.py` por medição (ele bateu o teto de 3.600 linhas) e
porque isto é FOLHA: só depende de `app.parsers`, de mais nada do bot. O
`processing` reexporta os nomes, então nenhum call site mudou.

O que mora aqui é uma decisão só, tomada três vezes no bot (texto digitado,
legenda de foto, legenda de arquivo): *esta mensagem é um link de mão?* Ter
as três perguntando ao mesmo lugar é o que impede uma delas de divergir —
divergência entre caminhos foi a causa dos dois últimos defeitos deste fluxo.
"""
from __future__ import annotations

import re

# domínios de replay de clube conhecidos (link, não arquivo)
# pppoker.club = link de compartilhamento novo (share.php?...&shareKey=UUID);
# replay.pppoker.net = link antigo do frame do replayer. Ambos carregam o
# shareKey que é o nome do arquivo JSON no CDN.
# gg.gl é o ENCURTADOR de replay da GGPoker. Sem ele na lista o link não era
# nem reconhecido como replay: caía no leitor de texto e o aluno recebia
# "não entendi", que é a pior resposta possível — sugere que ele errou.
# "pppoker." cobre .net/.club e o .ph da rls_20260819 (21/08, caso real)
_REPLAY_HOSTS = ("pppoker.", "supremapoker.net", "clubgg.com", "wepoker",
                 "pokerbros", "upoker", "gg.gl", "ggpoker.com",
                 "ggpoker.net", "gg.poker")


def replay_link_info(text: str, legenda: bool = False) -> dict | None:
    """Detecta link de replay de clube na mensagem. Retorna
    {'site', 'share_key'} ou None. Só dispara quando a mensagem É o link
    (não quando cita uma url no meio de uma pergunta longa).

    `legenda=True` para caption de foto compartilhada: ali a regra do
    "mensagem é só o link" não vale — o app do clube escreve o texto
    promocional dele em volta do link, e o aluno não controla isso.

    Varre TODAS as urls, não só a primeira: a legenda do PPPoker manda o link
    de BAIXAR O APP antes do replay. Olhando só a primeira, o link de download
    ganhava — e como ele não tem shareKey, ou o aluno ouvia "não consegui ler
    o link" (host pppoker.onelink.me) ou a foto promocional ia inteira pra
    visão (host onelink.me, que nem é de replay). O link que ABRE ganha."""
    t = (text or "").strip()
    achadas = [(m.group(0), m.group(0))
               for m in re.finditer(r'https?://[^\s]+', t)]
    if not achadas:
        # o público cola o link SEM https:// (copiado do chat do clube):
        # "replay.pppoker.net/...?shareKey=..." tem que funcionar igual
        achadas = [(m.group(0), "https://" + m.group(0)) for m in
                   re.finditer(r'\b[\w][\w.-]*\.[a-z]{2,6}/[^\s]+', t,
                                re.IGNORECASE)]
    reconhecido = None
    for raw, url in achadas:
        if not legenda and len(t) > len(raw) + 40:
            continue
        info = _info_do_link(url)
        if info is None:
            continue
        if info["share_key"]:
            return info
        # host de clube sem chave utilizável: guarda como plano B, mas segue
        # procurando — o replay de verdade costuma vir DEPOIS na mesma legenda
        reconhecido = reconhecido or info
    return reconhecido


def _info_do_link(url: str) -> dict | None:
    """{'site','url','share_key'} para uma url só, ou None se não for clube."""
    host = re.sub(r'^https?://([^/]+).*', r'\1', url).lower()
    if not any(h in host for h in _REPLAY_HOSTS):
        return None
    from app.parsers.pppoker_replay import share_key_from_url

    site = ("pppoker" if "pppoker" in host else
            "suprema" if "suprema" in host else
            "ggpoker" if ("gg.gl" in host or "ggpoker" in host
                          or "gg.poker" in host) else "outro")
    if site == "suprema":
        # a Suprema recebe o LINK inteiro: a chave sai dele dentro do parser
        from app.parsers.suprema_replay import token_do_link

        return {"site": site, "url": url,
                "share_key": url if token_do_link(url) else None}
    return {"site": site, "url": url,
            "share_key": share_key_from_url(url) if site == "pppoker" else None}


# clubes cujo link eu RECONHEÇO mas não sei abrir — dizer o nome é a
# diferença entre "a ferramenta é limitada" e "a ferramenta está quebrada"
_NOME_CLUBE = {"suprema": "Suprema", "clubgg": "ClubGG", "wepoker": "WePoker",
               "pokerbros": "PokerBros", "upoker": "UPoker",
               "ggpoker": "GGPoker"}


def replay_fallback_text(site: str | None = None,
                         chave_ilegivel: bool = False) -> str:
    """Mensagem para replay que não dá para puxar automático.

    Ela era UMA só para dois casos muito diferentes: "esse clube eu não
    abro" e "é PPPoker, que eu ABRO, mas não consegui ler a chave deste
    link". O aluno não tinha como saber em qual caiu — e no segundo caso a
    mensagem é simplesmente falsa, porque o replay dele eu sei ler.
    """
    saidas = ("📸 *Print do replay* — foto da tela da mão (cartas + board).\n"
              "✍️ *Ou descreve* — _\"77 no CO, 30bb, limpei, flop A♦7♣9♣...\"_"
              " — que eu rodo os números na hora. 🃏")
    if chave_ilegivel:
        return ("🔗 É um link da *PPPoker* — esse eu abro sozinho, mas não "
                "achei o código da mão neste aqui. Costuma ser link cortado "
                "ou encurtado: reabre o replay no app e usa *Compartilhar* "
                "para copiar o link inteiro.\n\nSe preferir não repetir:\n\n"
                + saidas)
    if site == "ggpoker":
        # a GGPoker cifra a mão (medido: 22 kB, entropia 7,99/8, blocos AES).
        # Mas ela tem uma saída OFICIAL e melhor: o histórico do PokerCraft
        # traz a SESSÃO inteira, não uma mão — e é isso que alimenta stats,
        # leaks e evolução. Mandar o aluno para o print seria pior conselho.
        # O alias do link (_8gph8vo-…) é código de COMPARTILHAMENTO, resolvido
        # só no servidor deles — não dá para virar Hand ID por fora. Mas o
        # PokerCraft mostra o Hand ID na própria mão, e a busca por id já
        # existe no `handsearch`. Então o aluno traz o número, e eu acho no
        # arquivo dele: fecha o ciclo sem depender do link.
        # Nada de mandar o aluno caçar código: `find_hand` casa por CARTAS
        # ("QJ", "QJs", "QdJd"), e ele está olhando o replay — as cartas
        # estão na cara dele. O Nº da mão é só uma das formas, e a menos
        # conveniente. Exigi-lo era atrito que eu mesmo inventei.
        return ("🔗 Link de replay da *GGPoker*. Esse eu não abro — o site "
                "não libera a mão pelo link.\n\n"
                "*Faz assim, que fica até melhor:*\n\n"
                "1️⃣ PokerCraft → *Hand History* → período → *Download*\n"
                "2️⃣ me manda o `.txt` aqui\n"
                "3️⃣ pede a mão pelas *cartas*: _\"abre a mão de AK\"_\n\n"
                "Não precisa procurar número nenhum — as cartas que você está "
                "vendo no replay bastam (e o Nº da mão também serve, se "
                "preferir).\n\n"
                "O `.txt` traz a *sessão inteira*: além dessa mão, sai seu "
                "perfil, seus leaks e sua evolução — o que uma mão sozinha "
                "nunca mostra. 🃏\n\n"
                "Se preferir resolver só esta agora:\n\n" + saidas)
    clube = _NOME_CLUBE.get(site or "")
    quem = f"da *{clube}*" if clube else "desse clube"
    return (f"🔗 Esse é um *link de replay* {quem}. Abro sozinho só os da "
            "*PPPoker* e da *Suprema* por enquanto — mas analiso a mão "
            "*agora* de dois jeitos:\n\n" + saidas)
