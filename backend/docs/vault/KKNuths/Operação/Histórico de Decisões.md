---
tags: [kknuths, operacao, decisoes]
---
# Histórico de Decisões (resumo)

- **Stacks nunca estimados** — bug "12bb vs 58bb" (era o valor do BB); análise
  passa stacks + stack efetivo; regra dura no prompt; teste de regressão
- **Motor KKN sempre ligado e invisível** — qualidade não é opção; flags só
  p/ rollout; profundidade sob demanda no chat
- **Selo de decisão = veredito do coach** — selo determinístico divergia do
  texto ("decisão ✅" + "jogou passivo demais"); fonte única
- **Relatório automático no upload** — era só script manual; virou default
  (REPORT_AUTO como alavanca de plano)
- **Voz do coach** — informal, veredito primeiro; proibido papo de sistema e
  "resumo brutal"; simplificação como botão
- **Nobel factual** — "baseado na ciência que ganhou…"; 2 Nobels (Kahneman
  2002, Nash 1994), ambos genuinamente usados
- **Suite hermética** — testes offline em qualquer ordem (gate queimava
  tokens reais)
- **Jam/fold transposto** — matriz Nash invertida corrigida e validada contra
  tabela de referência
- **Quota fail-closed** + upsert de mãos por chave natural (reenvio não duplica)
- **Veredito não se sorteia** — 99 recebeu "3-bet" e "call" em runs
  diferentes (temperature 1.0 + sem âncora); temperature 0.2/0.0 via
  wrapper `_create` + veredito preflop preso ao `preflop_range` +
  coerência entre mensagens ([[Coerência Gráfico-Análise]])
- **Número do aluno é insumo** — narração na legenda alimenta as tools;
  dado faltante vira pergunta, nunca "não dá pra calcular"
- **Print ilegível + narração = analisa pela narração** — fallback
  extract_from_hand_text(caption); "não li" só sem fonte nenhuma
- **hand_id por fingerprint** — todo print era 'vision-snapshot' e o
  upsert fazia cada foto SOBRESCREVER a anterior; sha1[:12] do conteúdo
  (reenvio deduplica, foto nova ganha linha)
- **Gráfico = mesmo número do veredito** — auditoria de 11 incoerências
  gráfico↔texto; invariantes em [[Coerência Gráfico-Análise]]
- **Glossário central (TERMOS_REGRA)** — calques banidos (par grande,
  rua/etapa p/ street…) nas 3 camadas de texto; registro sempre 'você'

## 2026-07-26
- **Regra é pedido, conferência é garantia** — 3 pedidos de gráfico viraram
  prosa com o motor pronto; 4 regras no prompt não resolveram. Nasceu o
  [[Guarda da Saída]], que confere a entrega ANTES de mandar
- **Taxa de entrega vira métrica** — antes era opinião minha e o defeito só
  aparecia por print do aluno
- **Construtor único de contexto** (`abrir_conversa`) que LEVANTA se a
  conversa não tem mão nem declara `sem_mao` — quiz e simulador gravavam
  sem `hand_id` e toda ferramenta de mão morria depois deles
- **Canário é regra, não lista** — o anterior conferia duas strings
  literais: era whitelist e não pegava arquivo novo
- **Sonda de jornadas > sonda E2E** — a `e2e_probe` NUNCA rodou (depende de
  conta-teste que nunca foi criada). A nova roda em processo, sem custo, e
  pergunta "chegou o que o aluno pediu?", não "deu erro?"
- **Multiway não se aproxima por independência** — medido: erra até 14
  pontos. Monte Carlo real ([[EV Multiway e Potes Paralelos]])
- **Herói tira as cartas ANTES do board** — o board saía de um baralho que
  ainda continha as cartas do herói; viés de +3 a 6 pontos de equity
- **Sem equity confiável, a opção não é oferecida** — `except` silencioso
  removido; melhor calar que devolver conta errada
- **Custo em DÓLAR, não em créditos** — `record_usage` gravava o inteiro 1;
  nenhum preço era defensável ([[Custo de LLM]]). Modelo fora da tabela vira
  `usd=None` + aviso: custo falso é pior que custo nenhum
- **Teto por plano** (free 50 / piloto 100 / pro ilimitado); plano
  desconhecido cai no FREE, nunca no ilimitado ([[Pricing e Planos]])
- **Não vender dentro do Telegram** — Stars custa ~32% no celular; Pix
  externo com webhook custa ~1%. Risco de política declarado
- **Só anunciar preço depois de medir o custo no piloto**
- **Resposta de erro é informação** — 403 do CloudFront e corpo `-1` foram
  descartados como "falhou" e eram as melhores pistas do dia
  ([[Ingestão de Replays de Clube]])
- **Parser só se escreve com o formato REAL na mão** — um parser inventado
  passa nos testes que eu mesmo escrevo e quebra na primeira mão de verdade,
  que é pior que não ter porque parece pronto
- **Biblioteca não faz I/O sozinha** — teste gravou fixture no `/tmp` do VPS
  durante o gate e o admin leu como se fosse captura real; outro saiu
  batendo em domínio inexistente. Efeito colateral só sai de `main()`
