---
titulo: Pendências e roadmap
tags: [gnh, roadmap, pendencias, todo]
atualizado: 2026-07-29
---

# Pendências e roadmap

[[00 - Indice|← Índice]]

Ordenado por **impacto**, não por esforço.

---

## 🔴 Bloqueadores — dependem do dono

### 1. Google Search Console
**Por quê:** as 109 URLs não são indexadas ativamente. Todo o SEO está pronto esperando.
**O que fazer:** criar a propriedade `https://gnhorizons.com`, copiar a metatag
`google-site-verification` e mandar. Instalação nas 3 páginas leva minutos. Depois,
enviar o sitemap.
**Depois disso:** Bing Webmaster importa do GSC com 1 clique.

### 2. Divulgar com os links UTM
**Por quê:** hoje quase todas as visitas entram "pela porta da frente", sem origem
rastreável. Sem isso não dá para saber o que traz cliente.
**O que fazer:** usar os links de [[07 - Promocoes e campanhas]] nas redes e no WhatsApp.

### 3. Confirmar dados do fornecedor
- **Plataformas:** "Altura" é altura de plataforma ou de trabalho? (~1,7 m de diferença)
- **Plataformas:** o modelo da foto `SJY0.124` é SJY0.12-4?
- **Grúa ZS-4T:** peso 3.000 kg confere? (igual à de 3 t)
- **Grúa 1,5 t:** cabeçalho trocado no PDF do fabricante
- **Curvas de carga** de 1,5 t e 4 t não vieram

---

## 🟠 Alto impacto — dá para fazer já

### 4. Sinônimos em português na busca
**Por quê:** o Brasil é o 2º maior público e há **caso documentado** de visitante que
buscou `escav` / `Pisos em Concreto`, não achou nada e foi embora.
**O que fazer:** adicionar `escavadeira`, `guindaste`, `empilhadeira`, `plataforma
elevatória`, `betoneira`, `piso de concreto`, `retroescavadeira`, `minicarregadeira`,
`argamassa` às `tags` em `catalogo-data.ts`.
**Esforço:** pequeno — só o arquivo de tags, sem tocar em layout.
**Como medir:** a linha "❗ Buscas SEM resultado" do resumo deve parar de acusar português.

### 5. Os 20 produtos sem specs
**Por quê:** cada catálogo vira página + ficha + PDF + 1 URL no sitemap.
**Faltam:** Regla Láser Vibratoria WS940, Bomba Transportadora de Concreto, Allanadora
de Concreto 1 m, Cortadora de Piso, Máquina de Marcado Vial, Central de Concreto
JBTS20, Proyectora de Revoque e outros.
**Nota:** "Proyectora de Revoque" e "Mortero de Proyección" **já apareceram nas
consultas reais** — priorizar esses.

### 6. Redirecionar `gnhorizons.com.br` → `gnhorizons.com`
Consolida autoridade de SEO num domínio só.

---

## 🟡 Melhorias

### 7. Bot do Telegram sob demanda
Comandos `/resumo`, `/ontem`, `/semana`. Código pronto em `deploy/telegram/gnh-bot.py`
+ `gnh-bot.service`, **não instalado**.
**Complicação:** o dono quer o comando no bot dele (Century). Um token = um escutador,
então é preciso **integrar no código do Century** (`/opt/agente-century`) ou conectar
como ferramenta do agente via RPC `resumen_dia`.

### 8. Captura de leads com consentimento
Discutido, nada implementado. Opções: ficha/catálogo "com porteiro" (formulário antes
do PDF) ou botão "Te llamamos".
**Contexto:** 0 leads de formulário até hoje — 100% da conversão é WhatsApp.

### 9. Enriquecer as fichas de plataforma
Dimensões, tensão, tamanho da canasta e tempo de subida estão como "Consultar".
Com as folhas de spec, as 12 fichas enriquecem de uma vez (basta editar `MODELOS`).

### 10. Análise de concorrente
Bloqueada pela política de rede do ambiente (proxy 403 em domínios externos).
Precisa de ambiente com allowlist mais permissiva, ou o dono cola os dados.

---

## ✅ Concluído recentemente

- Migração `gnhorizons.com` para o VPS, e-mails preservados
- 26 páginas de produto + 6 de categoria
- 8 fichas de grúa araña com curva de carga
- **12 fichas de plataforma com PDF e fotos reais** (28/07)
- **Landing de promoção com preview correto nas redes** (28/07)
- **Filtro anti-bot no analytics** (28/07)
- **Rastreio de rede de origem via `utm_source`** (28/07)
- Sitemap automático que varre `/promo/`

---

**Ver também:** [[06 - SEO e GEO]] · [[05 - Analytics e rastreamento]]
