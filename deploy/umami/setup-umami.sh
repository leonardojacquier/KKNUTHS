#!/usr/bin/env bash
# FASE 6B — instala Umami no VPS (rodar NA VPS, na pasta do repo: bash deploy/umami/setup-umami.sh)
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Subindo Umami (Docker)..."
docker compose up -d
echo "==> Aguardando o app responder..."
for i in $(seq 1 60); do
  curl -fsS http://127.0.0.1:3400/api/heartbeat >/dev/null 2>&1 && break
  sleep 2
done

echo "==> Registrando o site GNH com o website-id fixo usado nas páginas..."
docker exec umami-db psql -U umami -d umami -c "
  insert into website (website_id, name, domain, user_id, created_at)
  select '12bb20da-6e8c-4f0a-8953-5c8c430396f1', 'GNH Site', 'gnhorizons.com', user_id, now()
  from \"user\" where username = 'admin'
  on conflict (website_id) do nothing;"

echo "==> Pronto. Agora exponha no Caddy (valide antes de recarregar!):"
echo "-----------------------------------------------------------"
cat caddy-snippet.txt
echo "-----------------------------------------------------------"
echo "Login inicial do Umami: admin / umami  (TROQUE a senha no primeiro acesso)"
echo "Painel: https://stats.vortex369.com.br"
