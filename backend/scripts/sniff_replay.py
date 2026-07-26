"""FAREJADOR DE REPLAY — descobre de onde um replayer de clube tira a mão.

Por que existe: o parser da PPPoker não saiu de documentação, saiu de
captura de rede. O replayer é um jogo WebGL, mas a mão em si estava num
JSON estático num CDN — e o `shareKey` do link era o nome do arquivo. Achar
isso levou horas de tentativa manual. Este script faz a mesma busca sozinho,
para o próximo clube (Suprema, ClubGG, WePoker, PokerBros, UPoker).

Ele NÃO escreve parser. Ele responde a única pergunta que trava o parser:
*qual URL devolve a mão, e com que cara vem o JSON?* Com essa resposta o
parser vira trabalho mecânico de mapear campo.

Rode de onde a rede alcança o clube (o VPS):

    python scripts/sniff_replay.py "<link do replay>" [--telegram]

O que faz, em ordem:
  1. baixa a página do replay com User-Agent de celular (replayer de clube
     costuma servir coisa diferente pro desktop);
  2. varre a página E os .js que ela carrega procurando candidatos a
     endpoint (api/, .json, cdn., host de review/hand/replay);
  3. tenta cada candidato, injetando a chave do link onde couber — inclusive
     o palpite no formato PPPoker, porque vários apps de clube são
     white-label do mesmo fornecedor;
  4. de tudo que voltar JSON, mostra o ESQUELETO (chaves e tipos, sem
     despejar valores) e marca o que parece mão de poker.

Nada de segredo sai daqui: o link de replay é o que o próprio jogador
compartilha. O script só LÊ — não envia nada, não faz login, não toca em
conta de sala.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlparse

# Passar-se por NAVEGADOR não é detalhe: a API da Suprema devolve `-1` (2
# bytes) para o User-Agent padrão do curl e 13 kB para o Chrome, na MESMA
# URL. Sem estes cabeçalhos o farejador conclui "endpoint errado" quando o
# endpoint estava certo — o pior falso negativo que ele pode dar.
_UA_MOBILE = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/150.0.0.0 Safari/537.36"),
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}
_TIMEOUT = 25

# sinais de que um JSON é uma MÃO, não configuração de UI. Peso por quanto
# cada chave é específica de poker — 'cards' vale mais que 'id'.
_SINAIS = {
    "cards": 3, "card": 2, "board": 3, "hole": 3, "holecards": 3,
    "players": 3, "player": 1, "seat": 2, "seatid": 3, "seats": 2,
    "actions": 3, "action": 1, "flop": 3, "turn": 2, "river": 3,
    "preflop": 3, "pre_flop": 3, "pot": 3, "pots": 3, "pool": 1,
    "blind": 2, "smallblind": 3, "small_blind": 3, "bigblind": 3,
    "ante": 2, "stack": 2, "chips": 2, "winner": 2, "winning": 2,
    "showdown": 3, "rake": 2, "dealer": 2, "gameid": 1, "hand_id": 3,
}


# ------------------------------------------------------------- puras
def chaves(obj, prof: int = 0, limite: int = 6) -> set[str]:
    """Todas as chaves do JSON, em qualquer profundidade, minúsculas."""
    out: set[str] = set()
    if prof > limite:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k).lower())
            out |= chaves(v, prof + 1, limite)
    elif isinstance(obj, list):
        for v in obj[:20]:
            out |= chaves(v, prof + 1, limite)
    return out


def parece_mao(obj) -> int:
    """Pontuação de 'isto é uma mão de poker'. >= 8 é candidato forte.

    Soma de sinais em vez de exigir uma chave específica: cada clube nomeia
    do seu jeito, e exigir 'players' perderia um JSON que chama de 'users'.
    """
    ks = chaves(obj)
    return sum(peso for chave, peso in _SINAIS.items() if chave in ks)


def esqueleto(obj, prof: int = 0, limite: int = 4) -> object:
    """JSON reduzido a chaves e TIPOS. É o que se lê para escrever o parser;
    despejar os valores só afoga quem está procurando a estrutura."""
    if prof > limite:
        return "…"
    if isinstance(obj, dict):
        return {str(k): esqueleto(v, prof + 1, limite)
                for k, v in list(obj.items())[:40]}
    if isinstance(obj, list):
        if not obj:
            return []
        return [esqueleto(obj[0], prof + 1, limite),
                f"…+{len(obj) - 1} itens" if len(obj) > 1 else None]
    if isinstance(obj, str):
        return f"str({len(obj)})" if len(obj) > 24 else f"'{obj}'"
    return type(obj).__name__


_NOMES_CONHECIDOS = ("sharekey", "share_key", "handid", "hand_id", "hand",
                     "gameid", "game_id", "replay", "code", "key", "id")


def _parece_identificador(v: str) -> bool:
    """Valor com cara de id de mão, não de flag nem de timestamp.

    Exigir letra derruba timestamp (`1690000000`) e contador (`er=5`) sem
    precisar de lista de nomes proibidos.
    """
    if not re.fullmatch(r"[0-9a-zA-Z_-]{8,}", v or ""):
        return False
    return bool(re.search(r"[a-zA-Z]", v)) or len(v) >= 16


def chave_do_link(url: str) -> str | None:
    """O identificador da mão dentro do link, seja qual for o nome do
    parâmetro.

    Enumerar nomes não funciona: a Suprema chama de `t`
    (`r.supremapoker.net/?t=0s2kipvi002pt&er=5`), e um link real devolvia
    None — o farejador rodaria sem gerar palpite nenhum. Agora a regra olha
    o VALOR: nome conhecido tem preferência, senão vale o maior valor com
    cara de id.
    """
    from urllib.parse import parse_qsl, unquote, urlparse

    u = unquote(url or "")
    uuid = re.search(r"\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                     r"[0-9a-f]{4}-[0-9a-f]{12})\b", u, re.I)
    if uuid:
        return uuid.group(1)

    try:
        p = urlparse(u)
        params = parse_qsl(p.query, keep_blank_values=True)
        params += parse_qsl((p.fragment or "").lstrip("#/?"),
                            keep_blank_values=True)
    except Exception:
        params = []
    validos = [(k.lower(), v) for k, v in params if _parece_identificador(v)]
    for nome in _NOMES_CONHECIDOS:
        for k, v in validos:
            if k == nome:
                return v
    if validos:
        return max(validos, key=lambda kv: len(kv[1]))[1]

    cauda = re.search(r"/([0-9a-zA-Z_-]{16,})(?:\.json)?/?$", u)
    return cauda.group(1) if cauda else None


def scripts_da_pagina(html: str, base: str) -> list[str]:
    """TODO <script src> da página, sem filtro de nome.

    Existe separado de `candidatos_da_pagina` por causa de uma falha real:
    o filtro por palavra-chave (api|json|hand|replay…) descartava o bundle
    `/assets/index-4f3a.js`, que é justamente onde o endpoint está escrito.
    O farejador então varria zero bundles e concluía "não achei nada" sem
    nunca ter olhado no lugar certo.
    """
    urls = [urljoin(base, m.group(1)) for m in re.finditer(
        r"""<script[^>]+src=['"]([^'"]+)['"]""", html or "", re.I)]
    return list(dict.fromkeys(urls))[:12]


def _blobs_json(texto: str, minimo: int = 80) -> list[object]:
    """Objetos JSON embutidos no HTML (`window.__DADOS__ = {...}`).

    Página de 4 KB pode já trazer a mão inteira dentro de um <script>.
    Contagem de chaves porque regex não equilibra delimitador.
    """
    out: list[object] = []
    for i, ch in enumerate(texto or ""):
        if ch != "{" or len(out) >= 8:
            continue
        nivel, fim = 0, None
        for j in range(i, min(i + 200_000, len(texto))):
            if texto[j] == "{":
                nivel += 1
            elif texto[j] == "}":
                nivel -= 1
                if nivel == 0:
                    fim = j + 1
                    break
        if not fim or fim - i < minimo:
            continue
        try:
            out.append(json.loads(texto[i:fim]))
        except Exception:
            pass
    return out


def parece_endpoint(url: str) -> bool:
    """URL que vale bater com POST e variação de parâmetro.

    `.php` conta: a Suprema serve a mão em
    `ra.supremapoker.net/supremaAPI/replayInfo.php`, e uma API PHP quase
    sempre quer POST — bater só com GET devolve página de erro e parece
    'não é aqui'.
    """
    if re.search(r"\.(js|css|png|jpg|jpeg|gif|svg|woff2?|ttf|ico|mp3|mp4)"
                 r"($|\?)", url or "", re.I):
        return False
    return bool(re.search(r"(\.php|\.json|/api/|api\.|/v\d/|info|detail|"
                          r"replay|record|hand|review)", url or "", re.I))


def combinacoes_de_parametros(chave: str, query: str) -> list[dict]:
    """Como o endpoint pode querer receber a mão.

    A querystring ORIGINAL vem primeiro: é literalmente o que a página usa,
    então é o palpite com mais chance. Os apelidos existem porque a API
    interna raramente usa o mesmo nome curto da URL pública.
    """
    from urllib.parse import parse_qsl

    original = dict(parse_qsl(query or ""))
    combos: list[dict] = []
    if original:
        combos.append(original)
    for nome in ("t", "id", "key", "handId", "hand_id", "replayId",
                 "gameId", "shareKey"):
        c = {nome: chave}
        if original.get("er"):
            c["er"] = original["er"]
        if c not in combos:
            combos.append(c)
    return combos[:9]


def urls_cruas(texto: str) -> set[str]:
    """TODA url absoluta citada, sem filtro de palavra-chave.

    O filtro de `candidatos_da_pagina` serve para escolher o que TENTAR;
    esta função serve para o humano ENXERGAR. São coisas diferentes: um
    host de API sem 'api' no nome, ou um endpoint montado por concatenação
    (BASE + '/hand/' + id), nunca aparecem inteiros para a regra.
    """
    achados = {m.group(0).rstrip("\"'`,);")
               for m in re.finditer(r"https?://[^\s'\"`<>()\\]{6,200}",
                                    texto or "")}
    return {u for u in achados
            if not re.search(r"\.(png|jpg|jpeg|gif|svg|css|woff2?|ttf|ico|"
                             r"mp3|wav|mp4)($|\?)", u, re.I)
            and not re.search(r"(w3\.org|schema\.org|github\.com|"
                              r"npmjs|license|creativecommons)", u, re.I)}


def candidatos_da_pagina(texto: str, base: str) -> list[str]:
    """URLs plausíveis de API/CDN citadas na página ou num .js dela.

    Devolve em ordem de promessa: quem tem 'hand'/'review'/'replay' no
    caminho vem antes de um .json qualquer.
    """
    achados: list[str] = []
    for m in re.finditer(r"""['"](https?://[^'"\s]{8,300}|/[^'"\s]{4,300})['"]""",
                         texto or ""):
        bruto = m.group(1)
        if not re.search(r"(api|\.json|cdn|review|hand|replay|record|game)",
                         bruto, re.I):
            continue
        if re.search(r"\.(png|jpg|jpeg|gif|svg|css|woff2?|ttf|mp3|wav)($|\?)",
                     bruto, re.I):
            continue
        achados.append(urljoin(base, bruto))

    def promessa(u: str) -> int:
        p = 0
        if re.search(r"(review_?hand|hand_?record|replay|review)", u, re.I):
            p -= 3
        if re.search(r"\.json", u, re.I):
            p -= 2
        if re.search(r"/api/", u, re.I):
            p -= 1
        return p

    vistos, saida = set(), []
    for u in sorted(achados, key=promessa):
        if u not in vistos:
            vistos.add(u)
            saida.append(u)
    return saida[:60]


