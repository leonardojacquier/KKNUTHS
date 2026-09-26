#!/usr/bin/env bash
# Cria a pasta de um cliente novo a partir de clientes/_modelo.
# Uso: bash ferramentas/novo-cliente.sh "Nome do Cliente"
set -euo pipefail
[ $# -ge 1 ] || { echo 'Uso: bash ferramentas/novo-cliente.sh "Nome do Cliente"'; exit 1; }
NOME="$1"
AQUI="$(cd "$(dirname "$0")/.." && pwd)"
SLUG="$(python3 -c 'import re,sys,unicodedata as u;a=u.normalize("NFD",sys.argv[1]);a="".join(c for c in a if not u.combining(c)).lower();print(re.sub(r"[^a-z0-9]+","-",a).strip("-"))' "$NOME")"
DEST="$AQUI/clientes/$SLUG"
[ -e "$DEST" ] && { echo "Já existe: clientes/$SLUG"; exit 1; }
cp -r "$AQUI/clientes/_modelo" "$DEST"
find "$DEST" -type f \( -name '*.md' -o -name '*.html' \) -exec sed -i.bak "s/{{CLIENTE}}/$NOME/g" {} \; -exec rm -f {}.bak \;
echo "| $NOME | \`$SLUG/\` | — | onboarding |" >> "$AQUI/clientes/README.md"
echo "Criado: clientes/$SLUG"
echo "Próximo passo: preencher clientes/$SLUG/briefing.md (playbooks/01-onboarding.md)"
