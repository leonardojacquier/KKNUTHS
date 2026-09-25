"""O /stats do aluno de clube, e o botão que ensina onde fica o link.

Diagnóstico de 06/09 §2.2, ainda aberto em 25/09: replay e print ficam fora
das estatísticas de frequência (certo — são mãos escolhidas). Mas o aluno
com 50 replays ouvia do /stats "Ainda não tenho mãos suas". Falso. E o
botão Enviar dizia "link de replay, é só colar" sem dizer onde fica o link
— 19/09, o Fabio foi mais um cadastro sem nenhuma mão.
"""
from __future__ import annotations

from app.bot import perfil_de_decisoes as P

RESUMOS = [
    "✅ Você jogou bem — 3-bet e shove bem embasados\n\n"
    "✅ *Pré* — 3-bet 8bb com 8♠8♣.\n✅ *Flop* — shove.",
    "❌ Jogada cara — pagou o river sem preço\n\n"
    "✅ *Pré* — abriu.\n🟡 *Turn* — check.\n❌ *River* — pagou 18bb.",
    "🟡 Dava pra jogar melhor — sizing do pré\n\n"
    "🟡 *Pré* — abriu 4bb.\n❌ *River* — hero call sem blocker.",
]


def test_conta_os_selos_das_analises_entregues():
    c = P.contar(RESUMOS)
    assert c["geral"] == {"✅": 1, "🟡": 1, "❌": 1}
    assert c["por_street"]["river"]["❌"] == 2
    assert c["motivos_x"] == ["pagou o river sem preço"]


def test_texto_diz_o_placar_e_onde_escapa_e_explica_o_vpip():
    t = P.texto(RESUMOS, 3)
    assert "3 mão(s)" in t
    assert "✅ 1 · 🟡 1 · ❌ 1" in t
    assert "*river*" in t, "a street onde o erro se concentra"
    assert "sessão inteira" in t, "tem que dizer por que não há VPIP"


def test_replay_only_nao_ouve_mais_que_nao_tem_maos(monkeypatch):
    from app.bot import processing
    from app.models.canonical import CanonicalHand, PlayerSeat, Stakes

    mao = CanonicalHand(
        site="pppoker", hand_id="r1", hero="Hero",
        stakes=Stakes(small_blind=0.5, big_blind=1),
        players=[PlayerSeat(seat=1, name="Hero", stack=100, is_hero=True)],
        hero_cards=["Ah", "Kd"], streets=[], source_format="pppoker_replay")

    class _Repo:
        enabled = True

        def get_or_create_user(self, *a):
            return {"id": "u1"}

        def get_all_hands(self, _uid):
            return [mao] * 12

        def get_analysis_summaries(self, _uid):
            return RESUMOS

    monkeypatch.setattr(processing, "get_repository", lambda: _Repo())
    out = processing.stats_report(1, "t")
    assert out, "replay-only voltou a cair em 'Ainda não tenho mãos suas'"
    assert "12 mão(s)" in out and "Veredito do coach" in out
    assert "VPIP" in out and "%" not in out.split("_")[0], \
        "não pode inventar VPIP de mãos escolhidas"


def test_botao_enviar_ensina_o_compartilhar_e_o_lobby():
    from app.bot.handlers import _ENVIAR_TXT

    for termo in ("PPPoker", "Suprema", "Compartilhar", "lobby", ".zip"):
        assert termo in _ENVIAR_TXT, termo


def test_estilo_nao_manda_quem_tem_replay_embora_sem_rumo():
    import inspect

    from app.bot import handlers

    fonte = inspect.getsource(handlers.cmd_estilo)
    assert "/stats" in fonte and "Replay" in fonte
