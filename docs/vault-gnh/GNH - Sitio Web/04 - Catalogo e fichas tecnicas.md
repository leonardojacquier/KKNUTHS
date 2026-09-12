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
| Páginas estáticas de produto | 36 (30 de produto + 6 de categoria) |
| Fichas técnicas (HTML) | 90 |
| PDFs de ficha | 102 |
| Produtos **sem** tabela de specs | 11 |

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

## Produtos sem specs

Não têm página estática porque falta a tabela de dados do fabricante. Restam
**11** — entre eles Cortadora de Piso, Camión Grúa
(Grúa Móvil), Montacargas Todoterreno 3,5 t, Rodillo Compactador e Bulldozer.

**Para resolver:** mandar o catálogo do fabricante → vira tabela em `catalogo-data.ts`
→ página + ficha + PDF saem dos geradores.

> [!important] Onde os specs moram no bundle (armadilha)
> O bundle `assets/ventas-<hash>.js` tem **dois** lugares que definem specs:
> o campo `specs` inline de cada produto **e** um mapa `H = {"<nome>": {h,r}}`
> aplicado depois por `for(const e of o) H[e.name] && (e.specs = H[e.name])`.
> **O mapa `H` sobrescreve o inline.** Editar só o inline de um produto que já
> está em `H` não muda nada no site — foi o que aconteceu com a Carretilla
> Retráctil, que continuou mostrando a tabela CQD-A/B/J antiga depois de
> publicarmos os CQD20S/CQD25S. Ao mexer em specs, checar `H` primeiro.
>
> O link **"Ver detalles"** do card só é montado quando o produto tem `specs`
> (`const e = a.specs ? \`/ventas/${ua(a.name)}/\` : ""`). Uma página em
> `/ventas/<slug>/` sem specs no bundle fica inalcançável pelo buscador — era o
> caso da **Retroexcavadora**, corrigido em ago/2026. Hoje: 28 páginas de
> produto, 28 linkadas, zero órfãs.

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


## Setembro 2026 — lote "Parámetros del producto"

Origem: DOCX `Parámetros del producto` da fábrica, com dados soltos de vários
equipamentos que **já existiam como card no buscador, mas sem tabela**. Cada um
virou o pacote completo (specs no card + página + ficha HTML + ficha PDF + link
na categoria + sitemap).

### Mini Excavadora HT15 — três versões
O produto já tinha página com a gama SE/ST (800 kg a 6 t). O DOCX detalha as
**três versões do modelo de 1,5 t**, que compartilham chassi e geometria:

| | HT15-2 | HT15-3 | HT15-4 |
|---|---|---|---|
| Motor | Briggs & Stratton | Kepu 292 (China II) | Kubota D722 |
| Potência | 13 HP | 14 kW | 10,2 kW |
| Posto | aberto | aberto | **cabine fechada** |

Comuns às três: trem de rodagem **retrátil** 980 mm · sapata 180 mm ·
profundidade de escavação 1.850 mm · altura 2.450 mm · comandos piloto mecânicos
dos dois lados. PDF `mini-excavadora-ht15.pdf`.

### Camión Volquete de Orugas — QY-500 (0,5 t) e modelo de 1,2 t
- **QY-500:** 500 kg · gasolina 6,5 CV com partida elétrica · tração totalmente
  hidráulica · 3 km/h · rampa 35° · basculamento hidráulico 90° · 1.600 × 850 ×
  1.250 mm · chassi 1.230 × 730 mm · esteira de borracha com cabo de aço
  180 × 72 × 37 · peso 430 kg · Euro V.
- **1,2 t:** diesel monocilíndrico (China II) 7 kW · 1.200 kg · sapata 180 mm ·
  caçamba de 594 dm³ que **gira 180°** além de bascular 90° · autodescarga hidráulica.

Fotos novas recortadas do DOCX: `minidumper-qy500.jpg`, `minidumper-12t.jpg`
(+ `-thumb`). Página `/ventas/camion-volquete-de-orugas/`, PDF
`camion-volquete-orugas.pdf`.