def palpites_conhecidos(chave: str, host: str, query: str = "") -> list[str]:
    """Padrões que já funcionaram em outro clube. Vários apps de clube são
    white-label do mesmo fornecedor — o palpite é barato e às vezes acerta
    de primeira.

    `query` é a querystring ORIGINAL do link: quando o replay usa mais de um
    parâmetro (a Suprema manda `t` e `er`), a API costuma querer os dois, e
    palpitar só com a chave erra por falta de argumento.
    """
    if not chave:
        return []
    partes = host.split(".")
    raiz = partes[-2] if len(partes) >= 2 else host
    # r.supremapoker.net -> supremapoker.net: a API raramente fica no
    # subdomínio que serve a página do replay
    pai = ".".join(partes[-2:]) if len(partes) > 2 else host
    hosts = [host, pai, f"cdn.{pai}", f"api.{pai}", f"alicdn.{raiz}.club"]
    caminhos = [f"/review_hand/{chave}.json", f"/hand/{chave}.json",
                f"/api/hand/{chave}", f"/api/replay/{chave}",
                f"/api/record/{chave}", f"/api/hand/detail/{chave}",
                f"/replay/{chave}.json", f"/{chave}.json"]
    saida = [f"https://{h}{c}" for h in dict.fromkeys(hosts)
             for c in caminhos]
    if query:
        # mesma API, mas chamada como a página chamaria: com os parâmetros
        for h in dict.fromkeys(hosts):
            saida += [f"https://{h}/api/hand?{query}",
                      f"https://{h}/api/replay?{query}",
                      f"https://{h}/hand?{query}"]
    return saida


