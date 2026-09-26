# PROMPT — Deploy do site Kasteller (colar no Cowork)

> Cole o bloco abaixo numa sessão nova do Cowork/Claude Code.
> **Anexe junto:** o HTML do site (o seu frontend) e a pasta de assets
> (imagens, vídeos, fontes) se houver arquivos externos.
> A sessão precisa de acesso SSH ao VPS — se não tiver, ela vai te dar os
> comandos para você rodar; isso está previsto no prompt.

---

Você vai publicar o site da **KASTELLER REVESTIMIENTOS** no nosso VPS. O site em si
já está pronto (anexo) — sua tarefa é a infraestrutura: colocar no ar, deixar o
deploy automático funcionando e verificar que ficou bom.

## 1. Onde publicar

**Provisório (agora):** `https://gnh.vortex369.com.br/kasteller2`
**Definitivo (depois):** domínio próprio da Kasteller, ainda não registrado.

Publique de forma que a migração para o domínio próprio seja só trocar o bloco do
Caddy e o `canonical` — nada de caminhos absolutos amarrados a `/kasteller2` dentro
do HTML. Use caminhos **relativos** para os assets.

## 2. Servidor

- **VPS:** `root@srv1555380.hstgr.cloud` · IP `187.127.13.220` (Hostinger)
- **Servidor web:** Caddy, `/etc/caddy/Caddyfile`
- **Pasta do site GNH (já existe, não mexer):** `/opt/gnh`
- **Pasta nova da Kasteller:** `/opt/kasteller`

⚠️ **O Caddyfile é COMPARTILHADO com outros domínios.** Um reload com erro derruba
todos os sites do servidor. Regra inegociável:

```bash
caddy validate --config /etc/caddy/Caddyfile   # SEMPRE antes
systemctl reload caddy
```

Já houve um incidente em que outro projeto sobrescreveu o Caddyfile. Antes de mexer,
faça backup: `cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak-$(date +%F)`.

⚠️ O VPS roda **fail2ban** — evite rajadas de ssh/scp. Faça em poucas conexões
(mande um tar via pipe em vez de vários scp).

### Bloco do Caddy a adicionar

O domínio `gnh.vortex369.com.br` já tem um bloco servindo `/opt/gnh`. Acrescente
dentro dele um `handle_path` para a Kasteller — **sem tocar no resto**:

```caddy
gnh.vortex369.com.br {
    # ... o que já existe, preservar ...

    handle_path /kasteller2* {
        root * /opt/kasteller
        encode gzip
        @html path / *.html
        header @html Cache-Control "no-cache"
        file_server
    }
}
```

`handle_path` remove o prefixo `/kasteller2` antes de procurar o arquivo — por isso
os caminhos dentro do HTML devem ser relativos.

## 3. Repositório e deploy automático

O site da Kasteller vai num **repositório separado** do da GNH (decisão do dono).
Crie o repo, coloque o site nele, e replique o padrão de autodeploy que já funciona
para a GNH — um cron no VPS que a cada 2 minutos verifica se há commit novo:

```bash
#!/usr/bin/env bash
# /opt/kasteller-autodeploy.sh
set -euo pipefail
REPO="/root/kasteller-site"; BRANCH="main"; DEST="/opt/kasteller"
LOG="/var/log/kasteller-autodeploy.log"

cd "$REPO"
git fetch origin "$BRANCH" -q
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/$BRANCH)" ] && exit 0
git checkout "$BRANCH" -q && git reset --hard "origin/$BRANCH" -q

# gate de sanidade: HTML íntegro antes de publicar
grep -q "</html>" index.html || { echo "$(date -u +%FT%TZ) ERRO: HTML truncado" >> "$LOG"; exit 1; }

mkdir -p "$DEST"
rsync -a --delete ./public/ "$DEST/"    # ajuste a pasta de origem conforme o projeto
echo "$(date -u +%FT%TZ) deploy OK $(git rev-parse --short HEAD)" >> "$LOG"
```

Instalar com:
```bash
chmod +x /opt/kasteller-autodeploy.sh
( crontab -l 2>/dev/null | grep -v kasteller-autodeploy ; \
  echo "*/2 * * * * /opt/kasteller-autodeploy.sh >/dev/null 2>&1" ) | crontab -
```

## 4. Antes de publicar, aplique estas correções no HTML

Foram **medidas em teste**, não são opinião:

1. **Se o hero tem zoom com `scale: 2.9`, troque para `3.4`.** A célula central do
   grid 5×3 mede ~31vmax; abaixo de 3,26 ela não cobre a viewport e sobram barras
   pretas nas laterais em monitor panorâmico.
