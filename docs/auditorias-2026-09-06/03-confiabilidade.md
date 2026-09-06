# Anexo 3 — Auditoria de confiabilidade (SRE)

*Agente SRE, 06/09/2026. Base: commit `c315347`. Medido aqui: `pytest
--collect-only` = 1.695 testes; suíte completa = 1.695 passed em 573 s
(9m33s). Os scripts assumem "~3 min" (`vps_deploy.sh:50`, `auto_update.sh:131`).*

## 1. Linha do tempo de incidentes (reconstruída dos comentários)

| Data | O que quebrou | Causa raiz | O que foi feito | Fonte |
|---|---|---|---|---|
| 09/07 | Print GG lido como "98331bb" | Visão mistura fichas × bb | Backfill 29/07 | `oneshot/2026-07-29-backfill-unidades.sh` |
| 17-20/07 | Naipes/showdown errados no replay PPPoker; Suprema não abria | Parser JSON do CDN | Reparse, sondas | `oneshot/2026-07-17-*`, `2026-07-20-sonda-suprema-*` |
| 26/07 | 1 h investigando "queda" que não existia | Nada distinguia bot mudo de ocupado; recebimento só logado depois | `upload_recebido` antes de analisar; sonda horária | `sonda_recebimento.py:3-12`; `handlers.py:1114` |
| 26-27/07 | **275 restarts em laço**, `run_polling()` retornando limpo | Não documentada | Foreground, diagnóstico | `oneshot/2026-07-27-diagnostico-bot-parado.sh` |
| 27/07 | Crédito Anthropic zerou; aluno lia "Opa, me embananei"; dono soube "xingando" | 400 tratado como confusão | `saude.py` | `saude.py:3-15` |
| 28-29/07 | Antônio: print com blinds 15000/30000 e stacks em bb → tudo /30000 = 0; **nunca voltou** | Visão não coere unidades | `_coerir_unidades`; oneshot de desculpa | `llm.py:3089`; `anomalias.py:8-12` |
| 01-03/08 | 53% do custo LLM era reescrita de cache | TTL 5 min | TTL 1 h | `llm.py:1098-1106` |
| 02/08 | `ADMIN_TOKEN` na query string por Telegram → log do Caddy | Oneshot | **Ainda no repo** | `oneshot/2026-08-02-link-do-portal.sh:29-38`; `METODO.md:433` |
| 07/08 | Deploy sumiu sem erro | `auto_update.sh` sobrescreve a si mesmo | Re-exec de cópia | `auto_update.sh:8-22` |
| 07/08 | "Bot na versão anterior" era mentira: disco tinha código reprovado | rsync antes do pytest | Portão no clone | `auto_update.sh:71-79` |
| 07/08 | `POST /telegram/webhook` sem auth: qualquer POST forjava o dono | Código morto público | Removida | `main.py:26-42` |
| 07/08 | "KK só perde para QQ ou AA"; cooler imaginado; ICM `bf/(1+bf)` errava +18 pp; 0/25 torneios citavam ICM | Modelo narra; fórmula sem pote morto | `guarda_fatos`, `historia`, `icm`, `torneio` | `guarda_fatos.py:3`; `icm.py:84`; `torneio.py:3` |
| 09/08 | **Site caiu com bot verde e deploy anunciando sucesso** | Portão só via `pm2 describe` | `web_responde()` via HTTP | `auto_update.sh:114-129` |
| 09/08 | Portão `publicavel` invertido e **971 testes passavam**; `lembrar()` crash sob concorrência | Testes de texto; sem lock | Testes por comportamento; lock | `METODO.md:401-421`; `memoria_do_processo.py:51` |
| 13/08 | Nota 2.5: aluno recebeu "Vou usar a leitura…"; stub "VOCÊ (Tc Kh) em ?" entregue | Narração virava resposta; plano C era stub | `_resgatar_conclusao`, plano C digno | `llm.py:1881`; `analyzer.py:437` |
| 16/08 19:19 | **Meia frase entregue como análise**; `stop_reason` nunca lido; resgate recolava `tool_use` → 400; **rollback às cegas** (3 reverts) | Teto no p99; sinal ignorado; except mudo | Teto 4.000, corte nunca entregue, `plano_c` vira evento | `llm.py:27-36,1860,2176`; git `1b8b24d`… |
| 18/08 | Torneio de 192 mãos: principal cortou em 4.000, resgate em 2.500, aluno recebeu 1 linha; **16 lotes cortados**, única pista = reclamação | Teto sem alvo; `json.loads` tudo-ou-nada | Tetos próprios, `_pares_completos` | `llm.py:49-71`; `handreport.py:227-238` |
| 21/08 | **Causa raiz da semana**: sonnet-5 liga thinking se omitido; 2.500 tokens = um bloco `[thinking]`; conversa respondeu 3× sobre a mão errada; PPPoker mudou domínio (.ph) | Parâmetro omitido; rótulo enganava | `thinking: disabled`, modelo reserva, rótulo "Última mão ANALISADA" | `llm.py:1123-1135`; `link_do_clube.py:23` |

