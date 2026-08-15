"""Compara a voz ANTES e DEPOIS da mudança de prompt, na mesma mão.

Todo guarda deste plano detecta AUSÊNCIA de defeito. Nenhum mede se o texto
soa como conversa — e foi isso que o dono pediu. Este script existe para a
leitura humana, que é a única que responde a pergunta.

O "antes" sai de graça de hand_analysis.summary. O "depois" re-roda a MESMA
mão no MESMO modelo (coluna `modelo`), então a única variável é o prompt.
Para isso, o script refaz o MESMO caminho que a análise original percorreu:
CanonicalHand -> analyze_hand() -> coach() — é `analyze_hand()` que produz o
dicionário `structured` que `coach()` espera (spots, stacks em bb, cartas em
texto etc.); montar esse dicionário à mão de outro jeito entrega ao LLM um
contexto vazio e o "depois" vira lixo com aparência de resultado.

Só entram no lado a lado pares que comparam a MESMA COISA: análise de UMA
mão. Ficam de fora do sorteio:
  - registros sem hand_id (nada pra re-rodar);
  - insights de follow-up (summary começa com '[Follow-up]' — pergunta
    avulsa, não veredito de mão);
  - relatórios de TORNEIO. `analyze_tournament()` não grava "spots" no
    dicionário salvo (a coluna `mistakes` fica NULL), enquanto toda análise
    de mão avulsa sempre grava a lista (mesmo vazia). Um relatório de
    torneio usa `key_hands` e um prompt de "história do torneio" diferente
    do de mão avulsa — comparar os dois lado a lado como se fossem a mesma
    coisa engana quem está julgando.

Uso:  cd /opt/poker-bot && PYTHONPATH=. ./venv/bin/python \\
        scripts/comparar_voz.py --n 8 --saida /tmp/voz.md
"""
from __future__ import annotations

import argparse
import json


def montar_markdown(pares: list[dict]) -> str:
    """Monta o markdown lado a lado — função pura, sem rede (testável)."""
    linhas = ["# Voz do coach — antes × depois", ""]
    for i, p in enumerate(pares, 1):
        linhas += [f"## {i}. mão `{p['hand_id']}` · modelo `{p['modelo']}`",
                   "", "### ANTES", "", p["antes"] or "_(vazio)_", ""]
        if p.get("depois"):
            linhas += ["### DEPOIS", "", p["depois"], ""]
        else:
            # sumir com o par faria a mudança parecer melhor do que é: a
            # falha de geração PRECISA aparecer no arquivo que o dono lê.
            linhas += ["### DEPOIS", "", "_(a geração falhou)_", ""]
        linhas.append("---")
    return "\n".join(linhas)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--saida", default="/tmp/voz.md")
    args = ap.parse_args()

    from app.agent.analyzer import analyze_hand
    from app.agent.llm import coach
    from app.db import get_repository
    from app.models.canonical import CanonicalHand

    repo = get_repository()
    if not repo.enabled:
        print("sem Supabase")
        return 1

    rows = (repo.client.table("hand_analysis")
            .select("hand_id,summary,modelo,mistakes")
            .not_.is_("summary", "null")
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
            # mão avulsa; comparar como se fosse mistura formatos distintos
            continue

        try:
            mao = (repo.client.table("hands").select("canonical")
                   .eq("id", r["hand_id"]).limit(1).execute().data) or []
        except Exception as exc:
            # falha de rede/banco ao buscar ESTA mão não pode derrubar as
            # outras — só esta fica de fora do sorteio
            print(f"falhou ao buscar a mão {r['hand_id']}: {exc}")
            continue
        if not mao:
            continue

        try:
            hand = CanonicalHand.model_validate(mao[0]["canonical"])
            structured = analyze_hand(hand)
            novo = coach(structured, None, lang="pt", model=r.get("modelo"))
        except Exception as exc:
            # falha ao re-gerar o "depois" NÃO derruba o par: o "antes" já
            # está de graça no banco e a falha vira uma linha visível
            print(f"falhou em {r['hand_id']}: {exc}")
            novo = None

        pares.append({"hand_id": r["hand_id"], "modelo": r.get("modelo") or "?",
                      "antes": r["summary"], "depois": novo})

    with open(args.saida, "w", encoding="utf-8") as fh:
        fh.write(montar_markdown(pares))
    print(f"{len(pares)} pares em {args.saida}")
    print(json.dumps({"pares": len(pares)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
