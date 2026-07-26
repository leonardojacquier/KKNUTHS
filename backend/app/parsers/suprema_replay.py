"""Parser de replay da Suprema Poker (link de clube).

O replayer é um jogo Cocos Creator servido em `r.supremapoker.net`, e a mão
vem de uma API separada. Isto NÃO é engenharia reversa por tentativa: é
transcrição do `main.45fc5.js` do próprio replayer, que faz exatamente:

    let params = GetRequestParams();
    if (params.t != null) {
        let tokenParam = params.t;
        token = tokenParam.substr(0, 8);      // só os 8 PRIMEIROS
        let tp = tokenParam.substr(10, 1);    // índice 10 escolhe o ambiente
        if (tp == "0")      url = "https://brazildev.zvga.me:8590/supremaAPI/replayInfo.php";
        else if (tp == "1") url = "https://braziluatcdn7.zvga.me/supremaAPI/replayInfo.php";
        else                url = "https://ra.supremapoker.net/supremaAPI/replayInfo.php";
        sendAsync(`${url}?s=${token}`, ...)
    }

Dois detalhes que custaram uma rodada cada:
  • o parâmetro é `s`, não `t`, e o valor é o PREFIXO de 8 — mandar o `t`
    inteiro devolve `-1` (código de erro da aplicação, com HTTP 200);
  • o endpoint está atrás de CloudFront, que só aceita método cacheável:
    POST leva 403. É GET.

O `er` que vem no link não é usado nesta chamada.

Só leitura, e só do que o próprio jogador compartilhou: o link de replay é
público por construção. Nada de login, nada de conta de sala.
"""
from __future__ import annotations

import json
import logging
import urllib.request

from app.models.canonical import (
    Action,
    ActionType,
    CanonicalHand,
    HandFormat,
    PlayerSeat,
    Stakes,
    Street,
    StreetName,
)

log = logging.getLogger("suprema")

_APIS = {
    "0": "https://brazildev.zvga.me:8590/supremaAPI/replayInfo.php",
    "1": "https://braziluatcdn7.zvga.me/supremaAPI/replayInfo.php",
}
_API_PADRAO = "https://ra.supremapoker.net/supremaAPI/replayInfo.php"

# CABEÇALHOS: não são enfeite, são a diferença entre 13 kB e 2 bytes.
# A mesma URL, com o mesmo `?s=`, devolve `-1` para o User-Agent padrão do
# curl e a mão inteira para um navegador. Custou várias rodadas concluir
# que o endpoint estava errado quando o errado era o cabeçalho — o `-1` é
# indistinguível de "token inválido".
_UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/150.0.0.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://r.supremapoker.net",
    "Referer": "https://r.supremapoker.net/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}
_TIMEOUT = 25


# CARTAS: `cardsD` é numérico e `cards` já vem legível ("K♦"). Uso o
# numérico como fonte: o texto depende do idioma da conta e usa "10" em vez
# de "T", enquanto divmod(v, 16) é estável.
#   divmod(29,16) = (1,13) -> K♦ ;  divmod(67,16) = (4,3) -> 3♠
# O mapa de naipes é o MESMO da PPPoker (1=♦ 2=♣ 3=♥ 4=♠); lá a base é 256,
# aqui é 16. Conferido contra as 7 cartas de uma mão real.
_SUIT = {1: "d", 2: "c", 3: "h", 4: "s"}
_RANK = {**{n: str(n) for n in range(2, 10)},
         10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}


def _card(v) -> str | None:
    """Código numérico -> 'Kd'. None para valor fora da baralho."""
    try:
        naipe, rank = divmod(int(v), 16)
    except (TypeError, ValueError):
        return None
    if naipe not in _SUIT or rank not in _RANK:
        return None
    return f"{_RANK[rank]}{_SUIT[naipe]}"