### Máquina de Marcado Vial
Motor a gasolina Honda · 5,5 CV · avanço 15 km/h / ré 10 km/h ·
1.500 × 800 × 1.000 mm · 145 kg. Página `/ventas/maquina-de-marcado-vial/`,
PDF `maquina-marcado-vial.pdf`. Foto mantida (`marcado.png`, já publicada).

### Bomba Transportadora de Concreto
Distância horizontal 90 m · altura 25 m · pressão 10 MPa · tubulação Ø 80 mm ·
agregado ≤ 15 mm · traço recomendado 1:2:2 (cimento:areia:brita) · motor 15 kW ·
380 V · 700 kg. Página `/ventas/bomba-transportadora-de-concreto/`, PDF
`bomba-transportadora-concreto.pdf`. Foto mantida (`bomba-cemento.png`).

### Apilador CDD20-35 (novo modelo da série walkie)
2.000 kg · elevação 3.500 mm · h1 2.350 mm · h4 4.050 mm · comprimento 2.050 mm ·
largura 860 mm · garfos 1.200 × 170 × 50 mm · pernas 680 mm externo / 340 mm
interno · centro de carga 600 mm · garfo baixado a 90 mm · subida 80/130 mm/s ·
descida 110/90 mm/s · raio de giro 1.680 mm · freio eletromagnético · rodas PU
80 × 70 (dianteira) e 156 × 50 (traseira) · motor de tração 0,75 kW e de elevação
2,2 kW · bateria 24 V / 73 Ah. Entrou como 4ª coluna da tabela walkie na página,
na ficha e no PDF `apilador-cdd-d.pdf`. Foto `apilador-cdd20-35.jpg`.

### Alisadora VS836 — segunda ficha do fabricante
O DOCX traz **outra revisão** da folha da VS836 (marca VANSE, 座驾抹光机 = ride-on).
Dela aproveitamos só o que não conflita e foi somado à tabela publicada:
**8 pás** (4 por rotor), **largura de trabalho 1.900 mm**, distância entre furos
fixos **4,75″**, óleo de motor **SAE 30**, óleo da caixa redutora sintético do
fabricante e combustível **gasolina ≥ 90 octanas**.

> [!warning] A revisão nova diverge da publicada — não sobrescrita
> | | Publicado (folha anterior) | DOCX novo |
> |---|---|---|
> | Potência | 16,5 kW / 22,1 HP | 25 HP / 3.600 rpm |
> | Tanques | 19 L / 19 L | 20 L / 20 L |
> | Peso | 370 kg | 360 kg |
> | Altura | 1.300 mm | 1.350 mm |
> | Embalagem | 2.160 × 1.160 × 1.230 | 2.100 × 1.150 × 1.150 |
>
> Os valores do DOCX batem melhor com a coluna **VS836H** já publicada (25 HP,
> 20 L). Suspeita: a folha nova descreve a VS836H, ou houve revisão de projeto.
> **Nada foi alterado** — confirmar com a fábrica qual revisão vale.

> [!warning] Outras inconsistências deste lote
> - **QY-500:** a tabela do DOCX está com as colunas desalinhadas — aparece
>   "Peso = Euro V", "Emissões = Boliton" e "Motor = 3 km/h". Lendo com o
>   deslocamento de uma linha, fecha: peso 430 kg, emissões Euro V, motor Boliton.
>   Publicamos peso e emissões; **omitimos "altura máxima de elevação"** (ficou
>   sem valor) e a **marca do motor** (o DOCX diz *Runtong* num campo e *Boliton*
>   noutro).
> - **HT15-3:** "Kepu 292, 14 kW" — 292 cc a gasolina dificilmente entrega 14 kW.
>   Publicado como impresso; confirmar potência e se o motor é diesel.
> - **Máquina de marcado:** ré a 10 km/h e avanço a 15 km/h para um equipamento de
>   145 kg é alto; confirmar se são velocidades de deslocamento ou de pintura.
> - **CPC35** e **Montacargas Todoterreno 3,5 t**: o DOCX diz "já enviado ao grupo
>   de WhatsApp" / "enviar depois" — **sem dados**, seguem sem ficha.


