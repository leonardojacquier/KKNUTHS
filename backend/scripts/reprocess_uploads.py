"""Reprocessa uploads brutos do Storage com o parser atual.

Uso: python scripts/reprocess_uploads.py <telegram_id> [--dry-run]

Baixa cada arquivo em uploads/<telegram_id>/ do bucket, re-parseia com o parser
determinístico de hoje e faz upsert das mãos (mesma chave user_id+site+hand_id,
então dados corrompidos por bugs antigos de parsing são sobrescritos no lugar).

O bucket pode conter FRAGMENTOS (pastes cortados pelo Telegram) além do arquivo
completo — por isso, quando o mesmo hand_id aparece em mais de um arquivo, vence
a versão mais COMPLETA (mais ações/jogadores/summary), não a mais antiga.
Ao final recalcula e grava as stats do jogador.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis import compute_player_stats  # noqa: E402
from app.db import get_repository  # noqa: E402
from app.models.canonical import CanonicalHand  # noqa: E402
from app.parsers import parse_text  # noqa: E402


def completeness(h: CanonicalHand) -> tuple:
    """Quanto conteúdo a mão tem — para escolher entre versões do mesmo hand_id."""
    return (
        sum(len(s.actions) for s in h.streets),
        len(h.players),
        1 if h.collected else 0,
        1 if h.total_pot else 0,
        1 if h.hero_cards else 0,
    )


def pick_best(versions: list[CanonicalHand]) -> dict[str, CanonicalHand]:
    """Dedup por hand_id mantendo a versão mais completa de cada mão."""
    best: dict[str, CanonicalHand] = {}
    for h in versions:
        cur = best.get(h.hand_id)
        if cur is None or completeness(h) > completeness(cur):
            best[h.hand_id] = h
    return best


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    telegram_id = int(sys.argv[1])
    dry = "--dry-run" in sys.argv

    repo = get_repository()
    user = repo.get_or_create_user(telegram_id)
    if not user:
        print("usuário não encontrado / banco indisponível")
        return 1

    try:
        files = repo.client.storage.from_("uploads").list(str(telegram_id))
    except Exception as exc:
        print(f"falha ao listar uploads/{telegram_id}: {exc}")
        return 1
    if not files:
        print(f"nenhum upload bruto em uploads/{telegram_id}/")
        return 0

    parsed: list[CanonicalHand] = []
    failures = 0
    for f in files:
        name = f.get("name") if isinstance(f, dict) else getattr(f, "name", None)
        if not name:
            continue
        path = f"{telegram_id}/{name}"
        try:
            raw = repo.client.storage.from_("uploads").download(path)
            text = raw.decode("utf-8", errors="replace")
            hands = parse_text(text)
        except Exception as exc:
            # imagens/pdf no mesmo bucket e erros transientes: pula e segue
            print(f"  {path}: não parseável ({exc})")
            failures += 1
            continue
        print(f"  {path}: {len(hands)} mão(s)")
        parsed.extend(hands)

    best = pick_best(parsed)
    print(f"{len(best)} mão(s) únicas (melhor versão de cada)")
    saved = 0
    if not dry:
        for h in best.values():
            if repo.save_hand(user["id"], h):
                saved += 1
        print(f"{saved} gravadas")
        if saved:
            all_hands = repo.get_all_hands(user["id"])
            if all_hands:
                stats = compute_player_stats(all_hands)
                repo.upsert_player_stats(user["id"], stats)
                print(f"stats recalculadas sobre {len(all_hands)} mão(s)")
        if saved < len(best):
            print(f"AVISO: {len(best) - saved} upsert(s) falharam")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
