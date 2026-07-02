# Deploy no VPS GNH (padrão GNHFIN / agente-century)

O bot roda no mesmo VPS dos outros sistemas (`root@187.127.13.220`), no mesmo
padrão do bot financeiro (GNHFIN/Jarvis): app em `/opt/`, venv próprio, **pm2**.

## Passo a passo (da sua máquina, onde está o repositório clonado)

```bash
# 0. clonar o repo na sua máquina (se ainda não tiver)
git clone https://github.com/leonardojacquier/KKNUTHS.git
cd KKNUTHS/backend

# 1. criar o .env local (copie de .env.example e preencha as chaves:
#    ANTHROPIC_API_KEY, OPENAI_API_KEY, TELEGRAM_BOT_TOKEN,
#    SUPABASE_URL, SUPABASE_SERVICE_KEY)
cp .env.example .env && nano .env

# 2. subir o código + .env para o VPS
ssh root@187.127.13.220 "mkdir -p /opt/poker-bot"
rsync -az --exclude venv --exclude __pycache__ --exclude .pytest_cache \
    ./ root@187.127.13.220:/opt/poker-bot/

# 3. rodar o deploy (idempotente — use o mesmo comando para atualizar depois)
ssh root@187.127.13.220 "bash /opt/poker-bot/deploy/vps_deploy.sh"
```

O script cuida de: git de segurança, venv, dependências, testes (aborta se
falharem), pm2 (`poker-bot`) e cron do relatório semanal (domingo 18h).

## Operação (igual aos outros bots do VPS)

```bash
ssh root@187.127.13.220 "pm2 status"                      # está de pé?
ssh root@187.127.13.220 "pm2 logs poker-bot --lines 50"   # logs
ssh root@187.127.13.220 "pm2 restart poker-bot"           # reiniciar
```

## Atualizar versão

Repita os passos 2 e 3 — o rsync manda só o que mudou e o script reinicia.

## Notas

- O bot usa **polling** (não precisa de porta aberta nem domínio). Se um dia
  migrar para webhook, o FastAPI está pronto em `app/api/main.py`.
- Memória/banco ficam no **Supabase** (projeto kknuths-poker) — nada a instalar
  no VPS além do Python.
- Conforme a Revisão Geral de Código do VPS: venv próprio, sem segredos em
  /root, logs via pm2 (instale `pm2 install pm2-logrotate` se ainda não tiver).
