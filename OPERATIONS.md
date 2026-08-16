# KKNuths — Handoff / Operação (KB)
Atualizado: 2026-08-15 · escopo: tudo implementado até aqui

> **Mapa do código**: `backend/docs/ARQUITETURA.md`
> **O que a ferramenta afirma e o que se recusa a afirmar**: `backend/docs/METODO.md`

## Acesso
- **Bot**: @KKNUts_BOT (Telegram) · convite: t.me/KKNUts_BOT?start=<origem> (origem fica em bot_events)
- **Servidor**: Hostinger srv1555380 — `ssh root@187.127.13.220` (mesmo VPS do GNH/TitanCalc)
- **App**: `/opt/poker-bot` (venv próprio) · clone-fonte: `/opt/kknuths` (repo GitHub)
- **pm2**: `poker-bot` (bot polling) e `poker-web` (uvicorn 127.0.0.1:8014 — portal /admin)
- **Repo**: github.com/leonardojacquier/KKNUTHS · branch `claude/poker-analysis-telegram-bot-mfuyhf` · pasta `backend/`
- **Banco**: Supabase projeto `kknuths-poker` (ref htvjviovcfvtpgeloekn, sa-east-1) — Postgres + pgvector + Storage (bucket privado `uploads`)
- **Portal de gestão**: túnel `ssh -L 8014:127.0.0.1:8014 root@187.127.13.220` → http://localhost:8014/admin?key=<ADMIN_TOKEN do .env>
- **Segredos**: TODOS em `/opt/poker-bot/.env` (nunca no git; push protection ativo). Chaves: Telegram, Anthropic, OpenAI, Supabase URL+service_role, ADMIN_TOKEN, TELEGRAM_ADMIN_CHAT_ID=6452742024 (Leo)

## Arquitetura (3 partes)
1. **Bot Telegram** (pm2 `poker-bot`, long-polling): handlers finos async; trabalho pesado em `app/bot/processing.py` via to_thread (não bloqueia o loop)
2. **API/Portal** (pm2 `poker-web`, porta 8014): `/health`, `/admin` (KPIs, eventos, perfis), webhooks Telegram/Stripe (esqueleto)
3. **Supabase**: 21 tabelas — users, user_meta, uploads, hands (canonical jsonb), hand_analysis (+embedding 1536), tournaments, player_stats (+`publicavel`), player_stats_history, problemas/problema_evidencia/problema_medicao, licoes, conhecimento, glossario, player_notes, pending_drills, pending_sims, conversation_state, usage_events, bot_events (log de TUDO), subscriptions; função RAG match_hand_analysis; RLS ligado (acesso só service role)

## Funcionalidades no ar
- **Ingestão (7 modos)**: .txt PokerStars/GGPoker/Winamax/PartyPoker/888 · texto colado · CSV de tracker (HM/PT) · print/foto (visão lê ação completa) · PDF · voz (Whisper) · fallback por IA p/ formato desconhecido (com heurística anti-alucinação)
- **Análise**: Claude (Opus) com 12 tools determinísticas — equity MC, equity vs range, pot odds/EV/SPR/blefe, ICM Malmuth-Harville, bubble factor, **Nash push/fold HU calculado** (fictitious play, dados versionados), **solver de river CFR+**, charts pré-flop, population_tendencies (exploit do field), push_fold aproximado p/ posições não-HU
- **Torneio**: mãos-chave (all-ins + swings) + "história do torneio"
- **Conversa**: follow-up texto/áudio com contexto + releitura do print; coach geral (qualquer pergunta de poker, personalizada pelo perfil); memória recuperada do banco pós-restart
- **Treino**: /treino (drill persistido em pending_drills), /simular (replay jogável + veredito "e se"), quiz diário 19h (cron), /range (grade 13×13: opens e Nash com frequências)
- **Gráficos automáticos**: quando o coach usa um range, o PNG 13×13 vai junto (máx 2)
- **Perfil**: /stats cumulativo (hero de cada mão); /ask (RAG com embeddings OpenAI 1536)
- **Dossiê do vilão (ago/2026)**: `/torneio` (por código ou lista), `/vilao`, `/dossie <nome> [N]` → HTML de estudo com: figura da mão CENTRADA NO VILÃO (cartas dele quando houve showdown, "cartas não vistas" quando não), mãos mostradas classificadas pela LINHA, linhas escuras narradas pelos números delas (check-raise, stack comprometido, textura), padrões entre mãos ("3º overbet no river", sizing vs mediana DELE), cartas prováveis por CONTAGEM DE COMBOS (top-PFR% medido, suposição escrita na frase), dois retratos (showdown × linha) com a divergência, defesa do aluno por MDF. Determinístico + 1 síntese por IA conferida.
- **Vídeo (passo zero, 12/08)**: vídeo direto (≤20MB, limite da API de bots) ou LINK do YouTube (sem limite; servidor baixa com yt-dlp, teto 30min) → ffmpeg extrai 1 quadro/s, comparador determinístico mantém só as telas que MUDARAM, e a narração é transcrita pelo Whisper (custo impresso na resposta). É PROVA para o dono conferir — a visão sobre os frames ainda NÃO foi ligada.
- **Automação**: relatório semanal dom 18h (cron), aviso de deploy no TG do admin
- **Cota**: 100 análises/mês no free (env FREE_MONTHLY_ANALYSES); upload máx 2MB; 5 mãos coacheadas/torneio; pro/premium (users.plan manual) = ilimitado
- **Billing Stripe**: código pronto e DESLIGADO (decisão de produto); scripts/setup_stripe.py quando ligar

