# Método — o que a ferramenta afirma, o que ela se recusa a afirmar, e por quê

Atualizado: 2026-08-09

Este documento existe por um motivo específico. Em julho o dono disse:

> *"Eu não confio nada nos seus números e análises."*

Ele estava certo. O perfil de um aluno dizia **VPIP 94,3%**; o VPIP real dele,
em 406.639 mãos, era 26%. O número não estava errado por bug de conta — estava
errado por bug de **amostra**, que é um erro que nenhum teste unitário pega e
nenhuma revisão de código enxerga.

O que se seguiu não foi "consertar a conta". Foi construir um conjunto de
portões que impedem a ferramenta de dizer coisas que o dado dela não sustenta,
e testes que cobram esses portões. Este documento é o contrato.

**A regra geral, em uma linha:** *não ter número é melhor que ter número
errado, e o sistema tem que preferir dizer "não sei".*

---

## 1. O portão de amostra — viés de seleção não é amostra pequena

**A confusão que custou a confiança.** Aluno manda 53 replays de clube. VPIP
calculado: 94,3%. A leitura intuitiva é "amostra pequena, com mais mãos
converge". **Está errado.** Com 5.000 replays escolhidos pelo mesmo critério o
número daria o mesmo — porque *ninguém manda o replay de uma mão que largou no
pré*. A amostra não é pequena, é **curada**. Mais dados não consertam viés de
seleção; só o denominador certo conserta.

| | amostra pequena | viés de seleção |
|---|---|---|
| causa | poucas observações | as observações não são sorteadas |
| sintoma | intervalo largo | ponto deslocado, intervalo estreito |
| cura | mais dados | **outra fonte de dados** |
| como mente | admite que não sabe | parece que sabe |

**O portão.** `app/analysis/stats.py`:

```python
FONTES_COMPLETAS = {"txt", "text", "csv", "phh", "pdf"}
MINIMO_PARA_PERFIL = 30     # número, com intervalo declarado
MINIMO_PARA_ROTULO = 100    # rótulo de estilo ("LAG", "nit")
```

Só fonte que traz a **sessão inteira** entra em qualquer conta de frequência.
Replay avulso e print continuam valendo integralmente para analisar *aquela
mão* — equity, preço, EV, leitura de vilão. Nada disso depende de amostra.

**Duas camadas, porque uma não bastou.**

1. **Procedência** — o formato do arquivo traz mãos foldadas?
2. **Conteúdo** — a mão tem ações de pré-flop de verdade?

A segunda camada foi acrescentada depois de o CSV de tracker passar na
primeira e produzir *VPIP 0% · nit (tight-passive)* com `publicavel=True`. CSV
está em `FONTES_COMPLETAS` e está certo que esteja, mas mão-resumo não carrega
ações de rua. **Portão de procedência não substitui portão de conteúdo** — foi
o mesmo erro pelo outro lado.

**Escrita e leitura.** Consertar a conta não bastou, porque *ninguém relê uma
tabela*. A linha envenenada continuou no `player_stats` por dois dias depois do
conserto, e `processing.py` a injetava no contexto do coach a cada pergunta
aberta. Hoje a coluna `publicavel` é cobrada nos dois lados: `upsert_player_stats`
e `snapshot_player_stats` não gravam perfil impublicável, e
`perfil_que_pode_ser_dito()` filtra na leitura.

**Toda taxa carrega seu intervalo.** `margem_de_erro_pp()` existe para que
nenhuma taxa apareça sem ele:

> `VPIP 26%` é uma promessa de precisão que o denominador não paga.
> `VPIP 26% (n=148, ±7pp)` é o mesmo dado sem a promessa.

**O custo aceito.** O aluno que só joga PPPoker e Suprema — salas que não
exportam sessão — deixa de ter perfil. Isso foi comunicado a ele
explicitamente (`scripts/recado_amostra.py`), com a explicação do viés e a
lista do que continua funcionando.

---

## 2. Taxonomia de erro — contar em vez de opinar

Antes, `hand_analysis.mistakes` guardava a decisão, sem código e sem
denominador. Dava para mostrar uma mão. Não dava para dizer a frase que separa
diagnóstico de impressão:

