---
titulo: Glossário
tags: [gnh, glossario, referencia]
atualizado: 2026-07-29
---

# Glossário

[[00 - Indice|← Índice]]

## Do projeto

**Gateway** — a página `/`, onde o visitante escolhe entre Ventas e Institucional.

**Porta** — o clique nessa escolha. Vira o evento `porta` com valor `ventas` ou
`institucional`.

**Ficha técnica** — página A4 com marca GNH, uma por modelo, com specs e PDF para baixar.

**Jornada** — a sequência de eventos de uma mesma sessão, mostrada no resumo diário
(ex.: `porta:ventas → 🔎 grua → 🔧 Grúa Araña → 📄 ficha → 💬 WhatsApp`).

**Código de referência (`ref`)** — 4 letras derivadas da sessão anônima, coladas na
mensagem do WhatsApp. Permite ligar a conversa à navegação sem identificar a pessoa.

**`busqueda-vacia`** — busca que não retornou resultado. O catálogo dizendo o que falta.

**Landing (evento)** — o primeiro toque da sessão. Guarda `fuso|idioma|entrada`.

**Entrada** — por onde a pessoa chegou: `gateway`, `ventas`, `institucional`, `promo`
— com sufixo da rede quando o link traz `utm_source` (`promo-instagram`).

## Técnicos

**RLS** (*Row Level Security*) — regra do Postgres/Supabase que define quem lê e
escreve cada linha. Aqui: a chave anon só insere.

**JSON-LD** — bloco de dados estruturados que descreve a página para o Google
(`Product`, `Organization`, `BreadcrumbList`).

**Open Graph (`og:`)** — metatags que definem título, descrição e imagem do card
quando o link é colado numa rede social.

**UTM** — parâmetros de URL (`?utm_source=instagram`) que identificam a origem da visita.

**Canonical** — a URL oficial de uma página, para o Google não tratar variações como
conteúdo duplicado.

**GEO** (*Generative Engine Optimization*) — ser citado por ChatGPT, Gemini e afins.
O `llms.txt` serve a isso.

**Debounce** — esperar a pessoa parar de digitar antes de registrar. A busca usa 1,6 s.

**Progressive enhancement** — construir em camadas, da mais simples à mais rica, de
modo que a falha de uma camada não derrube a página.

**Hotlink** — carregar uma imagem direto do servidor de outro domínio.

**Crawler / bot** — robô que varre o site. Aumenta o número de "visitas" sem ser gente.

**Grey cloud** (Cloudflare) — DNS sem proxy: o Cloudflare só resolve o nome, o
tráfego vai direto ao servidor.

**fail2ban** — serviço que bloqueia IPs após tentativas repetidas de conexão. Por isso
os scripts de deploy economizam conexões SSH.

## Do produto

**Grúa araña** (*spider crane*) — guindaste de esteiras com estabilizadores
independentes, que entra por acessos estreitos e iça onde um guindaste comum não chega.

**Ancho de paso** — a largura mínima por onde a máquina passa. Define se ela entra na obra.

**Curva de carga** — tabela do fabricante que mostra a capacidade real conforme o raio
de operação e o ângulo da lança. É o que define se o içamento é seguro.

**Outrigger / estabilizador** — pé de apoio que estabiliza a máquina antes de operar.

**Mástil simple / doble** (SJY / SJYL) — plataforma com uma ou duas colunas de
alumínio. Duplo sustenta mais carga e chega mais alto.

**Electro-hidráulico** — acionamento elétrico com força hidráulica. Sem emissões,
serve para trabalhar dentro de galpões e lojas.

---

**Ver também:** [[00 - Indice]]
