# Anexo 4 — Auditoria de arquitetura

*Agente de arquitetura, 06/09/2026. Medido por AST (594 arestas de import
entre módulos de `app/`). 122 arquivos `.py` em `app/` (112 módulos), 120
arquivos de teste. `ARQUITETURA.md` diz "99 módulos, 74 testes", `llm.py`
"2.730 linhas" (real 3.435), `analysis/` "47 módulos" (real 58) — ~20%
desatualizado.*

## 1. Violações de camada

Matriz (pares módulo→módulo):

| de \ para | models | parsers | analysis | db | agent | bot | api |
|---|---|---|---|---|---|---|---|
| parsers | 10 | 9 | 0 | 0 | 0 | 0 | 0 |
| analysis | 20 | 0 | 112 | 0 | **6** | **4** | 0 |
| db | 1 | 0 | **2** | 1 | 0 | **1** | 0 |
| agent | 2 | 0 | 26 | 4 | 5 | **3** | 0 |
| bot | 2 | 3 | 49 | 6 | 13 | 33 | **1** |
| api | 1 | 0 | 2 | 1 | 0 | **1** | 9 |

**`analysis/` → `agent/` (7):** `handreport.py:15` (`analyze_hand` **no topo**), `:156`, `:357` (chama a API de dentro de `analysis/`); `handsearch.py:73,159`; `mental.py:81`; `selfcheck.py:70`; `tournament_board.py:68`.

**`analysis/` → `bot/` (6):** `handreport.py:109,545,584`; `dossie_html.py:106,304`; `selfcheck.py:107`. Causa: `hand_storyboard_streets` (`processing.py:3042`), `film_bands` (`:2374`), `decisions_by_street` (`:2914`) são puras e ficaram no bot.

**`db/` → `bot/`:** `db/repository.py:107` — `get_or_create_user` importa `app.bot.notify` e manda Telegram de dentro do repositório. `:231` (`FONTES_COMPLETAS`), `:342` (`bayes_stats`).

**`agent/` → `bot/` (10, todos em `llm.py`):** `:1296-1332` (`processing`), `:1358-1608` (`notify`), `:1609` (`progresso`).

**Ciclos mútuos (11):** `llm↔processing`, `handreport↔processing`, `handreport↔handsearch`, `selfcheck↔processing`, `site_assets↔processing`, `guarda_saida↔processing`, `lobby_flow↔processing`, `mao_do_relatorio↔processing`, `torneio_flow↔processing`, `nash_pushfold↔pushfold`, `manual_md↔manual_page`. Todos quebrados com import dentro de função — `handlers.py` tem **54 imports locais** de `processing`.

## 2. Acoplamento

**Fan-in:** `models.canonical` 39 · `analysis.equity` 22 · `config` 16 · `analysis.ranges` 14 · `db` 12. `bot.processing` **10** — importado por `llm`, `dossie_html`, `handreport`, `selfcheck`, `site_assets`, `guarda_saida`, `lobby_flow`, `mao_do_relatorio`, `torneio_flow`, `handlers`.

**Fan-out:** `bot.processing` **60** (importa 54% do sistema) · `agent.llm` 33 · `bot.handlers` 21 · `analysis.handreport` 13 · `analysis.dossie_html` 11.

`processing.py` é o deus-módulo: maior fan-out E 8º maior fan-in. O teto de 3.600 linhas segura tamanho, não acoplamento.

## 3. Cobertura de testes por área

| área | módulos | referenciados | testes que tocam |
|---|---|---|---|
| bot | 22 | 18 (+2 indiretos) | 64 |
| agent | 9 | 8 | 50 |
| analysis | 59 | 58 | 47 |
| parsers | 11 | 6 (+4 via `parse_text`) | 15 |
| db | 2 | 2 | 14 |
| api | 9 | 6 | 12 |
| billing | 2 | 1 | 2 |

**Sem referência:** `analysis/branding.py` (71); `bot/lobby_flow.py` (114, **zero** referência — entrega a leitura do lobby ao aluno); `storyboard.py` e `link_do_clube.py` só via reexport em `processing`; `agent/speech.py` (33); `api/landing.py` (250); `api/manual_md.py` (171); `billing/stripe_service.py` (124 — **o webhook que dá plano pago não tem teste**); `app/repository.py` (734, morto).

Falsos positivos descartados: os parsers são reexportados via `registry.py`.

## 4. Estado global mutável

`handlers.py` tem **85** `asyncio.to_thread` — threads reais.

**Com teto** (via `memoria_do_processo.lembrar`, 200 usuários): `RECENT_HANDS`, `LAST_ANALYSIS`, `LAST_UPLOAD_KIND`, `LAST_HAND_META`, `RECENT_DRILLS`, `PENDING_DOCS`, `PENDING_PASTE`, `HR_PENDING`. **`PENDING_CHARTS` — teto furado**: `:616,632` escrevem direto fora do lock.

