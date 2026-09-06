"""A sonda passa a olhar o SITE, e o portão do deploy também.

São dois processos no pm2 — `poker-bot` e `poker-web` — e até 09/08 tudo que
vigiava produção olhava só o primeiro: o portão do auto-deploy conferia
`pm2 describe poker-bot`, e esta sonda conferia webhook/getMe do Telegram.
O site podia cair com o bot verde, o deploy anunciando "🔄 Bot atualizado", e
ninguém sabia até o dono abrir o navegador.

O que estes testes prendem:

  * site fora vira VERMELHO, e o alerta diz que foi o SITE (chamar isso de
    "BOT NÃO ESTÁ RECEBENDO" manda o dono depurar o processo errado);
  * `/health` sozinho não basta — ele responde 200 com o resto quebrado;
  * app de pé e borda fora tem mensagem PRÓPRIA, porque o remédio é outro
    (Caddy/DNS/certificado, não `pm2 logs poker-web`);
  * não checado nunca alarma, que é a regra que já valia para o silêncio.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import sonda_recebimento as S  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


# ---- o veredito ------------------------------------------------------------

def test_site_fora_e_vermelho_e_o_alerta_diz_que_foi_o_site():
    v = S.avaliar("", True, 0.1, True, web=(False, "SITE fora: caiu"))
    assert v["nivel"] == "quebrado"
    txt = S.texto_do_alerta(v)
    assert "SITE FORA DO AR" in txt
    assert "BOT NÃO ESTÁ RECEBENDO" not in txt, (
        "queda do site anunciada como queda do bot manda depurar o processo "
        "errado")


def test_bot_e_site_juntos_tem_titulo_proprio():
    v = S.avaliar("", False, 0.1, True, web=(False, "SITE fora: caiu"))
    assert "BOT E SITE FORA" in S.texto_do_alerta(v)


def test_site_ok_nao_inventa_problema():
    v = S.avaliar("", True, 0.1, True, web=(True, ""))
    assert v["nivel"] == "ok" and S.texto_do_alerta(v) == ""


def test_site_nao_checado_nunca_alarma():
    """Mesma regra do silêncio: "não sei" não acorda ninguém."""
    v = S.avaliar("", True, 0.1, True)
    assert v["nivel"] == "ok" and v["web_ok"] is None


def test_o_bot_continua_sendo_vigiado():
    """A checagem nova não pode ter apagado a antiga."""
    assert S.avaliar("https://x/hook", True, 0.1, True,
                     web=(True, ""))["nivel"] == "quebrado"
    assert S.avaliar("", False, 0.1, True, web=(True, ""))["nivel"] == "quebrado"
    assert S.avaliar("", True, 9.0, True, web=(True, ""))["nivel"] == "suspeita"


# ---- a checagem de verdade -------------------------------------------------

@pytest.fixture
def web(monkeypatch):
    """Instala respostas por URL. Ausente = conexão recusada."""
    def _instalar(mapa: dict[str, tuple[int, int]]):
        class _R:
            def __init__(self, st, tam):
                self.status, self._c = st, b"x" * tam

            def read(self):
                return self._c

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def _abrir(url, timeout=None):
            if url not in mapa:
                raise ConnectionRefusedError("conexão recusada")
            return _R(*mapa[url])

        monkeypatch.setattr(S.urllib.request, "urlopen", _abrir)
    return _instalar


L, P = S.WEB_LOCAL, S.WEB_PUBLICO


def test_tudo_de_pe(web):
    web({f"{L}/health": (200, 88), f"{L}/": (200, 700_000),
         f"{P}/health": (200, 88)})
    assert S.checar_web() == (True, "")


def test_uvicorn_morto(web):
    web({})
    ok, motivo = S.checar_web()
    assert not ok and "poker-web" in motivo


def test_health_responde_e_a_pagina_esta_quebrada(web):
    """O caso que um teste de `/health` sozinho deixaria passar: a rota de
    saúde tem três linhas e não toca em template nenhum."""
    web({f"{L}/health": (200, 88), f"{P}/health": (200, 88)})
    ok, motivo = S.checar_web()
    assert not ok and "página quebrou" in motivo


def test_pagina_que_volta_vazia_tambem_conta_como_quebrada(web):
    """200 com corpo vazio é falha de render, não sucesso."""
    web({f"{L}/health": (200, 88), f"{L}/": (200, 12),
         f"{P}/health": (200, 88)})
    assert not S.checar_web()[0]


def test_app_de_pe_e_borda_fora_tem_diagnostico_proprio(web):
    """Local ok e público fora é Caddy/DNS/certificado. Mandar o dono olhar
    `pm2 logs poker-web` aqui é mandá-lo para o lugar errado."""
    web({f"{L}/health": (200, 88), f"{L}/": (200, 700_000)})
    ok, motivo = S.checar_web()
    assert not ok
    assert "BORDA" in motivo and "Caddy" in motivo
    assert "pm2 logs" not in motivo


# ---- o portão do deploy ----------------------------------------------------

def test_web_responde_reprova_quando_o_site_nao_responde_200():
    """Roda a função do `auto_update.sh` de verdade, com um `curl` de mentira
    no PATH — bash não se importa se o curl é o de verdade."""
    script = (RAIZ / "deploy/auto_update.sh").read_text()
    ini = script.index("web_responde() {")
    corpo = script[ini:script.index("\n}\n", ini) + 3]

    def _rodar(codigo: str) -> int:
        return subprocess.run(
            ["bash", "-c",
             f"curl() {{ echo -n '{codigo}'; }}\n{corpo}\nweb_responde"],
            capture_output=True).returncode

    assert _rodar("200") == 0
    assert _rodar("502") != 0, "site em 502 estaria sendo aprovado"
    assert _rodar("000") != 0, "site fora do ar estaria sendo aprovado"


def test_o_portao_e_o_rollback_cobrem_os_DOIS_processos():
    """CONTRATO HONESTO: shell não se importa, então esta parte é leitura do
    arquivo — o teste acima é que executa a lógica. O que se prende aqui é a
    LIGAÇÃO: a função existir e ninguém chamar não vale nada.
    """
    script = (RAIZ / "deploy/auto_update.sh").read_text()

    portao = script[script.index("export PORTAO_JA_PASSOU=1"):
                    script.index("MSG=$(cd")]
    assert "web_responde" in portao, (
        "o portão aprova o deploy sem conferir o site")
    assert "poker-bot" in portao, "o portão parou de conferir o bot"

    rollback = script[script.index("SUBIDA FALHOU"):]
    assert "pm2 restart poker-web" in rollback, (
        "o rollback restaura o disco e deixa o poker-web rodando de memória "
        "o código reprovado")
