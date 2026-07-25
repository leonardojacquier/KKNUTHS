"""Aviso IMEDIATO no chat, de dentro de uma ferramenta lenta.

Motivo (palavras do aluno sobre a espera do solver pós-flop): "foi isso que
me lascou". Ele pediu o gráfico, ficou olhando "Analisando sua colocação…"
por um minuto sem nenhum sinal de vida e concluiu — com razão — que a
ferramenta estava quebrada. O cálculo estava rodando; ele é que não tinha
como saber.

As tools rodam em thread separada (o handler chama process_followup via
asyncio.to_thread), então dá pra falar com o Telegram direto por HTTP aqui,
sem passar pelo loop do bot. É fire-and-forget: se o aviso falhar, o
trabalho continua — aviso que derruba a análise seria pior que o silêncio.
"""
from __future__ import annotations

import json
import logging
import urllib.request

log = logging.getLogger(__name__)


def avisar(telegram_id: int | None, texto: str) -> bool:
    """Manda uma mensagem solta pro chat. Nunca levanta exceção."""
    if not telegram_id or not texto:
        return False
    try:
        from app.config import get_settings

        token = get_settings().telegram_bot_token
        if not token:
            return False
        body = json.dumps({"chat_id": telegram_id, "text": texto[:800],
                           "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return bool(json.load(r).get("ok"))
    except Exception as exc:                       # rede/token/chat inválido
        log.debug("aviso de espera não saiu: %s", exc)
        return False


# quanto custa o equilíbrio por street, medido na máquina do deploy:
# flop ~57s, turn ~60s (carta amostrada em cada runout), river ~13s (exato)
ESPERA = {3: "cerca de 1 minuto", 4: "cerca de 1 minuto",
          5: "uns 15 segundos"}


def avisar_solver(telegram_id: int | None, board: list[str],
                  quantos_graficos: int = 2) -> bool:
    """O aviso específico do solver pós-flop: o que está rodando, quanto
    demora e o que vai chegar. Sem isso a espera parece pau."""
    from app.analysis.equity import pretty_cards

    street = {3: "flop", 4: "turn", 5: "river"}.get(len(board or []), "spot")
    tempo = ESPERA.get(len(board or []), "cerca de 1 minuto")
    volta = {0: "a conta", 1: "a conta e o *gráfico*"}.get(
        quantos_graficos, "a conta e os *2 gráficos*")
    return avisar(
        telegram_id,
        f"⏳ Resolvendo o equilíbrio do *{street}* {pretty_cards(list(board))} "
        f"— é CFR+ de verdade, mão a mão, e leva *{tempo}*.\n"
        f"Pode largar o celular: eu volto aqui com {volta} quando terminar. "
        f"(Não travou.)")
