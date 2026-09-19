"""A síntese por IA do dossiê — e a CONFERÊNCIA que a deixa existir.

O dono viu os dois retratos em produção e vetou o formato: "não tá legal,
ponha um pouco de IA". O que a IA acrescenta é a voz — o parágrafo de coach
que amarra retratos, defesa e padrões numa leitura que se lê. O que ela NÃO
pode acrescentar é número: a regra da casa continua sendo "o modelo escreve,
a conferência garante".

A conferência é literal: TODO número que aparecer na prosa tem que existir
nos fatos medidos (o JSON que o próprio módulo monta). Número inventado —
uma porcentagem calculada de cabeça, um "3×" que não está nos dados — e o
texto inteiro é descartado; o dossiê sai como sempre saiu, determinístico.
Falha de modelo nunca vira número na frente do aluno.
"""
from __future__ import annotations

import json
import re


def fatos_do_dossie(nome: str, hands: list) -> dict:
    """Os fatos MEDIDOS que a síntese pode citar — e nada além deles.

    Reusa os módulos do dossiê (mesa, showdowns, linha, defesa, padrões);
    recomputar aqui é barato e mantém a síntese sem acesso às mãos cruas."""
    from app.analysis.defesa import medir as medir_defesa
    from app.analysis.dossie import montar as montar_dossie
    from app.analysis.mesa import medir as medir_mesa
    from app.analysis.padroes import medir as medir_padroes
    from app.analysis.perfil_duplo import montar as montar_duplo

    mesa = medir_mesa(hands)
    linha = next((li for li in (mesa.linhas if mesa else ())
                  if li.nome.strip().lower() == nome.strip().lower()), None)
    d = montar_dossie(hands, nome)
    duplo = montar_duplo(hands, nome, d)
    defesa = medir_defesa(hands, nome)
    p = medir_padroes(hands, nome)

    fatos: dict = {"vilao": nome}
    if linha:
        fatos["perfil_pre_flop"] = {
            "maos_observadas": linha.maos,
            "vpip_pct": round(100 * linha.vpip),
            "vpip_margem_pp": round(100 * linha.vpip_margem),
            "pfr_pct": round(100 * linha.pfr),
            "gap_paga_sem_atacar_pp": round(100 * linha.gap),
            "rotulo_sustentado": linha.rotulo or "sem rótulo (amostra)",
        }
    if duplo.a:
        a = duplo.a
        fatos["retrato_showdown"] = {
            "maos_que_ele_mostrou": a.n, "valor": a.valor,
            "blefes": a.blefes, "so_pagou": a.pagou,
            "mostrou_sem_agredir": a.outras,
            "rotulo": a.rotulo,
        }
    if duplo.b:
        b = duplo.b
        fatos["retrato_linha"] = {
            "agressoes_pos_flop": b.agressoes,
            "sem_showdown": b.sem_showdown,
            "potes_levados_sem_mostrar": b.levou_sem_mostrar,
            "cbet": f"{b.cbet_k} de {b.cbet_n}",
            "segunda_barrela": f"{b.barrela_k} de {b.barrela_n}",
            "sizing_medio_pct_pote": {r: round(100 * fr)
                                      for r, fr in b.fracao_media.items()},
            "rotulo": b.rotulo or "",
        }
    if duplo.divergencia:
        fatos["divergencia_entre_retratos"] = duplo.divergencia
    if defesa:
        fatos["sua_defesa_no_river"] = {
            "apostas_dele": defesa.apostas, "seus_folds": defesa.folds,
            "fold_pct": round(100 * defesa.fold_taxa),
            "limiar_pct": (round(100 * defesa.limiar_fold)
                           if defesa.limiar_fold else None),
            "veredito": defesa.veredito,
        }
    padroes = {}
    if p.overbets_river:
        padroes["overbets_no_river"] = p.overbets_river
    if p.check_raises:
        padroes["check_raises"] = p.check_raises
        padroes["check_raises_que_mostraram_valor"] = p.check_raises_valor
        padroes["check_raises_que_mostraram_blefe"] = p.check_raises_blefe
    if p.acordou_no_river:
        padroes["acordou_so_no_river"] = p.acordou_no_river
    if p.mediana_por_rua:
        padroes["sizing_mediano_pct_pote"] = {
            r: round(100 * m) for r, m in p.mediana_por_rua.items()}
    if padroes:
        padroes["nota"] = "padrões DELE neste torneio — contagens, não taxas"
        fatos["padroes"] = padroes
    return fatos


_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def _canon(tok: str) -> str:
    """'0.60' e '0,6' são o mesmo número; '38' e '38.0' também."""
    return f"{float(tok.replace(',', '.')):g}"


def numeros_permitidos(fatos: dict) -> set[str]:
    """Todo número presente nos fatos — inclusive dentro de strings (a
    divergência e os '3 de 4' carregam números)."""
    return {_canon(m) for m in
            _NUMERO.findall(json.dumps(fatos, ensure_ascii=False))}


def conferir(texto: str, fatos: dict) -> list[str]:
    """Os números do texto que NÃO existem nos fatos. [] = texto aprovado.

    É proposital que '11 de 15 = 73%' reprove: 73 não está nos dados, é
    conta do modelo — e conta de modelo é exatamente o que não entra."""
    permitidos = numeros_permitidos(fatos)
    return [m for m in _NUMERO.findall(texto or "")
            if _canon(m) not in permitidos]
