---
tags: [kknuths, operacao, backlog]
---
# Backlog

## Piloto de 10 usuários (2026-07-26)
- [ ] Convidar os 10 testadores (folder pronto, SEM link — `Acesso por convite`)
- [ ] `/planode <id> piloto` para quem precisa de 100 análises
- [ ] Testar link da Suprema no bot ponta a ponta
- [ ] `/prova` numa mão da Suprema (confere pote e potes paralelos contra o
      gabarito da própria sala)
- [ ] Deixar o piloto rodar 1 semana e LER o `/quem` — é o custo real que
      libera a conversa de preço ([[Custo de LLM]])
- [ ] Criar a conta-teste do `e2e_probe` **ou** aposentar a sonda de vez
      (ela nunca rodou; a de jornadas cobre o essencial)

## Curto prazo
- [ ] DNS poker.vortex369.com.br → VPS + Caddy (comando já fornecido)
- [ ] Foto de perfil do bot via @BotFather (avatar pronto)
- [ ] Repo privado + rotação de todas as chaves do início
- [ ] Instagram: publicar os 3 posts de teste; medir 3-4 dias
- [ ] Meta: ativar IG no Business certo (rollout do conector pendente)

## Produto
- [ ] Fase 4+ calibração: sizing nas observações de showdown (bet_small vs big)
- [ ] Auto-import (e-mail/watcher de pasta)
- [ ] "Você vs field" expandido; páginas SEO de charts na landing
- [ ] Quiz adaptativo (Bayesian Knowledge Tracing) quando /treino tiver tração
- [ ] B2B: skin de portal para clubes
- [ ] Publicação orgânica no Instagram via API (conta Profissional + Página)

## Monetização
- [ ] **Depois do piloto, na ordem:** roteamento Opus/Haiku (corte esperado
      de 50–65% no custo) → rail Pix externo com webhook → comandos de
      promoção (`/creditar`, `/liberar`, cupom no .env)
- [ ] free=sob demanda / Pro=automático via REPORT_AUTO; "solver avançado"
      como linha Pro
- [ ] **Não** vender dentro do bot: Stars custa ~32% no celular
      ([[Pricing e Planos]])

## Dívida conhecida
- [ ] Solver postflop é heads-up; multiway entrega conta, não matriz
- [ ] `suprema_replay` como fonte EXATA em `procedencia.py` existia antes do
      parser (rótulo órfão) — hoje é verdade, mas o padrão de declarar
      suporte antes de existir se repetiu
- [ ] Fixture `tests/sample_hands/suprema_replay.json` tem apelidos REAIS de
      jogadores de clube (terceiros). Avaliar anonimizar