## Diagnóstico do aluno (camada nova — jul/ago 2026)
- **Portão de amostra**: só fonte de sessão inteira (`txt/text/csv/phh/pdf`) vira frequência; replay de clube e print seguem valendo para analisar a mão. Coluna `player_stats.publicavel` cobrada na ESCRITA e na LEITURA. Rótulo de estilo só com 100 mãos; taxa só com 30 e sempre com ±pp. **Detalhe e porquê em `backend/docs/METODO.md`.**
- **Taxonomia de erro** (`app/analysis/taxonomia.py`): 6 códigos com oportunidade/escorregada/custo computáveis; decisão pelo LIMITE INFERIOR do IC, IC99 acima de 10 códigos testados
- **Estratégia por faixa de stack** (`estrategia_torneio.py`): deep >40bb · padrão 25-40 · re-shove 15-25 · curto 8-15 · crítico <8; corte por ANTE, não por "etapa"; recusa afirmar direção com menos de 5 chances do outro lado
- **Ciclo de problema** (`problemas.py` + `plano_de_estudo.py`, comando `/foco`): 6 estados, 5 portões, máx 1 ativo, pré-requisito na frente do sintoma, critério de alta PRÉ-REGISTRADO na mesma gravação da abertura
- **Medição de evolução** (`evolucao.py`): 3 vereditos com `inconclusivo` obrigatório; linha de base nunca é a janela que diagnosticou; só mão real dá alta (quiz não); aferição 1-em-5 sem `leak_boost`

## Deploy (auto)
- Cron a cada 2 min: `deploy/auto_update.sh` → fetch do branch; commit novo → **pytest no CLONE** (portão) → só então rsync p/ /opt/poker-bot → `vps_deploy.sh` + pm2 restart → aviso "🔄" no TG do admin; falha → "⛔/⚠️" e bot antigo segue no ar
- **1.377 testes como portão** (todos determinísticos)
- O script re-executa de uma CÓPIA em /tmp: ele se sobrescreve no meio da própria execução, e bash lê por offset de byte (ver `test_deploy_testa_antes_de_copiar.py`)
- Snapshot em `/tmp/poker-bot-anterior` antes de copiar; se passar nos testes e não subir, restaura sozinho — e reinicia **bot e web** (antes só o bot: o disco voltava e o `poker-web` seguia de memória com o código reprovado)
- O portão de subida confere `pm2 describe poker-bot` **e** `curl 127.0.0.1:8014/health` (antes só o bot: deploy que derrubava o site anunciava sucesso)
- Compara com último deploy **bem-sucedido** (`/tmp/poker-autoupdate.ok`)
- Manual (se precisar): `git -C /opt/kknuths fetch && git -C /opt/kknuths reset --hard origin/<branch> && cp -r /opt/kknuths/backend/. /opt/poker-bot/ && bash /opt/poker-bot/deploy/vps_deploy.sh`
- Logs: `/var/log/poker-autodeploy.log`, `pm2 logs poker-bot`

