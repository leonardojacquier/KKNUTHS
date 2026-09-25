"""BACKUP do banco — o histórico do aluno é o ativo, e ele não tinha cópia.

Situação que motivou: todo o valor acumulado (mãos, análises, caderno do
coach, evolução do estilo) vive num único Postgres gerenciado. Um `delete`
errado, uma migração torta ou o projeto pausado e não havia de onde voltar.

Este script tira uma cópia COMPLETA em JSON comprimido, no disco do VPS,
todo dia. É deliberadamente burro: sem dependência de pg_dump, sem rede
além do próprio Supabase, e o arquivo é legível — dá pra abrir e conferir.

PRIVACIDADE: o dump contém mãos e conversas de aluno. Fica SÓ no VPS
(BACKUP_DIR, fora do repo), nunca vai pro git nem pro Telegram.

Cron:  0 4 * * *  (4h UTC = 1h BRT, fora do horário de jogo)
Restaurar:  python scripts/backup_db.py --restaurar <arquivo.json.gz>
            (só insere o que falta; nunca sobrescreve linha existente)
"""
from __future__ import annotations

import gzip
import json
import os
import pathlib
import sys
import urllib.request
from datetime import datetime, timezone

from app.config import get_settings
from app.db import get_repository

ADMIN_ID = 6452742024
GUARDAR = 14          # dias de cópias mantidas em disco
PAGINA = 1000         # o cliente do Supabase corta em 1000 por resposta

# ordem importa no restore: pai antes de filho (FK)
TABELAS = [
    "users", "subscriptions", "usage_events", "uploads", "hands",
    "hand_analysis", "tournaments", "player_stats", "player_stats_history",
    "player_notes", "bot_events", "pending_drills", "pending_sims",
    "conversation_state", "user_meta",
]
# embedding é vetor de 1536 floats: ~30 KB por linha. Sai do backup — é
# derivado (recalculável a partir do summary) e triplicaria o arquivo.
SEM_COLUNAS = {"hand_analysis": ["embedding"]}


def _destino() -> pathlib.Path:
    d = pathlib.Path(os.getenv("BACKUP_DIR", "/opt/poker-bot/backups"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _avisar(token: str | None, texto: str) -> None:
    """Backup que falha em silêncio é pior que não ter backup."""
    if not token:
        return
    body = json.dumps({"chat_id": ADMIN_ID, "text": texto[:3000],
                       "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


def puxar_tabela(repo, tabela: str) -> list[dict]:
    """Lê a tabela inteira, paginando (a resposta do Supabase é limitada)."""
    fora = SEM_COLUNAS.get(tabela, [])
    linhas: list[dict] = []
    for page in range(500):                      # teto de segurança: 500k
        try:
            r = (repo.client.table(tabela).select("*")
                 .range(page * PAGINA, page * PAGINA + PAGINA - 1).execute())
        except Exception as exc:                 # tabela ausente não mata o backup
            raise RuntimeError(f"{tabela}: {exc}") from exc
        lote = r.data or []
        for row in lote:
            for c in fora:
                row.pop(c, None)
        linhas += lote
        if len(lote) < PAGINA:
            break
    return linhas


def fazer_backup(repo) -> tuple[pathlib.Path, dict]:
    agora = datetime.now(timezone.utc)
    dados: dict[str, list[dict]] = {}
    contagem: dict[str, int] = {}
    for t in TABELAS:
        dados[t] = puxar_tabela(repo, t)
        contagem[t] = len(dados[t])
    pacote = {"gerado_em": agora.isoformat(), "versao": 1,
              "contagem": contagem, "tabelas": dados}
    caminho = _destino() / f"kknuths-{agora:%Y%m%d-%H%M}.json.gz"
    with gzip.open(caminho, "wt", encoding="utf-8") as fh:
        json.dump(pacote, fh, ensure_ascii=False, default=str)
    return caminho, contagem


def limpar_antigos(guardar: int = GUARDAR) -> int:
    """Mantém as N cópias mais recentes; disco de VPS não é infinito."""
    arqs = sorted(_destino().glob("kknuths-*.json.gz"))
    velhos = arqs[:-guardar] if len(arqs) > guardar else []
    for a in velhos:
        try:
            a.unlink()
        except OSError:
            pass
    return len(velhos)


def restaurar(repo, caminho: str) -> dict:
    """Reinsere o que FALTA (upsert por id). Nunca apaga nem sobrescreve
    linha existente — restore não pode ser mais perigoso que a perda."""
    with gzip.open(caminho, "rt", encoding="utf-8") as fh:
        pacote = json.load(fh)
    posto: dict[str, int] = {}
    for t in TABELAS:
        linhas = pacote.get("tabelas", {}).get(t) or []
        if not linhas:
            continue
        n = 0
        for i in range(0, len(linhas), 200):
            lote = linhas[i:i + 200]
            try:
                repo.client.table(t).upsert(
                    lote, ignore_duplicates=True).execute()
                n += len(lote)
            except Exception as exc:
                print(f"  ! {t}: {exc}")
                break
        posto[t] = n
    return posto


def main() -> int:
    settings = get_settings()
    repo = get_repository()
    if not repo.enabled:
        print("ERRO: Supabase não configurado.")
        return 1

    if "--restaurar" in sys.argv:
        arq = sys.argv[sys.argv.index("--restaurar") + 1]
        print(f"restaurando de {arq} (só o que faltar)…")
        for t, n in restaurar(repo, arq).items():
            print(f"  {t}: {n} linha(s)")
        return 0

    token = settings.telegram_bot_token
    try:
        caminho, contagem = fazer_backup(repo)
    except Exception as exc:
        _avisar(token, f"🚨 *Backup do banco FALHOU*: {type(exc).__name__} — "
                       f"{str(exc)[:200]}\nO histórico dos alunos está sem "
                       f"cópia de hoje.")
        print(f"ERRO: {exc}")
        return 1

    apagados = limpar_antigos()
    mb = caminho.stat().st_size / 1e6
    total = sum(contagem.values())
    print(f"backup: {caminho.name} — {total} linhas, {mb:.1f} MB "
          f"({apagados} cópia(s) antiga(s) removida(s))")
    for t, n in contagem.items():
        print(f"  {t}: {n}")

    # linha de vida: se as mãos SUMIREM de um dia pro outro, quero saber
    if contagem.get("hands", 0) == 0:
        _avisar(token, "🚨 *Backup rodou mas a tabela `hands` veio VAZIA.* "
                       "Ou o banco perdeu dados, ou a chave de serviço mudou.")
    repo.log_event(0, "backup_db", "backup_db",
                   {"linhas": total, "mb": round(mb, 2),
                    "arquivo": caminho.name, "hands": contagem.get("hands", 0)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
