"""O menu por categoria: uma fonte só, e o submenu que de fato abre.

O menu '/' do Telegram é flat — `setMyCommands` recebe uma lista sem grupo
nem separador, e não há como pedir aninhamento. Então a organização vive em
dois lugares: a ORDEM (+ emoji) na lista flat, e um submenu de verdade em
teclado inline no /start.

O risco que estes testes cobrem não é o desenho, é a DIVERGÊNCIA. A lista de
comandos já existiu em três cópias escritas à mão — `set_my_commands` com 19,
a ajuda longa com 12, o manual com outra coisa — e um comando que some de uma
delas vira comando que só quem já sabia encontra. Agora há uma fonte só, e o
que se confere é que os consumidores continuam saindo dela.
"""
from __future__ import annotations

import asyncio
import inspect
import re

import pytest

from app.bot import catalogo, handlers


# ---- o catálogo ------------------------------------------------------------

def test_nenhum_comando_em_duas_categorias():
    """Duplicata no catálogo vira duplicata no menu '/' — e o Telegram não
    reclama, só mostra o comando duas vezes."""
    todos = [c.nome for c in catalogo.todos_os_comandos()]
    repetidos = {n for n in todos if todos.count(n) > 1}
    assert not repetidos, f"comando em mais de uma categoria: {sorted(repetidos)}"


def test_o_menu_flat_sai_agrupado_por_categoria():
    """Numa lista sem cabeçalho, o agrupamento É a ordem: os comandos de uma
    categoria têm que sair em bloco contíguo, senão o emoji na frente vira
    enfeite e o aluno lê 19 itens embaralhados."""
    pares = catalogo.pares_do_menu()
    emojis = [desc.split(" ", 1)[0] for _, desc in pares]

    blocos = [e for i, e in enumerate(emojis) if i == 0 or e != emojis[i - 1]]
    assert len(blocos) == len(set(blocos)), (
        f"categoria interrompida e retomada mais adiante: {emojis}")
    assert blocos == [cat.emoji for cat in catalogo.CATEGORIAS]


def test_o_menu_cabe_nos_limites_do_telegram():
    """`setMyCommands` recusa a lista inteira se UM item for inválido — e a
    chamada mora dentro de um `except: pass`, então o bot subiria sem menu
    nenhum, em silêncio."""
    pares = catalogo.pares_do_menu()
    assert len(pares) <= 100, "o Telegram aceita no máximo 100 comandos"
    for nome, desc in pares:
        assert re.fullmatch(r"[a-z0-9_]{1,32}", nome), f"nome inválido: {nome}"
        assert 1 <= len(desc) <= 256, f"descrição fora do limite: {nome}"


# ---- os consumidores continuam saindo do catálogo --------------------------

def test_a_ajuda_longa_anuncia_TODOS_os_comandos():
    """O caso real: o texto de "Como funciona" listava 12 dos 19 comandos.
    /banca, /foco, /leitura, /prova, /spot e /vilao existiam, funcionavam e
    não apareciam para quem lia a ajuda."""
    faltando = [c.nome for c in catalogo.todos_os_comandos()
                if f"/{c.nome}" not in handlers.WELCOME]
    assert not faltando, (
        f"comandos vivos que a ajuda longa não menciona: {faltando}")


def test_o_menu_do_telegram_e_gerado_e_nao_escrito_a_mao():
    """Se alguém voltar a escrever `BotCommand(...)` item a item aqui, as
    cópias recomeçam a divergir no dia seguinte."""
    fonte = inspect.getsource(handlers._set_bot_menu)
    assert "pares_do_menu" in fonte
    nomes_soltos = re.findall(r'BotCommand\("([a-z_]+)"', fonte)
    assert not nomes_soltos, (
        f"lista escrita à mão de volta no menu: {nomes_soltos}")


# ---- o submenu abre de verdade ---------------------------------------------

class _Repo:
    enabled = False

    def __getattr__(self, _n):
        return lambda *a, **k: None


