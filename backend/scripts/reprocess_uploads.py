"""Reprocessa uploads brutos do Storage com o parser atual.

Uso: python scripts/reprocess_uploads.py <telegram_id> [--dry-run]

Baixa cada arquivo em uploads/<telegram_id>/ do bucket, re-parseia com o parser
determinístico de hoje e faz upsert das mãos (mesma chave user_id+site+hand_id,
então dados corrompidos por bugs antigos de parsing são sobrescritos no lugar).
Ao final recalcula e grava as stats do jogador.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.analysis import compute_player_stats  # noqa: E402
from app.db import get_repository  # noqa: E402
from app.parsers import parse_text  # noqa: E402


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

    files = repo.client.storage.from_("uploads").list(str(telegram_id))
    if not files:
        print(f"nenhum upload bruto em uploads/{telegram_id}/")
        return 0

    total, saved = 0, 0
    seen: set[str] = set()
    for f in files:
        name = f.get("name") if isinstance(f, dict) else getattr(f, "name", None)
        if not name:
            continue
        path = f"{telegram_id}/{name}"
        raw = repo.client.storage.from_("uploads").download(path)
        try:
            text = raw.decode("utf-8", errors="replace")
            hands = parse_text(text)
        except Exception as exc:
            print(f"  {path}: não parseável ({exc})")
            continue
        fresh = [h for h in hands if h.hand_id not in seen]
        seen.update(h.hand_id for h in fresh)
        total += len(fresh)
        print(f"  {path}: {len(hands)} mão(s), {len(fresh)} nova(s)")
        if dry:
            continue
        for h in fresh:
            if repo.save_hand(user["id"], h):
                saved += 1

    print(f"{total} mão(s) únicas; {saved} gravadas" + (" (dry-run)" if dry else ""))
    if not dry and saved:
        all_hands = repo.get_all_hands(user["id"])
        if all_hands:
            stats = compute_player_stats(all_hands)
            repo.upsert_player_stats(user["id"], stats)
            print(f"stats recalculadas sobre {len(all_hands)} mão(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