## Regla Láser Vibratoria WS940 — qual é a nossa

Origem: folheto **VANSE**, páginas 15 e 16 (*ride-on laser leveling machine*).
O folheto traz **duas** máquinas. O card do catálogo se chama exatamente
"Regla Láser Vibratoria WS940" e usa `img/prod/ws940.png` — foto onde se lê
**WS-940** na carenagem e aparecem rodas maciças. **A nossa é a WS940.** A
WS940C entrou na página como versão superior, claramente rotulada.

| Parâmetro | **WS940 (nossa)** | WS940C |
|---|---|---|
| Largura de nivelamento | 2,5 m | **3,0 m** |
| Sistema de vibração | Motor elétrico | Hidráulica |
| Força excitadora | 2.000 N | 200–900 N (máx.) |
| Tanque de combustível | 20 L | 19 L |
| Pneus | Maciços antiderrapantes | Infláveis estreitos |
| Peso líquido | 990 kg | **835 kg** |
| Dimensões | 3.600 × 3.000 × 1.650 mm | 3.470 × 3.430 × 1.525 mm |
| Transporte | 3.350 × 2.000 × 1.890 mm | **3.600 × 960 × 910 mm** |

Iguais nas duas: motor **Honda GX690** 18,4 kW / 25 HP a gasolina, pavimentação
por rosca transportadora hidráulica, sistema antiderrapante de série, ajuste
fino rápido da altura do receptor e dois tipos de pneu.

**Só a WS940:** avanço a velocidade constante (mais precisão e menos esforço do
operador). **Só a WS940C:** corpo todo em alumínio (nivela 50 cm a mais pesando
155 kg menos), freio hidráulico e sistema de reboque, cabeçote com pouso suave,
detecção de switches e calibração de válvulas, antibloqueio dos pilares e
**compatibilidade com sistema 3D profiler** — nivela contra modelo digital, não
só contra plano laser. Dobra para 96 cm de largura no transporte.

Publicado: página `/ventas/regla-laser-vibratoria-ws940/`, ficha
`/fichas/regla-laser-ws940.html` e PDF `regla-laser-ws940.pdf`. Foto da WS940C
(`ws940c.jpg`) recortada do folheto; a `ws940.png` já publicada foi mantida.

> [!warning] Força excitadora não fecha
> A WS940C, que é o modelo superior, aparece com **200–900 N** contra **2.000 N**
> da WS940 — menos da metade. Ou a vibração hidráulica é regulável e medida de
> outra forma, ou é erro de digitação no folheto. Publicado como impresso;
> confirmar com a fábrica.


## Camión bomba de hormigón HBTS-50

Origem: PDF de uma página do fabricante, "Parámetros del camión bomba de
hormigón". Entrou **na página que já existia** de bombeo
(`/ventas/bomba-transportadora-de-concreto/`), que agora cobre duas escalas:
a bomba estacionária elétrica de 15 kW e o caminhão bomba.

**Grupo de bombeo:** vazão máxima teórica 55 m³/h · pressão máxima 16 MPa ·
alcance teórico 800 m horizontal / 200 m vertical · slump 100–230 mm · agregado
brita ≤ 40 mm e seixo ≤ 50 mm · cilindro Ø 200 × 1.050 mm · saída Ø 180 mm ·
tubo redutor Ø 180→125 · tubulação/mangueira 125 mm · tubulação de três vias ·
funil 0,8 m³ com altura de enchimento 1.400 mm · motor Cummins 93 kW (Emission
II) · bomba de óleo Kawasaki · CLP Siemens com menu em inglês e espanhol ·
conjunto 7.400 × 2.400 × 2.750 mm.

**Chassi:** motor Cummins 125 kW (Emission VI) · 2 eixos · entre-eixos 3.360 mm ·
velocidade máxima 110 km/h · peso 8.900 kg · peso com carga 11.920 kg · ano 2026.

