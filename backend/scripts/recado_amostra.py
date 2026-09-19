"""Recado de UM tiro: o aluno que perdeu o perfil quando o portão entrou.

O VPIP 94,3% do Ricardo saiu de 53 replays que ELE escolheu mandar. Não foi
amostra pequena — foi viés de seleção: com 5.000 replays escolhidos por ele
o número daria o mesmo. A conta foi consertada, a linha envenenada foi
limpa, e o efeito colateral é que ele deixa de ter perfil.

Ele vai notar. Deixar que note sozinho é pior do que contar — e o dono
aprovou o texto antes deste arquivo existir.

Por que um script e não uma migração: mandar mensagem para uma pessoa real é
irreversível. Fica explícito, com o destinatário no código, rodado à mão, e
IDEMPOTENTE — o evento `recado_amostra` no `bot_events` é a trava, então
rodar duas vezes não manda duas vezes.

    cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python scripts/recado_amostra.py
    (acrescente --seco para ver o texto sem enviar)
"""
from __future__ import annotations

import sys

from app.config import get_settings
from app.db import get_repository

DESTINATARIO = 6921203436          # Ricardo Farah
EVENTO = "recado_amostra"

TEXTO = """Ricardo, preciso te falar de um erro meu.

Eu andei te dizendo que seu VPIP estava em 94%. Estava errado — e não foi \
erro de conta, foi de amostra.

Suas mãos aqui vieram de replay avulso: você manda a mão que achou \
interessante. E ninguém manda o replay de uma mão que largou no pré. Ou \
seja, eu estava medindo com que frequência você entra no pote usando *só as \
mãos em que você entrou*. Ia dar quase 100% de qualquer jeito — com 92 \
replays ou com 5.000.

Consertei, e o conserto tem um custo: *não vou mais te dar VPIP, PFR nem \
rótulo de estilo*. No PPPoker e na Suprema não existe export de sessão \
inteira, então eu não tenho como medir sua frequência de forma honesta. \
Prefiro te dizer "não sei" a te dar um número que te faria mudar o jogo à \
toa.

O que *não* muda — e é a maior parte: análise de cada mão que você mandar, a \
conta de equity e preço, o EV das suas decisões, treino, leitura de vilão, \
gráfico de range. Tudo isso é sobre *aquela mão* e não depende de amostra \
nenhuma.

E tem uma coisa que eu passo a fazer melhor: em vez de tentar dizer quem \
você é, eu digo quanto custou o que você fez. Manda os replays do mesmo \
jeito."""


def ja_enviado(repo) -> bool:
    """A trava. Sem ela, um segundo `python scripts/...` manda de novo — e
    repetir um pedido de desculpas é pior que não ter feito."""
    try:
        return bool((repo.client.table("bot_events").select("id")
                     .eq("telegram_id", DESTINATARIO).eq("event", EVENTO)
                     .limit(1).execute().data))
    except Exception:
        return True        # na dúvida, NÃO manda


def main() -> int:
    seco = "--seco" in sys.argv
    if seco:
        print(TEXTO)
        return 0

    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase — não dá para conferir se já foi enviado")
        return 1
    if ja_enviado(repo):
        print("já enviado antes; não repito")
        return 0

    token = get_settings().telegram_bot_token
    if not token:
        print("sem TELEGRAM_BOT_TOKEN")
        return 1

    from app.bot.licao_envio import _post

    if not _post(token, DESTINATARIO, TEXTO):
        print("o Telegram recusou o envio")
        return 1
    repo.log_event(DESTINATARIO, None, EVENTO, {"motivo": "portao_de_amostra"})
    print("recado enviado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
