# Resumo diário do gnhorizons.com no Telegram

Envia todo dia às 20h (Asunción) um resumo dos acessos ao site, direto no seu
Telegram. Lê só números agregados (sem dados pessoais) da função protegida
`resumen_dia()` de Supabase — usa a chave pública do site + um token de leitura,
então **nenhuma chave secreta poderosa fica no VPS**.

## Instalação no VPS (uma vez)

1. Copie o arquivo de config e preencha com o seu bot do Telegram:

   ```bash
   sudo mkdir -p /opt/gnh_lib
   sudo tee /opt/gnh_lib/gnh-resumen.env >/dev/null <<'ENV'
   RESUMEN_TOKEN=gnh-rsm-a91f7c2e
   TELEGRAM_BOT_TOKEN=COLE_AQUI_O_TOKEN_DO_SEU_BOT
   TELEGRAM_CHAT_ID=COLE_AQUI_O_SEU_CHAT_ID
   ENV
   sudo chmod 600 /opt/gnh_lib/gnh-resumen.env
   ```

   > O bot e o chat_id você já tem no `agente-century` — reutilize os mesmos
   > valores (o `TELEGRAM_ADMIN_CHAT_ID` do `.env` de lá é o chat_id).

2. Teste enviando o resumo de hoje agora:

   ```bash
   python3 ~/KKNUTHS/deploy/telegram/gnh-resumen-diario.py 0
   ```

   Deve chegar a mensagem no Telegram. (`1` = ontem, útil para testar.)

3. Agende no cron (20h Asunción — o servidor já está nesse fuso):

   ```bash
   ( crontab -l 2>/dev/null; echo '0 20 * * * /usr/bin/python3 /root/KKNUTHS/deploy/telegram/gnh-resumen-diario.py >> /var/log/gnh-resumen.log 2>&1' ) | crontab -
   ```

Pronto. Todo dia às 20h chega o resumo.

## Trocar o horário / token

- Horário: edite a linha do `crontab -e` (formato `min hora * * *`, em Asunción).
- Token: está na função `resumen_dia` (Supabase) e no `.env`. Para rotacionar,
  peça ao Claude para atualizar a função com um token novo e troque no `.env`.

---

# Bot de consulta sob demanda (comandos no Telegram)

Além do resumo automático das 20h, um bot responde na hora quando você
digita um comando: **/resumo** (hoje), **/ontem**, **/semana**, **/ajuda**.

> ⚠️ Um token de bot só aceita UM "escutador". Por isso use um bot
> **dedicado** (criado no @BotFather), não o mesmo do agente-century se
> ele já responder a comandos.

## Instalação no VPS

1. Crie o bot no Telegram: fale com **@BotFather** → `/newbot` → escolha
   nome e usuário → ele te dá um **token**.

2. Config (reaproveita seu chat_id):

   ```bash
   sudo tee /opt/gnh_lib/gnh-bot.env >/dev/null <<'ENV'
   RESUMEN_TOKEN=gnh-rsm-a91f7c2e
   BOT_TOKEN=COLE_O_TOKEN_DO_BOT_NOVO
   ALLOWED_CHATS=6452742024,7693591644
   ENV
   sudo chmod 600 /opt/gnh_lib/gnh-bot.env
   ```

   `ALLOWED_CHATS` = quem pode consultar (os outros recebem "não autorizado").

3. Instale o serviço (roda sempre, reinicia sozinho):

   ```bash
   sudo cp ~/KKNUTHS/deploy/telegram/gnh-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now gnh-bot
   sudo systemctl status gnh-bot --no-pager | head -8
   ```

4. No Telegram, abra o bot novo, mande **/start** e depois **/resumo**.
   O menu de comandos (botão "/") aparece automaticamente.

## Ver logs / reiniciar

```bash
journalctl -u gnh-bot -f          # logs ao vivo
sudo systemctl restart gnh-bot    # reiniciar
```
