"""O botão 🔍 do relatório mão a mão: do HTML de volta para o bot.

O relatório de torneio é um arquivo HTML — o aluno lê fora do Telegram, e até
aqui a única ponte de volta era a frase "me manda o Nº da mão no chat". O dono
pediu o atalho: *"...e coloca o botão"*. Cada mão do relatório ganha um link
`t.me/<BOT>?start=mao_<Nº da sala>`, e clicar dispara a análise COMPLETA
daquela mão.

Três decisões moram aqui, todas com o porquê:

**Qual id vai no payload.** O Telegram limita o payload de `/start` a 64 chars
de `[A-Za-z0-9_-]`. A tabela `hands` tem duas chaves possíveis: `id` (uuid da
linha, 36 chars, globalmente único) e `hand_id` (o Nº da sala). Vai o `hand_id`
por três motivos: (a) é o único id disponível no ponto em que o HTML é
montado — `build_report_html` recebe `CanonicalHand`, não linhas de banco, e
levar o uuid até lá exigiria encanamento novo em `processing.py`, que está no
teto de linhas; (b) é o MESMO número impresso no card da mão ("mão TM6146…"),
então o aluno consegue ver para onde o botão vai; (c) o uuid é globalmente
único, e para autorização isso é passivo, não ativo — ele aponta para uma
linha que pode ser de OUTRO aluno, obrigando a ler o dado alheio só para
depois recusar.

**Autorização.** O link é público e encaminhável: vai parar no grupo do clube.
A busca já nasce escopada em quem clicou (`get_hand_by_room_id(user_id, …)`),
então a mão de outro dono nunca é lida do banco — não há dado a vazar, nem
sequer para comparar. Quem clica num link alheio recebe recusa educada.

**Cota.** Conta como análise normal: é uma análise de mão completa, com o mesmo
custo de LLM de qualquer outra, e cobrar diferente por causa de onde o aluno
clicou seria uma regra que ninguém consegue explicar. Sai de graça porque o
caminho reaproveitado (`process_upload`) já é quem faz o portão e o consumo.

Este módulo é FOLHA em relação ao `processing`: importa `process_upload` só
dentro da função, porque o `processing` importa `maos_ja_lidas` daqui no topo.
"""
from __future__ import annotations

import logging
import re

from app.config import get_settings
from app.db import get_repository

log = logging.getLogger("mao_do_relatorio")

# prefixo do payload de /start — o galho que separa "vim do convite X" de
# "quero a mão Y". Curto de propósito: cada char gasto aqui é um char a menos
# de Nº de mão.
PREFIXO = "mao_"

# rótulo de formato do "upload" que o botão gera. Nome próprio (em vez de
# reaproveitar "txt") para o funil do portal conseguir medir quanta análise
# nasce do relatório — que é a pergunta que decide se o botão valeu.
FORMATO = "mao_do_relatorio"

# Telegram: `?start=` aceita no máximo 64 chars, alfanuméricos mais `_` e `-`.
MAX_PAYLOAD = 64
_MAX_ID = MAX_PAYLOAD - len(PREFIXO)
_ID_OK = re.compile(r"[A-Za-z0-9_-]+")

RECUSA = (
    "🔒 Esse link é de uma mão que não está no seu histórico.\n\n"
    "Cada aluno só abre as próprias mãos aqui — mão de poker é dado pessoal, "
    "e eu não mostro a de ninguém para outra pessoa.\n\n"
    "Me manda a SUA mão (print, texto ou arquivo) que eu analiso na hora! 🃏"
)

SEM_BANCO = (
    "😅 Não consigo abrir mãos guardadas agora — deu um engasgo do meu lado.\n"
    "Me manda a mão aqui no chat (print ou texto) que eu analiso na hora."
)


def link_da_mao(hand_id: str | None) -> str | None:
    """URL do botão 🔍 para uma mão, ou None quando o Nº não cabe no link.

    Nº com char fora do alfabeto do Telegram, ou longo demais, geraria um
    botão que abre o bot e PERDE a mão — o aluno clica e recebe as boas-vindas
    no lugar da análise. Não prometer botão é melhor que entregar botão morto:
    o relatório continua dizendo para mandar o Nº no chat.
    """
    if not _cabe_no_payload(hand_id):
        return None
    return (f"https://t.me/{get_settings().telegram_bot_username}"
            f"?start={PREFIXO}{hand_id}")


def id_no_payload(ref: str | None) -> str | None:
    """Nº da mão dentro do payload de /start, ou None se o payload não é nosso.

    None é resposta de rota, não erro: o `/start` de convite ("?start=site")
    tem que seguir para as boas-vindas de sempre.
    """
    if not ref or not ref.startswith(PREFIXO):
        return None
    hand_id = ref[len(PREFIXO):]
    return hand_id if _cabe_no_payload(hand_id) else None


def _cabe_no_payload(hand_id: str | None) -> bool:
    return bool(hand_id) and len(hand_id) <= _MAX_ID \
        and bool(_ID_OK.fullmatch(hand_id))


def maos_ja_lidas(maos: list | None):
    """Mãos que já vieram CANÔNICAS (do banco) no formato do pipeline de upload.

    `process_upload` começa por `ingest()`, que transforma bytes em
    `CanonicalHand`. Aqui a mão já é canônica: reingerir seria reparsear um
    texto de sala que não existe mais. Devolver um `IngestResult` pronto é o
    que permite reaproveitar o pipeline INTEIRO — selo, placar street a
    street, guardas de fatos e de voz, memória, cota — trocando uma linha no
    `processing`, em vez de duplicar a orquestração.

    None quando não há mão pronta: o chamador segue para o `ingest` normal.
    """
    if not maos:
        return None
    from app.ingestion.pipeline import IngestResult

    return IngestResult(
        list(maos), maos[0].site, FORMATO, confidence=maos[0].confidence,
        needs_review=False,
        note="mão reaberta pelo botão do relatório mão a mão")


def analisar_do_link(telegram_id: int, username: str | None,
                     ref: str | None) -> str | None:
    """Análise completa da mão apontada pelo link, para o DONO dela.

    None quando o payload não é de mão (o `/start` segue o caminho normal).
    """
    hand_id = id_no_payload(ref)
    if not hand_id:
        return None
    repo = get_repository()
    if not repo.enabled:
        return SEM_BANCO
    user = repo.get_or_create_user(telegram_id, username)
    # a consulta JÁ nasce escopada no clicador: não existe o passo "achei a
    # mão do outro e depois recusei", que é onde vazamento costuma morar
    mao = repo.get_hand_by_room_id(user["id"], hand_id) if user else None
    if mao is None:
        # evento próprio: link encaminhado é sinal de que o relatório está
        # circulando, e a taxa de recusa diz se o botão vira porta errada
        repo.log_event(telegram_id, username, "mao_do_link_negada",
                       {"mao": hand_id[:40]})
        return RECUSA
    repo.log_event(telegram_id, username, "mao_do_link", {"mao": hand_id[:40]})
    from app.bot.processing import process_upload

    # o `content` vai com o canônico da mão: o pipeline arquiva o bruto do que
    # ingeriu, e um arquivo vazio quebraria essa linhagem de auditoria.
    return process_upload(mao.model_dump_json().encode(), FORMATO,
                          telegram_id, username, maos=[mao])