**Padrão:** 60 scripts em `deploy/oneshot/`. Incidentes de LLM dominam agosto e quase todos têm a mesma forma: **o sinal existia e ninguém lia.**

## 2. Pontos de falha silenciosa

| # | Sev. | Onde | O que acontece |
|---|---|---|---|
| 2.1 | **alto** | `processing.py:683` + `handlers.py:1130` | `consume_quota` ANTES do envio. Telegram falha → cota + dólar gastos, análise gravada, **nunca entregue**, sem evento distinto |
| 2.2 | **alto** | `db/repository.py:20-35` | `_safe`: TODA falha de banco vira `log.warning` + `None`. Análise sem persistir, `bot_events` mudo. **Nenhum alerta ao admin** |
| 2.3 | **alto** | `sonda_recebimento.py:222` | Testa `getMe` — o TOKEN, não o PROCESSO. O laço de 275 restarts passaria |
| 2.4 | **alto** | `vps_deploy.sh:63,75` | `pm2 restart` a cada push mata `to_thread` em voo: aluno no "Analisando…" para sempre |
| 2.5 | médio | `llm.py:2006,2077,1929` | `plano_c`, `analise_cortada` com `telegram_id=0` — **não dá para saber qual aluno** |
| 2.6 | médio | `custo.py:134`; `llm.py:1145` | Contabilidade em `except: log.debug` — `/quem` subestima sem avisar |
| 2.7 | médio | `handreport.py:376` | Falha de rede num lote → 6 mãos no veredito determinístico, sem evento |
| 2.8 | médio | `speech.py:31`; `embeddings.py:30` | Chave OpenAI morta: voz e RAG degradam. `saude.py` só cobre Anthropic |
| 2.9 | médio | `daily_quiz.py:35`; `weekly_report.py:33` | Envio falho some; sem dead-man's-switch para cron ausente |
| 2.10 | médio | `auto_update.sh:84-87` | `pip install \|\| true` no venv de PRODUÇÃO antes do portão |
| 2.11 | médio | `vps_deploy.sh:116`; `jornadas.py:3` | Sonda E2E "dorme" sem credenciais nunca criadas — zero eventos `e2e` desde que existe |
| 2.12 | médio | `vps_deploy.sh:85-98` | `.oneshot-done/` só em `/opt/poker-bot`; perdido → 60 scripts rodam de novo, inclusive broadcasts |
| 2.14 | baixo | `saude.py:99`, `notify.py:67` | Alerta de que o Telegram caiu sai pelo Telegram |

53 blocos `except Exception: pass` em `app/` (18 em `handlers.py`).

## 3. Dependências externas

| Dependência | Retry | Fallback | Aviso ao admin | Sev. |
|---|---|---|---|---|
| **Anthropic** | 4 tentativas, backoff 1→8 s em 408/409/429/5xx/529 (`llm.py:1083-1095`) | resumo determinístico; modelo reserva opus; `_NO_TEMP`/`_NO_THINK` | só por substring (`credit balance`, `rate_limit`…) (`saude.py:31-49`), 1×/30 min | médio |
| **Telegram** | nenhum nas respostas | `_safe_reply` só Markdown; `_on_error` genérico | sonda horária — **pelo próprio Telegram** | **alto** |
| **Supabase** | nenhum; sem timeout | `_safe` → no-op; cota fail-closed | **nenhum** (backup avisa 1×/dia) | **alto** |
| Redis/RQ | — | — | — | baixo — **nunca importado**; dependência morta |
| CDN PPPoker | nenhum; timeout 15 s; host fixo `alicdn.pppoker.club` | `upload_failed` + texto | `anomalias` ≥3/dia às 21h | médio — já trocou domínio |
| Suprema | nenhum; host escolhido por 1 char do token entre 3; UA/Origin spoofados | idem | idem | médio — depende de CORS-bypass |
| Whisper/OpenAI | nenhum | "pode escrever?" | nenhum | médio |
| yt-dlp/ffmpeg | nenhum; yt-dlp sem timeout nem teto de bytes | texto + evento | só evento | médio |
| Playwright | nenhum | `None` | nenhum | baixo |

## 4. Custo e abuso

Cota: `check_quota` conta `usage_events` do mês (`quota.py:104-121`); só `consume_quota` grava (`processing.py:683`, único chamador). Free 50 (`.env.example` diz 100), piloto 100, pro/premium ilimitado. Admin isento.

