# Anexo 2 — Auditoria de produto

*Agente de produto, 06/09/2026. Leitura direta de `MANUAL.md`, `PLANO.md`,
`docs/COMPARATIVO-GTO-WIZARD.md`, `catalogo.py`, `handlers.py`,
`processing.py`, `guarda_*.py`, `link_do_clube.py`, `lobby_flow.py`,
`llm.py` (system prompt + TOOLS + `_dispatch`), `output_judge.py`,
`OPERATIONS.md`. Contagens de teste por grep — aproximadas.*

## 1. Inventário real de features

`FONTES_COMPLETAS = {txt,text,csv,phh,pdf}` (`stats.py:21`) — replay e print
ficam **fora** de toda estatística de frequência (`stats.py:113,131-134`).

| Comando | Rota | O que o aluno recebe | Gate real |
|---|---|---|---|
| `/start` | `cmd_start:226` | 5 linhas + botões Treinar/Enviar/Como funciona/Comandos; `?start=mao_<id>` abre mão do relatório | — |
| `/plano` | `cmd_plano:279` | teto, restantes | — |
| `/stats` | `cmd_stats:288` → `stats_report:1978` | perfil VPIP/PFR/3bet/AF, pró parecido, leaks+tilt | **replay-only → "Ainda não tenho mãos suas. Envie um arquivo"** (`handlers.py:295`) |
| `/estilo` | `cmd_estilo:374` → `style_report:1584` | cartão PNG + botões | ≥10 mãos de sessão completa → replay-only nunca |
| `/evolucao` | `cmd_evolucao:311` → `evolution_report:1411` | gráfico | snapshot só grava com sessão completa → replay-only nunca ganha ponto |
| `/torneio` | `cmd_torneio:540` | quadro PNG + leitura por faixa | ≥2 mãos com mesmo `tournament_id` |
| `/relatorio` | `cmd_relatorio:422` | HTML mão a mão (até 150) | ≥8 mãos de torneio |
| `/prova` | `cmd_prova:1528` → `selfcheck` | autoteste | — |
| `/preparar` | `cmd_preparar:445` | briefing + estrutura + range | `get_hands_para_perfil` **ou** `RECENT_HANDS` em memória → replay-only funciona **até o próximo restart** |
| `/simular` | `cmd_simular:1538` | figura + botões + veredito "e se" | mão com ação completa; demo se zero |
| `/treino` | `cmd_treino:835` → `build_drill:3160` | figura + botões; gabarito + streak + filme | `get_all_hands` (**inclui replay**) ou demo |
| `/leitura` | `cmd_leitura:785` → `build_hand_reading:2191` | história sem cartas do vilão + 4 opções | **Sempre `candidatas[0]`** (`:2213`) → mesma mão toda vez |
| `/foco` | `cmd_foco:485` → `foco_reply:1493` | problema atual | **replay-only → "só replay/print… manda o arquivo"** (`:1510`) |
| `/spot` | `cmd_spot:1354` → `spot_reply:2602` | texto + 2 gráficos | — |
| `/range` | `cmd_range:671` | 13×13 (+EV em spot Nash) | — |
| `/vilao` | `cmd_vilao:742` → `villain_report:2247` | perfil do oponente | inclui replay |
| `/dossie` | `cmd_dossie:495` | HTML | exige torneio |
| `/banca` | `cmd_banca:757` | RoR, downswing | — |
| `/ask` | `cmd_ask:638` | RAG | "usado zero vezes" (`processing.py:456`) |
| `/manual` | `cmd_manual:466` | PDF | — |

### Entradas

| Entrada | Rota | O que recebe |
|---|---|---|
| Link de replay | `_route_text:1810` → `replay_link_info` → `_tratar_replay:1765` | PPPoker/Suprema: análise completa + filme + gráficos + botões + rodapé com cota. Outros clubes → `replay_fallback_text` |
| Foto | `on_photo:1174` | legenda com link → replay; legenda com `lobby|estrutura|blinds|níveis|preparar` → lobby; senão visão |
| Arquivo | `on_document:1091` | imagem c/ link → replay; >2 MB rejeita; txt/phh/csv/pdf → `ingest`. CSV de tracker = sem ação street a street (`pipeline.py:93`) |
| Texto colado (HH) | `_route_text:1834` | análise igual ao arquivo; emenda de partes 4096 |
| Texto livre / mão narrada | `_route_text:1864` → `process_followup:1110` | coach com tools. **A mão narrada NÃO é ingerida nem persistida** — sem filme, sem Simular, não vira quiz |
| Voz | `on_voice:1891` → Whisper | mesmo destino do texto |
| Vídeo / YouTube | `on_video:1909`, `on_youtube:2005` | álbum de até 24 frames + transcrição. "Passo ZERO": **nenhuma análise** |

