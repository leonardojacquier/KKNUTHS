---
tags: [kknuths, tecnica, replay]
atualizado: 2026-07-26
---
# Ingestão de Replays de Clube

O público BR compartilha **link**, não arquivo. Dois clubes abrem sozinhos
hoje: **PPPoker** e **Suprema**. Os demais (ClubGG, WePoker, PokerBros,
UPoker) caem numa mensagem que NOMEIA o clube e oferece print/descrição.

## PPPoker
- Replayer WebGL (Egret); a mão é um JSON estático em
  `alicdn.pppoker.club/review_hand/<shareKey>.json`
- O `shareKey` do link É o nome do arquivo → extrair a mão vira um GET
- Cartas: `divmod(v, 256)` → (naipe, rank), **1=♦ 2=♣ 3=♥ 4=♠**
- Extração da chave aceita `shareKey`/`sharekey`/`share_key` em qualquer
  caixa, chave com `_`, URL escapada e UUID solto. O regex estreito
  devolvia None num link BOM e o aluno levava "não abro esse tipo"

## Suprema
Jogo **Cocos Creator** em `r.supremapoker.net`; a mão vem de uma API separada.
A regra abaixo é **transcrição do `main.45fc5.js` do próprio replayer**:

```js
token = params.t.substr(0, 8);     // só os 8 PRIMEIROS
tp    = params.t.substr(10, 1);    // índice 10 escolhe o ambiente
sendAsync(`${url}?s=${token}`)     // GET, sem cabeçalho extra
```

- Endpoint: `ra.supremapoker.net/supremaAPI/replayInfo.php?s=<8 chars>`
  (dev = `brazildev.zvga.me:8590`, homologação = `braziluatcdn7.zvga.me`)
- Layout do token: `[8 id][2 ?][1 ambiente][2 idioma]` — ex. `forilma5` `00`
  `2` `pt`. Só os 8 primeiros variam