## Diagnóstico (runbook)
- **SÃO DOIS PROCESSOS**: `poker-bot` (bot Telegram, polling) e `poker-web` (uvicorn 127.0.0.1:8014, site + portal, atrás do Caddy). Bot no ar não diz nada sobre o site — foi assim que o site caiu em 09/08 com tudo verde
- **Site fora, uma colada**:
  ```
  pm2 status; curl -s -o /dev/null -w 'local %{http_code}\n' http://127.0.0.1:8014/health
  curl -s -o /dev/null -w 'publico %{http_code}\n' https://poker.vortex369.com.br/health
  pm2 logs poker-web --lines 40 --nostream; df -h /
  ```
  local ≠ 200 → app (`pm2 restart poker-web`); local 200 e público ≠ 200 → Caddy/DNS/certificado, **não** é o app
- **Sonda horária** (`scripts/sonda_recebimento.py`) cobre os dois desde 09/08: manda 🚨 *SITE FORA DO AR* com o lado que caiu; "não checado" nunca alarma
- **Saúde geral**: `cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/diagnose.py` (testa .env, Telegram, Anthropic+modelos, OpenAI, Supabase)
- **Bot API na mão**: `scripts/tg.py me|chat <id>|send <id> <texto>` (NUNCA getUpdates — conflita com polling)
- **O que os usuários fazem**: tabela `bot_events` (start c/ ref do convite, upload, upload_failed c/ trecho+raw_path, ask, followup, simular, range, voice...)
- **Upload que falhou**: evento upload_failed traz trecho (500 chars) e caminho do arquivo bruto no Storage → reprocessável sem reenvio
- **Enviar TG sem o VPS**: Supabase pg_net → net.http_post na Bot API (usado p/ avisos)

## Crons instalados (crontab root)
- `*/2 * * * *` auto_update.sh (deploy)
- `0 19 * * *` scripts/daily_quiz.py (quiz do dia)
- `0 18 * * 0` scripts/weekly_report.py (resumo semanal + leak)

Outros scripts trazem um cron SUGERIDO na própria docstring e podem ou não
estar instalados — conferir com `crontab -l` no VPS, não confiar nesta lista:
`anomalias.py` (21h), `backup_db.py` (4h), `licao_do_dia.py` (14h),
`destilar_licoes.py` (9h15), `linguista.py` (7h40), `output_judge.py` (8h),
`nightly_coherence.py` (6h), `daily_usage.py` (23h), `destilar_conhecimento.py`.

**Caminho no VPS é `/opt/poker-bot`.** Todo comando de docstring usa esse
caminho e há teste cobrando (`test_o_caminho_do_runbook_e_o_caminho_real_do_deploy`),
porque nove scripts já disseram `/app/backend`, pasta que nunca existiu — e a
falha resultante (`./venv/bin/python: No such file or directory`) parece venv
quebrado e manda a investigação para o lado errado.

## Gotchas / lições (sangue real)
- **Segredos por chat viram `•••`** ao copiar (máscara do cliente) — transferir SEMPRE por arquivo (scp) ou printf via ssh; foi a causa do .env corrompido
- **PowerShell**: separador é `;` (não `&`); here-string multi-linha quebra — preferir comandos de uma linha
- **Teste que depende de LLM = deploy travado** (aconteceu): todo teste deve ser determinístico; portão segurou produção intacta
- **`git add -f` quase vazou o .env** — push protection do GitHub salvou; nunca forçar add
- **Rede das salas**: nunca conectar na conta do usuário (ToS/RTA) — só análise pós-sessão
- **Disco do VPS lota** (logs/pip) — `pm2 flush`, `journalctl --vacuum-size=200M`, `apt-get clean` liberam rápido
- **Vision/LLM caem** → produto degrada p/ resumo determinístico, nunca quebra
- **Evento de SAÍDA não é atividade do aluno**: `daily_quiz_sent`, `licao_recebida`, `convite_primeira_mao` e `reanalise_enviada` têm telegram_id de gente mas somos NÓS falando. Contá-los em "último acesso" faz todo aluno parecer ativo — o portal exclui em `_SO_RECEBEU`, e toda consulta manual ao `bot_events` tem que excluir também, senão dá churn zero
- **Cron tem `telegram_id <= 0`** — filtro por ID em vez de por nome, para que o cron escrito amanhã já nasça fora do feed
- **Consertar a conta não basta**: a linha errada continua no banco. Todo conserto de cálculo precisa de (a) limpeza da linha envenenada e (b) portão na LEITURA

