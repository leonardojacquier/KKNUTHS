"""SAÚDE DA API — separar "me embananei" de "a conta acabou".

Aconteceu em 2026-07-27: os créditos da API zeraram, toda chamada ao modelo
passou a receber 400 «Your credit balance is too low», e o bot respondia ao
aluno *"Opa, me embananei aqui"*. Duas coisas erradas nisso:

  1. O ALUNO leva a culpa implícita. "Me embananei" diz que o coach se
     confundiu — some a confiança dele na ferramenta, sendo que o problema
     é a fatura. Com dez testadores entrando, esse é o pior primeiro
     contato possível.
  2. O DONO não fica sabendo. O erro virava um evento silencioso no banco;
     ele descobriu xingando, não sendo avisado.

Isto classifica a falha e avisa o admin UMA vez por janela — alarme que
repete a cada chamada é alarme que se desliga.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.request

log = logging.getLogger(__name__)

ADMIN_ID = 6452742024
_SILENCIO_ENTRE_AVISOS = 1800.0     # 30 min: não repetir a cada chamada
_ultimo_aviso: dict[str, float] = {}

# (marca no texto do erro, tipo, o que o ALUNO lê)
_FALHAS = (
    ("credit balance is too low", "sem_credito",
     "Estou com um problema no meu lado (a conta da IA precisa de "
     "recarga). Já avisei o suporte — tenta de novo daqui a pouco."),
    ("insufficient_quota", "sem_credito",
     "Estou com um problema no meu lado (a conta da IA precisa de "
     "recarga). Já avisei o suporte — tenta de novo daqui a pouco."),
    ("rate_limit", "limite",
     "Estou recebendo muita coisa ao mesmo tempo. Me manda de novo em "
     "um minutinho que eu pego a sua."),
    ("authentication_error", "chave",
     "Estou com um problema de configuração no meu lado. Já avisei o "
     "suporte — volta daqui a pouco."),
    ("invalid_api_key", "chave",
     "Estou com um problema de configuração no meu lado. Já avisei o "
     "suporte — volta daqui a pouco."),
    ("overloaded", "sobrecarga",
     "O motor está congestionado agora. Tenta de novo em um minuto."),
)

_URGENTE = {"sem_credito", "chave"}     # exige ação humana, não passa sozinho


def classificar(exc: BaseException | str | None) -> tuple[str, str] | None:
    """(tipo, mensagem para o aluno) — ou None se não é falha de infra.

    Erro que NÃO é de infraestrutura devolve None de propósito: aí o
    "me embananei" continua correto, porque o problema é mesmo do modelo.
    """
    texto = str(exc or "").lower()
    if not texto:
        return None
    for marca, tipo, recado in _FALHAS:
        if marca in texto:
            return tipo, recado
    return None


def texto_do_alerta(tipo: str, detalhe: str) -> str:
    """Mensagem para o ADMIN. PURA."""
    titulos = {
        "sem_credito": "🚨 *CRÉDITO DA API ACABOU*",
        "chave": "🚨 *CHAVE DA API INVÁLIDA*",
        "limite": "🟡 *Rate limit na API*",
        "sobrecarga": "🟡 *API sobrecarregada*",
    }
    acao = {
        "sem_credito": "\n\n👉 console.anthropic.com → *Plans & Billing* → "
                       "adicionar créditos. Volta na hora, sem deploy.",
        "chave": "\n\n👉 conferir `ANTHROPIC_API_KEY` no .env do VPS.",
    }.get(tipo, "")
    return (f"{titulos.get(tipo, '🚨 *Falha na API*')}\n\n"
            f"Toda análise está caindo no fallback — o aluno recebe uma "
            f"mensagem de erro no lugar da análise.{acao}\n\n"
            f"`{detalhe[:300]}`")


def _avisar_admin(texto: str) -> None:
    from app.config import get_settings

    token = get_settings().telegram_bot_token
    if not token:
        return
    corpo = json.dumps({"chat_id": ADMIN_ID, "text": texto[:3500],
                        "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=corpo, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


# última falha de infra vista, para quem monta a resposta ao aluno: o erro
# morre lá no `_create` e a mensagem é escrita muitas camadas acima
_ultima: tuple[float, str, str] | None = None
JANELA_RECADO = 180.0    # 3 min: além disso, "me embananei" volta a ser
                         # a explicação honesta (pode ter sido outra coisa)


def recado_recente(agora: float | None = None) -> str | None:
    """O que dizer ao ALUNO se acabou de haver falha de infraestrutura.

    Janela curta de propósito: culpar a infra por um erro de meia hora atrás
    seria trocar uma explicação errada por outra.
    """
    if not _ultima:
        return None
    quando, _tipo, recado = _ultima
    agora = agora if agora is not None else time.monotonic()
    return recado if agora - quando <= JANELA_RECADO else None


def registrar(exc: BaseException | str | None,
              agora: float | None = None) -> tuple[str, str] | None:
    """Classifica, avisa o admin (no máximo 1x por 30 min por tipo) e grava
    o evento. Devolve o que o ALUNO deve ler, ou None.

    Nunca levanta: é chamada de dentro do tratamento de erro, e uma exceção
    aqui apagaria a falha original.
    """
    try:
        achado = classificar(exc)
        if not achado:
            return None
        tipo, recado = achado
        agora = agora if agora is not None else time.monotonic()

        global _ultima
        _ultima = (agora, tipo, recado)

        if agora - _ultimo_aviso.get(tipo, -1e9) >= _SILENCIO_ENTRE_AVISOS:
            _ultimo_aviso[tipo] = agora
            _avisar_admin(texto_do_alerta(tipo, str(exc or "")))
            try:
                from app.db import get_repository

                get_repository().log_event(
                    0, "saude_api", "api_indisponivel",
                    {"tipo": tipo, "urgente": tipo in _URGENTE,
                     "erro": str(exc or "")[:400]})
            except Exception:
                pass
        return tipo, recado
    except Exception as exc2:
        log.debug("saude: falhou ao classificar (%s)", exc2)
        return None
