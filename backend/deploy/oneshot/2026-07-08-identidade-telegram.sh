#!/usr/bin/env bash
# Identidade do bot no Telegram: descrição + short via API, e o avatar da
# logo enviado ao admin com o passo a passo do BotFather (a foto de perfil
# só o dono consegue trocar).
set -uo pipefail
cd /opt/poker-bot || exit 1

fail=0
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/set_bot_identity.py || fail=1
PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/tg_send_doc.py 6452742024 \
    app/api/assets/logo_avatar.png \
    "♠ Avatar oficial do bot. Para colocar: abra @BotFather → /setuserpic → escolha @KKNUts_BOT → envie esta imagem COMO FOTO (não como arquivo). 1 minuto e o bot ganha cara." || fail=1
exit $fail
