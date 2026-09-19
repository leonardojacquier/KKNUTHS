#!/usr/bin/env bash
# Reprocessa os uploads dos primeiros beta users com o parser corrigido — v2:
# a v1 dedupava por "primeiro visto" e podia gravar fragmento truncado por cima
# da mão completa; agora vence a versão mais completa de cada hand_id.
# Sai com código != 0 se qualquer usuário falhar (o deploy tenta de novo).
set -uo pipefail
cd /opt/poker-bot || exit 1

fail=0
for tgid in 8972465711 6104620007 6452742024; do
    echo "-- reprocessando uploads de $tgid --"
    PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/reprocess_uploads.py "$tgid" || fail=1
done
exit $fail
