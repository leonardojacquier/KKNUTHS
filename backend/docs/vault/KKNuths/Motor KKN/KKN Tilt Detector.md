---
tags: [kknuths, motor-kkn, exclusivo]
---
# 🚨 KKN Tilt Detector

**Exclusividade** — nenhum HUD mede. Base: Teoria da Perspectiva (Kahneman,
Nobel 2002): perder dói ~2×; perdendo, viramos buscadores de risco.

## Como funciona (`app/analysis/mental.py`)
- Gatilho: pote de ±15bb → janela das 8 mãos seguintes
- Compara VPIP na janela vs linha de base DO PRÓPRIO jogador, com shrinkage
  ancorado na base (força 12) — mínimo 6 mãos em janelas p/ diagnosticar,
  desvio mínimo 8 pontos
- **tilt_chase**: abre demais após perder ("você abre 42%; sua base é 24% —
  perseguindo prejuízo; saldo nessas 27 mãos: −31bb")
- **medo_de_ganhar**: trava após pote grande GANHO
- Superfície: bloco "🚨 KKN Tilt Detector" no /stats; fecha com "o plano é o
  mesmo antes e depois do pote grande"

Marketing: *"Seu HUD mostra o que você joga. O KKNuths mostra quando você
desmorona — e quanto custa."*
