---
tags: [kknuths, produto]
---
# Comandos do Bot

| Comando | O que faz |
|---|---|
| /start | menu inicial (welcome agrupado) |
| /stats | perfil (VPIP/PFR/3-bet/AF corrigidos por amostra) + leaks em bb/100 + KKN Tilt Detector + comparação com pros + caderno do coach |
| /estilo | cartão visual do estilo vs arquétipos (TAG/LAG/GTO/exploit) + transição de estilo como meta |
| /evolucao | linha do tempo com gráficos; botões por indicador (VPIP·PFR·3bet·AF·BB) |
| /torneio | quadro do último campeonato (curva de stack + 2 fileiras de KPIs) |
| /relatorio | reenvia o [[Relatório Mão a Mão]] do último torneio |
| /simular | rejoga uma mão real do usuário decisão a decisão, com botões |
| /treino | drill profissional de um spot real (contexto, preço, gabarito com conta) |
| /range | gráficos 13×13: `btn` (open), `sb 10` (Nash), `sb 10 ev`, `sb 10 icm 1.5` |
| /ask | busca semântica no histórico do próprio usuário |
| /manual | manual do jogador em PDF |
| /plano | plano REAL do aluno + quantas análises restam no mês |
| /spot | spot avulso do motor (open_shove, reshove, squeeze, call_shove) |
| /prova | a ferramenta se auditando nas mãos DO aluno (8 classes) |
| /vilao /leitura /banca /preparar | leitura de oponente, banca e briefing pré-torneio |

## Entrada de mãos
Print/foto · `.txt` de hand history · texto colado (remonta paste cortado) ·
**link de replay: PPPoker e Suprema abrem sozinhos**
([[Ingestão de Replays de Clube]]). Outros clubes recebem mensagem que
NOMEIA o clube e oferece print/descrição.

## Comandos de operação (só o dono, silenciosos para o aluno)
| Comando | O que faz |
|---|---|
| /quem [telegram_id] | custo de LLM do mês: total, por tarefa, por aluno e US$/análise ([[Custo de LLM]]) |
| /planode | sem argumento: lista alunos com telegram_id, plano e uso do mês |
| /planode `<id\|@nome> <plano>` | troca o plano, CONFERE no banco antes de confirmar e avisa o aluno |

`update_user_plan` engole exceção — confirmar sem reler seria dizer "✅
pronto" sobre gravação que pode não ter acontecido. Apelido que casa com
mais de uma pessoa é recusado, para não mudar o plano do errado.

Extras de conversa: botão **🎈 Explica mais simples** em toda resposta do coach;
quiz diário 19h; resumo semanal domingo 18h; aviso de espera antes do solver
(`app/bot/notify.py` — ~1 min no flop/turn, ~15s no river).
