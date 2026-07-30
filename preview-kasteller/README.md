# Site Kasteller Revestimientos — vista previa

`kasteller-site.html` é o one-page montado a partir do briefing (referências
h-h-architects no desktop e FOR LIVING no mobile). Autocontido: fontes e imagens
em base64, porque o ambiente bloqueia CDNs e a prévia roda sob CSP estrita.

```bash
python3 build-site.py          # lê assets-site/ e escreve kasteller-site.html
```

## Estrutura

Hero preso com scroll-zoom (desktop) / textura + linework (mobile) · Manifesto com
reveal palavra por palavra e contadores · Categorías · Materiales · Proyectos (faixa
horizontal com régua) · Proceso em degraus · Showroom · Footer.

## A entrada (efeito principal)

Mosaico 5×3 de 160vmax × 110vmax começando em `scale(.62)`. A seção mede **350vh** e
o palco é **`position:sticky`** — é isso que "prende" a tela. O quanto se rolou dentro
dessa altura vira progresso 0→1 e comanda:

| progresso | o que acontece |
|---|---|
| 0 → 0,72 | grid de `scale(.62)` a `scale(3.4)`, convergindo na célula central |
| 0,05 → 0,3 | o indicador "Scroll" some |
| 0,15 → 0,55 | o conteúdo recua (`scale .92`) e faz fade |
| 0,3 → 0,65 | o VÍDEO central sobe de brilho .78 para pleno |
| 0,5 → 0,85 | o header some |
| **0,72 → 1** | **payoff: o vídeo roda em tela cheia, limpo** |
| 0,85 → 1 | véu preto sobe até 40% para a transição |

**O destino do zoom é um `<video>`** (muted, loop, playsinline, com poster) —
`assets-site/kasteller-loop.webm`, um Ken Burns de 9,3 s / 84 KB gerado por ffmpeg a
partir da foto real + texturas com crossfade, porque Pexels/Coverr estão bloqueados
neste ambiente. Trocar pelos clipes reais do showroom (aí sim 2–3 cenas de obra).
WebM/VP9 porque o Chromium do sandbox não tem H.264; no servidor real, servir
`hero.webm` + `hero.mp4` como no site da GNH.

`scale(3.4)` — e não 2,9 — porque a célula central mede 30,72vmax: abaixo de ~3,26 ela
não cobre a viewport inteira em tela panorâmica.

**Por que sticky em vez do `pin` do GSAP:** o CDN está bloqueado neste ambiente, então
o efeito foi feito em vanilla. Como o progresso vem da *posição de scroll* (e não de
eventos de wheel), trackpad, roda e toque se comportam igual e dá para voltar rolando
para cima — que é o mesmo princípio do `scrub` do ScrollTrigger.

No mobile (≤720px) o palco é ocultado: a altura extra some e entra o hero imersivo.
Com `prefers-reduced-motion` o hero volta a ter 1 tela, sem zoom.

## Identidade

Só as 4 cores oficiais: `#000000` · `#FFFFFF` · `#E8E1D7` · `#544F4B`.
Tipografia Cormorant Garamond (display) + Inter (UI), subsetadas aos caracteres
usados — 5 faces em 124 KB.

O monograma **K é SVG**, traçado a partir da geometria real do logo (um chevron
grande + duas cunhas). Usado no header, no selo do hero mobile, como marca d'água
no menu e no footer.

## O que é provisório

- **Texturas geradas por código** (`marmol-*`, `travertino`, `piedra-gris`,
  `porcelanato`, `madera`) — o Unsplash está bloqueado no ambiente. Trocar pelas
  fotos reais.
- **Cifras do manifesto** (500+/80+/15) vieram do briefing como exemplo e estão
  marcadas na página como "a confirmar". Não publicar sem checar.
- Endereço e horário do showroom.

## Notas de implementação

- GSAP/Lenis não carregam aqui (CDN bloqueado): as animações são vanilla
  (rAF para parallax e scrub, IntersectionObserver para reveals). No servidor real
  dá para sobrepor GSAP seguindo o padrão da GNH — vanilla como base, GSAP assume
  quando presente.
- Conteúdo legível sem JavaScript; `prefers-reduced-motion` desliga tudo.
- No hero mobile a ordem de empilhamento é explícita (textura 0 · desenho 1 ·
  conteúdo 3): a div de textura tem `filter` e, sem isso, cobre o desenho técnico.