**Sem teto:** `river_solver._CACHE:34`; `handlers._IDENTIDADE_VISTA:117`; `quota._mem:52` (cota em memória quando o banco cai; zera no restart).

**Singletons escritos por um aluno e lidos por outro (o risco real):**

| variável | escrita | leitura |
|---|---|---|
| `llm.py:3007 LAST_VISION_CHECK` | `extract_from_image` | `processing.py:792` → "li A♠K♦ — confere?" |
| `llm.py:2428 LAST_SIMPLIFY_REASON` | `simplify` | `processing.py:1397` → "já está simples" |
| `llm.py:3316 LAST_LOBBY_CHECK` | lobby | `lobby_flow.py:101` → "⚠️ Li com dúvida" |
| `llm.py:3116 LAST_VISION_ERROR` | `:3082` | `pipeline.py:162` |
| `llm.py:3119 LAST_FOLLOWUP_ERROR` | `:2762` | `processing.py:1214` (telemetria) |

Dois alunos mandando print ao mesmo tempo → o B pode receber a divergência de cartas do A. `_TOOL_CHAT` já é `ContextVar` (`llm.py:1298`) — o padrão certo existe no mesmo arquivo.

## 5. Tratamento de exceção

283 `except`; **239 largos (84%)**; 0 nus. Dos 239, **165 engolem**: 53 `pass`, 52 `return X`, 31 `continue`, 22 `= None`, 7 `log.debug`. Por arquivo: `handlers.py` 24, `processing.py` 21, `llm.py` 18.

Os 10 mais perigosos:
1. `licao_qualidade.py:138` — guarda de mentira de poker quebra → `pass` → lição vai para todos.
2. `handlers.py:2279` — `reply_document` do relatório falha → `pass`; doc já removido da fila.
3. `handlers.py:2270` — idem para gráficos; o comentário em `:2266` nomeia "incoerência silenciosa".
4. `processing.py:845` — `persist_conversation` → `pass` → no próximo deploy, "não achei a mão".
5. `processing.py:829` — `_refresh_gabarito` → `pass` → gabarito de versão antiga.
6. `db/repository.py:349` — shrinkage falha → grava VPIP **cru** na história sem marcar.
7. `db/repository.py:559,586` — `model_validate` falha → `None` → mãos antigas invisíveis.
8. `taxonomia.py:431` — detector quebra → `continue` → mão some do numerador E do denominador.
9. `guarda_fatos.py:123` — equity falha → `continue` → afirmação sem conferência.
10. `llm.py:2525` — `simplify` → `return None` sem logar.

Menção: `pushfold.py:115,197` — solver quebra → tabela heurística como "aprox. Nash" sem log.

## 6. Configuração

32 leituras de env, todas com default; nenhuma obrigatória, nenhuma validação no boot.
- `ADMIN_TELEGRAM_ID` default `'6452742024'` **e hardcoded** em `saude.py:26`, `licao_envio.py:19`, `notify.py:23`.
- `TELEGRAM_BOT_USERNAME` default `'KKNUts_BOT'` — deep link errado é "botão que abre o bot errado".
- `PUBLIC_BASE_URL` default `localhost:8000` → `success_url` do Stripe aponta para localhost.
- `CALIBRATION_FILE` relativo ao CWD; cron noutro dir → priors sem log.
- `SUPABASE_*` vazios → cota vira `_mem` e zera no restart.

## 7. Duplicação

- `_font` ×6 (branding, hand_figure, range_chart, evolution_chart, style_chart, tournament_board) — duas estratégias de caminho.
- `_combos_da_mao` ×2 (`combos.py:72` própria vs `multiway_equity.py:29` delega) — mesmo conjunto, ordem diferente.
- `_mediana` ×2 (`defesa.py:200` retorna None em vazia; `estrutura.py:75` IndexError).
- `_num` ×4, `_cards` ×5, `_card` ×4 nos parsers.
- Homônimos com semântica diferente: `texto_do_plano` (`problemas.py:340` plano de estudo vs `processing.py:2669` cobrança); `_acao_pre_do_heroi` (`allin_audit.py:163` dict vs `taxonomia.py:99` Action).

## TOP 5 riscos por impacto no aluno

1. **Contaminação entre alunos** pelos `LAST_*` de `llm.py` sob 85 pontos de `to_thread`.
2. **Portões que falham abertos e calados** (`licao_qualidade:138`, `guarda_fatos:123`).
3. **Entrega perdida sem rastro** (`handlers.py:2270,2279`, `processing.py:845`).
4. **`processing.py` como deus-módulo** — 26 pontos onde camadas de baixo dependem de `bot/`.
5. **Números degradados sem marca** (`db/repository.py:349`, `pushfold.py:115`, `taxonomia.py:431`).