2. **O zoom deve completar em ~72% da timeline**, não em 100% — senão não existe o
   momento de "vídeo em tela cheia limpo". O véu preto entra só nos últimos 15%.
3. **No hero mobile**, se houver textura de fundo com `filter:` e um SVG de linework
   por cima, defina a ordem explicitamente (textura `z-index:0`, desenho `1`,
   conteúdo `3`) — o `filter` cria stacking context e engole o SVG.

## 5. Performance — fazer antes de subir

- **Fontes:** subsetar aos caracteres usados (latin + acentos ES). No nosso teste
  isso levou Cormorant Garamond + Inter de 399 KB para **124 KB**. Use `fonttools`
  (`pyftsubset`) e sirva woff2 com `font-display: swap`.
- **Imagens:** converter para WebP/AVIF com fallback, `loading="lazy"` abaixo da
  dobra, `width`/`height` explícitos para não pular layout.
- **Vídeo:** servir **dois formatos** — `.webm` (VP9) e `.mp4` (H.264) — com `poster`,
  `muted loop playsinline`. Sem os dois, quebra em algum navegador.
- **Cache:** HTML `no-cache` (já está no bloco do Caddy); imagens e vídeos cacheiam,
  então **ao trocar um asset, renomeie o arquivo** em vez de sobrescrever.
- Meta de Lighthouse: **> 85** em Performance mesmo com as animações.

## 6. SEO e compartilhamento

- `<title>`, `meta description`, `canonical`
- **Open Graph com imagem 1200×630** — a arte vertical corta no preview do WhatsApp
  e do Facebook. Se só houver imagem vertical, gere a OG assim: fundo = a própria
  imagem ampliada + blur + brilho reduzido, com a arte inteira centralizada por cima.
  `og:image` precisa de **URL absoluta**.
- JSON-LD `LocalBusiness` (é uma loja física com showroom)
- `robots.txt` + `sitemap.xml`
- Enquanto estiver no endereço provisório, use `<meta name="robots" content="noindex">`
  para o Google não indexar `/kasteller2` — **lembre de remover** ao migrar para o
  domínio próprio.

## 7. Verificação (obrigatória antes de me dizer que terminou)

Rode e me mostre os resultados:

- [ ] `curl -sS -o /dev/null -w "%{http_code}" https://gnh.vortex369.com.br/kasteller2/` → 200
- [ ] Certificado HTTPS válido
- [ ] Abrir em **390, 768, 1024, 1440 e 1920 px** e checar overflow lateral com
      `document.documentElement.scrollWidth > innerWidth`
- [ ] Console sem erros de JS
- [ ] Vídeo do hero realmente tocando (`!video.paused`), não só com poster
- [ ] `prefers-reduced-motion` desativa pins/parallax e pausa o vídeo
- [ ] Testar com JavaScript desligado — o conteúdo continua legível
- [ ] `tail /var/log/kasteller-autodeploy.log` mostrando deploy OK
- [ ] Fazer um commit de teste e confirmar que sobe sozinho em até 2 min
- [ ] O site da GNH (`gnhorizons.com` e `gnh.vortex369.com.br`) continua no ar

## 8. Dados reais da Kasteller

- WhatsApp / telefone: **+595 985 869 600**
- Instagram: `@kastellerrevestimientos`
- Facebook: `facebook.com/profile.php?id=100050328950600`
- Cidade: Ciudad del Este, Paraguay — **endereço e horário do showroom: a confirmar**
- Paleta oficial (não inventar cor): `#000000` `#FFFFFF` `#E8E1D7` `#544F4B`
- Idioma do site: **espanhol**

⚠️ Se o site trouxer números tipo "500+ proyectos / 80+ marcas / 15 años": são
**exemplo de briefing, não confirmados**. Não publique como fato — ou remova, ou
marque como a confirmar, até o dono validar.

## 9. Não faça

- Não toque em `/opt/gnh` nem nos blocos de outros domínios do Caddyfile
- Não faça `systemctl restart caddy` — use `reload`, e só depois do `validate`
- Não mexa em registros DNS de e-mail (MX, mail, webmail, cpanel) de domínio nenhum
- Não invente conteúdo, endereço, horário ou números da empresa
- Não comite segredo nenhum no repositório

## 10. No fim, me entregue

1. A URL funcionando
2. O bloco do Caddy que você adicionou (para eu guardar no repo)
3. O que precisa ser feito quando o domínio próprio for registrado
4. O que ficou pendente
