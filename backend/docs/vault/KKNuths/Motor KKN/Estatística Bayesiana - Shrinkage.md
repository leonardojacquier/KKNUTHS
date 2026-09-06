---
tags: [kknuths, motor-kkn]
---
# Estatística Bayesiana — Shrinkage

**Problema:** com poucas mãos, taxa crua mente ("3-bet 100%" com 1 oportunidade
— caso real que constrangeu o beta).

**Solução (beta-binomial):** cada taxa nasce ancorada no prior do field de MTT
e o dado real assume o controle conforme a amostra cresce. IC ~95% por
aproximação normal (sem scipy). AF por pseudo-contagens (não explode com
0 calls).

- Priors (média%, força em observações): VPIP (24, 40) · PFR (17, 40) ·
  3-bet (7, 25) · AF (2.0, 12)
- Superfícies: /stats, /estilo, quadro do torneio (3-bet e AF)
- Voz: "3-bet entre 5 e 14% — mande mais torneios que eu cravo"
- Código: `app/analysis/bayes.py` (shrunk_rate, shrunk_af, bayes_stats)

Kahneman conecta: é o antídoto da **lei dos pequenos números**.
