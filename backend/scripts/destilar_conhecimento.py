"""Destilador da MEMÓRIA COLETIVA — o que serve para todo mundo.

O produto sabia muito sobre cada aluno e nada sobre o conjunto: a busca
semântica trava em user_id, o caderno também. Então o erro que já custou
caro para três alunos diferentes chegava no quarto como novidade.

Este script lê o caderno de TODOS (player_notes), agrupa o que se repete
ENTRE alunos distintos e destila em saber reusável. Duas garantias que não
são detalhe:

  ANONIMATO — o prompt nunca recebe nome, e o que ele escreve é conferido
  depois: saber que cite nome de aluno é descartado, não "corrigido".

  EVIDÊNCIA — cada saber carrega de quantos alunos veio. Um padrão visto em
  1 é anedota e entra marcado como pista; a partir de 2 é padrão. O coach
  recebe essa contagem escrita, porque ela muda o peso da frase.

Roda diário, modelo barato. Cron sugerido:
  40 9 * * *  cd /app/backend && PYTHONPATH=. ./venv/bin/python \
              scripts/destilar_conhecimento.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict

from app.agent.embeddings import embed_text
from app.config import get_settings
from app.db import get_repository

MIN_ALUNOS = 2          # abaixo disso é anedota, não padrão
MAX_NOVOS = 6           # por rodada: destilar é barato, revisar não é
MAX_POR_TEMA = 3        # tema fértil não enche a memória sozinho

_PROMPT = (
    "Você destila PADRÕES DE POKER a partir de observações que um coach "
    "anotou sobre vários alunos diferentes. O padrão vai ser injetado no "
    "contexto de futuras análises, então precisa ser ACIONÁVEL e ANÔNIMO:\n"
    "- NUNCA cite nome, apelido, clube, sala, data ou horário. Nem invente.\n"
    "- o GATILHO diz quando o padrão se aplica ('BB com 12-18bb contra open "
    "do BTN'), específico o bastante para o coach reconhecer o spot\n"
    "- o TEXTO diz o que costuma dar errado e qual é a linha melhor, com o "
    "número que prova (EV em bb, preço em %). Saber sem número é opinião.\n"
    "- se as observações forem vagas ou não tiverem nada em comum de "
    "verdade, recuse: forçar padrão inexistente envenena todas as análises\n"
    "Um tema pode conter MAIS DE UM padrão distinto — devolva um por "
    "padrão, no máximo 3, do mais evidente para o menos. Não force: dois "
    "padrões de verdade valem mais que cinco inventados.\n"
    "Responda SÓ um array JSON:\n"
    '[{"titulo": "curto e concreto", "gatilho": "quando se aplica", '
    '"texto": "o que erra + a linha certa + o número", '
    '"categoria": "preflop|flop|turn|river|icm", "ev_bb": -4.2, '
    '"vale": true}]\n'
    'Sem padrão claro: [].'
)

_CATEGORIAS = ("preflop", "flop", "turn", "river", "icm")

# 1400 e não 600: copiei o teto do destilador de lições, mas o JSON dele é
# curto e o meu pede gatilho + texto detalhado. Na 1ª rodada real os SEIS
# temas morreram com "Unterminated string" por volta do char 1600 — que é
# exatamente 600 tokens de português. Truncar no meio da string não dá erro
# da API: dá JSON quebrado, e o custo já foi pago.
MAX_TOKENS = 1400


def _sem_cerca(txt: str) -> str:
    t = (txt or "").strip()
    if t.startswith("```"):
        partes = t.split("```")
        t = partes[1] if len(partes) > 1 else t
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    return t.strip()


def _objetos_completos(t: str) -> list[dict]:
    """Varre contando chaves e devolve só os objetos que FECHARAM.

    Serve ao caso que mais dói: o modelo devolve 4 padrões e o 4º é cortado
    no teto de tokens. Jogar a resposta inteira fora perderia 3 padrões bons
    já pagos. Ignora chave dentro de string (e escape) — sem isso um texto
    com '{' quebra a contagem.
    """
    saida: list[dict] = []
    nivel = inicio = 0
    dentro_str = escapado = False
    for i, ch in enumerate(t):
        if dentro_str:
            if escapado:
                escapado = False
            elif ch == "\\":
                escapado = True
            elif ch == '"':
                dentro_str = False
            continue
        if ch == '"':
            dentro_str = True
        elif ch == "{":
            if nivel == 0:
                inicio = i
            nivel += 1
        elif ch == "}":
            nivel -= 1
            if nivel == 0:
                try:
                    obj = json.loads(t[inicio:i + 1])
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    saida.append(obj)
            elif nivel < 0:
                nivel = 0
    return saida


def extrair_saberes(txt: str) -> list[dict]:
    """Os padrões que vieram, sejam quantos forem.

    Devolve LISTA porque o modelo devolve lista — e está certo: o tema
    "3-bet" reúne notas de 4 alunos e contém mesmo vários padrões distintos
    (fold marginal OOP, call em vez de jam...). A 1ª versão exigia um objeto
    só e descartava tudo achando que era erro de formato; o erro era meu.

    Aguenta cerca de código, preâmbulo do modelo, objeto solto, array, e
    array cortado no meio (aproveita os que fecharam).
    """
    t = _sem_cerca(txt)
    if not t:
        return []
    try:
        obj = json.loads(t)
        if isinstance(obj, dict):
            return [obj]
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    return _objetos_completos(t)


def cita_nome(texto: str, nomes: list[str]) -> bool:
    """O saber vazou identidade? Confere contra os nomes reais do banco."""
    baixo = (texto or "").lower()
    for n in nomes:
        n = (n or "").strip()
        if len(n) >= 3 and n.lower() in baixo:
            return True
    return False


def validar(bruto: object, nomes: list[str], alunos: int) -> dict | None:
    """Só padrão bem formado e anônimo entra na memória (função pura)."""
    if not isinstance(bruto, dict) or bruto.get("vale") is not True:
        return None
    titulo = str(bruto.get("titulo") or "").strip()
    gatilho = str(bruto.get("gatilho") or "").strip()
    texto = str(bruto.get("texto") or "").strip()
    cat = str(bruto.get("categoria") or "").strip().lower()
    if not (titulo and gatilho and texto):
        return None
    if len(texto) < 40:                      # frase de efeito não é saber
        return None
    if cat not in _CATEGORIAS:
        cat = None
    ev = bruto.get("ev_bb")
    try:
        ev = float(ev)
    except (TypeError, ValueError):
        ev = None
    junto = f"{titulo} {gatilho} {texto}"
    if cita_nome(junto, nomes):
        return None
    if not re.search(r"\d", texto):          # sem número é opinião
        return None
    return {"titulo": titulo[:200], "gatilho": gatilho[:400],
            "texto": texto[:1200], "categoria": cat, "ev_bb": ev,
            "alunos": alunos}


def agrupar_por_tema(notas: list[dict]) -> dict[str, list[dict]]:
    """Junta observações por palavra-chave de spot, contando ALUNOS.

    Agrupamento pobre de propósito: o objetivo é só dar ao LLM um punhado de
    observações plausivelmente relacionadas. Quem decide se há padrão de
    verdade é ele — e ele pode (e deve) recusar.
    """
    chaves = ("3-bet", "4-bet", "shove", "all-in", "c-bet", "check-raise",
              "river", "turn", "flop", "bolha", "icm", "blind", "limp",
              "overpair", "draw", "bluff", "value", "fold")
    grupos: dict[str, list[dict]] = defaultdict(list)
    for n in notas:
        texto = str(n.get("note") or "").lower()
        for k in chaves:
            if k in texto:
                grupos[k].append(n)
    return {k: v for k, v in grupos.items()
            if len({x.get("user_id") for x in v}) >= MIN_ALUNOS}


def main() -> int:
    s = get_settings()
    repo = get_repository()
    if not repo.enabled:
        print("banco indisponível")
        return 1
    if not s.anthropic_api_key:
        print("sem chave da Anthropic")
        return 1

    c = repo.client
    notas = (c.table("player_notes").select("user_id, kind, note, created_at")
             .order("created_at", desc=True).limit(400).execute().data) or []
    usuarios = (c.table("users").select("username").execute().data) or []
    nomes = [u.get("username") for u in usuarios if u.get("username")]

    existentes = {(x.get("titulo") or "").lower()
                  for x in repo.listar_conhecimento(limit=200)}
    grupos = agrupar_por_tema(notas)
    if not grupos:
        print("nenhum tema aparece em 2+ alunos ainda")
        repo.log_event(0, "conhecimento", "conhecimento_destilado",
                       {"novos": 0, "motivo": "sem tema multi-aluno"})
        return 0

    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    novos = 0
    ilegiveis = 0
    # tema com mais alunos primeiro: é onde a evidência é mais forte
    ordem = sorted(grupos.items(),
                   key=lambda kv: -len({x.get("user_id") for x in kv[1]}))
    for i, (tema, notas_do_tema) in enumerate(ordem, 1):
        if novos >= MAX_NOVOS:
            break
        # PARA de gastar quando o problema é sistêmico. Na 1ª rodada real os
        # seis temas falharam no parse, um atrás do outro, cada um pagando
        # uma chamada. Dois seguidos ilegíveis não é azar: é o formato.
        if ilegiveis >= 2:
            print("abortando: 2 respostas ilegíveis seguidas — problema de "
                  "formato, não de conteúdo. Nada mais será gasto.")
            break
        print(f"[{i}/{len(ordem)}] tema {tema}...", flush=True)
        n_alunos = len({x.get("user_id") for x in notas_do_tema})
        # SEM user_id no prompt: o modelo não precisa saber de quem é, e o
        # que ele não recebe não vaza
        corpo = "\n".join(f"- {str(x.get('note') or '')[:300]}"
                          for x in notas_do_tema[:12])
        try:
            resp = client.messages.create(
                model=s.cheap_model, max_tokens=MAX_TOKENS, temperature=0.2,
                system=_PROMPT,
                messages=[{"role": "user",
                           "content": f"Tema: {tema}\nObservações de "
                                      f"{n_alunos} alunos distintos:\n{corpo}"}],
            )
            txt = "".join(b.text for b in resp.content
                          if b.type == "text").strip()
        except Exception as exc:
            print(f"  falhou na chamada: {exc}")
            continue
        brutos = extrair_saberes(txt)
        if not brutos:
            ilegiveis += 1
            # o texto cru VAI para o log: sem ele o diagnóstico da primeira
            # rodada foi adivinhação a partir de "line 22 column 5"
            cortado = resp.stop_reason == "max_tokens"
            print(f"  ilegível{' (cortado no teto de tokens)' if cortado else ''}"
                  f" — resposta crua: {txt[:400]!r}")
            continue
        ilegiveis = 0
        if resp.stop_reason == "max_tokens":
            print(f"  (resposta cortada no teto — aproveitando os "
                  f"{len(brutos)} padrões que fecharam)")
        # teto por tema: um tema fértil não pode encher a memória sozinho e
        # deixar os outros 12 de fora nesta rodada
        for bruto in brutos[:MAX_POR_TEMA]:
            if novos >= MAX_NOVOS:
                break
            saber = validar(bruto, nomes, n_alunos)
            if not saber:
                print(f"  recusado: {str(bruto.get('titulo'))[:60]!r} "
                      "(vago, sem número, ou citou aluno)")
                continue
            if saber["titulo"].lower() in existentes:
                print(f"  já existe: {saber['titulo']}")
                continue
            repo.salvar_conhecimento(
                kind="padrao", embedding=embed_text(
                    f"{saber['gatilho']} {saber['texto']}"),
                origem={"tema": tema, "notas": len(notas_do_tema)}, **saber)
            existentes.add(saber["titulo"].lower())
            novos += 1
            print(f"  OK ({n_alunos} alunos) — {saber['titulo']}")

    repo.log_event(0, "conhecimento", "conhecimento_destilado",
                   {"novos": novos, "temas": len(grupos)})
    print(f"{novos} saberes novos de {len(grupos)} temas multi-aluno")
    return 0


if __name__ == "__main__":
    sys.exit(main())
