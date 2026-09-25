"""O vault é documentação viva: link quebrado passa despercebido por meses.

Nota que ninguém alcança pela Home é nota que não existe na prática — foi
assim que metade do que esta semana produziu ficou fora do mapa até alguém
pedir "documente tudo".
"""
import pathlib
import re

VAULT = pathlib.Path(__file__).resolve().parent.parent / "docs/vault/KKNuths"


def _notas():
    return {p.stem: p for p in VAULT.rglob("*.md")}


def test_vault_existe_e_tem_home():
    notas = _notas()
    assert notas, "vault sumiu"
    assert "00 - KKNuths Home" in notas


def test_nenhum_wikilink_quebrado():
    notas = _notas()
    quebrados = []
    for stem, p in sorted(notas.items()):
        for m in re.finditer(r"\[\[([^\]|#]+)", p.read_text()):
            alvo = m.group(1).strip()
            if alvo and alvo not in notas:
                quebrados.append(f"{stem} -> [[{alvo}]]")
    assert not quebrados, "wikilinks sem destino: " + "; ".join(quebrados)


def test_toda_nota_alcancavel_pela_home():
    """Documentação órfã não é documentação: ninguém chega nela."""
    notas = _notas()
    home = notas["00 - KKNuths Home"].read_text()
    citadas = {m.group(1).strip()
               for m in re.finditer(r"\[\[([^\]|#]+)", home)}
    # uma nota pode ser alcançada pela Home OU por outra que a Home cita
    alcancaveis = set(citadas)
    for nome in list(citadas):
        p = notas.get(nome)
        if p:
            alcancaveis |= {m.group(1).strip() for m in
                            re.finditer(r"\[\[([^\]|#]+)", p.read_text())}
    orfas = set(notas) - alcancaveis - {"00 - KKNuths Home"}
    assert not orfas, f"notas que a Home não alcança: {sorted(orfas)}"


def test_o_que_esta_semana_produziu_esta_documentado():
    """Canário de conteúdo: os assuntos que custaram caro têm que estar
    escritos, senão a próxima pessoa (ou eu, daqui a um mês) repete."""
    texto = "\n".join(p.read_text() for p in VAULT.rglob("*.md"))
    for assunto in ("suprema", "replayInfo.php", "divmod(v, 16)",
                    "Telegram Stars", "custo_llm", "piloto",
                    "guarda", "multiway", "backup_db"):
        assert assunto.lower() in texto.lower(), f"não documentado: {assunto}"
