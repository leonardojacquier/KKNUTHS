"""O botão 🔍 de cada mão do relatório mão a mão — o HTML de volta para o bot.

Pedido do dono, na íntegra: *"se tiver torneios mais longos analisa as 150
principais mãos e o resto coloca algo mais simplificado e coloca o botão"*.

Cada mão do HTML leva `t.me/KKNUts_BOT?start=mao_<Nº da sala>`. Clicar abre o
Telegram e dispara a análise COMPLETA daquela mão — o mesmo caminho da mão
avulsa (`process_upload`), com selo, placar street a street, voz nova e todos
os guardas; nada de orquestração duplicada.

O link é público e encaminhável — vai parar no grupo do clube. Por isso a
busca da mão já NASCE escopada em quem clicou: mão de aluno é dado de aluno, e
a linha de outro dono não chega nem a ser lida do banco.

Tudo determinístico: o caminho de análise entra mockado (salvo no teste de
cota, que roda o `process_upload` de verdade com o coach falso). Nenhuma
chamada de rede ou de LLM.
"""
from __future__ import annotations

import asyncio

import pytest

from app.models.canonical import (Action, ActionType, CanonicalHand,
                                  HandFormat, PlayerSeat, Stakes, Street,
                                  StreetName)

_BB = 100.0


def _mao(hand_id: str, *, net_bb: float = 0.0, aposta_bb: float = 1.0,
         allin: bool = False) -> CanonicalHand:
    """Mão de torneio sintética — o molde mínimo que o relatório aceita."""
    aposta = aposta_bb * _BB
    ganho = (net_bb + aposta_bb) * _BB        # net = ganho - investido
    return CanonicalHand(
        hand_id=hand_id, site="ggpoker", format=HandFormat.TOURNAMENT,
        tournament_id="T1",
        stakes=Stakes(small_blind=_BB / 2, big_blind=_BB),
        hero="Hero", hero_cards=["Ah", "Kd"],
        players=[
            PlayerSeat(seat=1, name="Hero", stack=5000, position="BTN",
                       is_hero=True),
            PlayerSeat(seat=2, name="Vilao", stack=5000, position="BB"),
        ],
        streets=[Street(name=StreetName.PREFLOP, actions=[
            Action(actor="Vilao", type=ActionType.POST, amount=_BB,
                   post_type="bb"),
            Action(actor="Hero", type=ActionType.RAISE, amount=aposta,
                   to_amount=aposta, all_in=allin),
            Action(actor="Vilao", type=ActionType.FOLD),
        ])],
        collected={"Hero": ganho} if ganho else {},
        played_at="2026-08-15T20:00:00Z",
    )


def test_cada_mao_do_relatorio_leva_o_botao_de_analise_completa():
    from app.analysis.handreport import build_report_html

    html = build_report_html([_mao("TM9001", net_bb=2.0)])
    assert "https://t.me/KKNUts_BOT?start=mao_TM9001" in html
    assert "Análise completa no bot" in html


def test_numero_de_mao_que_nao_cabe_no_link_nao_vira_botao_quebrado():
    """O payload de /start do Telegram aceita no máximo 64 chars de
    [A-Za-z0-9_-]. Fora disso o link abre o bot e perde a mão — melhor não
    prometer botão do que entregar botão morto."""
    from app.bot.mao_do_relatorio import link_da_mao

    assert link_da_mao("TM9001")
    assert link_da_mao("TM 90/01") is None
    assert link_da_mao("X" * 80) is None
    assert link_da_mao("") is None
    assert link_da_mao(None) is None


class _RepoDeMaos:
    """Repositório falso com dono por mão.

    Registra as CONSULTAS para o teste provar que a busca já nasce escopada
    pelo dono — mão alheia não chega nem a ser lida do banco.
    """

    enabled = True

    def __init__(self, por_dono, dono_por_telegram, plan="pro"):
        self.por_dono = por_dono
        self.dono_por_telegram = dono_por_telegram
        self.plan = plan
        self.consultas: list[tuple] = []
        self.usos: list[tuple] = []

    def get_or_create_user(self, telegram_id, username=None, lang="pt"):
        uid = self.dono_por_telegram.get(telegram_id)
        return {"id": uid, "plan": self.plan} if uid else None

    def get_hand_by_room_id(self, user_id, hand_id):
        self.consultas.append((user_id, hand_id))
        return self.por_dono.get(user_id, {}).get(hand_id)

    def record_usage(self, user_id, type_, cost_credits=0):
        self.usos.append((user_id, type_, cost_credits))

    def get_hands_para_perfil(self, user_id, limit=5000):
        return ([], 0)

    def save_upload(self, *a, **k):
        return "up1"

    def save_hand(self, *a, **k):
        return "h1"

    def __getattr__(self, nome):
        return lambda *a, **k: None


