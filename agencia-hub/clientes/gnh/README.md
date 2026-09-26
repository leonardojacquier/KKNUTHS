# GNH — Grupo GNH

- **Site oficial:** https://gnhorizons.com (comercial `/`, catálogo `/ventas/`, institucional `/institucional/`)
- **Prévia do dono:** gnh.vortex369.com.br (só desenvolvimento)
- **Código:** raiz do repositório KKNUTHS. Regras obrigatórias no `CLAUDE.md` da raiz.
- **Documentação completa:** `../../../docs/vault-gnh/GNH - Sitio Web/` (00 - Indice é o mapa)
- **Deploy:** automático. `git push` na branch `claude/professional-website-design-qqgnfg`,
  o VPS puxa a cada 2 minutos.

## Marca (resumo)
- Posicionamento: *grupo empresarial de comercio internacional*. **Nunca** "una importadora".
- Cores: slate `#0F172A`, royal `#1E3A8A`, laranja `#F26D21` só para CTA.
- Logo: sempre a versão **sem slogan** (`logo-*-sola.png`).
- Site em espanhol (voseo), conversa com o dono em português.

## O que já existe
- Catálogo de vendas com busca, cards, páginas de produto e fichas HTML+PDF.
- Linhas geradas por script: trituração (`gen-britagem/`) e minicarregadeiras (`gen-minicargadoras/`).
- Aditivos Camargo Química (fichas a partir do Drive), plataformas, gruas, equipamentos de obra.
- Analytics (Umami + Supabase), resumo diário no Telegram.

## Decisões importantes
Ver `docs/vault-gnh/GNH - Sitio Web/11 - Decisoes.md`. Destaques recentes:
- Fotos de produto em fundo branco com moldura **cinza** (o dourado foi recusado).
- Sem comparativo com equipamentos de outras marcas.
- O institucional não tem catálogo; produtos só em `/ventas/`.