### MANUAL promete × código entrega

**Promete e não entrega (para replay-only):**
- `MANUAL.md:166` "/stats: perfil, leaks e Tilt Detector" — responde "não tenho mãos suas".
- `MANUAL.md:167-169,180` `/estilo`, `/evolucao`, `/foco` — gated em `FONTES_COMPLETAS`.
- `MANUAL.md:152-154` "manda o print do lobby, ele lê a tabela" — só com palavra-chave na **legenda**; docstring `handlers.py:1150` diz "o manual e o /preparar ensinam a legenda"; **nenhum ensina** (grep "legenda" em MANUAL.md: 0).
- `MANUAL.md:43` áudio — depende de `OPENAI_API_KEY`; sem ela, "agora" mente.
- `MANUAL.md:143-151` blockers, PKO, população, defesa do river — existem **só como tool** (`llm.py:1288,1478,1622,1254`); **não há registro de quais tools foram chamadas**. ICM "automático" = `situacao_icm` só avisa que falta premiação; o cálculo real exige `save_tournament_payouts`.
- `_ENVIAR_TXT` (`handlers.py:213-223`) só cita PPPoker, não Suprema nem lobby.

**Entrega e o manual não conta:** vídeo/YouTube, `/preparar <descrição>`, `/evolucao vpip`, `/torneio <código>`, sintaxes de `/banca` e `/spot`, botão 🎈, botões pós-análise, card "Desafiar os amigos" com `?start=card`, streak, mão-demo, plano piloto, limite 2 MB.

## 2. Jornada do aluno novo

`/start` → `WELCOME_SHORT` + 4 botões. "Treinar agora" → mão sintética **em memória** → figura + gabarito determinístico + streak + **convite explícito à primeira mão** + botões. Sem LLM: primeiro valor em <1 min. Bem desenhado e testado (`test_primeiro_minuto_do_aluno.py`).

Primeira análise (replay): "🔗 Achei o link!" → contador → cabeçalho + procedência + selo/placar + rodapé "Análises restantes: 49" + 3 botões → filme → gráficos. **Forte.**

**Onde trava:**
1. "Enviar minhas mãos" não ensina onde fica o Compartilhar. O passo a passo só aparece na mensagem de **falha** (`link_do_clube.py:108-111`).
2. Foto do lobby sem legenda → visão de mão → cota gasta → "print ilegível" (confessado em `handlers.py:1188-1191`).
3. Aluno que "descreve a mão" cai em coaching geral, sem persistência.
4. **Depois de 3 replays testa `/stats`** (1º do menu) e ouve "Ainda não tenho mãos suas" — produto negando o que acabou de aceitar.
5. `/preparar` oscila com o auto-deploy (memória).
6. `WELCOME_SHORT` sempre diz "deixei uma mão de teste" (`:240`), mesmo para veterano.

Não há onboarding guiado nem opt-in ao quiz das 19h.

## 3. Módulos de `analysis/` — órfãos e semi-ligados

Nenhum dos 60 está sem importador. A distinção que importa:

- **A. Ligados a rota determinística** (33): cadeia `/dossie` e `/torneio`, `handreport`, `leaks`, `mental`, `prep`, `lobby`, `plano_de_estudo`, `evolucao`, `selfcheck`, `stats`, `bayes`, `taxonomia`, `hand_figure`, `range_chart`, `bankroll`, `villains`, `handsearch`, `pushfold`, `nash_pushfold`, `open_shove_solver`, `jam_fold_solver`, `allin_engine`, `ranges`, `equity`, `tools`… `lobby.py` está ligado, mas por gatilho de legenda.
- **B. Alcançáveis só via tool do LLM** (uso não medido): `icm` (`llm.py:1663`), `pko` (`:1478`), `blockers` (`:1288`), `range_advantage` (`:1280`), `population` (`:1622`), `rangetracker.read_villain` (`:1512`), `river_solver` (`:1606,1386`), `conferencia` (`:1907`). `side_pots`, `ev_streets`, `postflop_spot` têm resgate determinístico em `guarda_saida.remediar`.
- **C. Só script:** `calibration.py` → `scripts/calibrate_likelihood.py`. Nunca entregue ao aluno.
- **D. Ligados mas inalcançáveis para replay-only:** `leaks, mental, plano_de_estudo, problemas, evolucao, evolution_chart, style_chart, estrutura`.

## 4. Qualidade — o que é medido e o que não é

**Guardas inline:** `guarda_fatos` (dominância com equity real, carta do board, conta sem número), `guarda_voz` (título fixo, bastidor, pós-placar >800, autocorreção), `guarda_termos` (rio/ar/rua/OESD), `guarda_saida` (pediu gráfico e não veio → conta na marra), `llm.py` (selo de emergência, resgate, `_conferir_numeros`, plano C).

