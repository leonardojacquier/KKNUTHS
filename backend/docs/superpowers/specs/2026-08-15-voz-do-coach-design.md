# Voz do coach — a análise que soa como conversa

Data: 2026-08-15 · escopo: `coach()` e `followup()`

O pedido do dono, na íntegra: *"que fique bem natural como uma conversa
humana, com linguagem técnica, mas que seja didático, que seja claro, sem
enrolação. Não quero nada complexo."*

---

## 1. O problema, medido

Não por impressão. 403 análises reais de `hand_analysis` (45 dias):

| defeito | ocorrência | veredito |
|---|---|---|
| bloco depois do placar | **58% do texto** (740 de 1.662 chars, n=183) | **o alvo principal** |
| título fixo "A conta que mais pesa" | 102 / 403 (25%) | real, e a origem é nossa (§2) |
| bastidor vazando ("no caderno") | 45 / 403 (11%) | real |
| seção "o que treinar" | 19 / 403 (5%) | menor do que parecia |
| autocorreção no texto (`"... digo,"`) | 4 / 403 (1%) | existe; evento apenas |
| convite de premiação/ICM em parágrafo | 3 / 403 (0,7%) | **fora de escopo** |
| resposta maior que o teto de ~3.000 chars | máximo observado: 6.029 | o teto do V5 não é cobrado |

As duas últimas linhas são correções a afirmações feitas antes de medir. O
convite de ICM apareceu em 2 das 3 análises que li primeiro e eu o chamei de
sistêmico; na base inteira ele é 0,7%. **Amostra de três não é amostra** — é
o mesmo erro que o `METODO.md` §1 existe para impedir, cometido na leitura
em vez de no código.

### A origem do formulário é nossa

`llm.py:1854`, na instrução da análise:

> `"Feche com A conta que mais pesa."`

O título fixo não é vício do modelo. Foi pedido por escrito.

---

## 2. As decisões tomadas

Quatro perguntas, quatro respostas do dono:

1. **Didático = conceito + termo.** O jargão continua cru; a frase explica
   por que aquilo decide o spot; o termo ganha parêntese curto na primeira
   aparição.
2. **Selo (R1) e placar (R2) ficam intocados.** O corte é no que vem depois.
3. **Escopo: `coach()` + `followup()`.** As outras cinco superfícies de
   texto ficam de fora.
4. **Prompt + guarda determinístico + critério novo no juiz.** Prompt
   sozinho é pedido; este repositório documenta cinco guardas que furaram
   por serem só pedido.

---

## 3. O contrato novo da voz

### R3 — fechamento (reescrito)

Depois do placar: no máximo **2 parágrafos curtos**, e cada um precisa dizer
algo que o placar não disse. Sem título fixo. Sem recitar número que já
apareceu no placar — o fechamento explica o *porquê*, o placar já deu a
conta. "O que treinar" deixa de ser seção obrigatória.

### V4 — didático (reescrito)

A explicação do **conceito** mora dentro do "porquê curto" da linha do
placar, não como prosa adicional. Essa é a correção nº 6: explicar exige
palavras, e se as palavras forem parágrafo novo eu inflo exatamente o bloco
que estou cortando.

O **termo** ganha parêntese curto (≤6 palavras) na primeira aparição. O teto
de 2 parênteses por resposta é **chute a calibrar** na leitura lado a lado
(§5), não regra dura.

O botão 🎈 continua sendo o nível iniciante total.

### R7 — proibições novas

