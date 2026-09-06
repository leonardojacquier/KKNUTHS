#!/usr/bin/env bash
# Broadcast das novidades (manual novo) para todos os usuários do beta —
# pedido do admin em 05/07. Roda UMA vez (marcador do vps_deploy).
set -uo pipefail
cd /opt/poker-bot || exit 1

MSG='♠️ Novidades no KKNuths — seu coach de poker

Chegou uma leva grande de recursos novos. O que você pode fazer agora:

📊 SEU JOGO EM GRÁFICOS
• /estilo — cartão visual do seu estilo comparado aos grandes (Yuri Dzivielevski, Akkari, Dwan, Negreanu…). Quer mudar de jogo? Toque em "Virar LAG" (ou TAG/GTO) e receba o plano de transição.
• /evolucao — sua linha do tempo: VPIP, PFR, 3-bet e resultado em BB, com botões para ampliar cada indicador.
• /torneio — o quadro do seu último campeonato: curva do stack mão a mão, melhor e pior momento.

📐 RANGES E EV
• /range sb 10 ev — EV de cada mão no all-in (verde = empurrar rende mais)
• /range sb 10 icm 1.5 — o mesmo sob pressão de ICM (veja o range mudar na bolha)
• Ou peça na conversa: "me passa a tabela" — o gráfico chega em seguida.

📒 COACH COM MEMÓRIA
O coach agora mantém um caderno sobre o seu jogo: leaks, progressos e metas ficam anotados e ele cobra nas próximas análises. Veja no /stats.

📋 E FICOU MAIS FÁCIL ENVIAR
Cole a sessão inteira no chat — se o Telegram cortar em partes, eu junto tudo sozinho. Arquivos de GGPoker, PokerStars (até Zoom), Winamax, Party e 888, cash ou torneio.

Toque no botão de menu (/) para ver todos os comandos, ou mande /start. Bora estudar! 🃏'

fail=0
for chat in 8972465711 6104620007 6452742024; do
    echo "-- enviando novidades para $chat --"
    PYTHONPATH=/opt/poker-bot ./venv/bin/python scripts/tg.py send "$chat" "$MSG" \
        >/dev/null || fail=1
done
exit $fail
