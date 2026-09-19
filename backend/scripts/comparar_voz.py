"""Compara a voz ANTES e DEPOIS da mudança de prompt, na mesma mão.

Todo guarda deste plano detecta AUSÊNCIA de defeito. Nenhum mede se o texto
soa como conversa — e foi isso que o dono pediu. Este script existe para a
leitura humana, que é a única que responde a pergunta.

O "antes" sai de graça de hand_analysis.summary. O "depois" re-roda a MESMA
mão no MESMO modelo (coluna `modelo`), pelo MESMO caminho que a produção
percorre:

    CanonicalHand -> analyze_hand() -> coach(structured, perfil)
                  -> guarda_voz.limpar()

Cada elo tem um motivo. `analyze_hand()` é quem produz o dicionário
`structured` que `coach()` espera (spots, stacks em bb, cartas em texto
etc.); montar esse dicionário à mão de outro jeito entrega ao LLM um contexto
vazio e o "depois" vira lixo com aparência de resultado. O `perfil` é o
mesmo que `processing.py` passa (`stats.perfil_para_o_coach`): sem ele, um
"antes" que diz "você paga demais no river, 34% em 61 mãos" não tem
contrapartida possível, e o dono lê isso como o prompt novo tendo ficado
menos pessoal. E `limpar()` é o guarda da voz, por onde TODO texto de
produção passa antes de chegar ao aluno: sem ele, o dono julgaria um texto
que nenhum aluno receberia.

O que continua NÃO sendo espelhado está declarado no cabeçalho do markdown,
não só aqui — o artefato que o dono lê é o arquivo, não este docstring.

Só entram no sorteio linhas que comparam a MESMA COISA, no MESMO modelo:
  - registros sem hand_id (nada pra re-rodar);
  - insights de follow-up (summary começa com '[Follow-up]' — pergunta
    avulsa, não veredito de mão);
  - relatórios de TORNEIO. `analyze_tournament()` não grava "spots" no
    dicionário salvo (a coluna `mistakes` fica NULL), enquanto toda análise
    de mão avulsa sempre grava a lista (mesmo vazia). Um relatório de
    torneio usa `key_hands` e um prompt de "história do torneio" diferente
    do de mão avulsa — comparar os dois lado a lado como se fossem a mesma
    coisa engana quem está julgando;
  - registros com `modelo` NULL (linhas antigas, de antes da coluna
    existir): sem saber qual modelo gerou o "antes", `coach()` cairia
    silenciosamente no modelo padrão de HOJE para o "depois" — reintroduz o
    MODELO como segunda variável no experimento desenhado para isolar só o
    prompt. Filtrado direto na query.

Um candidato que passa nesses filtros mas falha DEPOIS (a mão sumiu de
`hands`, a busca deu erro de rede, a geração do "depois" falhou) não
desaparece do sorteio: vira um par visível no markdown, marcado como falha
— sumir com o par faria a comparação parecer melhor do que é.

Uso:  cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python \\
        scripts/comparar_voz.py --n 8 --saida /tmp/voz.md
"""
from __future__ import annotations

import argparse
import json
from typing import Callable


# O que o "depois" REFAZ e o que ele não refaz. Vai no topo do arquivo que o
# dono lê, não só no docstring do script: quem julga o lado a lado precisa
# saber, na mesma tela, o que é efeito do prompt e o que é efeito do resto.
CABECALHO = """# Voz do coach — antes × depois

> **Como ler este arquivo.**
>
> O **ANTES** é o texto que o aluno recebeu de verdade: o `summary` gravado
> em `hand_analysis`, escrito pelo prompt antigo, com o perfil do aluno
> daquele dia — e sem o guarda da voz, que ainda não existia.
>
> O **DEPOIS** re-roda a MESMA mão no MESMO modelo (coluna `modelo`) pelo
> caminho de produção: `analyze_hand()` → `coach()` com o perfil do aluno →
> `guarda_voz.limpar()`. É o texto que um aluno receberia hoje.
>
> **A variável que não dá para zerar, declarada:** o perfil do "depois" é o
> de HOJE — inclui as mãos que o aluno jogou depois que o "antes" foi
> escrito. Se um lado citar uma frequência do jogo dele e o outro não, o
> perfil é suspeito antes do prompt.
>
> **O que não roda no "depois":** os guardas de FATOS
> (`conferir_dominancia`, `corrigir_showdown`) e o guarda da saída. Nenhum
> deles mexe em VOZ — eles corrigem CONTA e carta —, então o que você está
> comparando aqui é voz contra voz.
"""


def montar_markdown(pares: list[dict]) -> str:
    """Monta o markdown lado a lado — função pura, sem rede (testável)."""
    linhas = [CABECALHO, ""]
    for i, p in enumerate(pares, 1):
        linhas += [f"## {i}. mão `{p['hand_id']}` · modelo `{p['modelo']}`",
                   "", "### ANTES", "", p["antes"] or "_(vazio)_", ""]
        if p.get("depois"):
            linhas += ["### DEPOIS", "", p["depois"], ""]
        else:
            # sumir com o par faria a mudança parecer melhor do que é: a
            # falha PRECISA aparecer no arquivo — e dizendo QUAL falha, que é
            # o que decide a reação do leitor (ver `montar_par`).
            linhas += ["### DEPOIS", "",
                       f"_({p.get('motivo') or 'a geração falhou'})_", ""]
        linhas.append("---")
    return "\n".join(linhas)


