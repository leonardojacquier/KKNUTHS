"""A imagem de propaganda do clube — reconhecer sem gastar visão nem cota.

O Compartilhar do PPPoker manda DUAS mensagens: primeiro a arte da mesa
vazia (foto, sem legenda), depois o link do replay. O desvio de 23/08 só
cobria as duas na mesma mensagem. Medido em 19/09: 8 das 10 fotos desde
20/08 tiveram link de replay do mesmo aluno em 30-90 s. Cada uma ia pra
visão, que alucinava uma mão (conf 0,5); o coach escrevia "sem imagem
legível"; o juiz dava 3,5; o aluno pagava uma unidade de cota e ~US$0,15
pra ouvir isso. Em 14/09, quatro em 90 minutos.

Duas coisas que NÃO funcionam, e por quê:
  · segurar a foto esperando o link — 30-90 s de atraso em todo print
    legítimo, pra poupar uma propaganda;
  · fingerprint fixo no código — o container não alcança o bucket, e a
    arte pode mudar quando o app atualizar.

O que funciona: a arte é SEMPRE a mesma. Basta reconhecê-la pelo hash
perceptual depois da primeira vez — e a primeira vez se anuncia sozinha,
porque o link chega logo depois. Aprender = "foto sem legenda + link de
replay do mesmo aluno em até JANELA_S" → o hash daquela foto é propaganda.

Por que aprender pelo link e não pela visão: a visão devolve conf 0,5 e uma
mão inventada, não "isto é propaganda" — sinal ruim. O link é um fato.

Persistência em `bot_events` (evento `imagem_promocional`), porque o
processo reinicia a cada deploy e memória de processo morreria junto. O
conhecimento é global: o que um aluno ensina vale para todos.
"""
from __future__ import annotations

import io
import logging
import time

from app.bot.memoria_do_processo import guardar_com_prazo
from app.db import get_repository

log = logging.getLogger(__name__)

# hash médio 8x8: 64 bits. Sobrevive à recompressão do Telegram (medido no
# teste com JPEG qualidade 55) e distingue artes diferentes por dezenas de bits.
_LADO = 8
TOLERANCIA = 6          # bits de diferença ainda considerados "a mesma arte"
JANELA_S = 180.0        # foto -> link: medido 30-90 s; folga para o aluno lento
_RECARGA_S = 600.0      # relê o banco a cada 10 min (o aprendizado é raro)

EVENTO_APRENDIDA = "imagem_promocional"
EVENTO_IGNORADA = "foto_promocional_ignorada"

TEXTO_PROPAGANDA = (
    "🖼 Essa é a arte de propaganda do clube, não a mão. A mão está no *link "
    "do replay* que o app manda junto — cola ele aqui que eu analiso. 🃏")

# telegram_id -> (quando, hash) das fotos SEM legenda que foram pra visão
FOTOS_RECENTES: dict[int, tuple[float, str]] = {}
# cache das artes conhecidas: (quando carregou, {hashes})
_CONHECIDAS: list = [0.0, set()]


def hash_da_imagem(conteudo: bytes) -> str | None:
    """Hash perceptual (média 8x8 em cinza) como 16 hex. None se não abrir."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(conteudo)).convert("L")
        img = img.resize((_LADO, _LADO), Image.Resampling.LANCZOS)
        # Pillow 12 depreciou getdata(); o substituto não existe nas antigas
        ler = getattr(img, "get_flattened_data", None) or img.getdata
        px = list(ler())
    except Exception:
        return None
    media = sum(px) / len(px)
    bits = 0
    for p in px:
        bits = (bits << 1) | (1 if p > media else 0)
    return f"{bits:0{_LADO * _LADO // 4}x}"


def distancia(h1: str | None, h2: str | None) -> int:
    """Distância de Hamming entre dois hashes; 'infinita' se algum faltar."""
    if not h1 or not h2:
        return _LADO * _LADO
    return bin(int(h1, 16) ^ int(h2, 16)).count("1")


def _conhecidas() -> set[str]:
    agora = time.time()
    if agora - _CONHECIDAS[0] < _RECARGA_S and _CONHECIDAS[1]:
        return _CONHECIDAS[1]
    achadas: set[str] = set()
    try:
        repo = get_repository()
        if repo.enabled:
            rows = (repo.client.table("bot_events").select("detail")
                    .eq("event", EVENTO_APRENDIDA)
                    .order("created_at", desc=True).limit(200)
                    .execute().data) or []
            achadas = {str((r.get("detail") or {}).get("hash") or "")
                       for r in rows} - {""}
    except Exception as exc:      # noqa: BLE001 — sem banco, sem memória; nunca derruba a foto
        log.debug("não carreguei as artes conhecidas: %s", exc)
    _CONHECIDAS[0] = agora
    _CONHECIDAS[1] = achadas
    return achadas


def e_propaganda(h: str | None) -> bool:
    """A foto é uma arte já aprendida?"""
    if not h:
        return False
    return any(distancia(h, k) <= TOLERANCIA for k in _conhecidas())


def registrar_foto(telegram_id: int, h: str | None) -> None:
    """Foto sem legenda foi pra visão: guarda o hash por JANELA_S, caso o
    link chegue em seguida e revele que era propaganda."""
    if h:
        guardar_com_prazo(FOTOS_RECENTES, telegram_id, (time.time(), h), JANELA_S)


def aprender_da_foto_recente(telegram_id: int) -> str | None:
    """Chegou link de replay: se este aluno mandou foto sem legenda há menos
    de JANELA_S, aquela foto era a propaganda. Devolve o hash aprendido.

    Um print de verdade seguido de link no mesmo intervalo também seria
    aprendido — e não faz mal: print real é único por mão e nunca repete,
    então o hash nunca vai casar com nada. A arte, ao contrário, repete
    sempre. É isso que torna o aprendizado seguro sem olhar a visão.
    """
    item = FOTOS_RECENTES.get(telegram_id)
    if not item:
        return None
    quando, h = item
    if time.time() - quando > JANELA_S:
        FOTOS_RECENTES.pop(telegram_id, None)
        return None
    FOTOS_RECENTES.pop(telegram_id, None)
    if e_propaganda(h):
        return h                  # já sabia; não duplica o evento
    try:
        repo = get_repository()
        if repo.enabled:
            repo.log_event(telegram_id, None, EVENTO_APRENDIDA,
                           {"hash": h, "aprendida_de": "link_apos_foto"})
    except Exception as exc:      # noqa: BLE001
        log.warning("não persisti a arte aprendida: %s", exc)
    _CONHECIDAS[1].add(h)
    _CONHECIDAS[0] = time.time()
    return h


def _esquecer_tudo() -> None:
    """Só para testes: zera a memória do processo."""
    FOTOS_RECENTES.clear()
    _CONHECIDAS[0] = 0.0
    _CONHECIDAS[1] = set()
