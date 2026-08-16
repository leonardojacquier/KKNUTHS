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

## Manutenção do VPS — `vps-aplicar-pendencias.sh`

```bash
ssh root@srv1555380.hstgr.cloud
cd /root/KKNUTHS && git pull
bash vps-aplicar-pendencias.sh
```

Idempotente. Cuida de duas coisas que **não** saem de um push, porque vivem fora
do repo:

**1. Matcher `@html` do Caddy.** O `path` do Caddy casa caminho exato, não
prefixo: sem o curinga `*/`, uma URL como `/ventas/apilador-electrico/` sai **sem**
`Cache-Control` e o navegador serve a versão velha — o clássico "deployei e não
mudou nada". A linha correta é:

```caddy
@html path / /index.html */ *.html
header @html Cache-Control "no-cache"
```

Três variantes furadas já apareceram neste Caddyfile, então a regra do script é
geral: **toda linha `@html path` sem `*/` é substituída**. Se o bloco do
`gnhorizons.com` não tiver matcher nenhum, ele insere as duas linhas.

**2. `/opt/gnh-autodeploy.sh`.** É uma *cópia* de `vps-autodeploy.sh`; enquanto
não for recopiada, o cron publica sem `assets/nuevo/` na raiz e as URLs limpas
quebram. O script também garante o cron de 2 min e remove entradas duplicadas.

### Proteções

- Backup do Caddyfile em `/root/Caddyfile.bak-<data>` antes de qualquer escrita.
- `caddy validate` obrigatório; se falhar, **restaura o backup e aborta sem
  reload** — o VPS é compartilhado e um reload ruim derruba todos os domínios.
- O `/etc/caddy/Caddyfile` está com **`chattr +i`** (imutável): nem root escreve,
  nem renomeia por cima, e o erro aparece como `Operation not permitted` — que
  **não** é falta de permissão. O script levanta o atributo só durante a edição e
  um `trap EXIT` o restaura mesmo se algo morrer no meio. Confira com
  `lsattr -d /etc/caddy/Caddyfile`.
- A crontab do root é compartilhada com os outros sites: é salva em
  `/root/crontab.bak-<data>` e o script aborta em vez de reescrevê-la às cegas se
  `crontab -l` falhar.

### Conferir

O script testa em **HTTPS** — na porta 80 o Caddy responde 308 redirecionando, o
que só mede o redirect e esconde os headers. Sinal de sucesso:

```
Cache-Control das subpáginas:
  HTTP/2 200
  cache-control: no-cache
```

---

## Migrar gnhorizons.com para o VPS

Objetivo: o gnhorizons.com passa a ser servido por este VPS, com o redesign na
home. Enquanto isso não for feito, **nada deste repositório aparece no
gnhorizons.com** — os scripts só publicam em `/opt/gnh` (gnh.vortex369.com.br).

### ⚠️ Os dois riscos que precisam ser respeitados

1. **110 URLs já indexadas.** O `sitemap.xml` do site atual lista 110 endereços
   (`/ventas/…`, `/fichas/*.html`, `/institucional/`, `/promo/…`). O deploy já
   publica `assets/nuevo/` na raiz justamente para que continuem respondendo.
   Se essa etapa for removida, todas viram 404 e a busca orgânica da GNH cai.
2. **E-mail.** O gnhorizons.com tem e-mail próprio (`nuevosnegocios@…`,
   `comercial@…`). Ao mexer no DNS, altere **somente** os registros `A`/`AAAA`
   do apex e o `CNAME`/`A` do `www`. **Nunca** apague ou edite `MX`, nem os
   `TXT` de SPF/DKIM/DMARC — isso derruba o e-mail da empresa.

### Ordem correta (não inverta)

**1. Publicar o conteúdo no VPS, com o domínio ainda apontando para o servidor antigo**

```bash
bash deploy-gnh.sh          # ou, no VPS: bash deploy-local.sh
ls /opt/gnh                 # tem que aparecer: ventas/ fichas/ institucional/ img/ sitemap.xml
```

**2. Adicionar o bloco no `/etc/caddy/Caddyfile`** (mantenha o bloco do
`gnh.vortex369.com.br` — ele continua útil para pré-visualizar):

```caddy
www.gnhorizons.com {
    redir https://gnhorizons.com{uri} permanent
}

gnhorizons.com {
    root * /opt/gnh
    encode gzip zstd
    file_server
    @html path *.html /
    header @html Cache-Control "no-cache"
}
```

```bash
caddy validate --config /etc/caddy/Caddyfile   # OBRIGATÓRIO — o VPS é compartilhado
systemctl reload caddy
```

**3. Conferir antes do DNS**, forçando o Host sem depender da resolução:

```bash
IP=$(hostname -I | awk '{print $1}')
for u in / /ventas/ /ventas/plataforma-articulada-y-telescopica/ \
         /institucional/ /sitemap.xml /img/logo-blanca.png; do
  printf '%s -> %s\n' "$u" "$(curl -s -o /dev/null -w '%{http_code}' \
    --resolve "gnhorizons.com:80:$IP" "http://gnhorizons.com$u")"
done
```

Todas precisam responder `200`. Se alguma der `404`, **pare** — o passo 1 não
publicou tudo. Só siga quando estiver limpo.

**4. Baixar o TTL do DNS para 300s** e esperar o TTL antigo expirar. Isso é o
que torna o rollback rápido se algo der errado.

**5. Trocar o DNS**: `A` do apex (`gnhorizons.com`) e do `www` para o IP do VPS.
Só esses. O Caddy emite o certificado HTTPS sozinho no primeiro acesso depois
que o DNS propagar (antes disso a emissão falha — é esperado).

**6. Verificar depois da propagação:**

```bash
curl -sI https://gnhorizons.com | head -3
curl -s https://gnhorizons.com/ventas/plataforma-articulada-y-telescopica/ | grep -c SZ34D
```

### Rollback

Devolver o registro `A` ao IP antigo. Como o TTL está em 300s, volta em ~5
minutos. O servidor antigo não foi tocado em nenhum momento deste processo.

### O que a migração corrige de brinde

O `canonical`, o `og:url` e os `hreflang` da página já apontam para
`https://gnhorizons.com/`. Hoje isso é um erro (o site mora em outro domínio, e
o Google é instruído a indexar a outra página). Depois da migração passam a
estar corretos, sem precisar editar nada.

## Checklist pré-deploy

- [ ] `git pull` (pegar a última versão do repo)
- [ ] `bash deploy-gnh.sh` mostrou `Deploy OK`
- [ ] `Ctrl+Shift+R` na página antes de conferir

## Depuração: "deployei e não mudou nada"

1. **A aba foi recarregada?** `Ctrl+Shift+R`.
2. **O md5 bateu?** A etapa 4 falha se divergir — se mostrou `Deploy OK`, o arquivo no ar é o seu.
3. **Vídeo antigo?** Vídeos ficam em cache — renomeie o arquivo e atualize a referência (ver "Cache").
