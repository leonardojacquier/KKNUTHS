# Endurecimento do VPS — GNH (3 passos)

## 1. Security headers no Caddy
```bash
cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak-$(date +%F)
nano /etc/caddy/Caddyfile
```
- Cole o snippet de `deploy/caddy-security-headers.txt` **no topo** do arquivo
- Dentro do bloco `gnh.vortex369.com.br { ... }` adicione a linha: `import gnh_security`
- Idem no bloco `stats.vortex369.com.br { ... }`
```bash
caddy validate --config /etc/caddy/Caddyfile   # OBRIGATÓRIO
systemctl reload caddy                          # só se disser "Valid configuration"
```
Conferir: https://securityheaders.com → digite gnh.vortex369.com.br (nota esperada: A)

## 2. Backup semanal do Umami
```bash
cd ~/KKNUTHS && git pull
bash deploy/umami/backup-umami.sh                 # primeiro backup agora (teste)
bash deploy/umami/backup-umami.sh --install-cron  # agenda toda segunda 03:20
```
Backups ficam em `~/backups/umami/` (mantém os últimos 8 = 2 meses).

## 3. Atualizações de segurança automáticas do sistema
```bash
apt-get install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades   # responda "Yes"
```

## 4. (Sem VPS) Monitoramento de uptime — 5 minutos, grátis
1. Crie conta em https://uptimerobot.com
2. Add New Monitor → HTTP(s) → `https://gnh.vortex369.com.br` (depois trocar p/ gnhorizons.com)
3. Alertas por e-mail — avisa se o site cair, checando a cada 5 min

## O que já está coberto (para referência)
- HTTPS automático (Caddy/Let's Encrypt) em todos os domínios
- Supabase com RLS testado: a chave do site só INSERE, nunca lê/apaga
- Umami em Docker isolado (porta só em localhost), senha trocada
- fail2ban ativo no VPS · site estático sem backend próprio
- Backup do site = o próprio repositório Git
