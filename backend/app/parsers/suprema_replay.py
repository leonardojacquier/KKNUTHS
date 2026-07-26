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