| # | Sev. | Achado |
|---|---|---|
| 4.1 | **crítico** | **A cota só cobre `process_upload`.** `process_followup` (`processing.py:1150-1276`), `/ask`, `/simular`, `/preparar`, `/dossie`, `/leitura`, `/spot` não chamam `check_quota`. Cada mensagem = até 1.200 tokens + 5 rodadas de tool; `solve_river` roda CFR+ **até 75 s de CPU**. Sem rate-limit por usuário. Free com 0 análises tem LLM + CPU ilimitados — e `texto_cota_esgotada` (`quota.py:161-169`) **o convida** |
| 4.2 | **alto** | **1 unidade de cota ≠ 1 chamada.** Torneio = coach 6.000 + resgate 4.000 + conferência + selo + **até 25 lotes** + retentativas + embedding. 50 torneios/mês > 1.000 chamadas |
| 4.3 | médio | Whisper sem teto; vídeo até 30 min por link (~US$0,18), sem limite/dia |
| 4.4 | médio | Paste 400 k chars; documento 2 MB; foto sem checagem própria |
| 4.5 | baixo | `_count_used` read-then-write sem transação; ok com 1 processo |

`custo.py` mede tokens e USD por chamada Anthropic (tabela estática "2026-06-24"). **Não mede:** Whisper, embeddings, banda, CPU do solver.

## 5. Observabilidade

**O dono vê:** `/quem`, `/planode`, `/prova`, `/termo`, `/licoes`; portal `/admin`; cadastro novo na hora; resumo 23h; anomalias 21h; juiz 8h; backup 4h; jornadas 7h; sonda horária; aviso de deploy.

**NÃO dá para ver:** processo morto/em laço; Supabase fora; chave OpenAI morta; qual aluno recebeu plano C; latência; disco (OPERATIONS.md:92 diz que "lota"; nenhum script checa `df`); cron ausente; pip/oneshot falhando. `/health` só diz se as chaves existem.

## 6. Deploy e rollback

| # | Sev. | Achado |
|---|---|---|
| 6.1 | **alto** | Suíte **9m33s**, não "~3 min". Push leva 4–12 min, na mesma CPU do bot e de outros dois sites |
| 6.2 | **alto** | **Rollback só para "não subiu".** Código que passa e está errado → revert + ciclo (16/08: 3 reverts). Snapshot de 1 geração em `/tmp`. Sem "voltar para o último OK" |
| 6.3 | médio | Dois pushes com testes de 8 min: `flock` sai calado; dois restarts em ~20 min; se A abortar, B desbloqueia A sem testar A |
| 6.4 | médio | Venv de produção mutado antes do portão; `pip install --upgrade pip` a cada deploy — PyPI fora = deploy falha |
| 6.5 | médio | Crontab reescrito por substring a cada deploy — cron manual apagado |
| 6.6 | baixo | `test_deploy_testa_antes_de_copiar.py` é lint de texto |

## 7. Segurança

| # | Sev. | Achado |
|---|---|---|
| 7.1 | **alto** | Anthropic, OpenAI, BotFather e Supabase service_role **passaram por chat**; rotação pendente desde 15/08 (`OPERATIONS.md:131`). Dois oneshots ainda mandam `admin?key=$ADMIN_TOKEN` por Telegram. Repo era público; deploy key pendente |
| 7.2 | médio | `ADMIN_ID = 6452742024` hardcoded em ≥8 arquivos |
| 7.3 | ok | Comandos de admin conferem ID e registram tentativa. Webhook não autenticado removido. Stripe valida assinatura. Portal com sessão HMAC |
| 7.4 | médio | Documento ≤2 MB, tipo só por extensão; voz sem teto; yt-dlp sem teto de bytes. Links de replay: allowlist de hosts — **sem SSRF** |
| 7.5 | médio | Injeção de prompt: sem defesa explícita; tools com efeito escopadas ao próprio aluno via contextvar |
| 7.6 | baixo | Backups JSON.gz **sem cifra** no VPS compartilhado |

## O que quebraria primeiro com 10× alunos

1. **Custo e CPU da conversa sem cota** — o solver de 75 s serializa no executor do único processo.
2. **Um VPS, um processo, deploy que reinicia a cada commit** — cada push vira incidente. `TETO_USUARIOS=200` a um passo.
3. **`bot_events` como tabela de tudo** — janelas fixas (5.000; 3.000/24 h; 30 páginas) truncam calado.
4. **Alarme de um destinatário** — vira ruído e o dono desliga.
5. **Dependências sem retry** — o CDN da PPPoker trocando domínio numa noite de torneio; o primeiro a saber é o aluno.