def test_o_botao_roda_a_analise_completa_da_mao_para_o_dono(monkeypatch):
    """O galho do /start reaproveita o caminho de mão avulsa (`process_upload`)
    com a mão já lida — nada de orquestração duplicada."""
    from app.bot import mao_do_relatorio as M
    from app.bot import processing as proc

    repo = _RepoDeMaos({"u1": {"TM9001": _mao("TM9001", net_bb=3.0)}},
                       {111: "u1"})
    monkeypatch.setattr(M, "get_repository", lambda: repo)
    visto: dict = {}

    def _falso(content, fmt, telegram_id, username, lang="pt", caption=None,
               maos=None):
        visto.update(maos=maos, telegram_id=telegram_id, fmt=fmt)
        return "ANÁLISE COMPLETA DA MÃO"

    monkeypatch.setattr(proc, "process_upload", _falso)

    saida = M.analisar_do_link(111, "leo", "mao_TM9001")
    assert saida == "ANÁLISE COMPLETA DA MÃO"
    assert [h.hand_id for h in visto["maos"]] == ["TM9001"]
    assert visto["telegram_id"] == 111


def test_link_encaminhado_nao_abre_a_mao_de_outro_aluno(monkeypatch):
    """O link do relatório pode ser repassado no grupo do clube. Mão do aluno
    é dado do aluno: para quem não é dono, recusa educada e nada mais."""
    from app.bot import mao_do_relatorio as M
    from app.bot import processing as proc

    do_leo = _mao("TM9001", net_bb=3.0)
    repo = _RepoDeMaos({"u1": {"TM9001": do_leo}}, {111: "u1", 222: "u2"})
    monkeypatch.setattr(M, "get_repository", lambda: repo)
    chamadas: list = []
    monkeypatch.setattr(proc, "process_upload",
                        lambda *a, **k: chamadas.append(a) or "NÃO DEVIA RODAR")

    saida = M.analisar_do_link(222, "curioso", "mao_TM9001")
    assert chamadas == [], "a análise rodou para quem não é dono da mão"
    # a busca já foi feita no escopo do CLICADOR: a linha do Leo não foi lida
    assert repo.consultas == [("u2", "TM9001")]
    assert saida and "não" in saida.lower()
    for vazamento in ("A♥", "K♦", "Ah", "Kd", "BTN", "+3.0"):
        assert vazamento not in saida, vazamento


def test_a_analise_pelo_botao_conta_na_cota_como_analise_normal(monkeypatch):
    """Default sensato: quem abre a mão pelo botão gasta uma análise, igual a
    quem manda a mão no chat. Roda o `process_upload` de verdade (com o coach
    mockado) para provar que o consumo acontece, não só que foi chamado."""
    from app.bot import mao_do_relatorio as M
    from app.bot import processing as proc

    repo = _RepoDeMaos({"u1": {"TM9001": _mao("TM9001", net_bb=3.0)}},
                       {111: "u1"})
    monkeypatch.setattr(M, "get_repository", lambda: repo)
    monkeypatch.setattr(proc, "get_repository", lambda: repo)
    monkeypatch.setattr(proc, "coach",
                        lambda *a, **k: "✅ Boa decisão. Texto do coach.")

    saida = M.analisar_do_link(111, "leo", "mao_TM9001")
    assert saida
    assert repo.usos == [("u1", "analysis", 1)], repo.usos
    proc.RECENT_HANDS.pop(111, None)
    proc.LAST_ANALYSIS.pop(111, None)


# ------------------------- o /start do Telegram --------------------------

class _Msg:
    def __init__(self):
        self.enviadas: list[str] = []

    async def reply_text(self, texto, **k):
        self.enviadas.append(texto)
        return self

    async def reply_markdown(self, texto, **k):
        self.enviadas.append(texto)
        return self

    async def delete(self):
        pass


class _TgUser:
    id = 111
    username = "leo"
    full_name = "Leo"


class _Update:
    def __init__(self):
        self.message = _Msg()
        self.effective_user = _TgUser()
        self.callback_query = None


class _Ctx:
    def __init__(self, args):
        self.args = args


def test_o_start_com_payload_de_mao_entrega_a_analise_no_lugar_do_bem_vindo(
        monkeypatch):
    from app.bot import handlers
    from app.bot import mao_do_relatorio as M

    repo = _RepoDeMaos({"u1": {"TM9001": _mao("TM9001", net_bb=3.0)}},
                       {111: "u1"})
    monkeypatch.setattr(M, "get_repository", lambda: repo)
    monkeypatch.setattr(M, "analisar_do_link",
                        lambda tg, nome, ref: "ANÁLISE COMPLETA DA MÃO")

    upd = _Update()
    asyncio.run(handlers.cmd_start(upd, _Ctx(["mao_TM9001"])))

    juntas = "\n".join(upd.message.enviadas)
    assert "ANÁLISE COMPLETA DA MÃO" in juntas
    assert handlers.WELCOME_SHORT not in juntas


def test_o_start_normal_continua_dando_as_boas_vindas():
    """O galho novo não pode roubar o /start de quem chega pelo convite."""
    from app.bot import handlers

    upd = _Update()
    asyncio.run(handlers.cmd_start(upd, _Ctx(["convite"])))
    assert handlers.WELCOME_SHORT in "\n".join(upd.message.enviadas)


@pytest.mark.parametrize("ref,esperado", [
    ("mao_TM9001", "TM9001"),
    ("mao_", None),
    ("convite", None),
    (None, None),
    ("mao_TM 9001", None),
])
def test_so_o_payload_de_mao_e_lido_como_mao(ref, esperado):
    from app.bot.mao_do_relatorio import id_no_payload

    assert id_no_payload(ref) == esperado
