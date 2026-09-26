#!/usr/bin/env bash
# Move o hub para um repositório PRIVADO só da agência, mantendo o histórico desta pasta.
#
# 1. No GitHub: New repository → nome "agencia-hub" → Private → SEM README → Create.
# 2. Na raiz do KKNUTHS clonado, rode:
#       bash agencia-hub/mover-para-repo-proprio.sh https://github.com/<usuario>/agencia-hub.git
# 3. Clone o repositório novo e abra no Cursor (File → Open Folder).
set -euo pipefail
[ $# -eq 1 ] || { echo "Uso: bash agencia-hub/mover-para-repo-proprio.sh <url-do-repo-privado>"; exit 1; }
cd "$(git rev-parse --show-toplevel)"
git subtree split --prefix=agencia-hub -b agencia-hub-export
git push "$1" agencia-hub-export:main
git branch -D agencia-hub-export
echo "Pronto: o hub está em $1 (branch main)."
