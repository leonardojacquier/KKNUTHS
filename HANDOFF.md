# HANDOFF — estado do projeto GNH (para retomar em nova sessão)

> Leia este arquivo ao iniciar uma sessão nova para continuar de onde paramos.
> Trabalho na branch `claude/professional-website-design-qqgnfg` (PR #2).
> Conversa em português; site em espanhol (base) + pt/en/zh no institucional.

## O que já está NO AR (produção)

- **Migração concluída**: `gnhorizons.com` aponta para o VPS (187.127.13.220),
  DNS via Cloudflare (grey cloud / DNS only), certificado Let's Encrypt OK.
  Emails comercial@ e nuevosnegocios@ seguem no cPanel (162.215.10.150 —
  registros mail/webmail/cpanel intactos).
- **Site**: gateway `/` + `/ventas/` + `/institucional/`. Deploy automático:
  cron do VPS `*/2 * * * * /opt/gnh-autodeploy.sh` puxa a branch e copia p/ /opt/gnh.
  Build: `cd gnh-hero && npm run build` → (da RAIZ) `rm -rf assets/nuevo &&
  cp -r gnh-hero/dist assets/nuevo` → `node gnh-hero/tools/build-institucional.cjs`.
- **Analytics**: Umami (stats.vortex369.com.br) + Supabase (projeto
  `tqvrsusrbnyahpxhnwxe`, "Base de Dados Resultado - GNH"). Tabelas events+leads,
  RLS anon INSERT-only. Função `resumen_dia(token, offset)` protegida por token
  `gnh-rsm-a91f7c2e` (só agregados, sem PII). Anon key é pública por design.
- **Rastreio de jornada**: eventos porta/product/ficha/busqueda/whatsapp/negocio/
  ceo-carta/idioma + `landing` (primeiro toque: tz|idioma|entrada). Código `ref`
  no WhatsApp liga conversa à navegação. Origem por fuso horário (função tz_pais).
- **Telegram resumo diário 20h**: `deploy/telegram/gnh-resumen-diario.py` via cron.
  Config em /opt/gnh_lib/gnh-resumen.env (BOT_TOKEN + CHAT_ID do agente-century,
  chat 6452742024). Já enviando.
- **Bot Telegram sob demanda** (/resumo /ontem /semana): `deploy/telegram/gnh-bot.py`
  + gnh-bot.service. NÃO instalado ainda — ver pendências.
- **SEO/GEO**: sitemap.xml, robots.txt, llms.txt (com termos PT), dados estruturados,
  resumo estático bilíngue em /ventas/ (dentro de #catalog, JS substitui).

## PENDÊNCIAS (próximos passos)

1. **Google Search Console** — usuário vai criar propriedade `https://gnhorizons.com`,
   pegar a metatag `google-site-verification` e mandar p/ instalar nas 3 páginas.
   Depois enviar sitemap. É o que destrava a indexação (e o Gemini).
2. **Bing Webmaster** — depois do GSC, importar de lá (1 clique, sem código).
3. **Bot /resumo no Century**: usuário quer o comando no bot dele (Century), que
   ESCUTA comandos (token 8896482814). Um token = um escutador → integrar no
   código do Century (/opt/agente-century) OU conectar como ferramenta do agente
   via RPC resumen_dia. Falta ver como o Century registra comandos/ferramentas.
4. **Páginas de produto indexáveis** (SEO por produto) — competir com concorrentes
   Wix (ex.: lumelogistica.com.py tem 1 URL por produto). Começar por Grúa Araña
   e plataformas. Base: as /fichas/ dos aditivos podem ser estendidas.
5. **Análise de concorrente** — bloqueada pela política de rede do ambiente
   (proxy 403 em domínios externos). Precisa network policy mais permissiva
   (allowlist) num ambiente novo, OU usuário cola dados/PageSpeed.
6. **Captura de nome/telefone** (leads) — discutido: só com consentimento.
   Opções: ficha/catálogo "com porteiro" (form antes do PDF), botão "Te llamamos".
   Nada implementado ainda.
7. **Filtro anti-bot** nos resumos (ignorar acessos tz nuvem/en-US diretos) — opcional.

## Decisões do dono (não revisitar)

- GNH é "grupo empresarial de comercio internacional", NUNCA "importadora".
- Sem unificação visual gateway/ventas × institucional. Sem I3 empresas.
- Cimento entra nas apresentações, mas no site NÃO ("cimento nao vamos colocar nada")
  — exceto o card "Cementos y Morteros" que já existe.
- Contatos: Kasteller +595 985 869 600 · Intonaco +595 993 366 650 /
  comercial@intonaco.com.py · WhatsApp geral GNH +595 995 360060.

## Infra / segredos (localização, não colar valores em commits)

- VPS: root@srv1555380.hstgr.cloud, Caddy multi-tenant, /etc/caddy/Caddyfile
  (SEMPRE `caddy validate` antes de reload; é compartilhado com outros domínios).
  ⚠️ Incidente conhecido: o autodeploy do poker-bot já sobrescreveu o Caddyfile
  uma vez (oneshot sslip.io). Cuidado.
- Supabase token de leitura: gnh-rsm-a91f7c2e (na função resumen_dia).
- Telegram: bot/chat do agente-century (grep TELEGRAM /opt/agente-century/.env).
