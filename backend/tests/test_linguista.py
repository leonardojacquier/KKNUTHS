"""O glossário vivo: IA propõe, o dono aprova, as camadas mecânicas executam.

Pedido do dono (02/08): "uma camadinha de IA pra fazer essa avaliação... na
lógica de um agente que aprende sozinho". O desenho separa os poderes:
o linguista (IA) só PROPÕE; aprovar é do dono (/termo, um toque); executar
é do corretor e do juiz, deterministicamente. A IA nunca edita o prompt
nem aprova a si mesma — proposta ruim descartada custa zero, prompt editado
errado contamina toda análise em silêncio.
"""
from scripts.linguista import filtrar, texto_do_aviso


def test_filtra_proposta_malformada_e_duplicada():
    achados = [
        {"errado": "mão de ferro", "certo": "nuts", "exemplo": "..."},
        {"errado": "mão de ferro", "certo": "nuts"},          # duplicada
        {"errado": "", "certo": "x"},                          # vazia
        {"errado": "abc", "certo": "x"},                       # curta demais
        {"errado": "y" * 80, "certo": "x"},                    # longa demais
        {"errado": "top pair", "certo": "top pair"},           # errado==certo
        None,                                                  # lixo
    ]
    out = filtrar(achados)
    assert [p["errado"] for p in out] == ["mão de ferro"]


def test_termo_ja_proibido_no_prompt_nao_vira_proposta():
    """'check atrás' já está no TERMOS_REGRA — propor de novo é ruído."""
    assert filtrar([{"errado": "check atrás", "certo": "check behind"}]) == []


def test_teto_de_propostas():
    muitos = [{"errado": f"termo inventado {i}", "certo": "x"}
              for i in range(20)]
    assert len(filtrar(muitos)) == 8


def test_aviso_ensina_os_tres_vereditos():
    txt = texto_do_aviso([{"id": 3, "errado": "mão de ferro",
                           "certo": "nuts", "exemplo": "tinha a mão de ferro"}])
    assert "#3" in txt and "mão de ferro" in txt
    for cmd in ("/termo ok N", "/termo ok N corrigir", "/termo nao N"):
        assert cmd in txt


def test_glossario_aprovado_entra_no_corretor():
    """Termo aprovado como 'corrigir' passa a ser trocado na entrega."""
    from app.agent import termos

    termos._CACHE.update({"ate": float("inf"),
                          "corrigir": [(termos._regex_literal("mão de ferro"),
                                        "nuts")],
                          "vigiar": ["contar as fichas"]})
    try:
        assert termos.corrigir("Você tinha a mão de ferro ali.") \
            == "Você tinha a nuts ali."
        assert termos.corrigir("encarta alta") == "encarta alta"  # borda ok
        assert termos.vigiados() == ["contar as fichas"]
    finally:
        termos._CACHE.update({"ate": 0.0, "corrigir": [], "vigiar": []})


def test_juiz_soma_o_glossario_vivo():
    from scripts.output_judge import judge_answer

    t = "No river ele foi contar as fichas antes de pagar."
    assert not any("calque" in p for p in judge_answer(t))
    assert any("contar as fichas" in p for p in
               judge_answer(t, calques_extra=("contar as fichas",)))


def test_linguista_nunca_toca_no_prompt():
    """A fronteira do desenho: aprender = acumular DADOS, não editar código."""
    import inspect

    from scripts import linguista

    fonte = inspect.getsource(linguista)
    assert "TERMOS_REGRA" in fonte, "lê o prompt para não repetir proposta"
    assert "_SYSTEM" not in fonte
    import re as _re

    assert ".write" not in fonte
    assert not _re.search(r"(?<!url)open\(", fonte), "sem escrita em arquivo"
