---
titulo: Catálogo e fichas técnicas
tags: [gnh, catalogo, fichas, produtos]
atualizado: 2026-08-14
---

# Catálogo e fichas técnicas

[[00 - Indice|← Índice]]

## Os números

| Item | Quantidade |
|---|---|
| Produtos no catálogo de busca | 40 |
| Páginas estáticas de produto | 31 |
| Fichas técnicas (HTML) | 84 |
| PDFs de ficha | 96 |
| Produtos **sem** tabela de specs | 18 |

## As três famílias de ficha

Todas usam o **mesmo formato visual** (folha A4 com marca GNH, cabeçalho, tabelas,
rodapé com contatos). Muda só a cor da família e o conteúdo.

| Família | Gerador | Cor | Qtd |
|---|---|---|---|
| **Aditivos / químicos** | `tools/build-aditivos.py` | por família química | ~59 |
| **Grúas araña** | `tools/build-gruas.cjs` | âmbar `#F59E0B` | 8 |
| **Plataformas elevadoras** | `tools/build-plataformas.cjs` | azul `#3B82F6` | 12 |

> [!tip] O CSS é compartilhado de verdade
> `build-plataformas.cjs` **lê o CSS de dentro de `build-gruas.cjs`** em tempo de
> execução. Se alguém mudar o visual das fichas de grúa, as de plataforma acompanham
> sozinhas — não existe cópia para envelhecer. Se o CSS não for encontrado, o gerador
> falha em voz alta (não gera ficha torta em silêncio).

## Como gerar

```bash
cd gnh-hero

node tools/build-gruas.cjs          # 8 fichas de grúa
node tools/build-plataformas.cjs    # 12 fichas de plataforma
python3 tools/build-aditivos.py     # fichas químicas (lê .md de content/)

node tools/make-pdfs.cjs            # PDFs de TODAS as fichas (via Chromium)
node tools/build-productos.cjs      # páginas de produto
node tools/build-categorias.cjs     # 6 páginas de categoria
node tools/build-sitemap.cjs        # sitemap (por último!)
```

Depois é preciso copiar para `assets/nuevo/` — ver [[03 - Deploy]].

## Regra inegociável dos dados

> [!danger] Não inventar número
> Campo sem dado no catálogo do fabricante **fica fora da tabela** ou vira
> "Consultar". Uma spec errada numa ficha técnica é um problema comercial e de
> segurança — o cliente dimensiona o serviço por ela.

Toda ficha traz no rodapé: *"Datos transcritos del catálogo del fabricante. Sujetos a
cambio sin previo aviso; confirmá la configuración final con nuestro equipo técnico."*

## Grúas araña (8 modelos, série ZS)

Capacidades de **1,5 t a 16 t**. Cada ficha tem rendimento, dimensões, motorização,
**curva de carga** e diagrama dimensional do fabricante.

| Modelo | Capac. | Radio | Altura | Ancho paso | Peso |
|---|---|---|---|---|---|
| ZS-1.5T | 1,5 t | 6 m | 6,5 m | 0,65 m | 1.300 kg |
| ZS-3T | 3 t | 10,5 m | 10,8 m | 0,80 m | 3.000 kg |
| ZS-4T | 4 t | 13 m | 15 m | 1,00 m | 3.000 kg ⚠️ |
| ZS-5T | 5 t | 15 m | 17 m | 1,50 m | 6.100 kg |
| ZS-8T | 8 t | 18 m | 21 m | 1,60 m | 8.700 kg |
| ZS-10T | 10 t | 18,5 m | 19,5 m | 1,80 m | 10.500 kg |
| ZS-12T | 12 t | 19 m | 21 m | 1,83 m | 12.500 kg |
| ZS-16T | 16 t | 23 m | 25 m | 2,70 m | 16.500 kg |

> [!warning] Dois pontos a confirmar com o fornecedor
> - **Peso da ZS-4T**: o catálogo diz 3.000 kg, igual à ZS-3T — suspeito.
> - **PDF da 1,5 t**: o cabeçalho do arquivo do fabricante está trocado.
> - **Curvas de carga de 1,5 t e 4 t** não vieram nos PDFs.

## Plataformas elevadoras (12 modelos, séries SJY / SJYL)

Mástil de alumínio, acionamento electro-hidráulico, sem emissões (uso interno).

