# Site Kasteller Revestimientos — vista previa

`kasteller-site.html` é o one-page montado a partir do briefing (referências
h-h-architects no desktop e FOR LIVING no mobile). Autocontido: fontes e imagens
em base64, porque o ambiente bloqueia CDNs e a prévia roda sob CSP estrita.

```bash
python3 build-site.py          # lê assets-site/ e escreve kasteller-site.html
```

## Estrutura

Hero (mosaico desktop / textura + linework mobile) · Manifesto com reveal palavra
por palavra e contadores · Categorías · Materiales · Proyectos (faixa horizontal com
régua) · Proceso em degraus · Showroom · Footer.

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
