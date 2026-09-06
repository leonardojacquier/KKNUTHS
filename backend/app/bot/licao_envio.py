"""Motor de envio da lição — usado pelo comando /licoes e pelo cron.

Um só lugar: o dono aprovar com `/licoes N ok` DISPARA na hora, e o cron
diário só varre o que sobrou na fila. Antes o envio morava no script e o
comando só marcava — o dono aprovava e esperava até o outro dia sem ver
nada acontecer.

TRAVA ANTI-RAJADA: se já saiu lição nas últimas horas, a aprovação seguinte
vai pra FILA em vez de disparar. Aprovar três seguidas não vira três pushes
no telefone do aluno — é a diferença entre um canal que ele espera e um que
ele silencia.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timedelta, timezone

ADMIN_ID = 6452742024
JANELA_ANTI_RAJADA_H = 6.0


def texto_da_licao(licao: dict) -> str:
    """Formata a lição para o aluno. Termina SEMPRE com o convite à mão —
    é o único CTA que ataca o gargalo do produto."""
    # SEM "(custou X bb)". Esse número vem de hand_analysis.ev_loss, que
    # apesar do nome guarda `net_bb` — o RESULTADO líquido da mão, não o EV
    # da decisão (repository.py:225). Colado numa lição ele vira resultadismo
    # com cara de conta: a auditoria achou uma lição de uma mão GANHA
    # (+40.8bb) anunciada como "custou 37,4bb", e o call de KK — que estava
    # certo — saindo como "custou 12,5bb". É o pecado que R5 do prompt
    # proíbe, entrando pelo encanamento em vez de pelo texto.
    #
    # O texto da lição já é obrigado a trazer o número que a prova (ver
    # _PROMPT em scripts/destilar_licoes.py). Um número a mais, medindo outra
    # coisa e chamado de custo, só ensina errado.
    return (f"📖 *Lição do dia — {licao['titulo']}*\n\n"
            f"{licao['spot']}\n\n"
            f"{licao['licao']}\n\n"
            "———\n"
            "_Spot real de um aluno, anonimizado._ 🃏 *Manda uma mão sua* "
            "(print, arquivo ou link do replay) que eu analiso na hora.")


def proxima_licao(repo) -> dict | None:
    """A mais antiga aprovada e ainda não enviada — fila FIFO, sem repetir."""
    linhas = (repo.client.table("licoes").select("*")
              .eq("aprovada", True).is_("enviada_em", "null")
              .order("id").limit(1).execute().data) or []
    return linhas[0] if linhas else None


def horas_desde_o_ultimo_envio(repo, agora: datetime | None = None
                               ) -> float | None:
    """Horas desde a última lição entregue. None se nunca saiu nenhuma."""
    agora = agora or datetime.now(timezone.utc)
    linhas = (repo.client.table("licoes").select("enviada_em")
              .not_.is_("enviada_em", "null")
              .order("enviada_em", desc=True).limit(1).execute().data) or []
    if not linhas or not linhas[0].get("enviada_em"):
        return None
    try:
        quando = datetime.fromisoformat(
            str(linhas[0]["enviada_em"]).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (agora - quando).total_seconds() / 3600.0


def pode_disparar_agora(horas: float | None,
                        janela: float = JANELA_ANTI_RAJADA_H) -> bool:
    """Função pura: nunca enviou (None) ou já passou a janela."""
    return horas is None or horas >= janela


def _post(token: str, chat_id: int, texto: str) -> bool:
    body = json.dumps({"chat_id": chat_id, "text": texto[:4000],
                       "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r).get("ok", False)
    except Exception:
        return False


def enviar_licao(repo, token: str, licao: dict) -> dict:
    """Manda a lição para todos os alunos e fecha a lição (enviada_em).

    Devolve {'enviados', 'fila'}. Marcar como enviada é o passo que garante
    que ela nunca repete — vem DEPOIS do laço e antes do aviso ao dono.
    """
    texto = texto_da_licao(licao)
    users = (repo.client.table("users").select("telegram_id")
             .execute().data) or []
    enviados = 0
    for u in users:
        tg = u.get("telegram_id")
        if not isinstance(tg, int) or tg <= 0:
            continue
        if _post(token, tg, texto):
            repo.log_event(tg, None, "licao_recebida", {"licao": licao["id"]})
            enviados += 1

    repo.client.table("licoes").update({
        "enviada_em": datetime.now(timezone.utc).isoformat(),
        "publicada": True}).eq("id", licao["id"]).execute()
    fila = (repo.client.table("licoes").select("id", count="exact")
            .eq("aprovada", True).is_("enviada_em", "null")
            .execute().count or 0)
    repo.log_event(0, "licao_do_dia", "licao_do_dia",
                   {"licao": licao["id"], "enviados": enviados,
                    "titulo": licao["titulo"], "fila": fila})
    return {"enviados": enviados, "fila": fila}
