"""O recado de um tiro só — e a trava que impede o segundo.

Mandar mensagem para uma pessoa real é irreversível. Repetir um pedido de
desculpas é pior que não ter feito.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import recado_amostra as R  # noqa: E402


def test_o_texto_assume_o_erro_na_primeira_linha():
    """Ele já sabe que o número estava errado — foi ele quem mandou o print
    do VPIP real. Rodeio aqui soaria pior que o erro."""
    assert R.TEXTO.splitlines()[0].endswith("erro meu.")


def test_o_texto_explica_o_vies_e_nao_a_amostra_pequena():
    """A confusão entre os dois é o que faria ele mandar MAIS replays
    achando que resolve."""
    assert "com 92 replays ou com 5.000" in R.TEXTO


def test_nao_pede_o_que_o_app_dele_nao_exporta():
    """Ele joga só PPPoker e Suprema, que não têm export de sessão. Pedir
    .txt seria pedir o impossível e faria a ferramenta parecer quebrada."""
    assert ".txt" not in R.TEXTO
    assert "não existe export de sessão inteira" in R.TEXTO


def test_o_texto_fecha_no_que_ele_ganha():
    assert "quanto custou o que você fez" in R.TEXTO
    assert "Manda os replays do mesmo jeito" in R.TEXTO


def test_lista_o_que_continua_funcionando():
    """Sem isso ele lê 'a ferramenta parou de funcionar pra mim'."""
    for pedaco in ("equity", "treino", "leitura de vilão", "range"):
        assert pedaco in R.TEXTO


def test_cabe_numa_mensagem_do_telegram():
    assert len(R.TEXTO) < 4000


class _Repo:
    def __init__(self, ja):
        self.ja = ja
        self.enabled = True

    class _T:
        def __init__(self, ja):
            self.ja = ja

        def select(self, *a, **k):
            return self

        def eq(self, *a):
            return self

        def limit(self, *a):
            return self

        def execute(self):
            return type("R", (), {"data": [{"id": 1}] if self.ja else []})()

    @property
    def client(self):
        repo = self

        class _C:
            def table(self, _):
                return _Repo._T(repo.ja)
        return _C()


def test_a_trava_le_o_evento():
    assert R.ja_enviado(_Repo(True)) is True
    assert R.ja_enviado(_Repo(False)) is False


def test_banco_fora_do_ar_nao_manda():
    """Na dúvida, NÃO manda: o custo de repetir é maior que o de atrasar."""
    class _Quebrado:
        enabled = True

        @property
        def client(self):
            raise RuntimeError("banco fora")

    assert R.ja_enviado(_Quebrado()) is True


def test_o_destinatario_esta_explicito_no_codigo():
    """Mensagem para pessoa real não sai de uma consulta que pode mudar."""
    assert R.DESTINATARIO == 6921203436