> *"você foldou 9 de 14 vezes nesse spot, e isso custou 2,1bb/100"*

`app/analysis/taxonomia.py` exige **quatro coisas** de cada código, e é a
segunda que quase sempre falta nas ferramentas do mercado:

1. **código fechado** — texto livre não se agrupa
2. **oportunidade computável** — o spot aconteceu, *mesmo que o aluno tenha
   acertado*. Sem denominador, "errou 4 vezes" não quer dizer nada: 4 em 4 e
   4 em 400 são jogadores diferentes.
3. **escorregada computável** — o que, naquele spot, foi o erro
4. **custo em bb**, e a honestidade de marcá-lo como `exato` ou `estimado`

Os seis códigos hoje: `open_perdido`, `shove_perdido`, `shove_largo`,
`call_caro`, `bb_subdefesa`, `limp_de_abertura`.

**O erro é medido na DECISÃO, nunca no resultado.** Um detector que olhasse
"perdeu o pote" estaria errado por construção — e este projeto já teve
exatamente esse bug (commit `9497ad8`, *resultadismo no encanamento*).

**Decisão pelo limite inferior, não pela média.** `agregar()` compara o limite
inferior do intervalo com a tolerância. Uma taxa de 40% com n=10 tem limite
inferior abaixo de qualquer tolerância razoável e não vira diagnóstico.

**Correção para comparações múltiplas.** Varrer os códigos e pegar o pior é,
por construção, procurar o extremo. A régua é **Šidák, sem degrau**: cada
teste roda a `1-(1-0,05)^(1/N)`, e como o portão usa o **limite inferior** de
um IC bilateral, a cauda de interesse é metade disso.

Com os 6 códigos de hoje isso dá **z = 2,63** — não 1,96. A versão anterior
era um degrau (`Z99 se testados > 10, senão Z95`) com dois defeitos que se
anulavam: z=2,576 está calibrado para *exatamente* N=10 e só ligava a partir
de N=11, ou seja, apenas na faixa em que já era insuficiente; e produção passa
`len(CODIGOS)` = 6, então o ramo endurecido **nunca executou**.

| N testados | z |
|---|---|
| 1 | 1,96 |
| 6 (hoje) | **2,63** |
| 10 | 2,80 |
| 20 | 3,02 |

**Dedup de custo.** Uma mesma decisão pode disparar dois códigos — um limp de
72o é limp de abertura *e* call caro. O custo é deduplicado por
`(hand_id, street)` tomando o máximo, senão o EV perdido conta duas vezes.

### O que os dados reais mostraram

Verificado contra a produção antes de virar conselho. **O denominador é a
oportunidade, não a mão** — para o limp isso significa pote não aberto e herói
fora dos blinds, que é a semântica exata do detector.

Remedido por SQL independente em 09/08/2026, sobre as mãos de fonte completa:

| aluno | oportunidades de abrir | limps | taxa | tolerância |
|---|---|---|---|---|
| Leo (`6452742024`) | 116 | 2 | **1,7%** | 5% |
| Odilon (`6104620007`) | 46 | 0 | **0%** | 5% |
| terceiro (`8972465711`) | 16 | 0 | **0%** | 5% |

| Afirmação testada | Resultado |
|---|---|
| "limp é o leak nº 1 do poker de clube" | **Falso para estes alunos** — todos abaixo da tolerância, dois deles em zero. A afirmação do especialista é sobre a população, não sobre estes três. |
| defesa de BB fraca | Leo folda 19/29 = 66% (referência 45-55%) — mas n=29 dá ±17pp, então é **suspeita**, não diagnóstico |
| "o problema mora na faixa de re-shove" | Leo tem 103 mãos em 15-25bb, exatamente onde o especialista previu |
| direção do erro (passivo vs largo) | era **artefato do nosso próprio conjunto de detectores** (4 passivos vs 2 largos) — corrigido |

> Erro cometido ao escrever este documento e corrigido na conferência: a
> primeira versão dizia "2 limps em 150 mãos". A contagem de limps estava
> certa, o denominador não — 150 eram *mãos*, e o que o detector usa são as
> **116 oportunidades de abrir**. Taxa com denominador errado é exatamente o
> defeito que o resto deste documento existe para impedir.

