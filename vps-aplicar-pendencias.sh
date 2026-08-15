#!/usr/bin/env bash
# Aplica no VPS as duas pendências pendentes do site GNH:
#   1. Cache-Control no-cache nas SUBPÁGINAS de produto (matcher @html do Caddy)
#   2. Reinstala /opt/gnh-autodeploy.sh (URLs limpas) e garante o cron
#
# Uso (NO VPS, como root):
#   cd /root/KKNUTHS && git pull && bash vps-aplicar-pendencias.sh
#
# O VPS é COMPARTILHADO: o script faz backup do Caddyfile, roda `caddy validate`
# e, se a validação falhar, restaura o backup e aborta SEM dar reload.
set -euo pipefail

CADDYFILE="/etc/caddy/Caddyfile"
REPO="/root/KKNUTHS"
DEST="/opt/gnh"
STAMP=$(date -u +%Y%m%d-%H%M%S)
BACKUP="/root/Caddyfile.bak-$STAMP"

say() { printf '\n\033[1m== %s\033[0m\n' "$1"; }
die() { printf '\033[31mERRO: %s\033[0m\n' "$1" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "rode como root"
[ -f "$CADDYFILE" ] || die "$CADDYFILE não existe"

# ── 1. Caddy: matcher @html cobrindo as subpáginas ─────────────────────────
say "1/2 — Cache-Control nas subpáginas (Caddy)"

CANONICO='@html path / /index.html */ *.html'
ANTIGO='^[[:space:]]*@html path (\*\.html /|/ \*\.html|\*\.html)[[:space:]]*$'

N=$(grep -cE "$ANTIGO" "$CADDYFILE" || true)

if [ "$N" = "0" ]; then
  if grep -qF "$CANONICO" "$CADDYFILE"; then
    echo "matcher já está correto — nada a fazer no Caddy"
  else
    die "nenhuma linha '@html path ...' reconhecida em $CADDYFILE.
Edite à mão: no bloco gnhorizons.com a linha deve ficar
    $CANONICO
depois rode: caddy validate --config $CADDYFILE && systemctl reload caddy"
  fi
else
  # Corrige TODAS as ocorrências. O matcher antigo (*.html /) pega a home e os
  # arquivos .html, mas não as URLs de diretório (/ventas/apilador-electrico/).
  # O bloco do gnh.vortex369.com.br tem o mesmo defeito do gnhorizons.com, então
  # os dois são corrigidos. A troca só AMPLIA o conjunto de páginas servidas com
  # no-cache — não deixa de servir nada.
  echo "$N linha(s) a corrigir:"
  grep -nE "$ANTIGO" "$CADDYFILE" | sed 's/^/    /'

  rm -f /etc/caddy/sed?????? 2>/dev/null || true   # sobras de execuções falhas
  cp -a "$CADDYFILE" "$BACKUP"
  echo "backup: $BACKUP"

  # `sed -i` grava um temporário ao lado e renomeia por cima — o rename é
  # negado quando o Caddyfile é bind-mount ("Operation not permitted").
  # Escrevemos o conteúdo no arquivo existente, sem renomear nada.
  TMP=$(mktemp /tmp/caddyfile.XXXXXX)
  trap 'rm -f "$TMP"' EXIT
  sed -E "s#^([[:space:]]*)@html path (\*\.html /|/ \*\.html|\*\.html)[[:space:]]*\$#\1$CANONICO#" \
      "$CADDYFILE" > "$TMP"
  [ -s "$TMP" ] || die "sed gerou arquivo vazio — nada foi alterado"
  cat "$TMP" > "$CADDYFILE" || die "sem permissão de escrita em $CADDYFILE"

  echo "diff aplicado:"
  diff -u "$BACKUP" "$CADDYFILE" | sed 's/^/    /' || true

  M=$(grep -cE "$ANTIGO" "$CADDYFILE" || true)
  [ "$M" = "0" ] || { cat "$BACKUP" > "$CADDYFILE"; die "sobraram $M linhas antigas; backup restaurado"; }

  if ! caddy validate --config "$CADDYFILE"; then
    cat "$BACKUP" > "$CADDYFILE"
    die "caddy validate FALHOU — Caddyfile restaurado, nenhum reload foi dado"
  fi

  systemctl reload caddy
  echo "Caddy recarregado"
fi

# ── 2. Script de auto-deploy + cron ────────────────────────────────────────
say "2/2 — auto-deploy e cron"

[ -f "$REPO/vps-autodeploy.sh" ] || die "$REPO/vps-autodeploy.sh não existe (rode git pull antes)"
cp "$REPO/vps-autodeploy.sh" /opt/gnh-autodeploy.sh
chmod +x /opt/gnh-autodeploy.sh
echo "/opt/gnh-autodeploy.sh atualizado"

if crontab -l 2>/dev/null | grep -q gnh-autodeploy; then
  echo "cron já configurado"
else
  ( crontab -l 2>/dev/null; echo "*/2 * * * * /opt/gnh-autodeploy.sh >/dev/null 2>&1" ) | crontab -
  echo "cron criado (a cada 2 min)"
fi

/opt/gnh-autodeploy.sh || true   # publica já, sem esperar o cron

# ── 3. Conferência ─────────────────────────────────────────────────────────
say "Conferência"

IP=$(hostname -I | awk '{print $1}')
for u in / /ventas/ /ventas/camion-volquete-de-orugas/ /ventas/apilador-electrico/ \
         /fichas/pdf/camion-volquete-orugas.pdf /sitemap.xml; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --resolve "gnhorizons.com:80:$IP" \
         "http://gnhorizons.com$u" || echo 000)
  printf '  %-46s %s\n' "$u" "$code"
done

echo
echo "Cache-Control das subpáginas:"
curl -sI --resolve "gnhorizons.com:80:$IP" \
  "http://gnhorizons.com/ventas/camion-volquete-de-orugas/" | grep -i 'cache-control' || \
  echo "  (sem header Cache-Control — revise o bloco do Caddy)"

echo
echo "Últimas linhas do log de deploy:"
tail -3 /var/log/gnh-autodeploy.log 2>/dev/null || echo "  (log ainda vazio)"

say "Pronto"
[ -f "$BACKUP" ] && echo "Se algo saiu errado no Caddy: cat $BACKUP > $CADDYFILE && caddy validate --config $CADDYFILE && systemctl reload caddy"
exit 0
