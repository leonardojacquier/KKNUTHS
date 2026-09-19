"""Fluxo da foto do lobby: ler, conferir, guardar, lembrar.

Extraído de `processing.py` quando o guarda de tamanho disparou (3607 linhas,
teto 3600) — o conselho do próprio guarda. As funções continuam reexportadas
lá, e `get_repository` é resolvido VIA processing em tempo de chamada, de
propósito: os testes trocam `processing.get_repository`, e uma importação
direta daqui faria o dublê deles ser ignorado em silêncio (a lição da
extração do storyboard: o que quebra é o nome livre que ninguém conferiu).
"""
from __future__ import annotations

import logging

log = logging.getLogger("processing")


def _repo():
    from app.bot import processing

    return processing.get_repository()


# a última estrutura fotografada. As nomeadas (`lobby:<slug>`) ficam como
# acervo; esta é o ponteiro para a que vale agora — sem ela, o /preparar teria
# que adivinhar qual das guardadas é a de hoje.
CHAVE_ATUAL = "lobby:atual"


def _lobby_guardado(repo, user):
    """A última estrutura que o aluno fotografou, ou None.

    Vive em `user_meta` porque é dado DELE e tem que sobreviver ao deploy:
    fotografar de novo antes de cada torneio seria o mesmo que não guardar.
    """
    if not (user and getattr(repo, "enabled", False)):
        return None
    try:
        from app.analysis.lobby import Lobby, Nivel

        bruto = repo.get_user_meta(user["id"], CHAVE_ATUAL)
        if not bruto:
            return None
        niveis = tuple(Nivel(*n) if isinstance(n, (list, tuple)) else Nivel(**n)
                       for n in (bruto.get("niveis") or []))
        if not niveis:
            return None
        return Lobby(**{**bruto, "niveis": niveis})
    except Exception:
        log.warning("estrutura guardada ilegível", exc_info=True)
        return None


def _slug_do_torneio(nome: str | None) -> str:
    """Chave estável para guardar a estrutura. Sem nome, uma só por aluno —
    melhor sobrescrever que perder."""
    import re as _re

    limpo = _re.sub(r"[^a-z0-9]+", "-", (nome or "").lower()).strip("-")
    return f"lobby:{limpo[:40] or 'ultimo'}"


def processar_lobby(content: bytes, media: str, telegram_id: int,
                    username: str | None) -> str:
    """Print do lobby -> estrutura lida, CONFERIDA e guardada.

    Guardar é o que faz isto valer a pena: ele fotografa uma vez e o
    /preparar usa daí em diante. Sem memória, seria uma leitura bonita que
    ele teria que repetir antes de todo torneio.

    A conferência contra as mãos dele do mesmo clube vem junto e vai no
    texto — leitura de tela erra, e erro que não aparece vira plano de jogo.
    """
    from app.agent.llm import extract_lobby_from_image
    from app.analysis.lobby import conferir_com_maos
    from app.analysis.lobby import texto as texto_do_lobby

    lobby = extract_lobby_from_image(content, media)
    if lobby is None:
        return ("Não consegui ler a estrutura nesse print. Manda a tela de "
                "*Informações do jogo* (a aba com a tabela de blinds) — "
                "quanto mais níveis aparecerem, melhor.")

    repo = _repo()
    user = repo.get_or_create_user(telegram_id, username) if repo.enabled else None
    maos = repo.get_hands_para_perfil(user["id"])[0] if user else []
    conferencia = conferir_com_maos(lobby, maos)

    if user:
        try:
            guardavel = {k: (list(v) if isinstance(v, tuple) else v)
                         for k, v in lobby._asdict().items()}
            repo.set_user_meta(user["id"], _slug_do_torneio(lobby.nome),
                               guardavel)
            repo.set_user_meta(user["id"], CHAVE_ATUAL, guardavel)
        except Exception:
            log.warning("não consegui guardar a estrutura do lobby",
                        exc_info=True)

    partes = [texto_do_lobby(lobby, conferencia)]

    from app.agent.llm import LAST_LOBBY_CHECK

    divergencias = (LAST_LOBBY_CHECK or {}).get("divergencias") or []
    if divergencias:
        partes.append("⚠️ *Li com dúvida:* " + "; ".join(divergencias[:3])
                      + "\nConfere esses números e me corrige se estiver errado.")
    partes.append("_Guardei. É só mandar /preparar antes do torneio._")

    if repo.enabled:
        repo.log_event(telegram_id, username, "lobby_lido",
                       {"nome": lobby.nome, "niveis": len(lobby.niveis),
                        "confere": f"{conferencia[0]}/{conferencia[1]}",
                        "divergencias": len(divergencias)})
    return "\n\n".join(partes)