Autocorreção dentro do texto entregue; bastidor do sistema ("anotei no
caderno", "vou puxar"). O convite de ICM **não** entra — 0,7% não é padrão.

As duas proibições têm tratamento diferente no guarda, de propósito: o
bastidor é corrigido (§4), a autocorreção é só medida. Proibir no prompt e
não corrigir no guarda é uma escolha, não um esquecimento — com n=4 o
conserto automático arrisca mais do que resolve.

### `instruction` do `coach()`

Perde `"Feche com A conta que mais pesa."`.

### `followup()`

Herda o V4 novo. É onde o aluno diz "não entendi", e é metade do que ele
percebe como "o coach falando".

---

## 4. Onde muda

| arquivo | mudança |
|---|---|
| `app/agent/llm.py` | `_SYSTEM["pt"]`: R3, R7, V4 · `instruction` do `coach()` · bloco do `followup()` |
| `app/bot/guarda_voz.py` | **novo**, ~90 linhas, mesma forma do `guarda_saida.py` |
| `app/bot/processing.py` | chama o guarda onde `guarda_saida` já é chamado |
| `scripts/output_judge.py` | contadores novos, separados da nota |

### O guarda: o que corrige e o que só registra

A separação existe porque reescrever texto arrisca mudar conteúdo, e esse
risco não vale para tudo.

**Corrige** (determinístico e seguro):

- rótulo `"A conta que mais pesa:"` — remove o rótulo, mantém a frase, **e
  só quando a frase sobrevive sozinha**. `"*A conta que mais pesa:* com
  12bb, AK em HJ é jam"` vira um parágrafo começando em minúscula se a
  remoção for cega. Correção nº 4: quando a frase não sobrevive, o guarda
  registra e não toca. Este repositório já tem
  `test_corretor_nao_estraga_portugues.py` para esta classe exata de bug.
- frase de **narração de busca** ("deixa eu conferir o EV", "vou puxar o
  histórico") — remove a frase inteira. Medido: 91/403 = **23%**.

  **Correção feita ao escrever o plano.** Esta linha dizia "anotei no
  caderno". Medindo separado: "anotei no caderno" são 32/403 (8%) e **não é
  defeito** — é voz de coach e é a regra A2 (`record_student_note`)
  aparecendo para o aluno. O guarda como estava especificado apagaria a
  frase mais humana da resposta e deixaria passar o bastidor de verdade,
  que é 3x mais comum. É o mesmo erro do convite de ICM (§1): tratar o que
  eu vi como o que existe.

**Só registra evento**:

- bloco pós-placar acima de **800 chars** (o sinal principal — §5). O 800
  sai da medição: a média é 740 e 34% das análises passam disso, então o
  teto marca a cauda sem acusar o caso comum. Número a calibrar depois da
  leitura lado a lado, como o teto de parênteses do V4.
- autocorreção `"... digo,"` — n=4 em 403. Correção nº 5: frequência baixa
  demais e falso positivo plausível na fala natural de coach ("não é
  fold... digo, não sempre"). Evento, nunca correção.
- número do placar repetido na prosa — contador secundário, ver §5

---

## 5. Verificação

### O sinal principal é comprimento, não repetição

Correção nº 3. Eu tinha escolhido "número do placar repetido na prosa"
porque dá para contar por regex. Mas repetir o `+1.49bb` no fechamento é
ênfase legítima — um coach faz isso. O defeito não é o número aparecer duas
vezes, é **o parágrafo inteiro não acrescentar nada**, e isso regex não vê.

O que dá para medir e correlaciona com o defeito: **chars depois da última
linha do placar**. Hoje: média 740, e 63 de 183 análises (34%) passam de
800. A repetição de número fica como contador secundário, não como gatilho.

### Nada disso mede "natural"

Correção nº 2, e o furo mais grave do desenho original: todo mecanismo acima
detecta *ausência de defeito*. Uma resposta pode passar em tudo e continuar
lendo como robô.

**A verificação que responde ao pedido:** 8-10 mãos reais do banco, rodadas
com o prompt velho e o prompt novo, entregues ao dono lado a lado. Leitura
humana, não nota automática. Custa alguns dólares e uma leitura. É o único
teste que mede o que foi pedido, e é o que decide se a mudança presta.

Script: `scripts/comparar_voz.py` (one-shot, saída em arquivo).

### O juiz não pode mudar de régua no mesmo dia

A nota 0-10 e seus critérios **ficam como estão**. Os checks novos entram
como contadores separados. Sem isso, a média móvel de 7 dias muda de
significado no meio da série e nenhuma comparação antes/depois vale.

### Testes

TDD, um teste por regra. **Teste de mutação obrigatório nos guardas**:
quebrar a linha de produção e confirmar que o teste falha nomeando o
arquivo. `METODO.md` §7 — cinco dos guardas mais importantes deste sistema
eram protegidos por comparação de texto do código-fonte, que não é teste.

---

## 6. Sequenciamento — e por que o deploy espera

Correção nº 1, e a que eu tinha ignorado por completo.

O `ANALYSIS_MODEL` virou `claude-sonnet-5` em 15/08. O item 3 do "Onde
paramos" é ler o juiz das 8h de **16/08** — o primeiro dia com Sonnet
default e conferência de números. Trocar o prompt antes dessa leitura faz a
nota de amanhã misturar duas variáveis, e a decisão de modelo tomada ontem
fica sem aferição.

**Portanto:** implementa-se tudo, com testes, e o merge para produção espera
a leitura do juiz de 16/08. A data da troca fica registrada para a série de
7 dias continuar interpretável.

---

## 7. Fora de escopo (YAGNI)

- As outras cinco superfícies de texto (`simplify`, `evaluate_line`,
  `synthesize_answer`, lição, dossiê)
- Tornar o placar (R2) flexível — é a fase 2, depois de medir esta
- Cobrar o teto de 3.000 chars do V5 (existe, é furado, mas é outro problema)
- O convite de ICM — 0,7% não justifica regra

---

## 8. Riscos

| risco | mitigação |
|---|---|
| prompt novo contradiz o R7 existente | `test_prompt_nao_briga_consigo.py` já roda; a explicação vai dentro do placar, não como prosa nova |
| guarda estraga português | só corrige quando a frase sobrevive sozinha; teste dedicado |
| resposta fica seca em vez de natural | leitura lado a lado (§5) antes do merge |
| dois prompts mudam juntos (`coach` + `followup`) | confusão menor e aceita; o defeito medido está nos dois |

---

## 9. Resultado (Task 7, 16/08/2026)

### A linha de base, remedida sobre a população certa

O §1 mediu 403 análises sem filtrar follow-up nem torneio. Refeito por SQL
independente (espelhando os regexes do `guarda_voz`) sobre a população que a
pergunta pede — **análises de mão reais dos últimos 45 dias**, excluindo
`summary like '[Follow-up]%'` e exigindo `mistakes is not null`:

| defeito | medido | população |
|---|---|---|
| bloco pós-placar | **67% do texto, 678 chars em média** | n=116 (com selo) |
| título fixo "A conta que mais pesa" | **48%** (102 de 212) | n=212 |
| bastidor de busca ("deixa eu conferir", "vou puxar") | **34%** (73 de 212) | n=212 |
| análises com bloco pós-placar > 800 chars | **14%** (30 de 212) | n=212 |
| autocorreção "... digo," | **3 casos** | n=212 |
| autocorreção NARRADA ("Corrigindo então:") | **2 casos** | n=212 |
| tamanho médio da análise | 1052 chars | n=116 |

> **Erro cometido ao escrever este documento e corrigido na conferência**: o
> §1 publicou "58% do texto, 740 de 1.662 chars, n=183", "título fixo 25%" e
> "bastidor 23%". O denominador estava contaminado — a amostra incluía
> follow-ups (sem placar) e análises de torneio, cuja prosa longa dilui a
> média e cuja ausência de placar não deveria nem entrar na conta de "bloco
> pós-placar". Filtrando para a população correta os defeitos **não
> diminuem, aumentam**: 67% em vez de 58%, 48% em vez de 25%, 34% em vez de
> 23%. A direção da conclusão do §1 se mantém e fica mais forte — mas o
> número publicado estava medido errado, **pelo mesmo erro que o
> `METODO.md` §1 existe para impedir**: denominador que engole população que
> não pertence à pergunta. O erro foi cometido de novo ao escrever este
> próprio documento, que existe justamente para impedir isso.

**Consequência para o teto calibrado.** `TETO_POS_PLACAR = 800` (§4) foi
calibrado sobre a média inflada de 740 chars, com a intenção de marcar a
cauda (34% das análises passavam do teto). Na média real de 678 chars, o
mesmo teto de 800 pega só **14%** das análises — mais alto, proporcionalmente,
do que a calibração original pretendia. Continua defensável: ele ainda pega
a cauda sem acusar o caso comum, e recalibrar para baixo sem a leitura
lado a lado (§5) seria a mesma pressa que gerou o erro acima. Mas o número
que vier depois de mergear precisa saber que a régua nasceu do denominador
errado.

### Achado novo: autocorreção narrada — nenhum guarda cobre

Nos 212 casos apareceu uma forma de defeito que não está em nenhuma das
listas de §1/§3: uma análise real **narra a própria correção para o
aluno** — *"Ajustando o fechamento com o número real… Corrigindo então:"* —
e chega a emitir "A conta que mais pesa" duas vezes na mesma resposta. É
pior que o `"... digo,"` do R7: ali o modelo tropeça e segue; aqui o aluno
lê o modelo se contradizendo e se consertando em público, como um rascunho
que vazou. 2 casos medidos (mesma população de 212).

Nem o guarda determinístico nem o R7 do prompt cobrem essa forma — o R7
proíbe autocorreção *dentro do texto* mas não descreve narração de
correção como categoria separada, e o guarda não tem regex para isso.
**Registrado como pendência conhecida, não corrigido nesta task** — 2 casos
é frequência baixa demais para justificar um padrão novo de correção
automática sem antes ver mais exemplos, pelo mesmo motivo que `"... digo,"`
ficou como evento e não como correção (§4).

### O que falta e não pôde ser feito aqui

O Passo 2 do plano original (rodar `scripts/comparar_voz.py` para gerar o
lado a lado antes/depois) exige chamar a API da Anthropic com credenciais
de produção. O ambiente que executou a Task 7 não tem `.env`, não tem
`ANTHROPIC_API_KEY` e `get_repository().enabled == False` — não há como
gerar o "depois" aqui. Comando pronto para rodar no VPS:

```bash
cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/comparar_voz.py --n 8 --saida /tmp/voz.md
```

A leitura de `/tmp/voz.md` continua sendo a decisão do dono (§5) — nenhum
número desta seção substitui isso.

---

## Documentos irmãos

`../METODO.md` · `../ARQUITETURA.md` · `../../../OPERATIONS.md`
