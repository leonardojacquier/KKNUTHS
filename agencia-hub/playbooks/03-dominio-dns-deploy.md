# 03 — Domínio, DNS e deploy

**Regra de ouro: não derrubar o e-mail do cliente.** Antes de mexer no DNS, anote todos os
registros existentes (MX, mail, webmail, cpanel, SPF/TXT, DKIM).

1. Mude **só** os registros `A` da raiz e do `www` para o servidor do site.
2. Deixe MX e os registros de e-mail como estão.
3. No Caddy (VPS da agência), um bloco por domínio. Sempre `caddy validate` antes de
   `systemctl reload caddy` — um erro derruba todos os sites do servidor.
4. HTTPS sai automático (Let's Encrypt) quando o DNS já aponta para o VPS.
5. Teste: `curl -I https://dominio/` (200 e certificado válido) e mande um e-mail de teste.

**Como a GNH e a Kasteller publicam:** cron no VPS a cada 2 minutos puxa a branch do Git e
copia os arquivos. Publicar = `git push`. Detalhes: `docs/vault-gnh/GNH - Sitio Web/03 - Deploy.md`.

**Cache:** HTML com `no-cache`. Vídeos e bundles JS ficam em cache: ao trocar, **mude o nome**
do arquivo (ex.: `ventas-<hash>.js`) e atualize a referência.
