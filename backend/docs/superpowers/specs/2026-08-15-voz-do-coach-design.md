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
  histórico") — remove a frase inteira, **exceto quando a frase carrega um
  número** (ver §10 I1 e §11 R1; "número" é `guarda_fatos._TEM_NUMERO`, a
  definição de conta da casa, não uma cópia só de bb/%). Medido: 91/403 =
  **23%**.

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
- número do placar repetido na prosa — contador secundário, ver §5. **Nem
  isso**, desde a onda final: ele saiu de `problemas_de_voz` e virou métrica
  avulsa, porque o R5b passou a EXIGIR a repetição (§10, I3)

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

> **Correção nº 7 (onda final).** "Contador secundário" ainda era gatilho
> demais: enquanto ele vivia dentro de `problemas_de_voz`, uma análise
> CONFORME gravava evento de voz. Ver §10, I3 — a repetição virou obrigação
> quando o R5b entrou, e a régua tinha que sair junto.

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

## 10. Onda de correção da revisão final (16/08/2026)

A revisão da branch inteira executou cenários contra o código e achou o que
as revisões tarefa a tarefa não podiam ver: **as duas metades da branch se
atropelam**. O prompt e o guarda agem sobre o mesmo texto em sequência, e o
juiz media o fim dessa sequência. Sete consertos, todos com teste que falha
com o código antigo.

**C1 — o juiz estava cego para o que existe para medir.** `conferir_e_limpar`
limpa o texto ANTES de ele ser gravado, e o juiz media o texto GRAVADO. Como
o guarda corrige exatamente título fixo e bastidor, esses dois contadores
iriam a ~0 por construção: **o bloco R3/R7/V4 do prompt poderia ser um no-op
completo e a linha do juiz seria idêntica** — e o merge está parado
esperando justamente essa leitura. O dado cru já estava gravado e ninguém o
lia: os eventos `voz_corrigida`/`voz_medida` guardam `problemas` medidos
antes da limpeza. O juiz agrega esses eventos na janela de 24h
(`resumo_dos_eventos_de_voz`) e imprime DUAS leituras nomeadas, porque são
coisas diferentes e as duas importam: **o que o MODELO escreveu** (antes da
limpeza — é o que diz se o prompt funcionou) e **o que o ALUNO recebeu**
(depois — é o produto). Atenção ao denominador: só existe evento quando há
algo a apontar, então a primeira leitura é numerador, nunca taxa.

**I1 — a limpeza podia apagar o número.** `_sem_narracao` removia a FRASE
inteira, e a frase pode ser a única com a conta:
`"Vou calcular: pedia 30%, tinha 12% → −11bb. Portanto foi call caro."`
virava `"Portanto foi call caro."`. Pior: `conta_sem_numero` e
`guarda_saida.faltou` rodam ANTES do guarda da voz nos dois caminhos, então
o defeito nascia depois do detector. Agora frase de bastidor **com número é
medida e entregue** — prosa feia é menos pior que conta apagada, e isso é o
§4 ("só corrige quando é seguro corrigir") aplicado ao caso que faltava. De
brinde mata o defeito da frase fundida por falta de espaço depois do ponto,
onde o aluno recebia só o selo.

**I2 — o guarda conhecia 1 rótulo e o R3 proíbe 3.** Trocar para "Resumo:"
deixava todos os contadores em sucesso com o formulário intacto sob
cabeçalho novo. Os dois rótulos genéricos só contam quando ABREM a linha
("em resumo, ..." não é título). Junto: o R3 proibia `'O que treinar:'` e
quatro linhas depois parecia licenciá-lo — a menção voltou para dentro da
própria proibição.

