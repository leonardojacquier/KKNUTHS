# GNH Hero — gateway + abertura cinematográfica

Site multi-página do Grupo GNH: **tela-pórtico** (gateway) na raiz que roteia para
`/ventas/` (hero cinematográfico do brief) ou `/institucional/` (placeholder Fase 4).
Spec do hero: `GNH-HERO-BRIEF.md` (raiz do repositório).

## Rotas

| Rota | Conteúdo | Entry |
|---|---|---|
| `/` | Gateway: logo, horizonte com "sol", wordmark, portas Ventas/Institucional | `src/portal.ts` + `src/gateway.css` |
| `/ventas/` | Hero do brief + counters + grid de empresas | `src/main.ts` |
| `/institucional/` | Placeholder (Fase 4 do plano) | `src/institucional.ts` |

Strings do gateway centralizadas em `STRINGS` (`src/portal.ts`) — trocar ES→PT é editar um objeto.
Logo real: subir `public/img/gnh-logo.svg` (até lá, placeholder "GNH" em Space Grotesk).

## Rodar

```bash
npm i
npm run dev        # http://localhost:5173
```

`npm run build` gera `dist/` (com checagem TypeScript); `npm run preview` serve o build.

## Stack

Vite + TypeScript · Tailwind (tokens GNH em `tailwind.config.js`) · GSAP + ScrollTrigger
(entrada com clip-path+blur, scrub do fundo, counters, reveals) · Lenis (smooth scroll,
glue em `src/main.ts`) · Space Grotesk + Inter via @fontsource.

## Onde mexer

| O quê | Onde |
|---|---|
| Copy do hero (título/sub/CTA) | `index.html` (seção HERO) |
| Números dos counters | `index.html` — `data-count` em cada `.counter` |
| Empresas do grid | `index.html` (seção GRID) |
| Timings da entrada / scrub | `src/hero.ts` |
| Tokens de cor/fonte | `tailwind.config.js` |

## Assets

Placeholders de gradiente marcam onde entram as imagens. Suba em `public/img/`:
`hero.webp` (fundo do hero — troque o `background` de `.hero-bg` em `src/style.css`
por `background-image`) e `card-<empresa>.webp` (grid — troque o conteúdo de `.card-media`).

## Acessibilidade / performance

Só `transform/opacity/filter` são animados; `will-change` na camada de scrub;
`prefers-reduced-motion: reduce` desliga Lenis, timelines e scrubs e mostra a versão
estática completa (via CSS, sem JS).
