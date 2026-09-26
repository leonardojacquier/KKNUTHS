# BUSCADOR DE PRODUCTOS KASTELLER — integração no projeto

> Módulo independente e namespaced (`.kb-*` / `#buscador`). Não altera
> nem depende de nada do restante da página além das fontes já carregadas.

## O que é
Busca inteligente do catálogo multi-marcas (Roca, Ceusa, Incepa, Castelli,
Castelatto, Portinari, Pasinato): uma única barra de pesquisa que filtra os
produtos **enquanto o cliente digita** — sem navegar página a página.
Insensível a acentos, vários termos combinam em E ("marmol 120 negro"),
sugestões de tags agrupadas por faceta (Marca / Tipo / Visual / Acabado /
Formato / Uso) que viram chips de filtro clicáveis, grid com entrada suave,
"ver más" progressivo e estado vazio com CTA de WhatsApp.
Se o site tiver o analytics `KT` (Supabase), o módulo registra sozinho:
`busqueda`, `busqueda-vacia`, `filtro`, `producto`. Sem `KT`, silêncio.

## PROMPT para colar no Claude Code (faça SOMENTE isto)
------------------------------------------------------------------
Adicione ao projeto o módulo de buscador contido na pasta `buscador/`
SEM ALTERAR NENHUM outro trecho de código, estilo ou comportamento
existente. Passos exatos:
1. Copie a pasta `buscador/` (css, js, productos.json) para a raiz do site.
2. No `<head>`, adicione:
   <link rel="stylesheet" href="buscador/kasteller-buscador.css">
3. Antes de `</body>` (depois dos scripts existentes), adicione:
   <script defer src="buscador/kasteller-buscador.js"></script>
4. Cole o conteúdo de `buscador/section-buscador.html` como uma nova
   `<section>` logo APÓS a seção `#categorias` (ou onde o Leo indicar).
5. Adicione um link "Catálogo" no menu apontando para `#buscador`.
Não modifique o hero, animações, tracking, ou qualquer outra seção.
------------------------------------------------------------------

## Dados
- `buscador/productos.json` já vem com uma SEMENTE real (24 itens colhidos
  dos sites oficiais: Roca com fotos do banco oficial, Ceusa com CDN da
  fábrica, séries Incepa e coleções Castelli).
- Catálogo completo: rode o raspador (pasta `scraper/`) numa máquina com
  internet (o Claude Code faz isso):
      cd scraper
      pip install -r requirements.txt
      playwright install chromium
      python scrape.py --site all --out ../buscador/productos.json --merge
  Sites e método já mapeados em reconhecimento real:
  ceusa/incepa = requests (rápido) · roca/castelli/castelatto/portinari/
  pasinato = Playwright (têm anti-bot/renderização JS).
- O tageamento é automático (`tagger.py`): look (mármol/piedra/madera/...),
  acabado (polido/mate/...), cor, formato NNxNN, tipo e usos saem do nome.
  Revise/enriqueça tags à mão no JSON quando quiser — o buscador só lê o JSON.

## Fotos: links ou download? (decisão de performance)
O JSON semente aponta para as URLs originais (Drive/CDNs das fábricas) —
funciona de imediato, bom para desenvolvimento. Para PRODUÇÃO, rode:
    python optimizar_imagenes.py --json ../buscador/productos.json
Isso baixa cada foto, corta na proporção do card, converte para WebP de
~40-60 KB e reescreve o JSON para servir do NOSSO domínio (`buscador/img/`).
Por quê: hotlink depende de 7 servidores de terceiros (lento e frágil —
quebra quando a fábrica reorganiza o site); baixado, o grid carrega
instantâneo do Caddy com cache, formato uniforme (design consistente).
500 produtos ≈ 25 MB. A URL original fica guardada em `img_origen`.
Fluxo completo: scrape.py → optimizar_imagenes.py → subir buscador/ no deploy.

## Formato de um produto
{"id","nombre","marca","linea","tipo","look","acabado","formato",
 "usos":[],"tags":[],"img","url"}
`img: null` mostra um tile elegante com o nome (sem quebrar o layout).

## Teste local
Abra `demo.html` no navegador: é a seção isolada com os dados embutidos.
Digite "marmol", "120", "madera", "roca", "cocina"…