> [!warning] Inconsistências e omissões deste PDF
> - **Unidades trocadas:** "Peso de carga (toneladas) 11920" (é kg) e "Velocidad
>   máxima de desplazamiento (kW) 110" (é km/h). Publicados corrigidos.
> - **Peso:** carga 11.920 kg > total 8.900 kg. Só fecha se 8.900 for o peso
>   vazio e 11.920 o PBT. Publicados como "peso do caminhão bomba" e "peso com
>   carga"; confirmar.
> - **Dois motores com normas distintas:** grupo de bombeo Cummins 93 kW
>   *Emission II* e chassi Cummins 125 kW *Emission VI*. Plausível (grupo próprio
>   sobre chassi novo), mas vale confirmar.
> - **"Tipo de válvula de distribución: Tragar"** — tradução literal do chinês
>   (吞). Provavelmente **válvula S**. Omitido da publicação até confirmação.
> - **"Hydraulic hose / Esfuerzo de MA"** — linha truncada no original, sem
>   valor. Omitida.
> - **"SIMENS PLC"** — erro de digitação de *Siemens*. Publicado corrigido.
> - **Sem foto** no PDF. A página usa a foto da bomba estacionária; pedir à
>   fábrica uma imagem do caminhão bomba.

> [!note] O pedido dizia "prensa"
> O arquivo enviado é do **camión bomba**, não de uma prensa. O catálogo tem
> "Ensayo a Compresión HST-YES2000" (prensa de ensaio à compressão) ainda **sem
> specs** — se era essa a intenção, falta o material dela.


## Prensa de ensayo a compresión HST-YES2000

Origem: **manual do fabricante** (Jinan Hensgrand Instrument / HST Group,
`M1907-1-EN`, 9 páginas). O card "Ensayo a Compresión HST-YES2000" já existia no
buscador sem specs e sem página — agora tem o pacote completo.

| Parâmetro | Valor |
|---|---|
| Carga máxima | 2.000 kN |
| Classe de exatidão | Classe 1 |
| Resolução mínima | 0,01 kN |
| Pratos de compressão | 220 × 250 mm (personalizável) |
| Distância vertical máx. entre pratos | 320 mm |
| Diâmetro do pistão | 250 mm |
| Curso máximo | 30 mm |
| Motor | 0,75 kW · 380 V |
| Dimensões | 880 × 370 × 1.220 mm |
| Peso líquido | 600 kg |

**Oito códigos de seção** no controlador (o operador escolhe o código e o
equipamento calcula a resistência): 1 = cubo 100 mm · 2 = cubo 150 mm (padrão) ·
3 = cubo 200 mm · 4 = não padrão (seção em cm² digitada) · 5 = flexão
150×150×550 · 6 = flexão 100×100×400 · 7 = flexão 40×40×160 · 8 = cubo 70,7 mm.

**Registro:** 500 ensaios numerados, preservados sem energia, com data e hora ·
impressão automática ao completar o grupo e reimpressão por número ·
interface **RS-232C** para exportar a um computador.

**Instalação:** sala limpa, seca, sem vibração, 0,5 m livres em volta, piso
nivelado em 0,2 mm/m · 380 V estáveis (máx. +10 %) · óleo hidráulico 15 L, N68
acima de 25 °C e N46 abaixo, troca anual (semestral com uso intensivo) ·
**verificação anual obrigatória** por organismo autorizado, com anel padrão em
10, 20, 40, 60 e 100 % da faixa.

Foto `prensa-hst-yes2000.jpg` extraída da capa do manual; a `compresion.png` já
publicada foi mantida no card. Página
`/ventas/ensayo-a-compresion-hst-yes2000/`, ficha `/fichas/prensa-hst-yes2000.html`,
PDF `prensa-hst-yes2000.pdf`, link em *Equipos de Concreto* e sitemap.

> [!note] O manual traz os códigos de calibração de fábrica
> As páginas 6 e 7 do manual publicam os códigos `66367128` (ajustar as cargas de
> calibração) e `66253681` (calibrar / autoteste do transdutor). **Não foram
> publicados no site** — mexer neles desregula a prensa, e a calibração só pode
> ser feita por pessoal habilitado. Ficam registrados aqui para o suporte.

