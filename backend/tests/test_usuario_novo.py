"""Cadastro novo é o evento nº1 do piloto — o dono quer saber NA HORA.

O resumo das 23h já contava usuários novos, mas com atraso de até um dia. No
piloto isso é tarde: se o primeiro convidado entra e trava em algo, o dono
precisa ver antes de mandar os outros nove.
"""
from app.bot import notify


def test_mensagem_traz_quem_e_e_o_que_fazer():
    t = notify.texto_usuario_novo("Ricardo Farah", 6921203436, total=5)
    assert "Ricardo Farah" in t and "6921203436" in t
    assert "5" in t                       # tamanho da base
    # aviso sem ação vira só notificação: os comandos vêm juntos
    assert "/quem 6921203436" in t
    assert "/planode 6921203436 piloto" in t


def test_sem_username_usa_o_id():
    t = notify.texto_usuario_novo(None, 999888777)
    assert "id 999888777" in t
    t2 = notify.texto_usuario_novo("   ", 999888777)
    assert "id 999888777" in t2


def test_dono_entrando_nao_e_noticia():
    enviados = []
    original = notify.avisar
    notify.avisar = lambda tg, txt: enviados.append(tg) or True
    try:
        assert notify.avisar_admin_usuario_novo("Leo", notify.ADMIN_ID) is False
        assert enviados == []
        notify.avisar_admin_usuario_novo("Alguem", 123456)
        assert enviados == [notify.ADMIN_ID]
    finally:
        notify.avisar = original


def test_aviso_sai_do_PONTO_UNICO_onde_o_usuario_nasce():
    """São 10 lugares chamando get_or_create_user. Instrumentar os chamadores
    é receita de esquecer um — o aviso mora no insert."""
    import inspect

    from app.db.repository import Repository

    fonte = inspect.getsource(Repository.get_or_create_user)
    assert "avisar_admin_usuario_novo" in fonte
    # e só depois do INSERT ter dado certo: usuário que já existia não avisa
    assert fonte.index("created.data") < fonte.index("avisar_admin_usuario_novo")


def test_falha_no_aviso_nao_derruba_o_cadastro(monkeypatch):
    """Telegram fora do ar não pode impedir alguém de se cadastrar.

    Por COMPORTAMENTO: o aviso EXPLODE e o teste cobra que o usuário volte
    assim mesmo. A versão anterior procurava `except Exception` no texto-fonte
    e conferia como o método termina — o que passa mesmo se o `try` estiver
    em volta do bloco errado, ou se o `raise` vier de dentro do `if`.
    """
    from app.db.repository import Repository

    class _Res:
        def __init__(self, data=None, count=None):
            self.data = data if data is not None else []
            self.count = count

    class _Users:
        def __init__(self, existentes):
            self._existentes = existentes
            self._count = False

        def select(self, *_a, count=None):
            self._count = count == "exact"
            return self

        def eq(self, *_a):
            return self

        def insert(self, linha):
            self._novo = linha
            return self

        def execute(self):
            if getattr(self, "_novo", None) is not None:
                return _Res([{**self._novo, "id": "u-novo"}])
            if self._count:
                return _Res([], count=7)
            return _Res(self._existentes)

    class _Cliente:
        def table(self, _nome):
            return _Users([])

    # `client` é property sem setter e `enabled` decide o _guard — então o
    # duplo entra por `_client`, que é o campo que a property devolve
    repo = Repository.__new__(Repository)
    repo.enabled = True
    repo._client = _Cliente()

    explodiu: list = []

    def _avisar_quebrado(*a, **k):
        explodiu.append(1)
        raise RuntimeError("Telegram fora do ar")

    import app.bot.notify as notify

    monkeypatch.setattr(notify, "avisar_admin_usuario_novo", _avisar_quebrado)

    criado = repo.get_or_create_user(555001, "novato", "pt")

    assert explodiu, "o aviso nem chegou a ser tentado — o teste não mediu nada"
    assert criado is not None, "o cadastro foi perdido porque o aviso falhou"
    assert criado["telegram_id"] == 555001 and criado["username"] == "novato"
