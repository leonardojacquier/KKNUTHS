# Poker Bot — Deploy no VPS GNH (padrão da casa)

- Servidor: Hostinger srv1555380 — `ssh root@187.127.13.220` (chave; sem senha).
- Terminal web (alternativa): https://cam.hostingervps.com/2548/
- Processo: **pm2** (`poker-bot`), como o bot do Jarvis/GNHFIN. App em `/opt/poker-bot`, venv próprio.
- Banco: Supabase (nada de Postgres a instalar). Bot em **polling** (não precisa de porta/Caddy/DNS).

## ⚠️ REGRA DURA — infraestrutura COMPARTILHADA do VPS

O VPS hospeda VÁRIOS apps (Jarvis, GNHFIN, sites GNH/vortex369) atrás de um
**Caddy multi-tenant**. `/etc/caddy/Caddyfile` é config GLOBAL da casa:

- **NUNCA criar/sobrescrever o Caddyfile** (nem qualquer config global:
  nginx, ufw, systemd de terceiros) em oneshot ou script deste repo.
  Incidente real (2026-07-20): um oneshot deste repo fez `cat >
  /etc/caddy/Caddyfile` e derrubou os sites dos outros apps.
- Exposição pública do portal (uvicorn 127.0.0.1:8014) = **adicionar um
  bloco** ao Caddyfile existente, coordenado com o dono do VPS — ex.:
  `poker.vortex369.com.br { reverse_proxy 127.0.0.1:8014 }` + registro DNS.
- Oneshots deste repo podem mexer APENAS em `/opt/poker-bot` e no banco
  Supabase do poker. Fora disso, é território de outro app.

## E2E do Telegram (camada 3 da verificação) — ativar quando quiser

A sonda `scripts/e2e_probe.py` DORME até existirem credenciais de uma
conta-teste no `.env`. Para ativar (~10 min, uma vez):

1. Crie uma conta de Telegram nova (chip/número separado — NÃO use a sua).
2. Com ela, entre em https://my.telegram.org → API development tools →
   crie um app → copie `api_id` e `api_hash`.
3. Na VPS: `cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/e2e_login.py`
   (pede api_id, api_hash, telefone e o código que chega no app).
4. Cole as 3 linhas impressas (`E2E_API_ID/E2E_API_HASH/E2E_SESSION`) no
   `/opt/poker-bot/.env`. Pronto: a cada deploy (e todo dia 7h30) a
   conta-teste percorre /start → cola mão → /range → /treino (clica) →
   /simular, e qualquer falha chega no SEU Telegram.

A sessão fica só no `.env` da VPS — nunca no repositório.

## Deploy — do PC do Leo (PowerShell; o repo é público, o VPS clona sozinho)

```powershell
# 1. VPS clona/atualiza o repo e monta /opt/poker-bot (idempotente)
ssh root@187.127.13.220 "git clone -b claude/poker-analysis-telegram-bot-mfuyhf https://github.com/leonardojacquier/KKNUTHS.git /opt/kknuths 2>/dev/null || git -C /opt/kknuths pull; mkdir -p /opt/poker-bot; cp -r /opt/kknuths/backend/. /opt/poker-bot/"

# 2. criar o .env no VPS (here-string do PowerShell -> stdin do ssh)
@'
TELEGRAM_BOT_TOKEN=...
ANTHROPIC_API_KEY=...
ANALYSIS_MODEL=claude-opus-4-8
CHEAP_MODEL=claude-haiku-4-5-20251001
OPENAI_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
SUPABASE_URL=https://htvjviovcfvtpgeloekn.supabase.co
SUPABASE_SERVICE_KEY=...
DEFAULT_LANG=pt
'@ | ssh root@187.127.13.220 "cat > /opt/poker-bot/.env"

# 3. rodar o deploy (mesmo comando para atualizar depois)
ssh root@187.127.13.220 "bash /opt/poker-bot/deploy/vps_deploy.sh"
```

PowerShell: separar comandos com `;` (não `&`). Para atualizar versão:
repetir os passos 1 e 3.

O script faz: git de segurança (sem `.bak`), venv próprio, dependências,
**roda os testes como gate** (aborta se falharem), sobe/reinicia no pm2 e
instala os crons do produto: relatório semanal (dom 18h), quiz diário (19h),
calibração (seg 5h), auditor de coerência (6h), sonda E2E (7h30), o
**resumo diário de uso pro admin** (`daily_usage.py`, 23h UTC / 20h BRT —
"entrou gente nova?", ativos do dia, mãos/perguntas/quiz) e o **juiz da
saída** (`output_judge.py`, 8h — audita as respostas que o coach mandou:
selo de veredito, número em cada decisão, jargão proibido, calque, carta
sem ícone; avisa o admin quando a qualidade cai).

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

## Auto-deploy (instalar uma vez, nunca mais atualizar na mão)

O cron confere o GitHub a cada 2 min; commit novo → testes → deploy → aviso
no Telegram do admin. Commit com teste quebrado NÃO sobe (bot antigo segue no ar).

```powershell
ssh root@187.127.13.220 "chmod +x /opt/poker-bot/deploy/auto_update.sh; grep -q '^TELEGRAM_ADMIN_CHAT_ID=' /opt/poker-bot/.env || echo 'TELEGRAM_ADMIN_CHAT_ID=6452742024' >> /opt/poker-bot/.env; (crontab -l 2>/dev/null | grep -v poker-autodeploy; echo '*/2 * * * * /opt/poker-bot/deploy/auto_update.sh >> /var/log/poker-autodeploy.log 2>&1') | crontab -; echo CRON INSTALADO"
```

Acompanhar: `ssh root@187.127.13.220 "tail -20 /var/log/poker-autodeploy.log"`

## Atualizar versão (manual, se precisar)

Repita os passos 2 e 3 do deploy (scp + script). O script commita o estado
anterior no git local do servidor antes de aplicar — rollback é `git checkout`.

## Gotchas (herdados dos runbooks da casa)

- `pm2 install pm2-logrotate` uma vez, se ainda não tiver (recomendação da
  Revisão Geral de Código do VPS — logs não crescem sem limite).
- O `.env` NUNCA vai pro git (o script ignora); backup dele: copie antes de mexer.
- Se os testes falharem no passo 3, o deploy aborta — nada sobe quebrado.
