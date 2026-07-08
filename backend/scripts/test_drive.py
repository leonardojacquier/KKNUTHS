"""Test-drive: roda um arquivo de mãos pelo pipeline COMPLETO (como se tivesse
chegado no chat) e entrega o resultado no Telegram do usuário — análise do
coach, quadro do torneio e gráficos. Deixa as mãos no banco, então /simular,
/treino, /stats e /torneio ficam prontos para uso interativo.

Uso (no VPS): python scripts/test_drive.py <arquivo.txt> <telegram_id>
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bot.processing import pop_charts, process_upload  # noqa: E402
from app.config import get_settings  # noqa: E402
from scripts.revalidation_report import _send_photo, _send_text  # noqa: E402


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    path, tg = Path(sys.argv[1]), int(sys.argv[2])
    token = get_settings().telegram_bot_token
    if not token:
        print("sem TELEGRAM_BOT_TOKEN")
        return 1

    _send_text(token, tg,
               "🧪 Test-drive: processei o torneio demo (10 mãos) pelo fluxo "
               "completo, como se você tivesse enviado o arquivo. Chegando: "
               "análise do coach + quadro + gráficos. Depois teste /simular, "
               "/treino, /torneio e /stats — as mãos já estão na sua conta.")
    reply = process_upload(path.read_bytes(), "txt", tg, "admin-test") or "(sem resposta)"
    for i in range(0, len(reply), 3900):
        _send_text(token, tg, reply[i:i + 3900])
    for png, caption in pop_charts(tg):
        try:
            _send_photo(token, tg, png, caption)
        except Exception as exc:
            print(f"foto falhou: {exc}")
    print(f"test-drive de {path.name} entregue a {tg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
