# KKNuths — Handoff / Operação (KB)
Atualizado: 2026-07-04 · escopo: tudo implementado até aqui

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
3. **Supabase**: users, uploads, hands (canonical jsonb), hand_analysis (+embedding 1536), tournaments, player_stats, usage_events, bot_events (log de TUDO), pending_drills; função RAG match_hand_analysis; RLS ligado (acesso só service role)

## Funcionalidades no ar
- **Ingestão (7 modos)**: .txt PokerStars/GGPoker/Winamax/PartyPoker/888 · texto colado · CSV de tracker (HM/PT) · print/foto (visão lê ação completa) · PDF · voz (Whisper) · fallback por IA p/ formato desconhecido (com heurística anti-alucinação)
- **Análise**: Claude (Opus) com 12 tools determinísticas — equity MC, equity vs range, pot odds/EV/SPR/blefe, ICM Malmuth-Harville, bubble factor, **Nash push/fold HU calculado** (fictitious play, dados versionados), **solver de river CFR+**, charts pré-flop, population_tendencies (exploit do field), push_fold aproximado p/ posições não-HU
- **Torneio**: mãos-chave (all-ins + swings) + "história do torneio"
- **Conversa**: follow-up texto/áudio com contexto + releitura do print; coach geral (qualquer pergunta de poker, personalizada pelo perfil); memória recuperada do banco pós-restart
- **Treino**: /treino (drill persistido em pending_drills), /simular (replay jogável + veredito "e se"), quiz diário 19h (cron), /range (grade 13×13: opens e Nash com frequências)
- **Gráficos automáticos**: quando o coach usa um range, o PNG 13×13 vai junto (máx 2)
- **Perfil**: /stats cumulativo (hero de cada mão); /ask (RAG com embeddings OpenAI 1536)
- **Automação**: relatório semanal dom 18h (cron), aviso de deploy no TG do admin
- **Cota**: 100 análises/mês no free (env FREE_MONTHLY_ANALYSES); upload máx 2MB; 5 mãos coacheadas/torneio; pro/premium (users.plan manual) = ilimitado
- **Billing Stripe**: código pronto e DESLIGADO (decisão de produto); scripts/setup_stripe.py quando ligar

## Deploy (auto)
- Cron a cada 2 min: `deploy/auto_update.sh` → fetch do branch; commit novo → reset + copia p/ /opt/poker-bot → `vps_deploy.sh` (pip + **89 testes como portão** + pm2 restart) → aviso "🔄" no TG do admin; falha → "⚠️" e bot antigo segue no ar
- Compara com último deploy **bem-sucedido** (`/tmp/poker-autoupdate.ok`)
- Manual (se precisar): `git -C /opt/kknuths fetch && git -C /opt/kknuths reset --hard origin/<branch> && cp -r /opt/kknuths/backend/. /opt/poker-bot/ && bash /opt/poker-bot/deploy/vps_deploy.sh`
- Logs: `/var/log/poker-autodeploy.log`, `pm2 logs poker-bot`

## Diagnóstico (runbook)
- **Saúde geral**: `cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/diagnose.py` (testa .env, Telegram, Anthropic+modelos, OpenAI, Supabase)
- **Bot API na mão**: `scripts/tg.py me|chat <id>|send <id> <texto>` (NUNCA getUpdates — conflita com polling)
- **O que os usuários fazem**: tabela `bot_events` (start c/ ref do convite, upload, upload_failed c/ trecho+raw_path, ask, followup, simular, range, voice...)
- **Upload que falhou**: evento upload_failed traz trecho (500 chars) e caminho do arquivo bruto no Storage → reprocessável sem reenvio
- **Enviar TG sem o VPS**: Supabase pg_net → net.http_post na Bot API (usado p/ avisos)

## Crons instalados (crontab root)
- `*/2 * * * *` auto_update.sh (deploy)
- `0 19 * * *` scripts/daily_quiz.py (quiz do dia)
- `0 18 * * 0` scripts/weekly_report.py (resumo semanal + leak)

## Gotchas / lições (sangue real)
- **Segredos por chat viram `•••`** ao copiar (máscara do cliente) — transferir SEMPRE por arquivo (scp) ou printf via ssh; foi a causa do .env corrompido
- **PowerShell**: separador é `;` (não `&`); here-string multi-linha quebra — preferir comandos de uma linha
- **Teste que depende de LLM = deploy travado** (aconteceu): todo teste deve ser determinístico; portão segurou produção intacta
- **`git add -f` quase vazou o .env** — push protection do GitHub salvou; nunca forçar add
- **Rede das salas**: nunca conectar na conta do usuário (ToS/RTA) — só análise pós-sessão
- **Disco do VPS lota** (logs/pip) — `pm2 flush`, `journalctl --vacuum-size=200M`, `apt-get clean` liberam rápido
- **Vision/LLM caem** → produto degrada p/ resumo determinístico, nunca quebra

## Pendências
1. **Deploy key no GitHub** (colar `/root/.ssh/kknuths_deploy.pub` em Settings→Deploy keys) e então **tornar o repo privado** — remote atual voltou p/ HTTPS até isso
2. **Rotacionar chaves** (Anthropic, OpenAI, BotFather, Supabase service) — passaram por chat
3. **1º usuário beta** (tg 6104620007, veio do link ?start=beta): arquivo rejeitado 2×; avisado pelo bot p/ reenviar — acompanhar bot_events
4. Fase 0 do business plan: 20–50 usuários, medir retenção W4 ≥35% antes de tráfego
5. Backlog priorizado: auto-sync (watcher de pasta), landing page PT (SEO vs Jenova), streaks, bankroll tracker, benchmarks do field, espanhol

## Documentos irmãos
- `PLANO.md` (produto) · `BUSINESS_PLAN.md` (negócio) · `MANUAL.md` (usuário, comercial) · `backend/README.md` (dev) · `backend/deploy/README.md` (deploy)
