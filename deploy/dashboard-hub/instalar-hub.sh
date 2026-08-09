#!/usr/bin/env bash
# Instala a página /marketing no portal dashboard.vortex369.com.br — tudo de uma vez.
#
# Uso (na VPS, um comando só):
#   bash instalar-hub.sh "postgresql://hub_reader.tqvrsusrbnyahpxhnwxe:SENHA@HOST:6543/postgres"
#
# Opcional: limitar quem vê a página (por padrão libera para todo usuário que tenha
# lista de permissões; quem não tem já enxerga tudo, por regra do próprio Sidebar):
#   bash instalar-hub.sh "postgresql://..." leonardo,marketing
#
# O que faz:
#   1. baixa os 3 arquivos novos do KKNUTHS (repositório público, sem token)
#   2. grava MKT_DATABASE_URL no .env.local
#   3. põe o grupo MARKETING no Sidebar
#   4. libera /marketing no usuarios.json
#   5. builda; se o build falhar, DESFAZ tudo e não reinicia o pm2
#
# Faz backup de tudo que toca em .backup-hub-<data>/ e imprime o caminho no fim.
set -euo pipefail

RAW="https://raw.githubusercontent.com/leonardojacquier/KKNUTHS/claude/professional-website-design-qqgnfg/deploy/dashboard-hub"
APP_DIR="/opt/dashboard-gnh"
PM2_APP="dashboard-gnh"

DB_URL="${1:-}"
if [ -z "$DB_URL" ]; then
  echo "Falta a string de conexão."
  echo 'Uso: bash instalar-hub.sh "postgresql://hub_reader.tqvrsusrbnyahpxhnwxe:SENHA@HOST:6543/postgres"'
  exit 1
fi
case "$DB_URL" in
  postgresql://hub_reader.*) : ;;
  *) echo "A string precisa começar com postgresql://hub_reader. — confira o usuário."; exit 1 ;;
esac

cd "$APP_DIR"
BACKUP="$APP_DIR/.backup-hub-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
echo "→ backup em $BACKUP"

salvar() { if [ -f "$1" ]; then cp -a "$1" "$BACKUP/$(echo "$1" | tr '/' '_')"; fi; }
salvar src/components/Sidebar.tsx
salvar data/usuarios.json
salvar .env.local

# ---------- 1. arquivos novos ----------
echo "→ baixando os arquivos"
mkdir -p src/lib "src/app/(app)/marketing"
curl -fsSL "$RAW/src/lib/db-mkt.ts"                          -o src/lib/db-mkt.ts
curl -fsSL "$RAW/src/app/(app)/marketing/page.tsx"           -o "src/app/(app)/marketing/page.tsx"
curl -fsSL "$RAW/src/app/(app)/marketing/MarketingView.tsx"  -o "src/app/(app)/marketing/MarketingView.tsx"

# ---------- 2. variável de ambiente ----------
touch .env.local
if grep -q '^MKT_DATABASE_URL=' .env.local; then
  # substitui a linha inteira sem interpretar a URL (delimitador | não aparece em URL)
  sed -i "s|^MKT_DATABASE_URL=.*|MKT_DATABASE_URL=\"$DB_URL\"|" .env.local
  echo "→ MKT_DATABASE_URL atualizado"
else
  printf '\nMKT_DATABASE_URL="%s"\n' "$DB_URL" >> .env.local
  echo "→ MKT_DATABASE_URL adicionado"
fi

# ---------- 3 e 4. menu e permissão ----------
HUB_USUARIOS="${2:-}" python3 - <<'PY'
import json, os, re, sys, pathlib

# --- Sidebar: grupo MARKETING logo após a abertura do array `groups` ---
p = pathlib.Path('src/components/Sidebar.tsx')
s = p.read_text(encoding='utf-8')
if '/marketing' in s:
    print('→ Sidebar: já tinha /marketing, não mexi')
else:
    m = re.search(r'const\s+groups\s*:\s*Group\[\]\s*=\s*\[', s)
    if not m:
        sys.exit('ERRO: não achei `const groups: Group[] = [` no Sidebar.tsx — pare e me avise')
    bloco = (
        "\n  { title: 'MARKETING', accent: 'green', items: ["
        "{ href: '/marketing', label: 'Hub de Marketing' }] },"
    )
    s = s[:m.end()] + bloco + s[m.end():]
    p.write_text(s, encoding='utf-8')
    print('→ Sidebar: grupo MARKETING inserido (aparece no topo; dá para mover depois)')

# --- usuarios.json: libera /marketing para quem tem lista de permissões ---
# Quem NÃO tem `allowed` já enxerga tudo (regra do próprio Sidebar), então nem toca.
p = pathlib.Path('data/usuarios.json')
d = json.loads(p.read_text(encoding='utf-8'))
usuarios = d if isinstance(d, list) else d.get('usuarios', d.get('users', []))
so_estes = [x.strip() for x in os.environ.get('HUB_USUARIOS', '').split(',') if x.strip()]
tocados = []
for u in usuarios:
    if so_estes and (u.get('user') or u.get('email') or u.get('nome')) not in so_estes:
        continue
    if isinstance(u, dict) and isinstance(u.get('allowed'), list) and '/marketing' not in u['allowed']:
        u['allowed'].append('/marketing')
        tocados.append(u.get('user') or u.get('email') or u.get('nome') or '?')
if tocados:
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('→ usuarios.json: /marketing liberado para', ', '.join(tocados))
    print('  (para restringir, rode de novo passando os nomes no 2º argumento)')
else:
    print('→ usuarios.json: nada a mudar (ninguém tem lista, ou já estava liberado)')
PY

# ---------- 5. build ----------
echo "→ build (pode levar 1-2 min)"
rm -rf .next-prev
if [ -d .next ]; then cp -a .next .next-prev; fi

if npm run build; then
  pm2 restart "$PM2_APP" --update-env
  echo
  echo "PRONTO. Abra https://dashboard.vortex369.com.br/marketing"
  echo "Backup do que foi alterado: $BACKUP"
else
  echo
  echo "BUILD FALHOU — desfazendo. O portal continua no ar como estava."
  rm -rf .next
  if [ -d .next-prev ]; then mv .next-prev .next; fi
  rm -f src/lib/db-mkt.ts
  rm -rf "src/app/(app)/marketing"
  for f in "$BACKUP"/*; do
    [ -e "$f" ] || continue
    dest=$(basename "$f" | tr '_' '/')
    cp -a "$f" "$APP_DIR/$dest"
  done
  echo "Restaurado de $BACKUP. Me mande o erro do build acima."
  exit 1
fi
