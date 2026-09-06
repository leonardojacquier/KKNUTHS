#!/usr/bin/env bash
# Prepara o VPS para o repositório ficar PRIVADO sem quebrar o auto-deploy.
# 1) Gera uma deploy key (só leitura) se não existir
# 2) Troca o remote do clone para SSH
# 3) Testa o acesso
# Depois de rodar: cole a chave pública impressa em
#   GitHub -> repo KKNUTHS -> Settings -> Deploy keys -> Add deploy key (read-only)
set -euo pipefail

KEY=/root/.ssh/kknuths_deploy
REPO_DIR=/opt/kknuths

if [ ! -f "$KEY" ]; then
    ssh-keygen -t ed25519 -N "" -f "$KEY" -C "kknuths-deploy@vps" -q
    echo "Deploy key criada."
fi

# usar esta chave só para github.com/KKNUTHS
mkdir -p /root/.ssh
if ! grep -q "kknuths_deploy" /root/.ssh/config 2>/dev/null; then
    cat >> /root/.ssh/config <<CFG

Host github.com-kknuths
    HostName github.com
    User git
    IdentityFile $KEY
    IdentitiesOnly yes
CFG
fi
ssh-keyscan -t ed25519 github.com >> /root/.ssh/known_hosts 2>/dev/null || true
sort -u /root/.ssh/known_hosts -o /root/.ssh/known_hosts

git -C "$REPO_DIR" remote set-url origin git@github.com-kknuths:leonardojacquier/KKNUTHS.git

echo
echo "================= COLE ESTA CHAVE NO GITHUB (Deploy keys, read-only) ================="
cat "${KEY}.pub"
echo "======================================================================================="
echo
echo "Depois de colar a chave E tornar o repo privado, teste com:"
echo "  git -C $REPO_DIR fetch origin && echo AUTO-DEPLOY OK"
