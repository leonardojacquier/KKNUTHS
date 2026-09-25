#!/usr/bin/env bash
# Retorno ao Ricardo: o .zip da GG que o bot recusou em 08/09 agora entra.
#
# 08/09 15:20 e 15:23: ele mandou o histórico do Mini Heater (GG, 07/09) em
# .zip e ouviu "formato 'zip' não suportado" duas vezes. Era o usuário mais
# pesado do piloto (232 mãos); depois disso, dois quizzes e nada mais.
# Corrigido em b904f37. Envio autorizado pelo dono em 25/09.
#
# TRAVA: antes de mandar, abre um .zip de verdade com o código IMPLANTADO.
# Se não sair mão, nada vai pro aluno — só pro dono. Prometer de novo uma
# coisa que não funciona seria pior que o silêncio.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import io, json, os, pathlib, traceback, urllib.request, zipfile

TOKEN = os.environ.get("TG_TOKEN", "")
DONO = 6452742024
ALUNO = 6921203436                       # Ricardo Farah

MENSAGEM = (
    "Fala, Ricardo! Aqui é o Leo, do KKNuths. No dia 8 você mandou o "
    "histórico do Mini Heater da GG em .zip e o bot respondeu \"formato não "
    "suportado\" — duas vezes. O erro foi nosso: o arquivo estava certo, o "
    "bot é que não abria zip.\n\n"
    "Já está corrigido. Pode mandar o .zip do PokerCraft do jeito que ele "
    "baixa, que o bot abre e analisa as mãos de dentro. Se quiser um formato "
    "específico (nota de 1 a 10, certas × erradas), é só escrever na "
    "legenda.\n\n"
    "Se ainda tiver aquele torneio de 07/09, manda de novo — quero ver a "
    "análise sair. Valeu pela paciência. 🙏"
)


def mandar(chat, texto):
    if not TOKEN:
        print("sem TELEGRAM_BOT_TOKEN")
        return False
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": texto}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30)
        return True
    except Exception as exc:
        print(f"envio falhou ({chat}): {exc}")
        return False


try:
    from app.db import get_repository
    from app.ingestion.pipeline import ingest

    amostra = pathlib.Path("tests/sample_hands/gg_tournament_paste.txt")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("GG20260907 - Tournament #310131883.txt", amostra.read_bytes())
    r = ingest(buf.getvalue(), "zip")
    diag = f"autoteste zip: {len(r.hands)} mão(s), site={r.site}, nota={r.note!r}"
    print(diag)

    if not r.hands:
        mandar(DONO, "[ricardo] NÃO enviei: o .zip não abriu no código "
               "implantado.\n" + diag)
    else:
        enviado = mandar(ALUNO, MENSAGEM)
        get_repository().log_event(ALUNO, "Ricardo Farah", "retorno_enviado",
                                   {"motivo": "zip", "ok": enviado})
        mandar(DONO, f"[ricardo] {'enviado' if enviado else 'FALHOU'}.\n"
               f"{diag}\n\n--- cópia do que ele recebeu ---\n" + MENSAGEM)
except Exception:
    mandar(DONO, "[ricardo] EXCEÇÃO:\n" + traceback.format_exc()[-2000:])
PY

exit 0
