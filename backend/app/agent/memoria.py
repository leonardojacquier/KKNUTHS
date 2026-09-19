"""MEMÓRIA DO COACH — o que ele já viu, injetado antes de analisar.

Duas memórias, e a segunda é a que não existia:

1. SUA PRÓPRIA história: as mãos parecidas que ESTE aluno já mandou. Já
   estava tudo indexado (385 análises, 100% com embedding) e nada lia —
   o único leitor era o comando /ask, usado zero vezes desde 02/07. Escrever
   embedding que ninguém consulta é custo puro.

2. A memória COLETIVA: o que o coach aprendeu com TODOS os alunos. Até aqui
   o produto era estritamente por aluno (match_hand_analysis trava em
   user_id, o caderno também), então as 194 mãos do Ricardo eram invisíveis
   para a 4ª mão do Antonio. Com 10 alunos isso é desperdício; com 100 é o
   ativo principal indo pro lixo.

A memória coletiva é ANÔNIMA por construção — quem escreve generaliza. Aqui
só se lê o que já foi generalizado; este módulo nunca vê nome de aluno.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# um saber visto num aluno só é anedota; a partir de dois vira padrão. O
# coach recebe os dois, mas sabe distinguir — e a força da evidência vai
# escrita, porque "3 alunos" muda o peso da frase e ele precisa disso.
MIN_ALUNOS_PADRAO = 2


def resumo_para_busca(structured: dict) -> str:
    """O texto que representa ESTA mão para procurar parecidas.

    Curto de propósito: o que define semelhança de spot é posição, stack,
    rua e a decisão — não o naipe nem o nome da sala. Jogar a mão inteira
    aqui traz vizinho por coincidência de vocabulário.
    """
    if not isinstance(structured, dict):
        return ""
    partes: list[str] = []
    spots = structured.get("spots") or []
    for s in spots[:3]:
        if not isinstance(s, dict):
            continue
        pedaco = " ".join(str(s.get(k) or "") for k in
                          ("street", "posicao", "acao", "board"))
        if pedaco.strip():
            partes.append(pedaco.strip())
    for chave in ("formato", "format", "hero_pos", "posicao"):
        v = structured.get(chave)
        if isinstance(v, (str, int, float)) and str(v).strip():
            partes.append(str(v))
    eff = structured.get("effective_bb") or structured.get("hero_stack_bb")
    if isinstance(eff, (int, float)):
        partes.append(f"{round(float(eff))}bb")
    return " · ".join(partes)[:600]


def _linha_do_saber(c: dict) -> str:
    """Um saber coletivo em uma linha, com a força da evidência à vista."""
    alunos = int(c.get("alunos") or 1)
    forca = ("visto em 1 aluno — trate como pista, não como regra"
             if alunos < MIN_ALUNOS_PADRAO
             else f"visto em {alunos} alunos")
    ev = c.get("ev_bb")
    custo = f" · custa ~{abs(float(ev)):.1f}bb" if isinstance(
        ev, (int, float)) else ""
    return (f"[{c.get('kind') or 'padrao'}] {c.get('titulo') or ''} — "
            f"QUANDO: {c.get('gatilho') or ''} — {c.get('texto') or ''} "
            f"({forca}{custo})")


def montar(structured: dict, repo, user_id: str | None,
           embed) -> tuple[dict, list[str]]:
    """Monta o bloco de memória do contexto. Devolve (bloco, ids_usados).

    Degradação graciosa em TODOS os passos: sem provedor de embedding, sem
    banco, ou com a busca falhando, devolve bloco vazio e a análise segue
    exatamente como antes. Memória é bônus, nunca requisito.
    """
    bloco: dict = {}
    usados: list[str] = []
    consulta = resumo_para_busca(structured)
    if not consulta or repo is None or not getattr(repo, "enabled", False):
        return bloco, usados

    try:
        vetor = embed(consulta)
    except Exception as exc:
        log.warning("memória: embedding falhou (%s)", exc)
        return bloco, usados
    if not vetor:
        return bloco, usados

    # 1) as mãos parecidas DESTE aluno
    if user_id:
        try:
            hits = repo.search_analysis(user_id, vetor, limit=3) or []
        except Exception as exc:
            log.warning("memória: busca no histórico falhou (%s)", exc)
            hits = []
        resumos = [str(h.get("summary") or "")[:400] for h in hits
                   if h.get("summary")]
        if resumos:
            bloco["suas_maos_parecidas"] = resumos
            bloco["instrucao_maos_parecidas"] = (
                "Mãos que ESTE aluno já mandou em spot parecido. Use para dar "
                "continuidade ('você já tinha feito isso na mão do BTN') e "
                "para checar se o veredito de hoje bate com o de antes. NÃO "
                "invente que ele repetiu algo se os spots não forem o mesmo.")

    # 2) o que o coach aprendeu com TODOS
    try:
        saberes = repo.buscar_conhecimento(vetor, limit=3) or []
    except Exception as exc:
        log.warning("memória: busca coletiva falhou (%s)", exc)
        saberes = []
    if saberes:
        bloco["aprendido_com_outros_alunos"] = [
            _linha_do_saber(c) for c in saberes]
        bloco["instrucao_coletiva"] = (
            "Padrões que o coach destilou das mãos de OUTROS alunos, já "
            "anonimizados. Use como prior, não como fato desta mão: se o que "
            "está na mesa contradiz o padrão, a mesa ganha. NUNCA diga ou "
            "sugira que outro aluno jogou algo — o aluno não pode saber que "
            "existem outros. Nada de 'vi outro jogador fazer isso'.")
        usados = [str(c["id"]) for c in saberes if c.get("id")]
    return bloco, usados
