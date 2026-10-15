---
titulo: Mapa de informação técnica dos produtos
tags: [gnh, catalogo, fichas, pendencias]
atualizado: 2026-10-11
---

# Mapa de informação técnica dos produtos

> Levantamento de 2026-10-11 sobre o catálogo publicado (`assets/nuevo/assets/ventas-31a4a23a.js`, páginas em `/ventas/` e fichas em `/fichas/`). Cada produto foi cruzado com: tabela de especificações no card, página própria com tabela, ficha HTML e PDF.

## Resumo

| Situação | Equipamentos e morteros | Aditivos | Total |
|---|---|---|---|
| ✅ Completo (tabela + ficha PDF) | 46 | 55 | 101 |
| 🟡 Tem dados, falta ficha PDF | 17 | — | 17 |
| 🟠 Ficha com tabela de dados vazia ou quebrada | — | 4 | 4 |
| 🔴 Sem nenhuma informação técnica | 9 | 5 | 14 |
| **Total** | **72** | **64** | **136** |

Não entram na conta as páginas de linha (Línea de Minicargadoras, Línea Completa de Trituración) e a de Implementos, que são índices; o catálogo do fabricante não traz especificação por implemento.

## 🔴 Sem nenhuma informação técnica

Nem tabela no card, nem página, nem ficha. O cliente só vê nome, foto e uma frase.

| Produto | Grupo | Marca | O que aparece hoje | Fonte a pedir |
|---|---|---|---|---|
| Montacargas Todoterreno 3,5 t | Movimentación | — | Só o nome e "para superficies difíciles". Sem marca, sem página. | catálogo do fornecedor |
| Camión Grúa (Grúa Móvil) | Movimentación | ZS | Card diz "Capacidades a consultar". | catálogo ZS (Jinan Zhishen) |
| Rodillo Compactador | Movimiento de Suelo | ZS | Só descrição genérica. | catálogo ZS (Jinan Zhishen) |
| Bulldozer | Movimiento de Suelo | ZS | Só descrição genérica. | catálogo ZS (Jinan Zhishen) |
| Motor Diésel 4HZD | Industria | — | Só descrição genérica. Sem marca. | catálogo do fornecedor |
| Mortero Estructural 30 kg | Morteros | Hormigomix | Sem resistência, consumo nem rendimento. Fonte: ficha Hormigomix. | ficha técnica Hormigomix |
| Mortero de Proyección 30 kg | Morteros | Hormigomix | Idem. | ficha técnica Hormigomix |
| Mortero Adhesivo AC-1 20 kg | Morteros | Hormigomix | Sem norma, tempo em aberto, consumo. | ficha técnica Hormigomix |
| Mortero Adhesivo AC-3 20 kg | Morteros | Hormigomix | Idem; o card cita "placas de más de 60×60 cm". | ficha técnica Hormigomix |
| Maturix — Monitoreo de curado | Aditivos · Especialidades | Camargo Química | Só descrição, sem ficha (o card não oferece PDF). | ficha técnica Camargo Química |
| CQ Macro Fiber Twisted 54 | Aditivos · Fibras | Camargo Química | Só descrição, sem ficha (o card não oferece PDF). | ficha técnica Camargo Química |
| CQ Seal Argamassas Poliméricas | Aditivos · Impermeabilizantes | Camargo Química | Só descrição, sem ficha (o card não oferece PDF). | ficha técnica Camargo Química |
| CQ Air Flow 9040 | Aditivos · Plastificantes | Camargo Química | Só descrição, sem ficha (o card não oferece PDF). | ficha técnica Camargo Química |
| CQ Flow Ultratech 90 | Aditivos · Plastificantes | Camargo Química | Só descrição, sem ficha (o card não oferece PDF). | ficha técnica Camargo Química |

Observações:
- **CQ Flow Ultratech 90**: existe no repositório a fonte de um "CQ Flow Ultratech" (concreto UHPC, `gnh-hero/content/fichas/cq-flow-ultratech.md`). Confirmar com a Camargo se é o mesmo produto antes de gerar a ficha.
- **Maturix** é um sistema de sensores de cura, não um aditivo: a ficha é do fabricante do sensor.

## 🟠 Aditivos com ficha, mas a tabela "Datos técnicos" vazia ou quebrada

A ficha existe e tem PDF, mas a tabela de dados saiu vazia ou com 1–2 linhas porque o texto do PDF original veio desalinhado (mesmo problema já corrigido no Acryltop).

| Aditivo | Família | Linhas na tabela | Situação da fonte |
|---|---|---|---|
| CQ ACCELERA PM SUPER | Aceleradores y retardadores | 2 | Revisar a fonte `cq-accelera-pm-super.md`. |
| CQ Fiber 54 Plus | Fibras | 0 | Revisar a fonte `cq-fiber-54-plus.md`. |
| CQ Green Seal | Impermeabilizantes | 2 | Duas fontes (`cq-green-seal-ficha-tecnica*.md`); revisar qual está completa. |
| CQ Robust 79 | Plastificantes | 0 | A fonte (`cq-robust-79.md`) tem densidade 1,07–1,10, pH 5,0–7,0 e dose 0,2–1,5 % s.p.c.: dá para corrigir sem pedir nada. |

