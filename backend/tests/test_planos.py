"""Teto por plano: o meio-termo entre 50 e ilimitado.

Antes só existiam dois mundos. Dar 100 análises a um testador exigia dar
ILIMITADO — exatamente o que não dá para bancar sem saber o custo.
"""
import app.quota as q
from app.bot.processing import texto_do_plano


def setup_function():
    q.reset_memory()


# ------------------------------------------------------------------- tetos
def test_piloto_tem_o_dobro_do_free():
    assert q.limite_do_plano("free") == q.FREE_MONTHLY_ANALYSES
    assert q.limite_do_plano("piloto") == 100
    assert q.limite_do_plano("pro") is None
    assert q.limite_do_plano("premium") is None


def test_plano_desconhecido_cai_no_free_e_nao_no_ilimitado():
    """Um typo em /planode não pode virar análise ilimitada de graça."""
    assert q.limite_do_plano("pilotoo") == q.FREE_MONTHLY_ANALYSES
    assert q.limite_do_plano("") == q.FREE_MONTHLY_ANALYSES
    assert q.limite_do_plano(None) == q.FREE_MONTHLY_ANALYSES


def test_maiuscula_e_espaco_nao_derrubam_o_teto():
    assert q.limite_do_plano("  Piloto ") == 100


# ------------------------------------------------------- cota de verdade
class _Repo:
    """Repo falso: conta análises do mês por usuário."""
    enabled = True

    def __init__(self, usados):
        self._usados = usados

        class _C:
            def table(_self, _nome):
                return _self

            def select(_self, *a, **k):
                return _self

            def eq(_self, *a, **k):
                return _self

            def gte(_self, *a, **k):
                return _self

            def execute(_self):
                class R:
                    count = usados
                return R()
        self.client = _C()


def test_piloto_continua_liberado_onde_o_free_ja_travou():
    user_free = {"id": "u1", "plan": "free"}
    user_piloto = {"id": "u1", "plan": "piloto"}
    repo = _Repo(usados=60)          # 60 análises no mês

    r_free = q.check_quota(111, user_free, repo)
    assert r_free.allowed is False and r_free.remaining == 0

    r_piloto = q.check_quota(111, user_piloto, repo)
    assert r_piloto.allowed is True and r_piloto.remaining == 40


def test_admin_segue_ilimitado():
    r = q.check_quota(q.ADMIN_TELEGRAM_ID, {"id": "u1", "plan": "free"},
                      _Repo(usados=9999))
    assert r.allowed is True and r.remaining == -1


def test_banco_caido_ainda_bloqueia_no_piloto():
    """Fail-closed vale para todo plano com teto, não só para o free."""
    class _Quebrado(_Repo):
        def __init__(self):
            super().__init__(0)

            class _C:
                def table(_s, _n):
                    raise RuntimeError("banco fora")
            self.client = _C()

    r = q.check_quota(111, {"id": "u1", "plan": "piloto"}, _Quebrado())
    assert r.allowed is False and r.degraded is True


# ------------------------------------------------------------------ texto
def test_plano_mostra_o_teto_de_quem_pergunta():
    """O testador com 100 lendo 'você tem 50' é o produto mentindo pra ele."""
    txt = texto_do_plano("piloto", restantes=73, teto=100)
    assert "*100* análises" in txt and "restam *73*" in txt
    assert "Piloto" in txt

    livre = texto_do_plano("free", restantes=12, teto=50)
    assert "*50* análises" in livre and "Beta gratuito" in livre

    ilimitado = texto_do_plano("pro", restantes=-1, teto=None)
    assert "ilimitadas" in ilimitado and "50" not in ilimitado


# ------------------------------------------------------------- /planode
def test_planode_recusa_plano_invalido_antes_de_tocar_no_banco():
    from app.bot.processing import mudar_plano_reply

    txt, alvo = mudar_plano_reply("12345", "pilotoo")
    assert alvo is None and "Plano desconhecido" in txt
    assert "`piloto`" in txt          # mostra as opções válidas


def test_planos_manuais_cobre_os_que_o_bot_atribui():
    assert set(q.PLANOS_MANUAIS) == {"free", "piloto", "pro", "premium"}
