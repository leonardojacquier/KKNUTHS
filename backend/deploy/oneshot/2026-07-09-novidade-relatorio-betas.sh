#!/usr/bin/env bash
# Anuncia o /relatorio aos dois betas — o Beta 2 pediu textualmente "análise
# completa de todas as mãos" antes de o comando existir.
set -uo pipefail
cd /opt/poker-bot || exit 1

fail=0
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/tg.py send 6104620007 \
"📋 Novidade: você pediu a análise completa de todas as mãos — agora ela existe. Manda /relatorio que eu te entrego o torneio inteiro, mão por mão: minha análise em cada mão, o selo de decisão separado do resultado e uma versão mais simples de cada leitura. Quer abrir alguma mão específica? Me manda o Nº dela (vem no relatório) ou as cartas aqui no chat. 🃏" || fail=1

PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/tg.py send 8972465711 \
"📋 Novidade no coach: /relatorio — o relatório mão a mão do seu último torneio, na hora que você quiser. Cada mão com análise, selo de decisão separado do resultado e uma versão mais simples de cada leitura. E qualquer mão que quiser discutir, me manda o Nº dela ou as cartas aqui no chat que a gente abre juntos. 🃏" || fail=1
exit $fail