## 🟡 Têm dados, mas falta a ficha técnica em PDF

A tabela aparece no card e na página, mas o vendedor não tem PDF para mandar no WhatsApp.

| Produto | Grupo | Linhas na tabela do card | Observação |
|---|---|---|---|
| Cortadora de Piso | Construcción | 6 |  |
| Montacargas Diésel 2 a 5 t | Movimentación | 8 |  |
| Transpaleta Eléctrica | Movimentación | 15 |  |
| Montacargas Trilateral | Movimentación | 4 | só modelo, carga, elevação e peso |
| Manipulador Telescópico | Movimentación | 4 | |
| Montacargas Eléctrico | Movimentación | 7 |  |
| Grúa sobre Camión | Movimentación | 11 |  |
| Plataforma Tijera Autopropulsada | Plataformas de Elevación | 10 |  |
| Plataforma Tijera de Orugas | Plataformas de Elevación | 6 | |
| Plataforma Articulada y Telescópica | Plataformas de Elevación | 10 |  |
| Plataforma Tijera con Estabilizadores | Plataformas de Elevación | 27 |  |
| Plataforma sobre Triciclo Eléctrico | Plataformas de Elevación | 5 | só modelo, capacidade, altura e peso |
| Retroexcavadora | Movimiento de Suelo | 7 |  |
| Hincadora de Pilotes | Movimiento de Suelo | 7 |  |
| Perforadora para Taludes | Movimiento de Suelo | 10 |  |
| Grupo Electrógeno Diésel 38 kVA | Industria | 31 |  |
| Cortacésped a Control Remoto | Industria | 6 | só versão, largura de corte e motor |

## ⚠️ Inconsistência encontrada

- **Carretilla Retráctil (Reach Truck)**: a tabela do card mistura os modelos **CSD10, CSD15 e CSD30-150**, que são os mesmos da **Montacargas Trilateral**, com os CQD20S/CQD25S da própria retráctil. A página da retráctil mostra só CQD20S/CQD25S. Conferir no catálogo ZS e tirar os CSD do card da retráctil.

## ✅ Completos

- **Construcción** (7): Regla Láser Vibratoria WS940, Bomba Transportadora de Concreto, Allanadora de Concreto 1 m, Mezcladora de Mortero N50, Máquina de Marcado Vial, Central de Concreto JBTS20, Proyectora de Revoque
- **Movimentación** (6): Grúa Araña, Mini Excavadora HT15, Camión Volquete de Orugas, Apilador Eléctrico, Plataforma de Mástil de Aluminio, Carretilla Retráctil (Reach Truck)
- **Minicargadoras** (20): Minicargadora HY320T, Minicargadora HYS360, Minicargadora HY380T, Minicargadora HYS380, Minicargadora HYS382T, Minicargadora HYSL390, Minicargadora HY-T470, Minicargadora HYS530, Minicargadora HYS530T, Minicargadora HY-V1000, Minicargadora HYS25, Minicargadora HYS35, Minicargadora HYS45, Minicargadora HYS50, Minicargadora HYS60, Minicargadora HYS65, Minicargadora HYS75, Minicargadora HYS100, Minicargadora HYS120, Minicargadora HYS125
- **Áridos y Trituración** (12): Alimentador Vibratorio ZSW, Trituradora de Mandíbulas PE, Trituradora de Mandíbulas HJ, Trituradora de Cono SC, Trituradora de Impacto PF, Trituradora de Impacto CI, Trituradora de Eje Vertical VSI7A, Criba Vibratoria HX, Cintas Transportadoras, Planta Móvil sobre Orugas WOTETRACK, Planta Móvil sobre Neumáticos MTF, Estación Modular KJ
- **Industria** (1): Ensayo a Compresión HST-YES2000
- **Aditivos** (55): Aceleradores y retardadores (4) · Cura del concreto (2) · Desmoldantes (5) · Especialidades (3) · Fibras (2) · Impermeabilizantes (2) · Limpieza y removedores (2) · Pigmentos (2) · Pisos industriales (6) · Plastificantes (24) · Selladores y PU (3)

Nos aditivos completos, faltam campos que às vezes não se aplicam (pH em fibras, selantes PU, pigmentos e desmoldantes): não é pendência.

## Categorias sem produtos

- **Cementos**: categoria publicada sem nenhum produto.
- **Fletes** (FletePar), **Intonaco** e **Pisos** (Kasteller) também não têm produtos no catálogo: funcionam como portas para os parceiros. Confirmar se é intencional.

## Prioridade sugerida

1. **CQ Robust 79**: os dados já estão na fonte; só regenerar a ficha.
2. **Carretilla Retráctil**: corrigir a tabela do card.
3. **4 morteros Hormigomix**: produto de giro, pedir as fichas ao fornecedor.
4. **5 aditivos sem ficha**: pedir os PDFs à Camargo Química.
5. **17 equipamentos sem PDF**: gerar as fichas a partir das tabelas que já existem, no mesmo padrão das fichas atuais.
6. **5 equipamentos sem dado nenhum**: pedir catálogo ao fornecedor ou tirar do site.
