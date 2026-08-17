---
titulo: Deploy
tags: [gnh, deploy, operacao]
atualizado: 2026-07-29
---

# Deploy

[[00 - Indice|← Índice]]

## O caminho normal: não faça nada

> [!success] O deploy é automático
> Um cron no VPS roda **a cada 2 minutos**, detecta commit novo na branch
> `claude/professional-website-design-qqgnfg` e publica.
> **Fazer `git push` já é o deploy.** O site fica atualizado em até ~2 minutos.

```
*/2 * * * * /opt/gnh-autodeploy.sh
```

O script (`vps-autodeploy.sh` no repo) faz:

1. `git fetch` da branch — se não há commit novo, **sai em silêncio**
2. `git reset --hard` para a versão remota
3. **Gate de sanidade**: confere se o HTML está íntegro (`</html>` presente).
   Falhou → aborta e registra no log, **nada vai pro ar**
4. Copia `gnh-redesign.html` (+ como `index.html`) e a pasta `assets/` para `/opt/gnh`
5. Registra sucesso em `/var/log/gnh-autodeploy.log`

Como o Caddy serve `/opt/gnh/assets/nuevo`, é a cópia de `assets/` que publica o site novo.

## Conferir se publicou

```bash
# no VPS
tail -5 /var/log/gnh-autodeploy.log
```

No navegador: `Ctrl+Shift+R` (o HTML é no-cache, mas a aba aberta roda o código velho).

## Caminhos alternativos

| Método | Quando usar | Comando |
|---|---|---|
| **Automático (cron)** | Sempre — é o padrão | só `git push` |
| **Manual no VPS** | Cron parado, ou pressa | `bash deploy-local.sh` (de `~/KKNUTHS`) |
| **Do seu PC** | Precisa de chave SSH | `bash deploy-gnh.sh` |
| **GitHub Actions** | Só funciona se o secret `VORTEX_SSH_KEY` existir; senão passa verde sem fazer nada | automático no push |

> [!warning] fail2ban no VPS
> O servidor tem fail2ban. **Evite rajadas de ssh/scp** — os scripts foram escritos
> para usar no máximo 2 conexões justamente por isso.

## Publicar mudanças de código (o passo que se esquece)

Alterar `gnh-hero/src/*.ts` **não basta** — é preciso construir e copiar para `assets/nuevo/`:

```bash
cd gnh-hero && npm run build && cd ..

# bundles novos (os nomes têm hash — apague os velhos)
rm -f assets/nuevo/assets/*.js assets/nuevo/assets/*.css
cp gnh-hero/dist/assets/*.js gnh-hero/dist/assets/*.css assets/nuevo/assets/
cp gnh-hero/dist/index.html         assets/nuevo/index.html
cp gnh-hero/dist/ventas/index.html  assets/nuevo/ventas/index.html

# sitemap SEMPRE por último (ele lê o que existe em assets/nuevo)
node gnh-hero/tools/build-sitemap.cjs
```

> [!danger] Nunca faça `rm -rf assets/nuevo`
> As páginas de produto, as 79 fichas, os PDFs e as landings de promoção vivem **só**
> em `assets/nuevo/` — o build do Vite não as regenera. Apagar a pasta destrói tudo isso.
> Copie seletivamente, como acima.

## Regras que já causaram problema

- **Nunca editar `index.html` no servidor** — é sobrescrito a cada deploy.
- **Ao trocar vídeo ou foto, renomeie o arquivo** — estáticos ficam em cache.
- **`caddy validate` antes de qualquer reload** — o Caddyfile é compartilhado ([[02 - Infraestrutura e DNS]]).
- **O sitemap é gerado por último** — ele varre `assets/nuevo/`, então rodar antes de
  sincronizar produz um sitemap desatualizado.

## Arquivos de deploy no repositório

