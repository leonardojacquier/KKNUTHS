---
tags: [kknuths, motor-kkn, moat]
---
# Calibração por Showdown — o moat de dados

Cada showdown revela as cartas de um vilão → cada ação pós-flop dele vira
observação rotulada (ação, tipo de mão na street). As contagens da base
inteira calibram as likelihoods do [[Leitura de Vilão - Range Tracker]] via
blend bayesiano: pouco dado → prior manda; base grande → o field REAL assume.

- Parser captura `shows [..]` / `showed [..]` → `shown_cards` no modelo
- Batch: `scripts/calibrate_likelihood.py` (cron semanal, seg 5h) →
  `calibration.json` no VPS (fora do git; protegido do rsync --delete)
- Tracker carrega o arquivo se existir; senão usa o prior
- Dedupe por (site, hand_id) — a mesma mão de dois usuários conta 1×

**Flywheel:** mais usuários → mais showdowns → leituras melhores p/ TODOS →
mais usuários. No manual aparece só como "aprende com a base" (mecanismo é
segredo — ver [[Estratégia e Moat]]).
