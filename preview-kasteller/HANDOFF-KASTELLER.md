# HANDOFF — Site Kasteller: estrutura, performance e correções

> Para usar com o SEU frontend (kastellersite_1.html ou outro).
> Aqui está tudo o que foi construído e descoberto por baixo do visual —
> o que vale a pena levar, independente de qual HTML for usado.

---

## 1. Correções MEDIDAS no efeito do hero (aplicar no seu frontend)

Estas três vieram de teste real, não de opinião — o seu arquivo de referência
tem os mesmos problemas:

### a) `scale: 2.9` NÃO cobre a tela
A célula central do grid 5×3 (165vmax de largura, gap 1,5vmax) mede ~31vmax.
Para cobrir 100vmax de viewport ela precisa de escala ≥ **3,26**.
Com 2,9 sobram barras pretas nas laterais em monitor panorâmico.
**Fix:** no GSAP, `.to("#grid", { scale: 3.4 })`.

### b) O zoom deve completar ANTES do fim do pin (payoff)
Se a escala anima de 0→100% do scrub, não existe momento de "vídeo em tela
cheia limpo". **Fix:** mapear o zoom para os primeiros ~72% da timeline e
deixar os ~28% finais só com o vídeo cheio + véu nos últimos 15%:
```js
tl.to("#grid", { scale: 3.4, ease: "none", duration: .72 }, 0)   // zoom até 72%
  .to("#veil", { opacity: .4, ease: "none" }, .85);              // véu no final
```

### c) Hero mobile: a textura com `filter` COBRE o desenho técnico
Se o hero mobile tiver textura de fundo com `filter:` (brightness etc.) e um
SVG de linework por cima, o filter cria stacking context e o SVG some.
**Fix:** ordem explícita — textura `z-index:0`, desenho `z-index:1`, conteúdo `z-index:3`.

### d) Detalhes que fazem diferença
- `end: "+=250%"` funciona, mas com o payoff use `+=250%` a `+=300%`.
- O header da referência já faz o certo: some em .5 e VOLTA em .97 — manter.
- Célula central: brilho .82 → 1.0 durante o zoom (o payoff fica "aceso").

## 2. Assets prontos no pacote (`kasteller-assets.zip`)

| Arquivo | O quê | Nota |
|---|---|---|
| `k-monograma.svg` | O K da marca **traçado do logo real** | 1 chevron + 2 cunhas; a referência usa 2 polígonos que NÃO são o K oficial |
| `kasteller-blanco.png` / `kasteller-negro.png` | Logo completo com fundo transparente | extraídos do PDF de identidade em alta |
| `fonts.css` | Cormorant Garamond (300/400) + Inter (300/400/500) em base64 | **subsetadas: 124 KB no total** (as faces completas do Google somam 399 KB) |
| `kasteller-loop.webm` | Vídeo placeholder do payoff: Ken Burns + crossfade, 9,3 s | **84 KB**, VP9; trocar pelos clipes reais |
| `og-template` (instruções § 5) | Como gerar o preview 1200×630 p/ WhatsApp/Instagram | mesma técnica usada na promo da GNH |

### O K oficial em SVG (copie e cole)
```html
<svg viewBox="0 0 113 126" fill="currentColor" aria-hidden="true">
  <path d="M50 0 H93 L43 63 L93 126 H50 L0 63 Z"/>
  <path d="M0 0 H37 L0 43 Z"/>
  <path d="M0 83 L37 126 H0 Z"/>
</svg>
```

## 3. Performance — o que foi feito e os números

| Técnica | Efeito |
|---|---|
| Fontes subsetadas aos caracteres usados (latin + ES) | 399 KB → **124 KB** |
| Cada imagem entra 1× como variável CSS (`--i-nome`) e é reusada | usar a mesma foto em N lugares não duplica bytes |
| Vídeo VP9 640×480, crf 47 | 9,3 s em **84 KB** |
| Página completa autocontida | **636 KB** com tudo dentro |
| `will-change` só no grid e na track | evita layers desnecessários |
| 1 único rAF para zoom + galeria + parallax + reveals | 1 listener de scroll passivo, sem jank |

**Para produção (com servidor):** tirar tudo de base64 → arquivos normais
(`/fonts`, `/img`, `/video`), aí a página HTML cai para ~30 KB e os assets cacheiam.
Vídeo: servir `hero.webm` (VP9) + `hero.mp4` (H.264) como no site da GNH.

## 4. Regras de robustez que valem para qualquer frontend

1. **Conteúdo visível sem JavaScript** — esconder para revelar só quando a
   classe `.js` estiver no root (`if(!reduced) root.classList.add('js')`).
2. **`prefers-reduced-motion`**: desligar pins (a seção volta a 100vh), zoom,
   parallax; pausar o vídeo no poster.
3. **Scrub, nunca eventos de wheel** — a referência já faz certo com GSAP.
   Sem GSAP, o equivalente é seção alta + `position:sticky` + progresso
   calculado de `getBoundingClientRect()`.
4. **Galeria horizontal no mobile** = swipe nativo (`overflow-x:auto` +
   `scroll-snap`), nunca pin.
5. Testar 390 / 768 / 1024 / 1440 / 1920 com
   `document.documentElement.scrollWidth > innerWidth` (pega overflow lateral).

## 5. Imagem OG para compartilhamento (fazer quando o site subir)

A arte/hero vertical corta no preview do WhatsApp/Facebook. Gerar um
1200×630: fundo = a própria imagem ampliada + blur 28 + brilho 0,45; a arte
inteira centralizada por cima. Apontar `og:image` para ela (URL absoluta).

## 6. Infra combinada (não muda com o frontend)

- **Provisório:** `gnh.vortex369.com.br/kasteller2` — pasta própria + `handle_path`
  no Caddy do VPS (⚠️ `caddy validate` antes de reload, Caddyfile é compartilhado).
- **Definitivo:** domínio próprio → `A @ 187.127.13.220` + `A www` + bloco novo
  no Caddy; HTTPS automático. Se houver e-mail no domínio, NÃO tocar em MX/mail/webmail.
- **Repositório separado** (decisão D2) com deploy por cron igual ao da GNH.
- **Analytics separado** (decisão D5): projeto Supabase próprio, mesmo esquema
  events/leads da GNH (INSERT-only via RLS), resumo diário no Telegram.

## 7. Conteúdo real já confirmado

- WhatsApp: **+595 985 869 600** · tel idem
- Instagram: `@kastellerrevestimientos`
- Facebook: `facebook.com/profile.php?id=100050328950600`
- Cidade: Ciudad del Este · endereço/horário do showroom: **a confirmar**
- Cifras (500+/80+/15): **exemplo do briefing — confirmar antes de publicar**
- Paleta oficial: `#000000` `#FFFFFF` `#E8E1D7` `#544F4B` (nada fora disso)

## 8. O que descartar sem dó

- As texturas `marmol-*.jpg` etc. — geradas por código só para compor; morrem
  quando as fotos reais chegarem.
- O HTML `kasteller-site.html` desta pasta, se o seu frontend for outro — ele
  foi o laboratório onde as correções acima foram medidas.