---

## 3. Estratégia de torneio — rejeitar a pergunta antes de respondê-la

A pergunta era *"etapa inicial mais tight ou mais agressivo?"*. A resposta
honesta começa por recusar a pergunta: **"etapa" mistura duas variáveis
ortogonais.**

- a **profundidade do stack** determina a árvore de decisão
- a **profundidade do torneio** determina a pressão de ICM

Um jogador com 18bb no nível 3 e outro com 18bb no nível 14 jogam a *mesma*
estratégia de fichas e estratégias de *risco* diferentes.

E a premissa "early mais tight" é de 2004, de uma era **sem ante nos níveis
iniciais**. Com ante, os ranges de open no early são os de cash 100bb, e o ICM
no early é ≈1 — é o momento de **máxima liberdade** para acumular. A variável
que de fato aperta os ranges é `ante == 0`, que é **dado exato na mão**.

> O corte é por **ante**, não por "etapa": um é medido, o outro é palpite com
> nome de estratégia.

**As faixas** (`app/analysis/estrategia_torneio.py`), por stack **efetivo**,
com fronteiras onde a *árvore* muda:

| faixa | bb | por quê |
|---|---|---|
| deep | > 40 | jogo de 3 ruas; implied odds contam |
| padrão | 25–40 | 3-bet cabe sem comprometer o stack |
| re-shove | 15–25 | o re-shove domina e o 3-bet não-all-in some |
| curto | 8–15 | push/fold com folga de fold equity |
| crítico | < 8 | push/fold puro |

**O que este módulo afirma e o que não afirma** — a distinção é o produto:

- **afirma**: EV perdido por faixa, contagem de erro e *direção* do erro. Vale
  com n=1, porque cada spot auditável tem resposta certa. *"Nesses 6 spots de
  15-25bb você deixou 5,3bb na mesa, todos na mesma direção"* é demonstrável.
- **não afirma**: frequência por faixa com amostra curta. Precisa de n≥60 *na
  faixa*, e a mão de torneio não é i.i.d. — quem quebra cedo só contribui com
  mãos de stack fundo, então o n por faixa é sempre desequilibrado e isso tem
  que aparecer.

`LinhaDaFaixa.direcao_confiavel` se **recusa** a afirmar direção quando o outro
lado teve menos de 5 chances.

---

## 4. Ciclo de problema — do erro ao plano, e do plano à alta

`app/analysis/problemas.py`. Seis estados, e cada um existe por um motivo:

| estado | significa |
|---|---|
| `observacao` | erro visto, sem denominador. **Não se fala com o aluno.** |
| `suspeita` | passou amostra e frequência, falhou custo ou recorrência |
| `problema` | passou os cinco portões. **Único estado que gera plano.** |
| `em_alta` | critério batido, em vigilância |
| `resolvido` | vigilância cumprida sem recaída |
| `arquivado` | sem oportunidade nova em 90 dias |

**`arquivado` separado de `resolvido` é o que impede o sistema de fabricar
vitória.** Quando o aluno para de jogar aquele spot — mudou de formato, de
stake, de horário — o problema não foi resolvido, ele **sumiu**. Um sistema
com três estados registra isso como sucesso e ensina o dono a confiar num
número que não aconteceu.

**Os cinco portões**, todos obrigatórios:

```python
MIN_OPORTUNIDADES = 20           # abaixo disso o posterior é o prior
MIN_OPORTUNIDADES_ESTIMADO = 30  # custo estimado exige mais evidência
MIN_CUSTO_BB100 = 0.75           # leak barato não merece 4 semanas
MIN_SESSOES = 3                  # erro numa noite só é tilt, não leak
MIN_DIAS = 10
MIN_PROCEDENCIA = 0.70           # print lido por visão não sustenta diagnóstico
```

**Teto de 1 problema ativo** (`MAX_ATIVOS = 1`). O argumento é **estatístico**,
não pedagógico: três problemas dividem as oportunidades por três e nenhum
fecha.