> [!warning] Armadilha do bundle: selecionar por glob pega o órfão
> `A.glob('ventas-????????.js')` casa tanto o bundle em uso quanto o antigo
> `ventas-C7TQ2lMR.js` (também 8 caracteres), e `next()` não garante ordem — numa
> tentativa o script editou o órfão e a assertion do `index.html` barrou antes de
> estragar algo. **Selecione sempre pelo que `/ventas/index.html` referencia.**
> O órfão foi removido nesta rodada.

## Setembro 2026 — Línea de Trituración (HONSN)

Grupo novo **"Áridos y Trituración"** dentro de Equipos, entre "Movimiento de Suelo" e "Industria". Fonte: catálogo geral 2026 da HONSN (Hongxing, China), 108 páginas chinês/inglês. É o catálogo da fábrica inteira — moinhos, flotação, fornos de cimento ficaram **de fora** de propósito; entrou só a linha de agregados.

**13 cards, 13 páginas, 12 fichas HTML + PDF**, categoria `/ventas/aridos-y-trituracion/`:

| Página | Séries | Linhas de tabela | Pág. catálogo |
|---|---|---|---|
| Línea Completa de Trituración | página-mãe, 6 etapas + 3 formatos | — | 1 |
| Alimentador Vibratorio ZSW | GZD, ZSW | 14 | 86 |
| Trituradora de Mandíbulas PE | PE, PEX | 18 | 19 |
| Trituradora de Mandíbulas HJ | HJ | 9 | 16 |
| Trituradora de Cono SC | S (secundária), F (terciária) | 33 | 22–23 |
| Trituradora de Impacto PF | PF | 8 | 30 |
| Trituradora de Impacto CI | CI primária e secundária | 11 | 29 |
| Trituradora de Eje Vertical VSI7A | VSI7A | 6 | 31 |
| Criba Vibratoria HX | HX, HX-D | 27 | 91–92 |
| Cintas Transportadoras | móvil, TD | 5 + 11 | 99 |
| Planta Móvil sobre Orugas WOTETRACK | WT, ST | 19 | 1–4 |
| Planta Móvil sobre Neumáticos MTF | MTF/MTN (tabelas idênticas, só muda o prefixo) | 35 | 6–10 |
| Estación Modular KJ | KJ | 23 | 11–12 |

Ficaram fora, por não serem o núcleo da linha: HCG (giratório de mina), CJ/HDX (mandíbulas — só aparecem como "equipo principal" das plantas móveis), HPM/MP/GYS (outros cones), HVI (arenera alternativa), HSF/HST (outros alimentadores), YK/SLS/HB/LS (outras peneiras), despoeiradores. Todos têm página no catálogo; se pedirem, é acrescentar em `gen-britagem/`.

**Como foi feito e como refazer.** O texto do catálogo é vetorizado (CorelDRAW) — não extrai; as tabelas foram lidas página a página e transcritas em `gen-britagem/dados_parte1.py` e `dados_parte2.py` (cada bloco diz a página). Copy em espanhol em `contenido.py`. `python3 gen-britagem/gen_site.py` regenera tudo. Os "Ver detalles" dos cards mostram uma tabela resumida (3 colunas, até 8 modelos + link "Ver los N modelos"); a tabela completa está na página do produto e na ficha.

**Fotos: ressalva.** São os rasters embutidos no próprio catálogo, 300–450 px, ampliados para 800×600. No card ficam bem; na página de produto (560 px) saem levemente suaves. Se a HONSN mandar os renders em alta, é só trocar os arquivos em `gen-britagem/img/` e rodar de novo. Já vêm com transparência — não passaram pelo recorte de fundo.

**Não inventado:** nenhum número fora do catálogo. A capacidade "50–1.500 t/h" da página-mãe é o intervalo das plantas móveis/modulares; a linha fixa com PE 1500×1800 + SC750 chega a mais, mas isso é dimensionamento, não spec.
