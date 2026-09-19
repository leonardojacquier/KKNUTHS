"""CONTADOR DE PROGRESSO — o aluno vê que a coisa está rodando.

Por que existe: um torneio com 150 mãos leva minutos. O bot dizia "✅
Recebido" e sumia. Sem sinal de vida, silêncio longo é indistinguível de
travamento — o aluno reenvia o arquivo, ou desiste.

E não foi só o aluno que se enganou: o `on_document` não registrava evento
nenhum ao RECEBER (só depois de analisar), então durante o processamento o
banco ficava idêntico ao de um bot morto. Passei uma hora investigando uma
queda que era só uma análise demorando.

Duas peças:
  • `marcar()` — o código síncrono de análise anuncia em que etapa está;
  • `acompanhar()` — tarefa async que edita UMA mensagem a cada poucos
    segundos com etapa + tempo decorrido.

Editar a mesma mensagem, e não mandar novas, é de propósito: o histórico do
aluno não vira uma parede de "ainda estou trabalhando".
"""
from __future__ import annotations

import asyncio
import logging
import time

log = logging.getLogger(__name__)

# telegram_id -> (texto da etapa, quando começou)
_PASSO: dict[int, tuple[str, float]] = {}

INTERVALO = 8.0          # segundos entre edições
_MOSTRA_A_PARTIR_DE = 6.0  # não polui análise rápida com contador


def marcar(telegram_id: int | None, texto: str) -> None:
    """Anuncia a etapa atual. Chamável do código SÍNCRONO de análise —
    é só escrita em dict, não bloqueia e não pode falhar."""
    if telegram_id:
        _PASSO[telegram_id] = (texto, time.monotonic())


def limpar(telegram_id: int | None) -> None:
    if telegram_id:
        _PASSO.pop(telegram_id, None)


def passo_atual(telegram_id: int | None) -> str | None:
    item = _PASSO.get(telegram_id or 0)
    return item[0] if item else None


def texto_do_contador(etapa: str | None, segundos: float,
                      titulo: str = "Analisando") -> str:
    """Mensagem do contador. PURA — testável sem Telegram nem relógio."""
    m, s = divmod(int(segundos), 60)
    tempo = f"{m}min {s:02d}s" if m else f"{s}s"
    corpo = etapa or titulo
    # a linha longa era escrita só para torneio ("Torneio grande leva alguns
    # minutos") e passou a aparecer também no solver pós-flop, que não tem
    # torneio nenhum. Frase que não bate com a etapa faz o aluno desconfiar
    # justamente do aviso que existe para ele NÃO desconfiar.
    aviso = ("\n\n_Isso leva alguns minutos — pode deixar aí que eu aviso "
             "quando terminar._" if segundos >= 45 else "")
    return f"⏳ *{corpo}…*\n`{tempo}`{aviso}"


async def acompanhar(mensagem, telegram_id: int,
                     titulo: str = "Analisando") -> asyncio.Task:
    """Começa a editar `mensagem` com etapa + tempo. Devolve a Task, que o
    chamador CANCELA quando o trabalho termina.

    Nunca deixa o contador derrubar a análise: toda falha de edição é
    engolida (mensagem apagada pelo aluno, rate limit, texto repetido).
    """
    inicio = time.monotonic()

    async def _tick() -> None:
        ultimo = ""
        try:
            while True:
                await asyncio.sleep(INTERVALO)
                decorrido = time.monotonic() - inicio
                if decorrido < _MOSTRA_A_PARTIR_DE:
                    continue
                texto = texto_do_contador(passo_atual(telegram_id),
                                          decorrido, titulo)
                if texto == ultimo:      # Telegram recusa edição idêntica
                    continue
                ultimo = texto
                try:
                    await mensagem.edit_text(texto, parse_mode="Markdown")
                except Exception as exc:
                    log.debug("contador não editou: %s", exc)
        except asyncio.CancelledError:
            raise

    return asyncio.create_task(_tick())


async def encerrar(tarefa: asyncio.Task | None, telegram_id: int | None,
                   mensagem=None, final: str | None = None) -> None:
    """Para o contador. Se `final` vier, deixa a mensagem com ele; senão
    apaga, para não sobrar um '⏳' órfão em cima da resposta pronta."""
    limpar(telegram_id)
    if tarefa:
        tarefa.cancel()
        try:
            await tarefa
        except (asyncio.CancelledError, Exception):
            pass
    if mensagem is None:
        return
    try:
        if final:
            await mensagem.edit_text(final, parse_mode="Markdown")
        else:
            await mensagem.delete()
    except Exception as exc:
        log.debug("contador não encerrou a mensagem: %s", exc)
