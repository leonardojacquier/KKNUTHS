---
titulo: Marca e conteúdo
tags: [gnh, marca, design, conteudo]
atualizado: 2026-07-29
---

# Marca e conteúdo

[[00 - Indice|← Índice]]

## Posicionamento

> [!danger] A regra que não se negocia
> **GNH NÃO é "una importadora".**
> É um **grupo empresarial de comercio internacional** — a importação é *uma* das
> cinco frentes de serviço, não a identidade da empresa.

Essa regra vale para o site, apresentações, textos de LLM (`llms.txt`) e qualquer
material. É decisão explícita do dono.

## Idiomas

| Área | Idioma |
|---|---|
| Site (base) | **Espanhol** |
| Institucional | Espanhol + português + inglês + chinês |
| Conversa com o dono | Português |
| Código e comentários | Português / espanhol conforme o arquivo |

O público real confirma a escolha: Paraguai (18) e Brasil (12) são as duas maiores
origens ([[05 - Analytics e rastreamento]]).

## Paleta

| Cor | Hex | Uso |
|---|---|---|
| Navy / slate | `#14213D` · `#0F172A` | Base institucional, cabeçalhos |
| Royal | `#1E3A8A` | Apoio (paleta "banking") |
| **Laranja GNH** | `#F26D21` | **Reservado para CTAs** |
| Gold | `#C9A961` | Detalhe fino nas fichas |
| Verde WhatsApp | `#22C15E` | Botões de WhatsApp |
| Vermelho promo | `#E11D2E` | Selo de promoção |

**Cores de família nas fichas:** aditivos variam por família química; grúas âmbar
`#F59E0B`; plataformas azul `#3B82F6`.

## Tipografia

- **Satoshi** — títulos
- **General Sans** — corpo
- Servidas pela Fontshare (CDN)
- Fallback: `Liberation Sans`, `Helvetica Neue`, Arial — importante porque o gerador
  de PDF roda **sem rede** e usa o fallback

## Vídeo do hero

Duas fontes, nesta ordem: `hero.webm` (VP9+Opus, ~1 MB) e `hero.mp4` (H.264, ~3,8 MB).
O JS só remove o elemento quando a **última** fonte falha — aí a página cai no
desenho em gradiente. Som é mudo por padrão (política dos navegadores), com botão
para ativar.

## Imagens hotlinkadas

Alguns logos e fotos vêm de `https://gnhorizons.com/assets/...` com cadeia de
`onerror`: tenta um segundo caminho e depois cai para SVG inline (logo do nav e do
rodapé, logo giratório do About) ou se remove (marquee de clientes).

> [!important] O site nunca pode parecer quebrado
> Se o servidor de imagens estiver fora, tudo tem fallback. Manter essa disciplina
> ao adicionar imagem nova.

## Mobile

`@media (max-width: 640px)`:
- o hero **perde** `min-height:100svh` de propósito — senão o vídeo 16:9 dá zoom
  excessivo em tela retrato
- o painel do logo em "About" é limitado a 280 px

> [!tip] Ao mexer no mobile, não toque no desktop
> As regras mobile foram ajustadas caso a caso. Alterações devem ficar dentro da
> media query.

## Tom dos textos

- Direto, técnico, sem adjetivo de propaganda vazio
- Specs sempre com a fonte declarada ("datos del catálogo del fabricante")
- CTA sempre com a ação clara ("Consultar por WhatsApp", "Ver ficha completa")
- A mensagem do WhatsApp já vai escrita, com o produto no texto

## O que NÃO entra no site

- **Cimento** — decisão do dono: entra nas apresentações, mas no site não.
  Exceção: o card "Cementos y Morteros" que já existe.
- **Unificação visual** entre gateway/ventas e institucional — decidido que não.
- **I3 empresas** — fora.

---

**Ver também:** [[11 - Decisoes]] · [[01 - Arquitetura do site]]