**Juiz diário:** forma (selo, placar, equity sem %, pergunta de decisão sem selo, auto-elogio, calques, carta sem naipe, >3500 chars) + nota 0-10 por Haiku (dá pra saber se jogou certo? cada decisão tem número? curta?).

**NÃO é medido:** (1) se o veredito está **certo**; (2) se o aluno **voltou** (há rótulo ativo/esfriando/sumido em `admin.py:319-345`, mas não retenção por coorte); (3) se a análise foi **lida/usada** (eventos `btn_*` existem, funil não); (4) se **fez a jogada certa depois** (só `drill_verdict` com `afericao`); (5) **quais tools** o coach chamou; (6) latência; (7) concordância nos follow-ups; (8) `cota_esgotada` × sumiço.

## 5. Atrito — as 10 mensagens mais prováveis

| # | Mensagem | Gatilho | Diz o que fazer? |
|---|---|---|---|
| 1 | "Ainda não tenho mãos suas. Envie um arquivo" `handlers.py:296` | `/stats` após replays | **Não** — falsa |
| 2 | "só replay/print… manda o arquivo de um torneio inteiro" `processing.py:1510` | `/foco` | pede o impossível |
| 3 | "Preciso de ~10 mãos. Envie uma sessão" `handlers.py:383` | `/estilo` | enganosa |
| 4 | "cada lote vira um ponto" `processing.py:1418` | `/evolucao` | falsa para replay |
| 5 | "mínimo 8 mãos de torneio" `handlers.py:435` | `/relatorio` | inatingível no clube |
| 6 | "link da ClubGG. Abro só PPPoker e Suprema — print ou descreve" `link_do_clube.py:142` | outro clube | **sim**, boa |
| 7 | "print ilegível… me manda em texto" `processing.py:349` | foto ruim | sim |
| 8 | "Opa, me embananei — pergunta de novo" `processing.py:1220` | LLM falhou | só "tente de novo" |
| 9 | "Algo deu errado do meu lado" `handlers.py:2379` | exceção | genérica |
| 10 | "Não consegui transcrever o áudio agora" `handlers.py:1902` | sem chave | "agora" mente |

As de estatística (#1-#5) são o bloco fraco e batem exatamente no público do piloto.

## 6. Dez melhorias (impacto × facilidade)

| # | O quê | Onde | h | Métrica |
|---|---|---|---|---|
| 1 | Ensinar o link no botão "Enviar" + palavra do lobby; mesmo texto no manual | `handlers.py:213-223`, `MANUAL.md` | 1 | % de 1ºs uploads que são replay; `replay_link` ↓ |
| 2 | `/stats`, `/estilo`, `/evolucao`, `/foco` **úteis para replay-only**: "perfil de decisões" (EV por decisão, categorias, custo dos erros, acerto no quiz) separado de "perfil de frequência" | `processing.py:1978,1584,1411,1493`; `handlers.py:295,383` | 8–12 | "não tenho mãos" para quem tem ≥1 → 0 |
| 3 | Logar as tools chamadas por análise | `llm.py:2241-2258` | 1–2 | distribuição de tools/30d |
| 4 | Confirmar/instalar crons (juiz, anomalias, daily_usage) | crontab; `OPERATIONS.md:69-78` | 0,5 | evento diário |
| 5 | Lobby sem legenda: 2 botões "É o lobby / É a mesa" antes de "ilegível" | `handlers.py:1174-1214` | 3–4 | `lobby_lido` ↑ |
| 6 | Mão narrada vira análise de verdade (persiste, filme, quiz) | `_route_text:1860`, `pipeline.py:99-126` | 4–6 | mãos com `source_format` narração |
| 7 | Juiz com métricas de resultado (follow-up em 24h, volta em 7d, acerto por categoria) | `output_judge.py`, `admin.py` | 4–6 | linhas no relatório |
| 8 | `/leitura` rotaciona | `processing.py:2213` | 1 | `hand_id` distintos |
| 9 | Botão "📤 Mandar outra mão"; `/start` condicional; opt-in ao quiz | `handlers.py:2061-2075,240` | 1–2 | 2º upload em 48h |
| 10 | Vídeo: fechar o passo 1 ou restringir ao admin | `handlers.py:1909-2044` | 1 / 10+ | — |

**Resumo:** o núcleo (link → análise → filme → conversa → treino) está ligado, testado e é bom. O que está quebrado para o piloto é o **segundo andar**: todo comando de perfil exige um arquivo que o aluno de clube não tem, e o produto responde como se ele nunca tivesse mandado nada.
