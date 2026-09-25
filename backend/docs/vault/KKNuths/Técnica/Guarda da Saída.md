---
tags: [kknuths, tecnica, qualidade]
atualizado: 2026-07-26
---
# Guarda da Saída

**Por que existe:** três vezes numa semana o aluno pediu gráfico de EV e
recebeu prosa. O motor estava pronto e certo nas três. O que faltou foi a
ponte — e ponte não se conserta com mais regra no prompt (já eram quatro:
C10, C11, C11b, C11c). Regra é pedido; isto é **conferência**.

Mesma lógica do portão de testes no deploy: não confio na intenção, confio
na verificação ANTES de entregar. O juiz da saída já fazia isso, mas roda no
dia seguinte — tarde demais para quem está esperando a resposta.

## Como funciona (`app/bot/guarda_saida.py`)
1. classifica o **pedido** do aluno (gráfico? número?) por regex
2. confere a **entrega** (saiu gráfico? tem número na resposta?)
3. o que faltou é **remediado** chamando a ferramenta na marra — só contas
   determinísticas, nada de pedir ao modelo de novo, que é o que já falhou
4. tudo vira evento: `entrega_ok` / `entrega_falha` / `entrega_remediada`

`street_pedida()` existe porque o guarda montava o gráfico da street mais
profunda — o aluno perguntava do TURN e receberia o river.

Sem conversa resolvida, a remediação diz **com todas as letras** que perdeu
a referência da mão. Nunca fica em silêncio nem inventa conta.

## A métrica que faltava
**Taxa de entrega** no resumo diário: de cada pedido conferível, quantos
saíram completos de primeira. Antes disso a nota de entrega era opinião
minha e o defeito só aparecia por print do aluno.

## Contexto da conversa (a família de bugs por trás)
`abrir_conversa()` é o **construtor único** de contexto e **levanta exceção**
se a conversa não tiver mão nem declarar `sem_mao=True`. Quiz e simulador
gravavam contexto sem `hand_id`, e TODA ferramenta de mão morria depois
deles. O canário anterior conferia duas strings literais — era whitelist e
não pegava arquivo novo; foi trocado por regra que varre os arquivos.

`_hand_id_no_contexto()` busca **recursivamente**; falha vira evento
`sem_mao_na_conversa`, que aparece no resumo diário.

## Sonda de jornadas (`scripts/jornadas.py`)
Roda o código de verdade **em processo** — sem Telegram, sem conta, sem LLM,
sem custo. Não pergunta "deu erro?", pergunta **"chegou o que o aluno
pediu?"**.

- **Parte A — dados reais:** percorre as `conversation_state` VIVAS e exige
  que a mão resolva. O gabarito não é meu: são as conversas dos alunos
- **Parte B — 5 jornadas sintéticas**, cada uma exigindo NÚMERO na saída

Existe porque a `e2e_probe` **nunca rodou uma vez**: depende de uma
conta-teste que nunca foi criada, e `bot_events` não tem um evento `e2e`
desde que ela foi escrita. A rede que eu contava como proteção nunca esteve
no ar.

Relacionado: [[Testes e Qualidade]] · [[Coerência Gráfico-Análise]] ·
[[Portal Admin e Métricas]]

## As quatro camadas da linguagem (02/08)
Mesma filosofia aplicada à terminologia, depois que "7 cheio de 2" e
"aumentou" chegaram ao aluno:

1. **Prompt** (`TERMOS_REGRA`) — previne: calques proibidos com a forma
   certa ao lado. Estático, protegido pelo portão de testes.
2. **Corretor** (`app/agent/termos.py`) — conserta na entrega: só a troca
   que um regex acerta em 100% dos casos ('check atrás'→'check behind').
   Determinístico, roda nos 6 loops de tools e na simplificação.
3. **Juiz** (8h) — vigia regressão e os termos ambíguos ('passou',
   'sequência'), que trocar errado seria pior que avisar.
4. **Linguista** (7h40, IA barata) — *aprende*: lê as análises do dia,
   propõe calques novos na tabela `glossario`; o dono aprova com
   `/termo ok N [corrigir]`; corretor e juiz leem o aprovado em 10 min.

Fronteira dura do desenho: **a IA propõe, nunca aprova nem edita o
prompt**. Aprender = acumular dados; proposta ruim descartada custa zero,
prompt editado errado contamina toda análise em silêncio.
