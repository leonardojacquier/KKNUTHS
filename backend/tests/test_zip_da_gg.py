"""O PokerCraft da GG exporta em .zip — e o bot recusava.

08/09, 15:20 e 15:23: o Ricardo (232 mãos, o único usuário pesado do
piloto) mandou o histórico de um torneio da GG duas vezes. Resposta: "formato
'zip' não suportado". O .txt estava lá dentro — o próprio evento guardou o
nome: "GG20260907 - Tournament #310131883 - Mini Heater 2.50 [Bounty
Turbo].txt". Depois disso, dois quizzes e nunca mais uma mão.
"""
from __future__ import annotations

import io
import pathlib
import zipfile

from app.ingestion.pipeline import ingest

_AMOSTRA = pathlib.Path(__file__).parent / "sample_hands" / "gg_tournament_paste.txt"


def _zip(arquivos: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, dado in arquivos.items():
            z.writestr(nome, dado)
    return buf.getvalue()


def test_zip_da_gg_com_um_txt_vira_as_maos_de_dentro():
    txt = _AMOSTRA.read_bytes()
    r = ingest(_zip({"GG20260907 - Tournament #310131883.txt": txt}), "zip")
    esperado = ingest(txt, "txt")
    assert r.hands, f"zip não virou mão: {r.note}"
    assert len(r.hands) == len(esperado.hands)
    assert r.site == esperado.site


def test_zip_reconhecido_pelo_conteudo_mesmo_sem_extensao():
    """Arquivo que chega sem extensão (ou com nome genérico) mas é zip."""
    r = ingest(_zip({"hh.txt": _AMOSTRA.read_bytes()}), "txt")
    assert r.hands


def test_zip_com_varios_torneios_junta_todos():
    txt = _AMOSTRA.read_bytes()
    um = len(ingest(txt, "txt").hands)
    r = ingest(_zip({"t1.txt": txt, "pasta/t2.txt": txt.replace(b"TM", b"TX")}), "zip")
    assert len(r.hands) >= um, "segundo torneio do zip foi ignorado"


def test_zip_sem_historico_explica_em_vez_de_dizer_nao_suportado():
    r = ingest(_zip({"foto.jpg": b"\xff\xd8\xff"}), "zip")
    assert not r.hands
    assert "não suportado" not in (r.note or "")
    assert ".txt" in (r.note or "")


def test_zip_corrompido_nao_derruba():
    r = ingest(b"PK\x03\x04isto nao e um zip de verdade", "zip")
    assert not r.hands and r.note


def test_trava_contra_zip_bomba():
    """Um zip de 1 kB que abre 200 MB derrubaria o processo do bot."""
    from app.ingestion import pipeline

    gigante = b"a" * (pipeline.ZIP_TETO_BYTES + 1)
    r = ingest(_zip({"bomba.txt": gigante}), "zip")
    assert not r.hands
    assert "grande" in (r.note or "").lower()