| Arquivo | Papel |
|---|---|
| `vps-autodeploy.sh` | O cron do VPS (fonte do que roda em `/opt/gnh-autodeploy.sh`) |
| `vps-aplicar-pendencias.sh` | Manutenção do VPS: conserta o matcher `@html` do Caddy e reinstala o auto-deploy + cron |
| `deploy-local.sh` | Deploy manual, rodado **no VPS** |
| `deploy-gnh.sh` | Deploy remoto via SSH, do PC do dono |
| `.github/workflows/deploy-vortex.yml` | Deploy por Actions (no-op sem o secret) |
| `.github/workflows/check-site.yml` | Diagnóstico manual: faz curl no site |
| `DEPLOY-GNH.md` | Guia original (⚠️ parcialmente desatualizado — descreve a fase single-file) |

---

**Ver também:** [[09 - Operacao diaria]] · [[01 - Arquitetura do site]]


## Manutenção do VPS — `vps-aplicar-pendencias.sh`

Roda **no VPS**, como root:

```bash
cd /root/KKNUTHS && git pull && bash vps-aplicar-pendencias.sh
```

É idempotente e faz, nesta ordem:

1. **Caddy** — troca toda linha `@html path` sem `*/` pela canônica e, se o bloco
   do `gnhorizons.com` não tiver matcher nenhum, insere `@html` + `header` antes
   da chave de fechamento dele. Antes de mexer faz backup em
   `/root/Caddyfile.bak-<data>`, levanta o `chattr +i` temporariamente, roda
   `caddy validate` e — se falhar — **restaura o backup e aborta sem reload**.
   Um `trap EXIT` garante que o imutável volte mesmo se o script morrer no meio.
2. **Auto-deploy** — copia `vps-autodeploy.sh` para `/opt/gnh-autodeploy.sh`,
   garante o cron de 2 min e remove entradas duplicadas. A crontab do root é
   compartilhada com os outros sites: ela é salva em `/root/crontab.bak-<data>` e
   o script aborta em vez de reescrever às cegas se `crontab -l` falhar.
3. **Conferência** — lista os blocos de site do Caddyfile e testa seis URLs em
   **HTTPS** (`--resolve` na 443). Testar na porta 80 só mede o redirect 308 para
   HTTPS e dá falso negativo, sem mostrar o `Cache-Control`.

Sinal de que está tudo certo:

```
Cache-Control das subpáginas:
  HTTP/2 200
  cache-control: no-cache
```


## O CI `check-site.yml` — o que ele sabe e o que já errou

Roda a cada push na branch e faz três coisas, nesta ordem:

1. **Sonda de alcance** (3 tentativas, 60 s entre elas). Se nenhuma completar,
   falha com uma mensagem única. Quando o fail2ban bane o IP do runner,
   **tudo** dá `000` — inclusive titancalc e umami, que não têm relação com o
   site — e do runner não dá para distinguir banimento de queda real. Nesse caso
   a instrução é abrir o site no navegador antes de agir.
2. **Espera o cron publicar** (5 tentativas, ~6 min no total). O deploy é por
   cron no VPS a cada 2 min, então logo após o push o site ainda serve o commit
   anterior. O sinal usado é o **nome do bundle** `assets/ventas-<hash>.js`, que
   muda a cada alteração por ser cacheado imutável: quando o publicado bate com
   o do repo, o deploy chegou.
3. **Conteúdo**: home do gnhorizons, redesign no vortex, página de produto e o
   header `Cache-Control: no-cache`.

> [!danger] Os dois domínios servem a MESMA raiz — `/opt/gnh`
> ```
> gnhorizons.com        -> /opt/gnh   (site OFICIAL, home = gnh-redesign.html)
> gnh.vortex369.com.br  -> /opt/gnh   (preview do dono, mesmo conteúdo)
> ```
> Em ago/2026 o CI acusou "SZ34D ausente na home do gnhorizons.com" e a leitura
> feita na hora foi errada: concluiu-se que a home antiga era intencional e isso
> chegou a ser documentado aqui. **Era bug de configuração** — o bloco do Caddy
> apontava para `/opt/gnh/assets/nuevo`. O marcador do redesign **deve** estar na
> home do gnhorizons.com; se não estiver, o root está errado. Ver
> [[02 - Infraestrutura e DNS]].
