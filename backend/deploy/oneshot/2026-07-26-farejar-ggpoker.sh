#!/usr/bin/env bash
# Descobre de onde a GGPoker serve a mão de um replay compartilhado.
#
# O ambiente de desenvolvimento não alcança gg.gl (a política de rede nega o
# CONNECT) e não há SSH. Este é o canal: o deploy roda isto UMA vez aqui, e a
# saída completa volta pelo Telegram do admin + fica em bot_events
# (event='farejar') para consulta por SQL depois.
#
# Só leitura. O link é o que o próprio jogador compartilha — nada de login,
# nada de conta de sala.
set -uo pipefail
cd /opt/poker-bot || exit 1

LINK="https://gg.gl/fovbb"

echo "== para onde o encurtador aponta =="
curl -sIL --max-time 25 "$LINK" 2>&1 | grep -iE '^(HTTP|location)' | head -20

echo
echo "== farejador =="
PYTHONPATH=/opt/poker-bot ./venv/bin/python \
    scripts/farejar_e_reportar.py "$LINK"

# sai 0 sempre: "não achei" é resultado válido e não deve marcar o oneshot
# como falho (falha faria ele repetir a cada deploy, sem nada novo a dizer)
exit 0
