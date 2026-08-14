# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository contains

Two independent deliverables coexist here — do not mix them up:

1. **TitanCalc / PavCalc** — a React + TypeScript + Vite app (`src/`) for rigid concrete pavement design (Titan Ingeniería / GNH brand). `TitanCalc.html` and `PavCalc.html` at the root are pre-built single-file exports of earlier versions; the editable source is `src/`.
2. **GNH website** — `gnh-redesign.html`, a **self-contained single-file site** (all CSS/JS inline, no build step) that redesigns gnhorizons.com. Its only external files are the hero videos in `assets/video/`. **Production serves BOTH domains from the same VPS deploy**: `gnh.vortex369.com.br` = `/opt/gnh` (redesign at `/`), and **`gnhorizons.com` = `/opt/gnh/assets/nuevo`** (the old-site tree in `assets/nuevo/` — its DNS already points to the VPS; see `deploy/caddy-gnhorizons.txt` and `docs/vault-gnh/GNH - Sitio Web/02 - Infraestrutura e DNS.md`). Every push therefore updates BOTH sites via the VPS cron (~2 min). `site-parallax.html` is an earlier standalone parallax demo (Titan-branded), kept as reference.

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
- **`gnhorizons.com` is LIVE from this repo** (root = `assets/nuevo/`). Anything added under `assets/nuevo/` publishes to gnhorizons.com on the next cron cycle. Do NOT describe the domain migration as pending.
- ⚠️ When touching Caddy config on the VPS: always `caddy validate` before `systemctl reload caddy` — a bad reload takes down every domain on the shared box.
- Cache: the HTML is served `no-cache`, and its CSS/JS are inline, so no cache-busting is needed. Videos in `assets/video/` DO cache — rename the file when replacing one.

## GNH single-file site architecture (`gnh-redesign.html`)

- **Brand tokens** in `:root`: slate `#0F172A` / royal `#1E3A8A` ("banking" palette), GNH orange `#F26D21` reserved for CTAs. Fonts: Satoshi (headings) + General Sans (body) via Fontshare.
- **Hero video**: `<video>` with two sources — `assets/video/hero.webm` (VP9+Opus, 1 MB) first, `hero.mp4` (H.264, 3.8 MB) fallback. JS removes the element only when the *last* source errors, and the page falls back to the gradient design. Sound is muted-autoplay with a toggle button (browser policy).
- **Progressive enhancement, three layers**: vanilla IntersectionObserver reveals + rAF parallax always work; GSAP/ScrollTrigger/Lenis load from CDN and, when present, disconnect the vanilla observer and take over; `prefers-reduced-motion` disables all of it.
- **Hotlinked images**: the real logos/photos are loaded from `https://gnhorizons.com/assets/...` with `onerror` chains that try a second path and then fall back to inline SVG (nav/footer logo, About spinning logo) or remove themselves (client marquee, built dynamically in JS from `client-1..14.png`). The site must never look broken if gnhorizons.com is unreachable.
- **Mobile (`@media max-width:640px`)**: the hero deliberately loses `min-height:100svh` so the 16:9 video doesn't over-zoom on portrait screens; the About logo panel is capped at 280px. Keep desktop untouched when adjusting mobile.
- The contact form posts to the existing site backend (`../api/registerenssage/` with fields `nmcontatct`, `email`, `message`) so it works when dropped onto the current server.
- SEO: title/meta/OG plus a JSON-LD `Organization` block in `<head>`. The `canonical` points to `https://gnhorizons.com/` (intended final domain).
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
