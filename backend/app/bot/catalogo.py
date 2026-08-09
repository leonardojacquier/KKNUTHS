"""Catálogo de comandos: uma lista só, três consumidores.

O menu '/' do Telegram é FLAT por decisão da API. `setMyCommands` recebe uma
lista de `BotCommand` e mostra na ordem em que a gente manda — não existe
aninhamento, não existe separador, não existe cabeçalho de grupo. Submenu de
verdade ali não é coisa que dá para escrever melhor; não existe. (O que a API
tem de hierárquico é `scope`, que decide QUEM vê a lista, não como ela se
organiza.)

Então a categorização acontece em dois lugares, com o mesmo catálogo atrás:

  * no menu '/', pela ORDEM e por um emoji de categoria à frente de cada
    descrição — é o agrupamento que a API permite, e um item passa a dizer a
    que grupo pertence sem depender de o aluno adivinhar pela vizinhança;
  * no /start, por submenu de verdade: um botão por categoria, que abre a
    lista daquela categoria com "voltar". Cada linha sai como `/comando`, que
    o Telegram renderiza clicável — abrir o submenu e tocar já executa.

Ter UMA fonte é o ponto principal, e não é estética. A mesma lista existia em
três lugares e os três divergiam: o `set_my_commands` tinha 19 comandos, o
texto de "Como funciona" anunciava 12, e os seis que faltavam lá — /banca,
/foco, /leitura, /prova, /spot, /vilao — só eram descobertos por quem já
sabia que existiam. Agora quem escreve um comando novo mexe aqui, e os três
lugares mudam juntos ou o teste estrutural falha.

O que NÃO mora aqui: os comandos de dono (/licoes, /planode, /quem, /termo).
Eles têm porteiro de `ADMIN_TELEGRAM_ID` e anunciá-los seria convidar o aluno
a bater numa porta trancada.
"""
from __future__ import annotations

from typing import NamedTuple


class Comando(NamedTuple):
    """Um comando de aluno.

    `curta` é o que cabe no menu '/' (o Telegram trunca em telas estreitas,
    então vale a pena ser curto de verdade); `longa` é a linha do submenu e da
    ajuda, onde há espaço para dizer o que a coisa faz.
    """

    nome: str
    curta: str
    longa: str


class Categoria(NamedTuple):
    slug: str
    emoji: str
    titulo: str
    comandos: tuple[Comando, ...]


CATEGORIAS: tuple[Categoria, ...] = (
    Categoria("perfil", "📊", "Análise e perfil", (
        Comando("stats", "Seu perfil de estilo",
                "perfil de estilo, leaks em bb/100 e KKN Tilt Detector"),
        Comando("estilo", "Você vs os grandes jogadores",
                "cartão visual do seu estilo vs os grandes + plano de "
                "transição"),
        Comando("evolucao", "Sua linha do tempo",
                "sua linha do tempo (VPIP, PFR, resultado…) com gráficos"),
        Comando("torneio", "Quadro do último torneio",
                "quadro do último torneio: curva do stack mão a mão"),
        Comando("relatorio", "Relatório mão a mão 📋",
                "o torneio inteiro analisado, mão por mão (HTML)"),
        Comando("prova", "Auditar a ferramenta 🔬",
                "auditar a ferramenta nas suas próprias mãos"),
    )),
    Categoria("treino", "🎮", "Treino", (
        Comando("preparar", "Preparação pré-torneio 🎯",
                "briefing pré-torneio: seus leaks, protocolo mental e metas"),
        Comando("simular", "Rejogue uma mão sua",
                "jogue uma mão sua de novo, decisão a decisão"),
        Comando("treino", "Drill rápido de um spot seu",
                "drill rápido: o que você faria neste spot?"),
        Comando("leitura", "Adivinhe a mão do vilão 🔎",
                "adivinhe a mão do vilão a partir da linha que ele tomou"),
        Comando("foco", "No que você está trabalhando 🎯",
                "no que você está trabalhando agora, e como está indo"),
    )),
    Categoria("ferramentas", "📐", "Ferramentas", (
        Comando("spot", "EV de all-in ⚖️",
                "EV de all-in: o equilíbrio do spot, com e sem ICM"),
        Comando("range", "Gráficos de range 13×13",
                "gráficos 13×13: `/range btn` · `/range sb 10` · "
                "`/range sb 10 ev` · `/range sb 10 icm 1.5`"),
        Comando("vilao", "Dossiê de um oponente 🎯",
                "dossiê de um oponente que já apareceu nas suas mãos"),
        Comando("banca", "Risco de ruína 💰",
                "risco de ruína e downswing esperado para a sua banca"),
        Comando("ask", "Busque no seu histórico",
                "busque no seu histórico de mãos: `/ask quantas vezes "
                "paguei 3-bet fora de posição?`"),
    )),
    Categoria("conta", "⚙️", "Conta e ajuda", (
        Comando("manual", "Manual do jogador 📖",
                "o manual do jogador em PDF"),
        Comando("plano", "Seu plano e limites",
                "seu plano, seus limites e o que já usou"),
        Comando("start", "Menu inicial",
                "voltar ao começo, com os atalhos do primeiro minuto"),
    )),
)


def todos_os_comandos() -> tuple[Comando, ...]:
    return tuple(c for cat in CATEGORIAS for c in cat.comandos)


def nomes() -> set[str]:
    return {c.nome for c in todos_os_comandos()}


def categoria_por_slug(slug: str) -> Categoria | None:
    for cat in CATEGORIAS:
        if cat.slug == slug:
            return cat
    return None


def pares_do_menu() -> list[tuple[str, str]]:
    """`(nome, descrição)` na ordem do catálogo, com o emoji da categoria à
    frente da descrição.

    O emoji é o único cabeçalho de grupo que sobra numa lista flat: o aluno
    que rola a lista vê 📊📊📊📊📊📊🎮🎮🎮… e a fronteira aparece sozinha.
    Devolve tuplas em vez de `BotCommand` para o catálogo não depender de
    `telegram` — assim ele carrega em teste sem o SDK e sem rede.
    """
    return [(c.nome, f"{cat.emoji} {c.curta}")
            for cat in CATEGORIAS for c in cat.comandos]


def texto_da_categoria(cat: Categoria) -> str:
    linhas = [f"{cat.emoji} *{cat.titulo}*\n"]
    linhas += [f"• /{c.nome} — {c.longa}" for c in cat.comandos]
    return "\n".join(linhas)


def texto_de_todas() -> str:
    """Todas as categorias em sequência — a ajuda longa do /start."""
    return "\n\n".join(texto_da_categoria(cat) for cat in CATEGORIAS)
