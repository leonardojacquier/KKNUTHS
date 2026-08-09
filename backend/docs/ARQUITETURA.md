# Arquitetura — mapa do que existe

Atualizado: 2026-08-09 · 99 módulos em `app/`, 74 arquivos de teste, 971 testes.

Este documento é o mapa. O **porquê** das decisões estatísticas está em
[`METODO.md`](METODO.md); o runbook de operação está em `../../OPERATIONS.md`.

---

## A regra que organiza tudo

> **Regra é pedido; conferência é garantia.**

O LLM faz o **julgamento** — o que dizer, em que ordem, com que tom. Ele nunca
faz a **conta**. Toda afirmação numérica sai de uma função determinística em
`app/analysis/`, e toda saída do modelo passa por guardas que conferem o texto
contra os fatos da mão antes de chegar ao aluno.

O corolário prático: pedir no prompt não é garantir. Onde a garantia importa,
existe um teste que a cobra e um guarda que a corrige em tempo de execução.

```
     upload                                                    aluno
        │                                                        ▲
        ▼                                                        │
  ┌───────────┐    ┌────────────┐    ┌──────────┐    ┌───────────────────┐
  │ parsers/  │───▶│ CanonicalHand│──▶│ analysis/ │──▶│ agent/llm.py      │
  │ 10 salas  │    │ (pydantic)  │    │ 12 tools  │   │ (julgamento)      │
  └───────────┘    └────────────┘    └──────────┘    └───────────────────┘
                                          │                     │
                                          │  as CONTAS          │ o TEXTO
                                          │                     ▼
                                          │          ┌────────────────────┐
                                          └─────────▶│ bot/guarda_fatos   │
                                                     │ bot/guarda_saida   │
                                                     │ agent/termos       │
                                                     └────────────────────┘
```

---

## As quatro camadas

### 1. `app/parsers/` — de arquivo bruto a `CanonicalHand`

Dez formatos, um modelo de saída. `registry.py` roteia o texto para o parser
certo; `base.py` é a interface comum.

| Módulo | Cobre |
|---|---|
| `pokerstars.py` | PokerStars (torneio + cash) |
| `ggpoker.py` | GGPoker |
| `winamax.py` | Winamax |
| `dealing_family.py` | PartyPoker e 888poker |
| `csv_tracker.py` | export de Hold'em Manager / PokerTracker |
| `phh.py` | PHH — padrão aberto TOML |
| `pppoker_replay.py` | replay de clube PPPoker |
| `suprema_replay.py` | replay de clube Suprema |

Fora daqui: print/foto (visão), PDF, voz (Whisper) e o fallback por IA para
formato desconhecido, todos em `app/ingestion/pipeline.py`.

**A distinção que atravessa o produto inteiro:** um `.txt` de sala é uma
*sessão inteira*; um replay de clube é uma *mão escolhida pelo aluno*. Os dois
servem para analisar aquela mão. Só o primeiro serve para contar frequência.
Ver [`METODO.md` §1](METODO.md).

### 2. `app/analysis/` — as contas

47 módulos, todos funções puras sobre `CanonicalHand`. Nenhum conhece o
Telegram, e a maioria não conhece o banco.

**Motores de decisão**
| Módulo | O que resolve |
|---|---|
| `equity.py` | equity por Monte Carlo (usa `treys` quando disponível) |
| `multiway_equity.py` | a chance de bater **todos**, não um de cada vez |
| `allin_engine.py` | motor único de EV para qualquer all-in pré-flop |
| `ev_streets.py` | EV de cada decisão, rua a rua, em pote multiway sem all-in |
| `icm.py` | ICM Malmuth-Harville |
| `nash_pushfold.py` | equilíbrio push/fold HU calculado (fictitious play) |
| `open_shove_solver.py` | open-shove de mesa cheia, EV por mão |
| `jam_fold_solver.py` | jam/fold HU em runtime, com ajuste de ICM |
| `river_solver.py` | CFR+ range-vs-range multi-street |
| `side_pots.py` | pote principal e paralelos |
| `pko.py` | matemática de bounty progressivo |

**Leitura e exploração**
`ranges.py`, `range_advantage.py`, `rangetracker.py` (leitura bayesiana do
range do vilão), `blockers.py`, `villains.py` (exploit por vilão),
`population.py` (tendências do field), `calibration.py` (likelihoods
calibradas por showdown).

**Diagnóstico do aluno** — a espinha do produto atual:
| Módulo | Papel |
|---|---|
| `stats.py` | estatísticas de estilo **e o portão de amostra** |
| `bayes.py` | encolhimento bayesiano (`shrunk_rate`) |
| `taxonomia.py` | conta erro por código, em vez de opinar |
| `estrategia_torneio.py` | onde o EV foi embora, por faixa de stack |
| `problemas.py` | ciclo de problema: diagnóstico → intervenção → alta |
| `evolucao.py` | ele melhorou? a medição que se recusa a mentir |
| `plano_de_estudo.py` | a cola entre os quatro acima e o banco |
| `leaks.py` | leaks convertidos em dinheiro |
| `mental.py` | vazamentos mentais (Kahneman) em números |
| `selfcheck.py` | a ferramenta auditando a si mesma nas mãos do aluno |
| `procedencia.py` | de onde veio cada dado e com que certeza |

