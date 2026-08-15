"""O comparador isola o PROMPT como variável — nada mais."""
from __future__ import annotations

from scripts.comparar_voz import montar_markdown


def test_o_markdown_traz_os_dois_lados_e_o_modelo():
    md = montar_markdown([{
        "hand_id": "abc", "modelo": "claude-opus-4-8",
        "antes": "✅ Você jogou bem\n\nA conta que mais pesa: era jam.",
        "depois": "✅ Você jogou bem\n\nCom 12bb, jam é a única linha.",
    }])
    assert "ANTES" in md and "DEPOIS" in md
    assert "claude-opus-4-8" in md
    assert "A conta que mais pesa" in md


def test_par_sem_depois_e_marcado_e_nao_some():
    """Falha de geração tem que aparecer; sumir com o par faria a
    comparação parecer melhor do que é."""
    md = montar_markdown([{"hand_id": "x", "modelo": "m",
                           "antes": "texto", "depois": None}])
    assert "falhou" in md.lower()
