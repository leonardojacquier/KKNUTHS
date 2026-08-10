"""Padrões do vilão ENTRE mãos — o que um coach lembra e o dossiê esquecia.

Cada mão escura era analisada sozinha, como se as outras não existissem.
Este módulo cruza o que já foi extraído: "é a 3ª vez que ele overbeta o
river", "este sizing é o dobro da mediana dele", "das 4 vezes que fez
check-raise, mostrou valor em 2 e blefe em nenhuma". É o salto de qualidade
que não custa nada: só agregação de fatos que as mãos já carregam.

Regras de sempre: contagem e mediana, nunca taxa projetada; o resultado das
mostradas vem da classificação POR LINHA do dossiê (nunca pelo resultado);
comparação de sizing só sai com 3+ apostas na rua — mediana de duas apostas
é coincidência com nome de estatística.
"""
from __future__ import annotations

from typing import NamedTuple

from app.analysis.defesa import _mediana
from app.analysis.dossie import ler_mao
from app.analysis.leitura_vilao import Fatos, fatos_da_mao

# apostas mínimas numa rua para a mediana virar régua de comparação
MINIMO_PARA_MEDIANA = 3
# distância mínima (razão) entre a aposta e a mediana para valer comentário
DESVIO_QUE_IMPORTA = 1.5


class Padroes(NamedTuple):
    overbets_river: int
    check_raises: int
    check_raises_valor: int      # dos check-raises, mostrou valor em N
    check_raises_blefe: int      # ... e blefe em N (pela LINHA, não resultado)
    acordou_no_river: int
    mediana_por_rua: dict        # rua -> mediana das frações dele (n >= 3)
    apostas_por_rua: dict        # rua -> quantas apostas entraram na conta


def medir(hands: list, vilao: str) -> Padroes:
    """Agrega os fatos de todas as mãos do vilão. Determinístico."""
    overbets = cr = cr_valor = cr_blefe = acordou = 0
    fracoes: dict[str, list[float]] = {}
    for h in (hands or []):
        f = fatos_da_mao(h, vilao)
        overbets += int(f.overbet_river)
        acordou += int(f.acordou_no_river)
        if f.check_raise_em:
            cr += 1
            m = ler_mao(h, vilao)
            if m is not None:
                cr_valor += int(m.papel in ("valor", "valor fino"))
                cr_blefe += int(m.papel == "blefe")
        for rua, fs in f.fracoes.items():
            fracoes.setdefault(rua, []).extend(fs)
    mediana = {rua: round(_mediana(fs), 2)
               for rua, fs in fracoes.items()
               if len(fs) >= MINIMO_PARA_MEDIANA}
    return Padroes(overbets_river=overbets, check_raises=cr,
                   check_raises_valor=cr_valor, check_raises_blefe=cr_blefe,
                   acordou_no_river=acordou, mediana_por_rua=mediana,
                   apostas_por_rua={r: len(fs) for r, fs in fracoes.items()})


def contexto(p: Padroes, f: Fatos) -> list[str]:
    """As linhas de contexto de UMA mão diante dos padrões do torneio.

    Só sai o que compara: padrão que a mão atual não toca fica de fora —
    contexto é lupa, não relatório repetido."""
    linhas: list[str] = []
    if f.overbet_river and p.overbets_river >= 2:
        linhas.append(f"não é a primeira: ele overbetou o river "
                      f"{p.overbets_river}× neste torneio")
    if f.acordou_no_river and p.acordou_no_river >= 2:
        linhas.append(f"padrão dele: acordou só no river em "
                      f"{p.acordou_no_river} mãos deste torneio")
    if f.check_raise_em and p.check_raises >= 2:
        base = (f"ele já fez check-raise {p.check_raises}× neste torneio")
        if p.check_raises_valor or p.check_raises_blefe:
            base += (f" — quando mostrou, era valor em "
                     f"{p.check_raises_valor} e blefe em "
                     f"{p.check_raises_blefe}")
        linhas.append(base)
    for rua, fs in sorted(f.fracoes.items()):
        med = p.mediana_por_rua.get(rua)
        if med is None or not fs:
            continue
        fr = fs[-1]                       # a aposta que fechou a rua
        if med > 0 and (fr / med >= DESVIO_QUE_IMPORTA
                        or fr / med <= 1 / DESVIO_QUE_IMPORTA):
            lado = "acima" if fr > med else "abaixo"
            fr = round(fr, 2)
            linhas.append(f"o sizing do {rua} ({fr:g}× pote) foge do padrão "
                          f"dele: mediana {med:g}× em "
                          f"{p.apostas_por_rua.get(rua, 0)} apostas — bem "
                          f"{lado} do normal DELE")
    if f.comprometeu is not None and f.comprometeu >= 0.5:
        linhas.append(f"ele comprometeu {round(100 * f.comprometeu)}% do "
                      f"stack nesta mão — não é aposta de tateio")
    extras = []
    if f.posicao_no_flop:
        extras.append(f.posicao_no_flop)
    if f.multiway:
        extras.append("pote multiway")
    if f.textura_flop:
        extras.append(f"flop {f.textura_flop}")
    if extras:
        linhas.append(" · ".join(extras))
    return linhas
