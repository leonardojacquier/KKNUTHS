---
titulo: Catálogo e fichas técnicas
tags: [gnh, catalogo, fichas, produtos]
atualizado: 2026-07-29
---

# Catálogo e fichas técnicas

[[00 - Indice|← Índice]]

## Os números

| Item | Quantidade |
|---|---|
| Produtos no catálogo de busca | 40 |
| Páginas estáticas de produto | 26 |
| Fichas técnicas (HTML) | 79 |
| PDFs de ficha | 79 |
| Produtos **sem** tabela de specs | 20 |

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
