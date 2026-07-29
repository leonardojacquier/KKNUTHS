#!/usr/bin/env bash
# Reprocessa a 1ª mão do Antônio com as unidades corrigidas e manda pra ele.
#
# 29/07 19:09: primeiro print da vida dele na ferramenta. A sala mostrava o
# nível em fichas (15000/30000) e a mesa em bb (17.4), a visão transcreveu as
# duas escalas, tudo dividiu por 30000 e virou zero. O coach respondeu
# pedindo o stack efetivo — que estava na foto. Ele não voltou desde então.
#
# Aqui a mão volta a rodar pelo caminho REAL do produto (analyze_hand +
# coach, com as tools de equity/push-fold), não por um texto escrito à mão.
#
# TRAVA: se a análise sair fraca (curta, sem o stack, ou pedindo dado de
# novo), NADA vai pro aluno — só pro dono. Errar duas vezes com o mesmo
# usuário é pior que não mandar.
set -uo pipefail
cd /opt/poker-bot || exit 1

TG_TOKEN=$(grep -m1 '^TELEGRAM_BOT_TOKEN=' .env | cut -d= -f2- | tr -d '"'"'"' \r')
export TG_TOKEN

PYTHONPATH=/opt/poker-bot ./venv/bin/python - <<'PY'
import json, os, traceback, urllib.request

TOKEN = os.environ.get("TG_TOKEN", "")
DONO = 6452742024
ALUNO = 8923428907                       # ANTONIO PIRES
MAO = "7142d539-8f42-4106-9005-ee67e9c73a08"   # vision-e6ee00c6cd73

DESCULPA = (
    "Antônio, sou eu de novo — e vim pedir desculpa.\n\n"
    "Ontem você me mandou o print daquele 9♠9♦ e eu te respondi *pedindo o "
    "seu stack*. Ele estava na foto o tempo todo: 17.4bb. O erro foi meu — "
    "aquela mesa mostra o nível em fichas (15000/30000) e os stacks em bb "
    "(17.4), e eu li as duas escalas como se fossem a mesma. Deu zero em "
    "tudo, e em vez de analisar sua mão eu te devolvi uma pergunta.\n\n"
    "Já está consertado. Aqui está a análise que você devia ter recebido:"
)
FECHO = (
    "\n\n———\n"
    "Foi seu primeiro print e ele saiu torto — desculpa mesmo. Manda outro "
    "quando quiser, ou o arquivo da sessão inteira, que aí eu consigo ver "
    "seus padrões e não só uma mão solta.\n\n"
    "E se me passar a premiação daquele torneio, todo spot de bolha e mesa "
    "final já sai com o ICM calculado, sem você precisar repetir."
)


def mandar(chat, texto, markdown=True):
    if not TOKEN:
        return False
    ok = True
    for i in range(0, len(texto), 3800):
        corpo = {"chat_id": chat, "text": texto[i:i + 3800]}
        if markdown:
            corpo["parse_mode"] = "Markdown"
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data=json.dumps(corpo).encode(),
            headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=30)
        except Exception as exc:
            print(f"envio falhou ({chat}): {exc}")
            # Markdown quebrado recusa a mensagem INTEIRA — cai pra texto puro
            if markdown:
                return mandar(chat, texto, markdown=False)
            ok = False
    return ok


def pede_dado_de_novo(t: str) -> bool:
    baixo = t.lower()
    return any(f in baixo for f in (
        "me passa o stack", "me passa seu stack", "qual seu stack",
        "qual é o seu stack", "me manda o stack", "preciso do stack",
        "me diz o stack", "não dá pra analisar", "nao da pra analisar",
        "vieram zerados", "vieram todos zerados"))


try:
    from app.agent import analyzer
    from app.agent.llm import _coerir_unidades, coach
    from app.db import get_repository
    from app.models.canonical import CanonicalHand

    repo = get_repository()
    linha = (repo.client.table("hands").select("id,canonical")
             .eq("id", MAO).single().execute().data)
    mao = CanonicalHand.model_validate(linha["canonical"])

    corrigiu = _coerir_unidades(mao.stakes, mao.players)
    ctx = analyzer.analyze_hand(mao)
    diag = (f"corrigiu_unidades={corrigiu} hero={ctx['hero_stack_bb']}bb "
            f"efetivo={ctx['effective_bb']}bb pote_somado={ctx['pot_total']} "
            f"pote_na_tela={ctx.get('pot_na_tela')}")
    print(diag)

    if ctx["hero_stack_bb"] != 17.4:
        raise RuntimeError(f"stack não bateu depois da correção: {diag}")

    # grava a mão consertada: pergunta de follow-up dele usa os números certos
    repo.client.table("hands").update(
        {"canonical": json.loads(mao.model_dump_json())}).eq("id", MAO).execute()

    texto = coach(ctx, None, lang="pt")
    problemas = []
    if len(texto) < 400:
        problemas.append(f"análise curta demais ({len(texto)} chars)")
    if "17" not in texto:
        problemas.append("não cita o stack de 17.4bb")
    if pede_dado_de_novo(texto):
        problemas.append("PEDE O DADO DE NOVO — era exatamente o defeito")

    if problemas:
        mandar(DONO, "[antônio] NÃO enviei pro aluno.\n" + diag + "\n\n"
               + "\n".join("• " + p for p in problemas)
               + "\n\n--- saiu isto ---\n" + texto[:2500], markdown=False)
    else:
        enviado = mandar(ALUNO, DESCULPA + "\n\n" + texto + FECHO)
        repo.log_event(ALUNO, "ANTONIO PIRES", "reanalise_enviada",
                       {"hand": MAO, "ok": enviado, "motivo": "unidades"})
        mandar(DONO, f"[antônio] {'enviado' if enviado else 'FALHOU'} pro "
               f"aluno.\n{diag}\n\n--- cópia do que ele recebeu ---\n"
               + DESCULPA + "\n\n" + texto + FECHO, markdown=False)
except Exception:
    mandar(DONO, "[antônio] EXCEÇÃO:\n" + traceback.format_exc()[-2000:],
           markdown=False)
PY

exit 0