| Modelo | Mástil | Capac. | Altura | Peso | Foto real |
|---|---|---|---|---|---|
| SJY0.15-4 | Simple | 150 kg | 4 m | 230 kg | — |
| SJY0.15-6 | Simple | 150 kg | 6 m | 270 kg | — |
| SJY0.12-8 | Simple | 120 kg | 8 m | 290 kg | — |
| SJY0.1-9 | Simple | 100 kg | 9 m | 320 kg | ✅ |
| SJY0.1-10 | Simple | 100 kg | 10 m | 330 kg | ✅ |
| SJYL0.2-4 | Doble | 240 kg | 4 m | 360 kg | — |
| SJYL0.23-6 | Doble | 230 kg | 6 m | 400 kg | ✅ |
| SJYL0.23-8 | Doble | 230 kg | 8 m | 440 kg | — |
| SJYL0.23-10 | Doble | 230 kg | 10 m | 520 kg | — |
| SJYL0.22-12 | Doble | 220 kg | 12 m | 610 kg | ✅ |
| SJYL0.2-14 | Doble | 200 kg | 14 m | 670 kg | — |
| SJYL0.15-16 | Doble | 150 kg | 16 m | 750 kg | — |

> [!question] Duas questões abertas
> - **"Altura"** é o rótulo do catálogo do fabricante. Não está confirmado se é altura
>   de plataforma ou altura de trabalho — a diferença é ~1,7 m e **muda a decisão de
>   compra**. Confirmar com o fornecedor.
> - **Foto `SJY0.124`**: nome ambíguo. Pelo padrão seria **SJY0.12-4** (120 kg, 4 m),
>   modelo que não está na tabela. A outra leitura ("SJY0.1-24", 24 m) não existe em
>   mástil simples. A foto está guardada, **sem uso público**, até confirmação.

**Dimensões, tensão de alimentação e tamanho da canasta ainda não temos** — as fichas
marcam "Consultar". Se o fornecedor mandar as folhas de spec, as 12 fichas enriquecem
de uma vez só (basta editar o array `MODELOS` do gerador).

## Os 20 produtos sem specs

Não têm página estática porque falta a tabela de dados:
Regla Láser Vibratoria WS940, Bomba Transportadora de Concreto, Allanadora de Concreto
1 m, Cortadora de Piso, Máquina de Marcado Vial, Central de Concreto JBTS20,
Proyectora de Revoque, entre outros.

**Para resolver:** mandar o catálogo do fabricante → vira tabela em `catalogo-data.ts`
→ página + ficha + PDF saem dos geradores.

## A busca do catálogo

- Dispara a partir de **3 letras**, registra o termo **1,6 s depois** que a pessoa
  para de digitar (não é tecla por tecla)
- Termos com resultado → evento `busqueda`; sem resultado → `busqueda-vacia`
- Os termos aceitos por produto ficam no campo `tags` de `catalogo-data.ts`

> [!bug] Falha conhecida: busca em português
> O catálogo **não tem sinônimos em português** — nem `escavadeira`, `guindaste`,
> `empilhadeira`, `betoneira`, `andaime`. Já há registro de visitantes brasileiros
> que buscaram e não acharam nada (ver [[05 - Analytics e rastreamento]]).
> O Brasil é o segundo maior público do site. **Correção pendente** ([[10 - Pendencias e roadmap]]).

---

**Ver também:** [[01 - Arquitetura do site]] · [[09 - Operacao diaria]]


## Agosto 2026 — catálogos adicionados nesta rodada

### Plataformas de trabalho aéreo (linha ZS, 10 modelos)

- **Onde**: seção `#plataformas` da home nova (`gnh-redesign.html`) — tabelas telescópica
  (SZ20D…SZ34D) e articulada (SQ16D, SQ16, SQ22D), modal de specs por modelo, miniaturas 4:3.
- **Fichas PDF**: `fichas/pdf/plataforma-<código-comercial>.pdf` (10 arquivos), gerador
  **`gen-fichas-plataformas.py` na raiz do repo** — lê os dados do objeto `PLAT` dentro do
  próprio `gnh-redesign.html`, então site e PDF nunca divergem. Fotos por modelo em
  `img/prod/plataforma/` (recortes das páginas do catálogo do fabricante + thumbs 4:3).
- **Nomenclatura**: código comercial GNH (SZ/SQ) na frente; código de fábrica (Z\*M-LI /
  Q\*M-LI/Do) como referência. Mapeamento verificado por peso, 1:1 nos 10 modelos.
  **O sufixo "D" da linha comercial = modelo elétrico** (não diesel!) — confirmado nos dois
  pares elétrico/diesel. Confirmar com a fábrica antes de imprimir material.
- A página antiga `/ventas/plataforma-articulada-y-telescopica/` ganhou a matriz completa
  de 27 parâmetros × 7 telescópicas + colunas novas na tabela de modelos.

