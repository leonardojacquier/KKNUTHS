"""O portão de testes roda ANTES de produção ser substituída.

Achado da auditoria de 07/08, reproduzido pelo agente: a ordem era

    1. rsync do código novo -> /opt/poker-bot     (produção JÁ substituída)
    2. vps_deploy.sh -> pytest                     (portão)
    3. pm2 restart                                 (só se o portão passou)

Com teste vermelho, o passo 3 não acontecia e o dono recebia no Telegram
"o bot continua na versão anterior". Era mentira: o processo seguia com o
código antigo apenas porque o Python já estava carregado em MEMÓRIA. O disco
tinha a versão reprovada, e o próximo restart — crash, reboot, `pm2 restart`,
o deploy seguinte — subia ela em silêncio. `grep rollback` no script: zero.

Não dá para rodar o deploy aqui (é VPS), mas a ORDEM é o bug, e ordem se lê.
Este teste é a memória disso.
"""
from __future__ import annotations

from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
AUTO = (DEPLOY / "auto_update.sh").read_text()
VPS = (DEPLOY / "vps_deploy.sh").read_text()


def _pos(texto: str, agulha: str) -> int:
    i = texto.find(agulha)
    assert i >= 0, f"não achei {agulha!r} no script"
    return i


def test_o_pytest_vem_antes_do_rsync_para_producao():
    """A inversão que era o bug inteiro."""
    portao = _pos(AUTO, "-m pytest -q tests/")
    copia = _pos(AUTO, 'rsync -a --delete')
    assert portao < copia, (
        "o rsync para produção acontece ANTES do pytest: código reprovado "
        "volta a chegar ao disco de produção")


def test_o_portao_roda_no_clone_e_nao_em_producao():
    """Testar em $APP seria testar o que já substituiu produção."""
    linha = next(l for l in AUTO.splitlines() if "-m pytest -q tests/" in l)
    assert '"$REPO/backend"' in linha, (
        f"o portão não aponta para o clone: {linha.strip()}")


def test_teste_vermelho_aborta_sem_tocar_em_producao():
    trecho = AUTO[_pos(AUTO, "-m pytest -q tests/"):]
    fim = trecho.find("rsync -a --delete")
    assert "exit 1" in trecho[:fim], "não aborta antes de copiar"
    # e a mensagem tem que dizer a verdade nova
    assert "produção não foi tocada" in AUTO


def test_existe_snapshot_e_restauracao():
    """O portão cobre teste vermelho; não cobre código que passa e morre no
    import. Para esse caso é preciso voltar atrás sem esperar um push."""
    assert "BACKUP=" in AUTO
    snapshot = _pos(AUTO, "BACKUP=/tmp/poker-bot-anterior")
    copia = _pos(AUTO, "rsync -a --delete")
    assert snapshot < copia, "o snapshot tem que ser feito ANTES de copiar"
    assert "restaurei a versão anterior" in AUTO
    assert "pm2 restart poker-bot" in AUTO


def test_confere_que_o_bot_subiu_de_verdade():
    """Sem checar o pm2, 'deploy OK' significa apenas 'o script terminou'."""
    assert 'pm2 describe poker-bot' in AUTO and 'grep -q "online"' in AUTO


def test_nao_paga_pytest_duas_vezes():
    """3 minutos por push, duas vezes, num cron de 2 em 2 minutos."""
    assert "PORTAO_JA_PASSOU=1" in AUTO
    assert 'PORTAO_JA_PASSOU:-0' in VPS
    # mas rodando à mão o portão continua valendo
    assert "-m pytest -q tests/" in VPS


def test_dependencia_nova_e_instalada_antes_do_portao():
    """Senão o teste falha por ImportError e culpa o commit errado."""
    pip = _pos(AUTO, 'pip" install -q -r')
    portao = _pos(AUTO, "-m pytest -q tests/")
    assert pip < portao


@pytest.mark.parametrize("script", ["auto_update.sh", "vps_deploy.sh"])
def test_scripts_sao_shell_valido(script):
    """Erro de sintaxe aqui só apareceria no VPS, no meio de um deploy."""
    import shutil
    import subprocess

    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash indisponível")
    r = subprocess.run([bash, "-n", str(DEPLOY / script)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