def montar_par(r: dict, buscar_mao: Callable[[], list],
               gerar_depois: Callable[[list], str]) -> dict:
    """Resolve UMA linha de hand_analysis (já filtrada) num par pro markdown.

    Isola a DECISÃO ("o que vira uma linha visível") da rede: `buscar_mao` e
    `gerar_depois` são callables injetados — permite testar que uma falha de
    busca vira par marcado, e não um `continue` mudo, sem chamar Supabase
    nem Claude de verdade. `gerar_depois` recebe o resultado de `buscar_mao`
    e devolve o texto do "depois" ou lança (mesmo contrato de `coach()`).

    NUNCA devolve None: todo candidato que chega aqui já passou pelos
    filtros de elegibilidade (hand_id, follow-up, torneio, modelo) — a
    partir daqui, sucesso ou falha, o par aparece no arquivo.

    O `motivo` separa três falhas que pedem reações OPOSTAS do leitor, e que
    antes saíam todas como "_(a geração falhou)_" — só o print de console
    distinguia, e console não é o artefato que o dono lê:
      - mão sumiu de `hands`: ignore o par, não diz nada sobre o prompt;
      - busca falhou: problema de rede/banco, rode de novo;
      - geração falhou: o prompt novo pode estar quebrando algo, e aí a
        pilha de exceção importa (o modo de falha silencioso conhecido é
        `CanonicalHand.model_validate` levantando em `canonical` de schema
        antigo, que faria TODOS os pares saírem como falha).
    """
    try:
        mao = buscar_mao()
    except Exception as exc:
        # rede/banco caiu ao buscar ESTA mão: não deixa de aparecer — só
        # o "depois" fica marcado como falha, igual a uma falha de geração
        print(f"falhou ao buscar a mão {r['hand_id']}: {exc}")
        return {"hand_id": r["hand_id"], "modelo": r.get("modelo") or "?",
                "antes": r["summary"], "depois": None,
                "motivo": f"a busca da mão falhou: {exc}"}

    if not mao:
        print(f"mão {r['hand_id']} não está mais em `hands`")
        return {"hand_id": r["hand_id"], "modelo": r.get("modelo") or "?",
                "antes": r["summary"], "depois": None,
                "motivo": "mão não encontrada em `hands` — nada a re-rodar, "
                          "o par não diz nada sobre o prompt"}

    try:
        novo = gerar_depois(mao)
        motivo = None
    except Exception as exc:
        # falha ao re-gerar o "depois" não derruba o par: o "antes" já
        # está de graça no banco e a falha vira uma linha visível
        print(f"falhou em {r['hand_id']}: {exc}")
        novo, motivo = None, f"a geração do 'depois' falhou: {exc}"

    return {"hand_id": r["hand_id"], "modelo": r.get("modelo") or "?",
            "antes": r["summary"], "depois": novo, "motivo": motivo}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--saida", default="/tmp/voz.md")
    args = ap.parse_args()

    from app.agent.analyzer import analyze_hand
    from app.agent.llm import coach
    from app.analysis import compute_player_stats
    from app.analysis.stats import perfil_para_o_coach
    from app.bot.guarda_voz import limpar
    from app.db import get_repository
    from app.models.canonical import CanonicalHand

    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase")
        return 1

    rows = (repo.client.table("hand_analysis")
            .select("hand_id,summary,modelo,mistakes")
            .not_.is_("summary", "null")
            .not_.is_("modelo", "null")
            .order("created_at", desc=True).limit(args.n * 3)
            .execute().data) or []

    pares: list[dict] = []
    for r in rows:
        if len(pares) >= args.n:
            break
        if not r.get("hand_id") or str(r.get("summary") or "").startswith("[Follow-up]"):
            continue
        if r.get("mistakes") is None:
            # relatório de torneio (analyze_tournament não tem "spots") ou
            # registro legado sem a coluna — nenhum dos dois é análise de
            # mão avulsa; comparar como se fosse misturaria formatos distintos
            continue

        def _buscar(hand_id: str = r["hand_id"]) -> list:
            # `user_id` vem junto: é ele que permite montar o MESMO perfil
            # que a produção passa ao coach() (ver _perfil).
            return (repo.client.table("hands").select("canonical,user_id")
                    .eq("id", hand_id).limit(1).execute().data) or []

        def _perfil(user_id: str | None) -> dict | None:
            """O perfil como processing.py o monta — mesma função, para não
            divergir. Sem user_id ou sem histórico, `coach()` recebe None,
            que é o que ele já espera de um aluno sem mãos completas."""
            if not user_id:
                return None
            todas, fora = repo.get_hands_para_perfil(user_id)
            if not todas:
                return None
            return perfil_para_o_coach(
                compute_player_stats(todas, player=None, fora_da_amostra=fora))

        def _gerar(mao: list, modelo: str | None = r.get("modelo")) -> str:
            hand = CanonicalHand.model_validate(mao[0]["canonical"])
            structured = analyze_hand(hand)
            texto = coach(structured, _perfil(mao[0].get("user_id")),
                          lang="pt", model=modelo)
            # produção NUNCA entrega o texto cru: conferir_e_limpar roda
            # entre coach() e save_hand_analysis (processing.py:577 × :663).
            # Julgar o cru é julgar um texto que nenhum aluno receberia.
            limpo, _feitos = limpar(texto)
            return limpo

        pares.append(montar_par(r, _buscar, _gerar))

    with open(args.saida, "w", encoding="utf-8") as fh:
        fh.write(montar_markdown(pares))
    print(f"{len(pares)} pares em {args.saida}")
    print(json.dumps({"pares": len(pares)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
