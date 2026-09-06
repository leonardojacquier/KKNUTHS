"""A quebra em blocos não pode perder a linha que importa.

O Telegram corta em 4096. A saída do farejador é uma lista de URLs — cortar
no meio de uma URL é o mesmo que perder a URL, e é justamente a linha que a
investigação inteira procura.
"""
import sys

sys.path.insert(0, "scripts")

from farejar_e_reportar import em_blocos  # noqa: E402


def test_texto_curto_vira_um_bloco_so():
    assert em_blocos("linha 1\nlinha 2") == ["linha 1\nlinha 2"]


def test_nada_se_perde_na_quebra():
    texto = "".join(f"https://api.clube.net/v2/hand/{i:04}.json\n"
                    for i in range(300))
    blocos = em_blocos(texto, limite=500)
    assert len(blocos) > 1
    assert "".join(blocos) == texto, "a quebra comeu conteúdo"


def test_url_nao_e_partida_no_meio():
    texto = "".join(f"https://api.clube.net/v2/hand/{i:04}.json\n"
                    for i in range(50))
    for b in em_blocos(texto, limite=200):
        for linha in b.splitlines():
            assert not linha or linha.endswith(".json"), (
                f"URL cortada ao meio: {linha!r}")


def test_linha_gigante_e_partida_sem_sumir():
    """Bundle minificado numa linha só não pode derrubar nem sumir."""
    gigante = "x" * 2500 + "\n"
    blocos = em_blocos(gigante, limite=400)
    assert "".join(blocos) == gigante


def test_bloco_respeita_o_limite():
    texto = "".join(f"linha razoavelmente comprida numero {i}\n"
                    for i in range(200))
    assert all(len(b) <= 400 for b in em_blocos(texto, limite=400))


def test_oneshot_existe_e_e_so_leitura():
    """O oneshot é o canal para rodar no VPS — ele não pode escrever nada
    fora de /opt/poker-bot nem tocar em config global do servidor."""
    import pathlib

    p = (pathlib.Path(__file__).resolve().parent.parent
         / "deploy/oneshot/2026-07-26-farejar-ggpoker.sh")
    texto = p.read_text()
    assert "cd /opt/poker-bot" in texto
    for proibido in ("/etc/", "crontab", "systemctl", "ufw", "apt ",
                     "rm -rf /", "nginx", "caddy"):
        assert proibido not in texto.lower(), proibido
