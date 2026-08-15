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
HEADER='header @html Cache-Control "no-cache"'
ANTIGO='^[[:space:]]*@html path (\*\.html /|/ \*\.html|\*\.html)[[:space:]]*$'

# (a) linhas no formato antigo, em qualquer bloco — o matcher (*.html /) pega a
#     home e os .html, mas não as URLs de diretório (/ventas/apilador-electrico/)
N=$(grep -cE "$ANTIGO" "$CADDYFILE" || true)

# (b) o bloco do gnhorizons.com pode não ter @html nenhum — nesse caso as
#     subpáginas saem sem Cache-Control e o navegador segura a versão velha
FALTA_GNH=0
if grep -qE '^gnhorizons\.com' "$CADDYFILE"; then
  if ! awk '/^gnhorizons\.com/{d=1} d && /@html path/{f=1} d && /^\}/{exit} END{exit !f}' "$CADDYFILE"; then
    FALTA_GNH=1
  fi
else
  echo "AVISO: não achei bloco começando em 'gnhorizons.com' — pulando o passo (b)"
fi

if [ "$N" = "0" ] && [ "$FALTA_GNH" = "0" ]; then
  grep -qF "$CANONICO" "$CADDYFILE" \
    && echo "Caddy já está correto — nada a fazer" \
    || die "nenhuma linha '@html path ...' reconhecida em $CADDYFILE.
Edite à mão: dentro do bloco gnhorizons.com acrescente
    $CANONICO
    $HEADER
depois rode: caddy validate --config $CADDYFILE && systemctl reload caddy"
else
  [ "$N" = "0" ] || { echo "(a) $N linha(s) no formato antigo:"; grep -nE "$ANTIGO" "$CADDYFILE" | sed 's/^/    /'; }
  [ "$FALTA_GNH" = "0" ] || echo "(b) bloco gnhorizons.com sem matcher @html — vou inserir"

  rm -f /etc/caddy/sed?????? 2>/dev/null || true   # sobras de execuções falhas
  cp -a "$CADDYFILE" "$BACKUP"
  echo "backup: $BACKUP"

  # O Caddyfile do VPS está com o atributo IMUTÁVEL (chattr +i): nem root
  # escreve nele, nem renomeia por cima — é o que fazia `sed -i` falhar com
  # "Operation not permitted". Levantamos o atributo só durante a edição e o
  # trap garante que ele volte, mesmo se o script morrer no meio.
  IMMUT=0
  if command -v lsattr >/dev/null 2>&1 && \
     lsattr -d "$CADDYFILE" 2>/dev/null | awk '{print $1}' | grep -q i; then
    IMMUT=1
  fi

  TMP=$(mktemp /tmp/caddyfile.XXXXXX)
  restaura() {
    [ "${IMMUT:-0}" = "1" ] && chattr +i "$CADDYFILE" 2>/dev/null || true
    rm -f "${TMP:-}" 2>/dev/null || true
  }
  trap restaura EXIT

  if [ "$IMMUT" = "1" ]; then
    echo "atributo imutável detectado — removendo temporariamente (será restaurado no fim)"
    chattr -i "$CADDYFILE" || die "chattr -i falhou em $CADDYFILE"
  fi

  # `sed -i` renomeia por cima do original; aqui escrevemos no arquivo existente.
  sed -E "s#^([[:space:]]*)@html path (\*\.html /|/ \*\.html|\*\.html)[[:space:]]*\$#\1$CANONICO#" \
      "$CADDYFILE" > "$TMP"

  if [ "$FALTA_GNH" = "1" ]; then
    awk -v canon="$CANONICO" -v hdr="$HEADER" '
      /^gnhorizons\.com/ { d=1 }
      d && /^\}/ { print "\t" canon; print "\t" hdr; d=0 }
      { print }
    ' "$TMP" > "$TMP.2" && mv "$TMP.2" "$TMP"
  fi

  [ -s "$TMP" ] || die "edição gerou arquivo vazio — nada foi alterado"
  cat "$TMP" > "$CADDYFILE" || die "não consegui escrever em $CADDYFILE.
