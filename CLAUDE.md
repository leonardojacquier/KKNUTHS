# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository contains

Two independent deliverables coexist here — do not mix them up:

1. **TitanCalc / PavCalc** — a React + TypeScript + Vite app (`src/`) for rigid concrete pavement design (Titan Ingeniería / GNH brand). `TitanCalc.html` and `PavCalc.html` at the root are pre-built single-file exports of earlier versions; the editable source is `src/`.
2. **GNH website** — `gnh-redesign.html`, a **self-contained single-file site** (all CSS/JS inline, no build step). Its only external files are the hero videos in `assets/video/`. `site-parallax.html` is an earlier standalone parallax demo (Titan-branded), kept as reference.

   🔴 **`gnhorizons.com` is the company's official site; `gnh.vortex369.com.br` is only the owner's preview URL.** Both are served by the same VPS deploy, but **from different roots, and that difference is deliberate**:

   | URL | Serves | Root |
   |---|---|---|
   | `gnhorizons.com/` | **commercial home** (`assets/nuevo/index.html`) — two doors: *Ventas →* and *Institucional →* | `/opt/gnh/assets/nuevo` |
   | `gnhorizons.com/institucional/` | the **institutional page**, i.e. the redesign | same |
   | `gnh.vortex369.com.br/` | `gnh-redesign.html` at `/`, as a **preview of the institutional page** | `/opt/gnh` |

   🛑 **`gnh-redesign.html` is the INSTITUTIONAL page, not the home of gnhorizons.com.** Never point `gnhorizons.com` at `/opt/gnh`: that replaces the commercial home — the page that sends visitors to the catalogue — with the institutional one. It was done once, in Aug-2026, and broke the live site until it was rolled back. The commercial home is what must stay at `gnhorizons.com/`.

   ⚠️ The repo contradicts itself here: `DEPLOY-GNH.md` § "Migrar gnhorizons.com" shows `root * /opt/gnh`, which is **stale/aspirational**. The authority is `deploy/caddy-gnhorizons.txt` (`root * /opt/gnh/assets/nuevo`) plus the live Caddyfile. When in doubt, ask the owner — do not "resolve" the contradiction by changing production.

   ▶️ **After editing `gnh-redesign.html`, run `python3 gen-institucional.py` and commit the result.** It regenerates `assets/nuevo/institucional/index.html`, which is what `gnhorizons.com/institucional/` actually serves. Without it the edit reaches the preview domain only. The script rewrites the asset paths for the deeper URL (`assets/nuevo/` → `/`, `assets/video/` and `assets/img/` → absolute, served by the Caddy `handle` blocks from `/opt/gnh`) and refuses to write if any relative `assets/` path survives.

User-facing language: the GNH site is written in **Spanish (es)**; conversation with the repo owner is in Portuguese.

## Commands

```bash
npm run dev        # Vite dev server (React calculator app)
npm run build      # tsc + vite build
npm run preview    # serve the build
```

There are no tests and no linter configured. TypeScript strict mode acts as the check (`npm run build` runs `tsc`).

## Deploy (GNH site)

Production is a shared multi-tenant VPS (`root@srv1555380.hstgr.cloud`, Hostinger) with Caddy serving `/opt/gnh` at `gnh.vortex369.com.br`. Full guide: `DEPLOY-GNH.md`.

- **On the VPS** (repo is cloned at `~/KKNUTHS` there): `bash deploy-local.sh` — pulls the branch, sanity-checks the HTML, copies `gnh-redesign.html` (+ `index.html` copy) and `assets/` to `/opt/gnh`.
- **From anywhere with SSH key**: `bash deploy-gnh.sh` (uses only 2 SSH connections — the VPS runs fail2ban; avoid bursts of ssh/scp).
- **GitHub Actions**: `.github/workflows/deploy-vortex.yml` auto-deploys on push to `claude/professional-website-design-qqgnfg` **only if** the `VORTEX_SSH_KEY` secret is set (otherwise it no-ops green). `check-site.yml` is a manual diagnostic that curls the site from a runner.
- **Never edit `index.html` on the server** — it is overwritten by every deploy (`gnh-redesign.html` is canonical).
- **`gnhorizons.com` is LIVE from this repo** (root = `assets/nuevo/`). Anything added under `assets/nuevo/` publishes to gnhorizons.com on the next cron cycle. Do NOT describe the domain migration as pending, and do NOT change that root — see the table above.
- ⚠️ When touching Caddy config on the VPS: always `caddy validate` before `systemctl reload caddy` — a bad reload takes down every domain on the shared box.
- Cache: the HTML is served `no-cache`, and its CSS/JS are inline, so no cache-busting is needed. Videos in `assets/video/` DO cache — rename the file when replacing one.

## GNH single-file site architecture (`gnh-redesign.html`)

