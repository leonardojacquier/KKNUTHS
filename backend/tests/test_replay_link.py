"""Link de replay: o que abre sozinho, e o que a mensagem diz quando não abre.

O aluno colou um link e recebeu "esse tipo eu ainda não abro sozinho". A
mesma frase saía em dois casos incompatíveis: clube que eu realmente não
leio, e link da PPPoker — que eu LEIO — cuja chave o regex não pegou. No
segundo caso a mensagem é falsa.
"""
from app.bot.processing import replay_fallback_text, replay_link_info
from app.parsers.pppoker_replay import share_key_from_url

CHAVE = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"


# ------------------------------------------------------- extração da chave
def test_formatos_de_link_que_o_aluno_cola():
    assert share_key_from_url(
        f"https://pppoker.club/share.php?lang=pt&shareKey={CHAVE}") == CHAVE
    assert share_key_from_url(
        f"https://replay.pppoker.net/#/?shareKey={CHAVE}") == CHAVE


def test_variantes_do_nome_do_parametro():
    """app, web e chat do clube escrevem diferente — e o regex era
    case-sensitive, devolvendo None num link BOM."""
    for param in ("shareKey", "sharekey", "SHAREKEY", "share_key"):
        url = f"https://pppoker.club/share.php?{param}={CHAVE}"
        assert share_key_from_url(url) == CHAVE, param


def test_chave_com_underscore_e_url_escapada():
    chave = "abc_DEF-123456789"
    assert share_key_from_url(
        f"https://pppoker.club/s?shareKey={chave}") == chave
    assert share_key_from_url(
        f"https://pppoker.club/s%3FshareKey%3D{CHAVE}") == CHAVE


def test_uuid_solto_e_o_ultimo_recurso():
    assert share_key_from_url(
        f"https://pppoker.club/review/{CHAVE}") == CHAVE


def test_nao_inventa_chave_onde_nao_tem():
    assert share_key_from_url("https://pppoker.club/") is None
    assert share_key_from_url("https://pppoker.club/share.php?lang=pt") is None
    assert share_key_from_url("") is None
    assert share_key_from_url(None) is None
    # chave curta demais não vale (evita casar com id de sessão)
    assert share_key_from_url("https://pppoker.club/s?shareKey=abc") is None


# ------------------------------------------------------------- detecção
def test_pppoker_resolve_a_chave_e_suprema_nao():
    pp = replay_link_info(f"https://pppoker.club/share.php?shareKey={CHAVE}")
    assert pp["site"] == "pppoker" and pp["share_key"] == CHAVE

    sup = replay_link_info("https://supremapoker.net/replay?id=99")
    assert sup["site"] == "suprema" and sup["share_key"] is None


def test_link_sem_https_tambem_conta():
    """O público cola o link copiado do chat do clube, sem protocolo."""
    r = replay_link_info(f"replay.pppoker.net/#/?shareKey={CHAVE}")
    assert r and r["share_key"] == CHAVE


# -------------------------------------------------------------- mensagem
def test_clube_nao_suportado_diz_o_nome_e_o_que_funciona():
    txt = replay_fallback_text("suprema")
    assert "Suprema" in txt and "PPPoker" in txt
    assert "Print do replay" in txt


def test_pppoker_ilegivel_nao_mente_dizendo_que_nao_abre():
    """O defeito: 'não abro esse tipo' sobre um replay que eu abro."""
    txt = replay_fallback_text("pppoker", chave_ilegivel=True)
    assert "esse eu abro sozinho" in txt
    assert "Compartilhar" in txt          # diz COMO consertar
    assert "não abro" not in txt.split("Se preferir")[0]


def test_gg_gl_e_reconhecido_como_replay():
    """Encurtador da GGPoker. Fora da lista de hosts, o link caía no leitor
    de TEXTO e o aluno recebia 'não entendi' — a pior resposta possível,
    porque sugere que ele errou."""
    r = replay_link_info("https://gg.gl/fovbb")
    assert r and r["site"] == "ggpoker"
    assert r["share_key"] is None          # ainda não abrimos sozinho
    txt = replay_fallback_text("ggpoker")
    assert "GGPoker" in txt and "Print do replay" in txt


def test_ggpoker_aponta_para_o_caminho_MELHOR_e_nao_so_para_o_print():
    """A mão da GGPoker vem cifrada, mas existe saída oficial e superior: o
    histórico do PokerCraft traz a SESSÃO inteira, não uma mão. Mandar o
    aluno só para o print seria dar o pior conselho disponível."""
    txt = replay_fallback_text("ggpoker")
    assert "PokerCraft" in txt and "Hand History" in txt
    assert ".txt" in txt
    assert "sessão inteira" in txt
    # e não promete abrir o que não abre
    assert "não abro" in txt


def test_ggpoker_ensina_a_pedir_a_MAO_especifica_depois():
    """O alias do link é código de compartilhamento, resolvido só no
    servidor deles — não vira Hand ID por fora. Mas o PokerCraft mostra o
    Hand ID, e a busca por id JÁ EXISTE no handsearch: o aluno traz o
    número e a mão é achada no arquivo dele. Fecha o ciclo sem o link."""
    txt = replay_fallback_text("ggpoker")
    assert "Hand ID" in txt
    assert "analisa a mão" in txt          # a frase que ele pode copiar


def test_busca_por_hand_id_realmente_existe():
    """A instrução acima só vale se a busca funcionar de verdade — prometer
    ao aluno um caminho que não existe é pior que não oferecer nada."""
    from app.analysis.handsearch import find_hand
    from app.api.site_assets import _demo_hand

    mao = _demo_hand()
    achado = find_hand([mao], mao.hand_id)
    assert achado and achado[0]["hand_id"] == mao.hand_id
    # id curto demais não casa (senão qualquer letra varreria o histórico)
    assert not find_hand([mao], "ab")


def test_o_coach_tem_a_ferramenta_de_abrir_mao_por_numero():
    """De nada adianta a busca existir se o coach não puder chamá-la — foi
    exatamente o defeito do gráfico de EV, que existia e nunca era invocado.
    """
    from app.agent.llm import TOOLS, _dispatch

    nomes = {t["name"] for t in TOOLS}
    assert "get_hand" in nomes
    esquema = next(t for t in TOOLS if t["name"] == "get_hand")
    assert "query" in esquema["input_schema"]["properties"]
    # sem histórico na conversa ela responde com ERRO explícito, não em branco
    assert "error" in _dispatch("get_hand", {"query": "RC1234567890"})


def test_mensagem_dos_outros_clubes_cita_as_duas_salas_que_abrem():
    txt = replay_fallback_text("clubgg")
    assert "ClubGG" in txt and "PPPoker" in txt and "Suprema" in txt


def test_clube_desconhecido_nao_quebra_a_mensagem():
    txt = replay_fallback_text("outro")
    assert "desse clube" in txt and "PPPoker" in txt
    assert replay_fallback_text(None)     # sem site: ainda tem que sair texto