**Pré-requisito na frente do sintoma.** Não adianta abrir "defesa de BB" para
quem não calcula preço de pote — metade daquelas mãos ele erra pelo motivo
errado, e a intervenção certa é outra. `PREREQ` mapeia quem destrava quem.

**Critério de alta pré-registrado.** Escrito **antes** da intervenção e
gravado na *mesma* operação que abre o problema (`plano_de_estudo.revisar()`).
Gravar depois abriria a porta para escrever a régua já sabendo o resultado —
que é exatamente o viés que o pré-registro impede.

**Categoria de controle e o dever de mostrar acertos.** Um sistema que só acha
problema é um crítico, e crítico se abandona. `revisar()` devolve também o que
está de pé: *"limp de abertura: 30 spots, nenhum erro"*.

---

## 5. Medir evolução sem mentir

`app/analysis/evolucao.py`. Esta é a parte com maior chance de queimar a
confiança de novo, porque **"progresso" é o número que o dono mais quer ver e o
mais fácil de fabricar sem perceber**.

### A ameaça principal: regressão à média

O problema é escolhido **por ser o pior** — ou seja, por estar no extremo da
flutuação. A próxima janela melhora sozinha, sem nenhum aprendizado. Isso é
**sistemático**, não ruído: sem neutralização, a ferramenta declara "melhorou"
para praticamente todo mundo.

A defesa: **a linha de base nunca é a janela que diagnosticou**
(`baseline_valida()`), e a barra de coleta começa em **zero** no instante em
que o problema abre (`_oportunidades_depois()`). Contar as 30 mãos do
diagnóstico diria *"30 de 30"* — "você já chegou" antes de coletar uma única
mão nova.

> Este erro foi cometido **duas vezes**: guardado em `problemas.py` e
> reintroduzido uma camada acima em `plano_de_estudo.py`. Por isso existe teste
> nas duas.

### Por que o quiz não serve como medida

Cinco vieses, do pior para o menor:

1. **Contaminação pelo `leak_boost` — e é do nosso próprio código.** O sorteio
   puxa mais das categorias em que o aluno erra. Ótimo para *treinar*, fatal
   para *medir*: quando ele melhora, o boost cai, o mix de spots muda, e a taxa
   observada muda por mudança de **amostra**, não de habilidade. A série
   temporal do drill é ininterpretável por construção.
2. **Memorização** — o drill é sobre a mão *dele*, que ele já jogou e cuja
   análise já leu.
3. **Chance** — 3–4 botões dão 25–33% de acerto no chute. Daí `kappa()`,
   acurácia corrigida por acaso.
4. **Formato** — quiz é sem pressão, sem tempo, com o spot já isolado.
5. **Feedback imediato** ensina o item, não necessariamente o conceito.

A correção: `app/bot/repeticao.py` separa **treino** de **aferição** —
1 drill em 5 (`A_CADA = 5`) é sorteado uniformemente, sem boost, e só esses
entram na série temporal.

**E só a frequência em mão real dá alta.** O quiz mede conhecimento; a mesa
mede desempenho.

### Três vereditos, sendo `inconclusivo` obrigatório

`MELHOROU` · `NAO_MELHOROU` · `INCONCLUSIVO`

> Um sistema que só sabe dizer "melhorou" ou "não melhorou" vai dizer um dos
> dois quando a resposta certa é **"ainda não sei"**.

`INCONCLUSIVO` é o veredito mais frequente, e é assim de propósito.
`MINIMO_ABSOLUTO = 30` oportunidades por período, sem exceção.

### O tamanho de amostra é dito no dia 1

`n_necessario(taxa_antes, taxa_alvo)` — bilateral, alfa 5%, poder 80%:

| de → para | oportunidades por período |
|---|---|
| 60% → 30% | 42 |
| 50% → 25% | 58 |
| 40% → 20% | 81 |
| 50% → 30% | 93 |
| 30% → 15% | 120 |

Melhoras pequenas (50% → 40%) precisam de ~400 por período e **simplesmente
não são detectáveis** no volume de um aluno de clube. Quando a tabela não
cobre, a função devolve um número grande de propósito: é a forma de o sistema
dizer *"esse alvo é imensurável"* em vez de fingir que mede.

### Contexto mudou, comparação recusada