Se não for o atributo imutável, pode ser AppArmor/SELinux. Diagnóstico:
    lsattr -d $CADDYFILE ; mount | grep -i caddy ; dmesg | tail -20"

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

  if [ "$IMMUT" = "1" ]; then
    chattr +i "$CADDYFILE" && IMMUT=0
    echo "atributo imutável restaurado"
  fi
fi

# ── 2. Script de auto-deploy + cron ────────────────────────────────────────
say "2/2 — auto-deploy e cron"

[ -f "$REPO/vps-autodeploy.sh" ] || die "$REPO/vps-autodeploy.sh não existe (rode git pull antes)"
cp "$REPO/vps-autodeploy.sh" /opt/gnh-autodeploy.sh
chmod +x /opt/gnh-autodeploy.sh
echo "/opt/gnh-autodeploy.sh atualizado"

# A crontab do root é COMPARTILHADA com os outros sites do VPS. Se `crontab -l`
# falhasse, o `( crontab -l ; echo ... ) | crontab -` antigo gravaria uma crontab
# contendo SÓ a linha do gnh, apagando os jobs dos outros domínios. Agora a lista
# atual é salva em arquivo e só seguimos adiante se a leitura tiver dado certo.
CRONBAK="/root/crontab.bak-$STAMP"
if crontab -l > "$CRONBAK" 2>/dev/null; then
  CRON_OK=1
else
  CRON_OK=0
  : > "$CRONBAK"
fi

if [ "$CRON_OK" = "0" ] && [ -s /var/spool/cron/crontabs/root ]; then
  die "'crontab -l' falhou mas /var/spool/cron/crontabs/root não está vazio.
Não vou reescrever a crontab às cegas — isso apagaria os jobs dos outros sites.
Confira à mão: crontab -l ; cat /var/spool/cron/crontabs/root"
fi

echo "crontab atual salva em $CRONBAK ($(wc -l < "$CRONBAK") linha(s))"

if grep -q gnh-autodeploy "$CRONBAK"; then
  echo "cron já configurado ($(grep -c gnh-autodeploy "$CRONBAK") entrada(s))"
else
  { cat "$CRONBAK"; echo "*/2 * * * * /opt/gnh-autodeploy.sh >/dev/null 2>&1"; } | crontab -
  echo "cron criado (a cada 2 min) — as $(wc -l < "$CRONBAK") linha(s) anteriores foram preservadas"
fi

/opt/gnh-autodeploy.sh || true   # publica já, sem esperar o cron

# ── 3. Conferência ─────────────────────────────────────────────────────────
say "Conferência"

IP=$(hostname -I | awk '{print $1}')

# Conferir em HTTPS: na porta 80 o Caddy responde 308 (redirect automático para
# HTTPS) e o teste não diz nada sobre o conteúdo nem sobre os headers.
echo "blocos de site no Caddyfile:"
grep -nE '^[^[:space:]#].*\{' "$CADDYFILE" | sed 's/^/    /'
echo

for u in / /ventas/ /ventas/camion-volquete-de-orugas/ /ventas/apilador-electrico/ \
         /fichas/pdf/camion-volquete-orugas.pdf /sitemap.xml; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --resolve "gnhorizons.com:443:$IP" \
         "https://gnhorizons.com$u" || echo 000)
  printf '  %-46s %s\n' "$u" "$code"
done

echo
echo "Cache-Control das subpáginas:"
curl -sI --resolve "gnhorizons.com:443:$IP" \
  "https://gnhorizons.com/ventas/camion-volquete-de-orugas/" \
  | grep -iE '^(HTTP/|cache-control)' | sed 's/^/  /' || \
  echo "  (sem header Cache-Control — o bloco do gnhorizons.com pode não ter o matcher @html)"

echo
echo "Últimas linhas do log de deploy:"
tail -3 /var/log/gnh-autodeploy.log 2>/dev/null || echo "  (log ainda vazio)"

say "Pronto"
[ -f "$BACKUP" ] && echo "Se algo saiu errado no Caddy: cat $BACKUP > $CADDYFILE && caddy validate --config $CADDYFILE && systemctl reload caddy"
exit 0
