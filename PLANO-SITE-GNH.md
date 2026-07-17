# Plano de Execução — Site GNH "Dois Caminhos"

**Objetivo geral:** um site com dois propósitos claros — **Venda** (canal B2B, Paraguai e Brasil) e **Institucional** (novos negócios e parceiros: China, Brasil, PY) — unidos por uma portada de entrada onde o visitante escolhe seu caminho (referência: gorostiaga.com.py).

**Princípios:** visual premium na linha já construída (slate + royal + laranja GNH, Satoshi/General Sans, motion) · leve e sem travar em qualquer dispositivo (celular, tablet, computador) · downloads via links externos, nunca arquivos pesados embutidos · Performance / SEO / Google IA desde a fundação.

---

## Arquitetura final

```
gnh.vortex369.com.br/          (depois: gnhorizons.com)
├── /                → PORTADA — escolha de caminho (leve, ~14KB)
├── /ventas/         → Canal B2B  (NOVO: produto, conversão, performance)
├── /institucional/  → Grupo GNH  (site atual, reorientado para empresa/parceiros)
└── /assets/         → vídeos e imagens compartilhados
```

---

## ✅ Fase 0 — Portada (CONCLUÍDA)

- [x] Tela de entrada com logo GNH real (fallback SVG), anel orbital animado
- [x] Duas portas: 🟠 **Productos y Ventas** · 🔵 **Grupo GNH**
- [x] "Recordar mi elección" (localStorage; `?portada=1` reseta)
- [x] WhatsApp no rodapé · ~14KB · testada desktop e mobile
- Preview: `https://gnh.vortex369.com.br/assets/portada.html`

---

## Fase 1 — Reestruturação (1 sessão)

| # | Tarefa | Quem |
|---|--------|------|
| 1.1 | Portada assume a raiz `/` (vira o `index.html`) | Claude |
| 1.2 | Site atual move para `/institucional/` | Claude |
| 1.3 | Esqueleto de `/ventas/` no ar (evita 404) | Claude |
| 1.4 | Atualizar script de auto-deploy no VPS | **Você cola 1 comando** |
| 1.5 | Links da portada apontam pros destinos definitivos | Claude |

**Critério de aceite:** os 3 endereços no ar; auto-deploy cobrindo os três; nada quebrado no celular.

---

## Fase 2 — Canal Ventas (1–2 sessões) — a maior

Página **produto-first**, enxuta (sem vídeo pesado; hero com imagem estática leve).

- **Vitrine por categoria** (deck expansível já validado): Aditivos · Cementos y Morteros · Pisos de Concreto · Equipos y Maquinaria · Transportes
- **Carrossel de produtos** moderno (scroll-snap, sem setinhas): foto, nome, marca, **CTA WhatsApp pré-preenchido por produto**
- **Fichas técnicas (aditivos)** e **catálogos (equipos)**: botões que abrem **links externos** (Drive/servidor) — página nunca trava com PDF
- **Faixa de promoções** — bloco editável; some sozinho quando vazio
- **Formulário de cotação** curto: nome, empresa, WhatsApp, produto de interesse
- Metas: **Lighthouse ≥ 90 · primeira tela < 2s em 4G · < 300KB inicial**

**Critério de aceite:** metas de performance batidas (medidas com Lighthouse/Playwright) + fluxo de cotação testado.

---

## Fase 3 — SEO + Google IA (junto com a Fase 2)

- **JSON-LD**: `Organization` · `Product`/`ItemList` por categoria · **`FAQPage`** (perguntas reais de compradores — é o que AI Overviews/ChatGPT/Gemini citam) · `BreadcrumbList`
- **hreflang es-PY / pt-BR** (preparando versão PT para o Brasil)
- `sitemap.xml` · `robots.txt` · canonicals por página
- Títulos/descriptions únicos por página; headings semânticos; **respostas diretas no texto** (formato que motores de IA usam como fonte)
- Open Graph completo (compartilhamento bonito no WhatsApp)

---

## Fase 4 — Institucional (1 sessão)

Reorienta o site atual para **empresa e parceiros** (China, Brasil, PY):

- **Quiénes somos** — mantém e aprofunda (Carta do CEO permanece)
- **Negocios del Grupo** — frentes do grupo como cards visuais
- **Nuestra Fortaleza** — seção nova: **Logística · Alianzas · Exclusividad**
- Vídeos e motion mantidos (hero grua GNH, banda "Nuestra flota")
- Preparação multilíngue: ES base → PT / EN / 中文 (JSON de traduções, como o site antigo)

**Critério de aceite:** narrativa institucional completa sem elementos de venda direta (catálogo migra para /ventas/).

---

## Fase 5 — QA Multiplataforma + Performance

- Bateria Playwright: iPhone SE · iPhone 14 · Android comum · tablet · notebook · desktop 4K
- Teste de peso por página e de todos os downloads externos
- Checklist de acessibilidade (contraste AA, alvos 44px, teclado, reduced-motion)
- Rodada final de Lighthouse nas 3 páginas

---

## 🔑 Insumos necessários (pode enviar em paralelo)

| # | Insumo | Para |
|---|--------|------|
| 1 | Fichas técnicas dos aditivos (PDFs ou links) | Fase 2 |
| 2 | Catálogos de equipamentos (PDFs ou links) | Fase 2 |
| 3 | Lista de produtos/marcas por categoria | Fase 2 |
| 4 | Fotos reais de produtos (senão: placeholders elegantes) | Fase 2 |
| 5 | Promoções ativas (se houver) | Fase 2 |
| 6 | Confirmação do domínio final (gnhorizons.com?) | Fase 3 |

---

## Sequência proposta

```
Fase 0 ✅ → Fase 1 → Fase 2 + 3 (juntas) → Fase 4 → Fase 5
```

Cada fase termina com verificação visual (screenshots desktop + mobile) antes de ir pro ar, como temos feito. Deploy contínuo via cron do VPS já operante.

*Aguardando aprovação para iniciar a Fase 1.*