### Central de Concreto JBTS20 (bomba misturadora diesel)

- **Fonte**: `JBST20.docx` do fabricante (o nome do arquivo tem as letras trocadas — o
  código correto é **JBTS20**, como o site já usava).
- **Specs-chave**: 10–20 m³/h · 8 MPa · alcance 260/80 m · slump 100–230 mm · cilindro
  140/700 mm · tolva 300 L · misturador 400/200 L · Cummins diesel 75 kW @ 2.100 rpm ·
  hidráulica 280 L (Bolseen/Manuli) · 4.300×1.700×2.450 mm · 3.950 kg.
- **Onde**: card no buscador com specs embutidas + página `/ventas/central-de-concreto-jbts20/`
  + ficha `/fichas/central-concreto-jbts20.html` + PDF · seção completa em
  `/ventas/equipos-de-concreto/#jbts20` · link no card "Equipos y Maquinaria" da home nova.
- **Foto**: decisão do dono — **a amarela** (`img/prod/central-concreto.png`) em tudo.
  A foto azul de fábrica fica guardada em `img/prod/jbts20.jpg` (não usar sem pedir).

### Proyectora de Revoque M6 (lançamento GNH)

- **Fonte**: `Para_metros_de_la_ma_quina_de_proyeccio_n_de_cemento.docx`.
- **Specs-chave**: 30 L/min · projeção 40 m horiz. / 20 m vert. · 4/5,5 kW · 220/380 V ·
  tolva 115 L · árido ≤4 mm · 123×72×155 cm · 220 kg. Componentes: compressor K2 e motor
  Nord (Alemanha), bomba Sea Land e mangueira IVG (Itália), elétrica Siemens.
  Acessórios: bomba de rosca D7-2.5 (27 L/min) e compressor HANDY K2 (250 L/min, 5,5 bar).
- **Onde**: card no buscador com specs + página `/ventas/proyectora-de-revoque/` + ficha
  `/fichas/proyectora-de-revoque.html` + PDF. WhatsApp da linha: **993 366650**.
- **Foto**: `img/prod/gnh-proyectora.png` (a que já estava no site — ordem do dono de não
  trocar fotos existentes).

### O mecanismo "Ver detalles" no buscador (convenção nova)

O template `B()` do bundle de ventas sempre soube renderizar tabela de specs embutida e
link "Ver detalles" — bastava o item ter o campo `specs:{h:[...],r:[[...]]}`. O link gerado
é `/ventas/<slug(nome)>/` (slug = `ua(name)`: minúsculas, sem acento, hífens), então **a
página de produto com esse slug precisa existir**. JBTS20 e Proyectora foram os primeiros.

> [!warning] Editar o bundle exige re-hash
> `assets/ventas-<hash>.js` é imutável no cache. Ao editar: salvar com nome novo
> (`md5` 8 chars do conteúdo), apagar o antigo e atualizar a referência em
> `ventas/index.html`. Sem isso, navegadores seguram o bundle velho para sempre.

> [!note] Fichas feitas à mão nesta rodada
> As fichas da JBTS20 e da Proyectora foram escritas direto (HTML + geradores one-off),
> fora do pipeline `gnh-hero/tools/build-*.cjs`. Se o pipeline for regenerar tudo um dia,
> incorporar esses dois produtos lá — ou eles ficarão órfãos do build.

### Alisadora de Hormigón Doble — VS836 / VS836H

- **Fonte**: `ALISADORA_DE_HORMIGON.pdf` (folheto GNH com as duas máquinas já marcadas).
- **Specs-chave** (ambas Honda GX690, gasolina, 96 cm × 2, 80–150 rpm, aspa 350×150 mm,
  2.000×1.000×1.300 mm): **VS836** mecânica, 16,5 kW/22,1 HP, tanques 19+19 L, 370 kg,
  embalagem 2.160×1.160×1.230 mm · **VS836H** hidráulica, 18,4 kW/25 HP, tanques 20+20 L,
  420 kg, embalagem 2.160×1.160×1.430 mm.
- **Onde**: card do buscador (item existente "Allanadora de Concreto 1 m" ganhou `specs`
  comparativas de 3 colunas) → página `/ventas/allanadora-de-concreto-1-m/` (slug do nome
  antigo, mantido de propósito para não quebrar o link do buscador) + ficha
  `/fichas/alisadora-de-hormigon.html` + **dois PDFs** (`alisadora-vs836.pdf`,
  `alisadora-vs836h.pdf`) + item ilustrado na lista de equipos-de-concreto.
