"""A cola: varrer as mãos, decidir, persistir, e devolver o que o aluno lê.

`taxonomia` sabe contar. `problemas` sabe decidir. `evolucao` sabe medir.
Nenhum dos três conhece o banco nem o aluno — e sem alguém que os ligue, os
três são bibliotecas que ninguém chama.

O QUE ESTA CAMADA GARANTE, e que nenhuma das outras podia garantir sozinha:

- O PORTÃO DE AMOSTRA ANTES DE TUDO. Só mão de sessão inteira entra na
  varredura. Replay avulso continua valendo para analisar aquela mão; para
  contar frequência, não. É o incidente do VPIP 94% fechado na origem.
- UM PROBLEMA ATIVO. Se já existe um, ele é REVISADO em vez de um novo ser
  aberto. Três ativos dividem as oportunidades por três e nenhum fecha.
- O PRÉ-REQUISITO ANTES DO SINTOMA. Não adianta abrir "defesa de BB" para
  quem não calcula preço de pote: metade daquelas mãos ele erra pelo motivo
  errado, e a intervenção certa é outra.
- O CRITÉRIO DE ALTA GRAVADO NA ABERTURA, não depois. Pré-registro só vale
  se for imutável na prática.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _dia(h) -> str:
    d = getattr(h, "played_at", None) or ""
    return str(d)[:10] or datetime.now(timezone.utc).date().isoformat()


def _evidencias_por_codigo(hands, obs) -> dict[str, list]:
    """Agrupa as observações por código e por DIA — a recorrência é sobre
    sessões distintas, e sem o dia não dá para separar leak de noite ruim."""
    from app.analysis.problemas import Evidencia

    dia_da_mao = {h.hand_id: _dia(h) for h in hands}
    por_codigo: dict[str, dict[str, list[int]]] = {}
    for o in obs:
        d = dia_da_mao.get(o.hand_id, "")
        if not d:
            continue
        c = por_codigo.setdefault(o.codigo, {})
        par = c.setdefault(d, [0, 0])
        par[0] += 1
        par[1] += int(o.escorregada)
    return {codigo: [Evidencia(d, opp, miss, True)
                     for d, (opp, miss) in sorted(dias.items())]
            for codigo, dias in por_codigo.items()}


def _oportunidades_depois(hands, obs, codigo: str, desde: str | None) -> int:
    """Oportunidades do código em mãos jogadas DEPOIS do diagnóstico.

    A barra de coleta mede o que veio DEPOIS da intervenção. Contar as mãos
    que diagnosticaram diria "30 de 30" no instante em que o problema abre —
    ou seja, "você já chegou" antes de ter coletado uma única mão nova. É a
    mesma confusão entre janela que diagnostica e janela que mede que faz a
    regressão à média virar melhora falsa.
    """
    if not desde:
        return 0
    dia_da_mao = {h.hand_id: _dia(h) for h in hands}
    return sum(1 for o in obs if o.codigo == codigo
               and dia_da_mao.get(o.hand_id, "") > desde)


def revisar(repo, user_id: str, hands: list) -> dict:
    """Varre, decide e persiste. Devolve o que o aluno vê.

    Idempotente por desenho: rodar de novo no mesmo material não abre
    problema novo — encontra o ativo e o revisa.
    """
    from app.analysis.problemas import (MAX_ATIVOS, PROBLEMA, avaliar,
                                        bloqueado_por, criterio_de_alta,
                                        prioridade, texto_do_plano)
    from app.analysis.stats import FONTES_COMPLETAS
    from app.analysis.taxonomia import CODIGOS, agregar, observar

    # PORTÃO: só sessão inteira. Um replay escolhido a dedo no meio já
    # envenena o denominador, e o denominador é a coisa toda.
    completas = [h for h in hands
                 if (getattr(h, "source_format", None) or "txt")
                 in FONTES_COMPLETAS]
    if not completas:
        return {"texto": "", "por_que": "sem mãos de sessão inteira",
                "diagnosticos": []}

    obs = observar(completas)
    diagnosticos = agregar(obs, len(completas))
    evid = _evidencias_por_codigo(completas, obs)

    for d in diagnosticos:
        v = avaliar(d, evid.get(d["codigo"], []), codigos_testados=len(CODIGOS))
        d["estado"] = v.estado
        d["por_que"] = v.por_que

    abertos = repo.problemas_do_aluno(user_id, ("problema", "em_alta")) or []
    resolvidos = {p["codigo"] for p in
                  (repo.problemas_do_aluno(user_id, ("resolvido",)) or [])}

    candidatos = [d for d in diagnosticos if d["estado"] == PROBLEMA]
    # PRÉ-REQUISITO NA FRENTE: o sintoma espera o fundamento
    for d in candidatos:
        d["bloqueado_por"] = bloqueado_por(d["codigo"], resolvidos)
    livres = [d for d in candidatos if not d.get("bloqueado_por")]
    livres.sort(key=lambda d: -prioridade(d, len(evid.get(d["codigo"], []))))

    ativo = None
    if abertos:
        # já tem um: REVISA, não abre outro
        vivo = abertos[0]
        atual = next((d for d in diagnosticos
                      if d["codigo"] == vivo["codigo"]), None)
        ativo = {**(atual or {}), **{
            "id": vivo["id"], "codigo": vivo["codigo"],
            # a barra de coleta é do que veio DEPOIS do diagnóstico
            "oportunidades": _oportunidades_depois(
                completas, obs, vivo["codigo"], vivo.get("diagnostico_ate")),
            "nome": CODIGOS[vivo["codigo"]].nome if vivo["codigo"] in CODIGOS
            else vivo["codigo"],
            "pergunta": CODIGOS[vivo["codigo"]].pergunta
            if vivo["codigo"] in CODIGOS else "",
            "alta_n_minimo": vivo.get("alta_n_minimo") or 30,
            "alta_por_extenso": vivo.get("alta_por_extenso") or ""}}
    elif livres and len(abertos) < MAX_ATIVOS:
        d = livres[0]
        alta = criterio_de_alta(d)
        # o critério vai na MESMA gravação da abertura: gravar depois abriria
        # a porta para escrever a régua já sabendo o resultado
        linha = repo.abrir_problema(
            user_id, d["codigo"], PROBLEMA, d["por_que"], alta,
            diagnostico_ate=datetime.now(timezone.utc).date().isoformat())
        ativo = {**d, "id": (linha or {}).get("id"),
                 "nome": CODIGOS[d["codigo"]].nome,
                 # acabou de abrir: ZERO mãos novas coletadas, por definição
                 "oportunidades": 0, "escorregadas": 0,
                 "diagnosticado_com": d["oportunidades"],
                 "alta_n_minimo": alta["n_minimo"],
                 "alta_por_extenso": alta["por_extenso"]}

    fila = [{"codigo": d["codigo"], "nome": CODIGOS[d["codigo"]].nome}
            for d in livres[1:]] + \
           [{"codigo": d["codigo"],
             "nome": f"{CODIGOS[d['codigo']].nome} (espera "
                     f"{d['bloqueado_por']})"}
            for d in candidatos if d.get("bloqueado_por")]

    # O QUE ESTÁ DE PÉ. Detector de acerto quase nunca é construído, e sem
    # ele a ferramenta é um crítico — crítico se abandona.
    acertos = [f"{CODIGOS[d['codigo']].nome}: {d['oportunidades']} spots, "
               f"nenhum erro"
               for d in diagnosticos
               if d["escorregadas"] == 0 and d["oportunidades"] >= 8][:2]

    return {"texto": texto_do_plano(ativo or {}, fila, acertos),
            "diagnosticos": diagnosticos, "ativo": ativo, "fila": fila,
            "acertos": acertos, "maos_completas": len(completas)}
