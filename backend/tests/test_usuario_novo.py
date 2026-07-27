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


def test_falha_no_aviso_nao_derruba_o_cadastro():
    """Telegram fora do ar não pode impedir alguém de se cadastrar."""
    import inspect

    from app.db.repository import Repository

    fonte = inspect.getsource(Repository.get_or_create_user)
    trecho = fonte[fonte.index("avisar_admin_usuario_novo"):]
    assert "except Exception" in fonte[:fonte.index("avisar_admin_usuario_novo")] \
        or "except Exception" in trecho, "aviso precisa estar protegido"
    # o return do usuário vem DEPOIS e independe do aviso
    assert fonte.rstrip().endswith("return created.data[0] if created.data else None")
