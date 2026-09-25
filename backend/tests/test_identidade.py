"""Usuário sem @ no Telegram não pode virar "None" no banco.

O primeiro usuário externo (28/07 02:01) entrou, treinou e saiu — e ficou
gravado como `username: null`. Não dava para saber quem era nem para falar
com ele. O Telegram SEMPRE manda first_name; o `@` é que é opcional, e eu
guardava só o `@`.
"""
from app.bot import handlers


class _User:
    def __init__(self, uid, username=None, full_name=None):
        self.id = uid
        self.username = username
        self.full_name = full_name


def setup_function():
    handlers._IDENTIDADE_VISTA.clear()


def test_prefere_o_arroba_mas_cai_no_nome_do_perfil():
    assert handlers._uname(_User(1, "leo_poker", "Leo J")) == "leo_poker"
    assert handlers._uname(_User(1, None, "Leo Jacquier")) == "Leo Jacquier"
    assert handlers._uname(_User(1, None, None)) is None


class _Repo:
    enabled = True

    def __init__(self):
        self.chamadas = []

    def get_or_create_user(self, tg, nome=None, lang="pt"):
        self.chamadas.append((tg, nome))
        return {"id": "u1"}


def test_identidade_gravada_com_o_nome_do_perfil():
    repo = _Repo()
    original = handlers.get_repository
    handlers.get_repository = lambda: repo
    try:
        handlers._sincronizar_identidade(8853316212, "Fulano de Tal")
        assert repo.chamadas == [(8853316212, "Fulano de Tal")]
    finally:
        handlers.get_repository = original


def test_nao_repete_o_select_a_cada_evento():
    """Sincronizar identidade em todo evento custaria um select por ação."""
    repo = _Repo()
    original = handlers.get_repository
    handlers.get_repository = lambda: repo
    try:
        for _ in range(5):
            handlers._sincronizar_identidade(42, "Ricardo")
        assert len(repo.chamadas) == 1
        # nome MUDOU (aluno trocou o @) -> sincroniza de novo
        handlers._sincronizar_identidade(42, "Ricardo Farah")
        assert len(repo.chamadas) == 2
    finally:
        handlers.get_repository = original


def test_sem_nome_nao_escreve_nada():
    """Não sobrescrever um nome bom com None — o backfill é só de melhora."""
    repo = _Repo()
    original = handlers.get_repository
    handlers.get_repository = lambda: repo
    try:
        handlers._sincronizar_identidade(42, None)
        assert repo.chamadas == []
    finally:
        handlers.get_repository = original


def test_falha_no_banco_nao_derruba_o_handler():
    class _Ruim:
        enabled = True

        def get_or_create_user(self, *a, **k):
            raise RuntimeError("banco fora")

    original = handlers.get_repository
    handlers.get_repository = lambda: _Ruim()
    try:
        handlers._sincronizar_identidade(42, "Alguem")   # não levanta
    finally:
        handlers.get_repository = original


def test_log_sincroniza_ANTES_de_registrar_o_evento():
    """Assim o /start já nasce com nome, em vez de esperar o aluno passar
    por um caminho que forneça a identidade."""
    import inspect

    fonte = inspect.getsource(handlers._log)
    assert fonte.index("_sincronizar_identidade") < fonte.index("log_event")


def test_nenhum_call_site_usa_username_cru():
    """`.username` cru perde exatamente quem não tem @ — que foi o caso."""
    import inspect

    fonte = inspect.getsource(handlers)
    assert "effective_user.username)" not in fonte, (
        "use _uname(update.effective_user), que cai no nome do perfil")
