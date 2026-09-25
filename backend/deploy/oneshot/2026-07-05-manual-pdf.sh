#!/usr/bin/env bash
# Envia o Manual do Jogador em PDF para os usuários do beta (uma vez).
set -uo pipefail
cd /opt/poker-bot || exit 1

PDF=app/api/assets/KKNuths-Manual.pdf
CAP='♠ Manual do Jogador — KKNuths. Tudo que o coach faz por você, com as imagens reais. E ele agora vive no bot: mande /manual quando quiser.'

fail=0
for chat in 8972465711 6104620007 6452742024; do
    echo "-- enviando manual PDF para $chat --"
    PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/tg_send_doc.py "$chat" "$PDF" "$CAP" || fail=1
done
exit $fail
