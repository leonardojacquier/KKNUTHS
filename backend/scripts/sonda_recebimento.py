"""SONDA DE RECEBIMENTO — o bot ainda ESCUTA?

Por que existe: em 2026-07-26 o banco tinha 104 eventos em 6 horas e nenhum
deles era de gente — todos de cron. Passei uma hora investigando uma queda
que não existia (o bot estava analisando um torneio), e a conclusão
incômoda foi outra: se fosse queda de verdade, **nada** teria avisado.

Nenhum monitor existente cobre isto, e por um motivo comum: todos rodam em
processo PRÓPRIO e não tocam no Telegram. `jornadas` passa 8/8 com o bot
morto. `nightly_coherence` idem. `output_judge` julga texto do banco.
`daily_usage` reporta número baixo às 23h, sem alarme. E a `e2e_probe`
nunca rodou uma vez sequer.

Checagens, e só fala quando algo está errado:

  1. WEBHOOK registrado — a falha mais silenciosa que existe: o processo
     fica verde, o log limpo, e o long-polling não recebe nada. Certeza,
     não suspeita.
  2. `getMe` falhando — separa "token quebrado/revogado" de "não recebe".
  3. SILÊNCIO humano longo demais em horário ativo — só suspeita, porque
     madrugada calma é normal. Por isso nunca alarma sozinho no vermelho.
  4. O SITE responde — acrescentado em 09/08, e pela mesma razão que criou
     esta sonda. São DOIS processos no pm2 (`poker-bot` e `poker-web`), e
     tudo que existia olhava só o primeiro: o portão do auto-deploy conferia
     `pm2 describe poker-bot`, esta sonda conferia o Telegram. O site podia
     cair — e caiu — com o bot verde, o deploy anunciando sucesso e ninguém
     avisado até o dono abrir o navegador.

O item 4 tem dois lados de propósito, porque eles quebram por motivos
diferentes e o remédio é outro:

  * `127.0.0.1:8014` é a aplicação. Falhou aqui: uvicorn morreu ou a rota
    explode — `pm2 logs poker-web` conta.
  * `https://poker.vortex369.com.br` é a borda. Local ok e público não:
    Caddy, DNS ou certificado — o app está de pé e ninguém alcança.

O item 3 só é confiável porque `upload_recebido`/`print_recebido` passaram
a ser gravados ANTES da análise. Antes disso esta sonda teria dado
exatamente o mesmo falso positivo que eu dei.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ADMIN_ID = 6452742024
FUSO_BR = timezone(timedelta(hours=-3))
HORA_ATIVA = (10, 2)        # 10h às 02h BRT — fora disso, silêncio é normal
SILENCIO_ALERTA_H = 3.0     # horas sem gente, dentro do horário ativo

# o site, dos dois lados: aplicação e borda
WEB_LOCAL = "http://127.0.0.1:8014"
WEB_PUBLICO = "https://poker.vortex369.com.br"

# eventos de SISTEMA não contam como sinal de vida: são justamente eles que
# enchiam o banco enquanto o bot podia estar mudo
_SISTEMA = (0,)


def em_horario_ativo(agora_br: datetime) -> bool:
    """Janela que atravessa a meia-noite (10h→02h)."""
    h = agora_br.hour
    inicio, fim = HORA_ATIVA
    return h >= inicio or h < fim


def avaliar(webhook_url: str | None, getme_ok: bool,
            horas_de_silencio: float | None, ativo: bool,
            web: tuple[bool, str] | None = None) -> dict:
    """Decide o veredito. PURA — testável sem rede e sem banco.

    `nivel`: 'ok' | 'suspeita' | 'quebrado'. Só 'quebrado' é certeza, e por
    isso é o único que justifica acordar alguém de madrugada.

    `web` é `(ok, motivo)` ou None. None significa NÃO CHECADO e nunca vira
    alarme — mesma regra do silêncio: "não sei" não acorda ninguém.
    """
    problemas: list[str] = []
    nivel = "ok"

    if web is not None and not web[0]:
        # site fora é certeza, não suspeita: ou responde, ou não responde
        nivel = "quebrado"
        problemas.append(web[1])

    if webhook_url:
        nivel = "quebrado"
        problemas.append(
            f"WEBHOOK registrado ({webhook_url[:60]}) — enquanto existir, o "
            "long-polling NÃO recebe nada. Corrigir com deleteWebhook "
            "(drop_pending_updates=false para não perder a fila).")
    if not getme_ok:
        nivel = "quebrado"
        problemas.append("getMe falhou — token inválido/revogado ou API fora.")

    if (horas_de_silencio is not None and ativo
            and horas_de_silencio >= SILENCIO_ALERTA_H):
        problemas.append(
            f"{horas_de_silencio:.1f}h sem NENHUMA interação humana em "
            "horário ativo (cron não conta).")
        if nivel == "ok":
            nivel = "suspeita"

    return {"nivel": nivel, "problemas": problemas,
            "webhook": webhook_url or "", "getme_ok": getme_ok,
            "silencio_h": horas_de_silencio, "horario_ativo": ativo,
            "web_ok": None if web is None else web[0]}


def texto_do_alerta(v: dict) -> str:
    """Mensagem para o admin. PURA.

    O título diz O QUE caiu. Chamar queda do site de "BOT NÃO ESTÁ
    RECEBENDO" manda o dono depurar o processo errado.
    """
    if v["nivel"] == "ok":
        return ""
    icone = "🚨" if v["nivel"] == "quebrado" else "🟡"
    web_caiu = v.get("web_ok") is False
    bot_caiu = bool(v.get("webhook")) or v.get("getme_ok") is False
    if web_caiu and bot_caiu:
        titulo = "*BOT E SITE FORA*"
    elif web_caiu:
        titulo = "*SITE FORA DO AR*"
    elif v["nivel"] == "quebrado":
        titulo = "*BOT NÃO ESTÁ RECEBENDO*"
    else:
        titulo = "*Suspeita: bot sem movimento*"
    corpo = "\n".join(f"• {p}" for p in v["problemas"])
    rodape = ("\n\n_Suspeita, não certeza: pode ser só um período calmo._"
              if v["nivel"] == "suspeita" else "")
    return f"{icone} {titulo}\n\n{corpo}{rodape}"


def checar_web(local: str = WEB_LOCAL, publico: str = WEB_PUBLICO
               ) -> tuple[bool, str]:
    """A aplicação responde, e a borda entrega? I/O isolada aqui.

    Não basta `/health`: ele é uma rota de três linhas que responde 200 com o
    resto do site quebrado. Por isso confere também a landing — página real,
    com template e assets — e exige tamanho de página, não só o status.
    """
    def _pega(url: str) -> tuple[int, int, str]:
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                return r.status, len(r.read()), ""
        except Exception as exc:                      # noqa: BLE001
            return 0, 0, f"{type(exc).__name__}: {exc}"

    st, _, err = _pega(f"{local}/health")
    if st != 200:
        return False, (f"SITE fora: {local}/health não respondeu "
                       f"({err or st}). O uvicorn caiu ou a rota explode — "
                       f"`pm2 logs poker-web --lines 50`.")
    st, tam, err = _pega(f"{local}/")
    if st != 200 or tam < 1000:
        return False, (f"SITE de pé mas a página quebrou: {local}/ deu "
                       f"{err or st} ({tam} bytes). `pm2 logs poker-web`.")

    st, tam, err = _pega(f"{publico}/health")
    if st != 200:
        return False, (f"App de pé, BORDA fora: {publico} não respondeu "
                       f"({err or st}) mas o 127.0.0.1:8014 respondeu. "
                       f"Caddy, DNS ou certificado — não é o app.")
    return True, ""


# ------------------------------------------------------------------- I/O
def _api(token: str, metodo: str) -> dict | None:
    try:
        with urllib.request.urlopen(
                f"https://api.telegram.org/bot{token}/{metodo}",
                timeout=20) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _avisar(token: str, texto: str) -> None:
    corpo = json.dumps({"chat_id": ADMIN_ID, "text": texto[:3500],
                        "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=corpo, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


def horas_desde_o_ultimo_humano(repo) -> float | None:
    """Idade do último evento de GENTE. None se não der para saber — e
    'não sei' nunca vira alarme."""
    try:
        linhas = (repo.client.table("bot_events").select("created_at")
                  .not_.in_("telegram_id", list(_SISTEMA))
                  .order("created_at", desc=True).limit(1)
                  .execute().data) or []
    except Exception:
        return None
    if not linhas:
        return None
    try:
        quando = datetime.fromisoformat(
            str(linhas[0]["created_at"]).replace("Z", "+00:00"))
    except Exception:
        return None
    return (datetime.now(timezone.utc) - quando).total_seconds() / 3600


def main() -> int:
    from app.config import get_settings
    from app.db import get_repository

    token = get_settings().telegram_bot_token
    if not token:
        print("sem token — nada a checar")
        return 0

    info = _api(token, "getWebhookInfo") or {}
    webhook = ((info.get("result") or {}).get("url") or "") if info else ""
    getme_ok = bool((_api(token, "getMe") or {}).get("ok"))

    repo = get_repository()
    silencio = horas_desde_o_ultimo_humano(repo) if repo.enabled else None
    ativo = em_horario_ativo(datetime.now(FUSO_BR))

    v = avaliar(webhook, getme_ok, silencio, ativo, web=checar_web())
    print(json.dumps(v, ensure_ascii=False))

    if repo.enabled:
        try:
            repo.log_event(0, "sonda_recebimento", "sonda_recebimento", v)
        except Exception:
            pass

    texto = texto_do_alerta(v)
    if texto:
        _avisar(token, texto)
    return 1 if v["nivel"] == "quebrado" else 0


if __name__ == "__main__":
    sys.exit(main())