**Saída visual** — `range_chart.py` (13×13), `hand_figure.py` (a mesa como
imagem), `evolution_chart.py`, `style_chart.py`, `tournament_board.py`,
`handreport.py` (dossiê HTML mão a mão), `branding.py`.

### 3. `app/agent/` — o julgamento

`llm.py` (2.730 linhas) carrega o prompt e as 12 tools determinísticas.
`analyzer.py` orquestra. `memoria.py` injeta o que o coach já viu.
`custo.py` mede o gasto em dólar por chamada. `saude.py` separa "me embananei"
de "a conta acabou". `termos.py` é o corretor determinístico de terminologia
que roda em **toda** saída. `speech.py` (Whisper) e `embeddings.py` (RAG).

### 4. `app/bot/` — o que o aluno vê

`handlers.py` é casca async fina; o trabalho pesado vai para
`processing.py` via `to_thread` para não travar o loop de polling.

**Os guardas**, que rodam depois do modelo e antes do aluno:
- `guarda_fatos.py` — a análise afirma coisa que não é verdade? KK não perde
  para QQ; "a conta" tem que ter conta. **Corrige**, não só registra.
- `guarda_saida.py` — a resposta responde o que foi pedido?
- `licao_qualidade.py` — portão da lição destilada, antes de ela falar com
  todos os alunos de uma vez.

Também aqui: `memoria_do_processo.py` (memória com teto LRU),
`repeticao.py` (repetição espaçada guiada por erro), `menus.py`,
`progresso.py`, `notify.py`, `leitura_da_mao.py`, `licao_envio.py`.

---

## Comandos no ar

| Comando | O que faz |
|---|---|
| `/start` | menu inicial |
| `/stats` | perfil de estilo — **só com amostra que permita** |
| `/estilo` | você vs os arquétipos dos grandes |
| `/evolucao` | linha do tempo com gráficos |
| `/foco` | **no que você está trabalhando** — o ciclo de problema |
| `/torneio` | quadro do último torneio |
| `/relatorio` | relatório mão a mão (HTML) |
| `/preparar` | preparação pré-torneio |
| `/spot` | EV de all-in, equilíbrio do spot |
| `/prova` | auditar a ferramenta nas suas próprias mãos |
| `/simular` | rejogue uma mão sua |
| `/treino` | drill de um spot seu |
| `/leitura` | adivinhe a mão do vilão |
| `/vilao` | dossiê de um oponente |
| `/banca` | risco de ruína e downswing |
| `/range` | grades 13×13 |
| `/ask` | busca no seu histórico (RAG) |
| `/licoes` | lições destiladas (dono) |
| `/manual`, `/plano`, `/quem`, `/termo`, `/planode` | apoio |

---

## Banco (Supabase / Postgres + pgvector)

21 tabelas. RLS ligado — acesso só por service role.

**Núcleo**: `users`, `user_meta`, `uploads`, `hands` (canonical jsonb),
`hand_analysis` (+ embedding 1536), `tournaments`.

**Diagnóstico**: `player_stats` (com a coluna `publicavel` — ver
[`METODO.md` §1](METODO.md)), `player_stats_history`, `problemas`,
`problema_evidencia`, `problema_medicao`.

**Conteúdo e operação**: `licoes`, `conhecimento`, `glossario`,
`player_notes`, `pending_drills`, `pending_sims`, `conversation_state`,
`bot_events` (log de tudo), `usage_events`, `subscriptions`.

Função RAG: `match_hand_analysis`.

---

## Testes como memória

74 arquivos, 971 testes, todos determinísticos — **teste que depende de LLM já
travou o deploy uma vez**, e o portão segurou produção intacta.

Os nomes dos arquivos são a lista de erros que o projeto já cometeu, e é assim
de propósito: `test_resultadismo_nao_e_ev_da_decisao`,
`test_amostra_curada_nao_vira_frequencia`, `test_drill_nao_condena_fold_certo`,
`test_prompt_nao_ensina_o_que_proibe`, `test_deploy_testa_antes_de_copiar`,
`test_corretor_nao_estraga_portugues`, `test_medir_evolucao_sem_mentir`.

Três testes guardam o processo, não o produto:
- `test_processing_nao_incha.py` — teto de linhas em `processing.py`. Já
  disparou duas vezes e nas duas estava certo; forçou as extrações de
  `stats.py` e `repeticao.py`.
- `test_deploy_testa_antes_de_copiar.py` — a ordem do deploy é o bug, e ordem
  se lê. Inclui o caminho do runbook.
- `test_prompt_nao_briga_consigo.py` — o prompt não pode se contradizer.
