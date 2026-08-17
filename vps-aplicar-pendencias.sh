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

# (a) Regra geral: uma linha `@html path` só cobre as URLs de diretório
#     (/ventas/camion-volquete-de-orugas/) se tiver o curinga `*/`. Sem ele, a
#     subpágina sai sem Cache-Control e o navegador segura a versão velha.
#     Já apareceram três variantes furadas no Caddyfile deste VPS:
#         @html path *.html /
#         @html path / *.html
#         @html path / /index.html /ventas/ /institucional/ *.html
#     em vez de caçar cada forma, tratamos como defeituosa toda linha sem `*/`.
#     O canônico é um superconjunto de todas elas: `*/` cobre /ventas/,
#     /institucional/ e qualquer subpasta, e `/` continua explícito.
ANTIGO='^[[:space:]]*@html path '
N=$(grep -E "$ANTIGO" "$CADDYFILE" | grep -vcF '*/' || true)

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

# (c) root do gnhorizons.com apontando para a subpasta em vez de /opt/gnh
ROOT_ERRADO=0
if awk '/^gnhorizons\.com/{d=1} d && /^[[:space:]]*root \* \/opt\/gnh\/assets\/nuevo[[:space:]]*$/{f=1} d && /^\}/{exit} END{exit !f}' "$CADDYFILE"; then
  ROOT_ERRADO=1
fi

if [ "$N" = "0" ] && [ "$FALTA_GNH" = "0" ] && [ "$ROOT_ERRADO" = "0" ]; then
  grep -qF "$CANONICO" "$CADDYFILE" \
    && echo "Caddy já está correto — nada a fazer" \
    || die "nenhuma linha '@html path ...' reconhecida em $CADDYFILE.
Edite à mão: dentro do bloco gnhorizons.com acrescente
    $CANONICO
    $HEADER
depois rode: caddy validate --config $CADDYFILE && systemctl reload caddy"
else
  [ "$N" = "0" ] || { echo "(a) $N linha(s) @html sem o curinga */:"; grep -nE "$ANTIGO" "$CADDYFILE" | grep -vF '*/' | sed 's/^/    /'; }
  [ "$FALTA_GNH" = "0" ] || echo "(b) bloco gnhorizons.com sem matcher @html — vou inserir"
  [ "$ROOT_ERRADO" = "0" ] || echo "(c) root do gnhorizons.com em /opt/gnh/assets/nuevo — a home do site oficial está caindo no site antigo; vou apontar para /opt/gnh"

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
  # awk em vez de sed: a condição é negativa (linha @html que NÃO tem `*/`).
  # A indentação original da linha é preservada.
  awk -v canon="$CANONICO" '
    /^[[:space:]]*@html path / && $0 !~ /\*\// {
      match($0, /^[[:space:]]*/)
      print substr($0, 1, RLENGTH) canon
      next
    }
    { print }
  ' "$CADDYFILE" > "$TMP"

  if [ "$FALTA_GNH" = "1" ]; then
    awk -v canon="$CANONICO" -v hdr="$HEADER" '
      /^gnhorizons\.com/ { d=1 }
      d && /^\}/ { print "\t" canon; print "\t" hdr; d=0 }
      { print }
    ' "$TMP" > "$TMP.2" && mv "$TMP.2" "$TMP"
  fi

  # (c) O gnhorizons.com é o site OFICIAL e sua home tem que ser o redesign.
  #     Com root */opt/gnh/assets/nuevo* o redesign em /opt/gnh/index.html nunca
  #     é servido (a home cai no site antigo) e as fotos do redesign, que
  #     apontam para assets/nuevo/img/..., quebram. A raiz correta é /opt/gnh,
  #     a mesma do domínio de preview — é o que os scripts de deploy montam.
  if [ "$ROOT_ERRADO" = "1" ]; then
    awk '
      /^gnhorizons\.com/ { d=1 }
      d && /^[[:space:]]*root \* \/opt\/gnh\/assets\/nuevo[[:space:]]*$/ {
        match($0, /^[[:space:]]*/)
        print substr($0, 1, RLENGTH) "root * /opt/gnh"
        next
      }
      d && /^\}/ { d=0 }
      { print }
    ' "$TMP" > "$TMP.2" && mv "$TMP.2" "$TMP"
  fi

  [ -s "$TMP" ] || die "edição gerou arquivo vazio — nada foi alterado"
  cat "$TMP" > "$CADDYFILE" || die "não consegui escrever em $CADDYFILE.
Se não for o atributo imutável, pode ser AppArmor/SELinux. Diagnóstico:
    lsattr -d $CADDYFILE ; mount | grep -i caddy ; dmesg | tail -20"

  echo "diff aplicado:"
  diff -u "$BACKUP" "$CADDYFILE" | sed 's/^/    /' || true

  M=$(grep -E "$ANTIGO" "$CADDYFILE" | grep -vcF '*/' || true)
  [ "$M" = "0" ] || { cat "$BACKUP" > "$CADDYFILE"; die "sobraram $M linhas @html sem */; backup restaurado"; }

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

CNT=$(grep -c gnh-autodeploy "$CRONBAK" || true)
if [ "${CNT:-0}" -gt 1 ]; then
  # Duas entradas rodando o mesmo script a cada 2 min podem se sobrepor no
  # git reset --hard. Mantém a primeira e descarta as demais.
  awk '/gnh-autodeploy/{if(vista++) next} {print}' "$CRONBAK" | crontab -
  echo "cron tinha $CNT entradas duplicadas — mantida 1"
elif [ "${CNT:-0}" = "1" ]; then
  echo "cron já configurado (1 entrada)"
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
# O reload do Caddy é gracioso: por um instante os handlers antigos ainda
# respondem, e esta conferência roda logo depois dele. Sem a espera, dá falso
# negativo. As outras URLs não servem para checar o root — /ventas/, as fichas e
# o sitemap.xml respondem 200 nos DOIS roots; só a "/" distingue.
echo "Home do gnhorizons.com (tem que ser o redesign):"
home_ok=0
for i in 1 2 3 4 5; do
  if curl -sk --max-time 20 --resolve "gnhorizons.com:443:$IP" https://gnhorizons.com/ | grep -qF 'SZ34D'; then
    home_ok=1
    break
  fi
  sleep 3
done
if [ "$home_ok" = "1" ]; then
  echo "  OK — home é o redesign (tentativa $i)"
else
  echo "  FALHOU — a home NÃO é o redesign depois de ~15 s; confira o root do bloco gnhorizons.com"
fi

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
