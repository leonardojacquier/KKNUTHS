---
tags: [kknuths, tecnica, visao, qualidade]
atualizado: 2026-07-29
---
# Unidades da Leitura de Print

**Por que existe:** a primeira mão que um usuário novo
mandou na vida virou uma mesa de zeros, e o coach respondeu pedindo o stack
que estava na foto. Foi o primeiro contato dele com a ferramenta. Ele não
voltou.

## O defeito
A sala mostrava **duas escalas ao mesmo tempo**: o nível no cabeçalho em
fichas (`15000/30000`) e a mesa em bb (stacks `17.4`, `66.6`, `28.5`; pote
`10.1`). A visão transcreveu as duas literalmente — o que é *fiel à imagem*
e, por isso, difícil de culpar.

Só que tudo abaixo da visão divide por `big_blind`:

```
17.4 / 30000 = 0.0
```

`hero_stack_bb` 0.0, `pot_bb` 0.0, `amount_bb` 0.0. O coach recebeu uma
mesa inteira zerada e fez a coisa honesta com o que tinha: pediu o dado.
**O coach não errou. O erro chegou pronto até ele.**

## A guarda (`llm._coerir_unidades`)
O sinal é impossível de acontecer de verdade: **o maior stack da mesa não
pode ser menor que um big blind** — o pote sozinho já seria maior que todo
mundo. Quando isso aparece, quem está fora de escala são os blinds; stacks,
apostas e pote já estão em bb. A guarda traz os blinds para bb.

Não dispara em: torneio normal em fichas, cash em dólar, jogador eliminado
com stack 0, mesa sem jogador, blind zerado.

O caminho inverso (blinds em bb, stacks em fichas) **não** é corrigido: não
existe limiar seguro que separe isso de um cash deep legítimo. Consertar só
o que é provavelmente impossível.

## As outras duas camadas
- **Prompt da visão** exige uma unidade só e explica o caso das duas
  escalas. A guarda conserta o estrago; o prompt evita que aconteça.
- **`analyze_hand` marca `stacks_ilegiveis`** quando `0.0bb` sai de um stack
  com ficha na mesa, para fonte que não passa pela visão. `0.0` lido como
  número de verdade faz o coach raciocinar sobre um spot que não existe.

## Pote: a tela manda no snapshot
Achado do mesmo print. O pote reconstruído somando as ações é um **piso**
quando a fonte é foto de meio de mão — a imagem não mostra a linha inteira.
A tela dizia 10.1bb, a soma dava 7.5, e é o pote que define o preço.

`pot_na_tela` aparece só quando a fonte é imagem **e** o lido é maior que o
somado. Lido menor é erro de leitura, e aí a soma manda: mão fechada não
perde ficha.

## O padrão que se repete
Quarta vez que o defeito não está onde a mensagem de erro aponta. O coach
disse "os stacks vieram zerados" e estava certo — a causa era três camadas
acima. Ver [[Histórico de Decisões]].

Ligações: [[Arquitetura Técnica]] · [[Testes e Qualidade]] ·
[[Ingestão de Replays de Clube]] · [[Runbook de Operação]]