- **Brand tokens** in `:root`: slate `#0F172A` / royal `#1E3A8A` ("banking" palette), GNH orange `#F26D21` reserved for CTAs. Fonts: Satoshi (headings) + General Sans (body) via Fontshare.
- **Hero video**: `<video>` with two sources — `assets/video/hero.webm` (VP9+Opus, 1 MB) first, `hero.mp4` (H.264, 3.8 MB) fallback. JS removes the element only when the *last* source errors, and the page falls back to the gradient design. Sound is muted-autoplay with a toggle button (browser policy).
- **Progressive enhancement, three layers**: vanilla IntersectionObserver reveals + rAF parallax always work; GSAP/ScrollTrigger/Lenis load from CDN and, when present, disconnect the vanilla observer and take over; `prefers-reduced-motion` disables all of it.
- **Hotlinked images**: the real logos/photos are loaded from `https://gnhorizons.com/assets/...` with `onerror` chains that try a second path and then fall back to inline SVG (nav/footer logo, About spinning logo) or remove themselves (client marquee, built dynamically in JS from `client-1..14.png`). The site must never look broken if gnhorizons.com is unreachable.
- **Mobile (`@media max-width:640px`)**: the hero deliberately loses `min-height:100svh` so the 16:9 video doesn't over-zoom on portrait screens; the About logo panel is capped at 280px. Keep desktop untouched when adjusting mobile.
- **Contact has no form**: the `#contacto` section is `tel:` / `mailto:` / WhatsApp / social links only. (An earlier version posted to `../api/registerenssage/`; that form no longer exists.)
- SEO: title/meta/OG plus a JSON-LD `Organization` block in `<head>`. The `canonical` points to `https://gnhorizons.com/` (intended final domain).
- **`#catalogo` section**: a deck of six collapsed panels with vertical titles that expand on hover (`.cat{flex:1}` → `.cat:hover{flex:3}`), becoming a swipe deck under 900px and a single column under 640px. **This look is the owner's choice — do not "fix" it into an open grid.** It is also the only place the partner brands appear in text (Itambé, Intonaco, Fletepar, Castelatto, Hormigomix, Camargo Química), so do not delete it either.
- 🛑 **The institutional page must NOT contain a catalogue.** The nav "Catálogo" link points to **`/ventas/`**, and product listings belong there. A `#plataformas` section with a model comparison table lived here until Aug-2026 and was removed for exactly this reason — do not add product tables, spec grids or model listings back to `gnh-redesign.html`.
- **GNH logo: no tagline.** Every *visible* GNH logo is the mark-only version — `logo-oficial-sola.png`, `logo-blanca-sola.png`, `logo-ficha-sola.png` — never the `…-oficial/blanca/ficha.png` files that carry "Generando Nuevos Horizontes" under the letters. The tagline versions stay in the repo only for `og:image` (social cards want the wordmark). The fichas embed their logo *inside* the file — base64 in `assets/nuevo/fichas/*.html`, an image XObject in `assets/nuevo/fichas/pdf/*.pdf` — so swapping a file does nothing there; run `python3 patch-fichas-html.py` and `python3 patch-fichas-pdf.py`, which rebuild the logo at the original pixel size so the layout does not move. Both are idempotent. The 276×107 logo in the `cq-*` fichas is **Camargo Química's**, not ours — never touch it.

- **Positioning rule from the owner**: GNH must NOT be described as "una importadora" — it is a *grupo empresarial de comercio internacional* (import is one of five service fronts).

## Calculator app architecture (`src/`)

- `src/calculations/` — pure domain logic (slab, subbase, subgrade, concrete, fibers, reinforcement, additives, compaction), orchestrated by `src/calculations/index.ts`. UI-free; this is where engineering formulas live.
- `src/components/` — `InputForm/` (sectioned form), `Results/` (one component per result domain), `Drawings/` (SVG cross-section and plan view), all typed via `src/types/`.
- shadcn/ui conventions are configured (`components.json`, `@/` alias → `src/`, `src/components/ui/`, `cn()` in `src/lib/utils.ts`).
- Single-file exports (like `TitanCalc.html`) are produced with `vite-plugin-singlefile`.

## Environment constraints (Claude Code on the web)

This repo is usually worked on from a sandboxed cloud session: outbound network is allowlist-only (npm/pypi/GitHub work; `gnhorizons.com`, `vortex369.com.br` and SSH port 22 are blocked) and no SSH keys exist in the sandbox. Direct deploys must therefore go through the user's terminal or GitHub Actions. The sandboxed Chromium (`/opt/pw-browsers/chromium-*`) lacks H.264 — test videos with the WebM source. A full ffmpeg is available via `pip install imageio-ffmpeg`.

## Git

Work happens on `claude/professional-website-design-qqgnfg` (GNH site) — PR #2 tracks it. The repo's default branch is `claude/concrete-pavement-calculator-ihv3y` (calculator). Push with `git push -u origin <branch>`.
