# Poker Bot — Deploy no VPS GNH (padrão da casa)

- Servidor: Hostinger srv1555380 — `ssh root@187.127.13.220` (chave; sem senha).
- Terminal web (alternativa): https://cam.hostingervps.com/2548/
- Processo: **pm2** (`poker-bot`), como o bot do Jarvis/GNHFIN. App em `/opt/poker-bot`, venv próprio.
- Banco: Supabase (nada de Postgres a instalar). Bot em **polling** (não precisa de porta/Caddy/DNS).

## Deploy — do PC do Leo (Windows, mesmo estilo do TitanCalc)

```bat
:: 0. clonar/atualizar o repo (uma vez)
git clone https://github.com/leonardojacquier/KKNUTHS.git
cd KKNUTHS\backend
git checkout claude/poker-analysis-telegram-bot-mfuyhf

:: 1. criar o .env (copie .env.example e preencha as 5 chaves:
::    ANTHROPIC_API_KEY, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN,
::    SUPABASE_URL, SUPABASE_SERVICE_KEY)
copy .env.example .env
notepad .env

:: 2. enviar o código + .env pro VPS
ssh root@187.127.13.220 "mkdir -p /opt/poker-bot"
scp -r app tests scripts deploy requirements.txt run_bot.py Procfile Dockerfile README.md .env.example root@187.127.13.220:/opt/poker-bot/
scp .env root@187.127.13.220:/opt/poker-bot/.env

:: 3. rodar o deploy (idempotente — mesmo comando para atualizar depois)
ssh root@187.127.13.220 "bash /opt/poker-bot/deploy/vps_deploy.sh"
```

O script faz: git de segurança (sem `.bak`), venv próprio, dependências,
**roda os 42 testes como gate** (aborta se falharem), sobe/reinicia no pm2 e
instala o cron do relatório semanal (domingo 18h).

## Verificação pós-deploy

```bash
ssh root@187.127.13.220 "pm2 status poker-bot"
ssh root@187.127.13.220 "pm2 logs poker-bot --lines 30 --nostream"
# no Telegram: mandar /start pro bot e um .txt de hand history
```

## Operação

```bash
ssh root@187.127.13.220 "pm2 restart poker-bot"     # reiniciar
ssh root@187.127.13.220 "pm2 logs poker-bot"        # logs ao vivo
```

## Atualizar versão

Repita os passos 2 e 3 do deploy (scp + script). O script commita o estado
anterior no git local do servidor antes de aplicar — rollback é `git checkout`.

## Gotchas (herdados dos runbooks da casa)

- `pm2 install pm2-logrotate` uma vez, se ainda não tiver (recomendação da
  Revisão Geral de Código do VPS — logs não crescem sem limite).
- O `.env` NUNCA vai pro git (o script ignora); backup dele: copie antes de mexer.
- Se os testes falharem no passo 3, o deploy aborta — nada sobe quebrado.