**I3 — o contador marcava como defeito o que o prompt MANDA.** `numeros_
repetidos` sai de `problemas_de_voz`. Motivo, para o registro: quando o §5
o classificou como "secundário", o R5b ainda não existia. Com o R5b, a
história do desfecho ("você estava atrás desde o pré: 30% no flop, 12% no
river") é OBRIGATÓRIA e repete as equities do placar por definição —
executado numa análise conforme, o contador devolvia `12%, 30%`. Mantê-lo
como defeito gravaria um evento em quase toda análise CERTA e faria
`com_numero_repetido` **subir como efeito direto da melhoria**. Escopar por
regex não era opção: a diferença entre RECITAR o preço e CONTAR a história é
semântica. Continua calculável (`numeros_repetidos`) e continua contado no
`voz_do_dia`, agora sem virar defeito nem gerar evento.

**I4 — a linha diária comparava duas populações.** `resumo_de_voz` somava
relatório de torneio e análise de decisão única, que não têm placar: nesses
textos `bloco_pos_placar` devolve tudo depois da 1ª linha, e um relatório de
1200 chars vira "bloco" de 1199, marcado longo, todo dia. Dois filtros:
`mistakes is not null` (o mesmo do comparador) e ≥2 linhas de selo. A
população da NOTA fica intocada — a régua não muda no meio da série. E a
linha imprime **678**, não os 740 que o §9 declarou medidos sobre população
contaminada.

**I5 — o experimento de uma variável tinha três.** O comparador gerava o
"depois" sem o perfil do aluno e sem o guarda da voz. Os dois foram
espelhados (o perfil pela MESMA função que `processing.py` usa, extraída
para `stats.perfil_para_o_coach`), e o que não dá para espelhar está
declarado no cabeçalho do `/tmp/voz.md`: o perfil do "depois" é o de HOJE,
não o do dia do "antes". O markdown também passou a distinguir "mão não
encontrada" de "a geração falhou" — os dois pedem reações opostas do leitor.

**I6 — o R3 ia sem escopo para a conversa**, onde a pergunta do aluno costuma
ser justamente pela conta. Proibir formulário não pode virar proibir
responder: se o aluno PERGUNTAR pelo número, o número vai.

**I7 — três fechadores obrigatórios para duas vagas.** R5b, C3b (o ICM que
falta) e A1 disputavam o teto do R3 sem prioridade escrita, e o candidato a
cair era o C3b — o único com número computado que o placar não deu, e o
único cuja ausência o aluno não percebe. A prioridade está escrita. Pago com
`"Medido: hoje esse bloco é 58% do texto."`, número que o §9 desta mesma
spec já tinha corrigido para 67%/678: o prompt segue em 3198/3200 palavras.

### O que a onda NÃO consertou, de propósito

- `TETO_POS_PLACAR = 800` continua calibrado sobre a média inflada de 740
  (§9). Recalibrar sem a leitura lado a lado seria a mesma pressa que gerou
  o erro do denominador.
- O prompt `en` não foi tocado e o guarda é só PT: aluno com `lang="en"`
  recebe a voz antiga e entra nos contadores zerado, inflando o "sucesso".
- O caminho de TORNEIO não recebeu a voz nova (`instruction` separada) — o
  que a branch fez foi parar de contá-lo como se fosse análise de mão.
- O botão 🎈 não tem guarda da voz nem contador.

## 11. Os três resíduos da re-revisão final (16/08/2026)

A re-revisão da onda §10 confirmou os oito consertos e deixou três resíduos
adjudicados, com prescrição exata. O dono autorizou os três, e nada além
deles: *"Eu quero q simplifique mas que não apague números importantes. Pode
consertar as 3"*.

Essa primeira frase é o **critério do guarda da voz**, e está gravada na
docstring do módulo `guarda_voz.py` e na de `_sem_narracao`, com atribuição.
Ela resolve toda decisão de corrigir × só medir: simplificar é o pedido,
apagar número é o limite.

**R1 — a limpeza ainda podia apagar a única conta.** O I1 fechou o cenário,
não a classe. A trava de `_sem_narracao` usava o `_NUMERO` do próprio
`guarda_voz`, que só conhece `bb` e `%`. A definição de conta desta casa é
`guarda_fatos._TEM_NUMERO`, e o comentário dela já dizia por quê: *"exigir
sufixo bb/%/fichas reprovava as duas formas mais básicas da matemática de
poker"*. Quatro textos executados pelo re-revisor continuavam perdendo a
única conta e virando veredito pelado:

| texto do modelo | o que o aluno recebia |
|---|---|
| `Vou calcular: o pote paga 2.5 para 1 e você tem 1 em 3. Portanto foi call caro.` | `Portanto foi call caro.` |
| `Vou conferir: você tinha 9 outs. Portanto foi call caro.` | `Portanto foi call caro.` |
| `Vou calcular: o pote tinha 5000 fichas e o call custa 1200 fichas. …` | `Portanto foi call caro.` |
| `Vou rodar o EV: deu +8.2 no shove. Portanto foi jam claro.` | `Portanto foi jam claro.` |

`_sem_narracao` passou a consultar `guarda_fatos._TEM_NUMERO`. Uma definição
de conta, um lugar só — e `guarda_fatos` não importa `guarda_voz` em direção
nenhuma, então o import de topo não fecha ciclo (conferido antes). `_NUMERO`
continua existindo e continua certo para `numeros_repetidos`, cujo universo
é o placar, e o placar escreve bb e %. Alargar não virou "nunca mais limpo
nada": `"Vou conferir o range: 16.9 combos."` continua saindo inteira,
porque número solto sem unidade não é conta — o próprio `_TEM_NUMERO` diz
isso ("não é afrouxar até `\d`").

**R2 — o juiz media certo e mostrava incompleto.** Os dois defeitos eram de
REPORTE, e moravam numa f-string dentro de `main()`, função que só roda com
Supabase — por isso nenhum teste podia pegá-los. A montagem saiu para
`linha_da_voz(cru, voz)`, pura e testada sobre o texto renderizado.

- **(a) a linha 🗣 não era comparável à base.** Imprimia numerador puro ("1
  respostas tiveram algo a apontar") ao lado de uma base que é TAXA (48% /
  34%): absoluto não se compara com percentual, que é o mesmo erro de
  denominador que a §9 documenta ter cometido. E o numerador somava duas
  populações — `em_conversa` era calculado e jogado fora na hora de
  imprimir, com 185 de 423 `summary` históricos sendo follow-up. Agora:
  `eventos − em_conversa` sobre `voz['analisadas']` (mesma população, mesma
  janela) vira a taxa comparável; a conversa aparece à parte; os contadores
  por defeito seguem rotulados como numerador das duas somadas.
- **(b) a linha 🧹 tinha parado de mostrar o lado do ALUNO.** O conserto do
  C1 moveu `título fixo · bastidor · bloco longo` para a leitura do modelo —
  certo, é ela que mede o prompt — e deixou a do aluno só com a média do
  bloco. São dois lados: o que o modelo produziu mede o PROMPT, o que o
  aluno recebeu mede o GUARDA. E o lado do aluno virou informativo
  exatamente agora, porque o I1/R1 fez o guarda RECUSAR limpar quando a
  frase carrega a única conta: **`com_bastidor` entregue deixou de tender a
  zero**. A métrica que a onda piorou de propósito era a que tinha saído da
  tela do dono. A docstring de `resumo_de_voz` ainda afirmava o contrário
  ("título fixo e bastidor tendem a zero: é o guarda funcionando") e foi
  corrigida contador a contador.

**R3 — teste que prometia no nome o que não cobrava no código.**
`test_o_juiz_audita_a_janela_de_24h_e_nao_o_museu` foi reescrito na onda §10
porque contava consultas (`== 1`) e quebrou com a consulta nova do C1. Ficou
mais forte num eixo e mais fraco no da própria docstring: com `>= 3`
consultas e "usa day_ago OU week_ago", trocar a query de análises para
`week_ago` passava (que é literalmente auditar o museu) e apagar uma
consulta inteira também. Agora o teste mapeia **cada consulta pelo nome para
a sua janela exata** — as três de entrega em `day_ago`, e só a média móvel em
`week_ago`. `bot_events` é lida duas vezes com propósitos opostos, então a
chave distingue `bot_events/voz` de `bot_events/nota_resposta`.

Junto, o buraco próprio do C1: trocar a consulta a `bot_events` por
`eventos_voz = []` reinstalava a cegueira do C1 — com rótulo honesto na tela
— e os 22 testes de juiz/voz ficavam verdes, porque os testes AST prendiam a
CHAMADA a `resumo_dos_eventos_de_voz` e nunca a query que a alimenta. O
teste novo prende a corrente inteira por AST: consulta a `bot_events`
filtrando os dois eventos de voz → laço sobre `eventos_voz` → o mesmo nome
que entra em `resumo_dos_eventos_de_voz`.

### O que os resíduos NÃO tocaram

O selo (R1 do prompt) e o placar (R2) seguem intocados, o prompt segue em
3198/3200 palavras, e os itens que são decisão do dono continuam abertos:
prompt `en`, caminho de torneio, autocorreção narrada sem guarda e o
`TETO_POS_PLACAR = 800` calibrado sobre a média inflada de 740.

## Documentos irmãos

`../METODO.md` · `../ARQUITETURA.md` · `../../../OPERATIONS.md`