# --------------------------------------------------------------- I/O
def _get(url: str, limite_bytes: int = 4_000_000) -> tuple[int, bytes, str]:
    req = urllib.request.Request(url, headers=_UA_MOBILE)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return (r.status, r.read(limite_bytes),
                    r.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as e:
        return e.code, b"", ""
    except Exception as e:
        return 0, str(e).encode()[:200], ""


_DESPEJO = "/tmp/replay_sniff"


def _guardar(pasta: str | None, nome: str, dados: bytes) -> None:
    """Guarda página e bundles em disco. Quando o farejador não acha nada,
    o material bruto é o que permite olhar com o olho humano em vez de
    rodar de novo às cegas.

    `pasta=None` NÃO grava, e esse é o padrão de propósito: com o caminho
    fixo embutido, o teste de integração gravou seus fixtures no /tmp do
    VPS durante o portão do deploy. O admin abriu a pasta esperando a
    página da Suprema e achou 57 bytes de mentira minha. Efeito colateral
    só sai de `main()`, nunca de biblioteca.
    """
    import os

    if not pasta:
        return
    try:
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, nome), "wb") as f:
            f.write(dados)
    except Exception:
        pass


def _bater(url: str, metodo: str, dados: dict, referer: str) -> tuple[int, bytes]:
    """GET / POST-form / POST-json no mesmo endpoint.

    O Referer vai junto de propósito: API de clube costuma recusar quem não
    veio da própria página do replay, e sem ele a resposta é um 403 que
    parece 'endpoint errado'.
    """
    from urllib.parse import urlencode, urlparse

    cab = dict(_UA_MOBILE)
    cab["Referer"] = referer
    cab["Origin"] = f"https://{urlparse(referer).netloc}"
    corpo = None
    if metodo == "GET":
        url = url + ("&" if "?" in url else "?") + urlencode(dados)
    elif metodo == "POST-form":
        corpo = urlencode(dados).encode()
        cab["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        corpo = json.dumps(dados).encode()
        cab["Content-Type"] = "application/json"
    req = urllib.request.Request(
        url, data=corpo, headers=cab,
        method="GET" if metodo == "GET" else "POST")
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return r.status, r.read(4_000_000)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return 0, b""


# respostas de ERRO que na verdade CONFIRMAM o endpoint. O 403 do
# CloudFront "supports only cachable requests" quer dizer: a URL existe, o
# método é que está errado — use GET. Jogar isso fora como "falhou" foi o
# que quase me fez descartar o endpoint certo da Suprema.
_PISTAS = (
    ("only cachable requests", "CDN só aceita GET/HEAD — o endpoint EXISTE"),
    ("request method that was used", "método errado, a URL está certa"),
    ("method not allowed", "método errado, a URL está certa"),
    ("missing parameter", "faltou parâmetro — a URL está certa"),
    ("invalid token", "quer autenticação — a URL está certa"),
)


def pista_do_erro(corpo: bytes) -> str | None:
    """Traduz uma resposta de erro que ainda assim é informação."""
    t = (corpo or b"").decode("utf-8", "replace").lower()[:4000]
    for marca, significado in _PISTAS:
        if marca in t:
            return significado
    # corpo que é só um número curto ("-1", "0", "404") é código de erro da
    # APLICAÇÃO, com HTTP 200. Foi o que a Suprema devolveu quando o método
    # já estava certo: prova de que o endpoint responde, e de que o
    # problema passou a ser o parâmetro (ou o replay expirou).
    if re.fullmatch(r"\s*-?\d{1,4}\s*", t or ""):
        return (f"resposta da aplicação «{t.strip()}» — o endpoint RESPONDE; "
                "o que está errado agora é o parâmetro (ou o replay expirou)")
    return None


def probar_endpoint(url: str, combos: list[dict], referer: str,
                    relatar=print) -> list[dict]:
    """Roda a matriz método × parâmetros e devolve o que voltou com cara de
    mão. Para na primeira combinação boa de cada método — o objetivo é
    descobrir COMO chamar, não varrer tudo.

    GET vem primeiro: API de clube costuma ficar atrás de CDN, e CDN
    normalmente só deixa passar método cacheável.
    """
    achados: list[dict] = []
    ja_relatado: set[str] = set()
    for metodo in ("GET", "POST-form", "POST-json"):
        for dados in combos:
            s, c = _bater(url, metodo, dados, referer)
            if s != 200 or not c:
                # resposta de erro pode ser a melhor pista do dia — antes
                # ela era descartada em silêncio junto com o resto
                pista = pista_do_erro(c)
                if pista and pista not in ja_relatado:
                    ja_relatado.add(pista)
                    relatar(f"      ↳ {metodo} devolveu {s}: {pista}")
                continue
            obj = _talvez_json(c)
            if obj is None:
                continue
            pontos = parece_mao(obj)
            if pontos >= 5:
                achados.append({"url": f"{url}  [{metodo} {dados}]",
                                "pontos": pontos, "esqueleto": esqueleto(obj),
                                "bruto": obj})
                break
    return achados


def _talvez_json(corpo: bytes):
    try:
        return json.loads(corpo.decode("utf-8", "replace"))
    except Exception:
        return None


def farejar(url: str, despejo: str | None = None) -> dict:
    """Devolve {'chave', 'achados': [{url, pontos, esqueleto}], 'tentados'}."""
    partes_url = urlparse(url)
    host = (partes_url.netloc or "").lower()
    chave = chave_do_link(url)
    print(f"host: {host}\nchave extraída do link: {chave or '(nenhuma)'}\n")
    if not chave:
        print("AVISO: sem chave, os palpites por padrão conhecido não rodam "
              "— sobra só o que estiver escrito na página e nos bundles.\n")

    status, corpo, ctype = _get(url)
    print(f"página do replay: HTTP {status} · {ctype} · {len(corpo)} bytes")

    alvos: list[str] = list(palpites_conhecidos(
        chave or "", host, partes_url.query))
    cruas: set[str] = set()
    # o próprio link pode JÁ ser a mão: alguns clubes compartilham a URL do
    # JSON direto. Eu descartava essa resposta e saía dizendo "nada achei"
    # com a mão na mão.
    direto = _talvez_json(corpo) if corpo else None
    achados_diretos = []
    if direto is not None and parece_mao(direto) >= 5:
        achados_diretos.append({"url": url, "pontos": parece_mao(direto),
                                "esqueleto": esqueleto(direto),
                                "bruto": direto})
    if corpo and "json" not in ctype.lower():
        texto = corpo.decode("utf-8", "replace")
        _guardar(despejo, "pagina.html", corpo)

        # mão embutida no próprio HTML: página de 4 KB pode já trazer tudo
        for blob in _blobs_json(texto):
            if parece_mao(blob) >= 5:
                achados_diretos.append({
                    "url": url + " (JSON embutido no HTML)",
                    "pontos": parece_mao(blob), "esqueleto": esqueleto(blob),
                    "bruto": blob})

        da_pagina = candidatos_da_pagina(texto, url)
        scripts = scripts_da_pagina(texto, url)
        print(f"  scripts na página: {len(scripts)}")
        for s_url in scripts:
            print(f"    {s_url}")
        print(f"  candidatos citados na página: {len(da_pagina)}")
        alvos += da_pagina

        # TODO bundle é varrido, tenha o nome que tiver — o endpoint mora
        # aqui, e filtrar bundle por nome foi o que cegou a primeira versão
        de_bundle = 0
        for j in scripts:
            s, c, _ = _get(j)
            if s != 200 or not c:
                print(f"    ! bundle não baixou ({s}): {j}")
                continue
            miolo = c.decode("utf-8", "replace")
            _guardar(despejo, re.sub(r"[^\w.-]", "_", j.split("/")[-1])[:60], c)
            novos = candidatos_da_pagina(miolo, j)
            de_bundle += len(novos)
            alvos += novos
            cruas |= urls_cruas(miolo)
        print(f"  candidatos achados nos bundles: {de_bundle}")
        for u in sorted(alvos)[:20]:
            print(f"    → {u}")
        # TODA url absoluta do bundle, sem filtro. "3 candidatos" num app
        # inteiro é pouco demais para ser verdade: o filtro por palavra-chave
        # descarta host de API que não tenha 'api' no nome, e endpoint montado
        # por concatenação (BASE + '/x/' + id) nunca aparece inteiro. Aqui o
        # olho humano vê o que a regra não viu.
        if cruas:
            print(f"\n  URLs absolutas citadas nos bundles ({len(cruas)}):")
            for u in sorted(cruas)[:40]:
                print(f"    {u}")

        # matriz método × parâmetro nos endpoints citados. Bater só com GET
        # numa API PHP devolve página de erro e parece 'não é aqui'.
        endpoints = [u for u in sorted(cruas) if parece_endpoint(u)][:6]
        if endpoints:
            combos = combinacoes_de_parametros(chave or "", partes_url.query)
            print(f"\n  testando {len(endpoints)} endpoint(s) com "
                  f"{len(combos)} combinações × 3 métodos…")
            for e in endpoints:
                novos = probar_endpoint(e, combos, url)
                print(f"    {'✓' if novos else '·'} {e}")
                achados_diretos += novos
    if chave:
        # troca id genérico do bundle pela chave do link deste replay
        alvos += [re.sub(r"(?<=[/=])[0-9a-zA-Z_-]{16,}(?=(\.json)?$)",
                         chave, a) for a in list(alvos)[:20]]

    vistos, achados, tentados = {url}, list(achados_diretos), 0
    for alvo in alvos:
        if alvo in vistos or len(vistos) > 80:
            continue
        vistos.add(alvo)
        tentados += 1
        s, c, ct = _get(alvo)
        if s != 200 or not c:
            continue
        dados = _talvez_json(c)
        if dados is None:
            continue
        pontos = parece_mao(dados)
        if pontos >= 5:
            achados.append({"url": alvo, "pontos": pontos,
                            "esqueleto": esqueleto(dados), "bruto": dados})
    achados.sort(key=lambda a: -a["pontos"])
    return {"chave": chave, "achados": achados, "tentados": tentados}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    url = sys.argv[1]
    r = farejar(url, despejo=_DESPEJO)
    print(f"\n{r['tentados']} endpoints tentados · "
          f"{len(r['achados'])} devolveram JSON com cara de mão\n")
    if not r["achados"]:
        print("Nada por HTTP simples. Próximo passo é olhar o material bruto:\n"
              f"  ls -la {_DESPEJO}/\n"
              f"  head -c 4000 {_DESPEJO}/pagina.html\n"
              "Se a página não citar endpoint nenhum, a mão vem por "
              "WebSocket ou POST autenticado — aí só captura no navegador "
              "resolve (F12 > Network com o replay rodando).")
        return 1
    for i, a in enumerate(r["achados"][:3], 1):
        print(f"── candidato {i} (pontos {a['pontos']})\n{a['url']}")
        print(json.dumps(a["esqueleto"], ensure_ascii=False, indent=2)[:2500])
        print()
    saida = "/tmp/replay_sniff.json"
    with open(saida, "w") as f:
        json.dump([{k: v for k, v in a.items() if k != "esqueleto"}
                   for a in r["achados"][:3]], f, ensure_ascii=False, indent=2)
    print(f"JSON bruto dos candidatos: {saida}")

    if "--telegram" in sys.argv:
        from scripts.jornadas import _avisar   # reusa o aviso do admin

        _avisar("🔍 *Farejador de replay*\n"
                + "\n".join(f"• {a['pontos']} pts — `{a['url'][:120]}`"
                            for a in r["achados"][:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