`contexto_mudou()` — 30% de mudança no mix (buy-in, formato, faixa de stack) e
a comparação é recusada. Antes e depois viram maçã com laranja.

---

## 6. Guardas — regra é pedido, conferência é garantia

Pedir no prompt não garante nada. Onde a garantia importa, existe um guarda
que **corrige** em tempo de execução (antes só registrava) e um teste que
cobra o guarda.

- **`app/bot/guarda_fatos.py`** — a análise afirma coisa que não é verdade? KK
  não perde para QQ. "A conta" tem que ter conta. Inclui dominância *invertida*
  ("**Só AA e QQ** te viram favorito" — as mãos vêm antes do verbo, o que a
  regex original não enxergava, e o texto real da lição era exatamente assim).
- **`app/bot/guarda_saida.py`** — a resposta responde o que foi pedido?
- **`app/agent/termos.py`** — corretor determinístico de terminologia em toda
  saída, com teste separado (`test_corretor_nao_estraga_portugues.py`) para
  que a correção não estrague português correto.
- **`app/bot/licao_qualidade.py`** — portão da lição destilada, **antes de ela
  falar com todos os alunos de uma vez**. Busca as cartas em tempo de *leitura*
  (`licoes.hand_analysis_id → hand_analysis.hand_id → hands.canonical`), para
  que o portão valha também para as 29 lições já engavetadas. Pega lição que
  generaliza de uma mão só, e lição que critica um tamanho e propõe outro
  menor.

**O prompt não pode ensinar o que proíbe.** `test_prompt_nao_ensina_o_que_proibe.py`
existe porque o exemplo dourado do próprio prompt usava os calques que a regra
bania — *top par*, *check atrás*, *sequência*.
`test_prompt_nao_briga_consigo.py` existe porque R7 contradizia R2.

---

## 7. Testes que valem — teste de mutação

Um teste que passa com o código quebrado é decorativo, e decorativo é pior que
ausente: dá a sensação de cobertura sem a cobertura.

O procedimento adotado: **quebre a linha de produção, rode o teste, confirme
que ele falha.** Foi assim que se descobriu que um teste de pixel da zona de
shove contava vermelho do texto "▼ pior mão" que fica **fora** do gráfico — o
teste passava com a linha do desenho apagada.

Mesmo procedimento aplicado ao guarda do runbook: apagar a correção do caminho
faz o teste falhar nomeando o arquivo.

---

## 8. O que a ferramenta se recusa a dizer — e o que disso está PROVADO

A lista, junta, é o contrato. A coluna da direita é o resultado da auditoria
de 09/08/2026, em que cinco agentes independentes tentaram furar cada
garantia rodando código, não lendo. **Um contrato sem essa coluna é uma
promessa, e este documento existe justamente porque promessa não basta.**

| Não diz | Condição | Estado verificado |
|---|---|---|
| VPIP / PFR / 3-bet | fonte não traz sessão inteira | ✅ no coach · ⚠️ 6 outros consumidores não consultam `publicavel` |
| qualquer taxa | menos de 30 mãos | ⚠️ **fura** — `/stats` publica com 12 |
| rótulo de estilo | menos de 100 mãos | ⚠️ **fura** — `/estilo` devolve "LAG" com 12 mãos |
| taxa sem intervalo | nunca | ⚠️ a frequência por faixa sai com `±`; `/stats` e `/estilo` ainda não |
| diagnóstico | 5 portões | ✅ vale, mas só para 2 dos 6 códigos (ver abaixo) |
| direção do erro | as taxas dos dois lados não se separam | ✅ teste de duas proporções; falsa direção sob H0 caiu de 99,5% para ≤5,2% |
| frequência por faixa | n < 60 na faixa | ✅ |
| "melhorou" | < 30 oportunidades no período | ✅ roda a cada envio de mãos (ligado em 09/08) |
| "melhorou" | contexto mudou > 30% | ⚠️ a função existe e `revisar()` ainda não passa o contexto |
| "resolvido" quando o aluno sumiu | → `arquivado` | ⚠️ `em_alta` já é alcançável; `arquivado` (90 dias sem spot) ainda não tem quem dispare |
| alta com base em quiz | sempre | ✅ por omissão — nada dá alta |

