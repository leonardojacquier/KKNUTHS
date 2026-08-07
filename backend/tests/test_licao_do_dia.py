"""Lição do dia: envio diário do que o DONO aprovou — nunca do estoque cru.

Pedido do dono (07/08): "criar um enviar diário dessa lição escolhida".
A trava é a de sempre: o destilador estoca, o dono aprova (/licoes N ok),
o cron envia UMA por dia. Lição não aprovada não sai; lição já enviada não
repete; fila vazia é silêncio pro aluno e aviso pro dono.
"""
import inspect

from scripts.licao_do_dia import main, texto_da_licao

_LICAO = {"id": 7, "titulo": "Pagar river sem preço",
          "spot": "Torneio, ~20bb. Vilão dá overbet no river.",
          "licao": "Pedia 33% e a mão tinha 18%.", "ev_bb": -9.3,
          "categoria": "river"}


def test_texto_traz_o_custo_e_termina_convidando_a_mao():
    t = texto_da_licao(_LICAO)
    assert "Lição do dia" in t and _LICAO["titulo"] in t
    assert "9.3bb" in t, "o número que prova a lição"
    assert "custou" in t
    assert t.rstrip().endswith("analiso na hora."), \
        "o CTA da primeira mão fecha SEMPRE — é o gargalo do funil"


def test_ganho_aparece_como_rendeu():
    t = texto_da_licao({**_LICAO, "ev_bb": 11.9})
    assert "rendeu 11.9bb" in t


def test_ev_ausente_nao_quebra_nem_inventa():
    t = texto_da_licao({**_LICAO, "ev_bb": None})
    assert "custou" not in t and "rendeu" not in t


def test_licao_anonima_nao_vaza_aluno():
    """O texto enviado sai só do que o destilador já anonimizou."""
    t = texto_da_licao(_LICAO)
    assert "anonimizado" in t.lower()
    for campo in ("hand_analysis_id", "user", "telegram"):
        assert campo not in t


def test_so_sai_o_que_foi_aprovado_e_nunca_repete():
    fonte = inspect.getsource(__import__("scripts.licao_do_dia",
                                         fromlist=["proxima_licao"]).proxima_licao)
    assert 'eq("aprovada", True)' in fonte, "estoque cru não sai"
    assert 'is_("enviada_em", "null")' in fonte, "enviada não repete"
    assert '.order("id")' in fonte, "FIFO: a mais antiga aprovada primeiro"


def test_fila_vazia_avisa_o_dono_e_nao_incomoda_o_aluno():
    fonte = inspect.getsource(main)
    bloco = fonte[fonte.index("if not licao:"):fonte.index("enviar_licao(")]
    assert "ADMIN_ID" in bloco, "o dono é avisado"
    assert "return 0" in bloco, "e o cron sai sem mandar nada pro aluno"
    assert "enviar_licao(repo" not in bloco, "aluno não recebe nada"


def test_marca_como_enviada_depois_de_enviar():
    """O envio mora em app/bot/licao_envio (comando e cron compartilham)."""
    from app.bot.licao_envio import enviar_licao

    fonte = inspect.getsource(enviar_licao)
    assert "enviada_em" in fonte and "publicada" in fonte
    assert fonte.index("for u in users") < fonte.index('"enviada_em":'), \
        "marca DEPOIS do envio — falha no meio não perde a lição"


def test_comando_aprova_e_desaprova():
    from app.bot.processing import licoes_reply

    fonte = inspect.getsource(licoes_reply)
    assert '"aprovada": True' in fonte and '"aprovada": False' in fonte
    assert "já foi enviada" in fonte, "não deixa reaprovar o que já saiu"