class _Query:
    """Callback query falsa. Guarda o que foi editado — é o que o aluno vê."""

    def __init__(self, data: str, edicao_falha: bool = False):
        self.data = data
        self.respondeu = False
        self.editado: str | None = None
        self.teclado = None
        self.nova_mensagem: str | None = None
        self._falha = edicao_falha
        query = self

        class _Msg:
            async def reply_markdown(self, texto, reply_markup=None, **k):
                query.nova_mensagem = texto
                query.teclado = reply_markup

        self.message = _Msg()

    async def answer(self):
        self.respondeu = True

    async def edit_message_text(self, texto, parse_mode=None, reply_markup=None):
        if self._falha:
            raise RuntimeError("message is not modified")
        self.editado = texto
        self.teclado = reply_markup


class _Update:
    def __init__(self, query):
        self.callback_query = query
        self.effective_user = None
        self.message = None


def _abrir(data: str, **kw) -> _Query:
    q = _Query(data, **kw)
    asyncio.run(handlers.on_menu(_Update(q), None))
    return q


def _rotulos(teclado) -> list[str]:
    return [b.text for linha in teclado.inline_keyboard for b in linha]


def _destinos(teclado) -> list[str]:
    return [b.callback_data for linha in teclado.inline_keyboard for b in linha]


@pytest.fixture(autouse=True)
def _sem_banco(monkeypatch):
    monkeypatch.setattr(handlers, "get_repository", lambda: _Repo())


def test_a_raiz_oferece_uma_porta_para_cada_categoria():
    """Categoria sem botão é categoria inalcançável — os comandos dela voltam
    a existir só para quem já sabia."""
    q = _abrir("menu:home")
    assert q.respondeu, "callback sem answer() deixa o botão girando no cliente"
    assert set(_destinos(q.teclado)) == {
        f"menu:{cat.slug}" for cat in catalogo.CATEGORIAS}


@pytest.mark.parametrize("cat", catalogo.CATEGORIAS, ids=lambda c: c.slug)
def test_cada_categoria_abre_com_seus_comandos_e_a_volta(cat):
    q = _abrir(f"menu:{cat.slug}")
    for c in cat.comandos:
        assert f"/{c.nome}" in q.editado, (
            f"/{c.nome} está em {cat.slug} e não apareceu ao abrir a categoria")
    de_outras = [c.nome for outra in catalogo.CATEGORIAS if outra is not cat
                 for c in outra.comandos if f"/{c.nome} —" in q.editado]
    assert not de_outras, f"{cat.slug} vazou comando de outra: {de_outras}"
    assert _destinos(q.teclado) == ["menu:home"], "submenu sem volta é beco"


def test_o_submenu_edita_a_mensagem_em_vez_de_empilhar_copias():
    q = _abrir("menu:treino")
    assert q.editado and q.nova_mensagem is None


def test_edicao_que_falha_cai_para_mensagem_nova():
    """Mensagem antiga demais e "não modificada" fazem o `editMessageText`
    explodir. Menu que trava é pior que menu duplicado."""
    q = _abrir("menu:treino", edicao_falha=True)
    assert q.nova_mensagem and "/treino" in q.nova_mensagem


def test_botao_de_versao_antiga_cai_na_raiz_em_vez_de_sumir():
    """Teclado velho na conversa continua clicável para sempre."""
    q = _abrir("menu:categoria_que_nao_existe_mais")
    assert q.editado and set(_destinos(q.teclado)) == {
        f"menu:{cat.slug}" for cat in catalogo.CATEGORIAS}


def test_o_submenu_esta_registrado_e_o_start_leva_ate_ele():
    """Handler não registrado = botão que não faz nada."""
    fonte = inspect.getsource(handlers)
    assert re.search(r'CallbackQueryHandler\(on_menu,\s*pattern=r?"\^menu:"',
                     fonte), "on_menu não está registrado no padrão ^menu:"
    assert "menu:home" in _destinos(handlers._START_KB), (
        "o /start não tem porta para o menu de comandos")