- **Método GET.** POST leva 403 do CloudFront ("supports only cachable
  requests") — que não é recusa, é a URL certa reclamando do método
- **Cabeçalho de navegador é OBRIGATÓRIO.** A mesma URL devolve `-1`
  (2 bytes) para o User-Agent padrão do curl e 13 kB para o Chrome. Ver
  [[#O -1 que custou seis rodadas]]
- `er` do link não participa da chamada
- Cartas: `divmod(v, 16)`, **mesma escada de naipes da PPPoker** (que usa
  256). Há teste comparando os dois mapas
- Sem login, sem cookie, `access-control-allow-origin: *`

### Formato do JSON
| chave | conteúdo |
|---|---|
| `playerID` | uid do HERÓI |
| `players` | uid → displayID, seat, `coins` = stack **antes do ante** |
| `gameExtra` | filme da mão: `startinfo`, `player_action`, `nextround` |
| `gameResult.sidepotsdetail` | um bloco por pote, com `prize` de cada um |
| `gameResult.sharedcardsD` | board final |

`state`: 1 ante · 2 blinds · 3 preflop · 4 flop · 5 turn · 6 river (1-3 são
todos PRÉ-FLOP; separá-los criaria street que não existe).

### Decisões do parser (cada uma virou teste)
- **`allin` não é tipo de ação** — vira RAISE, CALL ou BET conforme o total
  fique acima ou abaixo da maior aposta da street. Na mão-fixture isso
  separa o re-shove do MP (123.652, raise) do all-in do HJ por menos
  (105.000, **call**). Tratar como categoria própria apaga a agressão, que
  é o que a análise lê
- **`return` não é jogada** — é aposta não paga voltando (`chips` negativo).
  Como ação viraria "call negativo" no meio da mão; entra como correção do
  investido
- **Ante fora do `to_amount`**, igual à PPPoker. Ante não é aposta a
  igualar; somá-lo faria a MESMA mão sair diferente conforme a sala
- **`nextround` nomeia a street que ACABOU** — o evento `preflop` carrega o
  FLOP. Ler o nome como "board desta street" adianta uma carta em todas
- **`players.coins` é o stack PRÉ-ante** — usar o pós-ante encolhe a mesa
  inteira em um ante
- Nome repetido ganha sufixo de assento, senão as ações de um jogador
  entram no outro
- Carta ilegível é descartada, não vira placeholder: mão com carta
  inventada sai confiante e errada

## O -1 que custou seis rodadas
O servidor não diz que recusou o cliente — **finge que a mão não existe**.
`-1` chega com **HTTP 200**, então quem confia no status importa lixo, e é
indistinguível de "token expirado". Perseguimos expiração enquanto o
problema era o `User-Agent`.

Lições que viraram código:
- resposta de ERRO é informação: 403 do CloudFront = método errado com URL
  certa; corpo que é só um número = endpoint responde, parâmetro errado.
  Ver `pista_do_erro` em [[#Farejador de replay]]
- GET antes de POST: API de clube fica atrás de CDN

## GGPoker / PokerCraft — INVESTIGAÇÃO ENCERRADA (2026-07-26)
Não abrimos, e a decisão é definitiva. Fica registrado para ninguém
reabrir do zero.

`gg.gl/<código>` é encurtador → `my.pokercraft.com/embedded/shared/
hand-replay/<alias>`. App Angular que desenha a mão num `<canvas>` (não há
vídeo). **Duas** chamadas, achadas por HAR:

| endpoint | tamanho | o que é |
|---|---|---|
| `/api/share/alias?type=handReplay&alias=…` | 336 B | envelope |
| `/api/share/alias/hand-replay?type=…` | **22.368 B** | **a mão** |

Ambas devolvem `{"data": "<hex>"}` **cifrado**:

| medida | envelope | a mão |
|---|---|---|
| blocos de 16 | 21 | 1.398 |
| entropia | 7,39 | **7,99** de 8,00 |
| bytes distintos | 189/256 | **256/256** |
| blocos repetidos | 0 | 0 |

Entropia 7,99 com os 256 valores presentes e nenhum bloco repetido é
indistinguível de aleatório: não é compressão nem codificação. E o
envelope MUDA a cada chamada com o mesmo link (IV aleatório).

**A chave vive no bundle do cliente.** Extraí-la para decifrar seria
contornar proteção técnica deliberada de sala regulada — não fazemos, e
não indicamos caminho. Diferente da Suprema, onde o JSON é servido em
claro e só faltava o cabeçalho certo.

**O caminho para GGPoker é o arquivo do PokerCraft** (Hand History →
Download → `.txt`), que é oficial, exato e traz a SESSÃO inteira em vez de
uma mão. É o que a mensagem do bot passa a oferecer — mandar o aluno só
para o print seria o pior conselho disponível.

Armadilha para quem revisitar: o `ng-state` da página traz apenas a
PRIMEIRA chamada (o servidor renderizou), o que dá a falsa impressão de
que só existe uma. A segunda é feita no navegador e só aparece em HAR
capturado **com o DevTools aberto antes do carregamento**.

## Farejador de replay
`scripts/sniff_replay.py <link> [--telegram]` — roda de onde a rede alcança
o clube (o VPS). Descobre de onde um replayer novo tira a mão:

1. baixa a página com UA de **navegador** (sem isso: falso negativo)
2. varre **TODO** `<script src>`, sem filtro de nome — o filtro por
   palavra-chave descartava `/assets/index-4f3a.js`, que é onde o endpoint
   mora, e o script concluía "não achei" sem ter olhado
3. lista **todas** as URLs absolutas dos bundles (`urls_cruas`) — o filtro
   escolhe o que TENTAR, isto mostra o que EXISTE
4. matriz método × parâmetro nos endpoints, com Referer/Origin
5. traduz respostas de erro em pista, em vez de descartá-las
6. salva página e bundles em `/tmp/replay_sniff/` (só via `main()`)

Se ele não achar nada, o caminho é **F12 → Network → Preserve log →
recarregar** e `Copy as cURL`. Foi o `grep` do bundle e o HAR que
destravaram a Suprema, não os palpites.

## Ligação no produto (testada elo a elo)
`replay_link_info` → `ingest(fmt)` → parser → análise. Motor certo que
ninguém chama não entrega nada — foi o defeito do gráfico de EV, e por isso
há teste para cada elo.

Relacionado: [[Arquitetura Técnica]] · [[Testes e Qualidade]] ·
[[Runbook de Operação]]
