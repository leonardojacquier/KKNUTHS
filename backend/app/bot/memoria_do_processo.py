"""A memória do processo tem TETO — antes era um dicionário que só crescia.

Onze mapas por telegram_id vivem no processo do bot (mãos recentes, contexto
da última análise, gráficos pendentes, paste cortado pelo Telegram...). Não
havia UM `pop` de despejo em nenhum: quem entrava nunca saía. Os `pop` que
existiam eram de CONSUMO — o handler pega o gráfico e some — e o que nunca
foi consumido ficava para sempre.

Medido nesta base (08/08), com a amostra real de mão do PokerStars:

    1 CanonicalHand  ~ 32 KB
    _RECENT_CAP      = 300 mãos por usuário
    1 usuário cheio  ~ 9.4 MB
    100 usuários     ~ 939 MB   -- só RECENT_HANDS

O bot roda em VPS com pm2. Com 100 alunos ele não fica lento: ele morre, e
o pm2 reinicia perdendo o contexto de conversa de TODO MUNDO ao mesmo tempo.

Despejo é seguro porque nada aqui é a fonte da verdade: `_user_hands` cai
para `repo.get_all_hands` quando a memória está vazia, e o drill pendente
também mora no banco (`set_pending_drill`). O que se perde num despejo é
latência, não dado.

LRU por ESCRITA: reinserir a chave joga para o fim (dict preserva ordem de
inserção), então `next(iter(mapa))` é sempre o mais parado.
"""
from __future__ import annotations

import logging
import os
import time

log = logging.getLogger("memoria")

# quantos USUÁRIOS cabem em cada mapa. 200 com o cap de 300 mãos dá ~1.9 GB
# no pior caso teórico de RECENT_HANDS, mas o pior caso exige 200 usuários
# com 300 mãos cada em memória ao mesmo tempo; o real hoje é 10 alunos e a
# maior amostra tem 97 envios. O teto existe para o dia em que não for.
TETO_USUARIOS = int(os.getenv("MEMORIA_TETO_USUARIOS", "200"))


def lembrar(mapa: dict, chave, valor, teto: int = TETO_USUARIOS) -> None:
    """Grava e despeja o mais parado quando o mapa passa do teto."""
    mapa.pop(chave, None)          # reinserir = marcar como recente
    mapa[chave] = valor
    while len(mapa) > teto:
        velho = next(iter(mapa))
        mapa.pop(velho, None)
        log.debug("memória cheia: despejei %s (teto %d)", velho, teto)


def esquecer(mapa: dict, chave) -> None:
    """Tira a chave do mapa — entrada zerada é entrada que não precisa ficar."""
    mapa.pop(chave, None)


def varrer_expirados(mapa: dict, ttl: float, agora: float | None = None,
                     quando=lambda v: v[0]) -> int:
    """Some com o que passou do prazo. Devolve quantos saíram.

    Os mapas de gráfico/documento/paste JÁ tinham TTL — mas só conferido na
    hora de consumir, com `pop`. O que nunca foi consumido (a resposta falhou,
    o aluno sumiu) nunca era olhado de novo, e PNG e HTML de relatório são o
    conteúdo mais pesado que o processo segura.
    """
    agora = time.time() if agora is None else agora
    mortos = []
    for chave, valor in mapa.items():
        try:
            if agora - float(quando(valor)) > ttl:
                mortos.append(chave)
        except Exception:
            mortos.append(chave)       # formato estranho não fica de lembrança
    for chave in mortos:
        mapa.pop(chave, None)
    return len(mortos)


def guardar_com_prazo(mapa: dict, chave, valor, ttl: float,
                      teto: int = TETO_USUARIOS, quando=lambda v: v[0]) -> None:
    """Grava um item com prazo: varre os vencidos e respeita o teto."""
    varrer_expirados(mapa, ttl, quando=quando)
    lembrar(mapa, chave, valor, teto)
