# Deploy do site GNH

Guia operacional — mesmo padrão do TitanCalc.
Site (após setup): **https://gnh.vortex369.com.br**

---

## TL;DR

```bash
# na pasta do repo KKNUTHS (clonado no seu PC)
git pull
bash deploy-gnh.sh
```

Depois: `Ctrl+Shift+R` na página antes de conferir (o HTML é no-cache, mas a aba aberta roda o código velho).

---

## O que o `deploy-gnh.sh` faz

Tem `set -euo pipefail` — **para no primeiro erro**. Usa só **2 conexões SSH** (fail2ban-friendly).

| # | Etapa | Detalhe |
|---|-------|---------|
| 1 | **Gate de sanidade** | HTML íntegro + vídeos presentes. Falhou → **nada vai pro ar**. |
| 2 | **Carimba o build** | md5 (10 chars) impresso no terminal — compare depois se precisar. |
| 3 | **Envia tudo** | `tar` via pipe SSH → `/opt/gnh/` (1 conexão para HTML + assets/vídeos). |
| 4 | **index.html + md5** | `cp gnh-redesign.html index.html` no servidor e verifica md5 local×remoto. |

- `index.html` — o que a raiz do site serve. **Nunca edite** — é sobrescrito a cada deploy.
- `gnh-redesign.html` — o canônico, o que você edita.

## Cache — mais simples que o TitanCalc

O site da GNH é **um arquivo só** (CSS/JS inline no HTML). Como o HTML é servido com
`no-cache`, **não existe o problema do `?v=`** aqui. A única exceção: se trocar os
vídeos em `assets/video/`, renomeie o arquivo (ex.: `hero2.webm`) e atualize a
referência no HTML — vídeos ficam em cache no navegador.

---

## Setup único (primeira vez) — DNS + Caddy

### 1. DNS
No painel do domínio `vortex369.com.br`, crie um registro **A**:
`gnh` → mesmo IP do VPS (o de `titancalc.vortex369.com.br`).

### 2. Caddy (no VPS)

> ⚠️ **VPS COMPARTILHADO** — um reload ruim derruba **todos** os domínios.
> **Sempre** `caddy validate` antes do reload.

```bash
ssh root@srv1555380.hstgr.cloud

# adicione ao /etc/caddy/Caddyfile:
#
#   gnh.vortex369.com.br {
#       root * /opt/gnh
#       file_server
#       @html path *.html /
#       header @html Cache-Control "no-cache"
#   }

caddy validate --config /etc/caddy/Caddyfile   # OBRIGATÓRIO
systemctl reload caddy
```

O Caddy emite o certificado HTTPS sozinho na primeira visita (DNS precisa já estar propagado).

---

## Alternativa: deploy pelo GitHub (sem PC)

O repo tem `.github/workflows/deploy-vortex.yml`. Cadastre **um único secret**
(`VORTEX_SSH_KEY` = chave privada com acesso ao VPS) em
*Settings → Secrets and variables → Actions* e dispare pela aba **Actions → Run workflow**.
Host e pasta já estão preenchidos no workflow.

---

## Checklist pré-deploy

- [ ] `git pull` (pegar a última versão do repo)
- [ ] `bash deploy-gnh.sh` mostrou `Deploy OK`
- [ ] `Ctrl+Shift+R` na página antes de conferir

## Depuração: "deployei e não mudou nada"

1. **A aba foi recarregada?** `Ctrl+Shift+R`.
2. **O md5 bateu?** A etapa 4 falha se divergir — se mostrou `Deploy OK`, o arquivo no ar é o seu.
3. **Vídeo antigo?** Vídeos ficam em cache — renomeie o arquivo e atualize a referência (ver "Cache").