def _cards(lista) -> list[str]:
    """Lista de códigos -> ['Kd', 'Qd']. Carta ilegível é descartada em vez
    de virar placeholder: mão com carta inventada é pior que mão incompleta.
    """
    if not isinstance(lista, (list, tuple)):
        return []
    return [c for c in (_card(v) for v in lista) if c]


def token_do_link(url: str) -> str | None:
    """O `t` cru do link (13 caracteres na prática, mas não fixo o tamanho:
    o replayer só exige que exista)."""
    from urllib.parse import parse_qsl, unquote, urlparse

    try:
        p = urlparse(unquote(url or ""))
        params = dict(parse_qsl(p.query))
        params.update(dict(parse_qsl((p.fragment or "").lstrip("#/?"))))
    except Exception:
        return None
    t = (params.get("t") or "").strip()
    return t or None


def url_da_api(token: str) -> str | None:
    """Endpoint + parâmetro, exatamente como o replayer monta.

    Devolve None para token curto demais: sem 8 caracteres não há prefixo
    para mandar, e chutar um pedaço menor só geraria `-1`.
    """
    if not token or len(token) < 8:
        return None
    prefixo = token[:8]
    ambiente = token[10:11]          # substr(10, 1) — vazio se o token é curto
    base = _APIS.get(ambiente, _API_PADRAO)
    return f"{base}?s={prefixo}"


def api_do_link(url: str) -> str | None:
    """Atalho: link do aluno -> URL que devolve a mão."""
    t = token_do_link(url)
    return url_da_api(t) if t else None


def baixar(url_do_link: str) -> dict | None:
    """Busca o JSON da mão. None quando o link não resolve ou a API recusa.

    `-1` (e qualquer corpo que seja só um número) é o código de erro da
    aplicação — chega com HTTP 200 e por isso precisa ser tratado aqui, não
    pelo status.
    """
    alvo = api_do_link(url_do_link)
    if not alvo:
        return None
    try:
        req = urllib.request.Request(alvo, headers=_UA)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            corpo = r.read(8_000_000)
    except Exception as exc:
        log.warning("suprema: falha ao buscar %s: %s", alvo, exc)
        return None
    texto = corpo.decode("utf-8", "replace").strip()
    if not texto or texto.lstrip("-").isdigit():
        log.warning("suprema: API respondeu «%s» (replay expirado ou token "
                    "inválido)", texto[:20])
        return None
    try:
        dados = json.loads(texto)
    except Exception:
        log.warning("suprema: resposta não é JSON (%d bytes)", len(texto))
        return None
    return dados if isinstance(dados, dict) else {"raiz": dados}


# ------------------------------------------------------------------ parse
# `state` numera a fase da mão. 1 e 2 são postagens e pertencem ao pré-flop
# junto com o 3 — separá-los criaria uma street que não existe no jogo.
_STATE_STREET = {1: StreetName.PREFLOP, 2: StreetName.PREFLOP,
                 3: StreetName.PREFLOP, 4: StreetName.FLOP,
                 5: StreetName.TURN, 6: StreetName.RIVER}

# `nextround` traz o board revelado AO FIM da street que ele nomeia: o
# evento com stateName='preflop' carrega o FLOP. Ler o nome como "board
# desta street" adiantaria uma carta em todas elas.
_BOARD_DE = {"preflop": StreetName.FLOP, "flop": StreetName.TURN,
             "turn": StreetName.RIVER}

_POST = {"ante": "ante", "sb": "sb", "bb": "bb", "straddle": "straddle"}


def _nomes(players: dict) -> dict[int, str]:
    """uid -> nome exibido, sem repetir. Dois jogadores com o mesmo apelido
    viram atores distintos; sem isso as ações de um entrariam no outro."""
    saida: dict[int, str] = {}
    usados: set[str] = set()
    for chave, p in (players or {}).items():
        uid = int(p.get("uid") or chave or 0)
        nome = str(p.get("displayID") or f"uid{uid}").strip() or f"uid{uid}"
        if nome in usados:
            nome = f"{nome} (s{p.get('seat')})"
        usados.add(nome)
        saida[uid] = nome[:40]
    return saida