- **Fotos**: recortadas do folheto → `img/prod/alisadora-vs836.jpg` e `-vs836h.jpg`
  (+ thumbs 4:3). A foto antiga `allanadora.png` **foi mantida no card do buscador**
  (ordem do dono: não trocar fotos que já estão no site).

> [!warning] Erros no folheto do fabricante — corrigidos ao publicar
> 1. VS836H: "Potencia 1845 kW / 25 HP" → publicado **18,4 kW / 25 HP** (1845 kW é impossível).
> 2. Ambas: a linha "Velocidad de trabajo 350(L)×150(w) mm" traz na verdade o **tamanho da
>    aspa** (bate com "14 × 6 pulgadas" da linha seguinte) → publicado como aspa/cuchilla.
> 3. VS836H: linha "Diámetro del Flotador" vem **sem valor** → omitida.
> 4. VS836H: "420 kg / 916 ibs" → 420 kg são 926 lb; publicado o valor métrico.
> Confirmar os quatro pontos com a fábrica antes de imprimir material comercial.

### Equipamentos de armazém — CQD (retrátil) e CDD (apiladores)

Três catálogos do fabricante entraram de uma vez, alimentando **dois produtos que já
existiam** no buscador (nenhum item novo foi criado no catálogo):

**Carretilla Retráctil Cuatridireccional — CQD20S / CQD25S** (`CQD25S.pdf`)
- 2.000/2.500 kg · elevação 7.500 mm · avanço 650/735 mm · bateria 48 V 400/420 Ah ·
  tração 6,5 kW + elevação 8,6 kW (AC) · 7,8/8 km/h · raio 1.920/2.075 mm · 3.900/4.100 kg.
- Diferencial comercial: **quadridirecional** — gira as rodas 90° e anda de lado, movendo
  carga longa em corredor de 2,77–2,86 m. Controle **Curtis (EUA)**, hidráulica **Shimadzu**,
  bateria Donghai. Opcionais: câmera sem fio, bateria de lítio, 4 garfos, ajuste hidráulico.
- Página `/ventas/carretilla-retractil-reach-truck/` **reescrita** (antes só tinha uma tabela
  genérica) + ficha `/fichas/carretilla-retractil-cqd.html` + PDF. Foto: `img/prod/reach-cqd.jpg`.

**Apilador Eléctrico CDD — duas famílias** (`CDDD.pdf` + `CDD05C_07C_10C_07B_10B_15DH_15DK.pdf`)
- **Walkie CDD-D**: CDD15D-25 (1.500 kg/2,5 m), CDD20D-25 (2.000 kg/2,5 m), CDD20D-45
  (2.000 kg/4,5 m) · 24 V · tração 1,5 kW AC + elevação 2,2 kW · 870/880/1.370 kg.
- **Autoelevantes** (elevam a si mesmos até 1,6 m, para carga/descarga sem rampa):
  CDD05C 500 kg · CDD07C 700 kg · CDD10C 1.000 kg (série C = semielétrica) ·
  CDD07B 700 kg · CDD10B 1.000 kg (série B = full elétrica, +tração 0,8 kW, rampa 5–10 %) ·
  CDD15D 1.500 kg (tesoura, elevação 2,2 kW, **radiocontrole até 30 m**). Todos 48 V, oito
  alturas de 800 a 1.600 mm — o peso varia com a altura escolhida.
- Página **nova** `/ventas/apilador-electrico/` (o produto existia no buscador sem página) +
  ficha `/fichas/apilador-electrico.html` + **dois PDFs** (`apilador-cdd-d.pdf`,
  `apilador-autoelevante-cdd.pdf`). Fotos: `apilador-cdd-d.jpg`, `apilador-autoelevante.jpg`.

> [!warning] Inconsistências do material original (publicadas com correção ou omissão)
> - CDD15D: peso "450/**354**/460/463..." — o 354 quebra a sequência crescente; provável 454.
>   Publicada a faixa 450–480 kg sem citar o valor suspeito.
> - Séries B e D: velocidade máxima impressa com unidade **"kw/h"** (deveria ser km/h).
>   Omitida da ficha até confirmação.
> - CDD07B/CDD10B: largura total com valor único (852 mm) enquanto W1/W3 têm dois valores —
>   possível célula incompleta no original.
> - CDD05C: descida 80 mm/s, único fora do padrão 100 mm/s da família (mantido como impresso).
> - O arquivo cobre 15DH/15DK no nome, mas as páginas trazem só **CDD15D** — confirmar se
>   DH/DK são variantes de bateria (lítio/chumbo) do mesmo modelo.
> Confirmar tudo com a fábrica antes de material impresso.
