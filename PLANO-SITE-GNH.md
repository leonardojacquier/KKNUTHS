# Plano de Execução — Site GNH "Dois Caminhos"

**Objetivo geral:** um site com dois propósitos — **Ventas** (canal B2B, Paraguai e Brasil) e
**Institucional** (novos negócios e parceiros: China, Brasil, PY) — unidos por uma entrada
cinematográfica onde o visitante escolhe seu caminho (referência: gorostiaga.com.py).

**Princípios:** visual premium com motion · leve e sem travar em qualquer dispositivo ·
downloads via links externos (nunca arquivos pesados embutidos) · Performance / SEO / Google IA
desde a fundação · captura de dados de acesso e leads.

_Última atualização: 2026-07-17._

---

## Arquitetura

```
gnh.vortex369.com.br/   (produção; migra p/ gnhorizons.com)
├── /                → ENTRADA: cortina + pórtico (escolha de caminho)
├── /ventas/         → Canal B2B  (leve, produto, conversão)
├── /institucional/  → Grupo GNH  (empresa, parceiros)
└── /assets/         → vídeos, imagens, analytics

Preview do projeto novo (Vite): /assets/nuevo/
```

Stack do projeto novo: Vite + TypeScript · Tailwind (tokens navy #14213D / navy2 #0D1626 /
orange #E87722) · GSAP + ScrollTrigger + Lenis · Space Grotesk + Inter. Pasta: `gnh-hero/`.

---

## ✅ FASE 0 — Entrada (CONCLUÍDA)

- [x] **Cortina** de abertura: branca, fecha pro centro, revela das bordas (~0.7s), reaparece a cada carga
- [x] **Gateway/pórtico**: logo GNH oficial, horizonte com "sol", wordmark, portas Ventas | Institucional, rodapé "Paraguay · Brasil"
- [x] Entrada suave da logo (scale + blur, sem "pancada")
- [x] Roteamento das duas portas + transição de saída
- [x] Mobile-first (portas empilham e centralizam), `prefers-reduced-motion`, foco de teclado
- [x] Preload (fonts + load) · componentes isolados (`curtain.ts`, `gateway.ts`, `portal.ts`)

---

## 🟠 LINHA VENTAS — canal B2B (PY + Brasil) · foco: PRODUTO

| # | Passo | Status |
|---|-------|--------|
| V1 | **Vitrine por categoria** (deck expansível): **Equipos · Aditivos · Fletes · Cemento · Morteros** | a fazer |
| V2 | **Carrossel de produtos** (scroll-snap): foto, marca, **CTA WhatsApp pré-preenchido por produto** | a fazer |
| V3 | **Fichas técnicas** (aditivos) + **catálogos** (equipos) = **download por link externo** (nunca trava) | a fazer |
| V4 | **Faixa de promoções** (editável; some quando vazia) | a fazer |
| V5 | **Formulário de cotação** curto (nome, empresa, WhatsApp, produto) → grava lead (ver Fase 6) | a fazer |
| V6 | **Performance**: Lighthouse ≥ 90 · 1ª tela < 2s em 4G · sem vídeo pesado | meta |
| V7 | **SEO + Google IA**: JSON-LD `Product`/`ItemList` + `FAQPage`, hreflang **es-PY / pt-BR**, sitemap | a fazer |

**Categorias (V1):** Equipos · Aditivos · Fletes · Cemento · Morteros.
**Insumos necessários (você):** fichas técnicas (aditivos) · catálogos (equipos) · lista de
produtos/marcas por categoria · fotos de produtos · promoções ativas.

---

## 🔵 LINHA INSTITUCIONAL — grupo e parceiros (China · Brasil · PY) · foco: EMPRESA

| # | Passo | Status |
|---|-------|--------|
| I1 | **Hero cinematográfico** (brief: máscara+blur, scroll-scrub, counters) | esqueleto pronto ✅ |
| I2 | **Quiénes somos** — quem é o Grupo GNH | a fazer |
| I3 | **Negocios del Grupo** — 4 empresas como cards **com as logos reais**: **GNH · FletePar · Rodosafra · Intonaco** | ajustar |
| I4 | **Nuestra Fortaleza**: Logística · Alianzas · Exclusividad | a fazer |
| I5 | **Carta del CEO** | a fazer |
| I6 | **Multilíngue**: ES base → PT / EN / 中文 | a fazer |
| I7 | **SEO**: JSON-LD `Organization`, Open Graph | a fazer |

---

## 🧩 ELEMENTOS COMUNS (rodapé / contato — nas duas linhas)

| # | Elemento | Detalhe |
|---|----------|---------|
| C1 | **Localización de tiendas** | **Ciudad del Este (CDE)** e **Asunción** — endereço + mapa (Google Maps embed leve ou link) |
| C2 | **Redes sociales** | **Instagram · Facebook · TikTok** (ícones no rodapé, links reais) |
| C3 | **Contacto directo** | WhatsApp flutuante + telefone + e-mail (já validados no site atual) |
| C4 | **Logos das empresas** | GNH · FletePar · Rodosafra · Intonaco — arquivos reais em `/public/img` |

**Insumos (você):** endereços das 2 lojas · links das redes (IG/FB/TikTok) · arquivos das 4 logos.

---

## 📊 FASE 6 — Analytics & Leads (opção B + C) · em paralelo com a Ventas

**Objetivo:** medir acessos, entender comportamento e capturar leads — sem depender do Google,
com os dados nas mãos da GNH.

### B) Tráfego — Umami (self-hosted no VPS)
- [ ] Instalar Umami no VPS (Docker) ao lado do site
- [ ] Sem cookies → sem banner de consentimento; leve; LGPD-friendly
- [ ] Painel: visitas, origem (país/cidade), dispositivo, páginas mais vistas
- [ ] Snippet de rastreamento nas 3 páginas (entrada, ventas, institucional)

### C) Eventos de negócio — Supabase (já conectado)
- [ ] Tabela `events` (tipo, detalhe, timestamp, sessão anônima)
- [ ] Eventos-chave: escolha de porta (Ventas/Institucional) · clique em produto · download de ficha/catálogo · clique WhatsApp
- [ ] Tabela `leads` (nome, empresa, WhatsApp, produto, origem) — alimentada pelo form V5
- [ ] Painel simples de leitura (qual porta converte mais, produtos mais procurados, leads da semana)

**Privacidade:** sem dados pessoais no tráfego (Umami é anônimo); leads só com consentimento
no formulário. Aviso de privacidade curto no rodapé.

---

## Sequência sugerida

```
FASE 0 ✅  →  LINHA VENTAS (V1–V7) + FASE 6 (B+C)  →  LINHA INSTITUCIONAL (I2,I4,I5,I6,I7)  →  QA final
```

Começar pela **Ventas** (gera receita, é a maior) com a captura de dados junto. Cada etapa
termina com verificação visual (screenshots desktop + mobile) antes de ir pro ar. Deploy
contínuo via cron do VPS já operante.

---

## Pendências de decisão

- [ ] Por qual linha começar a construção pesada — **Ventas** (recomendado) ou Institucional?
- [ ] Domínio final: gnhorizons.com? (afeta canonical/hreflang da Fase V7/I7)
- [ ] Unificar tokens: o projeto novo usa navy #14213D / Space Grotesk; o site atual usa
      slate #0F172A / Satoshi. Definir uma direção única quando promover o projeto novo à raiz.