## Situação da base (15/08/2026, medida)
- 14 usuários · 1.418 mãos · 227 uploads · 406 análises · 140 notas de aluno · 35 lições · 36 itens de conhecimento · 2.904 eventos
- **9 ativos na semana** (Leo + 8): Alvino 17 eventos, Paulo 14 (8 uploads), alvgomes19 12, Ricardo 6, ttbahr 5, Luiz 4, Raphael 3, Sivio 2
- Pico às sextas/sábados (dia de torneio); a semana esfria de segunda a quinta
- **`/dossie` tem 9 usos e TODOS são do dono** — nenhum aluno descobriu a funcionalidade mais forte do mês
- Nota do juiz da saída: 5.8 (14/08) → **6.3 (15/08)**, média 7d 6.2. A/B por modelo nos dias com dado: sonnet 7.7 (n=12) × opus 6.0 (n=13)

## Situação anterior (09/08/2026, para comparar)
- 11 usuários · 660 mãos · 517 de fonte completa · 6 usuários já mandaram mão · 389 análises · 29 lições · 18 itens de conhecimento · 2.476 eventos
- **Churn real** (excluindo eventos de saída): 6 ativos · 1 esfriando · **4 sumidos**
- O mais caro deles: tg `6104620007`, **159 mãos**, sem agir há **21 dias** — é o aluno com maior investimento feito e nenhum retorno
- **5 dos 11 nunca mandaram uma mão** — o funil trava no primeiro upload, não no engajamento
- `problemas` está em 0: o ciclo (`/foco`) acabou de subir e ninguém abriu ainda

## Onde paramos (15/08/2026) — esperando o DONO
1. **Testar o vídeo**: colar o link do react do YouTube no bot (ou mandar vídeo ≤20MB). Volta: telas distintas + narração transcrita + custo impresso. **A pergunta a responder: a mão que o youtuber narra está inteira na transcrição?** Com o "sim", a fase 2 é um modelo de TEXTO extrair cada mão narrada (~US$0,10/react) — visão só confere os frames.
2. **Publicar o post do dossiê** (`scratchpad/post/`, 1080×1350 + legenda pronta) — a feature mais forte do mês está invisível para os alunos.
3. **Ler o juiz das 8h de 16/08** — é o 1º dia com Sonnet default + conferência de números. Métricas a olhar: nota do dia, eventos `numeros_corrigidos`/`numeros_nao_conferidos` no banco, e a queda de custo (~5x no caminho principal).
4. Servidor local da Bot API (`telegram-bot-api`) se aparecer vídeo grande fora do YouTube — sobe o teto de 20MB para 2GB. Precisa de `api_id`/`api_hash` de my.telegram.org (NUNCA por chat — arquivo/ssh).
5. **Voz do coach**: implementada e testada na branch `claude/voz-do-coach`, **NÃO deployada**. O merge espera a leitura do juiz de 16/08 (item 3 acima) para não misturar troca de modelo com troca de prompt na mesma nota — ver `backend/docs/superpowers/specs/2026-08-15-voz-do-coach-design.md` §6. Falta rodar o comparador lado a lado no VPS (exige `ANTHROPIC_API_KEY`, que este ambiente de verificação não tem):
   ```
   cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/comparar_voz.py --n 8 --saida /tmp/voz.md
   ```
   A leitura de `/tmp/voz.md` é a decisão do dono; a linha de base medida (antes) está na spec, §9. O arquivo agora abre com um cabeçalho dizendo o que o "depois" refaz (perfil do aluno + guarda da voz) e a variável que sobra (o perfil é o de HOJE) — leia isso antes de creditar diferença ao prompt.

   **Depois da onda de correção da revisão final (spec §10), a linha 🗣 do juiz mudou**: passou a ter DUAS leituras, e elas não são intercambiáveis. "O que o MODELO escreveu" vem dos eventos `voz_corrigida`/`voz_medida` (medidos ANTES da limpeza — é o único número que diz se o prompt novo funcionou). "O que o ALUNO recebeu" vem do texto gravado, DEPOIS da limpeza, e só de análise de mão com placar — torneio e decisão única saem da conta. A referência impressa é **678** chars, não 740: o 740 saiu de denominador contaminado (spec §9).

   **Como ler as duas linhas depois dos resíduos (spec §11):**
   - 🗣 **mede o PROMPT.** Vem com denominador e com as QUATRO populações separadas: `X de Y análises de mão com placar com algo a apontar = Z%` é comparável à base da §9 (título fixo 48%, bastidor 34%). O que aparece com `+` depois dela — `em conversa`, `em torneio`, `análise sem placar` — é população à parte e NÃO entra na taxa; as quatro somadas dão o total de eventos do dia. Os contadores por defeito na mesma linha continuam sendo NUMERADOR de todas somadas — não os leia como taxa. **A taxa não pode passar de 100%**: se passar, a linha imprime `⚠️ acima da base` e a leitura está torta (análise com evento gravado e sem linha em `hand_analysis`) — foi exatamente o defeito da 1ª versão dela, que somava torneio e análise sem placar num numerador cujo denominador não os continha e chegou a imprimir 50% num dia em que a verdade era 0%.
   - 🧹 **mede o GUARDA**, e voltou a mostrar `título fixo · bastidor entregue · bloco longo` do lado do aluno. **`bastidor entregue` não tende a zero de propósito**: o guarda recusa apagar a frase de bastidor quando ela carrega a única conta (spec §10 I1 + §11 R1). Subir aí pode ser o guarda acertando — quem diz se o prompt melhorou é a linha 🗣. Só `título fixo` ainda tende a zero.

