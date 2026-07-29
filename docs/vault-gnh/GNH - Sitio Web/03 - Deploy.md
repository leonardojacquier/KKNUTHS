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
| `deploy-local.sh` | Deploy manual, rodado **no VPS** |
| `deploy-gnh.sh` | Deploy remoto via SSH, do PC do dono |
| `.github/workflows/deploy-vortex.yml` | Deploy por Actions (no-op sem o secret) |
| `.github/workflows/check-site.yml` | Diagnóstico manual: faz curl no site |
| `DEPLOY-GNH.md` | Guia original (⚠️ parcialmente desatualizado — descreve a fase single-file) |

---

**Ver também:** [[09 - Operacao diaria]] · [[01 - Arquitetura do site]]