def _tipo_da_acao(acao: str, investido: float, chips: float,
                  maior: float) -> tuple[ActionType, str | None]:
    """(tipo, post_type). `allin` não é um tipo: é um call, um raise ou uma
    aposta que por acaso gastou tudo — quem trata como categoria própria
    perde a informação de agressão, que é o que a análise usa."""
    a = (acao or "").strip().lower()
    if a in _POST:
        return ActionType.POST, _POST[a]
    if a == "fold":
        return ActionType.FOLD, None
    if a == "check":
        return ActionType.CHECK, None
    if a == "call":
        return ActionType.CALL, None
    if a == "bet":
        return ActionType.BET, None
    if a == "raise":
        return ActionType.RAISE, None
    if a == "allin":
        total = investido + chips
        if maior <= 0:
            return ActionType.BET, None
        return (ActionType.RAISE if total > maior + 1e-9
                else ActionType.CALL), None
    return ActionType.CALL, None      # desconhecido: não inventa agressão


def parse(dados: dict) -> CanonicalHand | None:
    """JSON do replayInfo.php -> CanonicalHand.

    Transcrição do formato observado numa mão real, não inferência: o
    servidor manda posição (`pos`), cartas nas duas representações e o
    detalhamento de cada pote paralelo com quem ganhou o quê.
    """
    if not isinstance(dados, dict):
        return None
    eventos = dados.get("gameExtra") or []
    players = dados.get("players") or {}
    if not eventos or not players:
        return None

    inicio = next((e for e in eventos if e.get("e") == "startinfo"), {})
    sb = float(inicio.get("smallblind") or 0)
    bb = float(inicio.get("bigblind") or 0)
    nomes = _nomes(players)
    heroi_uid = int(dados.get("playerID") or 0)
    heroi = nomes.get(heroi_uid)

    # assentos: `coins` em `players` é o stack ANTES do ante (conferido
    # contra o primeiro evento de cada jogador)
    pos_por_uid: dict[int, str] = {}
    for ev in eventos:
        if ev.get("e") == "player_action" and ev.get("pos"):
            pos_por_uid.setdefault(int(ev.get("uid") or 0), str(ev["pos"]))
    assentos = []
    for chave, p in players.items():
        uid = int(p.get("uid") or chave or 0)
        assentos.append(PlayerSeat(
            seat=int(p.get("seat") or 0), name=nomes.get(uid, f"uid{uid}"),
            stack=float(p.get("coins") or 0), is_hero=(uid == heroi_uid),
            position=pos_por_uid.get(uid)))
    assentos.sort(key=lambda s: s.seat)

    ante = 0.0
    for ev in eventos:
        if (ev.get("e") == "player_action"
                and str(ev.get("action", "")).lower() == "ante"):
            ante = float(ev.get("chips") or 0)
            break

    # ---- ações, street a street
    por_street: dict[StreetName, list[Action]] = {}
    board_de: dict[StreetName, list[str]] = {}
    investido: dict[int, float] = {}      # total na street corrente
    street_atual = StreetName.PREFLOP
    for ev in eventos:
        tipo_ev = ev.get("e")
        if tipo_ev == "nextround":
            alvo = _BOARD_DE.get(str(ev.get("stateName") or "").lower())
            if alvo:
                board_de[alvo] = _cards(ev.get("cardsD"))
            nova = _STATE_STREET.get(int(ev.get("state") or 3))
            if nova and nova != street_atual:
                street_atual, investido = nova, {}
            continue
        if tipo_ev != "player_action":
            continue

        uid = int(ev.get("uid") or 0)
        acao = str(ev.get("action") or "").lower()
        chips = float(ev.get("chips") or 0)
        st = _STATE_STREET.get(int(ev.get("state") or 3), StreetName.PREFLOP)
        if st != street_atual:
            street_atual, investido = st, {}

        # `return` é devolução de aposta não paga, não é jogada: entra como
        # correção do investido. Tratá-la como ação criaria um "call
        # negativo" no meio da mão.
        if acao == "return":
            investido[uid] = investido.get(uid, 0.0) + chips
            continue

        maior = max(investido.values(), default=0.0)
        tipo, post = _tipo_da_acao(acao, investido.get(uid, 0.0), chips, maior)
        # ANTE fica FORA do investido, como no parser da PPPoker. Ante não
        # é aposta a igualar: somá-lo inflaria o `to_amount` de todo mundo e
        # a MESMA mão sairia com números diferentes conforme a sala — o
        # motor de análise é um só.
        if post != "ante":
            investido[uid] = investido.get(uid, 0.0) + chips
        ms = ev.get("millisec")
        por_street.setdefault(st, []).append(Action(
            actor=nomes.get(uid, f"uid{uid}"), type=tipo, amount=chips,
            to_amount=investido.get(uid, 0.0), post_type=post,
            all_in=(acao == "allin" or float(ev.get("coins") or 1) == 0),
            time_raw=(float(ms) / 1000 if ms is not None else None)))

    streets = []
    for nome_st in (StreetName.PREFLOP, StreetName.FLOP, StreetName.TURN,
                    StreetName.RIVER):
        acoes = por_street.get(nome_st, [])
        board = board_de.get(nome_st, [])
        if acoes or board:
            streets.append(Street(name=nome_st, board=board, actions=acoes))

    # ---- resultado: potes paralelos com dono
    resultado = dados.get("gameResult") or {}
    board_final = _cards(resultado.get("sharedcardsD")) or (
        board_de.get(StreetName.RIVER) or [])
    mostradas: dict[str, list[str]] = {}
    ganhou: dict[str, float] = {}
    for pote in (resultado.get("sidepotsdetail") or []):
        for linha in pote or []:
            uid = int(linha.get("uid") or 0)
            nome = nomes.get(uid, f"uid{uid}")
            cartas = _cards(linha.get("cardsD"))
            if cartas:
                mostradas[nome] = cartas
            premio = float(linha.get("prize") or 0)
            if premio:
                ganhou[nome] = ganhou.get(nome, 0.0) + premio
    total = sum(float(x or 0) for x in (resultado.get("sidepots") or [])) or None

    cartas_heroi = _cards((players.get(str(heroi_uid))
                           or players.get(heroi_uid) or {}).get("cardsD"))
    if heroi and not cartas_heroi:
        cartas_heroi = mostradas.get(heroi, [])

    # torneio: a Suprema manda os campos mtt SEMPRE; o que distingue é ter
    # horário de início de verdade
    extra = dados.get("matchExtra") or {}
    torneio = bool(str(extra.get("mtt_starttime") or "").strip())

    return CanonicalHand(
        site=f"Suprema · clube {inicio.get('clubID') or '?'}"[:80],
        hand_id=str(dados.get("replayGameID")
                    or inicio.get("id") or "suprema")[:64],
        format=HandFormat.TOURNAMENT if torneio else HandFormat.CASH,
        stakes=Stakes(small_blind=sb, big_blind=bb, ante=ante),
        hero=heroi,
        players=assentos,
        hero_cards=cartas_heroi,
        shown_cards=mostradas,
        streets=streets,
        final_board=board_final,
        total_pot=total,
        collected=ganhou,
        tournament_id=str(inicio.get("matchID") or "") or None,
        source_format="suprema_replay",
        confidence=0.95,
    )


def fetch_and_parse(url_do_link: str) -> CanonicalHand | None:
    """Link do aluno -> mão pronta. None quando não dá (e o motivo vai no log)."""
    dados = baixar(url_do_link)
    if not dados:
        return None
    try:
        return parse(dados)
    except Exception as exc:
        log.warning("suprema: falha ao converter a mão: %s", exc, exc_info=True)
        return None