## Pendências
1. **Deploy key no GitHub** (colar `/root/.ssh/kknuths_deploy.pub` em Settings→Deploy keys) e então **tornar o repo privado** — remote atual voltou p/ HTTPS até isso
2. **Rotacionar chaves** (Anthropic, OpenAI, BotFather, Supabase service) — passaram por chat
3. **Reativar os 4 sumidos**, começando pelo de 159 mãos — é a informação mais cara da base
4. **Primeiro upload é o gargalo** (5 de 11 nunca mandaram mão), não a retenção depois
5. Fase 0 do business plan: 20–50 usuários, medir retenção W4 ≥35% antes de tráfego
6. **Relatório de inversão** (tight no early + loose perto do dinheiro) — depende de mãos SEM ante, e todas as 517 completas hoje têm ante
7. `dead_opener` em `allin_engine.py:203/261` — cheiro de código não resolvido; erros provavelmente se cancelam dentro de um blind, direção não provada
8. Backlog: auto-sync (watcher de pasta), landing page PT (SEO vs Jenova), streaks, bankroll tracker, benchmarks do field, espanhol

## Decisões de modelo (15/08/2026)
- `ANALYSIS_MODEL` default = **claude-sonnet-5** (era opus-4-8). Motivo: A/B do juiz (7.7 × 6.0) + custo ~5x menor + nota do dia 6.3 abaixo da meta 7 combinada com o dono. **Reverter = 1 linha no .env** (`ANALYSIS_MODEL=claude-opus-4-8`) + pm2 restart, sem deploy.
- **Conferência de números na análise** (`app/analysis/conferencia.py`): todo número citado precisa de lastro no contexto da mão ou no resultado de ferramenta. Órfão → 1 reescrita corretiva; persiste → entrega + evento `numeros_nao_conferidos`. Nunca degrada abaixo do que já ia sair; análise limpa não gasta chamada extra.
- Três defeitos de MONTAGEM (não de modelo) corrigidos em 15/08, cada um com teste: selo ancorado por LINHA (não por bloco); resgate da conclusão quando o modelo só narra bastidor; fallback determinístico com selo/naipe em vez de stub (`VOCÊ (Tc Kh) em ?` chegou a aluno).

## Regras de comunicação com o Leo (registradas a pedido dele)
- **PROIBIDA a palavra "honesto/honesta/honestidade" (e variações) nas respostas ao Leo** — 15/08/2026, pedido dele, sem exceção. Diga o fato direto, sem se autoqualificar. (Vale para o chat com ele; o código e docs internos não mudam.)

## Documentos irmãos
- `backend/docs/ARQUITETURA.md` (mapa do código) · `backend/docs/METODO.md` (o que a ferramenta afirma e o que se recusa a afirmar)
- `PLANO.md` (produto) · `BUSINESS_PLAN.md` (negócio) · `MANUAL.md` (usuário, comercial) · `backend/README.md` (dev) · `backend/deploy/README.md` (deploy)