### Corrigido em 09/08 (commit `e1c0497`), cada um conferido por mutação

- **O portão principal não tinha teste.** Invertendo `processing.py:489` para
  `if not stats.publicavel` — o que manda o perfil cru ao modelo exatamente
  quando ele é impublicável — **os 971 testes passavam**. O teste comparava
  uma substring do código-fonte. Agora há teste de comportamento *e* um teste
  por AST que cobra que a condição exercitada seja a que está em produção —
  sem o segundo, o primeiro protege código que pode já não existir.
- **A linha legada furava a leitura.** `detail.get("publicavel") is False` não
  pega a chave *ausente*, que é a assinatura de toda linha gravada antes de o
  portão existir. Agora falha fechado.
- **O portão de conteúdo testava existência, não decisão.** `Street` não tem
  `__bool__`, e os parsers semeiam a street de preflop sempre. 120 `.txt`
  truncados davam `VPIP 0% · nit · publicavel=True`. A pergunta agora é se
  alguém decidiu alguma coisa.
- **O `/foco` misturava janelas.** O aluno lia *"42 escorregada(s) nessas 12"*.
  As duas metades da fração passam a vir da mesma população.
- **`lembrar()` quebrava sob concorrência.** O despejo itera com
  `next(iter(mapa))` enquanto outra thread insere; 4 escritores, 3 morreram em
  3 segundos. Latente (só dispara no teto de 200), mas roda no meio do upload
  fora de qualquer `except`.

### Aberto — a lista priorizada

Conferida por execução em 09/08, e não por memória. O que fechou saiu daqui.

**1. Não há paginação em `get_hands_para_perfil`.** Zero `.range()` no
repositório. O corte de 1.000 linhas do PostgREST trunca em silêncio, e as
mãos que não desceram são reportadas ao coach como "amostra curada" — mão
legítima descrita como escolhida a dedo. Só morde acima de 1.000 mãos por
aluno; o maior hoje tem 349.

**2. `ADMIN_TOKEN` em dois scripts de `deploy/oneshot/`.** O cookie já não é
o segredo mestre, mas `2026-08-02-link-do-portal*.sh` seguem no repo fazendo
`curl ".../admin?key=$ADMIN_TOKEN"` e mandando esse link por Telegram. Query
string vai para o log do Caddy.

**3. Frequência sem margem em `/stats` e `/estilo`.** A frequência por faixa
de stack já sai com `±`; esses dois comandos ainda não.

A lição estrutural é uma só, e já estava escrita na seção 7: **teste que
compara texto do código não é teste.** Cinco dos guardas mais importantes do
sistema eram protegidos exatamente assim, e o padrão se replicou porque
funciona — passa verde, parece cobertura, e só o teste de mutação separa uma
coisa da outra.

---

## Erros que este documento existe para não repetir

1. **Consertei a conta e não limpei a tabela.** A linha envenenada seguiu viva
   por dois dias. *Ninguém relê uma tabela.*
2. **Portão de procedência sem portão de conteúdo.** CSV passou e deu VPIP 0%
   com rótulo "nit".
3. **Denominador que engole a ação certa.** `bb_subdefesa` incluía a própria
   call do herói no "investido", tirando o acerto do denominador e inflando a
   taxa.
4. **Direção do erro como artefato do próprio instrumento.** 4 detectores
   passivos contra 2 largos fazem todo aluno parecer passivo.
5. **A janela que diagnostica usada como janela que mede.** Cometido duas
   vezes, em camadas diferentes.
6. **Nosso próprio `leak_boost` contaminando nossa própria medição.**
7. **Teste de pixel decorativo** que media texto fora do gráfico.
8. **Runbook apontando para pasta que nunca existiu** (`/app/backend`), o que
   faz a falha parecer venv quebrado e manda a investigação para o lado errado.

---

## Documentos irmãos

`ARQUITETURA.md` (mapa do código) · `../../OPERATIONS.md` (runbook) ·
`../../PLANO.md` (produto) · `../../BUSINESS_PLAN.md` (negócio) ·
`../../MANUAL.md` (usuário)
